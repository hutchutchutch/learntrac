#!/usr/bin/env python3
"""
Check what's in Neo4j after processing
"""

import subprocess
import os

SCRIPT_CONTENT = '''
import asyncio
import os
import sys

sys.path.insert(0, '/app')

from src.pdf_processing.neo4j_connection_manager import ConnectionConfig, Neo4jConnectionManager

async def check_content():
    """Check Neo4j content"""
    
    # Connect to Neo4j
    config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    connection = Neo4jConnectionManager(config)
    if not await connection.initialize():
        print("Failed to connect to Neo4j!")
        return
    
    print("Neo4j Content Summary")
    print("=" * 60)
    
    # Check textbooks
    result = await connection.execute_query("""
        MATCH (t:Textbook)
        RETURN t.textbook_id as id, t.title as title, t.test_run as test
        ORDER BY t.processed_date DESC
        LIMIT 5
    """)
    
    print("\\nTextbooks:")
    for r in result:
        test_flag = " (TEST)" if r.get('test') else ""
        print(f"  - {r['id']}: {r['title']}{test_flag}")
    
    # Check chapters for latest textbook
    if result:
        textbook_id = result[0]['id']
        print(f"\\nAnalyzing textbook: {textbook_id}")
        
        # Chapters
        result = await connection.execute_query("""
            MATCH (t:Textbook {textbook_id: $id})-[:HAS_CHAPTER]->(c:Chapter)
            RETURN c.chapter_number as num, c.title as title
            ORDER BY c.chapter_number
        """, {"id": textbook_id})
        
        print(f"\\nChapters ({len(result)}):")
        for r in result[:5]:
            print(f"  Chapter {r['num']}: {r['title']}")
        if len(result) > 5:
            print(f"  ... and {len(result) - 5} more")
        
        # Check PRECEDES relationships
        result = await connection.execute_query("""
            MATCH (c1:Chapter {textbook_id: $id})-[:PRECEDES]->(c2:Chapter)
            RETURN c1.chapter_number as from_ch, c2.chapter_number as to_ch
            ORDER BY c1.chapter_number
            LIMIT 5
        """, {"id": textbook_id})
        
        print(f"\\nChapter PRECEDES relationships ({len(result)} shown):")
        for r in result:
            print(f"  Chapter {r['from_ch']} -> Chapter {r['to_ch']}")
        
        # Sections
        result = await connection.execute_query("""
            MATCH (t:Textbook {textbook_id: $id})-[:HAS_CHAPTER]->(c:Chapter)-[:HAS_SECTION]->(s:Section)
            RETURN c.chapter_number as ch_num, count(s) as section_count
            ORDER BY c.chapter_number
        """, {"id": textbook_id})
        
        print(f"\\nSections per chapter:")
        total_sections = 0
        for r in result[:5]:
            print(f"  Chapter {r['ch_num']}: {r['section_count']} sections")
            total_sections += r['section_count']
        if len(result) > 5:
            print(f"  ... and {len(result) - 5} more chapters")
        
        # Concepts
        result = await connection.execute_query("""
            MATCH (co:Concept {textbook_id: $id})
            RETURN count(co) as count
        """, {"id": textbook_id})
        
        concept_count = result[0]['count'] if result else 0
        print(f"\\nConcepts: {concept_count}")
        
        # Chunks
        result = await connection.execute_query("""
            MATCH (ch:Chunk {textbook_id: $id})
            WITH ch, ch.embedding IS NOT NULL as has_embedding
            RETURN count(ch) as total, sum(CASE WHEN has_embedding THEN 1 ELSE 0 END) as with_embeddings
        """, {"id": textbook_id})
        
        if result and result[0]['total'] > 0:
            print(f"\\nChunks:")
            print(f"  Total: {result[0]['total']}")
            print(f"  With embeddings: {result[0]['with_embeddings']}")
        
        # Sample chunk content
        result = await connection.execute_query("""
            MATCH (ch:Chunk {textbook_id: $id})
            WHERE ch.text IS NOT NULL
            RETURN ch.chunk_id as id, ch.chapter_number as ch_num, 
                   substring(ch.text, 0, 100) as preview
            LIMIT 3
        """, {"id": textbook_id})
        
        if result:
            print("\\nSample chunks:")
            for r in result:
                print(f"  {r['id']} (Ch {r['ch_num']}): {r['preview']}...")
    
    await connection.close()

if __name__ == "__main__":
    asyncio.run(check_content())
'''

def check_neo4j():
    """Check Neo4j content"""
    
    # Create script
    script_path = "/tmp/check_neo4j.py"
    with open(script_path, 'w') as f:
        f.write(SCRIPT_CONTENT)
    
    # Copy to container
    copy_cmd = f"docker cp {script_path} learntrac-api:/tmp/check_neo4j.py"
    subprocess.run(copy_cmd, shell=True)
    
    # Run
    exec_cmd = "docker exec learntrac-api python /tmp/check_neo4j.py"
    result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("\nLog output:")
        print(result.stderr[-1000:])  # Last 1000 chars
    
    # Clean up
    os.remove(script_path)

if __name__ == "__main__":
    check_neo4j()