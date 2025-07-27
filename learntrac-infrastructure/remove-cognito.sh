#!/bin/bash
# Script to remove AWS Cognito resources from LearnTrac infrastructure

set -e

echo "==============================================="
echo "Removing AWS Cognito from LearnTrac Infrastructure"
echo "==============================================="

# Backup current files
echo "Creating backups..."
BACKUP_DIR="backups/cognito-removal-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup files that will be modified
cp main.tf "$BACKUP_DIR/"
cp ecs.tf "$BACKUP_DIR/"
cp outputs.tf "$BACKUP_DIR/"
cp cognito-updates.tf "$BACKUP_DIR/" 2>/dev/null || true
cp api-gateway-enhanced.tf "$BACKUP_DIR/" 2>/dev/null || true
cp api-gateway-llm-methods.tf "$BACKUP_DIR/" 2>/dev/null || true

echo "Backups created in $BACKUP_DIR"

# First, destroy Cognito resources using Terraform
echo ""
echo "Destroying Cognito resources in AWS..."
echo "This will remove:"
echo "  - Cognito User Pool"
echo "  - Cognito User Pool Client"
echo "  - Cognito User Pool Domain"
echo "  - Cognito Resource Server"
echo "  - Cognito User Groups"
echo "  - Cognito Lambda function"
echo "  - Related IAM roles and policies"
echo ""

read -p "Do you want to proceed with destroying these resources? (yes/no): " confirm
if [[ $confirm != "yes" ]]; then
    echo "Aborted."
    exit 1
fi

# Target destroy of Cognito resources
echo "Running targeted destroy of Cognito resources..."
terraform destroy -target=aws_cognito_user_pool.learntrac_users \
                  -target=aws_cognito_user_pool_client.learntrac_client \
                  -target=aws_cognito_user_pool_domain.learntrac_domain \
                  -target=aws_cognito_resource_server.learntrac_api \
                  -target=aws_cognito_user_group.admins \
                  -target=aws_cognito_user_group.instructors \
                  -target=aws_cognito_user_group.students \
                  -target=aws_cognito_identity_provider.google \
                  -target=aws_lambda_function.cognito_pre_token_generation \
                  -target=aws_lambda_permission.cognito_invoke \
                  -target=aws_iam_role.lambda_cognito \
                  -target=aws_iam_role_policy_attachment.lambda_cognito_basic \
                  -target=aws_iam_role_policy.lambda_cognito_enhanced \
                  -target=aws_cloudwatch_log_group.cognito_lambda_logs \
                  -target=aws_secretsmanager_secret.cognito_config \
                  -target=aws_secretsmanager_secret_version.cognito_config \
                  -auto-approve

echo "Cognito resources destroyed."

# Now remove Cognito configuration from Terraform files
echo ""
echo "Removing Cognito configuration from Terraform files..."

# Remove cognito-updates.tf
if [ -f "cognito-updates.tf" ]; then
    rm cognito-updates.tf
    echo "Removed cognito-updates.tf"
fi

# Update main.tf - remove Cognito resources
# This is complex, so we'll create a cleaned version
cat > main.tf.cleaned << 'EOF'
# This file has been cleaned of Cognito resources
# Original file is backed up in $BACKUP_DIR
# 
# TODO: Manually review and remove the following sections from main.tf:
# - IAM role for Lambda Cognito (lines ~145-166)
# - Lambda function cognito_pre_token_generation (lines ~168-187)
# - Cognito User Pool (lines ~190-246)
# - Cognito Resource Server (lines ~248-268)
# - Cognito User Pool Client (lines ~270-304)
# - Cognito User Groups (lines ~306-328)
# - Cognito Domain (lines ~330-334)
# - Lambda Permission for Cognito (lines ~336-342)
# - Secrets Manager for Cognito config (lines ~366-382)
EOF

echo "Created main.tf.cleaned - Please manually update main.tf"

# Update outputs.tf - remove Cognito outputs
sed -i.bak '/output "cognito_/,/^}/d' outputs.tf
echo "Updated outputs.tf - removed Cognito outputs"

# Update ecs.tf - remove Cognito environment variables
sed -i.bak '/COGNITO_POOL_ID/d; /COGNITO_CLIENT_ID/d' ecs.tf
echo "Updated ecs.tf - removed Cognito environment variables"

# Update API Gateway files to remove Cognito references
if [ -f "api-gateway-enhanced.tf" ]; then
    sed -i.bak 's/${aws_cognito_resource_server.learntrac_api.identifier}\/read/learntrac-api\/read/g' api-gateway-enhanced.tf
fi

if [ -f "api-gateway-llm-methods.tf" ]; then
    sed -i.bak 's/${aws_cognito_resource_server.learntrac_api.identifier}\/read/learntrac-api\/read/g' api-gateway-llm-methods.tf
    sed -i.bak 's/${aws_cognito_resource_server.learntrac_api.identifier}\/write/learntrac-api\/write/g' api-gateway-llm-methods.tf
fi

echo ""
echo "==============================================="
echo "Cognito removal process completed!"
echo "==============================================="
echo ""
echo "Manual steps required:"
echo "1. Edit main.tf and remove the Cognito-related resources listed in main.tf.cleaned"
echo "2. Update any API Gateway authorizers that were using Cognito"
echo "3. Review and commit the changes"
echo "4. Run 'terraform plan' to verify the changes"
echo "5. Run 'terraform apply' to apply the final infrastructure updates"
echo ""
echo "The auth proxy approach will handle authentication through the Learning API"
echo "instead of direct Cognito integration."