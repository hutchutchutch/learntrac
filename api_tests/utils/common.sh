#!/bin/bash

# Common utility functions for API testing

# Source configuration
source "$(dirname "$0")/../config.sh"

# Global variables for authentication
ACCESS_TOKEN=""
REFRESH_TOKEN=""
USER_ID=""

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✓ ${message}${NC}"
            ;;
        "FAIL")
            echo -e "${RED}✗ ${message}${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ ${message}${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠ ${message}${NC}"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Function to make API requests
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local headers=$4
    local output_file="${OUTPUT_DIR}/$(date +%s)_response.json"
    
    local url="${API_BASE_URL}${API_PATH}${endpoint}"
    
    # Build curl command
    local curl_cmd="curl $CURL_OPTIONS -X $method"
    
    # Add headers
    curl_cmd="$curl_cmd -H 'Content-Type: application/json'"
    
    if [ -n "$ACCESS_TOKEN" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $ACCESS_TOKEN'"
    fi
    
    if [ -n "$headers" ]; then
        curl_cmd="$curl_cmd $headers"
    fi
    
    # Add data for POST/PUT/PATCH requests
    if [ -n "$data" ] && [ "$method" != "GET" ] && [ "$method" != "DELETE" ]; then
        curl_cmd="$curl_cmd -d '$data'"
    fi
    
    # Add URL and output
    curl_cmd="$curl_cmd -w '\n%{http_code}' '$url'"
    
    if [ "$VERBOSE" = "true" ]; then
        print_status "INFO" "Request: $method $url"
        if [ -n "$data" ]; then
            print_status "INFO" "Data: $data"
        fi
    fi
    
    # Execute request
    local response=$(eval "$curl_cmd" 2>/dev/null)
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    # Save response if configured
    if [ "$SAVE_RESPONSES" = "true" ]; then
        echo "$body" > "$output_file"
    fi
    
    # Return both body and status code
    echo "$body"
    return $http_code
}

