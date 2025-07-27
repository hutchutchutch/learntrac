#!/bin/bash

echo "1. Testing API connectivity from Trac container..."
docker exec trac-legacy curl -s http://learntrac-api:8001/api/trac/debug/ping | python -m json.tool

echo -e "\n2. Testing Cognito validation endpoint..."
docker exec trac-legacy curl -X POST http://learntrac-api:8001/api/trac/auth/validate-code \
  -H "Content-Type: application/json" \
  -d '{"code": "test-code", "redirect_uri": "http://localhost:8000/auth/callback"}' \
  | python -m json.tool

echo -e "\n3. Checking if API can reach Cognito..."
docker exec learntrac-api curl -s https://hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com/.well-known/openid-configuration | head -5