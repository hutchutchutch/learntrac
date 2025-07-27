#!/usr/bin/env python3
from neo4j import GraphDatabase
import sys

# New Neo4j credentials
uri = "neo4j+s://acb9d506.databases.neo4j.io"
username = "neo4j"
password = "8pQcA75CGQYcUNaZTHKYZSAo8tO9h-Z5oqkxk_G1c1o"

def test_connection():
    driver = None
    try:
        # Create driver
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        # Verify connectivity
        driver.verify_connectivity()
        print("✓ Successfully connected to Neo4j!")
        
        # Run a simple query
        with driver.session() as session:
            result = session.run("RETURN 1 as num")
            record = result.single()
            print(f"✓ Query test successful: {record['num']}")
            
        # Get database info
        with driver.session() as session:
            result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
            for record in result:
                print(f"✓ Component: {record['name']}, Version: {record['versions']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
        
    finally:
        if driver:
            driver.close()

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)