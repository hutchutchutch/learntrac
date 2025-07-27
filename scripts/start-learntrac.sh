#!/bin/bash
# Start LearnTrac with Cognito Authentication
# This script starts both the Learning API and Trac containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NETWORK_NAME="learntrac-network"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting LearnTrac with Cognito Auth${NC}"
echo -e "${GREEN}========================================${NC}"

# Change to project root
cd "$PROJECT_ROOT"

# Function to check if container is running
container_is_running() {
    docker ps --format "table {{.Names}}" | grep -q "^$1$"
}

# Function to wait for service to be healthy
wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for $service_name to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $service_name is ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ $service_name failed to start after $max_attempts attempts${NC}"
    return 1
}

# Step 1: Create network if it doesn't exist
echo -e "\n${YELLOW}Step 1: Setting up Docker network...${NC}"
if ! docker network inspect $NETWORK_NAME >/dev/null 2>&1; then
    docker network create $NETWORK_NAME
    echo -e "${GREEN}✓ Created network: $NETWORK_NAME${NC}"
else
    echo -e "${GREEN}✓ Network already exists: $NETWORK_NAME${NC}"
fi

# Step 2: Stop any existing containers
echo -e "\n${YELLOW}Step 2: Cleaning up existing containers...${NC}"
for container in learning-service trac-service; do
    if container_is_running $container; then
        echo "Stopping $container..."
        docker stop $container >/dev/null 2>&1 || true
    fi
    if docker ps -a --format "table {{.Names}}" | grep -q "^$container$"; then
        echo "Removing $container..."
        docker rm $container >/dev/null 2>&1 || true
    fi
done
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Step 3: Using RDS PostgreSQL
echo -e "\n${YELLOW}Step 3: Using AWS RDS PostgreSQL...${NC}"
# Load environment variables if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
    echo -e "${GREEN}✓ Loaded environment variables${NC}"
fi

# Use RDS connection string
RDS_DATABASE_URL="${DATABASE_URL_API_AWS}"
echo -e "${GREEN}✓ Using RDS PostgreSQL instance${NC}"

# Step 4: Redis removed - no longer needed
echo -e "\n${YELLOW}Step 4: Redis removed - skipping...${NC}"

# Step 5: Start Learning API Service
echo -e "\n${YELLOW}Step 5: Starting Learning API Service (Python 3.11)...${NC}"

# Check if we have the image
if ! docker images | grep -q "learntrac-learning-service"; then
    echo -e "${YELLOW}Building learning service image...${NC}"
    docker build -t learntrac-learning-service:latest -f learntrac-api/Dockerfile learntrac-api/
fi

docker run -d \
    --name learning-service \
    --network $NETWORK_NAME \
    -p 8001:8001 \
    -e DATABASE_URL="$RDS_DATABASE_URL" \
    -e NEO4J_URI="${NEO4J_URI:-}" \
    -e NEO4J_USERNAME="${NEO4J_USERNAME:-}" \
    -e NEO4J_PASSWORD="${NEO4J_PASSWORD:-}" \
    -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    -e COGNITO_REGION="us-east-2" \
    -e COGNITO_DOMAIN="hutch-learntrac-dev-auth" \
    -e COGNITO_CLIENT_ID="5adkv019v4rcu6o87ffg46ep02" \
    -e COGNITO_USER_POOL_ID="us-east-2_IvxzMrWwg" \
    -e TRAC_BASE_URL="http://localhost:8000" \
    -e API_BASE_URL="http://localhost:8001" \
    -e ALLOWED_ORIGINS="http://localhost:8000,http://localhost:8001" \
    learntrac-learning-service:latest

# Wait for Learning API to be ready
wait_for_service "Learning API" "http://localhost:8001/health"

# Step 6: Build and prepare Trac plugins
echo -e "\n${YELLOW}Step 6: Building Trac plugins...${NC}"

# Build AuthProxy plugin
if [ -d "plugins/authproxy" ]; then
    echo "Building AuthProxy plugin..."
    cd plugins/authproxy
    python setup.py bdist_egg
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}✓ AuthProxy plugin built${NC}"
fi

