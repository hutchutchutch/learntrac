#!/bin/bash

# Authentication API Tests

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source common utilities
source "$SCRIPT_DIR/../utils/common.sh"

# Test counters
PASSED=0
FAILED=0

# Test: Login with valid credentials
test_login_valid() {
    local auth_data=$(cat <<EOF
{
    "username": "$TEST_USER_STUDENT",
    "password": "$TEST_PASS_STUDENT",
    "grant_type": "password"
}
EOF
)
    
    local response=$(make_request "POST" "/auth/login" "$auth_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "access_token refresh_token token_type expires_in user"; then
            # Extract tokens for subsequent tests
            ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token')
            REFRESH_TOKEN=$(echo "$response" | jq -r '.refresh_token')
            USER_ID=$(echo "$response" | jq -r '.user.id')
            
            # Verify token type
            local token_type=$(echo "$response" | jq -r '.token_type')
            if [ "$token_type" = "bearer" ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Login with invalid credentials
test_login_invalid() {
    local auth_data=$(cat <<EOF
{
    "username": "invalid_user",
    "password": "wrong_password",
    "grant_type": "password"
}
EOF
)
    
    local response=$(make_request "POST" "/auth/login" "$auth_data")
    local status=$?
    
    if [ $status -eq 401 ] || [ $status -eq 400 ]; then
        if validate_json "$response" "error"; then
            return 0
        fi
    fi
    
    return 1
}

# Test: Login with missing fields
test_login_missing_fields() {
    local auth_data=$(cat <<EOF
{
    "username": "$TEST_USER_STUDENT"
}
EOF
)
    
    local response=$(make_request "POST" "/auth/login" "$auth_data")
    local status=$?
    
    if [ $status -eq 400 ]; then
        return 0
    fi
    
    return 1
}

# Test: Refresh token
test_refresh_token() {
    # First login to get tokens
    if ! authenticate; then
        return 1
    fi
    
    # Wait a moment
    sleep 1
    
    local refresh_data=$(cat <<EOF
{
    "refresh_token": "$REFRESH_TOKEN"
}
EOF
)
    
    local response=$(make_request "POST" "/auth/refresh" "$refresh_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "access_token token_type expires_in"; then
            # Update access token
            ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token')
            return 0
        fi
    fi
    
    return 1
}

# Test: Refresh with invalid token
test_refresh_invalid_token() {
    local refresh_data=$(cat <<EOF
{
    "refresh_token": "invalid_refresh_token_12345"
}
EOF
)
    
    local response=$(make_request "POST" "/auth/refresh" "$refresh_data")
    local status=$?
    
    if [ $status -eq 401 ] || [ $status -eq 400 ]; then
        return 0
    fi
    
    return 1
}

# Test: Get current user profile
test_get_profile() {
    # Ensure we're authenticated
    if [ -z "$ACCESS_TOKEN" ]; then
        if ! authenticate; then
            return 1
        fi
    fi
    
    local response=$(make_request "GET" "/auth/me")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "id username email roles created_at learning_profile"; then
            # Verify user ID matches
            local profile_id=$(echo "$response" | jq -r '.id')
            if [ "$profile_id" = "$USER_ID" ]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Get profile without authentication
test_get_profile_unauthorized() {
    # Clear token temporarily
    local saved_token=$ACCESS_TOKEN
    ACCESS_TOKEN=""
    
    local response=$(make_request "GET" "/auth/me")
    local status=$?
    
    # Restore token
    ACCESS_TOKEN=$saved_token
    
    if [ $status -eq 401 ]; then
        return 0
    fi
    
    return 1
}

# Test: Logout
test_logout() {
    # Ensure we're authenticated
    if [ -z "$ACCESS_TOKEN" ]; then
        if ! authenticate; then
            return 1
        fi
    fi
    
    local response=$(make_request "POST" "/auth/logout")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "message"; then
            # Verify the token is invalidated by trying to use it
            local test_response=$(make_request "GET" "/auth/me")
            local test_status=$?
            
            if [ $test_status -eq 401 ]; then
                # Clear tokens
                ACCESS_TOKEN=""
                REFRESH_TOKEN=""
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Login as instructor
test_login_instructor() {
    local auth_data=$(cat <<EOF
{
    "username": "$TEST_USER_INSTRUCTOR",
    "password": "$TEST_PASS_INSTRUCTOR",
    "grant_type": "password"
}
EOF
)
    
    local response=$(make_request "POST" "/auth/login" "$auth_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        if validate_json "$response" "access_token user"; then
            # Verify instructor role
            local roles=$(echo "$response" | jq -r '.user.roles[]')
            if echo "$roles" | grep -q "instructor"; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test: Concurrent login attempts
test_concurrent_logins() {
    local auth_data=$(cat <<EOF
{
    "username": "$TEST_USER_STUDENT",
    "password": "$TEST_PASS_STUDENT",
    "grant_type": "password"
}
EOF
)
    
    # Attempt multiple logins concurrently
    local pids=()
    local results_dir="${OUTPUT_DIR}/concurrent_login_results"
    mkdir -p "$results_dir"
    
    for i in {1..5}; do
        (
            local response=$(make_request "POST" "/auth/login" "$auth_data")
            local status=$?
            echo "$status" > "$results_dir/result_$i"
        ) &
        pids+=($!)
    done
    
    # Wait for all requests to complete
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    # Check all succeeded
    local all_success=true
    for i in {1..5}; do
        local status=$(cat "$results_dir/result_$i")
        if [ "$status" != "200" ]; then
            all_success=false
            break
        fi
    done
    
    # Cleanup
    rm -rf "$results_dir"
    
    if [ "$all_success" = true ]; then
        return 0
    fi
    
    return 1
}

# Run all tests
run_all_tests() {
    print_status "INFO" "Starting Authentication API Tests"
    
    # Run each test
    if run_test "Login with valid credentials" test_login_valid; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Login with invalid credentials" test_login_invalid; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Login with missing fields" test_login_missing_fields; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Refresh token" test_refresh_token; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Refresh with invalid token" test_refresh_invalid_token; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get current user profile" test_get_profile; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Get profile without authentication" test_get_profile_unauthorized; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Logout" test_logout; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Login as instructor" test_login_instructor; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    if run_test "Concurrent login attempts" test_concurrent_logins; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    # Test rate limiting if enabled
    if [ "$RATE_LIMIT_TEST" = "true" ]; then
        if run_test "Authentication rate limiting" test_auth_rate_limit; then
            ((PASSED++))
        else
            ((FAILED++))
        fi
    fi
    
    # Generate report
    generate_report "Authentication API" $PASSED $FAILED
    
    # Cleanup
    cleanup_test_data
}

# Test: Authentication rate limiting
test_auth_rate_limit() {
    local auth_data=$(cat <<EOF
{
    "username": "$TEST_USER_STUDENT",
    "password": "$TEST_PASS_STUDENT",
    "grant_type": "password"
}
EOF
)
    
    local blocked_count=0
    local total_requests=20
    
    for i in $(seq 1 $total_requests); do
        local response=$(make_request "POST" "/auth/login" "$auth_data" 2>&1)
        local status=$?
        
        if [ $status -eq 429 ]; then
            ((blocked_count++))
        fi
        
        # Small delay
        sleep 0.1
    done
    
    if [ $blocked_count -gt 0 ]; then
        print_status "INFO" "Rate limit triggered after $((total_requests - blocked_count)) requests"
        return 0
    fi
    
    return 1
}

# Main execution
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    run_all_tests
fi