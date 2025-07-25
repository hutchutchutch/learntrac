#!/bin/bash
# Test Suite: Cognito User Pool Validation
# Validates subtask 1.2 (Cognito configuration)

set -euo pipefail

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"
source "$SCRIPT_DIR/../utils/common.sh"

# Test Functions

test_cognito_user_pool_exists() {
    if [ -z "$COGNITO_USER_POOL_ID" ]; then
        log_error "COGNITO_USER_POOL_ID not set"
        return 1
    fi
    
    local pool_info=$(aws cognito-idp describe-user-pool \
        --user-pool-id "$COGNITO_USER_POOL_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$pool_info" ]; then
        local pool_name=$(echo "$pool_info" | jq -r '.UserPool.Name')
        log_success "User pool exists: $pool_name (ID: $COGNITO_USER_POOL_ID)"
        return 0
    else
        log_error "User pool not found: $COGNITO_USER_POOL_ID"
        return 1
    fi
}

test_cognito_app_client() {
    if [ -z "$COGNITO_CLIENT_ID" ]; then
        log_error "COGNITO_CLIENT_ID not set"
        return 1
    fi
    
    local client_info=$(aws cognito-idp describe-user-pool-client \
        --user-pool-id "$COGNITO_USER_POOL_ID" \
        --client-id "$COGNITO_CLIENT_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$client_info" ]; then
        local client_name=$(echo "$client_info" | jq -r '.UserPoolClient.ClientName')
        log_success "App client exists: $client_name (ID: $COGNITO_CLIENT_ID)"
        
        # Check OAuth flows
        local allowed_flows=$(echo "$client_info" | jq -r '.UserPoolClient.AllowedOAuthFlows[]' 2>/dev/null)
        if echo "$allowed_flows" | grep -q "code"; then
            log_success "Authorization code flow is enabled"
        else
            log_warning "Authorization code flow not enabled"
        fi
        
        return 0
    else
        log_error "App client not found: $COGNITO_CLIENT_ID"
        return 1
    fi
}

