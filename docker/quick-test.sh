#!/bin/bash

echo "Quick Local Test - LearnTrac Containers"
echo "======================================"
echo ""

# Stop any existing containers
echo "Cleaning up..."
docker stop trac-test learntrac-test 2>/dev/null || true
docker rm trac-test learntrac-test 2>/dev/null || true

# Create network
docker network create learntrac-test 2>/dev/null || true

# Run containers
echo "Starting containers..."
docker run -d --name trac-test --network learntrac-test -p 8000:8000 learntrac/trac:test
docker run -d --name learntrac-test --network learntrac-test -p 8001:8001 learntrac/api:test

echo "Waiting for services..."
sleep 10

# Test endpoints
echo ""
echo "Testing endpoints:"
echo "1. Trac: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)"
echo "2. API: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health)"
echo ""
echo "Services:"
echo "- Trac: http://localhost:8000"
echo "- API: http://localhost:8001/docs"
echo ""
echo "Stop with: docker stop trac-test learntrac-test"