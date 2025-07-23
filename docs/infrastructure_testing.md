# LearnTrac Infrastructure Testing Guide

## Overview
This guide provides step-by-step instructions to test and verify the deployed LearnTrac infrastructure before deploying application code.

## Infrastructure Components Status

### ✅ Successfully Deployed
- ECS Cluster
- ECR Repositories (Trac & LearnTrac)
- Application Load Balancer (ALB)
- Target Groups with health checks
- Security Groups
- Redis (ElastiCache)
- RDS PostgreSQL (existing)
- AWS Secrets Manager (Neo4j & OpenAI credentials)
- Auto-scaling policies
- CloudWatch Log Groups

### 🔄 Pending
- Docker images in ECR
- ECS services running with actual containers
- Actual application testing

## Testing Steps

### 1. Gather Infrastructure Information

First, let's get all the important outputs from Terraform:

```bash
cd learntrac-infrastructure

# Get all outputs
terraform output

# Get specific outputs
terraform output alb_dns_name
terraform output trac_ecr_repository_url
terraform output learntrac_ecr_repository_url
terraform output redis_endpoint
terraform output ecs_cluster_name
```

### 2. Test ALB Connectivity

The ALB should be accessible even without services running:

```bash
# Get ALB DNS name
ALB_DNS=$(terraform output -raw alb_dns_name)

# Test ALB default response
curl -v http://$ALB_DNS/

# Expected: "Welcome to TracLearn" (note: this still has old naming)
```

### 3. Create Test Docker Images

Since the ECS services are expecting Docker images, let's create minimal test images:

#### Create test-containers directory:
```bash
mkdir -p test-containers/trac
mkdir -p test-containers/learntrac
```

#### Minimal Trac Test Container:
```dockerfile
# test-containers/trac/Dockerfile
FROM python:2.7-slim
RUN pip install flask
WORKDIR /app
COPY app.py .
EXPOSE 8000
CMD ["python", "app.py"]
```

```python
# test-containers/trac/app.py
from flask import Flask
import os

app = Flask(__name__)

@app.route('/trac/login')
def health():
    return 'Trac Test Container - Health Check OK', 200

@app.route('/')
def root():
    return 'Trac Test Container - Root', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

#### Minimal LearnTrac Test Container:
```dockerfile
# test-containers/learntrac/Dockerfile
FROM python:3.11-slim
RUN pip install fastapi uvicorn
WORKDIR /app
COPY main.py .
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

```python
# test-containers/learntrac/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/learntrac/health")
def health():
    return {"status": "healthy", "service": "learntrac-test"}

@app.get("/")
def root():
    return {"message": "LearnTrac Test Container"}
```

### 4. Build and Push Test Images to ECR

```bash
# Get ECR login token
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $(terraform output -raw trac_ecr_repository_url | cut -d'/' -f1)

# Build and push Trac test image
cd test-containers/trac
TRAC_REPO=$(cd ../../learntrac-infrastructure && terraform output -raw trac_ecr_repository_url)
docker build -t $TRAC_REPO:test .
docker push $TRAC_REPO:test

# Build and push LearnTrac test image
cd ../learntrac
LEARNTRAC_REPO=$(cd ../../learntrac-infrastructure && terraform output -raw learntrac_ecr_repository_url)
docker build -t $LEARNTRAC_REPO:test .
docker push $LEARNTRAC_REPO:test
```

### 5. Update ECS Services to Use Test Images

The services are already created but need to be updated with the image URIs. This happens automatically when the images are pushed with the correct tags.

### 6. Monitor ECS Service Deployment

```bash
# Watch service status
aws ecs describe-services \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services hutch-learntrac-dev-trac hutch-learntrac-dev-learntrac \
  --query 'services[*].[serviceName,desiredCount,runningCount,pendingCount]' \
  --output table

# Check task status
aws ecs list-tasks \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --query 'taskArns' \
  --output text | xargs -I {} aws ecs describe-tasks \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --tasks {} \
  --query 'tasks[*].[taskDefinitionArn,lastStatus,stoppedReason]'
```

### 7. Test ALB Path Routing

Once services are running, test each path:

```bash
ALB_DNS=$(terraform output -raw alb_dns_name)

# Test Trac paths
curl -v http://$ALB_DNS/trac/login
curl -v http://$ALB_DNS/wiki/test
curl -v http://$ALB_DNS/ticket/123

# Test LearnTrac API paths
curl -v http://$ALB_DNS/api/learntrac/health
curl -v http://$ALB_DNS/api/chat/test
curl -v http://$ALB_DNS/api/voice/test

# Test static assets routing
curl -v http://$ALB_DNS/static/test.css
curl -v http://$ALB_DNS/chrome/test.js
```

### 8. Test Redis Connectivity

```bash
# Get Redis endpoint
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)

# Test with redis-cli (requires redis-tools)
redis-cli -h $REDIS_ENDPOINT -p 6379 ping
# Expected: PONG
```

### 9. Verify RDS Connectivity

```bash
# Get RDS endpoint
RDS_ENDPOINT=$(terraform output -raw rds_endpoint | cut -d':' -f1)

# Test with psql (requires postgresql-client)
psql -h $RDS_ENDPOINT -U learntrac_user -d learntrac -c "SELECT version();"
```

### 10. Check Secrets Manager

```bash
# Verify secrets exist
aws secretsmanager list-secrets --query "SecretList[?contains(Name, 'learntrac')].[Name,ARN]" --output table

# Get Neo4j secret (without revealing password)
aws secretsmanager describe-secret --secret-id $(terraform output -raw neo4j_secret_arn)
```

### 11. Monitor CloudWatch Logs

```bash
# List log streams for Trac
aws logs describe-log-streams \
  --log-group-name /ecs/hutch-learntrac-dev-trac \
  --order-by LastEventTime \
  --descending

# List log streams for LearnTrac
aws logs describe-log-streams \
  --log-group-name /ecs/hutch-learntrac-dev-learntrac \
  --order-by LastEventTime \
  --descending

# Tail logs (requires awslogs)
awslogs get /ecs/hutch-learntrac-dev-trac ALL --watch
awslogs get /ecs/hutch-learntrac-dev-learntrac ALL --watch
```

## Expected Results

### ✅ Success Indicators
- ALB responds with default message
- ECS services show `runningCount` equal to `desiredCount`
- Health check endpoints return 200 OK
- Path routing correctly forwards to appropriate service
- Redis responds with PONG
- CloudWatch logs show application startup messages

### ❌ Common Issues and Solutions

1. **ECS Tasks Failing to Start**
   - Check CloudWatch logs for error messages
   - Verify ECR images exist
   - Check task definition has correct image URI
   - Verify security groups allow traffic

2. **Health Checks Failing**
   - Ensure health check paths match application routes
   - Verify security groups allow ALB to reach ECS tasks
   - Check application is listening on correct port

3. **ALB Not Routing Traffic**
   - Verify listener rules are created
   - Check target group health
   - Ensure services are registered with target groups

## Next Steps

After all tests pass:
1. Deploy actual Trac and LearnTrac Docker images
2. Configure database migrations
3. Set up monitoring dashboards
4. Configure auto-scaling thresholds
5. Add CloudWatch alarms

## Troubleshooting Commands

```bash
# Check ECS service events
aws ecs describe-services \
  --cluster hutch-learntrac-dev-cluster \
  --services hutch-learntrac-dev-trac \
  --query 'services[0].events[0:5]'

# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names "trac-*" \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

# Force new deployment
aws ecs update-service \
  --cluster hutch-learntrac-dev-cluster \
  --service hutch-learntrac-dev-trac \
  --force-new-deployment
```