#!/usr/bin/env python3

import subprocess
import os

SCRIPT = '''
import asyncio
import os
import sys
sys.path.insert(0, '/app')

from src.pdf_processing.neo4j_connection_manager import ConnectionConfig, Neo4jConnectionManager

async def check():
    config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    connection = Neo4jConnectionManager(config)
    if not await connection.initialize():
        return
    
    # Check all PRECEDES relationships
    result = await connection.execute_query("""
        MATCH (c1:Chapter)-[r:PRECEDES]->(c2:Chapter)
        WHERE c1.textbook_id = 'cs_intro_test_f4e2271b'
        RETURN c1.chapter_number as from_ch, c2.chapter_number as to_ch
        ORDER BY c1.chapter_number
    """)
    
    print(f"Found {len(result)} PRECEDES relationships for test textbook:")
    for r in result:
        print(f"  Chapter {r['from_ch']} -> Chapter {r['to_ch']}")
    
    await connection.close()

asyncio.run(check())
'''

# Create and run script
script_path = "/tmp/check_rel.py"
with open(script_path, 'w') as f:
    f.write(SCRIPT)

subprocess.run(f"docker cp {script_path} learntrac-api:/tmp/check_rel.py", shell=True)
result = subprocess.run("docker exec learntrac-api python /tmp/check_rel.py", shell=True, capture_output=True, text=True)

if result.stdout:
    print(result.stdout)
    
os.remove(script_path)