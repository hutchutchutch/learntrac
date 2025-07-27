#!/bin/bash
cd /app

# Install apt dependencies first
apt-get update -qq && apt-get install -y -qq gcc libpq-dev

echo "Installing Python dependencies..."
# Create a minimal requirements file
cat > /tmp/requirements-minimal.txt << EOF
fastapi==0.104.0
uvicorn[standard]==0.24.0
neo4j==5.14.0
asyncpg==0.29.0
psycopg-binary
psycopg
sqlalchemy[asyncio]==2.0.0
redis==5.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.0.0
PyJWT==2.8.0
httpx==0.25.0
python-dotenv==1.0.0
alembic==1.12.0
aiohttp==3.9.0
python-multipart==0.0.6
aiofiles
greenlet
mako
numpy
pandas
openai
cryptography
networkx
pypdf
PyMuPDF
pdfplumber
sentence-transformers
EOF

# Install all at once
pip install -q -r /tmp/requirements-minimal.txt || {
    echo "Failed to install all dependencies, trying one by one..."
    while read -r line; do
        [ -z "$line" ] || pip install -q "$line" || echo "Failed: $line"
    done < /tmp/requirements-minimal.txt
}

echo "Testing Neo4j connection..."
python3 -c "
from neo4j import GraphDatabase
import os
try:
    driver = GraphDatabase.driver(
        os.getenv('NEO4J_URI', 'bolt://host.docker.internal:7687'),
        auth=(os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASSWORD', ''))
    )
    with driver.session() as session:
        session.run('RETURN 1')
    driver.close()
    print('✅ Neo4j connection successful')
except Exception as e:
    print(f'⚠️  Neo4j connection failed: {e}')
    print('Continuing anyway...')
"

# Set Python path
export PYTHONPATH=/app:$PYTHONPATH

# Start the API directly
echo "Starting API server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8001 --log-level info