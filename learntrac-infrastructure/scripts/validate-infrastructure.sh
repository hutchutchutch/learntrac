#!/bin/bash
# Infrastructure Validation Script for LearnTrac
# Run this after terraform apply to validate the deployment

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
PASS=0
FAIL=0

echo "================================================"
echo "LearnTrac Infrastructure Validation"
echo "================================================"
echo

# Function to check a resource
check_resource() {
    local resource_type=$1
    local resource_name=$2
    local description=$3
    
    if terraform state show "${resource_type}.${resource_name}" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} ${description}"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} ${description}"
        ((FAIL++))
    fi
}

# Function to check AWS resource
check_aws_resource() {
    local aws_command=$1
    local description=$2
    
    if eval "$aws_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} ${description}"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} ${description}"
        ((FAIL++))
    fi
}

# Check Terraform state resources
echo "Checking Terraform State..."
echo "----------------------------"
check_resource "aws_db_instance" "learntrac" "RDS PostgreSQL instance"
check_resource "aws_cognito_user_pool" "learntrac_users" "Cognito User Pool"
check_resource "aws_api_gateway_rest_api" "learntrac_api" "API Gateway"
check_resource "aws_ecs_cluster" "main" "ECS Cluster"
check_resource "aws_elasticache_cluster" "redis" "Redis Cache Cluster"
check_resource "aws_ecr_repository" "learntrac" "ECR Repository - LearnTrac"
check_resource "aws_ecr_repository" "trac" "ECR Repository - Trac"
check_resource "module.alb.aws_lb" "main" "Application Load Balancer"
echo

# Check AWS resources are accessible
echo "Checking AWS Resource Accessibility..."
echo "--------------------------------------"

# Get region from Terraform
REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-east-2")

# RDS connectivity
if DB_ENDPOINT=$(terraform output -raw db_endpoint 2>/dev/null); then
    echo -e "${GREEN}✓${NC} RDS endpoint available: ${DB_ENDPOINT}"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Could not retrieve RDS endpoint"
    ((FAIL++))
fi

# API Gateway URL
if API_URL=$(terraform output -raw api_gateway_url 2>/dev/null); then
    echo -e "${GREEN}✓${NC} API Gateway URL: ${API_URL}"
    ((PASS++))
    
    # Test API health endpoint (if exists)
    if curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" | grep -q "200\|404"; then
        echo -e "${GREEN}✓${NC} API Gateway is responding"
        ((PASS++))
    else
        echo -e "${YELLOW}⚠${NC} API Gateway health check failed (might be normal if endpoint doesn't exist)"
    fi
else
    echo -e "${RED}✗${NC} Could not retrieve API Gateway URL"
    ((FAIL++))
fi

# ALB DNS
if ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null); then
    echo -e "${GREEN}✓${NC} ALB DNS: ${ALB_DNS}"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Could not retrieve ALB DNS"
    ((FAIL++))
fi
echo

# Check Secrets Manager
echo "Checking Secrets Manager..."
echo "---------------------------"
check_aws_resource "aws secretsmanager describe-secret --secret-id hutch-learntrac-dev-db-credentials --region $REGION" "Database credentials secret"
check_aws_resource "aws secretsmanager describe-secret --secret-id hutch-learntrac-dev-cognito-config --region $REGION" "Cognito configuration secret"
echo

# Check Security Groups
echo "Checking Security Groups..."
echo "---------------------------"
for sg in rds redis ecs_tasks alb vpc_endpoints; do
    if SG_ID=$(terraform state show "aws_security_group.$sg" 2>/dev/null | grep -E "id\s+=" | awk '{print $3}' | tr -d '"'); then
        if [ -n "$SG_ID" ]; then
            echo -e "${GREEN}✓${NC} Security group '$sg' exists: $SG_ID"
            ((PASS++))
        else
            echo -e "${RED}✗${NC} Security group '$sg' ID not found"
            ((FAIL++))
        fi
    else
        echo -e "${YELLOW}⚠${NC} Security group '$sg' might not be in state"
    fi
done
echo

# Check IAM Roles
echo "Checking IAM Roles..."
echo "---------------------"
check_resource "aws_iam_role" "lambda_cognito" "Lambda Cognito execution role"
check_resource "module.trac_service.aws_iam_role" "ecs_execution" "ECS execution role - Trac"
check_resource "module.learntrac_service.aws_iam_role" "ecs_task" "ECS task role - LearnTrac"
echo

# Summary
echo "================================================"
echo "Validation Summary"
echo "================================================"
echo -e "Passed: ${GREEN}${PASS}${NC}"
echo -e "Failed: ${RED}${FAIL}${NC}"
echo

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All validation checks passed!${NC}"
    exit 0
else
    echo -e "${YELLOW}Some validation checks failed. Please investigate.${NC}"
    exit 1
fi