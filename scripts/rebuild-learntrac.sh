#!/bin/bash
# Rebuild and restart LearnTrac services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Rebuilding LearnTrac Services${NC}"
echo -e "${YELLOW}========================================${NC}"

# Stop existing services
echo -e "\n${YELLOW}Stopping existing services...${NC}"
"$SCRIPT_DIR/stop-learntrac.sh"

# Remove old images
echo -e "\n${YELLOW}Removing old images...${NC}"
docker rmi learntrac-trac:latest 2>/dev/null || true
docker rmi learntrac-learning-service:latest 2>/dev/null || true
echo -e "${GREEN}✓ Old images removed${NC}"

# Clean build cache (optional)
read -p "Clean Docker build cache? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker builder prune -f
    echo -e "${GREEN}✓ Build cache cleaned${NC}"
fi

# Start services (which will rebuild)
echo -e "\n${YELLOW}Starting services with fresh build...${NC}"
"$SCRIPT_DIR/start-learntrac.sh"