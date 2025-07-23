# LearnTrac Infrastructure Testing - Step by Step Guide

This guide provides exact commands to run in your terminal to test the deployed infrastructure.

## Prerequisites

Before starting, ensure you have:
- AWS CLI configured with appropriate credentials
- Docker installed and running
- Terminal open in the project root directory

## Step 1: Initial Infrastructure Test

First, let's check what was successfully deployed:

```bash
# Navigate to the scripts directory
cd scripts

# Run the infrastructure test
./test-infrastructure.sh
```

**Expected output:**
- ✅ ALB is responding
- ✅ ECR repositories exist
- ✅ ECS cluster exists
- ⚠️  Services may show 0 running tasks (this is normal - no images deployed yet)

## Step 2: Get Infrastructure Information

Get the key infrastructure details:

```bash
# Navigate to infrastructure directory
cd ../learntrac-infrastructure

# Get ALB DNS name (save this - you'll use it a lot)
terraform output alb_dns_name

# Get ECR repository URLs
terraform output trac_ecr_repository_url
terraform output learntrac_ecr_repository_url

# Get other important values
terraform output ecs_cluster_name
terraform output redis_endpoint
```

**Save the ALB DNS name for later use:**
```bash
# Set as environment variable for easier testing
export ALB_DNS=$(terraform output -raw alb_dns_name)
echo "ALB URL: http://$ALB_DNS"
```

## Step 3: Test Basic ALB Connectivity

Test that the ALB is responding:

```bash
# Test default route
curl -v http://$ALB_DNS/

# You should see: "Welcome to TracLearn"
```

## Step 4: Deploy Test Containers

Now let's deploy minimal test containers to verify ECS works:

```bash
# Go back to project root
cd ..

# Deploy test containers
./scripts/deploy-test-containers.sh
```

**This script will:**
1. Build test containers locally
2. Login to ECR
3. Push containers to ECR
4. Force new ECS deployments

## Step 5: Monitor Deployment Progress

Watch the services come online (this takes 2-3 minutes):

```bash
# Get cluster name
CLUSTER=$(cd learntrac-infrastructure && terraform output -raw ecs_cluster_name)

# Watch service status (press Ctrl+C to exit)
watch -n 5 "aws ecs describe-services \
  --cluster $CLUSTER \
  --services hutch-learntrac-dev-trac hutch-learntrac-dev-learntrac \
  --query 'services[*].[serviceName,runningCount,desiredCount]' \
  --output table"
```

**Wait until you see:**
- runningCount equals desiredCount for both services
- This usually takes 2-3 minutes

## Step 6: Check ECS Task Status

If services aren't starting, check why:

```bash
# List all tasks
aws ecs list-tasks --cluster $CLUSTER

# Get task details (replace task-arn with actual ARN from above)
aws ecs describe-tasks \
  --cluster $CLUSTER \
  --tasks [task-arn] \
  --query 'tasks[0].stoppedReason'
```

## Step 7: Check CloudWatch Logs

View container logs to debug issues:

```bash
# Install awslogs if not already installed
pip install awslogs

# View Trac logs
awslogs get /ecs/hutch-learntrac-dev-trac ALL --start='5m ago'

# View LearnTrac logs
awslogs get /ecs/hutch-learntrac-dev-learntrac ALL --start='5m ago'
```

## Step 8: Test ALB Routing

Once services are running, test all routes:

```bash
# Run the ALB routing test script
./scripts/test-alb-routing.sh
```

Or test manually:

```bash
# Test Trac routes
curl http://$ALB_DNS/trac/login
curl http://$ALB_DNS/wiki/TestPage
curl http://$ALB_DNS/ticket/123

# Test LearnTrac API routes
curl http://$ALB_DNS/api/learntrac/health
curl http://$ALB_DNS/api/chat/test
curl http://$ALB_DNS/api/voice/test

# Pretty print JSON responses
curl -s http://$ALB_DNS/api/learntrac/health | python -m json.tool
```

