#!/bin/bash
# Health check script for Learning Service API

# Check if API is responding
if curl -f -s http://localhost:8001/health > /dev/null; then
    # Check detailed health status
    HEALTH_STATUS=$(curl -s http://localhost:8001/health | python3 -c "
import json
import sys
data = json.load(sys.stdin)
if data.get('status') == 'healthy' and all(
    service.get('status') == 'connected' 
    for service in data.get('services', {}).values()
):
    print('healthy')
else:
    print('unhealthy')
")
    
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        exit 0
    else
        echo "API health check returned unhealthy status"
        exit 1
    fi
else
    echo "API HTTP check failed"
    exit 1
fi