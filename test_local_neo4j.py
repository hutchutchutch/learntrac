#!/usr/bin/env python3
"""
Test script to verify local Neo4j connection and upload PDF
"""

import os
import subprocess
import time

def update_env_and_restart():
    """Update docker-compose to use local Neo4j"""
    
    print("Updating API to use local Neo4j...")
    
    # Create a temporary env file for local Neo4j
    env_content = """
# Use local Neo4j instead of Aura
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jpassword
"""
    
    # Write to a temporary .env.local file
    with open('.env.local', 'w') as f:
        f.write(env_content)
    
    print("\n1. Stopping current API container...")
    subprocess.run("docker stop learntrac-api", shell=True)
    
    print("\n2. Starting API with local Neo4j configuration...")
    # Start with updated environment
    start_cmd = """docker run -d --name learntrac-api-local \
        --network learntrac_learntrac-network \
        -p 8002:8001 \
        -e NEO4J_URI=bolt://neo4j:7687 \
        -e NEO4J_USER=neo4j \
        -e NEO4J_PASSWORD=neo4jpassword \
        -e DATABASE_URL=$RDS_DATABASE_URL \
        -e OPENAI_API_KEY=$OPENAI_API_KEY \
        -v $(pwd)/learntrac-api:/app \
        -v $(pwd)/textbooks:/app/textbooks \
        learntrac-api-learntrac-api \
        uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload"""
    
    subprocess.run(start_cmd, shell=True)
    
    print("\n3. Waiting for API to start...")
    time.sleep(5)
    
    # Check health
    health_check = subprocess.run(
        "curl -s http://localhost:8002/health",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if health_check.returncode == 0:
        print("✓ API is running on port 8002 with local Neo4j")
    else:
        print("✗ API failed to start")
        
    # Clean up
    if os.path.exists('.env.local'):
        os.remove('.env.local')

def test_direct_neo4j():
    """Test Neo4j connection directly"""
    
    print("\nTesting direct Neo4j connection...")
    
    # Use cypher-shell to test connection
    test_query = 'MATCH (n) RETURN count(n) as node_count LIMIT 1;'
    
    cmd = f'''docker exec learntrac-neo4j cypher-shell -u neo4j -p neo4jpassword "{test_query}"'''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Neo4j connection successful")
        print(f"Output: {result.stdout}")
    else:
        print("✗ Neo4j connection failed")
        print(f"Error: {result.stderr}")

def initialize_neo4j_indexes():
    """Initialize Neo4j indexes for vector search"""
    
    print("\nInitializing Neo4j indexes...")
    
    queries = [
        # Create constraints
        "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;",
        "CREATE CONSTRAINT textbook_id IF NOT EXISTS FOR (t:Textbook) REQUIRE t.textbook_id IS UNIQUE;",
        "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE;",
        
        # Create indexes
        "CREATE INDEX chunk_embedding IF NOT EXISTS FOR (c:Chunk) ON (c.embedding);",
        "CREATE INDEX chunk_textbook IF NOT EXISTS FOR (c:Chunk) ON (c.textbook_id);",
        "CREATE INDEX section_textbook IF NOT EXISTS FOR (s:Section) ON (s.textbook_id);"
    ]
    
    for query in queries:
        cmd = f'''docker exec learntrac-neo4j cypher-shell -u neo4j -p neo4jpassword "{query}"'''
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if "already exists" in result.stdout or result.returncode == 0:
            print(f"✓ {query.split()[1]} {query.split()[2]}")
        else:
            print(f"✗ Failed: {result.stderr}")

if __name__ == "__main__":
    print("Local Neo4j Test Script")
    print("=" * 60)
    
    # Test direct Neo4j connection
    test_direct_neo4j()
    
    # Initialize indexes
    initialize_neo4j_indexes()
    
    # Option to restart API with local Neo4j
    response = input("\nDo you want to restart the API with local Neo4j? (y/n): ")
    if response.lower() == 'y':
        update_env_and_restart()
    
    print("\nNote: To properly process the PDF, we need the API to connect to local Neo4j.")
    print("The current API is configured for Neo4j Aura (cloud) which may not be accessible.")