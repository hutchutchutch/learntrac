#!/bin/bash
# Script to deploy Lambda functions

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"

echo "Deploying Lambda functions for LearnTrac..."

# Build Lambda packages first
echo "Building Lambda packages..."
"${SCRIPT_DIR}/build-lambda-packages.sh"

# Apply Terraform changes
cd "${INFRA_DIR}"

echo ""
echo "Initializing Terraform..."
terraform init

echo ""
echo "Planning Terraform changes..."
terraform plan -out=lambda-deployment.tfplan

echo ""
read -p "Do you want to apply these changes? (yes/no) " -n 3 -r
echo ""
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]
then
    echo "Applying Terraform changes..."
    terraform apply lambda-deployment.tfplan
    
    echo ""
    echo "Lambda deployment complete!"
    echo ""
    echo "API Gateway endpoints:"
    terraform output api_gateway_url
    echo ""
    echo "Lambda function ARNs:"
    terraform output llm_generate_function_arn
    terraform output llm_evaluate_function_arn
else
    echo "Deployment cancelled."
    rm -f lambda-deployment.tfplan
fi