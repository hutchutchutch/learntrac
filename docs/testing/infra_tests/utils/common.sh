#!/bin/bash
# Common utilities for infrastructure tests

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test result tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $*"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $*"
}

# Test execution functions
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    log_info "Running test: $test_name"
    
    if eval "$test_command"; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_success "$test_name"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "$test_name"
        return 1
    fi
}

skip_test() {
    local test_name="$1"
    local reason="$2"
    
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    log_skip "$test_name - Reason: $reason"
}

# AWS CLI helpers
aws_describe_resource() {
    local service="$1"
    local command="$2"
    local resource_id="$3"
    local jq_filter="${4:-.}"
    
    aws "$service" "$command" --region "$AWS_REGION" ${resource_id:+--$resource_id} 2>/dev/null | jq -r "$jq_filter"
}

# Connectivity test helpers
test_tcp_connectivity() {
    local host="$1"
    local port="$2"
    local timeout="${3:-5}"
    
    timeout "$timeout" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null
}

# PostgreSQL test helpers
test_postgres_connection() {
    local endpoint="$1"
    local port="$2"
    local database="$3"
    local username="$4"
    local password="$5"
    
    PGPASSWORD="$password" psql \
        -h "$endpoint" \
        -p "$port" \
        -U "$username" \
        -d "$database" \
        -c "SELECT version();" \
        -t -A 2>/dev/null
}

check_postgres_table_exists() {
    local endpoint="$1"
    local database="$2"
    local schema="$3"
    local table="$4"
    local username="$5"
    local password="$6"
    
    local query="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$schema' AND table_name='$table';"
    
    local count=$(PGPASSWORD="$password" psql \
        -h "$endpoint" \
        -p "$RDS_PORT" \
        -U "$username" \
        -d "$database" \
        -t -A \
        -c "$query" 2>/dev/null)
    
    [ "$count" = "1" ]
}

# Redis test helpers
test_redis_connection() {
    local endpoint="$1"
    local port="$2"
    local auth_token="$3"
    
    if [ -n "$auth_token" ]; then
        redis-cli -h "$endpoint" -p "$port" -a "$auth_token" --no-auth-warning ping 2>/dev/null
    else
        redis-cli -h "$endpoint" -p "$port" ping 2>/dev/null
    fi
}

# HTTP test helpers
test_http_endpoint() {
    local url="$1"
    local expected_status="${2:-200}"
    local auth_header="$3"
    
    local curl_opts="-s -o /dev/null -w %{http_code}"
    if [ -n "$auth_header" ]; then
        curl_opts="$curl_opts -H 'Authorization: $auth_header'"
    fi
    
    local status=$(curl $curl_opts "$url")
    [ "$status" = "$expected_status" ]
}

# JSON validation helpers
validate_json_file() {
    local file="$1"
    
    if [ ! -f "$file" ]; then
        return 1
    fi
    
    jq empty "$file" 2>/dev/null
}

# Terraform helpers
validate_terraform_config() {
    local tf_dir="$1"
    
    cd "$tf_dir" && terraform validate -no-color
}

check_terraform_resource() {
    local tf_dir="$1"
    local resource_type="$2"
    local resource_name="$3"
    
    cd "$tf_dir" && terraform state show "${resource_type}.${resource_name}" >/dev/null 2>&1
}

# Start test suite
start_test_suite() {
    local suite_name="$1"
    echo
    echo "========================================="
    echo "Running Test Suite: $suite_name"
    echo "========================================="
    echo
}

# Test summary
print_test_summary() {
    echo
    echo "========================================="
    echo "Test Summary"
    echo "========================================="
    echo "Total tests run: $TESTS_RUN"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    echo -e "Skipped: ${YELLOW}$TESTS_SKIPPED${NC}"
    echo "========================================="
    
    if [ $TESTS_FAILED -eq 0 ] && [ $TESTS_RUN -gt 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    elif [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}Some tests failed!${NC}"
        return 1
    else
        echo -e "${YELLOW}No tests were run!${NC}"
        return 2
    fi
}

# Retry mechanism
retry_with_backoff() {
    local max_attempts="${1:-3}"
    local delay="${2:-1}"
    shift 2
    local command=("$@")
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if "${command[@]}"; then
            return 0
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            log_warning "Attempt $attempt failed. Retrying in ${delay}s..."
            sleep "$delay"
            delay=$((delay * 2))
        fi
        
        attempt=$((attempt + 1))
    done
    
    return 1
}

# Export all functions
export -f log_info log_success log_error log_warning log_skip
export -f run_test skip_test
export -f aws_describe_resource
export -f test_tcp_connectivity test_postgres_connection check_postgres_table_exists
export -f test_redis_connection test_http_endpoint
export -f validate_json_file validate_terraform_config check_terraform_resource
export -f print_test_summary retry_with_backoff