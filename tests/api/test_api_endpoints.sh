#!/bin/bash
# test_api_endpoints.sh - Comprehensive API endpoint tests

set -e

# Configuration
API_URL=${API_URL:-"http://localhost:8001"}
VERBOSE=${VERBOSE:-false}
AUTH_TOKEN=${AUTH_TOKEN:-""}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0

# Helper functions
log() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

verbose() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${YELLOW}[DEBUG]${NC} $1"
    fi
}

# Build auth header
get_auth_header() {
    if [ -n "$AUTH_TOKEN" ]; then
        echo "-H 'Authorization: Bearer $AUTH_TOKEN'"
    else
        echo ""
    fi
}

# Generic API test function
test_api() {
    local method=$1
    local endpoint=$2
    local expected_status=$3
    local description=$4
    local data=${5:-""}
    
    log "Testing: $description"
    verbose "Method: $method"
    verbose "URL: $API_URL$endpoint"
    
    # Build curl command
    cmd="curl -s -w '\n%{http_code}' -X $method"
    cmd="$cmd $(get_auth_header)"
    
    if [ "$method" != "GET" ] && [ -n "$data" ]; then
        cmd="$cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    
    cmd="$cmd '$API_URL$endpoint'"
    
    verbose "Command: $cmd"
    
    # Execute request
    response=$(eval "$cmd" 2>/dev/null || true)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    verbose "Status: $http_code"
    verbose "Response: $(echo "$body" | head -n 3)..."
    
    if [[ "$http_code" == "$expected_status" ]]; then
        success "$description - Status: $http_code"
        echo "$body"  # Return response body for further processing
        return 0
    else
        error "$description - Expected: $expected_status, Got: $http_code"
        verbose "Full response: $body"
        return 1
    fi
}

# Test health endpoints
test_health_endpoints() {
    echo ""
    echo "===== Health & Status Endpoints ====="
    
    test_api "GET" "/health" "200" "Health check"
    test_api "GET" "/api/v1/status" "200" "API status"
}

# Test authentication endpoints
test_auth_endpoints() {
    echo ""
    echo "===== Authentication Endpoints ====="
    
    test_api "GET" "/api/v1/auth/status" "401" "Auth status (no token)"
    test_api "POST" "/api/v1/auth/login" "422" "Login (no data)"
    test_api "POST" "/api/v1/auth/logout" "401" "Logout (no token)"
    test_api "POST" "/api/v1/auth/refresh" "401" "Refresh token (no token)"
}

# Test concept endpoints
test_concept_endpoints() {
    echo ""
    echo "===== Concept Management Endpoints ====="
    
    test_api "GET" "/api/v1/concepts" "200" "List concepts"
    test_api "GET" "/api/v1/concepts/1" "404" "Get concept (not found)"
    test_api "POST" "/api/v1/concepts" "401" "Create concept (unauthorized)"
    test_api "PUT" "/api/v1/concepts/1" "401" "Update concept (unauthorized)"
    test_api "DELETE" "/api/v1/concepts/1" "401" "Delete concept (unauthorized)"
    
    # Search and filter
    test_api "GET" "/api/v1/concepts?search=test" "200" "Search concepts"
    test_api "GET" "/api/v1/concepts?category=math" "200" "Filter by category"
    test_api "GET" "/api/v1/concepts?difficulty=beginner" "200" "Filter by difficulty"
}

# Test analytics endpoints
test_analytics_endpoints() {
    echo ""
    echo "===== Analytics Endpoints ====="
    
    test_api "GET" "/api/v1/analytics/progress" "401" "Progress analytics (unauthorized)"
    test_api "GET" "/api/v1/analytics/performance" "401" "Performance metrics (unauthorized)"
    test_api "GET" "/api/v1/analytics/insights" "401" "Learning insights (unauthorized)"
    test_api "GET" "/api/v1/analytics/trends" "401" "Trend analysis (unauthorized)"
}

