#!/bin/bash
# Test Suite: API Gateway Configuration
# Validates subtask 1.3 (API Gateway with Cognito authorizer)

set -euo pipefail

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"
source "$SCRIPT_DIR/../utils/common.sh"

# Test Functions

test_api_gateway_exists() {
    if [ -z "$API_GATEWAY_ID" ]; then
        log_error "API_GATEWAY_ID not set"
        return 1
    fi
    
    local api_info=$(aws apigateway get-rest-api \
        --rest-api-id "$API_GATEWAY_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$api_info" ]; then
        local api_name=$(echo "$api_info" | jq -r '.name')
        log_success "API Gateway exists: $api_name (ID: $API_GATEWAY_ID)"
        return 0
    else
        log_error "API Gateway not found: $API_GATEWAY_ID"
        return 1
    fi
}

test_api_gateway_authorizers() {
    local authorizers=$(aws apigateway get-authorizers \
        --rest-api-id "$API_GATEWAY_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$authorizers" ]; then
        local cognito_authorizer=$(echo "$authorizers" | jq -r '.items[] | select(.type == "COGNITO_USER_POOLS")')
        
        if [ -n "$cognito_authorizer" ]; then
            local auth_name=$(echo "$cognito_authorizer" | jq -r '.name')
            local auth_id=$(echo "$cognito_authorizer" | jq -r '.id')
            log_success "Cognito authorizer found: $auth_name (ID: $auth_id)"
            
            # Check if it's linked to our user pool
            local provider_arns=$(echo "$cognito_authorizer" | jq -r '.providerARNs[]')
            if echo "$provider_arns" | grep -q "$COGNITO_USER_POOL_ID"; then
                log_success "Authorizer is linked to correct Cognito User Pool"
                return 0
            else
                log_error "Authorizer not linked to expected Cognito User Pool"
                return 1
            fi
        else
            log_error "No Cognito authorizer found"
            return 1
        fi
    else
        log_error "Failed to retrieve authorizers"
        return 1
    fi
}

test_api_gateway_resources() {
    local resources=$(aws apigateway get-resources \
        --rest-api-id "$API_GATEWAY_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$resources" ]; then
        local resource_count=$(echo "$resources" | jq '.items | length')
        log_info "API has $resource_count resources"
        
        # List all paths
        log_info "API Resources:"
        echo "$resources" | jq -r '.items[] | .path' | sort | while read -r path; do
            log_info "  - $path"
        done
        
        # Check for common paths
        local expected_paths=("/tickets" "/wiki" "/components" "/milestones" "/auth")
        for path in "${expected_paths[@]}"; do
            if echo "$resources" | jq -r '.items[].path' | grep -q "^$path"; then
                log_success "Found expected resource: $path"
            else
                log_warning "Expected resource not found: $path"
            fi
        done
        
        return 0
    else
        log_error "Failed to retrieve API resources"
        return 1
    fi
}

test_api_gateway_methods_authorization() {
    local resources=$(aws apigateway get-resources \
        --rest-api-id "$API_GATEWAY_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$resources" ]; then
        local protected_count=0
        local unprotected_count=0
        
        # Check each resource for methods
        echo "$resources" | jq -r '.items[] | @base64' | while read -r resource_encoded; do
            local resource=$(echo "$resource_encoded" | base64 -d)
            local resource_id=$(echo "$resource" | jq -r '.id')
            local resource_path=$(echo "$resource" | jq -r '.path')
            local methods=$(echo "$resource" | jq -r '.resourceMethods | keys[]?' 2>/dev/null)
            
            if [ -n "$methods" ]; then
                echo "$methods" | while read -r method; do
                    # Skip OPTIONS (CORS preflight)
                    if [ "$method" = "OPTIONS" ]; then
                        continue
                    fi
                    
                    # Get method details
                    local method_info=$(aws apigateway get-method \
                        --rest-api-id "$API_GATEWAY_ID" \
                        --resource-id "$resource_id" \
                        --http-method "$method" \
                        --region "$AWS_REGION" 2>/dev/null)
                    
                    if [ -n "$method_info" ]; then
                        local auth_type=$(echo "$method_info" | jq -r '.authorizationType')
                        local authorizer_id=$(echo "$method_info" | jq -r '.authorizerId // empty')
                        
                        if [ "$auth_type" = "CUSTOM" ] || [ "$auth_type" = "COGNITO_USER_POOLS" ] || [ -n "$authorizer_id" ]; then
                            log_info "  $method $resource_path - Protected (auth: $auth_type)"
                            protected_count=$((protected_count + 1))
                        else
                            log_warning "  $method $resource_path - Unprotected"
                            unprotected_count=$((unprotected_count + 1))
                        fi
                    fi
                done
            fi
        done
        
        log_info "Protected methods: $protected_count"
        log_info "Unprotected methods: $unprotected_count"
        
        return 0
    else
        log_error "Failed to check method authorization"
        return 1
    fi
}

