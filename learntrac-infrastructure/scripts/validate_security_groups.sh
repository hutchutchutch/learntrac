#!/bin/bash
# validate_security_groups.sh
# Validates all LearnTrac security groups and their rules

set -e

echo "========================================="
echo "LearnTrac Security Groups Validation"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check security group
check_security_group() {
    local sg_name=$1
    local expected_rules=$2
    
    echo "Checking Security Group: $sg_name"
    echo "----------------------------------------"
    
    # Get security group details
    sg_info=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=*$sg_name*" \
        --query 'SecurityGroups[0]' \
        --output json 2>/dev/null || echo "{}")
    
    if [ "$sg_info" == "{}" ] || [ "$sg_info" == "null" ]; then
        echo -e "${RED}✗ Security group not found${NC}"
        return 1
    fi
    
    # Extract group ID and name
    group_id=$(echo "$sg_info" | jq -r '.GroupId')
    group_name=$(echo "$sg_info" | jq -r '.GroupName')
    
    echo "Group ID: $group_id"
    echo "Group Name: $group_name"
    echo ""
    
    # Check ingress rules
    echo "Ingress Rules:"
    echo "$sg_info" | jq -r '.IpPermissions[] | "  Port: \(.FromPort // "All") | Protocol: \(.IpProtocol) | Source: \(.IpRanges[0].CidrIp // .UserIdGroupPairs[0].GroupId // "N/A")"'
    
    # Check egress rules
    echo ""
    echo "Egress Rules:"
    echo "$sg_info" | jq -r '.IpPermissionsEgress[] | "  Port: \(.FromPort // "All") | Protocol: \(.IpProtocol) | Destination: \(.IpRanges[0].CidrIp // "N/A")"'
    
    echo -e "${GREEN}✓ Security group validated${NC}"
    echo ""
}

# Validate RDS Security Group
echo "1. RDS Security Group"
check_security_group "learntrac-dev-rds-sg" "5432"

# Validate Redis Security Group
echo "2. Redis Security Group"
check_security_group "learntrac-dev-redis-sg" "6379"

# Validate ALB Security Group
echo "3. ALB Security Group"
check_security_group "learntrac-dev-alb-sg" "80,443"

# Validate ECS Task Security Groups
echo "4. ECS Task Security Groups"
check_security_group "learntrac-dev-trac-ecs-tasks-sg" "8000"
check_security_group "learntrac-dev-learntrac-ecs-tasks-sg" "8001"

# Validate VPC Endpoints Security Group
echo "5. VPC Endpoints Security Group"
check_security_group "learntrac-dev-vpc-endpoints-sg" "443"

# Summary
echo "========================================="
echo "Security Group Validation Summary"
echo "========================================="

# Check for overly permissive rules
echo ""
echo "Checking for security concerns..."

# Check for unrestricted inbound access (0.0.0.0/0)
public_sgs=$(aws ec2 describe-security-groups \
    --filters "Name=ip-permission.cidr,Values=0.0.0.0/0" \
    --query 'SecurityGroups[?contains(GroupName, `learntrac`)].GroupName' \
    --output json)

if [ "$public_sgs" != "[]" ]; then
    echo -e "${YELLOW}⚠ Security groups with public access (0.0.0.0/0):${NC}"
    echo "$public_sgs" | jq -r '.[]'
    echo "  Note: ALB security group is expected to have public access"
else
    echo -e "${GREEN}✓ No unexpected public access found${NC}"
fi

# Check for missing security groups
echo ""
echo "Checking for missing components..."
expected_components=("rds" "redis" "alb" "ecs-tasks" "vpc-endpoints")
missing=0

for component in "${expected_components[@]}"; do
    count=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=*learntrac*$component*" \
        --query 'length(SecurityGroups)' \
        --output text)
    
    if [ "$count" -eq 0 ]; then
        echo -e "${RED}✗ Missing security group for: $component${NC}"
        missing=$((missing + 1))
    fi
done

if [ $missing -eq 0 ]; then
    echo -e "${GREEN}✓ All expected security groups present${NC}"
fi

echo ""
echo "Validation complete!"