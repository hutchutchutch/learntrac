#!/bin/bash
# View logs for LearnTrac services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if specific service requested
SERVICE=$1

show_usage() {
    echo "Usage: $0 [service]"
    echo "Services: all, trac, learning"
    echo "Example: $0 trac"
}

view_logs() {
    local service=$1
    local container=$2
    
    if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
        echo -e "\n${BLUE}========== $service Logs ==========${NC}"
        docker logs --tail 50 -f $container
    else
        echo -e "${YELLOW}$service ($container) is not running${NC}"
    fi
}

case "$SERVICE" in
    "trac")
        view_logs "Trac" "trac-service"
        ;;
    "learning")
        view_logs "Learning API" "learning-service"
        ;;
    "postgres")
        view_logs "PostgreSQL" "postgres"
        ;;
    "all"|"")
        # Show all logs with tmux or in sequence
        if command -v tmux &> /dev/null; then
            # Use tmux for split view
            tmux new-session -d -s learntrac-logs
            tmux send-keys -t learntrac-logs "docker logs -f learning-service" C-m
            tmux split-window -t learntrac-logs -v
            tmux send-keys -t learntrac-logs "docker logs -f trac-service" C-m
            tmux attach-session -t learntrac-logs
        else
            # Show logs in sequence
            echo -e "${YELLOW}Showing logs for all services (Ctrl+C to switch)${NC}"
            echo -e "${BLUE}========== Learning API Logs ==========${NC}"
            docker logs --tail 20 learning-service 2>/dev/null || echo "Learning API not running"
            echo -e "\n${BLUE}========== Trac Logs ==========${NC}"
            docker logs --tail 20 trac-service 2>/dev/null || echo "Trac not running"
            echo -e "\n${YELLOW}Use '$0 trac' or '$0 learning' to follow specific logs${NC}"
        fi
        ;;
    "-h"|"--help")
        show_usage
        ;;
    *)
        echo -e "${RED}Unknown service: $SERVICE${NC}"
        show_usage
        exit 1
        ;;
esac