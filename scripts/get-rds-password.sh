#!/bin/bash

# Script to retrieve RDS password from AWS Secrets Manager
# This helps developers get the actual RDS password for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Please configure AWS credentials using: aws configure"
    exit 1
fi

# Default values
AWS_REGION=${AWS_REGION:-us-east-2}
SECRET_NAME=${SECRET_NAME:-learntrac-dev-db-password}

echo -e "${YELLOW}Retrieving RDS password from AWS Secrets Manager...${NC}"
echo "Region: $AWS_REGION"
echo "Secret Name: $SECRET_NAME"

# Get the secret value
SECRET_VALUE=$(aws secretsmanager get-secret-value \
    --region $AWS_REGION \
    --secret-id $SECRET_NAME \
    --query SecretString \
    --output text 2>/dev/null) || {
    echo -e "${RED}Error: Failed to retrieve secret${NC}"
    echo "Make sure you have the necessary permissions to access AWS Secrets Manager"
    exit 1
}

# Parse the JSON to get the password
if command -v jq &> /dev/null; then
    PASSWORD=$(echo $SECRET_VALUE | jq -r '.password // .')
else
    # Fallback if jq is not installed - assumes the secret is just the password string
    PASSWORD=$SECRET_VALUE
fi

echo -e "${GREEN}Successfully retrieved RDS password${NC}"
echo
echo "To use this password, add it to your .env file:"
echo -e "${YELLOW}RDS_PASSWORD=$PASSWORD${NC}"
echo
echo "Or export it as an environment variable:"
echo -e "${YELLOW}export RDS_PASSWORD=$PASSWORD${NC}"
echo
echo "Full connection string:"
echo -e "${YELLOW}postgresql://learntrac:$PASSWORD@hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com:5432/learntrac${NC}"