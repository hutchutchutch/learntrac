#!/bin/bash
# test_network_connectivity.sh
# Tests network connectivity between LearnTrac components

set -e

echo "========================================="
echo "LearnTrac Network Connectivity Test"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get infrastructure details
echo "Gathering infrastructure information..."

# Get RDS endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier "hutch-learntrac-dev-db" \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text 2>/dev/null || echo "not-found")

# Get Redis endpoint
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
    --cache-cluster-id "hutch-learntrac-dev-redis" \
    --show-cache-node-info \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
    --output text 2>/dev/null || echo "not-found")

# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names "hutch-learntrac-dev-alb" \
    --query 'LoadBalancers[0].DNSName' \
    --output text 2>/dev/null || echo "not-found")

echo ""
echo "Infrastructure Endpoints:"
echo "------------------------"
echo "RDS Endpoint: $RDS_ENDPOINT"
echo "Redis Endpoint: $REDIS_ENDPOINT"
echo "ALB DNS: $ALB_DNS"
echo ""

# Function to test connectivity
test_connectivity() {
    local service=$1
    local endpoint=$2
    local port=$3
    
    echo "Testing connectivity to $service..."
    
    if [ "$endpoint" == "not-found" ]; then
        echo -e "${RED}✗ $service endpoint not found${NC}"
        return 1
    fi
    
    # Use timeout command for connection test
    if timeout 5 bash -c "echo >/dev/tcp/$endpoint/$port" 2>/dev/null; then
        echo -e "${GREEN}✓ $service is reachable on port $port${NC}"
        return 0
    else
        echo -e "${RED}✗ $service is not reachable on port $port${NC}"
        return 1
    fi
}

# Test from local machine
echo "========================================="
echo "Testing from Local Machine"
echo "========================================="
echo ""

# Test ALB
test_connectivity "ALB HTTP" "$ALB_DNS" 80
test_connectivity "ALB HTTPS" "$ALB_DNS" 443

# Test RDS (if publicly accessible)
test_connectivity "RDS PostgreSQL" "$RDS_ENDPOINT" 5432

echo ""
echo "========================================="
echo "Testing from ECS Tasks (if possible)"
echo "========================================="
echo ""

# Function to run connectivity test from ECS
test_from_ecs() {
    local task_family=$1
    local target_name=$2
    local target_endpoint=$3
    local target_port=$4
    
    echo "Testing $target_name from $task_family task..."
    
    # Check if task definition exists
    task_def=$(aws ecs describe-task-definition \
        --task-definition "$task_family" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text 2>/dev/null || echo "not-found")
    
    if [ "$task_def" == "not-found" ]; then
        echo -e "${YELLOW}⚠ Task definition $task_family not found${NC}"
        return 1
    fi
    
    # Create a one-off task to test connectivity
    cat > /tmp/ecs-connectivity-test.json <<EOF
{
    "containerOverrides": [{
        "name": "app",
        "command": ["sh", "-c", "nc -zv $target_endpoint $target_port || echo 'Connection failed'"]
    }]
}
EOF
    
    echo "  Running connectivity test task..."
    # Note: This would need proper subnet and security group configuration
    echo -e "${YELLOW}  Note: Actual ECS task execution requires running infrastructure${NC}"
}

# Test from ECS tasks (conceptual - requires running tasks)
test_from_ecs "hutch-learntrac-dev-trac" "RDS" "$RDS_ENDPOINT" 5432
test_from_ecs "hutch-learntrac-dev-learntrac" "Redis" "$REDIS_ENDPOINT" 6379

echo ""
echo "========================================="
echo "Security Group Rules Analysis"
echo "========================================="
echo ""

# Check if ECS can access RDS
echo "Checking if ECS services can access RDS..."
rds_sg=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=*learntrac*rds*" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "not-found")

if [ "$rds_sg" != "not-found" ]; then
    # Check if RDS security group has rules for ECS
    ecs_access=$(aws ec2 describe-security-groups \
        --group-ids "$rds_sg" \
        --query 'SecurityGroups[0].IpPermissions[?FromPort==`5432`].UserIdGroupPairs[].GroupId' \
        --output json)
    
    if [ "$ecs_access" == "[]" ] || [ "$ecs_access" == "null" ]; then
        echo -e "${YELLOW}⚠ RDS security group does not allow ECS access${NC}"
        echo "  Recommendation: Add ECS task security groups to RDS ingress rules"
    else
        echo -e "${GREEN}✓ RDS security group allows ECS access${NC}"
    fi
fi

# Check if ECS can access Redis
echo ""
echo "Checking if ECS services can access Redis..."
redis_sg=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=*learntrac*redis*" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "not-found")

if [ "$redis_sg" != "not-found" ]; then
    # Check if Redis security group has rules for ECS
    ecs_access=$(aws ec2 describe-security-groups \
        --group-ids "$redis_sg" \
        --query 'SecurityGroups[0].IpPermissions[?FromPort==`6379`].UserIdGroupPairs[].GroupId' \
        --output json)
    
    if [ "$ecs_access" != "[]" ] && [ "$ecs_access" != "null" ]; then
        echo -e "${GREEN}✓ Redis security group allows ECS access${NC}"
    else
        echo -e "${YELLOW}⚠ Redis security group configuration unclear${NC}"
    fi
fi

echo ""
echo "========================================="
echo "VPC Endpoints Status"
echo "========================================="
echo ""

# Check VPC endpoints
endpoints=("s3" "ecr.api" "ecr.dkr" "logs" "secretsmanager")
for endpoint in "${endpoints[@]}"; do
    status=$(aws ec2 describe-vpc-endpoints \
        --filters "Name=service-name,Values=com.amazonaws.us-east-2.$endpoint" \
        --query 'VpcEndpoints[0].State' \
        --output text 2>/dev/null || echo "not-found")
    
    if [ "$status" == "available" ]; then
        echo -e "${GREEN}✓ VPC Endpoint for $endpoint: Available${NC}"
    elif [ "$status" == "not-found" ]; then
        echo -e "${YELLOW}⚠ VPC Endpoint for $endpoint: Not configured${NC}"
    else
        echo -e "${RED}✗ VPC Endpoint for $endpoint: $status${NC}"
    fi
done

echo ""
echo "========================================="
echo "Network Test Summary"
echo "========================================="
echo ""
echo "Note: Some tests require running infrastructure and may show as unreachable from local machine."
echo "ECS task connectivity tests are conceptual and require actual running tasks."
echo ""
echo "Key recommendations:"
echo "1. Ensure ECS task security groups are added to RDS ingress rules"
echo "2. Verify all VPC endpoints are in 'available' state"
echo "3. Test actual connectivity after infrastructure deployment"
echo ""
echo "Test complete!"