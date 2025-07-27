#!/bin/bash

# Script to fix the dependency cycle by destroying old resources first

set -e

echo "==============================================="
echo "Fixing Terraform dependency cycle"
echo "==============================================="

echo "Step 1: Destroying old API Gateway resources..."

# Destroy old API Gateway resources first to break the cycle
terraform destroy -target=aws_api_gateway_usage_plan.learntrac_plan \
                  -target=aws_api_gateway_stage.learntrac_stage \
                  -target=aws_api_gateway_deployment.learntrac_api \
                  -target=aws_api_gateway_authorizer.cognito \
                  -target=aws_api_gateway_rest_api.learntrac_api \
                  -auto-approve

echo "Step 2: Destroying Cognito resources..."

# Destroy Cognito resources
terraform destroy -target=aws_cognito_user_pool.learntrac_users \
                  -target=aws_cognito_user_pool_client.learntrac_client \
                  -target=aws_cognito_user_pool_domain.learntrac_domain \
                  -target=aws_cognito_resource_server.learntrac_api \
                  -target=aws_cognito_user_group.admins \
                  -target=aws_cognito_user_group.instructors \
                  -target=aws_cognito_user_group.students \
                  -target=aws_lambda_function.cognito_pre_token_generation \
                  -target=aws_lambda_permission.cognito_invoke \
                  -target=aws_iam_role.lambda_cognito \
                  -target=aws_iam_role_policy_attachment.lambda_cognito_basic \
                  -target=aws_secretsmanager_secret.cognito_config \
                  -target=aws_secretsmanager_secret_version.cognito_config \
                  -auto-approve

echo "Step 3: Applying remaining changes..."

# Now apply the rest of the changes
terraform apply -auto-approve

echo "==============================================="
echo "Dependency cycle fixed successfully!"
echo "==============================================="