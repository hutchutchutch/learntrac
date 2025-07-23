#!/bin/bash
# LearnTrac Infrastructure Test Script
# This script performs basic health checks on the deployed infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo "========================================="
echo "LearnTrac Infrastructure Testing"
echo "========================================="
echo ""

# Change to infrastructure directory
cd "$(dirname "$0")/../learntrac-infrastructure"

print_info "Gathering infrastructure information..."

# Get Terraform outputs
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")
TRAC_ECR=$(terraform output -raw trac_ecr_repository_url 2>/dev/null || echo "")
LEARNTRAC_ECR=$(terraform output -raw learntrac_ecr_repository_url 2>/dev/null || echo "")
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint 2>/dev/null || echo "")
ECS_CLUSTER=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")

# Test 1: ALB Connectivity
print_info "Testing ALB connectivity..."
if [ -n "$ALB_DNS" ]; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/ 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        print_status 0 "ALB is responding (HTTP $HTTP_CODE)"
        echo "   URL: http://$ALB_DNS/"
    else
        print_status 1 "ALB is not responding properly (HTTP $HTTP_CODE)"
    fi
else
    print_status 1 "Could not get ALB DNS name"
fi

# Test 2: ECR Repositories
print_info "Checking ECR repositories..."
if [ -n "$TRAC_ECR" ]; then
    aws ecr describe-repositories --repository-names hutch-learntrac-dev-trac >/dev/null 2>&1
    print_status $? "Trac ECR repository exists"
    echo "   URL: $TRAC_ECR"
else
    print_status 1 "Could not get Trac ECR URL"
fi

if [ -n "$LEARNTRAC_ECR" ]; then
    aws ecr describe-repositories --repository-names hutch-learntrac-dev-learntrac >/dev/null 2>&1
    print_status $? "LearnTrac ECR repository exists"
    echo "   URL: $LEARNTRAC_ECR"
else
    print_status 1 "Could not get LearnTrac ECR URL"
fi

# Test 3: ECS Cluster and Services
print_info "Checking ECS cluster and services..."
if [ -n "$ECS_CLUSTER" ]; then
    aws ecs describe-clusters --clusters $ECS_CLUSTER >/dev/null 2>&1
    print_status $? "ECS cluster exists: $ECS_CLUSTER"
    
    # Check services
    SERVICES=$(aws ecs list-services --cluster $ECS_CLUSTER --query 'serviceArns[*]' --output text 2>/dev/null)
    if [ -n "$SERVICES" ]; then
        print_status 0 "ECS services found"
        
        # Get service status
        aws ecs describe-services --cluster $ECS_CLUSTER --services $SERVICES \
            --query 'services[*].[serviceName,desiredCount,runningCount,pendingCount]' \
            --output table
    else
        print_status 1 "No ECS services found"
    fi
else
    print_status 1 "Could not get ECS cluster name"
fi

# Test 4: Redis Connectivity
print_info "Checking Redis endpoint..."
if [ -n "$REDIS_ENDPOINT" ]; then
    print_status 0 "Redis endpoint configured: $REDIS_ENDPOINT"
    
    # Test if redis-cli is available
    if command -v redis-cli &> /dev/null; then
        redis-cli -h $REDIS_ENDPOINT -p 6379 ping >/dev/null 2>&1
        print_status $? "Redis connectivity test"
    else
        print_info "redis-cli not installed, skipping connectivity test"
    fi
else
    print_status 1 "Could not get Redis endpoint"
fi

# Test 5: Secrets Manager
print_info "Checking AWS Secrets Manager..."
NEO4J_SECRET=$(terraform output -raw neo4j_secret_arn 2>/dev/null || echo "")
if [ -n "$NEO4J_SECRET" ]; then
    aws secretsmanager describe-secret --secret-id $NEO4J_SECRET >/dev/null 2>&1
    print_status $? "Neo4j credentials secret exists"
else
    print_status 1 "Could not get Neo4j secret ARN"
fi

# Test 6: Target Group Health
print_info "Checking target group health..."
TARGET_GROUPS=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'learntrac')].[TargetGroupArn,TargetGroupName]" --output text 2>/dev/null)
if [ -n "$TARGET_GROUPS" ]; then
    while IFS=$'\t' read -r arn name; do
        HEALTHY=$(aws elbv2 describe-target-health --target-group-arn $arn --query 'TargetHealthDescriptions[?TargetHealth.State==`healthy`]' --output text 2>/dev/null | wc -l)
        TOTAL=$(aws elbv2 describe-target-health --target-group-arn $arn --query 'TargetHealthDescriptions' --output text 2>/dev/null | wc -l)
        if [ $TOTAL -gt 0 ]; then
            echo "   $name: $HEALTHY/$TOTAL healthy"
        else
            echo "   $name: No registered targets"
        fi
    done <<< "$TARGET_GROUPS"
else
    print_status 1 "No target groups found"
fi

# Test 7: CloudWatch Log Groups
print_info "Checking CloudWatch log groups..."
aws logs describe-log-groups --log-group-name-prefix "/ecs/hutch-learntrac" --query 'logGroups[*].logGroupName' --output text >/dev/null 2>&1
print_status $? "CloudWatch log groups exist"

echo ""
echo "========================================="
echo "Testing Complete"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. If ECR repositories are empty, build and push Docker images"
echo "2. If services show 0 running tasks, check CloudWatch logs"
echo "3. Once services are running, test ALB path routing"
echo ""
echo "For detailed testing instructions, see: docs/infrastructure_testing.md"