# Add at the top of main.tf for consistent naming
locals {
  project_prefix = "${var.owner_prefix}-${var.project_name}-${var.environment}"
  common_tags = {
    Owner       = "hutch"
    OwnerEmail  = "hutchenbach@gmail.com"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    CreatedDate = "2025-07-22"  # Use a fixed date instead of timestamp()
  }
}

# Generate random password for RDS
resource "random_password" "db_password" {
  length  = 32
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Data source to get default VPC
data "aws_vpc" "default" {
  default = true
}

# Data source to get subnets
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Create security group for RDS
resource "aws_security_group" "rds" {
  name        = "${local.project_prefix}-rds-sg" 
  description = "Security group for ${var.owner_prefix} ${var.project_name} RDS instance - ${var.environment}"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["${var.allowed_ip}/32"]
    description = "PostgreSQL access from developer IP"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-rds-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Create DB subnet group
resource "aws_db_subnet_group" "main" {
  name        = "${local.project_prefix}-subnet-group" 
  description = "DB subnet group for ${var.owner_prefix} ${var.project_name} - ${var.environment}"
  subnet_ids  = data.aws_subnets.default.ids

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-db-subnet-group"
  })
}

# Create RDS PostgreSQL instance
resource "aws_db_instance" "learntrac" {
  identifier = "${local.project_prefix}-db" 
  
  # Engine configuration
  engine         = "postgres"
  engine_version = "15.8"  
  instance_class = var.db_instance_class
  
  # Storage
  allocated_storage     = var.db_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  
  # Database configuration
  db_name  = var.project_name
  username = "${var.project_name}_admin"
  password = random_password.db_password.result
  port     = 5432
  
  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = true
  
  # Backup configuration
  backup_retention_period = var.environment == "prod" ? 30 : 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  # Performance and monitoring
  enabled_cloudwatch_logs_exports = ["postgresql"]
  performance_insights_enabled    = var.environment == "prod"
  monitoring_interval            = var.environment == "prod" ? 60 : 0
  
  # Other settings
  auto_minor_version_upgrade = true
  deletion_protection       = var.environment == "prod"
  skip_final_snapshot      = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${local.project_prefix}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-database"
  })
}

# Store password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name        = "${local.project_prefix}-db-credentials"
  description = "RDS credentials for ${var.owner_prefix} ${var.project_name} database - ${var.environment}"
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-db-secret"
  })
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = aws_db_instance.learntrac.username
    password = random_password.db_password.result
    engine   = "postgres"
    host     = aws_db_instance.learntrac.address
    port     = aws_db_instance.learntrac.port
    dbname   = aws_db_instance.learntrac.db_name
  })
}

# API Gateway REST API for LearnTrac (without Cognito authorizer)
resource "aws_api_gateway_rest_api" "learntrac" {
  name        = "${local.project_prefix}-api"
  description = "API Gateway for LearnTrac services - ${var.environment}"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-api-gateway"
  })
}

# Note: API Gateway deployment moved to api-gateway-enhanced.tf 
# where methods are defined to ensure deployment has methods

# API Gateway Stage  
resource "aws_api_gateway_stage" "learntrac" {
  deployment_id = aws_api_gateway_deployment.learntrac.id
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  stage_name    = var.environment
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip            = "$context.identity.sourceIp"
      requestTime   = "$context.requestTime"
      httpMethod    = "$context.httpMethod"
      resourcePath  = "$context.resourcePath"
      status        = "$context.status"
      protocol      = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-api-stage-${var.environment}"
  })
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/api-gateway/${local.project_prefix}"
  retention_in_days = var.environment == "prod" ? 30 : 7
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-api-logs"
  })
}

# Note: ECR repositories are defined in ecr.tf