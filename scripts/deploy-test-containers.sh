#!/bin/bash
# Deploy test containers to ECR for infrastructure testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
echo "Deploying Test Containers to ECR"
echo "========================================="
echo ""

# Get to the right directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Get ECR repository URLs from Terraform
print_info "Getting ECR repository URLs..."
cd "$PROJECT_ROOT/learntrac-infrastructure"

TRAC_REPO=$(terraform output -raw trac_ecr_repository_url)
LEARNTRAC_REPO=$(terraform output -raw learntrac_ecr_repository_url)
REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-east-2")

print_status 0 "Retrieved ECR repository URLs"
echo "   Trac: $TRAC_REPO"
echo "   LearnTrac: $LEARNTRAC_REPO"

# Login to ECR
print_info "Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin ${TRAC_REPO%/*}
print_status $? "ECR login successful"

# Build and push Trac test container
print_info "Building Trac test container..."
cd "$PROJECT_ROOT/test-containers/trac"
docker build -t trac-test .
print_status $? "Trac container built"

print_info "Tagging Trac container..."
docker tag trac-test:latest $TRAC_REPO:latest
docker tag trac-test:latest $TRAC_REPO:test
print_status $? "Trac container tagged"

print_info "Pushing Trac container to ECR..."
docker push $TRAC_REPO:latest
docker push $TRAC_REPO:test
print_status $? "Trac container pushed to ECR"

# Build and push LearnTrac test container
print_info "Building LearnTrac test container..."
cd "$PROJECT_ROOT/test-containers/learntrac"
docker build -t learntrac-test .
print_status $? "LearnTrac container built"

print_info "Tagging LearnTrac container..."
docker tag learntrac-test:latest $LEARNTRAC_REPO:latest
docker tag learntrac-test:latest $LEARNTRAC_REPO:test
print_status $? "LearnTrac container tagged"

print_info "Pushing LearnTrac container to ECR..."
docker push $LEARNTRAC_REPO:latest
docker push $LEARNTRAC_REPO:test
print_status $? "LearnTrac container pushed to ECR"

# Update ECS services to use new images
print_info "Updating ECS services..."
CLUSTER_NAME=$(cd "$PROJECT_ROOT/learntrac-infrastructure" && terraform output -raw ecs_cluster_name)

print_info "Force new deployment for Trac service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service hutch-learntrac-dev-trac \
    --force-new-deployment \
    --query 'service.serviceName' \
    --output text
print_status $? "Trac service update initiated"

print_info "Force new deployment for LearnTrac service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service hutch-learntrac-dev-learntrac \
    --force-new-deployment \
    --query 'service.serviceName' \
    --output text
print_status $? "LearnTrac service update initiated"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Wait 2-3 minutes for services to stabilize"
echo "2. Run: ./scripts/test-infrastructure.sh"
echo "3. Check service health in AWS console"
echo ""
echo "To monitor deployment progress:"
echo "aws ecs describe-services --cluster $CLUSTER_NAME --services hutch-learntrac-dev-trac hutch-learntrac-dev-learntrac --query 'services[*].[serviceName,runningCount,desiredCount]' --output table"