# Function to authenticate and get token
authenticate() {
    local username=${1:-$TEST_USER_STUDENT}
    local password=${2:-$TEST_PASS_STUDENT}
    
    print_status "INFO" "Authenticating as $username..."
    
    local auth_data=$(cat <<EOF
{
    "username": "$username",
    "password": "$password",
    "grant_type": "password"
}
EOF
)
    
    local response=$(make_request "POST" "/auth/login" "$auth_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token')
        REFRESH_TOKEN=$(echo "$response" | jq -r '.refresh_token')
        USER_ID=$(echo "$response" | jq -r '.user.id')
        
        if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
            print_status "SUCCESS" "Authentication successful"
            export ACCESS_TOKEN
            export REFRESH_TOKEN
            export USER_ID
            return 0
        fi
    fi
    
    print_status "FAIL" "Authentication failed (HTTP $status)"
    return 1
}

# Function to refresh token
refresh_token() {
    print_status "INFO" "Refreshing access token..."
    
    local refresh_data=$(cat <<EOF
{
    "refresh_token": "$REFRESH_TOKEN"
}
EOF
)
    
    local response=$(make_request "POST" "/auth/refresh" "$refresh_data")
    local status=$?
    
    if [ $status -eq 200 ]; then
        ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token')
        if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
            print_status "SUCCESS" "Token refreshed successfully"
            export ACCESS_TOKEN
            return 0
        fi
    fi
    
    print_status "FAIL" "Token refresh failed (HTTP $status)"
    return 1
}

# Function to validate JSON response
validate_json() {
    local response=$1
    local expected_fields=$2
    
    # Check if response is valid JSON
    if ! echo "$response" | jq . >/dev/null 2>&1; then
        print_status "FAIL" "Invalid JSON response"
        return 1
    fi
    
    # Check for expected fields
    if [ -n "$expected_fields" ]; then
        for field in $expected_fields; do
            local value=$(echo "$response" | jq -r ".$field" 2>/dev/null)
            if [ -z "$value" ] || [ "$value" = "null" ]; then
                print_status "FAIL" "Missing expected field: $field"
                return 1
            fi
        done
    fi
    
    return 0
}

# Function to run a test case
run_test() {
    local test_name=$1
    local test_function=$2
    
    echo ""
    echo -e "${BLUE}Running test: ${test_name}${NC}"
    echo "----------------------------------------"
    
    # Run the test
    if $test_function; then
        print_status "SUCCESS" "$test_name passed"
        return 0
    else
        print_status "FAIL" "$test_name failed"
        return 1
    fi
}

# Function to generate test report
generate_report() {
    local test_suite=$1
    local passed=$2
    local failed=$3
    local total=$((passed + failed))
    
    echo ""
    echo "========================================"
    echo -e "${BLUE}Test Suite: ${test_suite}${NC}"
    echo "========================================"
    echo -e "Total Tests: ${total}"
    echo -e "Passed: ${GREEN}${passed}${NC}"
    echo -e "Failed: ${RED}${failed}${NC}"
    
    if [ $failed -eq 0 ]; then
        echo -e "\n${GREEN}All tests passed!${NC}"
    else
        echo -e "\n${RED}Some tests failed!${NC}"
    fi
    echo "========================================"
}

# Function to clean up test data
cleanup_test_data() {
    print_status "INFO" "Cleaning up test data..."
    
    # Logout to invalidate tokens
    if [ -n "$ACCESS_TOKEN" ]; then
        make_request "POST" "/auth/logout" "" >/dev/null 2>&1
    fi
    
    # Clear tokens
    ACCESS_TOKEN=""
    REFRESH_TOKEN=""
    USER_ID=""
}

# Function to wait with retry
retry_request() {
    local max_attempts=$RETRY_COUNT
    local attempt=1
    local wait_time=$RETRY_DELAY
    
    while [ $attempt -le $max_attempts ]; do
        if "$@"; then
            return 0
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            print_status "WARN" "Attempt $attempt failed, retrying in ${wait_time}s..."
            sleep $wait_time
        fi
        
        ((attempt++))
    done
    
    return 1
}

# Function to test rate limiting
test_rate_limit() {
    local endpoint=$1
    local limit=$2
    local count=0
    local blocked=0
    
    print_status "INFO" "Testing rate limit on $endpoint (limit: $limit)..."
    
    for i in $(seq 1 $((limit + 10))); do
        local response=$(make_request "GET" "$endpoint" 2>&1)
        local status=$?
        
        if [ $status -eq 429 ]; then
            ((blocked++))
        fi
        
        ((count++))
        
        # Small delay to avoid overwhelming
        sleep 0.1
    done
    
    if [ $blocked -gt 0 ]; then
        print_status "SUCCESS" "Rate limiting working: $blocked requests blocked"
        return 0
    else
        print_status "FAIL" "Rate limiting not working properly"
        return 1
    fi
}

# Function to upload file
upload_file() {
    local endpoint=$1
    local file_path=$2
    local field_name=${3:-"file"}
    
    local url="${API_BASE_URL}${API_PATH}${endpoint}"
    
    local curl_cmd="curl $CURL_OPTIONS -X POST"
    curl_cmd="$curl_cmd -H 'Authorization: Bearer $ACCESS_TOKEN'"
    curl_cmd="$curl_cmd -F '${field_name}=@${file_path}'"
    curl_cmd="$curl_cmd -w '\n%{http_code}' '$url'"
    
    local response=$(eval "$curl_cmd" 2>/dev/null)
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    echo "$body"
    return $http_code
}

# Function to measure response time
measure_response_time() {
    local method=$1
    local endpoint=$2
    
    local start_time=$(date +%s.%N)
    make_request "$method" "$endpoint" >/dev/null 2>&1
    local end_time=$(date +%s.%N)
    
    local response_time=$(echo "$end_time - $start_time" | bc)
    echo "$response_time"
}

# Export functions
export -f print_status
export -f make_request
export -f authenticate
export -f refresh_token
export -f validate_json
export -f run_test
export -f generate_report
export -f cleanup_test_data
export -f retry_request
export -f test_rate_limit
export -f upload_file
export -f measure_response_time