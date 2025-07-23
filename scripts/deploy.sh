#!/bin/bash

set -e

ENVIRONMENT=${1:-dev}
ACTION=${2:-apply}
AWS_REGION=${AWS_REGION:-us-east-2}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "==================================="
echo "LearnTrac Deployment Script"
echo "==================================="
echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"
echo "AWS Region: $AWS_REGION"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS CLI is not configured. Please run 'aws configure'"
    exit 1
fi

# Set ECR registry URL
ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Function to build and push Docker image
build_and_push_image() {
    local IMAGE_NAME=$1
    local DOCKERFILE_PATH=$2
    local ECR_REPO_NAME="hutch-learntrac-$ENVIRONMENT-$IMAGE_NAME"
    
    echo "Building $IMAGE_NAME image..."
    docker build -t $IMAGE_NAME:latest $DOCKERFILE_PATH
    
    echo "Tagging image for ECR..."
    docker tag $IMAGE_NAME:latest $ECR_REGISTRY/$ECR_REPO_NAME:latest
    
    echo "Pushing to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    docker push $ECR_REGISTRY/$ECR_REPO_NAME:latest
}

# Build and push Docker images
if [ "$ACTION" == "apply" ]; then
    echo "Building and pushing Docker images..."
    
    # Build Trac image
    if [ -d "trac-legacy" ]; then
        build_and_push_image "trac" "./trac-legacy"
    else
        echo "Warning: trac-legacy directory not found"
    fi
    
    # Build LearnTrac API image
    if [ -d "learntrac-api" ]; then
        build_and_push_image "learntrac" "./learntrac-api"
    else
        echo "Warning: learntrac-api directory not found"
    fi
fi

# Deploy infrastructure with Terraform
echo ""
echo "Deploying infrastructure with Terraform..."
cd learntrac-infrastructure

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    terraform init
fi

# Create terraform.tfvars if it doesn't exist
if [ ! -f "terraform.tfvars" ]; then
    echo "Creating terraform.tfvars..."
    cat > terraform.tfvars <<EOF
environment = "$ENVIRONMENT"
aws_region = "$AWS_REGION"
EOF
fi

# Run Terraform
terraform $ACTION -auto-approve

# Update ECS services to use new images
if [ "$ACTION" == "apply" ]; then
    echo ""
    echo "Updating ECS services with new images..."
    
    CLUSTER_NAME="hutch-learntrac-$ENVIRONMENT-cluster"
    
    # Update Trac service
    echo "Updating Trac service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service hutch-learntrac-$ENVIRONMENT-trac \
        --force-new-deployment \
        --region $AWS_REGION || echo "Trac service not found or update failed"
    
    # Update LearnTrac service
    echo "Updating LearnTrac service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service hutch-learntrac-$ENVIRONMENT-learntrac \
        --force-new-deployment \
        --region $AWS_REGION || echo "LearnTrac service not found or update failed"
    
    # Get ALB DNS name
    echo ""
    echo "==================================="
    echo "Deployment Complete!"
    echo "==================================="
    
    ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "ALB not found")
    echo "Application URL: http://$ALB_DNS"
    echo ""
    echo "Access patterns:"
    echo "  - Trac: http://$ALB_DNS/trac/"
    echo "  - LearnTrac API: http://$ALB_DNS/api/learntrac/health"
    echo ""
fi

echo "Done!"