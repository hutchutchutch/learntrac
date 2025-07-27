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
import time
from urllib.parse import urlparse, quote_plus

async def check_db():
    try:
        db_url = os.environ.get('DATABASE_URL', '')
        
        # Convert postgres:// to postgresql:// for asyncpg
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        # Manual parsing for URLs with special characters
        if '://' in db_url and '@' in db_url:
            scheme_rest = db_url.split('://', 1)
            scheme = scheme_rest[0]
            rest = scheme_rest[1]
            
            userpass_host = rest.split('@', 1)
            if len(userpass_host) == 2:
                userpass = userpass_host[0]
                host_rest = userpass_host[1]
                
                if ':' in userpass:
                    username = userpass.split(':', 1)[0]
                    password = userpass.split(':', 1)[1]
                    
                    # Encode password if it has special characters
                    if any(c in password for c in '{}[]()&%'):
                        password = quote_plus(password)
                    
                    # Rebuild URL
                    db_url = f'{scheme}://{username}:{password}@{host_rest}'
        
        conn = await asyncpg.connect(db_url)
        await conn.close()
        return True
    except Exception as e:
        print(f'Connection error: {e}')
        return False

async def main():
    max_attempts = 30
    for i in range(max_attempts):
        if await check_db():
            print('PostgreSQL is ready')
            exit(0)
        await asyncio.sleep(2)
    exit(1)

asyncio.run(main())
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
user = os.environ.get('NEO4J_USERNAME', '')
password = os.environ.get('NEO4J_PASSWORD', '')

max_attempts = 30
for i in range(max_attempts):
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        print('Neo4j is ready')
        exit(0)
    except Exception as e:
        print(f'Attempt {i+1}/{max_attempts}: {e}')
        time.sleep(2)
print('Neo4j connection failed after all attempts')
exit(1)
"; do
    echo "Neo4j not ready, retrying..."
    sleep 2
done

# Redis removed - no longer needed

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