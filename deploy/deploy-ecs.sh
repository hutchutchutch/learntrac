#!/bin/bash
# Script to deploy LearnTrac to AWS ECS

set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
CLUSTER_NAME=${ECS_CLUSTER_NAME:-learntrac-cluster}
SERVICE_NAME_TRAC=${ECS_SERVICE_TRAC:-learntrac-trac-service}
SERVICE_NAME_API=${ECS_SERVICE_API:-learntrac-api-service}
TASK_FAMILY_TRAC=${ECS_TASK_TRAC:-learntrac-trac}
TASK_FAMILY_API=${ECS_TASK_API:-learntrac-api}
IMAGE_TAG=${IMAGE_TAG:-latest}

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting ECS deployment...${NC}"

# Check if cluster exists
echo -e "${YELLOW}Checking ECS cluster...${NC}"
if ! aws ecs describe-clusters --clusters ${CLUSTER_NAME} --region ${AWS_REGION} | grep -q "ACTIVE"; then
    echo -e "${RED}Error: ECS cluster ${CLUSTER_NAME} not found or not active${NC}"
    exit 1
fi

# Update task definitions
echo -e "${YELLOW}Updating task definitions...${NC}"

# Trac task definition
cat > /tmp/trac-task-def.json <<EOF
{
  "family": "${TASK_FAMILY_TRAC}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "trac",
      "image": "${ECR_REGISTRY}/learntrac-trac:${IMAGE_TAG}",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://\${DB_USER}:\${DB_PASSWORD}@\${RDS_ENDPOINT}/\${DB_NAME}"
        },
        {
          "name": "LEARNING_SERVICE_URL",
          "value": "http://learntrac-api.local:8001"
        },
        {
          "name": "COGNITO_USER_POOL_ID",
          "value": "\${COGNITO_USER_POOL_ID}"
        },
        {
          "name": "COGNITO_CLIENT_ID",
          "value": "\${COGNITO_CLIENT_ID}"
        },
        {
          "name": "AWS_REGION",
          "value": "${AWS_REGION}"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/learntrac-trac",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/login || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# API task definition
cat > /tmp/api-task-def.json <<EOF
{
  "family": "${TASK_FAMILY_API}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "learning-service",
      "image": "${ECR_REGISTRY}/learntrac-api:${IMAGE_TAG}",
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://\${DB_USER}:\${DB_PASSWORD}@\${RDS_ENDPOINT}/\${DB_NAME}"
        },
        {
          "name": "NEO4J_URI",
          "value": "\${NEO4J_URI}"
        },
        {
          "name": "NEO4J_USER",
          "value": "\${NEO4J_USER}"
        },
        {
          "name": "NEO4J_PASSWORD",
          "value": "\${NEO4J_PASSWORD}"
        },
        {
          "name": "REDIS_URL",
          "value": "\${REDIS_URL}"
        },
        {
          "name": "OPENAI_API_KEY",
          "value": "\${OPENAI_API_KEY}"
        },
        {
          "name": "AWS_REGION",
          "value": "${AWS_REGION}"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/learntrac-api",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Register task definitions
echo -e "${YELLOW}Registering task definitions...${NC}"
TRAC_TASK_ARN=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/trac-task-def.json \
    --region ${AWS_REGION} \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

API_TASK_ARN=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/api-task-def.json \
    --region ${AWS_REGION} \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo -e "${GREEN}Task definitions registered:${NC}"
echo "Trac: ${TRAC_TASK_ARN}"
echo "API: ${API_TASK_ARN}"

# Update services
echo -e "${YELLOW}Updating ECS services...${NC}"

# Update Trac service
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${SERVICE_NAME_TRAC} \
    --task-definition ${TRAC_TASK_ARN} \
    --force-new-deployment \
    --region ${AWS_REGION}

# Update API service
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${SERVICE_NAME_API} \
    --task-definition ${API_TASK_ARN} \
    --force-new-deployment \
    --region ${AWS_REGION}

# Wait for services to stabilize
echo -e "${YELLOW}Waiting for services to stabilize...${NC}"
aws ecs wait services-stable \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME_TRAC} ${SERVICE_NAME_API} \
    --region ${AWS_REGION}

echo -e "${GREEN}Deployment complete!${NC}"

# Show service status
echo -e "${YELLOW}Service status:${NC}"
aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME_TRAC} ${SERVICE_NAME_API} \
    --region ${AWS_REGION} \
    --query 'services[*].[serviceName,status,runningCount,desiredCount]' \
    --output table

# Clean up
rm -f /tmp/trac-task-def.json /tmp/api-task-def.json