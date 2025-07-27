#!/bin/bash
# Simple startup script that skips optional checks

set -e

echo "Starting Learning Service API (simplified)..."

# Create log directory
mkdir -p /var/log/api
chmod 755 /var/log/api

# Install missing packages on the fly
pip install PyJWT email-validator 2>/dev/null || true

# Set Python path
export PYTHONPATH=/app:$PYTHONPATH

# Start the API server directly
echo "Starting FastAPI server..."
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --log-level ${LOG_LEVEL:-info}