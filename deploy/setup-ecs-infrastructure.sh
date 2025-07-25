#!/bin/bash
# Script to set up AWS ECS infrastructure for LearnTrac

set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
CLUSTER_NAME=${ECS_CLUSTER_NAME:-learntrac-cluster}
VPC_ID=${VPC_ID}
SUBNET_IDS=${SUBNET_IDS}
SECURITY_GROUP_NAME="learntrac-ecs-sg"
LOG_GROUP_TRAC="/ecs/learntrac-trac"
LOG_GROUP_API="/ecs/learntrac-api"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up ECS infrastructure for LearnTrac...${NC}"

# Check required parameters
if [ -z "$VPC_ID" ]; then
    echo -e "${RED}Error: VPC_ID environment variable not set${NC}"
    echo "Please set VPC_ID to your VPC ID"
    exit 1
fi

if [ -z "$SUBNET_IDS" ]; then
    echo -e "${RED}Error: SUBNET_IDS environment variable not set${NC}"
    echo "Please set SUBNET_IDS to comma-separated subnet IDs (e.g., subnet-123,subnet-456)"
    exit 1
fi

# Create ECS cluster
echo -e "${YELLOW}Creating ECS cluster...${NC}"
aws ecs create-cluster \
    --cluster-name ${CLUSTER_NAME} \
    --region ${AWS_REGION} \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy \
        capacityProvider=FARGATE,weight=1,base=1 \
        capacityProvider=FARGATE_SPOT,weight=4 || echo "Cluster already exists"

# Create security group
echo -e "${YELLOW}Creating security group...${NC}"
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
    --group-name ${SECURITY_GROUP_NAME} \
    --description "Security group for LearnTrac ECS tasks" \
    --vpc-id ${VPC_ID} \
    --region ${AWS_REGION} \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=${SECURITY_GROUP_NAME}" \
        --region ${AWS_REGION} \
        --query 'SecurityGroups[0].GroupId' \
        --output text)

echo "Security Group ID: ${SECURITY_GROUP_ID}"

# Add ingress rules
echo -e "${YELLOW}Adding security group rules...${NC}"
# Allow HTTP for Trac
aws ec2 authorize-security-group-ingress \
    --group-id ${SECURITY_GROUP_ID} \
    --protocol tcp \
    --port 8080 \
    --cidr 0.0.0.0/0 \
    --region ${AWS_REGION} 2>/dev/null || echo "Rule already exists"

# Allow API port
aws ec2 authorize-security-group-ingress \
    --group-id ${SECURITY_GROUP_ID} \
    --protocol tcp \
    --port 8001 \
    --cidr 0.0.0.0/0 \
    --region ${AWS_REGION} 2>/dev/null || echo "Rule already exists"

# Create CloudWatch log groups
echo -e "${YELLOW}Creating CloudWatch log groups...${NC}"
aws logs create-log-group \
    --log-group-name ${LOG_GROUP_TRAC} \
    --region ${AWS_REGION} 2>/dev/null || echo "Log group already exists"

aws logs create-log-group \
    --log-group-name ${LOG_GROUP_API} \
    --region ${AWS_REGION} 2>/dev/null || echo "Log group already exists"

# Create task execution role
echo -e "${YELLOW}Creating IAM roles...${NC}"
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

EXECUTION_ROLE_ARN=$(aws iam create-role \
    --role-name learntrac-ecs-execution-role \
    --assume-role-policy-document file:///tmp/trust-policy.json \
    --region ${AWS_REGION} \
    --query 'Role.Arn' \
    --output text 2>/dev/null || \
    aws iam get-role \
        --role-name learntrac-ecs-execution-role \
        --region ${AWS_REGION} \
        --query 'Role.Arn' \
        --output text)

# Attach execution role policy
aws iam attach-role-policy \
    --role-name learntrac-ecs-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
    --region ${AWS_REGION} 2>/dev/null || echo "Policy already attached"

# Create task role
TASK_ROLE_ARN=$(aws iam create-role \
    --role-name learntrac-ecs-task-role \
    --assume-role-policy-document file:///tmp/trust-policy.json \
    --region ${AWS_REGION} \
    --query 'Role.Arn' \
    --output text 2>/dev/null || \
    aws iam get-role \
        --role-name learntrac-ecs-task-role \
        --region ${AWS_REGION} \
        --query 'Role.Arn' \
        --output text)

# Create task role policy
cat > /tmp/task-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:AdminGetUser",
        "cognito-idp:AdminUpdateUserAttributes",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "s3:GetObject",
        "s3:PutObject",
        "lambda:InvokeFunction"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name learntrac-ecs-task-role \
    --policy-name learntrac-task-policy \
    --policy-document file:///tmp/task-policy.json \
    --region ${AWS_REGION}

# Create ECS services
echo -e "${YELLOW}Creating ECS services...${NC}"

# Convert comma-separated subnet IDs to JSON array
SUBNET_JSON=$(echo $SUBNET_IDS | jq -R 'split(",")')

# Trac service
cat > /tmp/trac-service.json <<EOF
{
  "serviceName": "learntrac-trac-service",
  "taskDefinition": "learntrac-trac",
  "desiredCount": 1,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ${SUBNET_JSON},
      "securityGroups": ["${SECURITY_GROUP_ID}"],
      "assignPublicIp": "ENABLED"
    }
  }
}
EOF

aws ecs create-service \
    --cluster ${CLUSTER_NAME} \
    --cli-input-json file:///tmp/trac-service.json \
    --region ${AWS_REGION} 2>/dev/null || echo "Trac service already exists"

# API service
cat > /tmp/api-service.json <<EOF
{
  "serviceName": "learntrac-api-service",
  "taskDefinition": "learntrac-api",
  "desiredCount": 2,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ${SUBNET_JSON},
      "securityGroups": ["${SECURITY_GROUP_ID}"],
      "assignPublicIp": "ENABLED"
    }
  }
}
EOF

aws ecs create-service \
    --cluster ${CLUSTER_NAME} \
    --cli-input-json file:///tmp/api-service.json \
    --region ${AWS_REGION} 2>/dev/null || echo "API service already exists"

# Clean up
rm -f /tmp/trust-policy.json /tmp/task-policy.json /tmp/trac-service.json /tmp/api-service.json

echo -e "${GREEN}ECS infrastructure setup complete!${NC}"
echo
echo "Summary:"
echo "- Cluster: ${CLUSTER_NAME}"
echo "- Security Group: ${SECURITY_GROUP_ID}"
echo "- Execution Role: ${EXECUTION_ROLE_ARN}"
echo "- Task Role: ${TASK_ROLE_ARN}"
echo
echo "Next steps:"
echo "1. Update your .env file with the security group and role ARNs"
echo "2. Run ./deploy/push-to-ecr.sh to push images"
echo "3. Run ./deploy/deploy-ecs.sh to deploy services"