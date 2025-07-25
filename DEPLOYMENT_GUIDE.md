# LearnTrac Deployment Guide

This guide covers all deployment options for LearnTrac, from local development to production AWS deployment.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Compose Production](#docker-compose-production)
3. [AWS ECS Deployment](#aws-ecs-deployment)
4. [Monitoring and Maintenance](#monitoring-and-maintenance)
5. [Troubleshooting](#troubleshooting)

## Local Development

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/learntrac.git
cd learntrac

# Copy environment template
cp .env.docker.example .env
# Edit .env with your configuration

# Start development environment
make dev
```

### Development URLs

- Trac: http://localhost:8080
- Learning API: http://localhost:8001
- Neo4j Browser: http://localhost:7474
- Redis: localhost:6379

### Development Commands

```bash
# View logs
make logs

# Access container shells
make shell-trac
make shell-api

# Run tests
make test

# Stop services
make down
```

## Docker Compose Production

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 1.29+
- Production server with at least 4GB RAM

### Setup

1. **Prepare Environment**

```bash
# Copy and configure environment
cp .env.docker.example .env
vim .env  # Add production values
```

2. **Start Production Services**

```bash
# Pull latest images
docker-compose pull

# Start services
make prod
```

3. **Verify Deployment**

```bash
# Check health
make health

# View logs
make logs
```

### SSL/TLS Configuration

For production, use a reverse proxy like Nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name learntrac.yourdomain.com;

    ssl_certificate /etc/ssl/certs/learntrac.crt;
    ssl_certificate_key /etc/ssl/private/learntrac.key;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## AWS ECS Deployment

### Prerequisites

- AWS CLI configured
- Existing VPC and subnets
- RDS PostgreSQL instance
- ElastiCache Redis cluster
- Neo4j instance (Aura or self-hosted)

### Step 1: Set Up Infrastructure

```bash
# Export required variables
export VPC_ID=vpc-xxxxxxxxx
export SUBNET_IDS=subnet-xxxxx,subnet-yyyyy
export AWS_REGION=us-east-1

# Run infrastructure setup
chmod +x deploy/setup-ecs-infrastructure.sh
./deploy/setup-ecs-infrastructure.sh
```

### Step 2: Configure Environment

Update `.env` with AWS resources:

```bash
# RDS Configuration
RDS_ENDPOINT=learntrac.xxxxx.us-east-1.rds.amazonaws.com:5432

# ElastiCache Configuration
ELASTICACHE_ENDPOINT=learntrac.xxxxx.cache.amazonaws.com

# Neo4j Configuration
NEO4J_URI=bolt://your-neo4j-instance:7687

# Cognito Configuration
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 3: Build and Push Images

```bash
# Build and push to ECR
chmod +x deploy/push-to-ecr.sh
./deploy/push-to-ecr.sh
```

### Step 4: Deploy to ECS

```bash
# Deploy services
chmod +x deploy/deploy-ecs.sh
./deploy/deploy-ecs.sh
```

### Step 5: Configure Load Balancer

1. Create Application Load Balancer in AWS Console
2. Create target groups for:
   - Trac service (port 8080)
   - API service (port 8001)
3. Configure listener rules:
   - `/api/*` → API target group
   - `/*` → Trac target group

### Auto-Scaling Configuration

```bash
# Create scaling policies
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --resource-id service/learntrac-cluster/learntrac-api-service \
    --scalable-dimension ecs:service:DesiredCount \
    --min-capacity 2 \
    --max-capacity 10

aws application-autoscaling put-scaling-policy \
    --policy-name learntrac-api-cpu-scaling \
    --service-namespace ecs \
    --resource-id service/learntrac-cluster/learntrac-api-service \
    --scalable-dimension ecs:service:DesiredCount \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration \
        targetValue=70.0,predefinedMetricType=ECSServiceAverageCPUUtilization
```

## Monitoring and Maintenance

### CloudWatch Dashboards

Create dashboards for:

- ECS service metrics (CPU, memory, task count)
- Application logs (errors, warnings)
- API response times
- Database connections

### Log Analysis

```bash
# View recent logs
aws logs tail /ecs/learntrac-trac --follow
aws logs tail /ecs/learntrac-api --follow

# Search for errors
aws logs filter-log-events \
    --log-group-name /ecs/learntrac-api \
    --filter-pattern "ERROR"
```

### Backup Procedures

#### Database Backup

```bash
# Manual backup
aws rds create-db-snapshot \
    --db-instance-identifier learntrac \
    --db-snapshot-identifier learntrac-manual-$(date +%Y%m%d%H%M%S)

# Automated backups (configure in RDS)
# Set backup retention period: 7-35 days
```

#### Neo4j Backup

```bash
# For Neo4j Aura
# Use the Aura console for automated backups

# For self-hosted
docker exec neo4j neo4j-admin dump \
    --to=/backup/neo4j-$(date +%Y%m%d).dump
```

### Updates and Maintenance

#### Rolling Updates

```bash
# Update task definition and deploy
./deploy/deploy-ecs.sh

# Monitor deployment
aws ecs describe-services \
    --cluster learntrac-cluster \
    --services learntrac-trac-service learntrac-api-service
```

#### Database Migrations

```bash
# Connect to API container
aws ecs execute-command \
    --cluster learntrac-cluster \
    --task <task-id> \
    --container learning-service \
    --interactive \
    --command "/bin/bash"

# Run migrations
alembic upgrade head
```

## Troubleshooting

### Common Issues

#### 1. Container Health Check Failures

**Symptoms**: Tasks stopping and starting repeatedly

**Solution**:
```bash
# Check logs
aws logs tail /ecs/learntrac-trac --since 1h

# Verify database connectivity
# Check security groups allow database access
```

#### 2. Memory Issues

**Symptoms**: Tasks killed due to memory limits

**Solution**:
```bash
# Increase task memory in task definition
# Monitor memory usage in CloudWatch
```

#### 3. Database Connection Pool Exhaustion

**Symptoms**: "too many connections" errors

**Solution**:
- Increase RDS max_connections parameter
- Adjust application pool settings
- Implement connection pooling

#### 4. API Gateway Timeouts

**Symptoms**: 504 Gateway Timeout errors

**Solution**:
- Increase API Gateway timeout (max 29 seconds)
- Optimize slow queries
- Implement caching

### Debug Commands

```bash
# ECS task details
aws ecs describe-tasks \
    --cluster learntrac-cluster \
    --tasks <task-arn>

# Container logs
docker logs <container-id>

# Database connectivity test
docker-compose exec trac psql -h $RDS_ENDPOINT -U $DB_USER -d $DB_NAME

# API health check
curl http://localhost:8001/health

# Trac status
curl http://localhost:8080/login
```

### Performance Tuning

#### Trac Optimization

```ini
# In trac.ini
[trac]
database_pool_size = 20
database_pool_max_overflow = 5
```

#### API Optimization

```python
# In src/config.py
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10
REDIS_POOL_SIZE = 50
```

#### Docker Resource Limits

```yaml
# In docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

## Security Best Practices

1. **Secrets Management**
   - Use AWS Secrets Manager for sensitive data
   - Rotate credentials regularly
   - Never commit secrets to Git

2. **Network Security**
   - Use VPC endpoints for AWS services
   - Implement WAF rules on ALB
   - Enable VPC Flow Logs

3. **Container Security**
   - Scan images for vulnerabilities
   - Use read-only root filesystems
   - Run containers as non-root user

4. **Monitoring**
   - Enable AWS GuardDuty
   - Set up CloudWatch alarms
   - Implement log aggregation

## Support

For issues or questions:

1. Check logs and error messages
2. Review this guide and DOCKER_DEPLOYMENT.md
3. Search GitHub issues
4. Contact the development team

Remember to always test changes in a staging environment before deploying to production!