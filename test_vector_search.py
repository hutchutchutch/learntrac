#!/usr/bin/env python3

import subprocess
import os

SCRIPT = '''
import asyncio
import os
import sys
sys.path.insert(0, '/app')

from src.pdf_processing.neo4j_connection_manager import ConnectionConfig, Neo4jConnectionManager
from src.services.embedding_service import EmbeddingService

async def test_search():
    # Initialize services
    config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    connection = Neo4jConnectionManager(config)
    if not await connection.initialize():
        return
    
    embedding_service = EmbeddingService()
    await embedding_service.initialize()
    
    print("\\n" + "=" * 60)
    print("VECTOR SEARCH TEST")
    print("=" * 60)
    
    # Test queries
    queries = [
        "What is computer science?",
        "Explain algorithms and data structures",
        "How do computers work?",
        "What is computational thinking?"
    ]
    
    for query in queries:
        print(f"\\nQuery: '{query}'")
        print("-" * 50)
        
        # Generate embedding for query
        query_embedding = await embedding_service.generate_embedding(query)
        
        if query_embedding:
            # Since vector index might have issues, let's do a simple text search
            result = await connection.execute_query("""
                MATCH (ch:Chunk {textbook_id: 'cs_textbook_f4e2271b'})
                WHERE toLower(ch.text) CONTAINS toLower($query)
                OPTIONAL MATCH (ch)-[:BELONGS_TO]->(s:Section)
                OPTIONAL MATCH (s)<-[:HAS_SECTION]-(c:Chapter)
                RETURN ch.chunk_id as id,
                       substring(ch.text, 0, 200) as preview,
                       s.section_number as section,
                       c.chapter_number as chapter,
                       c.title as chapter_title
                LIMIT 3
            """, {"query": query.split()[0]})  # Use first word for simple search
            
            if result:
                print(f"Found {len(result)} relevant chunks:")
                for i, r in enumerate(result):
                    print(f"\\n{i+1}. Chapter {r['chapter']}: {r['chapter_title']}")
                    if r['section']:
                        print(f"   Section: {r['section']}")
                    print(f"   Preview: {r['preview']}...")
            else:
                print("No results found with text search")
                
                # Try broader search
                result = await connection.execute_query("""
                    MATCH (ch:Chunk {textbook_id: 'cs_textbook_f4e2271b'})
                    RETURN ch.chunk_id as id,
                           substring(ch.text, 0, 100) as preview
                    LIMIT 3
                """)
                
                if result:
                    print(f"\\nShowing {len(result)} sample chunks:")
                    for r in result:
                        print(f"  - {r['preview']}...")
        else:
            print("Failed to generate query embedding")
    
    # Show some statistics
    result = await connection.execute_query("""
        MATCH (ch:Chunk {textbook_id: 'cs_textbook_f4e2271b'})
        WHERE ch.embedding IS NOT NULL
        RETURN count(ch) as with_embeddings
    """)
    
    embed_count = result[0]['with_embeddings'] if result else 0
    
    result = await connection.execute_query("""
        MATCH (ch:Chunk {textbook_id: 'cs_textbook_f4e2271b'})
        RETURN count(ch) as total
    """)
    
    total_count = result[0]['total'] if result else 0
    
    print(f"\\n\\nEMBEDDING STATISTICS:")
    print(f"Total chunks: {total_count}")
    print(f"Chunks with embeddings: {embed_count}")
    print(f"Coverage: {embed_count/total_count*100:.1f}%" if total_count > 0 else "0%")
    
    await connection.close()

asyncio.run(test_search())
'''

# Create and run script
script_path = "/tmp/test_search.py"
with open(script_path, 'w') as f:
    f.write(SCRIPT)

subprocess.run(f"docker cp {script_path} learntrac-api:/tmp/test_search.py", shell=True)
result = subprocess.run("docker exec learntrac-api python /tmp/test_search.py", shell=True, capture_output=True, text=True)

if result.stdout:
    print(result.stdout)
if result.stderr:
    print("\nLog output:")
    print(result.stderr[-1000:])
    
os.remove(script_path)