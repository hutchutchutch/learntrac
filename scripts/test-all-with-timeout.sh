#!/bin/bash
# Comprehensive infrastructure test with timeouts

echo "==================================="
echo "LearnTrac Complete Infrastructure Test"
echo "==================================="

# Setup
export ALB_DNS=$(cd learntrac-infrastructure && terraform output -raw alb_dns_name && cd ..)
export CLUSTER=$(cd learntrac-infrastructure && terraform output -raw ecs_cluster_name && cd ..)
export REDIS_ENDPOINT=$(cd learntrac-infrastructure && terraform output -raw redis_endpoint && cd ..)
PASS=0
FAIL=0

# Function to test with timeout
test_component() {
    echo -n "Testing $1... "
    if timeout 5s bash -c "$2" >/dev/null 2>&1; then
        echo "✅ PASS"
        ((PASS++))
    else
        echo "❌ FAIL (timeout or error)"
        ((FAIL++))
    fi
}

# Function for quick tests (no timeout needed)
test_component_quick() {
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
test_component_quick "ECS Cluster" "aws ecs describe-clusters --clusters $CLUSTER"
test_component_quick "Trac Service Running" "aws ecs describe-services --cluster $CLUSTER --services hutch-learntrac-dev-trac --query 'services[0].runningCount' --output text | grep -E '^[1-9]'"
test_component_quick "LearnTrac Service Running" "aws ecs describe-services --cluster $CLUSTER --services hutch-learntrac-dev-learntrac --query 'services[0].runningCount' --output text | grep -E '^[1-9]'"

# Test Redis with explicit timeout and better error handling
echo -n "Testing Redis Connectivity... "
if [ -n "$REDIS_ENDPOINT" ]; then
    # Try nc (netcat) first as it's faster
    if command -v nc >/dev/null 2>&1; then
        if timeout 2s nc -zv $REDIS_ENDPOINT 6379 >/dev/null 2>&1; then
            echo "✅ PASS (port open)"
            ((PASS++))
        else
            echo "❌ FAIL (port closed or timeout)"
            ((FAIL++))
        fi
    else
        # Fallback to Redis docker test with timeout
        if timeout 5s docker run --rm redis:alpine redis-cli -h $REDIS_ENDPOINT ping 2>&1 | grep -q "PONG"; then
            echo "✅ PASS"
            ((PASS++))
        else
            echo "❌ FAIL (timeout or connection refused)"
            ((FAIL++))
        fi
    fi
else
    echo "❌ FAIL (no endpoint)"
    ((FAIL++))
fi

test_component_quick "ECR Trac Repository" "aws ecr describe-repositories --repository-names hutch-learntrac-dev-trac"
test_component_quick "ECR LearnTrac Repository" "aws ecr describe-repositories --repository-names hutch-learntrac-dev-learntrac"
test_component_quick "Secrets Manager" "aws secretsmanager list-secrets --query 'SecretList[?contains(Name, \`learntrac\`)]' --output text"

echo ""
echo "==================================="
echo "Test Summary: $PASS passed, $FAIL failed"
echo "==================================="

# Additional diagnostics if services aren't running
if ! aws ecs describe-services --cluster $CLUSTER --services hutch-learntrac-dev-trac --query 'services[0].runningCount' --output text | grep -qE '^[1-9]'; then
    echo ""
    echo "⚠️  ECS Services are not running. Checking why..."
    echo ""
    
    # Get recent events
    echo "Recent ECS Events:"
    aws ecs describe-services --cluster $CLUSTER --services hutch-learntrac-dev-trac --query 'services[0].events[0:3].[createdAt,message]' --output table 2>/dev/null || echo "Could not get events"
    
    echo ""
    echo "To fix ECS networking issues, run:"
    echo "./scripts/fix-ecs-networking.sh"
fi

if [ $FAIL -eq 0 ]; then
    echo ""
    echo "🎉 All infrastructure tests passed!"
    exit 0
else
    echo ""
    echo "⚠️  Some tests failed. Issues found:"
    echo ""
    echo "1. ECS services are not running (likely networking issue)"
    echo "2. Redis might be in a private subnet without access"
    echo ""
    echo "Next steps:"
    echo "1. Run: ./scripts/fix-ecs-networking.sh"
    echo "2. Wait 2-3 minutes for services to start"
    echo "3. Run this test again"
    exit 1
fi