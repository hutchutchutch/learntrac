# LearnTrac Infrastructure

This directory contains all Terraform configurations and management scripts for the LearnTrac AWS infrastructure.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Components](#components)
- [Configuration](#configuration)
- [Operations](#operations)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Additional Documentation](#additional-documentation)

## Overview

LearnTrac is a learning management system built on top of Trac, integrating modern cloud services for enhanced educational features. The infrastructure includes:

- **AWS Cognito** for user authentication
- **RDS PostgreSQL** for data persistence
- **ElastiCache Redis** for session management
- **ECS Fargate** for containerized services
- **Application Load Balancer** for traffic distribution
- **VPC Endpoints** for secure AWS service access

## Prerequisites

### Required Tools

- **Terraform** >= 1.0
- **AWS CLI** >= 2.0
- **Docker** >= 20.10
- **PostgreSQL client** (psql)
- **Git**
- **jq** (for JSON processing)

### AWS Account Setup

1. AWS account with appropriate permissions
2. IAM user with programmatic access
3. Configured AWS CLI profile:
   ```bash
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Default region: us-east-2
   # Default output format: json
   ```

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/learntrac.git
cd learntrac/learntrac-infrastructure
```

### 2. Configure Environment

```bash
# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars
# Update allowed_ip with your current IP address
```

### 3. Initialize and Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Apply infrastructure (takes ~10-15 minutes)
terraform apply

# Save outputs for later use
terraform output -json > infrastructure-outputs.json
```

### 4. Initialize Databases

```bash
# Initialize Trac database schema
./database/initialize_trac_db.sh

# Initialize learning schema
./database/initialize_learning_schema.sh

# Verify schemas
./scripts/validate-infrastructure.sh
```

### 5. Build and Deploy Applications

```bash
# Login to ECR
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  $(terraform output -raw trac_ecr_repository_url | cut -d'/' -f1)

# Build and push Trac container
cd docker/trac
docker build -t $(terraform output -raw trac_ecr_repository_url):latest .
docker push $(terraform output -raw trac_ecr_repository_url):latest

# Build and push LearnTrac API container
cd ../learntrac
docker build -t $(terraform output -raw learntrac_ecr_repository_url):latest .
docker push $(terraform output -raw learntrac_ecr_repository_url):latest

# Update ECS services
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service trac-service \
  --force-new-deployment

aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service learntrac-service \
  --force-new-deployment
```

### 6. Access Application

```bash
# Get application URL
echo "Application URL: $(terraform output -raw alb_url)"

# Test endpoints
curl $(terraform output -raw alb_url)/health
curl $(terraform output -raw alb_url)/trac/
curl $(terraform output -raw alb_url)/api/learntrac/health
```

## Architecture

For detailed architecture diagrams, see [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)

### High-Level Overview

```
Internet → ALB → ECS Tasks → Backend Services
                     ↓
              [Trac, LearnTrac API]
                     ↓
         [RDS, Redis, Cognito, External APIs]
```

## Components

### Core Services

| Component | Purpose | Access |
|-----------|---------|--------|
| RDS PostgreSQL | Primary database | Port 5432 |
| ElastiCache Redis | Session cache | Port 6379 |
| AWS Cognito | User authentication | HTTPS API |
| ECS Fargate | Container hosting | Via ALB |
| ALB | Load balancing | Port 80/443 |

### Resource Naming Convention

All resources follow the pattern: `{owner}-{project}-{environment}-{resource}`

Examples:
- RDS: `hutch-learntrac-dev-db`
- ALB: `hutch-learntrac-dev-alb`
- ECS Cluster: `hutch-learntrac-dev-cluster`

## Configuration

### Terraform Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region | us-east-2 |
| `environment` | Environment name | dev |
| `allowed_ip` | Your IP for DB access | Required |
| `db_instance_class` | RDS instance type | db.t3.micro |
| `db_allocated_storage` | Storage in GB | 20 |

### Environment-Specific Settings

```bash
# Development
cp environments/dev/terraform.tfvars terraform.tfvars

# Production
cp environments/prod/terraform.tfvars terraform.tfvars
```

## Operations

### Daily Operations

```bash
# Check infrastructure status
./scripts/validate-infrastructure.sh

# View ECS task logs
aws logs tail /ecs/hutch-learntrac-dev/trac --follow

# Monitor RDS connections
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=hutch-learntrac-dev-db \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### Backup and Recovery

```bash
# Create manual RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier hutch-learntrac-dev-db \
  --db-snapshot-identifier hutch-learntrac-dev-manual-$(date +%Y%m%d)

# List snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier hutch-learntrac-dev-db
```

### Scaling Operations

```bash
# Scale ECS service
aws ecs update-service \
  --cluster hutch-learntrac-dev-cluster \
  --service trac-service \
  --desired-count 3

# Resize RDS instance (requires downtime)
aws rds modify-db-instance \
  --db-instance-identifier hutch-learntrac-dev-db \
  --db-instance-class db.t3.small \
  --apply-immediately
```

## Troubleshooting

For detailed troubleshooting, see [INFRASTRUCTURE_REFERENCE.md](./INFRASTRUCTURE_REFERENCE.md#troubleshooting-guide)

### Common Issues

1. **Cannot connect to RDS**
   ```bash
   # Update security group with your current IP
   MY_IP=$(curl -s https://checkip.amazonaws.com)
   aws ec2 authorize-security-group-ingress \
     --group-id $(terraform output -raw security_group_id) \
     --protocol tcp \
     --port 5432 \
     --cidr $MY_IP/32
   ```

2. **ECS tasks not starting**
   ```bash
   # Check task status
   aws ecs list-tasks \
     --cluster hutch-learntrac-dev-cluster \
     --service-name trac-service
   
   # View task details
   aws ecs describe-tasks \
     --cluster hutch-learntrac-dev-cluster \
     --tasks [TASK_ARN]
   ```

3. **ALB health checks failing**
   ```bash
   # Check target health
   aws elbv2 describe-target-health \
     --target-group-arn [TARGET_GROUP_ARN]
   ```

## Security

For comprehensive security documentation, see [SECURITY_AND_NETWORK_GUIDE.md](./SECURITY_AND_NETWORK_GUIDE.md)

### Key Security Features

- ✅ Encryption at rest for RDS and secrets
- ✅ TLS/SSL for data in transit
- ✅ IAM roles for service authentication
- ✅ VPC isolation with security groups
- ✅ Secrets managed via AWS Secrets Manager
- ✅ JWT token-based authentication

### Security Best Practices

1. Regularly rotate secrets
2. Review security group rules monthly
3. Enable CloudTrail for audit logging
4. Use VPC endpoints for AWS service access
5. Implement least privilege IAM policies

## Additional Documentation

| Document | Description |
|----------|-------------|
| [INFRASTRUCTURE_REFERENCE.md](./INFRASTRUCTURE_REFERENCE.md) | Detailed resource reference and runbooks |
| [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md) | Visual architecture diagrams |
| [SECURITY_AND_NETWORK_GUIDE.md](./SECURITY_AND_NETWORK_GUIDE.md) | Security configuration and network flows |
| [database/README.md](./database/README.md) | Database setup and migration guides |
| [docker/README.md](./docker/README.md) | Container build instructions |

## Management Scripts

### Infrastructure Management

- `list-learntrac-resources.sh` - List all AWS resources
- `scripts/validate-infrastructure.sh` - Validate infrastructure health
- `scripts/apply-terraform-staged.sh` - Apply changes in stages
- `scripts/test_network_connectivity.sh` - Test network connectivity

### Database Scripts

- `database/initialize_trac_db.sh` - Initialize Trac schema
- `database/initialize_learning_schema.sh` - Initialize learning tables
- `scripts/test_redis_connection.py` - Test Redis connectivity

### Validation Scripts

- `validate-rds.sh` - Validate RDS configuration
- `scripts/validate-elasticache.sh` - Validate Redis setup
- `test-api-gateway.sh` - Test API Gateway endpoints

## Environment Variables

### Required for Terraform

```bash
export TF_VAR_allowed_ip=$(curl -s https://checkip.amazonaws.com)
export TF_VAR_environment=dev
export TF_VAR_aws_region=us-east-2
```

### Required for Applications

```bash
# Database
export DATABASE_URL=$(terraform output -raw rds_connection_string)

# Redis
export REDIS_URL=redis://$(terraform output -raw redis_endpoint):6379

# Cognito
export COGNITO_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export COGNITO_CLIENT_ID=$(terraform output -raw cognito_client_id)

# AWS Region
export AWS_REGION=us-east-2
```

## Maintenance

### Regular Tasks

- **Daily**: Check CloudWatch logs and metrics
- **Weekly**: Verify backups and test restoration
- **Monthly**: Review security groups and IAM policies
- **Quarterly**: Update dependencies and patch systems

### Monitoring Setup

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name LearnTracDev \
  --dashboard-body file://monitoring/dashboard.json
```

## Cost Optimization

### Current Monthly Costs (Estimated)

- RDS: ~$15 (db.t3.micro)
- ECS: ~$30 (2 services)
- ALB: ~$20
- ElastiCache: ~$15
- Data Transfer: ~$10
- **Total**: ~$90/month

### Cost Saving Tips

1. Use RDS instance scheduler for dev environments
2. Implement auto-scaling for ECS services
3. Use S3 lifecycle policies for logs
4. Consider Reserved Instances for production

## Support and Contribution

### Getting Help

- Check [Troubleshooting Guide](./INFRASTRUCTURE_REFERENCE.md#troubleshooting-guide)
- Review [AWS Service Documentation](https://docs.aws.amazon.com/)
- Contact: [Development Team Email]

### Contributing

1. Create feature branch
2. Make changes and test locally
3. Run `terraform plan` to verify
4. Submit pull request with detailed description

---

For detailed technical documentation, refer to the additional documentation files listed above.

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