## Step 9: Test Other Infrastructure Components

### Test Redis Connectivity

```bash
# Get Redis endpoint
REDIS=$(cd learntrac-infrastructure && terraform output -raw redis_endpoint)

# If you have redis-cli installed
redis-cli -h $REDIS ping

# Or use Docker
docker run --rm redis:alpine redis-cli -h $REDIS ping
```

### Check Secrets Manager

```bash
# List secrets
aws secretsmanager list-secrets \
  --query "SecretList[?contains(Name, 'learntrac')].[Name,Description]" \
  --output table

# Get Neo4j secret ARN
NEO4J_SECRET=$(cd learntrac-infrastructure && terraform output -raw neo4j_secret_arn)

# View secret details (without revealing values)
aws secretsmanager describe-secret --secret-id $NEO4J_SECRET
```

### Check Target Group Health

```bash
# Get target group health status
aws elbv2 describe-target-groups \
  --query "TargetGroups[?contains(TargetGroupName, 'learntrac')].[TargetGroupArn]" \
  --output text | while read arn; do
    echo "Target Group: $arn"
    aws elbv2 describe-target-health --target-group-arn $arn
    echo "---"
done
```

## Step 10: Comprehensive Test

Run all tests again to ensure everything is working:

```bash
# Run infrastructure test
./scripts/test-infrastructure.sh

# If all services are running, you should see:
# ✅ All infrastructure components
# ✅ Services with running tasks
# ✅ Healthy target groups
```

## Troubleshooting Commands

If something isn't working:

### Check ECS Service Events
```bash
aws ecs describe-services \
  --cluster $CLUSTER \
  --services hutch-learntrac-dev-trac \
  --query 'services[0].events[0:5]' \
  --output table
```

### Force New Deployment
```bash
aws ecs update-service \
  --cluster $CLUSTER \
  --service hutch-learntrac-dev-trac \
  --force-new-deployment
```

### Check Security Groups
```bash
# List all security groups
aws ec2 describe-security-groups \
  --filters "Name=tag:Project,Values=learntrac" \
  --query "SecurityGroups[*].[GroupId,GroupName,Description]" \
  --output table
```

### View ECS Task Definition
```bash
aws ecs describe-task-definition \
  --task-definition hutch-learntrac-dev-trac \
  --query 'taskDefinition.containerDefinitions[0]'
```

## Success Criteria

You know the infrastructure is working when:

1. ✅ `./scripts/test-infrastructure.sh` shows all green checkmarks
2. ✅ Both ECS services show running tasks (1/1)
3. ✅ ALB health checks are passing (target groups show healthy)
4. ✅ All test endpoints return expected responses
5. ✅ CloudWatch logs show containers starting successfully
6. ✅ Redis responds to ping
7. ✅ Secrets are accessible in Secrets Manager

## Next Steps

Once all tests pass:

1. Build and deploy the actual Trac and LearnTrac applications
2. Configure database connections and migrations
3. Set up monitoring and alarms
4. Configure auto-scaling thresholds
5. Add SSL certificate to ALB

## Quick Reference

```bash
# Key commands to remember
export ALB_DNS=$(cd learntrac-infrastructure && terraform output -raw alb_dns_name)
export CLUSTER=$(cd learntrac-infrastructure && terraform output -raw ecs_cluster_name)

# Test endpoints
curl http://$ALB_DNS/trac/login          # Trac health
curl http://$ALB_DNS/api/learntrac/health # LearnTrac health

# Check services
aws ecs describe-services --cluster $CLUSTER --services hutch-learntrac-dev-trac hutch-learntrac-dev-learntrac --query 'services[*].[serviceName,runningCount,desiredCount]' --output table

# View logs
awslogs get /ecs/hutch-learntrac-dev-trac ALL --start='5m ago'
```