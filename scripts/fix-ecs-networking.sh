#!/bin/bash
# Fix ECS networking issues by enabling public IP assignment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        exit 1
    fi
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo "========================================="
echo "Fixing ECS Networking Issues"
echo "========================================="
echo ""

CLUSTER="hutch-learntrac-dev-cluster"

# First, let's check the current configuration
print_info "Checking current network configuration..."

echo -e "${BLUE}Current Trac Service Network Config:${NC}"
aws ecs describe-services \
  --cluster $CLUSTER \
  --services hutch-learntrac-dev-trac \
  --query 'services[0].networkConfiguration.awsvpcConfiguration' \
  --output json | jq '.'

echo ""
echo -e "${BLUE}Current LearnTrac Service Network Config:${NC}"
aws ecs describe-services \
  --cluster $CLUSTER \
  --services hutch-learntrac-dev-learntrac \
  --query 'services[0].networkConfiguration.awsvpcConfiguration' \
  --output json | jq '.'

echo ""
print_info "Getting subnet and security group information..."

# Get the current configuration
TRAC_CONFIG=$(aws ecs describe-services \
  --cluster $CLUSTER \
  --services hutch-learntrac-dev-trac \
  --query 'services[0].networkConfiguration.awsvpcConfiguration' \
  --output json)

LEARNTRAC_CONFIG=$(aws ecs describe-services \
  --cluster $CLUSTER \
  --services hutch-learntrac-dev-learntrac \
  --query 'services[0].networkConfiguration.awsvpcConfiguration' \
  --output json)

# Extract subnets and security groups
TRAC_SUBNETS=$(echo $TRAC_CONFIG | jq -r '.subnets | join(",")')
TRAC_SG=$(echo $TRAC_CONFIG | jq -r '.securityGroups | join(",")')

LEARNTRAC_SUBNETS=$(echo $LEARNTRAC_CONFIG | jq -r '.subnets | join(",")')
LEARNTRAC_SG=$(echo $LEARNTRAC_CONFIG | jq -r '.securityGroups | join(",")')

echo "Trac Subnets: $TRAC_SUBNETS"
echo "Trac Security Groups: $TRAC_SG"
echo ""
echo "LearnTrac Subnets: $LEARNTRAC_SUBNETS"
echo "LearnTrac Security Groups: $LEARNTRAC_SG"

echo ""
print_info "Checking if subnets are public or private..."

# Check subnet routing
for subnet in $(echo $TRAC_SUBNETS | tr ',' ' '); do
    ROUTE_TABLE=$(aws ec2 describe-route-tables \
      --filters "Name=association.subnet-id,Values=$subnet" \
      --query 'RouteTables[0].RouteTableId' \
      --output text)
    
    if [ "$ROUTE_TABLE" != "None" ]; then
        IGW_ROUTE=$(aws ec2 describe-route-tables \
          --route-table-ids $ROUTE_TABLE \
          --query 'RouteTables[0].Routes[?GatewayId && starts_with(GatewayId, `igw-`)].GatewayId' \
          --output text)
        
        if [ -n "$IGW_ROUTE" ] && [ "$IGW_ROUTE" != "None" ]; then
            echo "✅ Subnet $subnet has Internet Gateway route (public subnet)"
        else
            echo "⚠️  Subnet $subnet has NO Internet Gateway route (private subnet)"
        fi
    fi
done

echo ""
read -p "Do you want to enable public IP assignment for ECS tasks? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Enabling public IP assignment for Trac service..."
    
    aws ecs update-service \
      --cluster $CLUSTER \
      --service hutch-learntrac-dev-trac \
      --network-configuration "awsvpcConfiguration={subnets=[$TRAC_SUBNETS],securityGroups=[$TRAC_SG],assignPublicIp=ENABLED}" \
      --force-new-deployment \
      --query 'service.serviceName' \
      --output text
    
    print_status $? "Trac service updated with public IP assignment"
    
    print_info "Enabling public IP assignment for LearnTrac service..."
    
    aws ecs update-service \
      --cluster $CLUSTER \
      --service hutch-learntrac-dev-learntrac \
      --network-configuration "awsvpcConfiguration={subnets=[$LEARNTRAC_SUBNETS],securityGroups=[$LEARNTRAC_SG],assignPublicIp=ENABLED}" \
      --force-new-deployment \
      --query 'service.serviceName' \
      --output text
    
    print_status $? "LearnTrac service updated with public IP assignment"
    
    echo ""
    echo "========================================="
    echo "✅ Network Configuration Updated!"
    echo "========================================="
    echo ""
    echo "Services will now:"
    echo "1. Stop existing tasks"
    echo "2. Start new tasks with public IPs"
    echo "3. Be able to pull images from ECR"
    echo ""
    echo "Monitor progress with:"
    echo "watch -n 5 'aws ecs describe-services --cluster $CLUSTER --services hutch-learntrac-dev-trac hutch-learntrac-dev-learntrac --query \"services[*].[serviceName,runningCount,desiredCount]\" --output table'"
    
else
    echo ""
    echo "========================================="
    echo "Alternative Solutions:"
    echo "========================================="
    echo ""
    echo "1. Add NAT Gateway to private subnets"
    echo "2. Create VPC Endpoints for ECR"
    echo "3. Move services to public subnets"
    echo ""
    echo "To check recent task failures:"
    echo "aws ecs list-tasks --cluster $CLUSTER --desired-status STOPPED --query 'taskArns[0]' --output text | xargs -I {} aws ecs describe-tasks --cluster $CLUSTER --tasks {} --query 'tasks[0].[stoppedReason,containers[0].reason]'"
fi

echo ""
print_info "Checking for recent stopped tasks to diagnose the issue..."
STOPPED_TASK=$(aws ecs list-tasks --cluster $CLUSTER --desired-status STOPPED --max-items 1 --query 'taskArns[0]' --output text)

if [ "$STOPPED_TASK" != "None" ] && [ -n "$STOPPED_TASK" ]; then
    echo ""
    echo -e "${BLUE}Most recent stopped task details:${NC}"
    aws ecs describe-tasks \
      --cluster $CLUSTER \
      --tasks $STOPPED_TASK \
      --query 'tasks[0].[taskArn,stoppedReason,stopCode,containers[0].[name,reason,exitCode]]' \
      --output json | jq '.'
fi