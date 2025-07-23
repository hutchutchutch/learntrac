#!/bin/bash
set -e

echo "================================================"
echo "LearnTrac Integrated Local Testing Script"
echo "================================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Parse command line arguments
USE_AWS_DB=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --aws-db)
            USE_AWS_DB=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --aws-db    Use AWS RDS instead of local PostgreSQL"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Clean up existing containers
echo "Cleaning up existing containers..."
docker-compose down -v 2>/dev/null || true
docker stop trac-local learntrac-api-local postgres-local redis-local 2>/dev/null || true
docker rm trac-local learntrac-api-local postgres-local redis-local 2>/dev/null || true
docker network rm learntrac-network 2>/dev/null || true

# Create .env file
echo ""
echo "Creating environment configuration..."

if [ "$USE_AWS_DB" = true ]; then
    print_warning "Using AWS RDS database - fetching credentials..."
    
    # Get AWS credentials
    DB_SECRET=$(aws secretsmanager get-secret-value \
        --secret-id hutch-learntrac-dev-db-credentials \
        --region us-east-2 \
        --query SecretString --output text)
    
    DB_USERNAME=$(echo $DB_SECRET | jq -r .username)
    DB_PASSWORD=$(echo $DB_SECRET | jq -r .password)
    DB_HOST=$(echo $DB_SECRET | jq -r .host)
    DB_NAME=$(echo $DB_SECRET | jq -r .dbname)
    REDIS_ENDPOINT="hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com"
    
    cat > .env << EOF
# AWS Cognito
COGNITO_USER_POOL_ID=us-east-2_IvxzMrWwg
COGNITO_CLIENT_ID=5adkv019v4rcu6o87ffg46ep02
COGNITO_DOMAIN=hutch-learntrac-dev-auth
AWS_REGION=us-east-2

# Database (AWS RDS)
DATABASE_URL_TRAC=postgres://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}
DATABASE_URL_API=postgresql+asyncpg://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}

# Redis (AWS ElastiCache)
REDIS_URL=redis://${REDIS_ENDPOINT}:6379

# Environment
ENVIRONMENT=local
BASE_URL=http://localhost:8001
EOF
    
    print_status "AWS credentials loaded"
else
    cat > .env << EOF
# AWS Cognito
COGNITO_USER_POOL_ID=us-east-2_IvxzMrWwg
COGNITO_CLIENT_ID=5adkv019v4rcu6o87ffg46ep02
COGNITO_DOMAIN=hutch-learntrac-dev-auth
AWS_REGION=us-east-2

# Environment
ENVIRONMENT=local
BASE_URL=http://localhost:8001
EOF
    
    print_status "Local environment configured"
fi

# Build and start containers
echo ""
echo "Building and starting containers..."

if [ "$USE_AWS_DB" = true ]; then
    # Run without local database services
    docker-compose up -d trac learntrac-api
else
    # Run with all services including local database
    docker-compose up -d
fi

# Wait for services to be healthy
echo ""
echo "Waiting for services to become healthy..."

# Function to check if service is healthy
check_health() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps | grep -q "$service.*healthy"; then
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    return 1
}

# Check each service
services_to_check="learntrac-api trac"
if [ "$USE_AWS_DB" = false ]; then
    services_to_check="postgres redis learntrac-api trac"
fi

for service in $services_to_check; do
    echo -n "Checking $service"
    if check_health $service; then
        print_status " $service is healthy"
    else
        print_error " $service failed to become healthy"
        echo ""
        echo "Container logs:"
        docker-compose logs $service
        exit 1
    fi
done

# Run integration tests
echo ""
echo "================================================"
echo "Running Integration Tests"
echo "================================================"
echo ""

# Test 1: Check if Trac can reach API
echo "1. Testing Trac → API communication:"
docker exec trac-local curl -s http://learntrac-api:8001/health | jq . || print_error "Failed to reach API from Trac"

# Test 2: Check if API can reach Trac
echo ""
echo "2. Testing API → Trac communication:"
docker exec learntrac-api-local curl -s http://trac:8000 > /dev/null && print_status "API can reach Trac" || print_error "Failed to reach Trac from API"

# Test 3: Test API endpoints from host
echo ""
echo "3. Testing API endpoints from host:"
curl -s http://localhost:8001/health | jq .
curl -s http://localhost:8001/api/learntrac/health | jq .

# Test 4: Test Trac from host
echo ""
echo "4. Testing Trac from host:"
curl -s -o /dev/null -w "Trac HTTP Status: %{http_code}\n" http://localhost:8000/

# Test 5: Check database connectivity
echo ""
echo "5. Testing database connectivity:"
if [ "$USE_AWS_DB" = true ]; then
    docker exec learntrac-api-local python -c "
import asyncio
import asyncpg
import os

async def test_db():
    db_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    try:
        conn = await asyncpg.connect(db_url)
        version = await conn.fetchval('SELECT version()')
        print(f'✓ Connected to PostgreSQL: {version.split(\",\")[0]}')
        await conn.close()
    except Exception as e:
        print(f'✗ Database connection failed: {e}')

asyncio.run(test_db())
"
else
    docker exec postgres-local pg_isready -U learntrac && print_status "Local PostgreSQL is ready"
fi

# Test 6: Check Redis connectivity
echo ""
echo "6. Testing Redis connectivity:"
if [ "$USE_AWS_DB" = true ]; then
    docker exec learntrac-api-local python -c "
import redis
import os

try:
    r = redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print('✓ Connected to Redis')
except Exception as e:
    print(f'✗ Redis connection failed: {e}')
"
else
    docker exec redis-local redis-cli ping && print_status "Local Redis is ready"
fi

# Display service URLs and logs
echo ""
echo "================================================"
echo "Services Running"
echo "================================================"
echo ""
echo "🌐 Service URLs:"
echo "   Trac Legacy:     http://localhost:8000"
echo "   LearnTrac API:   http://localhost:8001"
echo "   API Docs:        http://localhost:8001/docs"
echo ""
echo "🔍 Container Names:"
echo "   Trac:            trac-local"
echo "   LearnTrac API:   learntrac-api-local"
if [ "$USE_AWS_DB" = false ]; then
    echo "   PostgreSQL:      postgres-local"
    echo "   Redis:           redis-local"
fi
echo ""
echo "📋 Useful Commands:"
echo "   View logs:       docker-compose logs -f [service-name]"
echo "   Stop all:        docker-compose down"
echo "   Restart:         docker-compose restart [service-name]"
echo "   Shell access:    docker exec -it [container-name] /bin/bash"
echo ""
echo "🔐 Test Authentication:"
echo "   Trac login:      http://localhost:8000/login"
echo "   API auth test:   http://localhost:8001/docs (use 'Authorize' button)"
echo ""

# Show recent logs
echo "================================================"
echo "Recent Logs"
echo "================================================"
echo ""
echo "Trac logs:"
docker-compose logs --tail=5 trac
echo ""
echo "API logs:"
docker-compose logs --tail=5 learntrac-api

echo ""
print_status "All services are running and healthy!"