#!/bin/bash
# Staged Terraform Apply Script for LearnTrac Infrastructure
# This script applies Terraform changes in stages to minimize risk

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to ask for confirmation
confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Operation cancelled by user"
        exit 1
    fi
}

# Check if we're in the right directory
if [ ! -f "main.tf" ]; then
    print_error "This script must be run from the terraform directory containing main.tf"
    exit 1
fi

# Start the staged apply process
print_status "Starting staged Terraform apply process"

# Stage 1: Security Groups and Network
print_status "Stage 1: Applying security groups and network configurations"
confirm "Apply security group changes?"
terraform apply -target=aws_security_group.rds_enhanced \
                -target=aws_security_group.lambda_sg \
                -target=aws_security_group.ecs_shared \
                -auto-approve

# Stage 2: Database Enhancements
print_status "Stage 2: Applying database enhancements"
confirm "Apply RDS parameter groups and monitoring?"
terraform apply -target=aws_db_parameter_group.learntrac_pg15 \
                -target=aws_db_option_group.learntrac_options \
                -target=aws_iam_role.rds_enhanced_monitoring \
                -target=aws_kms_key.rds_encryption \
                -auto-approve

# Stage 3: Lambda and Cognito
print_status "Stage 3: Applying Lambda and Cognito updates"
confirm "Apply Lambda and Cognito changes?"
terraform apply -target=aws_cloudwatch_log_group.cognito_lambda_logs \
                -target=aws_iam_role_policy.lambda_cognito_enhanced \
                -auto-approve

# Stage 4: API Gateway
print_status "Stage 4: Applying API Gateway resources"
confirm "Apply API Gateway changes?"
terraform apply -target=aws_api_gateway_deployment.learntrac_api \
                -target=aws_api_gateway_stage.learntrac_stage \
                -target=module.aws_api_gateway \
                -auto-approve

# Stage 5: Monitoring and Dashboards
print_status "Stage 5: Applying monitoring resources"
confirm "Apply CloudWatch dashboards and alarms?"
terraform apply -target=aws_cloudwatch_dashboard.main \
                -target=aws_cloudwatch_metric_alarm \
                -target=aws_sns_topic.alerts \
                -auto-approve

# Final Stage: Complete Apply
print_status "Final Stage: Applying all remaining resources"
print_warning "This will apply all remaining changes"
confirm "Proceed with full apply?"

# Run final plan to show what will be applied
terraform plan -out=final.tfplan
terraform show -no-color final.tfplan | head -50

confirm "Apply the final plan?"
terraform apply final.tfplan

print_status "Terraform apply completed successfully!"

# Post-apply validation
print_status "Running post-apply validation..."

# Check if critical resources were created
if terraform state show aws_db_instance.learntrac > /dev/null 2>&1; then
    print_status "✓ RDS instance exists"
else
    print_error "✗ RDS instance not found"
fi

if terraform state show aws_cognito_user_pool.learntrac_users > /dev/null 2>&1; then
    print_status "✓ Cognito user pool exists"
else
    print_error "✗ Cognito user pool not found"
fi

if terraform state show aws_api_gateway_rest_api.learntrac_api > /dev/null 2>&1; then
    print_status "✓ API Gateway exists"
else
    print_error "✗ API Gateway not found"
fi

# Output important information
print_status "Generating outputs..."
terraform output -json > terraform-outputs.json

print_status "Apply process completed. Check terraform-outputs.json for resource details."
print_warning "Remember to:"
echo "  1. Test API endpoints"
echo "  2. Verify database connectivity"
echo "  3. Check CloudWatch dashboards"
echo "  4. Configure application with new endpoints"