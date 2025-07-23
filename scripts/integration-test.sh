#!/bin/bash
# integration-test.sh - Run integration tests for LearnTrac

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL=${TEST_API_URL:-"http://localhost:8001"}
TRAC_URL=${TEST_TRAC_URL:-"http://localhost:8000"}
MAX_RETRIES=30
RETRY_DELAY=2

# Helper functions
echo_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local retries=0
    
    echo_info "Waiting for $service_name to be ready at $url..."
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -s -f "$url/health" > /dev/null 2>&1; then
            echo_success "$service_name is ready!"
            return 0
        fi
        
        retries=$((retries + 1))
        echo_info "Attempt $retries/$MAX_RETRIES - $service_name not ready yet..."
        sleep $RETRY_DELAY
    done
    
    echo_error "$service_name failed to start after $MAX_RETRIES attempts"
    return 1
}

# Test API endpoints
test_api_endpoints() {
    echo_info "Testing API endpoints..."
    
    # Test health endpoint
    echo_info "Testing /health endpoint..."
    if curl -s -f "$API_URL/health" | grep -q "ok"; then
        echo_success "Health endpoint OK"
    else
        echo_error "Health endpoint failed"
        return 1
    fi
    
    # Test API docs
    echo_info "Testing /docs endpoint..."
    if curl -s -f "$API_URL/docs" > /dev/null 2>&1; then
        echo_success "API docs endpoint OK"
    else
        echo_error "API docs endpoint failed"
        return 1
    fi
    
    # Test main API endpoints
    endpoints=("/api/v1/concepts" "/api/v1/analytics/progress" "/api/v1/auth/status")
    
    for endpoint in "${endpoints[@]}"; do
        echo_info "Testing $endpoint..."
        response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint" 2>/dev/null || true)
        http_code=$(echo "$response" | tail -n1)
        
        if [[ "$http_code" == "200" ]] || [[ "$http_code" == "401" ]]; then
            echo_success "$endpoint returned $http_code (expected)"
        else
            echo_error "$endpoint returned unexpected status: $http_code"
            return 1
        fi
    done
}

# Test Trac endpoints
test_trac_endpoints() {
    echo_info "Testing Trac endpoints..."
    
    # Test Trac main page
    echo_info "Testing Trac main page..."
    if curl -s -f "$TRAC_URL" | grep -q "Trac"; then
        echo_success "Trac main page OK"
    else
        echo_error "Trac main page failed"
        return 1
    fi
    
    # Test Trac login page
    echo_info "Testing Trac login page..."
    if curl -s -f "$TRAC_URL/login" > /dev/null 2>&1; then
        echo_success "Trac login page OK"
    else
        echo_error "Trac login page failed"
        return 1
    fi
}

# Test container connectivity
test_container_connectivity() {
    echo_info "Testing container connectivity..."
    
    # Check if API can reach Trac (via host.docker.internal)
    echo_info "Testing API -> Trac connectivity..."
    docker-compose -f docker-compose.test.yml exec -T api curl -s -f "http://host.docker.internal:8000" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo_success "API can reach Trac"
    else
        echo_error "API cannot reach Trac"
        return 1
    fi
}

# Run database connectivity test
test_database_connectivity() {
    echo_info "Testing database connectivity..."
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        echo_error ".env file not found. Please create it from .env.template"
        return 1
    fi
    
    # Source .env file
    source .env
    
    # Test database connection from API container
    echo_info "Testing database connection from API container..."
    docker-compose -f docker-compose.test.yml exec -T api python -c "
import os
import asyncpg
import asyncio

async def test_db():
    try:
        conn = await asyncpg.connect(os.environ.get('DATABASE_URL', '').replace('postgresql+asyncpg://', 'postgresql://'))
        await conn.fetchval('SELECT 1')
        await conn.close()
        print('Database connection successful')
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

asyncio.run(test_db())
" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo_success "Database connectivity OK"
    else
        echo_error "Database connectivity failed"
        return 1
    fi
}

# Main test execution
main() {
    echo_info "Starting integration tests..."
    
    # Check if docker-compose file exists
    if [ ! -f docker-compose.test.yml ]; then
        echo_error "docker-compose.test.yml not found"
        exit 1
    fi
    
    # Wait for services to be ready
    wait_for_service "$API_URL" "API" || exit 1
    wait_for_service "$TRAC_URL" "Trac" || exit 1
    
    # Run tests
    test_api_endpoints || exit 1
    test_trac_endpoints || exit 1
    test_container_connectivity || exit 1
    test_database_connectivity || exit 1
    
    echo_success "All integration tests passed!"
}

# Run main function
main "$@"