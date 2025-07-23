#!/bin/bash
# test_trac_endpoints.sh - Test Trac system endpoints

set -e

# Source configuration
TRAC_URL=${TRAC_URL:-"http://localhost:8000"}
VERBOSE=${VERBOSE:-false}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
log() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

verbose() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${YELLOW}[DEBUG]${NC} $1"
    fi
}

# Test function wrapper
test_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3
    local method=${4:-"GET"}
    
    log "Testing: $description"
    verbose "URL: $TRAC_URL$endpoint"
    
    response=$(curl -s -w "\n%{http_code}" -X "$method" "$TRAC_URL$endpoint" 2>/dev/null || true)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    verbose "Status: $http_code"
    
    if [[ "$http_code" == "$expected_status" ]]; then
        success "$description - Status: $http_code"
        return 0
    else
        error "$description - Expected: $expected_status, Got: $http_code"
        verbose "Response: $body"
        return 1
    fi
}

# Test content validation
test_content() {
    local endpoint=$1
    local search_string=$2
    local description=$3
    
    log "Testing content: $description"
    verbose "URL: $TRAC_URL$endpoint"
    
    response=$(curl -s "$TRAC_URL$endpoint" 2>/dev/null || true)
    
    if echo "$response" | grep -q "$search_string"; then
        success "$description - Found: '$search_string'"
        return 0
    else
        error "$description - Not found: '$search_string'"
        verbose "Response preview: $(echo "$response" | head -n 5)..."
        return 1
    fi
}

# Main test suite
run_tests() {
    local failed=0
    
    echo "===== Trac Endpoint Tests ====="
    echo "Target: $TRAC_URL"
    echo ""
    
    # Basic endpoints
    test_endpoint "/" "200" "Main page" || ((failed++))
    test_endpoint "/login" "200" "Login page" || ((failed++))
    test_endpoint "/wiki" "200" "Wiki main page" || ((failed++))
    test_endpoint "/timeline" "200" "Timeline" || ((failed++))
    test_endpoint "/roadmap" "200" "Roadmap" || ((failed++))
    test_endpoint "/browser" "200" "Repository browser" || ((failed++))
    test_endpoint "/query" "200" "Ticket query" || ((failed++))
    test_endpoint "/report" "200" "Reports" || ((failed++))
    test_endpoint "/search" "200" "Search page" || ((failed++))
    test_endpoint "/prefs" "302" "Preferences (redirect to login)" || ((failed++))
    
    # API endpoints
    test_endpoint "/jsonrpc" "405" "JSON-RPC endpoint (method not allowed)" || ((failed++))
    test_endpoint "/xmlrpc" "405" "XML-RPC endpoint (method not allowed)" || ((failed++))
    
    # Static resources
    test_endpoint "/chrome/common/css/trac.css" "200" "CSS resources" || ((failed++))
    test_endpoint "/chrome/common/js/trac.js" "200" "JavaScript resources" || ((failed++))
    
    # Content validation
    echo ""
    echo "===== Content Validation ====="
    test_content "/" "Trac" "Main page contains 'Trac'" || ((failed++))
    test_content "/wiki" "Wiki" "Wiki page contains 'Wiki'" || ((failed++))
    test_content "/timeline" "Timeline" "Timeline contains 'Timeline'" || ((failed++))
    
    # Health check
    echo ""
    echo "===== Health Check ====="
    test_endpoint "/health" "200" "Health check endpoint" || ((failed++))
    
    # Summary
    echo ""
    echo "===== Test Summary ====="
    total_tests=$((18))  # Update this when adding tests
    passed=$((total_tests - failed))
    
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}All tests passed! ($passed/$total_tests)${NC}"
        return 0
    else
        echo -e "${RED}$failed tests failed! ($passed/$total_tests passed)${NC}"
        return 1
    fi
}

# Run tests
run_tests