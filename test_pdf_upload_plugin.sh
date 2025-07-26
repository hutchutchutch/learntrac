#!/bin/bash

# Script to test the PDF upload plugin in Docker containers
# This will spin up both Trac and Learning Service with console logging

echo "=========================================="
echo "PDF Upload Plugin Test"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    log_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        log_info "Please edit .env file with your configuration"
        exit 1
    else
        log_error ".env.example not found. Creating basic .env file..."
        cat > .env << EOF
# Database Configuration
DB_USER=learntrac
DB_PASSWORD=learntrac_password
RDS_ENDPOINT=host.docker.internal
DB_NAME=learntrac

# Neo4j Configuration
NEO4J_URI=bolt://neo4j-dev:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Redis Configuration
ELASTICACHE_ENDPOINT=redis-dev

# API Keys
OPENAI_API_KEY=your-openai-key-here

# Ports
TRAC_PORT=8080
API_PORT=8001

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG
EOF
        log_warning "Basic .env created. Please add your API keys."
    fi
fi

# Create necessary directories
log_info "Creating necessary directories..."
mkdir -p logs/trac logs/api
mkdir -p docker/trac/plugins

# Copy the PDF upload plugin to the Trac plugins directory
log_info "Copying PDF upload plugin to Docker volume..."
cp -r plugins/pdfuploadmacro docker/trac/plugins/

# Create a test script to verify API endpoints
cat > check_endpoints.sh << 'EOF'
#!/bin/bash

echo "Checking API endpoints..."
echo ""

# Check Learning Service API
echo "1. Learning Service API (http://localhost:8001):"
curl -s -o /dev/null -w "   Status: %{http_code}\n" http://localhost:8001/health || echo "   Status: Connection failed"
curl -s http://localhost:8001/docs > /dev/null && echo "   Docs: Available at http://localhost:8001/docs" || echo "   Docs: Not available"

echo ""

# Check Trac Service
echo "2. Trac Service (http://localhost:8080):"
curl -s -o /dev/null -w "   Status: %{http_code}\n" http://localhost:8080 || echo "   Status: Connection failed"

echo ""

# Check Trac LearnTrac endpoint
echo "3. Trac LearnTrac Upload Endpoint:"
curl -s -o /dev/null -w "   Status: %{http_code}\n" http://localhost:8080/learntrac/upload || echo "   Status: Connection failed"

echo ""

# Check Neo4j (if running in development profile)
echo "4. Neo4j Browser (http://localhost:7474):"
curl -s -o /dev/null -w "   Status: %{http_code}\n" http://localhost:7474 || echo "   Status: Not running (development profile only)"

echo ""
EOF

chmod +x check_endpoints.sh

# Stop any existing containers
log_info "Stopping existing containers..."
docker-compose down

# Start containers with development profile
log_info "Starting containers with development profile..."
log_info "This includes local Neo4j and Redis for testing"

# Build and start in detached mode first
docker-compose --profile development build

log_info "Starting services..."
docker-compose --profile development up -d

# Wait for services to be ready
log_info "Waiting for services to start..."
sleep 10

# Check if containers are running
log_info "Checking container status..."
docker-compose ps

# Follow logs in a new way that shows both containers
log_info "Starting log monitoring..."
echo ""
echo "=========================================="
echo "Container Logs (Ctrl+C to stop)"
echo "=========================================="

# Create a script to install the plugin in Trac container
log_info "Installing PDF upload plugin in Trac container..."
docker exec -it trac-service bash -c "cd /app/plugins/pdfuploadmacro && python setup.py install" || log_warning "Plugin installation needs manual intervention"

# Check endpoints in background
(sleep 15 && echo "" && echo "========================================" && echo "Endpoint Status Check:" && echo "========================================" && ./check_endpoints.sh && echo "========================================" && echo "") &

# Show logs from both containers
docker-compose --profile development logs -f --tail=50

# Cleanup function
cleanup() {
    echo ""
    log_info "Stopping containers..."
    docker-compose down
    rm -f check_endpoints.sh
    exit 0
}

# Set trap for cleanup
trap cleanup EXIT INT TERM