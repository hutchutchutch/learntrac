# LearnTrac Infrastructure Testing - Step by Step Guide

This guide provides exact commands to run from the **project root directory** to test the deployed infrastructure. Each step builds on the previous one, with a comprehensive test at the end.

## Prerequisites

Before starting, ensure you have:
- AWS CLI configured with appropriate credentials
- Docker installed and running
- Terminal open in the project root directory (`learntrac/`)

## Initial Setup - Export Environment Variables

Run these commands first to set up variables used throughout testing:

```bash
# From project root, export key variables
export ALB_DNS=$(cd learntrac-infrastructure && terraform output -raw alb_dns_name && cd ..)
export CLUSTER=$(cd learntrac-infrastructure && terraform output -raw ecs_cluster_name && cd ..)
export REDIS_ENDPOINT=$(cd learntrac-infrastructure && terraform output -raw redis_endpoint && cd ..)
export TRAC_ECR=$(cd learntrac-infrastructure && terraform output -raw trac_ecr_repository_url && cd ..)
export LEARNTRAC_ECR=$(cd learntrac-infrastructure && terraform output -raw learntrac_ecr_repository_url && cd ..)

# Verify variables are set
echo "ALB: $ALB_DNS"
echo "Cluster: $CLUSTER"
echo "Redis: $REDIS_ENDPOINT"
```

## Step 1: Initial Infrastructure Test

Test what was successfully deployed:

```bash
# From project root
./scripts/test-infrastructure.sh
```

**Expected output:**
- ✅ ALB is responding
- ✅ ECR repositories exist
- ✅ ECS cluster exists
- ⚠️  Services may show 0 running tasks (normal if no images deployed)

**Success Criteria:** ALB responds with HTTP 200

## Step 2: Test Basic ALB Connectivity

Verify the load balancer is accessible:

```bash
# Test default route
curl -v http://$ALB_DNS/

# Expected: "Welcome to TracLearn" with HTTP 200
```

**Success Criteria:** Receives HTTP 200 response

## Step 3: Fix ECS Networking (If Needed)

If services show continuous restarts in Step 1:

```bash
# Run networking diagnostic and fix script
./scripts/fix-ecs-networking.sh

# Follow prompts to enable public IP assignment if needed
```

**Success Criteria:** Script identifies networking issues and offers fix

## Step 4: Deploy Test Containers

Deploy minimal containers to verify ECS functionality:

```bash
# From project root - deploy test containers
./scripts/deploy-test-containers.sh
```

**Success Criteria:** 
- ✅ Images built successfully
- ✅ Images pushed to ECR
- ✅ Service updates initiated

## Step 5: Monitor Deployment Progress

Wait for services to stabilize:

```bash
# Monitor service status (Ctrl+C to exit)
watch -n 5 'aws ecs describe-services \
  --cluster '"$CLUSTER"' \
  --services hutch-learntrac-dev-trac hutch-learntrac-dev-learntrac \
  --query "services[*].[serviceName,runningCount,desiredCount]" \
  --output table'
```

**Success Criteria:** Both services show runningCount = desiredCount = 1

## Step 6: Verify Container Health

Check if containers are running properly:

```bash
# Check running tasks
aws ecs list-tasks --cluster $CLUSTER --desired-status RUNNING --output table

# If no running tasks, check stopped tasks for errors
aws ecs list-tasks --cluster $CLUSTER --desired-status STOPPED --query 'taskArns[0]' --output text | \
  xargs -I {} aws ecs describe-tasks --cluster $CLUSTER --tasks {} \
  --query 'tasks[0].[stoppedReason,containers[0].reason]' --output text
```

**Success Criteria:** At least 2 running tasks (one per service)

## Step 7: Test ALB Routing

Verify all routing rules work correctly:

```bash
# From project root - run comprehensive routing test
./scripts/test-alb-routing.sh
```

Or test individual endpoints:

```bash
# Test Trac endpoints
curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/trac/login
curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/wiki/test
curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/ticket/123

# Test LearnTrac API endpoints
curl -s http://$ALB_DNS/api/learntrac/health | python -m json.tool
curl -s http://$ALB_DNS/api/chat/test | python -m json.tool
curl -s http://$ALB_DNS/api/voice/test | python -m json.tool
```

**Success Criteria:** All endpoints return HTTP 200

## Step 8: Test Infrastructure Components

### Redis Connectivity
```bash
# Test Redis with Docker
docker run --rm redis:alpine redis-cli -h $REDIS_ENDPOINT ping
```
**Success Criteria:** Returns "PONG"

### Secrets Manager
```bash
# List LearnTrac secrets
aws secretsmanager list-secrets \
  --query "SecretList[?contains(Name, 'learntrac')].[Name,ARN]" \
  --output table

# Verify Neo4j secret exists
aws secretsmanager describe-secret \
  --secret-id $(cd learntrac-infrastructure && terraform output -raw neo4j_secret_arn) \
  --query '[Name,ARN,CreatedDate]' --output table
```
**Success Criteria:** Secrets are listed and accessible