# Build PDF upload plugin
if [ -d "plugins/pdfuploadmacro" ]; then
    echo "Building PDF upload plugin..."
    cd plugins/pdfuploadmacro
    python setup.py bdist_egg
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}✓ PDF upload plugin built${NC}"
fi

# Step 7: Start Trac Service
echo -e "\n${YELLOW}Step 7: Starting Trac Service (Python 2.7)...${NC}"

# Check if we have the Trac image
if ! docker images | grep -q "learntrac-trac"; then
    echo -e "${YELLOW}Building Trac image...${NC}"
    docker build -t learntrac-trac:latest -f trac-legacy/Dockerfile trac-legacy/
fi

# Create Trac init script
cat > /tmp/init-trac.sh << 'EOF'
#!/bin/bash
set -e

echo "Initializing Trac environment..."

# Install dependencies
pip install --quiet trac==1.4.3 PyJWT==1.7.1 cryptography==2.8

# Create Trac environment if it doesn't exist
if [ ! -f "/var/trac/projects/VERSION" ]; then
    trac-admin /var/trac/projects initenv "LearnTrac" "sqlite:db/trac.db"
fi

# Configure Trac
cat > /var/trac/projects/conf/trac.ini << 'EOFINI'
[trac]
database = sqlite:db/trac.db
base_url = http://localhost:8000

[project]
name = LearnTrac
descr = Learning Management System with Trac

[components]
authproxy.* = enabled
trac.web.auth.* = disabled
pdfuploadmacro.* = enabled

[authproxy]
service_url = http://learning-service:8001

[attachment]
max_size = 262144
render_unsafe_content = false

[logging]
log_file = trac.log
log_level = INFO
log_type = file
EOFINI

# Install plugins if mounted
if [ -f "/plugins/authproxy/dist/*.egg" ]; then
    easy_install /plugins/authproxy/dist/*.egg 2>/dev/null || true
fi
if [ -f "/plugins/pdfuploadmacro/dist/*.egg" ]; then
    easy_install /plugins/pdfuploadmacro/dist/*.egg 2>/dev/null || true
fi

# Set permissions
chmod -R 777 /var/trac/projects

# Start Trac
echo "Starting Trac on port 8000..."
exec tracd --port 8000 --base-path=/trac /var/trac/projects
EOF

chmod +x /tmp/init-trac.sh

docker run -d \
    --name trac-service \
    --network $NETWORK_NAME \
    -p 8000:8000 \
    -v "$(pwd)/plugins/authproxy:/plugins/authproxy:ro" \
    -v "$(pwd)/plugins/pdfuploadmacro:/plugins/pdfuploadmacro:ro" \
    -v "/tmp/init-trac.sh:/init-trac.sh:ro" \
    -v "trac-data:/var/trac/projects" \
    --entrypoint /bin/bash \
    python:2.7 \
    /init-trac.sh

# Wait for Trac to be ready
sleep 5

# Step 8: Final checks
echo -e "\n${YELLOW}Step 8: Verifying services...${NC}"

if wait_for_service "Trac" "http://localhost:8000/trac"; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ LearnTrac is running successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\nServices available at:"
    echo -e "  - Trac Wiki: ${GREEN}http://localhost:8000/trac/wiki${NC}"
    echo -e "  - Learning API: ${GREEN}http://localhost:8001/docs${NC}"
    echo -e "  - Auth Login: ${GREEN}http://localhost:8001/auth/login${NC}"
    echo -e "\nTo view logs:"
    echo -e "  - Learning API: ${YELLOW}docker logs -f learning-service${NC}"
    echo -e "  - Trac: ${YELLOW}docker logs -f trac-service${NC}"
else
    echo -e "\n${RED}✗ Failed to start services${NC}"
    echo -e "Check logs with:"
    echo -e "  ${YELLOW}docker logs learning-service${NC}"
    echo -e "  ${YELLOW}docker logs trac-service${NC}"
    exit 1
fi