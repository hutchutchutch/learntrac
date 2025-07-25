#!/bin/bash
# Test Suite: Terraform Configuration Validation
# Validates subtasks 1.1 (Audit) and 1.9 (State/Apply)

set -euo pipefail

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"
source "$SCRIPT_DIR/../utils/common.sh"

# Test Functions

test_terraform_files_exist() {
    local required_files=(
        "main.tf"
        "variables.tf"
        "outputs.tf"
        "versions.tf"
    )
    
    for file in "${required_files[@]}"; do
        if [ -f "$TF_DIR/$file" ]; then
            log_success "Found required file: $file"
        else
            log_error "Missing required file: $file"
            return 1
        fi
    done
    
    return 0
}

test_terraform_validate() {
    cd "$TF_DIR" || return 1
    
    if terraform init -backend=false >/dev/null 2>&1; then
        log_info "Terraform initialized successfully"
    else
        log_error "Terraform initialization failed"
        return 1
    fi
    
    if terraform validate -no-color; then
        log_success "Terraform configuration is valid"
        return 0
    else
        log_error "Terraform configuration validation failed"
        return 1
    fi
}

test_terraform_backend_s3() {
    # Check if S3 backend is configured
    if grep -q 'backend "s3"' "$TF_DIR"/*.tf 2>/dev/null; then
        log_info "S3 backend configuration found"
        
        # Verify S3 bucket exists
        if aws s3api head-bucket --bucket "$TF_STATE_BUCKET" 2>/dev/null; then
            log_success "S3 state bucket exists: $TF_STATE_BUCKET"
        else
            log_error "S3 state bucket not found: $TF_STATE_BUCKET"
            return 1
        fi
        
        # Check versioning is enabled
        local versioning=$(aws s3api get-bucket-versioning --bucket "$TF_STATE_BUCKET" --query 'Status' --output text 2>/dev/null)
        if [ "$versioning" = "Enabled" ]; then
            log_success "S3 bucket versioning is enabled"
        else
            log_error "S3 bucket versioning is not enabled"
            return 1
        fi
    else
        log_error "S3 backend not configured in Terraform files"
        return 1
    fi
    
    return 0
}

test_terraform_lock_table() {
    # Verify DynamoDB lock table exists
    if aws dynamodb describe-table --table-name "$TF_LOCK_TABLE" --region "$AWS_REGION" >/dev/null 2>&1; then
        log_success "DynamoDB lock table exists: $TF_LOCK_TABLE"
        
        # Check table has correct key schema
        local key_schema=$(aws dynamodb describe-table \
            --table-name "$TF_LOCK_TABLE" \
            --region "$AWS_REGION" \
            --query 'Table.KeySchema[?AttributeName==`LockID`].KeyType' \
            --output text 2>/dev/null)
        
        if [ "$key_schema" = "HASH" ]; then
            log_success "Lock table has correct key schema"
            return 0
        else
            log_error "Lock table has incorrect key schema"
            return 1
        fi
    else
        log_error "DynamoDB lock table not found: $TF_LOCK_TABLE"
        return 1
    fi
}

test_terraform_modules() {
    # Check for module usage
    if find "$TF_DIR" -name "*.tf" -exec grep -l "module \"" {} \; | grep -q .; then
        log_info "Terraform modules detected"
        
        # Validate each module directory exists
        local modules=$(grep -h "source.*=" "$TF_DIR"/*.tf 2>/dev/null | sed 's/.*source.*=.*"\(.*\)".*/\1/' | grep -v "^http" | grep -v "^git")
        
        for module in $modules; do
            if [[ "$module" == ./* ]]; then
                if [ -d "$TF_DIR/$module" ]; then
                    log_success "Module directory exists: $module"
                else
                    log_error "Module directory not found: $module"
                    return 1
                fi
            fi
        done
    else
        log_info "No local modules detected"
    fi
    
    return 0
}

test_terraform_resource_audit() {
    # Audit key resource types
    local resource_types=(
        "aws_cognito_user_pool"
        "aws_api_gateway_rest_api"
        "aws_db_instance"
        "aws_elasticache_cluster"
        "aws_vpc"
        "aws_security_group"
    )
    
    log_info "Auditing Terraform resource declarations..."
    
    for resource in "${resource_types[@]}"; do
        if grep -q "resource \"$resource\"" "$TF_DIR"/*.tf 2>/dev/null; then
            log_success "Found resource type: $resource"
        else
            log_warning "Resource type not found: $resource"
        fi
    done
    
    return 0
}

test_terraform_state_consistency() {
    if [ -z "$TF_STATE_BUCKET" ] || [ -z "$TF_STATE_KEY" ]; then
        skip_test "Terraform state consistency" "State backend not configured"
        return 0
    fi
    
    cd "$TF_DIR" || return 1
    
    # Initialize with backend
    if terraform init -reconfigure >/dev/null 2>&1; then
        log_info "Terraform initialized with backend"
        
        # Check if state file exists
        if aws s3api head-object --bucket "$TF_STATE_BUCKET" --key "$TF_STATE_KEY" >/dev/null 2>&1; then
            log_success "Terraform state file exists in S3"
            
            # Run plan to check drift
            if terraform plan -detailed-exitcode -no-color >/dev/null 2>&1; then
                log_success "Infrastructure matches Terraform state (no drift)"
                return 0
            else
                exit_code=$?
                if [ $exit_code -eq 2 ]; then
                    log_warning "Terraform plan shows pending changes"
                    return 0  # This is not necessarily a failure
                else
                    log_error "Terraform plan failed"
                    return 1
                fi
            fi
        else
            log_warning "Terraform state file not found in S3"
            return 0  # May be first run
        fi
    else
        log_error "Failed to initialize Terraform with backend"
        return 1
    fi
}

# Main test execution
main() {
    log_info "Starting Terraform Configuration Tests..."
    echo "========================================="
    
    # Validate configuration
    if ! validate_config; then
        log_error "Configuration validation failed"
        exit 1
    fi
    
    # Check if Terraform directory exists
    if [ ! -d "$TF_DIR" ]; then
        log_error "Terraform directory not found: $TF_DIR"
        exit 1
    fi
    
    # Run tests
    run_test "Terraform files exist" test_terraform_files_exist
    run_test "Terraform configuration validates" test_terraform_validate
    run_test "Terraform backend S3 bucket" test_terraform_backend_s3
    run_test "Terraform lock table" test_terraform_lock_table
    run_test "Terraform modules" test_terraform_modules
    run_test "Terraform resource audit" test_terraform_resource_audit
    run_test "Terraform state consistency" test_terraform_state_consistency
    
    # Print summary
    print_test_summary
}

# Execute main function
main "$@"