### Target Group Health
```bash
# Check all target groups
aws elbv2 describe-target-groups \
  --query "TargetGroups[?contains(TargetGroupName, 'learntrac')].[TargetGroupName,HealthCheckPath,TargetType]" \
  --output table

# Check target health
aws elbv2 describe-target-groups \
  --query "TargetGroups[?contains(TargetGroupName, 'learntrac')].TargetGroupArn" \
  --output text | while read arn; do
    echo "=== Target Group: $(basename $arn) ==="
    aws elbv2 describe-target-health --target-group-arn $arn \
      --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State]' \
      --output table
done
```
**Success Criteria:** All targets show "healthy" state

## Step 9: Verify Logs

Check CloudWatch logs for any errors:

```bash
# Check if logs exist
aws logs describe-log-streams \
  --log-group-name /ecs/hutch-learntrac-dev-trac \
  --order-by LastEventTime --descending --max-items 1 \
  --query 'logStreams[0].lastEventTime' --output text

aws logs describe-log-streams \
  --log-group-name /ecs/hutch-learntrac-dev-learntrac \
  --order-by LastEventTime --descending --max-items 1 \
  --query 'logStreams[0].lastEventTime' --output text

# View recent logs (requires awslogs)
pip install awslogs >/dev/null 2>&1
awslogs get /ecs/hutch-learntrac-dev-trac ALL --start='10m ago' | tail -20
awslogs get /ecs/hutch-learntrac-dev-learntrac ALL --start='10m ago' | tail -20
```

**Success Criteria:** Logs show containers starting without errors

## Step 10: Comprehensive Infrastructure Test

Run the complete test suite:

```bash
# From project root - final comprehensive test
./scripts/test-infrastructure.sh

# All items should show ✅
```

**Success Criteria:** All components show green checkmarks

## Composite Test Script

Create and run a single script that validates everything:

```bash
# Create comprehensive test script
cat > ./scripts/test-all.sh << 'EOF'
#!/bin/bash
# Comprehensive infrastructure test

echo "==================================="
echo "LearnTrac Complete Infrastructure Test"
echo "==================================="

# Setup
export ALB_DNS=$(cd learntrac-infrastructure && terraform output -raw alb_dns_name && cd ..)
export CLUSTER=$(cd learntrac-infrastructure && terraform output -raw ecs_cluster_name && cd ..)
PASS=0
FAIL=0

# Function to test and report
test_component() {
    echo -n "Testing $1... "
    if eval "$2" >/dev/null 2>&1; then
        echo "✅ PASS"
        ((PASS++))
    else
        echo "❌ FAIL"
        ((FAIL++))
    fi
}

# Run all tests
test_component "ALB Connectivity" "curl -s -f http://$ALB_DNS/"
test_component "Trac Health Check" "curl -s -f http://$ALB_DNS/trac/login"
test_component "LearnTrac Health Check" "curl -s -f http://$ALB_DNS/api/learntrac/health"
test_component "ECS Cluster" "aws ecs describe-clusters --clusters $CLUSTER"
test_component "Trac Service Running" "aws ecs describe-services --cluster $CLUSTER --services hutch-learntrac-dev-trac --query 'services[0].runningCount' --output text | grep -E '^[1-9]'"
test_component "LearnTrac Service Running" "aws ecs describe-services --cluster $CLUSTER --services hutch-learntrac-dev-learntrac --query 'services[0].runningCount' --output text | grep -E '^[1-9]'"
test_component "Redis Connectivity" "docker run --rm redis:alpine redis-cli -h $(cd learntrac-infrastructure && terraform output -raw redis_endpoint) ping"
test_component "ECR Trac Repository" "aws ecr describe-repositories --repository-names hutch-learntrac-dev-trac"
test_component "ECR LearnTrac Repository" "aws ecr describe-repositories --repository-names hutch-learntrac-dev-learntrac"
test_component "Secrets Manager" "aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `learntrac`)]' --output text"

echo ""
echo "==================================="
echo "Test Summary: $PASS passed, $FAIL failed"
echo "==================================="

if [ $FAIL -eq 0 ]; then
    echo "🎉 All infrastructure tests passed!"
    exit 0
else
    echo "⚠️  Some tests failed. Check the output above."
    exit 1
fi
EOF

chmod +x ./scripts/test-all.sh

# Run comprehensive test
./scripts/test-all.sh
```

## Success Criteria Summary

Infrastructure is fully operational when:

1. ✅ ALB responds on all configured paths
2. ✅ Both ECS services have running tasks
3. ✅ Target groups report healthy targets
4. ✅ Redis connectivity confirmed
5. ✅ ECR repositories accessible
6. ✅ Secrets Manager configured
7. ✅ CloudWatch logs show no errors
8. ✅ All routing rules work correctly

## Troubleshooting Quick Commands

```bash
# Debug ECS issues
./scripts/debug-ecs.sh

# Fix networking issues
./scripts/fix-ecs-networking.sh

# Force service restart
aws ecs update-service --cluster $CLUSTER --service hutch-learntrac-dev-trac --force-new-deployment
aws ecs update-service --cluster $CLUSTER --service hutch-learntrac-dev-learntrac --force-new-deployment

# Check recent events
aws ecs describe-services --cluster $CLUSTER --services hutch-learntrac-dev-trac --query 'services[0].events[0:5]' --output table
```

## Next Steps

Once all tests pass:
1. Deploy actual Trac and LearnTrac applications
2. Configure database migrations
3. Set up monitoring dashboards
4. Configure auto-scaling policies
5. Add SSL certificates