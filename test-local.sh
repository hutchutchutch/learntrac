#!/bin/bash

echo "🧪 Testing LearnTrac Docker Containers"
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test Trac endpoints
echo -e "\n📌 Testing Trac (Python 2.7) on port 8000:"
echo -n "  - Root page: "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200\|302"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

echo -n "  - Login page: "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login | grep -q "200"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

# Test API endpoints
echo -e "\n🚀 Testing LearnTrac API (Python 3.11) on port 8001:"
echo -n "  - Root endpoint: "
if curl -s http://localhost:8001/ | jq -e '.message' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

echo -n "  - Health check: "
if curl -s http://localhost:8001/health | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

echo -n "  - API health: "
if curl -s http://localhost:8001/api/learntrac/health | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

echo -n "  - Courses endpoint: "
if curl -s http://localhost:8001/api/learntrac/courses | jq -e '.courses | length > 0' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

echo -n "  - API documentation: "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/docs | grep -q "200"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

echo -e "\n✅ Testing complete!"