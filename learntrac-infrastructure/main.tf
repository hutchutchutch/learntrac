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

# IAM role for Lambda (moved before Lambda function)
resource "aws_iam_role" "lambda_cognito" {
  name = "${local.project_prefix}-lambda-cognito-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_cognito_basic" {
  role       = aws_iam_role.lambda_cognito.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Create Lambda for pre-token generation (moved before User Pool)
resource "aws_lambda_function" "cognito_pre_token_generation" {
  filename         = "lambda/cognito-pre-token-generation.zip"
  function_name    = "${local.project_prefix}-cognito-pre-token"
  role            = aws_iam_role.lambda_cognito.arn
  handler         = "cognito-pre-token-generation.handler"  # Fixed: should be filename.function_name
  runtime         = "python3.11"
  timeout         = 10
  source_code_hash = filebase64sha256("lambda/cognito-pre-token-generation.zip")

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-cognito-pre-token-lambda"
  })
}

# AWS Cognito User Pool for LearnTrac
resource "aws_cognito_user_pool" "learntrac_users" {
  name = "${local.project_prefix}-users"

  # Password policy
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # User attributes
  schema {
    attribute_data_type = "String"
    name                = "email"
    required            = true
    mutable             = true
  }

  schema {
    attribute_data_type = "String"
    name                = "name"
    required            = true
    mutable             = true
  }

  schema {
    attribute_data_type = "String"
    name                = "role"
    mutable             = true
  }

  # Lambda configuration
  lambda_config {
    pre_token_generation = aws_lambda_function.cognito_pre_token_generation.arn
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration
  auto_verified_attributes = ["email"]
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-user-pool"
  })

  lifecycle {
    ignore_changes = [schema]
  }
}

# Cognito Resource Server (moved outside User Pool)
resource "aws_cognito_resource_server" "learntrac_api" {
  identifier = "${local.project_prefix}-api"
  name       = "${local.project_prefix}-api"
  user_pool_id = aws_cognito_user_pool.learntrac_users.id

  scope {
    scope_name        = "read"
    scope_description = "Read access to LearnTrac API"
  }

  scope {
    scope_name        = "write"
    scope_description = "Write access to LearnTrac API"
  }

  scope {
    scope_name        = "admin"
    scope_description = "Admin access to LearnTrac API"
  }
}

# User Pool Client (fixed for OAuth flow compatibility)
resource "aws_cognito_user_pool_client" "learntrac_client" {
  name         = "${local.project_prefix}-client"
  user_pool_id = aws_cognito_user_pool.learntrac_users.id

  # OAuth settings
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]  # Removed client_credentials
  allowed_oauth_scopes                 = [
    "email", 
    "openid", 
    "profile",
    "${aws_cognito_resource_server.learntrac_api.identifier}/read",
    "${aws_cognito_resource_server.learntrac_api.identifier}/write",
    "${aws_cognito_resource_server.learntrac_api.identifier}/admin"
  ]
  
  callback_urls                = ["http://localhost:8000/auth/callback"]
  logout_urls                   = ["http://localhost:8000/logout"]
  supported_identity_providers  = ["COGNITO"]

  # Token validity
  refresh_token_validity = 30  # days
  access_token_validity  = 1   # hours
  id_token_validity      = 1   # hours

  # Security
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation      = true
  
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
}

# Create admin user group
resource "aws_cognito_user_group" "admins" {
  name         = "admins"
  user_pool_id = aws_cognito_user_pool.learntrac_users.id
  description  = "LearnTrac administrators"
  precedence   = 1
}

# Create instructor group
resource "aws_cognito_user_group" "instructors" {
  name         = "instructors"
  user_pool_id = aws_cognito_user_pool.learntrac_users.id
  description  = "LearnTrac instructors"
  precedence   = 2
}

# Create student group
resource "aws_cognito_user_group" "students" {
  name         = "students"
  user_pool_id = aws_cognito_user_pool.learntrac_users.id
  description  = "LearnTrac students"
  precedence   = 3
}

# Cognito Domain
resource "aws_cognito_user_pool_domain" "learntrac_domain" {
  domain       = "${local.project_prefix}-auth"
  user_pool_id = aws_cognito_user_pool.learntrac_users.id
}

# Grant Cognito permission to invoke Lambda
resource "aws_lambda_permission" "cognito_invoke" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cognito_pre_token_generation.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.learntrac_users.arn
}

# API Gateway for REST API
resource "aws_api_gateway_rest_api" "learntrac_api" {
  name        = "${local.project_prefix}-api"
  description = "LearnTrac API with Cognito authentication"

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-api-gateway"
  })
}

# Cognito authorizer
resource "aws_api_gateway_authorizer" "cognito" {
  name            = "${local.project_prefix}-cognito-authorizer"
  rest_api_id     = aws_api_gateway_rest_api.learntrac_api.id
  type            = "COGNITO_USER_POOLS"
  provider_arns   = [aws_cognito_user_pool.learntrac_users.arn]
  identity_source = "method.request.header.Authorization"
}

# Store Cognito configuration
resource "aws_secretsmanager_secret" "cognito_config" {
  name        = "${local.project_prefix}-cognito-config"
  description = "Cognito configuration for ${var.project_name}"
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-cognito-secret"
  })
}

resource "aws_secretsmanager_secret_version" "cognito_config" {
  secret_id = aws_secretsmanager_secret.cognito_config.id
  secret_string = jsonencode({
    user_pool_id    = aws_cognito_user_pool.learntrac_users.id
    client_id       = aws_cognito_user_pool_client.learntrac_client.id
    domain          = aws_cognito_user_pool_domain.learntrac_domain.domain
    region          = var.aws_region
  })
}