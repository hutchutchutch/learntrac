#!/bin/bash
# Script to build and push Docker images to AWS ECR

set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_TAG=${IMAGE_TAG:-latest}

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting ECR push process...${NC}"

# Login to ECR
echo -e "${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Create repositories if they don't exist
echo -e "${YELLOW}Creating ECR repositories if needed...${NC}"
aws ecr describe-repositories --repository-names learntrac-trac --region ${AWS_REGION} 2>/dev/null || \
    aws ecr create-repository --repository-name learntrac-trac --region ${AWS_REGION}

aws ecr describe-repositories --repository-names learntrac-api --region ${AWS_REGION} 2>/dev/null || \
    aws ecr create-repository --repository-name learntrac-api --region ${AWS_REGION}

# Build images
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose build

# Tag images
echo -e "${YELLOW}Tagging images...${NC}"
docker tag learntrac_trac:latest ${ECR_REGISTRY}/learntrac-trac:${IMAGE_TAG}
docker tag learntrac_learning-service:latest ${ECR_REGISTRY}/learntrac-api:${IMAGE_TAG}

# Push images
echo -e "${YELLOW}Pushing images to ECR...${NC}"
docker push ${ECR_REGISTRY}/learntrac-trac:${IMAGE_TAG}
docker push ${ECR_REGISTRY}/learntrac-api:${IMAGE_TAG}

echo -e "${GREEN}Successfully pushed images to ECR!${NC}"
echo -e "Trac image: ${ECR_REGISTRY}/learntrac-trac:${IMAGE_TAG}"
echo -e "API image: ${ECR_REGISTRY}/learntrac-api:${IMAGE_TAG}"