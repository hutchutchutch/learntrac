#!/bin/bash

# Simple script to run Docker containers and test PDF upload plugin

echo "=========================================="
echo "Starting LearnTrac Docker Test"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p logs/trac logs/api
mkdir -p docker/trac/plugins

# Copy plugin to Docker build context
echo -e "${YELLOW}Copying PDF upload plugin...${NC}"
cp -r plugins/pdfuploadmacro docker/trac/plugins/

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << 'EOF'
# Test environment variables
OPENAI_API_KEY=sk-test
DB_USER=test
DB_PASSWORD=test
RDS_ENDPOINT=localhost
DB_NAME=learntrac
NEO4J_URI=bolt://neo4j-dev:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
ELASTICACHE_ENDPOINT=redis-dev
EOF
fi

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose down 2>/dev/null || true
docker-compose -f docker-compose.test.yml down 2>/dev/null || true

# Build and run with test configuration
echo -e "${YELLOW}Building and starting containers...${NC}"

# Use the test docker-compose if it exists, otherwise use the main one with development profile
if [ -f docker-compose.test.yml ]; then
    docker-compose -f docker-compose.test.yml up --build
else
    docker-compose --profile development up --build
fi