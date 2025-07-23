#!/bin/bash

# Exit on error
set -e

echo "Starting LearnTrac API initialization..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
for i in {1..30}; do
    if python -c "
import psycopg2
import os
import re

# Parse DATABASE_URL
db_url = os.environ.get('DATABASE_URL', '')
if db_url.startswith('postgresql+asyncpg://'):
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

try:
    conn = psycopg2.connect(db_url)
    conn.close()
    print('Database is ready!')
    exit(0)
except Exception as e:
    print(f'Database not ready: {e}')
    exit(1)
    "; then
        echo "Database is ready!"
        break
    fi
    echo "Waiting for database... ($i/30)"
    sleep 2
done

# Run database migrations
echo "Running database migrations..."
cd /app
alembic upgrade head || echo "No migrations to run or alembic not configured"

# Start the API server
echo "Starting LearnTrac API server on port 8001..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8001