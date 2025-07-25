# LearnTrac Infrastructure Reference Documentation

**Last Updated:** 2025-07-25  
**Environment:** Development (dev)  
**AWS Region:** us-east-2  
**AWS Account ID:** 971422717446

## Table of Contents

1. [AWS Resource Identifiers](#aws-resource-identifiers)
2. [Connection Endpoints](#connection-endpoints)
3. [Architecture Overview](#architecture-overview)
4. [Security Configuration](#security-configuration)
5. [Secrets Management](#secrets-management)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Disaster Recovery Runbook](#disaster-recovery-runbook)
8. [Setup Instructions](#setup-instructions)

## AWS Resource Identifiers

### Core Infrastructure
- **VPC:** Default VPC
- **Region:** us-east-2
- **Project Prefix:** hutch-learntrac-dev

### RDS PostgreSQL Database
- **Instance Identifier:** hutch-learntrac-dev-db
- **Endpoint:** hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com:5432
- **Engine:** PostgreSQL 15.8
- **Instance Class:** db.t3.micro
- **Storage:** 20GB gp3 (encrypted)
- **Database Name:** learntrac
- **Master Username:** learntrac_admin
- **Security Group:** sg-0456074f9f3016cdf

### AWS Cognito Authentication
- **User Pool ID:** us-east-2_IvxzMrWwg
- **User Pool Endpoint:** cognito-idp.us-east-2.amazonaws.com/us-east-2_IvxzMrWwg
- **Client ID:** 5adkv019v4rcu6o87ffg46ep02
- **Domain:** hutch-learntrac-dev-auth
- **Domain URL:** https://hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com
- **User Groups:** admins, instructors, students

### ElastiCache Redis
- **Cluster ID:** hutch-learntrac-dev-redis
- **Endpoint:** hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com:6379
- **Engine:** Redis 7
- **Node Type:** cache.t3.micro

### ECS Fargate
- **Cluster Name:** hutch-learntrac-dev-cluster
- **ECR Repositories:**
  - Trac: 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac
  - LearnTrac: 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac

### Application Load Balancer
- **DNS Name:** hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com
- **URL:** http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com

### AWS Secrets Manager
- **RDS Credentials:** hutch-learntrac-dev-db-credentials
- **Cognito Config:** hutch-learntrac-dev-cognito-config
- **Neo4j Credentials:** arn:aws:secretsmanager:us-east-2:971422717446:secret:hutch-learntrac-dev-neo4j-credentials-frXMQe
- **OpenAI API Key:** arn:aws:secretsmanager:us-east-2:971422717446:secret:hutch-learntrac-dev-openai-api-key-zThpKt

## Connection Endpoints

### Application URLs
- **Trac Legacy:** http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/trac/
- **LearnTrac API:** http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/api/learntrac/health
- **Health Check:** http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/health

### Database Connection
```bash
# Connection string format
postgres://learntrac_admin:[PASSWORD]@hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com:5432/learntrac

# Using psql
psql -h hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com -p 5432 -U learntrac_admin -d learntrac
```

### Redis Connection
```bash
# Redis CLI connection
redis-cli -h hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com -p 6379
```

## Architecture Overview

### Component Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet Gateway                          │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Load Balancer                     │
│              (hutch-learntrac-dev-alb.*.amazonaws.com)         │
└─────────────────────────────────────────────────────────────────┘
                    │                            │
                    ▼                            ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│      Trac Service (ECS)      │    │   LearnTrac API (ECS)       │
│        Python 2.7            │    │       Python 3.11           │
│         Port: 8000           │    │        Port: 8001           │
└─────────────────────────────┘    └─────────────────────────────┘
           │                                    │
           │                                    │
           ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Shared Services Layer                      │
├─────────────────────────┬─────────────────┬────────────────────┤
│    RDS PostgreSQL       │  ElastiCache    │    AWS Cognito     │
│   (Trac + Learning)     │     Redis       │   (User Auth)      │
└─────────────────────────┴─────────────────┴────────────────────┘
```

### Database Schema Organization

```sql
-- Public schema (Trac tables)
public.ticket
public.component
public.milestone
public.wiki
public.attachment
public.permission

-- Learning schema (Custom tables)
learning.paths
learning.concept_metadata
learning.prerequisites
learning.progress
```

## Security Configuration

### Security Groups

#### RDS Security Group (sg-0456074f9f3016cdf)
- **Inbound Rules:**
  - Port 5432 (PostgreSQL) from 162.206.172.65/32
  - Port 5432 from ECS task security group
- **Outbound Rules:**
  - All traffic allowed

#### ECS Task Security Group
- **Inbound Rules:**
  - Port 8000 from ALB security group (Trac)
  - Port 8001 from ALB security group (LearnTrac API)
- **Outbound Rules:**
  - Port 5432 to RDS security group
  - Port 6379 to ElastiCache security group
  - Port 443 to 0.0.0.0/0 (AWS services)

#### ElastiCache Security Group
- **Inbound Rules:**
  - Port 6379 from ECS task security group
- **Outbound Rules:**
  - All traffic allowed

#### ALB Security Group
- **Inbound Rules:**
  - Port 80 from 0.0.0.0/0
  - Port 443 from 0.0.0.0/0 (when HTTPS configured)
- **Outbound Rules:**
  - Port 8000 to ECS task security group
  - Port 8001 to ECS task security group

### IAM Roles

#### ECS Task Execution Role
- AmazonECSTaskExecutionRolePolicy
- Secrets Manager read access for specific secrets
- CloudWatch Logs write access

#### ECS Task Role
- RDS Data API access
- ElastiCache access
- Secrets Manager read for application secrets

## Secrets Management

### Retrieving Secrets

```bash
# Get RDS password
aws secretsmanager get-secret-value \
  --secret-id hutch-learntrac-dev-db-credentials \
  --query SecretString \
  --output text | jq -r '.password'

# Get Cognito configuration
aws secretsmanager get-secret-value \
  --secret-id hutch-learntrac-dev-cognito-config \
  --query SecretString \
  --output text | jq '.'

# Get Neo4j credentials
aws secretsmanager get-secret-value \
  --secret-id arn:aws:secretsmanager:us-east-2:971422717446:secret:hutch-learntrac-dev-neo4j-credentials-frXMQe \
  --query SecretString \
  --output text | jq '.'

# Get OpenAI API key
aws secretsmanager get-secret-value \
  --secret-id arn:aws:secretsmanager:us-east-2:971422717446:secret:hutch-learntrac-dev-openai-api-key-zThpKt \
  --query SecretString \
  --output text
```

### Updating Secrets

```bash
# Update Neo4j credentials
aws secretsmanager update-secret \
  --secret-id hutch-learntrac-dev-neo4j-credentials \
  --secret-string '{"uri":"neo4j+s://your-instance.databases.neo4j.io","username":"neo4j","password":"your-password"}'

# Update OpenAI API key
aws secretsmanager update-secret \
  --secret-id hutch-learntrac-dev-openai-api-key \
  --secret-string "sk-your-api-key-here"
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Cannot Connect to RDS Database

**Symptoms:** Connection timeout or refused
```bash
# Check security group rules
aws ec2 describe-security-groups --group-ids sg-0456074f9f3016cdf

# Verify your IP address
curl -s https://checkip.amazonaws.com

# Test connection
nc -zv hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com 5432
```

**Solutions:**
- Update security group to include your current IP
- Ensure you're using the correct port (5432)
- Verify RDS instance is not in maintenance window

#### 2. ECS Tasks Not Starting

**Symptoms:** Tasks stuck in PENDING or fail immediately
```bash
# Check task logs
aws ecs describe-tasks \
  --cluster hutch-learntrac-dev-cluster \
  --tasks [TASK_ARN] \
  --query 'tasks[0].stoppedReason'

# View CloudWatch logs
aws logs tail /ecs/hutch-learntrac-dev/trac --follow
```

**Solutions:**
- Check ECR image exists and is accessible
- Verify task role has necessary permissions
- Ensure secrets are correctly formatted
- Check memory/CPU allocation is sufficient

#### 3. ALB Health Checks Failing

**Symptoms:** Target unhealthy in ALB
```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn [TARGET_GROUP_ARN]

# Test health endpoint directly
curl http://[TASK_IP]:8000/health
```

**Solutions:**
- Verify health check path is correct
- Increase health check timeout/interval
- Check application startup time
- Review security group rules

#### 4. Redis Connection Issues

**Symptoms:** Cannot connect to ElastiCache
```bash
# Test from ECS task or bastion host
redis-cli -h hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com ping
```

**Solutions:**
- Ensure connecting from within VPC
- Check ElastiCache security group
- Verify Redis cluster is available

#### 5. Cognito Authentication Failures

**Symptoms:** JWT validation fails or users can't log in
```bash
# Get JWKS endpoint
curl https://cognito-idp.us-east-2.amazonaws.com/us-east-2_IvxzMrWwg/.well-known/jwks.json

# Test token endpoint
curl -X POST https://hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=5adkv019v4rcu6o87ffg46ep02&client_secret=[SECRET]"
```

**Solutions:**
- Verify callback URLs match exactly
- Check user pool app client settings
- Ensure correct OAuth flows are enabled
- Verify domain is properly configured

## Disaster Recovery Runbook

### Backup Procedures

#### 1. RDS Backup
```bash
# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier hutch-learntrac-dev-db \
  --db-snapshot-identifier hutch-learntrac-dev-db-manual-$(date +%Y%m%d-%H%M%S)

# List available snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier hutch-learntrac-dev-db \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]' \
  --output table
```

#### 2. Export Terraform State
```bash
# Backup current state
cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d-%H%M%S)

# Consider moving to S3 backend
terraform init -backend-config="bucket=learntrac-terraform-state" \
  -backend-config="key=dev/terraform.tfstate" \
  -backend-config="region=us-east-2"
```

#### 3. Export Secrets
```bash
# Backup all secrets (store securely!)
for secret in hutch-learntrac-dev-db-credentials \
              hutch-learntrac-dev-cognito-config \
              hutch-learntrac-dev-neo4j-credentials \
              hutch-learntrac-dev-openai-api-key; do
  aws secretsmanager get-secret-value --secret-id $secret \
    --query SecretString --output text > backup/$secret.json
done
```

### Recovery Procedures

#### 1. RDS Recovery from Snapshot
```bash
# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier hutch-learntrac-dev-db-restored \
  --db-snapshot-identifier [SNAPSHOT_ID]

# Update security group and parameter group
aws rds modify-db-instance \
  --db-instance-identifier hutch-learntrac-dev-db-restored \
  --vpc-security-group-ids sg-0456074f9f3016cdf
```

#### 2. Recreate Infrastructure
```bash
# From backup state
terraform init
terraform plan -out=recovery.plan
terraform apply recovery.plan

# Or from scratch
terraform init
terraform apply -var-file=terraform.tfvars
```

#### 3. Restore Application Data
```sql
-- Connect to restored database
psql -h [NEW_ENDPOINT] -U learntrac_admin -d learntrac

-- Verify Trac tables
SELECT COUNT(*) FROM ticket;
SELECT COUNT(*) FROM wiki;

-- Verify learning tables
SELECT COUNT(*) FROM learning.paths;
SELECT COUNT(*) FROM learning.concept_metadata;
```

### Rollback Procedures

#### Infrastructure Rollback
```bash
# Revert to previous Terraform state
cp terraform.tfstate.backup terraform.tfstate
terraform plan
terraform apply

# Or use state management
terraform state list
terraform state rm [RESOURCE_TO_REMOVE]
```

#### Database Schema Rollback
```sql
-- Use rollback script
psql -h hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com \
  -U learntrac_admin -d learntrac \
  -f database/06_learning_schema_rollback.sql
```

## Setup Instructions

### Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform 1.0+** installed
3. **PostgreSQL client** for database operations
4. **Docker** for building containers
5. **Redis CLI** for cache testing (optional)

### Initial Setup

#### 1. Clone and Initialize
```bash
cd learntrac-infrastructure
terraform init
```

#### 2. Configure Variables
```bash
# Copy example and update
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vi terraform.tfvars
```

#### 3. Plan and Apply
```bash
# Review changes
terraform plan

# Apply infrastructure
terraform apply
```

#### 4. Initialize Databases
```bash
# Trac schema
./database/initialize_trac_db.sh

# Learning schema
./database/initialize_learning_schema.sh
```

#### 5. Build and Deploy Containers
```bash
# Build Trac container
docker build -t hutch-learntrac-dev-trac ./docker/trac

# Build LearnTrac API container
docker build -t hutch-learntrac-dev-learntrac ./docker/learntrac

# Push to ECR
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin 971422717446.dkr.ecr.us-east-2.amazonaws.com

docker tag hutch-learntrac-dev-trac:latest \
  971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest

docker push 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest
```

#### 6. Update ECS Services
```bash
# Force new deployment
aws ecs update-service \
  --cluster hutch-learntrac-dev-cluster \
  --service trac-service \
  --force-new-deployment
```

### Environment Configuration

#### Local Development
```bash
# .env file for local testing
DATABASE_URL=postgres://learntrac_admin:[PASSWORD]@hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com:5432/learntrac
REDIS_URL=redis://hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com:6379
COGNITO_POOL_ID=us-east-2_IvxzMrWwg
COGNITO_CLIENT_ID=5adkv019v4rcu6o87ffg46ep02
AWS_REGION=us-east-2
```

#### ECS Task Environment
Automatically populated from:
- Secrets Manager for sensitive values
- Task definition for non-sensitive values

### Monitoring and Maintenance

#### CloudWatch Dashboards
Create custom dashboard with:
- RDS CPU and connection metrics
- ECS task count and CPU/memory utilization
- ALB request count and target health
- ElastiCache cache hits/misses

#### Alarms to Configure
- RDS CPU > 80%
- RDS connections > 80% of max
- ECS service unhealthy tasks > 0
- ALB unhealthy targets > 0
- ElastiCache evictions > threshold

#### Regular Maintenance
- Weekly RDS snapshot verification
- Monthly security group audit
- Quarterly secret rotation
- Annual disaster recovery drill

## Additional Resources

- [AWS RDS PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [ECS Fargate Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/fargate.html)
- [Cognito Developer Guide](https://docs.aws.amazon.com/cognito/latest/developerguide/)
- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

For questions or issues, contact the development team or refer to the project's issue tracker.