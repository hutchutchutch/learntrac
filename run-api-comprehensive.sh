#!/bin/bash
set -e

cd /app

# Install system dependencies
echo "Installing system dependencies..."
apt-get update -qq && apt-get install -y -qq gcc libpq-dev build-essential python3-dev

echo "Creating comprehensive requirements file..."
cat > /tmp/requirements-comprehensive.txt << 'EOF'
# Core framework
fastapi==0.104.0
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
neo4j==5.14.0
asyncpg==0.29.0
psycopg-binary
psycopg[pool]
sqlalchemy[asyncio]==2.0.0
alembic==1.12.0
greenlet==3.0.0

# Caching
redis==5.0.0

# Data validation and settings
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.0.0

# Authentication
python-jose[cryptography]==3.3.0
PyJWT==2.8.0
cryptography==41.0.0

# HTTP client
httpx==0.25.0
aiohttp==3.9.0

# File handling
aiofiles==23.2.1
python-dotenv==1.0.0

# Data processing
numpy==1.26.0
pandas==2.1.0
networkx==3.2.0

# PDF processing
pypdf==3.17.0
PyMuPDF==1.23.0
pdfplumber==0.10.0

# ML/AI (minimal versions)
openai==1.3.0
# Skip heavy ML dependencies for now
# sentence-transformers==2.2.0

# Other utilities
mako==1.3.0
typing-extensions==4.8.0
EOF

echo "Installing all dependencies..."
pip install --no-cache-dir -r /tmp/requirements-comprehensive.txt

echo "Testing imports..."
python3 -c "
import sys
import importlib

required_modules = [
    'fastapi', 'uvicorn', 'neo4j', 'asyncpg', 'sqlalchemy',
    'redis', 'pydantic', 'email_validator', 'jwt', 'httpx',
    'aiohttp', 'aiofiles', 'numpy', 'pandas', 'networkx',
    'pypdf', 'fitz', 'pdfplumber', 'openai'
]

failed = []
for module in required_modules:
    try:
        importlib.import_module(module)
        print(f'✓ {module}')
    except ImportError as e:
        print(f'✗ {module}: {e}')
        failed.append(module)

if failed:
    print(f'\nFailed to import: {failed}')
    sys.exit(1)
else:
    print('\nAll modules imported successfully!')
"

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

# Start the API
echo "Starting API server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8001 --log-level info