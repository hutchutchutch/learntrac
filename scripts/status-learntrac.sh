#!/bin/bash
# Check status of LearnTrac services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}LearnTrac Services Status${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to check container status
check_container() {
    local name=$1
    local port=$2
    local url=$3
    
    printf "%-20s" "$name:"
    
    if docker ps --format "table {{.Names}}" | grep -q "^$name$"; then
        printf "${GREEN}Running${NC} "
        
        # Check if port is accessible
        if [ ! -z "$port" ] && [ ! -z "$url" ]; then
            if curl -s -f "$url" > /dev/null 2>&1; then
                printf "${GREEN}(Healthy)${NC}"
            else
                printf "${YELLOW}(Starting...)${NC}"
            fi
        fi
        
        # Get container info
        local info=$(docker ps --filter "name=$name" --format "{{.Status}}")
        printf " - $info"
    else
        printf "${RED}Not Running${NC}"
    fi
    echo
}

# Check main services
echo -e "\n${YELLOW}Main Services:${NC}"
check_container "trac-service" "8000" "http://localhost:8000/trac"
check_container "learning-service" "8001" "http://localhost:8001/health"

# Redis removed - no supporting services needed

# Check RDS connection
echo -e "\n${YELLOW}RDS PostgreSQL:${NC}"
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi
RDS_HOST=$(echo "${DATABASE_URL_API_AWS:-}" | sed -n 's/.*@\([^:]*\):.*/\1/p')
if [ ! -z "$RDS_HOST" ]; then
    echo -e "RDS Instance: ${GREEN}$RDS_HOST${NC}"
else
    echo -e "RDS Instance: ${YELLOW}Not configured${NC}"
fi

# Check network
echo -e "\n${YELLOW}Docker Network:${NC}"
if docker network ls | grep -q "learntrac-network"; then
    echo -e "learntrac-network: ${GREEN}Created${NC}"
else
    echo -e "learntrac-network: ${RED}Not Found${NC}"
fi

# Check endpoints
echo -e "\n${YELLOW}Service Endpoints:${NC}"
endpoints=(
    "Trac Wiki|http://localhost:8000/trac/wiki"
    "Learning API Docs|http://localhost:8001/docs"
    "Auth Login|http://localhost:8001/auth/login"
    "Health Check|http://localhost:8001/health"
)

for endpoint in "${endpoints[@]}"; do
    IFS="|" read -r name url <<< "$endpoint"
    printf "%-20s %s " "$name:" "$url"
    
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
done

# Show quick commands
echo -e "\n${YELLOW}Quick Commands:${NC}"
echo "Start services:  ./scripts/start-learntrac.sh"
echo "Stop services:   ./scripts/stop-learntrac.sh"
echo "View logs:       ./scripts/logs-learntrac.sh [service]"
echo "Trac logs:       docker logs -f trac-service"
echo "API logs:        docker logs -f learning-service"