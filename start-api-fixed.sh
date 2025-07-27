#!/bin/bash
cd /app

# Set Python path
export PYTHONPATH=/app:$PYTHONPATH

# Quick Neo4j test
echo "Testing Neo4j connection..."
python3 -c "
from neo4j import GraphDatabase
import os
try:
    driver = GraphDatabase.driver(
        os.getenv('NEO4J_URI', 'bolt://neo4j-dev:7687'),
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

# Start the API
echo "Starting API server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8001 --log-level info