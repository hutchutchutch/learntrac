#!/bin/bash
# Startup script for Learning Service API

set -e

echo "Starting Learning Service API initialization..."

# Wait for database to be ready
echo "Waiting for PostgreSQL database..."
until python3 -c "
import asyncpg
import asyncio
import os

async def check_db():
    try:
        conn = await asyncpg.connect(os.environ.get('DATABASE_URL', ''))
        await conn.close()
        return True
    except:
        return False

loop = asyncio.get_event_loop()
max_attempts = 30
for i in range(max_attempts):
    if loop.run_until_complete(check_db()):
        print('PostgreSQL is ready')
        exit(0)
    asyncio.sleep(2)
exit(1)
"; do
    echo "PostgreSQL not ready, retrying..."
    sleep 2
done

# Wait for Neo4j to be ready
echo "Waiting for Neo4j database..."
until python3 -c "
from neo4j import GraphDatabase
import os
import time

uri = os.environ.get('NEO4J_URI', '')
user = os.environ.get('NEO4J_USER', '')
password = os.environ.get('NEO4J_PASSWORD', '')

max_attempts = 30
for i in range(max_attempts):
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        print('Neo4j is ready')
        exit(0)
    except:
        time.sleep(2)
exit(1)
"; do
    echo "Neo4j not ready, retrying..."
    sleep 2
done

# Wait for Redis to be ready
echo "Waiting for Redis..."
until python3 -c "
import redis
import os

redis_url = os.environ.get('REDIS_URL', '')
max_attempts = 30
for i in range(max_attempts):
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print('Redis is ready')
        exit(0)
    except:
        time.sleep(2)
exit(1)
"; do
    echo "Redis not ready, retrying..."
    sleep 2
done

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Create log directory
mkdir -p /var/log/api
chmod 755 /var/log/api

# Start the API server
echo "Starting FastAPI server..."
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --log-config /app/logging.conf \
    --log-level ${LOG_LEVEL:-info}