test_cognito_domain() {
    if [ -z "$COGNITO_DOMAIN" ]; then
        skip_test "Cognito domain" "COGNITO_DOMAIN not configured"
        return 0
    fi
    
    local domain_info=$(aws cognito-idp describe-user-pool-domain \
        --domain "$COGNITO_DOMAIN" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$domain_info" ]; then
        local status=$(echo "$domain_info" | jq -r '.DomainDescription.Status')
        if [ "$status" = "ACTIVE" ]; then
            log_success "Cognito domain is active: $COGNITO_DOMAIN"
            return 0
        else
            log_error "Cognito domain not active: $status"
            return 1
        fi
    else
        log_error "Cognito domain not found: $COGNITO_DOMAIN"
        return 1
    fi
}

test_cognito_password_policy() {
    local pool_info=$(aws cognito-idp describe-user-pool \
        --user-pool-id "$COGNITO_USER_POOL_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$pool_info" ]; then
        local min_length=$(echo "$pool_info" | jq -r '.UserPool.Policies.PasswordPolicy.MinimumLength')
        local require_uppercase=$(echo "$pool_info" | jq -r '.UserPool.Policies.PasswordPolicy.RequireUppercase')
        local require_lowercase=$(echo "$pool_info" | jq -r '.UserPool.Policies.PasswordPolicy.RequireLowercase')
        local require_numbers=$(echo "$pool_info" | jq -r '.UserPool.Policies.PasswordPolicy.RequireNumbers')
        local require_symbols=$(echo "$pool_info" | jq -r '.UserPool.Policies.PasswordPolicy.RequireSymbols')
        
        log_info "Password policy:"
        log_info "  Minimum length: $min_length"
        log_info "  Require uppercase: $require_uppercase"
        log_info "  Require lowercase: $require_lowercase"
        log_info "  Require numbers: $require_numbers"
        log_info "  Require symbols: $require_symbols"
        
        if [ "$min_length" -ge 8 ]; then
            log_success "Password minimum length meets security requirements"
            return 0
        else
            log_warning "Password minimum length is less than 8 characters"
            return 0  # Warning, not failure
        fi
    else
        log_error "Failed to retrieve password policy"
        return 1
    fi
}

test_cognito_mfa_configuration() {
    local mfa_config=$(aws cognito-idp get-user-pool-mfa-config \
        --user-pool-id "$COGNITO_USER_POOL_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$mfa_config" ]; then
        local mfa_configuration=$(echo "$mfa_config" | jq -r '.MfaConfiguration')
        log_info "MFA Configuration: $mfa_configuration"
        
        if [ "$mfa_configuration" = "ON" ] || [ "$mfa_configuration" = "OPTIONAL" ]; then
            log_success "MFA is enabled"
            
            # Check MFA types
            local sms_enabled=$(echo "$mfa_config" | jq -r '.SmsMfaConfiguration.SmsAuthenticationMessage' | grep -q "null" && echo "false" || echo "true")
            local totp_enabled=$(echo "$mfa_config" | jq -r '.SoftwareTokenMfaConfiguration.Enabled')
            
            [ "$sms_enabled" = "true" ] && log_info "  SMS MFA: Enabled"
            [ "$totp_enabled" = "true" ] && log_info "  TOTP MFA: Enabled"
            
            return 0
        else
            log_warning "MFA is not enabled"
            return 0  # Warning, not failure
        fi
    else
        log_error "Failed to retrieve MFA configuration"
        return 1
    fi
}

test_cognito_jwt_configuration() {
    local client_info=$(aws cognito-idp describe-user-pool-client \
        --user-pool-id "$COGNITO_USER_POOL_ID" \
        --client-id "$COGNITO_CLIENT_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$client_info" ]; then
        # Check token validity periods
        local id_token_validity=$(echo "$client_info" | jq -r '.UserPoolClient.IdTokenValidity // 60')
        local access_token_validity=$(echo "$client_info" | jq -r '.UserPoolClient.AccessTokenValidity // 60')
        local refresh_token_validity=$(echo "$client_info" | jq -r '.UserPoolClient.RefreshTokenValidity // 30')
        
        log_info "Token validity periods:"
        log_info "  ID Token: $id_token_validity minutes"
        log_info "  Access Token: $access_token_validity minutes"
        log_info "  Refresh Token: $refresh_token_validity days"
        
        # Check if reasonable values
        if [ "$access_token_validity" -le 1440 ]; then  # 24 hours
            log_success "Access token validity is reasonable"
            return 0
        else
            log_warning "Access token validity might be too long"
            return 0
        fi
    else
        log_error "Failed to retrieve JWT configuration"
        return 1
    fi
}

test_cognito_callback_urls() {
    local client_info=$(aws cognito-idp describe-user-pool-client \
        --user-pool-id "$COGNITO_USER_POOL_ID" \
        --client-id "$COGNITO_CLIENT_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$client_info" ]; then
        local callback_urls=$(echo "$client_info" | jq -r '.UserPoolClient.CallbackURLs[]' 2>/dev/null)
        local logout_urls=$(echo "$client_info" | jq -r '.UserPoolClient.LogoutURLs[]' 2>/dev/null)
        
        if [ -n "$callback_urls" ]; then
            log_info "Callback URLs configured:"
            echo "$callback_urls" | while read -r url; do
                log_info "  - $url"
            done
            
            # Check if API Gateway URL is in callbacks
            if [ -n "$API_GATEWAY_URL" ]; then
                if echo "$callback_urls" | grep -q "$API_GATEWAY_URL"; then
                    log_success "API Gateway URL is in callback URLs"
                else
                    log_warning "API Gateway URL not found in callback URLs"
                fi
            fi
        else
            log_warning "No callback URLs configured"
        fi
        
        if [ -n "$logout_urls" ]; then
            log_info "Logout URLs configured:"
            echo "$logout_urls" | while read -r url; do
                log_info "  - $url"
            done
        fi
        
        return 0
    else
        log_error "Failed to retrieve callback URLs"
        return 1
    fi
}

test_cognito_user_attributes() {
    local pool_info=$(aws cognito-idp describe-user-pool \
        --user-pool-id "$COGNITO_USER_POOL_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$pool_info" ]; then
        log_info "Required attributes:"
        echo "$pool_info" | jq -r '.UserPool.SchemaAttributes[] | select(.Required == true) | .Name' | while read -r attr; do
            log_info "  - $attr"
        done
        
        # Check for email verification
        local email_verification=$(echo "$pool_info" | jq -r '.UserPool.AutoVerifiedAttributes[]' | grep -q "email" && echo "true" || echo "false")
        if [ "$email_verification" = "true" ]; then
            log_success "Email auto-verification is enabled"
        else
            log_warning "Email auto-verification is not enabled"
        fi
        
        return 0
    else
        log_error "Failed to retrieve user attributes"
        return 1
    fi
}

# Main test execution
main() {
    log_info "Starting Cognito User Pool Tests..."
    echo "========================================="
    
    # Validate configuration
    if ! validate_config; then
        log_error "Configuration validation failed"
        exit 1
    fi
    
    # Run tests
    run_test "Cognito user pool exists" test_cognito_user_pool_exists
    run_test "Cognito app client configuration" test_cognito_app_client
    run_test "Cognito domain configuration" test_cognito_domain
    run_test "Cognito password policy" test_cognito_password_policy
    run_test "Cognito MFA configuration" test_cognito_mfa_configuration
    run_test "Cognito JWT configuration" test_cognito_jwt_configuration
    run_test "Cognito callback URLs" test_cognito_callback_urls
    run_test "Cognito user attributes" test_cognito_user_attributes
    
    # Print summary
    print_test_summary
}

# Execute main function
main "$@"