# Test chat endpoints
test_chat_endpoints() {
    echo ""
    echo "===== Chat/AI Endpoints ====="
    
    test_api "POST" "/api/v1/chat" "401" "Chat completion (unauthorized)"
    test_api "GET" "/api/v1/chat/history" "401" "Chat history (unauthorized)"
    test_api "DELETE" "/api/v1/chat/history" "401" "Clear chat history (unauthorized)"
    
    # Chat with data (still should be unauthorized without token)
    local chat_data='{"message": "Hello, can you help me learn Python?"}'
    test_api "POST" "/api/v1/chat" "401" "Chat with message" "$chat_data"
}

# Test learning path endpoints
test_learning_endpoints() {
    echo ""
    echo "===== Learning Path Endpoints ====="
    
    test_api "GET" "/api/v1/learning/paths" "401" "List learning paths (unauthorized)"
    test_api "GET" "/api/v1/learning/paths/1" "401" "Get learning path (unauthorized)"
    test_api "POST" "/api/v1/learning/paths" "401" "Create learning path (unauthorized)"
    test_api "GET" "/api/v1/learning/recommendations" "401" "Get recommendations (unauthorized)"
    test_api "POST" "/api/v1/learning/progress" "401" "Update progress (unauthorized)"
}

# Test documentation endpoints
test_docs_endpoints() {
    echo ""
    echo "===== Documentation Endpoints ====="
    
    test_api "GET" "/docs" "200" "Swagger UI"
    test_api "GET" "/redoc" "200" "ReDoc"
    test_api "GET" "/openapi.json" "200" "OpenAPI schema"
}

# Test rate limiting
test_rate_limiting() {
    echo ""
    echo "===== Rate Limiting Tests ====="
    
    log "Testing rate limits (10 rapid requests)..."
    local rate_limited=false
    
    for i in {1..10}; do
        response=$(curl -s -w "\n%{http_code}" "$API_URL/api/v1/concepts" 2>/dev/null || true)
        http_code=$(echo "$response" | tail -n1)
        
        if [[ "$http_code" == "429" ]]; then
            rate_limited=true
            success "Rate limiting active (429 received on request $i)"
            break
        fi
    done
    
    if [ "$rate_limited" = false ]; then
        log "Rate limiting not triggered in 10 requests (may be disabled in test env)"
    fi
}

# Test CORS headers
test_cors() {
    echo ""
    echo "===== CORS Configuration ====="
    
    log "Testing CORS headers..."
    
    response=$(curl -s -I -X OPTIONS \
        -H "Origin: http://example.com" \
        -H "Access-Control-Request-Method: GET" \
        "$API_URL/api/v1/concepts" 2>/dev/null || true)
    
    if echo "$response" | grep -q "Access-Control-Allow-Origin"; then
        success "CORS headers present"
        verbose "$(echo "$response" | grep "Access-Control")"
    else
        error "CORS headers missing"
    fi
}

# Main test runner
run_all_tests() {
    echo "========================================="
    echo "LearnTrac API Endpoint Test Suite"
    echo "========================================="
    echo "API URL: $API_URL"
    echo "Auth Token: $([ -n "$AUTH_TOKEN" ] && echo "Provided" || echo "Not provided")"
    echo ""
    
    # Check if API is reachable
    if ! curl -s -f "$API_URL/health" > /dev/null 2>&1; then
        error "API is not reachable at $API_URL"
        exit 1
    fi
    
    # Run test suites
    test_health_endpoints
    test_auth_endpoints
    test_concept_endpoints
    test_analytics_endpoints
    test_chat_endpoints
    test_learning_endpoints
    test_docs_endpoints
    test_rate_limiting
    test_cors
    
    # Summary
    echo ""
    echo "========================================="
    echo "Test Summary"
    echo "========================================="
    echo -e "Passed: ${GREEN}$PASSED${NC}"
    echo -e "Failed: ${RED}$FAILED${NC}"
    echo -e "Total: $((PASSED + FAILED))"
    
    if [ $FAILED -eq 0 ]; then
        echo -e "\n${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}Some tests failed!${NC}"
        exit 1
    fi
}

# Run tests
run_all_tests