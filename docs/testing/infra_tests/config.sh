#!/bin/bash
# Infrastructure Test Configuration
# Central settings for all infrastructure validation tests

# AWS Configuration
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_PROFILE="${AWS_PROFILE:-default}"

# Terraform Configuration
export TF_DIR="${TF_DIR:-./learntrac-infrastructure}"
export TF_STATE_BUCKET="${TF_STATE_BUCKET:-learntrac-terraform-state}"
export TF_STATE_KEY="${TF_STATE_KEY:-infrastructure/terraform.tfstate}"
export TF_LOCK_TABLE="${TF_LOCK_TABLE:-learntrac-terraform-locks}"

# Cognito Configuration
export COGNITO_USER_POOL_ID="${COGNITO_USER_POOL_ID:-}"
export COGNITO_CLIENT_ID="${COGNITO_CLIENT_ID:-}"
export COGNITO_DOMAIN="${COGNITO_DOMAIN:-}"

# API Gateway Configuration
export API_GATEWAY_ID="${API_GATEWAY_ID:-}"
export API_GATEWAY_STAGE="${API_GATEWAY_STAGE:-prod}"
export API_GATEWAY_URL="${API_GATEWAY_URL:-}"

# RDS Configuration
export RDS_ENDPOINT="${RDS_ENDPOINT:-}"
export RDS_PORT="${RDS_PORT:-5432}"
export RDS_DATABASE="${RDS_DATABASE:-learntrac}"
export RDS_USERNAME="${RDS_USERNAME:-learntrac_admin}"
export RDS_PASSWORD="${RDS_PASSWORD:-}"

# ElastiCache Configuration
export REDIS_ENDPOINT="${REDIS_ENDPOINT:-}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_AUTH_TOKEN="${REDIS_AUTH_TOKEN:-}"

# VPC Configuration
export VPC_ID="${VPC_ID:-}"
export PRIVATE_SUBNET_IDS="${PRIVATE_SUBNET_IDS:-}"
export PUBLIC_SUBNET_IDS="${PUBLIC_SUBNET_IDS:-}"

# Test Configuration
export TEST_TIMEOUT="${TEST_TIMEOUT:-30}"
export TEST_RETRIES="${TEST_RETRIES:-3}"
export TEST_PARALLEL="${TEST_PARALLEL:-false}"

# Output Configuration
export TEST_OUTPUT_DIR="${TEST_OUTPUT_DIR:-./test-results}"
export TEST_LOG_LEVEL="${TEST_LOG_LEVEL:-INFO}"

# Trac Configuration
export TRAC_VERSION="${TRAC_VERSION:-1.4.4}"
export TRAC_SCHEMA_TABLES="attachment auth_cookie cache component enum milestone node_change notify permission report repository revision session session_attribute system ticket ticket_change ticket_custom version wiki"

# Learning Schema Configuration
export LEARNING_SCHEMA="${LEARNING_SCHEMA:-learning}"
export LEARNING_TABLES="paths concept_metadata chunks questions responses"

# Load environment-specific overrides if they exist
if [ -f ".env.test" ]; then
    source .env.test
fi

# Validate required configurations
validate_config() {
    local errors=0
    
    # Check required AWS configuration
    if [ -z "$AWS_REGION" ]; then
        echo "ERROR: AWS_REGION not set"
        errors=$((errors + 1))
    fi
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        echo "ERROR: AWS CLI not configured or credentials invalid"
        errors=$((errors + 1))
    fi
    
    return $errors
}