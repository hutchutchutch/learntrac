#!/bin/bash
cd /app

# Run database migrations
echo "Running database migrations..."
alembic upgrade head || echo "Migration failed, continuing anyway..."

# Start the API
echo "Starting API server..."
uvicorn src.main:app --host 0.0.0.0 --port 8001 --log-level info