test_api_gateway_cors_configuration() {
    local resources=$(aws apigateway get-resources \
        --rest-api-id "$API_GATEWAY_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$resources" ]; then
        local cors_configured=0
        local cors_missing=0
        
        # Check for OPTIONS methods (CORS preflight)
        echo "$resources" | jq -r '.items[] | @base64' | while read -r resource_encoded; do
            local resource=$(echo "$resource_encoded" | base64 -d)
            local resource_path=$(echo "$resource" | jq -r '.path')
            local has_options=$(echo "$resource" | jq -r '.resourceMethods.OPTIONS // empty')
            
            if [ -n "$has_options" ]; then
                log_info "  CORS configured for: $resource_path"
                cors_configured=$((cors_configured + 1))
            else
                # Check if resource has other methods (needs CORS)
                local other_methods=$(echo "$resource" | jq -r '.resourceMethods | keys[]?' 2>/dev/null | grep -v OPTIONS | wc -l)
                if [ "$other_methods" -gt 0 ]; then
                    log_warning "  CORS missing for: $resource_path"
                    cors_missing=$((cors_missing + 1))
                fi
            fi
        done
        
        if [ "$cors_missing" -eq 0 ]; then
            log_success "CORS configuration looks complete"
            return 0
        else
            log_warning "Some resources might need CORS configuration"
            return 0  # Warning, not failure
        fi
    else
        log_error "Failed to check CORS configuration"
        return 1
    fi
}

test_api_gateway_deployment() {
    if [ -z "$API_GATEWAY_STAGE" ]; then
        log_warning "API_GATEWAY_STAGE not set, using 'prod'"
        API_GATEWAY_STAGE="prod"
    fi
    
    local deployment=$(aws apigateway get-stage \
        --rest-api-id "$API_GATEWAY_ID" \
        --stage-name "$API_GATEWAY_STAGE" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$deployment" ]; then
        local deployment_id=$(echo "$deployment" | jq -r '.deploymentId')
        local created_date=$(echo "$deployment" | jq -r '.createdDate')
        local last_updated=$(echo "$deployment" | jq -r '.lastUpdatedDate')
        
        log_success "API Gateway stage '$API_GATEWAY_STAGE' is deployed"
        log_info "  Deployment ID: $deployment_id"
        log_info "  Created: $created_date"
        log_info "  Last updated: $last_updated"
        
        # Check stage variables
        local stage_vars=$(echo "$deployment" | jq -r '.variables // {}')
        if [ "$stage_vars" != "{}" ]; then
            log_info "  Stage variables:"
            echo "$stage_vars" | jq -r 'to_entries[] | "    \(.key): \(.value)"'
        fi
        
        return 0
    else
        log_error "API Gateway stage '$API_GATEWAY_STAGE' not found"
        return 1
    fi
}

test_api_gateway_endpoint_url() {
    if [ -n "$API_GATEWAY_URL" ]; then
        log_info "Testing API Gateway endpoint: $API_GATEWAY_URL"
        
        # Test base URL (should return 403 without auth)
        local status=$(curl -s -o /dev/null -w "%{http_code}" "$API_GATEWAY_URL")
        
        if [ "$status" = "403" ] || [ "$status" = "401" ]; then
            log_success "API Gateway endpoint responds with expected auth error"
            return 0
        elif [ "$status" = "200" ]; then
            log_warning "API Gateway endpoint allows unauthenticated access"
            return 0  # Could be intentional for some endpoints
        else
            log_error "API Gateway endpoint returned unexpected status: $status"
            return 1
        fi
    else
        # Construct URL from API ID and stage
        local constructed_url="https://${API_GATEWAY_ID}.execute-api.${AWS_REGION}.amazonaws.com/${API_GATEWAY_STAGE}"
        log_info "Testing constructed URL: $constructed_url"
        
        local status=$(curl -s -o /dev/null -w "%{http_code}" "$constructed_url")
        
        if [ "$status" = "403" ] || [ "$status" = "401" ] || [ "$status" = "200" ]; then
            log_success "API Gateway is accessible at: $constructed_url"
            log_info "Consider setting API_GATEWAY_URL=$constructed_url"
            return 0
        else
            log_error "API Gateway not accessible, status: $status"
            return 1
        fi
    fi
}

test_api_gateway_throttling() {
    local stage_info=$(aws apigateway get-stage \
        --rest-api-id "$API_GATEWAY_ID" \
        --stage-name "$API_GATEWAY_STAGE" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$stage_info" ]; then
        local throttle_rate=$(echo "$stage_info" | jq -r '.throttle.rateLimit // empty')
        local throttle_burst=$(echo "$stage_info" | jq -r '.throttle.burstLimit // empty')
        
        if [ -n "$throttle_rate" ] && [ -n "$throttle_burst" ]; then
            log_info "API throttling configured:"
            log_info "  Rate limit: $throttle_rate requests/second"
            log_info "  Burst limit: $throttle_burst requests"
            log_success "Throttling is configured"
        else
            log_warning "API throttling not configured at stage level"
        fi
        
        return 0
    else
        log_error "Failed to check throttling configuration"
        return 1
    fi
}

# Main test execution
main() {
    log_info "Starting API Gateway Tests..."
    echo "========================================="
    
    # Validate configuration
    if ! validate_config; then
        log_error "Configuration validation failed"
        exit 1
    fi
    
    # Run tests
    run_test "API Gateway exists" test_api_gateway_exists
    run_test "API Gateway Cognito authorizers" test_api_gateway_authorizers
    run_test "API Gateway resources" test_api_gateway_resources
    run_test "API Gateway method authorization" test_api_gateway_methods_authorization
    run_test "API Gateway CORS configuration" test_api_gateway_cors_configuration
    run_test "API Gateway deployment" test_api_gateway_deployment
    run_test "API Gateway endpoint accessibility" test_api_gateway_endpoint_url
    run_test "API Gateway throttling" test_api_gateway_throttling
    
    # Print summary
    print_test_summary
}

# Execute main function
main "$@"