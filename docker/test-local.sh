#!/bin/bash
set -e

echo "================================================"
echo "LearnTrac Local Docker Testing Script"
echo "================================================"

# Get AWS credentials
echo "Fetching AWS credentials..."
export COGNITO_USER_POOL_ID="us-east-2_IvxzMrWwg"
export COGNITO_CLIENT_ID="5adkv019v4rcu6o87ffg46ep02"
export COGNITO_DOMAIN="hutch-learntrac-dev-auth"
export AWS_REGION="us-east-2"

# Get database credentials
DB_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id hutch-learntrac-dev-db-credentials \
  --region us-east-2 \
  --query SecretString --output text)

export DB_USERNAME=$(echo $DB_SECRET | jq -r .username)
export DB_PASSWORD=$(echo $DB_SECRET | jq -r .password)
export DB_HOST=$(echo $DB_SECRET | jq -r .host)
export DB_NAME=$(echo $DB_SECRET | jq -r .dbname)
export REDIS_ENDPOINT="hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com"

echo "✓ AWS credentials loaded"

# Create .env file for docker-compose
cat > .env << EOF
# AWS Cognito
COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}
COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
COGNITO_DOMAIN=${COGNITO_DOMAIN}
COGNITO_POOL_ID=${COGNITO_USER_POOL_ID}
AWS_REGION=${AWS_REGION}

# Database
DATABASE_URL_TRAC=postgres://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}
DATABASE_URL_API=postgresql+asyncpg://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}

# Redis
REDIS_URL=redis://${REDIS_ENDPOINT}:6379

# Environment
ENVIRONMENT=local
BASE_URL=http://localhost:8001
EOF

echo "✓ Environment file created"

# Clean up any existing containers
echo ""
echo "Cleaning up existing containers..."
docker stop trac-test learntrac-test 2>/dev/null || true
docker rm trac-test learntrac-test 2>/dev/null || true
docker network rm learntrac-test 2>/dev/null || true

# Create network
echo ""
echo "Creating Docker network..."
docker network create learntrac-test

# Build images
echo ""
echo "Building Docker images..."
echo "Building Trac image..."
docker build -t learntrac/trac:test ./trac

echo ""
echo "Building LearnTrac API image..."
docker build -t learntrac/api:test ./learntrac

# Run containers
echo ""
echo "Starting containers..."

# Start Trac
echo "Starting Trac container..."
docker run -d \
  --name trac-test \
  --network learntrac-test \
  -p 8000:8000 \
  -e TRAC_ENV=/var/trac/projects \
  -e DATABASE_URL="postgres://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}" \
  -e COGNITO_DOMAIN="${COGNITO_DOMAIN}" \
  -e COGNITO_CLIENT_ID="${COGNITO_CLIENT_ID}" \
  -e AWS_REGION="${AWS_REGION}" \
  -e COGNITO_USER_POOL_ID="${COGNITO_USER_POOL_ID}" \
  learntrac/trac:test

# Start LearnTrac API
echo "Starting LearnTrac API container..."
docker run -d \
  --name learntrac-test \
  --network learntrac-test \
  -p 8001:8001 \
  -e ENVIRONMENT=local \
  -e DATABASE_URL="postgresql+asyncpg://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}" \
  -e REDIS_URL="redis://${REDIS_ENDPOINT}:6379" \
  -e COGNITO_POOL_ID="${COGNITO_USER_POOL_ID}" \
  -e COGNITO_CLIENT_ID="${COGNITO_CLIENT_ID}" \
  -e COGNITO_DOMAIN="${COGNITO_DOMAIN}" \
  -e AWS_REGION="${AWS_REGION}" \
  -e BASE_URL="http://localhost:8001" \
  learntrac/api:test

# Wait for containers to start
echo ""
echo "Waiting for containers to start..."
sleep 10

# Check container status
echo ""
echo "Container Status:"
docker ps --filter name=trac-test --filter name=learntrac-test --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check health
echo ""
echo "Checking container health..."
echo -n "Trac health: "
docker inspect trac-test --format='{{.State.Health.Status}}' || echo "No health check"
echo -n "LearnTrac API health: "
docker inspect learntrac-test --format='{{.State.Health.Status}}' || echo "No health check"

# Test endpoints
echo ""
echo "================================================"
echo "Testing Endpoints"
echo "================================================"

echo ""
echo "1. Testing Trac (http://localhost:8000/):"
curl -s -o /dev/null -w "   Status: %{http_code}\n" http://localhost:8000/ || echo "   Failed to connect"

echo ""
echo "2. Testing LearnTrac API Root (http://localhost:8001/):"
curl -s http://localhost:8001/ | jq . || echo "   Failed to connect"

echo ""
echo "3. Testing LearnTrac Health (http://localhost:8001/health):"
curl -s http://localhost:8001/health | jq . || echo "   Failed to connect"

echo ""
echo "4. Testing LearnTrac API Health (http://localhost:8001/api/learntrac/health):"
curl -s http://localhost:8001/api/learntrac/health | jq . || echo "   Failed to connect"

echo ""
echo "5. Testing LearnTrac Courses (http://localhost:8001/api/learntrac/courses):"
curl -s http://localhost:8001/api/learntrac/courses | jq . || echo "   Failed to connect"

# Show logs
echo ""
echo "================================================"
echo "Container Logs (last 10 lines each)"
echo "================================================"

echo ""
echo "Trac logs:"
docker logs trac-test --tail 10

echo ""
echo "LearnTrac API logs:"
docker logs learntrac-test --tail 10

echo ""
echo "================================================"
echo "Test Summary"
echo "================================================"
echo "Trac URL: http://localhost:8000"
echo "LearnTrac API URL: http://localhost:8001"
echo "API Documentation: http://localhost:8001/docs"
echo ""
echo "To view logs: docker logs -f [trac-test|learntrac-test]"
echo "To stop: docker stop trac-test learntrac-test"
echo "To clean up: docker rm trac-test learntrac-test && docker network rm learntrac-test"
echo ""
echo "Next steps:"
echo "1. Test Cognito login flow at http://localhost:8000/login"
echo "2. Test API authentication at http://localhost:8001/docs"
echo "3. If everything works, push images to ECR"