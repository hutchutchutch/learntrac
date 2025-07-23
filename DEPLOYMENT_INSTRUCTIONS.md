# LearnTrac Docker Deployment Instructions

## Prerequisites
- AWS CLI installed and configured with appropriate credentials
- Docker installed and running
- Access to AWS account ID: 971422717446
- Region: us-east-2

## Step 1: ECR Login
```bash
# Login to ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 971422717446.dkr.ecr.us-east-2.amazonaws.com
```

## Step 2: Tag and Push Images

### Push Trac Image
```bash
# Tag the Trac image
docker tag hutch-learntrac-dev-trac:latest 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest

# Push to ECR
docker push 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest
```

### Push LearnTrac API Image
```bash
# Tag the LearnTrac API image
docker tag hutch-learntrac-dev-learntrac:latest 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac:latest

# Push to ECR
docker push 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac:latest
```

## Step 3: Update ECS Services

### Update Trac Service
```bash
aws ecs update-service \
    --cluster hutch-learntrac-dev-cluster \
    --service hutch-learntrac-dev-trac \
    --force-new-deployment \
    --region us-east-2
```

### Update LearnTrac Service
```bash
aws ecs update-service \
    --cluster hutch-learntrac-dev-cluster \
    --service hutch-learntrac-dev-learntrac \
    --force-new-deployment \
    --region us-east-2
```

## Step 4: Monitor Deployment

### Check Service Status
```bash
# Check both services status
aws ecs describe-services \
    --cluster hutch-learntrac-dev-cluster \
    --services hutch-learntrac-dev-trac hutch-learntrac-dev-learntrac \
    --region us-east-2 \
    --query 'services[*].[serviceName,runningCount,desiredCount,deployments[0].status]' \
    --output table
```

### Monitor CloudWatch Logs
```bash
# Monitor Trac logs
aws logs tail /ecs/hutch-learntrac-dev-trac --follow --region us-east-2

# In another terminal, monitor LearnTrac logs
aws logs tail /ecs/hutch-learntrac-dev-learntrac --follow --region us-east-2
```

## Step 5: Test Endpoints

### Test ALB Health
```bash
# Base ALB endpoint
curl -v http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/

# Trac endpoints
curl http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/trac/
curl http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/ticket/

# LearnTrac API endpoints
curl http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/health
curl http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/api/learntrac/health
```

## Troubleshooting

### If ECS Tasks Won't Start:
1. Check CloudWatch logs for startup errors
2. Verify ECR images were pushed successfully:
   ```bash
   aws ecr describe-images --repository-name hutch-learntrac-dev-trac --region us-east-2
   aws ecr describe-images --repository-name hutch-learntrac-dev-learntrac --region us-east-2
   ```

### If Health Checks Fail:
1. Ensure security groups allow ALB to reach ECS tasks on ports 8000 and 8001
2. Check task definition memory/CPU settings
3. Verify environment variables in ECS task definitions

### Common Issues:
- **503 Service Unavailable**: Tasks not running or health checks failing
- **Connection Refused**: Security group or network ACL blocking traffic
- **Task Stops Immediately**: Check CloudWatch logs for startup errors

## Next Steps After Successful Deployment:
1. Configure proper environment variables in ECS task definitions
2. Set up database connections when RDS is ready
3. Configure Redis connection strings
4. Add authentication and authorization
5. Set up monitoring and alerts

## Rollback Procedure:
If deployment fails:
```bash
# List previous task definition revisions
aws ecs list-task-definitions --family-prefix hutch-learntrac-dev --region us-east-2

# Update service to use previous task definition
aws ecs update-service \
    --cluster hutch-learntrac-dev-cluster \
    --service SERVICE_NAME \
    --task-definition PREVIOUS_TASK_DEF:REVISION \
    --region us-east-2
```