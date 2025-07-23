# LearnTrac Infrastructure

This directory contains all Terraform configurations and management scripts for the LearnTrac AWS infrastructure.

## Quick Start

1. Initialize Terraform:
   ```bash
   terraform init

2. Review planned changes:
   ```bash
    terraform plan

3. Apply infrastructure:
   ```bash
    terraform apply

4. Get database connection string:
   ```bash
    terraform output -raw rds_connection_string

Resource Naming Convention
All resources follow the pattern: learntrac-{environment}-{resource-type}

RDS Instance: learntrac-dev-db
Security Group: learntrac-dev-rds-sg
DB Subnet Group: learntrac-dev-subnet-group
Secrets: learntrac-dev-db-credentials

Management Scripts

list-learntrac-resources.sh - List all LearnTrac AWS resources
terraform destroy - Remove all infrastructure

Environment Variables

PROJECT_NAME: learntrac
ENVIRONMENT: dev/staging/prod
AWS_REGION: us-east-2

## Terraform Configuration Files

### main.tf
```hcl
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

# User Pool Client
resource "aws_cognito_user_pool_client" "learntrac_client" {
  name         = "${local.project_prefix}-client"
  user_pool_id = aws_cognito_user_pool.learntrac_users.id

  # OAuth settings
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  callback_urls                        = ["http://localhost:8000/auth/callback"]
  logout_urls                          = ["http://localhost:8000/logout"]
  supported_identity_providers         = ["COGNITO"]

  # Token validity
  refresh_token_validity        = 30     # days
  access_token_validity         = 1      # hours
  id_token_validity            = 1      # hours

  # Security
  prevent_user_existence_errors = "ENABLED"
  
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
  domain       = "${local.project_prefix}-auth"  # Will be: hutch-learntrac-dev-auth
  user_pool_id = aws_cognito_user_pool.learntrac_users.id
}
```

### outputs.tf
```hcl
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.learntrac.endpoint
}

output "rds_connection_string" {
  description = "PostgreSQL connection string for Trac"
  value       = "postgres://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.learntrac.endpoint}/${aws_db_instance.learntrac.db_name}"
  sensitive   = true
}

output "secret_manager_secret_name" {
  description = "AWS Secrets Manager secret name"
  value       = aws_secretsmanager_secret.db_password.name
}

output "security_group_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.learntrac_users.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.learntrac_client.id
}

output "cognito_user_pool_endpoint" {
  value = aws_cognito_user_pool.learntrac_users.endpoint
}

output "cognito_domain" {
  value = aws_cognito_user_pool_domain.learntrac_domain.domain
}

output "cognito_domain_url" {
  value = "https://${aws_cognito_user_pool_domain.learntrac_domain.domain}.auth.${var.aws_region}.amazoncognito.com"
}
```

### variables.tf
```hcl
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "owner_prefix" {
  description = "Owner prefix for all resources"
  type        = string
  default     = "hutch"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "learntrac"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "db_instance_class" {
  description = "RDS instance type"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "learntrac_admin"
}

variable "allowed_ip" {
  description = "Your IP address for database access"
  type        = string
  default     = "162.206.172.65"
}

variable "owner_email" {
  description = "Email of the resource owner"
  type        = string
  default     = "hutchenbach@gmail.com"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.7"  # Latest stable 15.x version
}
```

### versions.tf
```hcl
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
```

### terraform.tfvars
```hcl
aws_region   = "us-east-2"
project_name = "learntrac"
environment  = "dev"
allowed_ip   = "162.206.172.65"
```



