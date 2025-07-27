from neo4j import GraphDatabase
import os
import sys

uri = os.getenv('NEO4J_URI', 'bolt://neo4j-dev:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', '8pQcA75CGQYcUNaZTHKYZSAo8tO9h-Z5oqkxk_G1c1o')

print(f"Testing connection to: {uri}")
print(f"User: {user}")
print(f"Password length: {len(password)}")

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        result = session.run("RETURN 'Connection successful!' as message")
        record = result.single()
        print(f"\n✅ SUCCESS: {record['message']}")
        
        # Test creating a node
        result = session.run("""
            CREATE (t:Test {name: 'LearnTrac Connection Test', timestamp: datetime()})
            RETURN t.name as name, t.timestamp as timestamp
        """)
        record = result.single()
        print(f"Created test node: {record['name']} at {record['timestamp']}")
        
        # Clean up
        session.run("MATCH (t:Test) DELETE t")
        print("Cleaned up test node")
        
    driver.close()
    print("\n✅ Neo4j connection confirmed!")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Connection failed: {str(e)}")
    sys.exit(1)