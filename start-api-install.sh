#!/bin/bash
cd /app

echo "Installing core dependencies..."
# Install in smaller batches to avoid issues
pip install -q fastapi==0.104.0 uvicorn==0.24.0
pip install -q neo4j==5.14.0 asyncpg==0.29.0 
pip install -q psycopg-binary sqlalchemy==2.0.0
pip install -q redis==5.0.0 pydantic==2.5.0 pydantic-settings==2.1.0
pip install -q email-validator==2.0.0 PyJWT==2.8.0 httpx==0.25.0
pip install -q python-dotenv==1.0.0 alembic==1.12.0
pip install -q aiohttp==3.9.0 python-multipart==0.0.6
pip install -q greenlet  # For sqlalchemy

echo "Dependencies installed"

# Now run the patched API
exec /app/start-api-novector.sh