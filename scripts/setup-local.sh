#!/bin/bash

set -e

echo "==================================="
echo "LearnTrac Local Development Setup"
echo "==================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Warning: Conda is not installed. Will use system Python instead."
    USE_CONDA=false
else
    USE_CONDA=true
fi

# Create Python 2.7 environment for Trac
if [ "$USE_CONDA" = true ]; then
    echo "Creating Python 2.7 environment for Trac..."
    conda create -n trac_env python=2.7 -y || echo "Trac environment already exists"
    
    echo "Installing Trac dependencies..."
    conda activate trac_env
    pip install -r trac-legacy/requirements.txt
    conda deactivate
else
    echo "Using system Python for Trac (requires Python 2.7)"
fi

# Create Python 3.11 environment for LearnTrac
if [ "$USE_CONDA" = true ]; then
    echo "Creating Python 3.11 environment for LearnTrac API..."
    conda create -n learntrac_env python=3.11 -y || echo "LearnTrac environment already exists"
    
    echo "Installing LearnTrac dependencies..."
    conda activate learntrac_env
    pip install -r learntrac-api/requirements.txt
    conda deactivate
else
    echo "Using system Python 3 for LearnTrac"
    pip3 install -r learntrac-api/requirements.txt
fi

# Start PostgreSQL locally
echo ""
echo "Starting PostgreSQL..."
docker run -d \
    --name learntrac-postgres \
    -e POSTGRES_PASSWORD=localpass \
    -e POSTGRES_DB=learntrac \
    -p 5432:5432 \
    postgres:15 || echo "PostgreSQL container already exists"

# Start Redis locally
echo "Starting Redis..."
docker run -d \
    --name learntrac-redis \
    -p 6379:6379 \
    redis:7-alpine || echo "Redis container already exists"

# Start Neo4j locally (optional)
echo "Starting Neo4j (optional)..."
docker run -d \
    --name learntrac-neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/learntrac123 \
    neo4j:5-community || echo "Neo4j container already exists"

# Wait for services to be ready
echo ""
echo "Waiting for services to start..."
sleep 5

# Check service status
echo ""
echo "Checking service status..."
docker ps | grep -E "learntrac-postgres|learntrac-redis|learntrac-neo4j" || true

echo ""
echo "==================================="
echo "Local Environment Setup Complete!"
echo "==================================="
echo ""
echo "Database connection strings:"
echo "  PostgreSQL: postgresql://postgres:localpass@localhost:5432/learntrac"
echo "  Redis: redis://localhost:6379"
echo "  Neo4j: neo4j://neo4j:learntrac123@localhost:7687"
echo ""

if [ "$USE_CONDA" = true ]; then
    echo "To start Trac (Python 2.7):"
    echo "  conda activate trac_env"
    echo "  cd trac-legacy"
    echo "  python -m trac.web.standalone --port 8000 /path/to/trac/env"
    echo ""
    echo "To start LearnTrac API (Python 3.11):"
    echo "  conda activate learntrac_env"
    echo "  cd learntrac-api"
    echo "  uvicorn src.main:app --reload --port 8001"
else
    echo "To start services:"
    echo "  cd trac-legacy && python2 -m trac.web.standalone --port 8000 /path/to/trac/env"
    echo "  cd learntrac-api && python3 -m uvicorn src.main:app --reload --port 8001"
fi

echo ""
echo "To stop services:"
echo "  docker stop learntrac-postgres learntrac-redis learntrac-neo4j"
echo ""
echo "To remove services:"
echo "  docker rm learntrac-postgres learntrac-redis learntrac-neo4j"