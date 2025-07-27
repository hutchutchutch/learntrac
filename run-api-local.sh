#!/bin/bash
# Run the API locally without Docker

cd learntrac-api

# Set environment variables
export DATABASE_URL=postgresql://learntrac_admin:learntrac_password@localhost:5432/learntrac
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=8pQcA75CGQYcUNaZTHKYZSAo8tO9h-Z5oqkxk_G1c1o
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=sk-dummy-key
export LOG_LEVEL=INFO
export ENVIRONMENT=development

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running database migrations..."
alembic upgrade head

echo "Starting API server..."
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload