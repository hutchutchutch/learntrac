#!/bin/bash
# Stop LearnTrac services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Stopping LearnTrac Services${NC}"
echo -e "${YELLOW}========================================${NC}"

# Function to stop container if running
stop_container() {
    local container=$1
    if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
        echo -e "Stopping $container..."
        docker stop $container
        echo -e "${GREEN}✓ Stopped $container${NC}"
    else
        echo -e "${YELLOW}$container is not running${NC}"
    fi
}

# Stop services
echo -e "\n${YELLOW}Stopping services...${NC}"
stop_container "trac-service"
stop_container "learning-service"

# Redis removed - no longer needed

# Optional: Remove containers
read -p "Remove stopped containers? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Removing containers...${NC}"
    docker rm trac-service learning-service 2>/dev/null || true
    echo -e "${GREEN}✓ Containers removed${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ LearnTrac services stopped${NC}"
echo -e "${GREEN}========================================${NC}"