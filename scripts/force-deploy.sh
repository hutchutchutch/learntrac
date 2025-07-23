#!/bin/bash
# Force deployment script for LearnTrac containers (images already in ECR)

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "LearnTrac Force Deployment Script"
echo "========================================="

# Configuration
REGION="us-east-2"
ACCOUNT_ID="971422717446"
CLUSTER_NAME="hutch-learntrac-dev-cluster"
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Step 1: Update ECS Services (force new deployment with existing images)
echo -e "${YELLOW}Step 1: Forcing new deployment of ECS services...${NC}"
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service hutch-learntrac-dev-trac \
    --force-new-deployment \
    --region ${REGION} \
    --no-cli-pager
echo -e "${GREEN}✓ Trac service update initiated${NC}"

aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service hutch-learntrac-dev-learntrac \
    --force-new-deployment \
    --region ${REGION} \
    --no-cli-pager
echo -e "${GREEN}✓ LearnTrac service update initiated${NC}"

# Step 2: Wait and Check Status
echo -e "${YELLOW}Step 2: Waiting for services to stabilize (this may take 2-3 minutes)...${NC}"
sleep 30

# Check service status
echo -e "${YELLOW}Checking service status...${NC}"
aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services hutch-learntrac-dev-trac hutch-learntrac-dev-learntrac \
    --region ${REGION} \
    --query 'services[*].[serviceName,runningCount,desiredCount,deployments[0].status]' \
    --output table

# Step 3: Test Endpoints
echo -e "${YELLOW}Step 3: Testing endpoints...${NC}"
ALB_URL="http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com"

echo "Testing ALB root..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" ${ALB_URL}/

echo "Testing LearnTrac health..."
curl -s ${ALB_URL}/health | jq . || echo "Failed to get health status"

echo "Testing LearnTrac API health..."
curl -s ${ALB_URL}/api/learntrac/health | jq . || echo "Failed to get API health status"

echo ""
echo "========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================="
echo "ALB URL: ${ALB_URL}"
echo ""
echo "To monitor logs:"
echo "  aws logs tail /ecs/hutch-learntrac-dev-trac --follow --region ${REGION}"
echo "  aws logs tail /ecs/hutch-learntrac-dev-learntrac --follow --region ${REGION}"