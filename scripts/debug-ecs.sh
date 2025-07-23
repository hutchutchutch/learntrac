#!/bin/bash
# Debug ECS deployment issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================="
echo "ECS Deployment Debugging"
echo "========================================="
echo ""

# Get cluster name
CLUSTER="hutch-learntrac-dev-cluster"

echo -e "${YELLOW}1. Checking Service Events (Last 10)${NC}"
echo "=== Trac Service Events ==="
aws ecs describe-services \
  --cluster $CLUSTER \
  --services hutch-learntrac-dev-trac \
  --query 'services[0].events[0:10].[createdAt,message]' \
  --output table

echo ""
echo "=== LearnTrac Service Events ==="
aws ecs describe-services \
  --cluster $CLUSTER \
  --services hutch-learntrac-dev-learntrac \
  --query 'services[0].events[0:10].[createdAt,message]' \
  --output table

echo ""
echo -e "${YELLOW}2. Checking Task Status${NC}"
# List all tasks (running and stopped)
TASKS=$(aws ecs list-tasks --cluster $CLUSTER --desired-status STOPPED --query 'taskArns' --output text)
if [ -n "$TASKS" ]; then
    echo "=== Recently Stopped Tasks ==="
    for task in $TASKS; do
        echo "Task: $(basename $task)"
        aws ecs describe-tasks \
          --cluster $CLUSTER \
          --tasks $task \
          --query 'tasks[0].[taskDefinitionArn,lastStatus,stoppedReason,stopCode]' \
          --output text
        
        # Get container stop reasons
        aws ecs describe-tasks \
          --cluster $CLUSTER \
          --tasks $task \
          --query 'tasks[0].containers[*].[name,exitCode,reason]' \
          --output table
        echo "---"
    done
else
    echo "No stopped tasks found"
fi

echo ""
echo -e "${YELLOW}3. Checking Task Definitions${NC}"
# Check if task definitions exist and have correct image
echo "=== Trac Task Definition ==="
aws ecs describe-task-definition \
  --task-definition hutch-learntrac-dev-trac \
  --query 'taskDefinition.containerDefinitions[0].[name,image,memory,cpu,essential]' \
  --output table

echo ""
echo "=== LearnTrac Task Definition ==="
aws ecs describe-task-definition \
  --task-definition hutch-learntrac-dev-learntrac \
  --query 'taskDefinition.containerDefinitions[0].[name,image,memory,cpu,essential]' \
  --output table

echo ""
echo -e "${YELLOW}4. Checking Subnet Configuration${NC}"
# Check if subnets have route to internet (for ECR pull)
aws ecs describe-services \
  --cluster $CLUSTER \
  --services hutch-learntrac-dev-trac \
  --query 'services[0].networkConfiguration.awsvpcConfiguration' \
  --output json

echo ""
echo -e "${YELLOW}5. Checking CloudWatch Logs for Errors${NC}"
# Try to get any logs
echo "=== Trac Logs ==="
aws logs tail /ecs/hutch-learntrac-dev-trac --since 1h 2>/dev/null || echo "No logs found"

echo ""
echo "=== LearnTrac Logs ==="
aws logs tail /ecs/hutch-learntrac-dev-learntrac --since 1h 2>/dev/null || echo "No logs found"

echo ""
echo -e "${YELLOW}6. Checking IAM Roles${NC}"
# Check execution role permissions
EXEC_ROLE=$(aws ecs describe-task-definition \
  --task-definition hutch-learntrac-dev-trac \
  --query 'taskDefinition.executionRoleArn' \
  --output text)
  
echo "Execution Role: $EXEC_ROLE"
aws iam list-attached-role-policies --role-name $(basename $EXEC_ROLE) --output table 2>/dev/null || echo "Could not check role policies"

echo ""
echo "========================================="
echo "Common Issues:"
echo "1. No internet access from private subnets (can't pull from ECR)"
echo "2. Insufficient memory/CPU allocation"
echo "3. IAM role missing ECR permissions"
echo "4. Security group blocking traffic"
echo "5. Task definition referencing wrong image"
echo "========================================="