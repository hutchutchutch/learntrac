#!/bin/bash

# Test script for API Gateway with Cognito Authorization
# This script demonstrates how to test the API Gateway endpoints with JWT tokens

# Configuration
API_GATEWAY_URL="${API_GATEWAY_URL:-https://your-api-id.execute-api.us-east-2.amazonaws.com/dev}"
COGNITO_DOMAIN="${COGNITO_DOMAIN:-hutch-learntrac-dev-auth}"
COGNITO_REGION="${AWS_REGION:-us-east-2}"
CLIENT_ID="${COGNITO_CLIENT_ID:-5adkv019v4rcu6o87ffg46ep02}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "API Gateway Test Script"
echo "======================="
echo ""

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local token=$3
    local data=$4
    
    echo -e "${YELLOW}Testing: ${method} ${endpoint}${NC}"
    
    if [ -z "$token" ]; then
        # Test without token
        if [ -z "$data" ]; then
            response=$(curl -s -X ${method} \
                "${API_GATEWAY_URL}${endpoint}" \
                -H "Content-Type: application/json" \
                -w "\nHTTP_STATUS:%{http_code}")
        else
            response=$(curl -s -X ${method} \
                "${API_GATEWAY_URL}${endpoint}" \
                -H "Content-Type: application/json" \
                -d "${data}" \
                -w "\nHTTP_STATUS:%{http_code}")
        fi
    else
        # Test with token
        if [ -z "$data" ]; then
            response=$(curl -s -X ${method} \
                "${API_GATEWAY_URL}${endpoint}" \
                -H "Authorization: Bearer ${token}" \
                -H "Content-Type: application/json" \
                -w "\nHTTP_STATUS:%{http_code}")
        else
            response=$(curl -s -X ${method} \
                "${API_GATEWAY_URL}${endpoint}" \
                -H "Authorization: Bearer ${token}" \
                -H "Content-Type: application/json" \
                -d "${data}" \
                -w "\nHTTP_STATUS:%{http_code}")
        fi
    fi
    
    # Extract HTTP status code
    http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_STATUS:/d')
    
    # Pretty print JSON if jq is available
    if command -v jq &> /dev/null; then
        body=$(echo "$body" | jq '.' 2>/dev/null || echo "$body")
    fi
    
    # Color code based on status
    if [[ $http_status -ge 200 && $http_status -lt 300 ]]; then
        echo -e "${GREEN}Status: ${http_status}${NC}"
    elif [[ $http_status -ge 400 && $http_status -lt 500 ]]; then
        echo -e "${YELLOW}Status: ${http_status}${NC}"
    else
        echo -e "${RED}Status: ${http_status}${NC}"
    fi
    
    echo "Response: $body"
    echo ""
}

# Test 1: Health check (public endpoint)
echo "1. Testing public endpoints (no auth required)"
echo "---------------------------------------------"
test_endpoint "GET" "/health" "" ""

# Test 2: Auth endpoints
echo "2. Testing auth endpoints"
echo "------------------------"
test_endpoint "POST" "/auth/login" "" '{"username":"test@example.com","password":"TestPass123!"}'

# Test 3: Protected endpoints without token (should fail)
echo "3. Testing protected endpoints without token (should return 401)"
echo "--------------------------------------------------------------"
test_endpoint "GET" "/api/v1/learning/courses" "" ""
test_endpoint "GET" "/api/v1/trac/tickets" "" ""

# Test 4: Get JWT token (manual step)
echo "4. JWT Token Test"
echo "-----------------"
echo "To test protected endpoints, you need a valid JWT token."
echo ""
echo "Option 1: Use Cognito Hosted UI"
echo "  URL: https://${COGNITO_DOMAIN}.auth.${COGNITO_REGION}.amazoncognito.com/login?client_id=${CLIENT_ID}&response_type=token&scope=openid+profile+email&redirect_uri=http://localhost:8000/auth/callback"
echo ""
echo "Option 2: Use AWS CLI to get token"
echo "  aws cognito-idp initiate-auth \\"
echo "    --client-id ${CLIENT_ID} \\"
echo "    --auth-flow USER_PASSWORD_AUTH \\"
echo "    --auth-parameters USERNAME=your-username,PASSWORD=your-password"
echo ""

# Test 5: Protected endpoints with token
echo "5. Testing protected endpoints with token"
echo "----------------------------------------"
echo "Set JWT_TOKEN environment variable and run:"
echo "  JWT_TOKEN='your-token-here' ./test-api-gateway.sh"
echo ""

if [ ! -z "$JWT_TOKEN" ]; then
    echo "Token detected, testing protected endpoints..."
    test_endpoint "GET" "/api/v1/learning/courses" "$JWT_TOKEN" ""
    test_endpoint "POST" "/api/v1/learning/courses" "$JWT_TOKEN" '{"title":"New Course","description":"Test course","duration":"4 weeks"}'
    test_endpoint "GET" "/api/v1/learning/courses/course-001" "$JWT_TOKEN" ""
    test_endpoint "GET" "/api/v1/trac/tickets" "$JWT_TOKEN" ""
fi

# Test 6: CORS preflight
echo "6. Testing CORS preflight requests"
echo "---------------------------------"
test_endpoint "OPTIONS" "/api/v1/learning/courses" "" ""

# Summary
echo "Test Summary"
echo "============"
echo "- Public endpoints should return 200"
echo "- Protected endpoints without token should return 401"
echo "- Protected endpoints with valid token should return 200"
echo "- OPTIONS requests should return 200 with CORS headers"
echo ""
echo "Note: Replace API_GATEWAY_URL with your actual API Gateway URL"
echo "      You can find it in Terraform output or AWS Console"