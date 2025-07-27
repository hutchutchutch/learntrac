#!/usr/bin/env python3
import os
from neo4j import GraphDatabase

# Test different password combinations
passwords = [
    "8pQcA75CGQYcUNaZTHKYZSAo8tO9h-Z5oqkxk_G1c1o",  # The one you provided
    "password",  # Default
    "neo4j"  # Another default
]

uri = "bolt://localhost:7687"
username = "neo4j"

print(f"Testing connection to Neo4j at {uri}")
print(f"Username: {username}")
print("-" * 50)

for pwd in passwords:
    try:
        print(f"\nTrying password: {pwd[:10]}...")
        driver = GraphDatabase.driver(uri, auth=(username, pwd))
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record:
                print(f"✅ SUCCESS! Connected with password: {pwd}")
                print(f"Test query result: {record['test']}")
                
                # Get some basic info
                result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
                for record in result:
                    print(f"Component: {record['name']} - Version: {record['versions']}")
                
                driver.close()
                break
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        continue
else:
    print("\n❌ All password attempts failed!")