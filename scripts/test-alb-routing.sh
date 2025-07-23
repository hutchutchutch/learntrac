#!/bin/bash
# Test ALB routing rules

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_test() {
    echo -e "${BLUE}Testing: $1${NC}"
}

print_result() {
    if [ "$1" = "200" ]; then
        echo -e "${GREEN}✅ HTTP $1 - $2${NC}"
    else
        echo -e "${RED}❌ HTTP $1 - $2${NC}"
    fi
}

# Get ALB DNS
cd "$(dirname "$0")/../learntrac-infrastructure"
ALB_DNS=$(terraform output -raw alb_dns_name)

if [ -z "$ALB_DNS" ]; then
    echo -e "${RED}Could not get ALB DNS name${NC}"
    exit 1
fi

echo "========================================="
echo "Testing ALB Routing Rules"
echo "========================================="
echo ""
echo "ALB URL: http://$ALB_DNS"
echo ""

# Function to test endpoint
test_endpoint() {
    local path=$1
    local expected_service=$2
    
    print_test "$path"
    
    response=$(curl -s -w "\n%{http_code}" http://$ALB_DNS$path 2>/dev/null || echo "000")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    print_result "$http_code" "$expected_service"
    
    if [ "$http_code" = "200" ] && [ -n "$body" ]; then
        echo "   Response: $(echo $body | head -c 100)..."
    fi
    echo ""
}

echo "=== Testing Trac Routes ==="
test_endpoint "/trac/login" "Trac health check"
test_endpoint "/trac/" "Trac main page"
test_endpoint "/wiki/TestPage" "Trac wiki"
test_endpoint "/ticket/123" "Trac ticket"
test_endpoint "/timeline/" "Trac timeline"
test_endpoint "/browser/" "Trac browser"

echo "=== Testing LearnTrac API Routes ==="
test_endpoint "/api/learntrac/health" "LearnTrac health check"
test_endpoint "/api/learntrac/info" "LearnTrac info"
test_endpoint "/api/chat/test" "Chat API"
test_endpoint "/api/voice/test" "Voice API"
test_endpoint "/api/analytics/test" "Analytics API"

echo "=== Testing Static Asset Routes ==="
test_endpoint "/static/test.css" "Static CSS"
test_endpoint "/chrome/test.js" "Chrome JS"

echo "=== Testing Default Route ==="
test_endpoint "/" "Default response"

echo ""
echo "========================================="
echo "ALB Routing Test Complete"
echo "========================================="