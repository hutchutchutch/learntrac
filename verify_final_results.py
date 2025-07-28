#!/usr/bin/env python3

import subprocess
import os

SCRIPT = '''
import asyncio
import os
import sys
sys.path.insert(0, '/app')

from src.pdf_processing.neo4j_connection_manager import ConnectionConfig, Neo4jConnectionManager

async def verify():
    config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    connection = Neo4jConnectionManager(config)
    if not await connection.initialize():
        return
    
    print("\\n" + "=" * 60)
    print("FINAL VERIFICATION - cs_textbook_f4e2271b")
    print("=" * 60)
    
    # 1. Check chapters and PRECEDES
    result = await connection.execute_query("""
        MATCH (c:Chapter {textbook_id: 'cs_textbook_f4e2271b'})
        OPTIONAL MATCH (c)-[:PRECEDES]->(next:Chapter)
        RETURN c.chapter_number as num, c.title as title, next.chapter_number as next_num
        ORDER BY c.chapter_number
    """)
    
    print(f"\\n1. CHAPTERS ({len(result)}) with PRECEDES relationships:")
    for r in result[:5]:
        next_info = f" -> Chapter {r['next_num']}" if r['next_num'] else ""
        print(f"   Chapter {r['num']}: {r['title'][:50]}...{next_info}")
    if len(result) > 5:
        print(f"   ... and {len(result) - 5} more chapters")
    
    # 2. Check sections and relationships
    result = await connection.execute_query("""
        MATCH (c:Chapter {textbook_id: 'cs_textbook_f4e2271b'})-[:HAS_SECTION]->(s:Section)
        WITH c.chapter_number as ch_num, count(s) as section_count
        RETURN ch_num, section_count
        ORDER BY ch_num
        LIMIT 5
    """)
    
    print("\\n2. SECTIONS per chapter:")
    total_sections = 0
    for r in result:
        print(f"   Chapter {r['ch_num']}: {r['section_count']} sections")
        total_sections += r['section_count']
    
    # Check NEXT relationships between sections
    result = await connection.execute_query("""
        MATCH (s1:Section {textbook_id: 'cs_textbook_f4e2271b'})-[:NEXT]->(s2:Section)
        RETURN count(*) as count
    """)
    
    next_count = result[0]['count'] if result else 0
    print(f"\\n   Sequential NEXT relationships between sections: {next_count}")
    
    # 3. Check concepts
    result = await connection.execute_query("""
        MATCH (s:Section {textbook_id: 'cs_textbook_f4e2271b'})-[:CONTAINS_CONCEPT]->(co:Concept)
        WITH s.section_number as section, count(co) as concept_count
        RETURN section, concept_count
        ORDER BY section
        LIMIT 10
    """)
    
    print("\\n3. CONCEPTS per section (first 10):")
    for r in result:
        print(f"   Section {r['section']}: {r['concept_count']} concepts")
    
    # 4. Check chunks
    result = await connection.execute_query("""
        MATCH (ch:Chunk {textbook_id: 'cs_textbook_f4e2271b'})
        WITH ch.chapter_number as ch_num, count(ch) as chunk_count
        RETURN ch_num, chunk_count
        ORDER BY ch_num
    """)
    
    print("\\n4. CHUNKS per chapter:")
    total_chunks = 0
    for r in result[:5]:
        print(f"   Chapter {r['ch_num']}: {r['chunk_count']} chunks")
        total_chunks += r['chunk_count']
    
    # 5. Check chunk relationships
    result = await connection.execute_query("""
        MATCH (ch:Chunk {textbook_id: 'cs_textbook_f4e2271b'})-[:BELONGS_TO]->(s:Section)
        RETURN count(*) as count
    """)
    
    belongs_count = result[0]['count'] if result else 0
    print(f"\\n5. CHUNK RELATIONSHIPS:")
    print(f"   Chunks with BELONGS_TO->Section: {belongs_count}")
    
    # 6. Summary of all relationships
    result = await connection.execute_query("""
        MATCH (t:Textbook {textbook_id: 'cs_textbook_f4e2271b'})
        OPTIONAL MATCH (t)-[:HAS_CHAPTER]->(c:Chapter)
        OPTIONAL MATCH (c)-[:HAS_SECTION]->(s:Section)
        OPTIONAL MATCH (s)-[:CONTAINS_CONCEPT]->(co:Concept)
        OPTIONAL MATCH (:Chunk {textbook_id: 'cs_textbook_f4e2271b'})-[:BELONGS_TO]->(s2:Section)
        OPTIONAL MATCH (c1:Chapter {textbook_id: 'cs_textbook_f4e2271b'})-[:PRECEDES]->(c2:Chapter)
        OPTIONAL MATCH (s1:Section {textbook_id: 'cs_textbook_f4e2271b'})-[:NEXT]->(s2:Section)
        WITH 
            count(DISTINCT c) as chapters,
            count(DISTINCT s) as sections,
            count(DISTINCT co) as concepts,
            count(DISTINCT c1) as chapters_with_precedes,
            count(DISTINCT s1) as sections_with_next
        RETURN *
    """)
    
    if result:
        r = result[0]
        print("\\n6. SUMMARY:")
        print(f"   Total chapters: {r['chapters']}")
        print(f"   Total sections: {r['sections']}")
        print(f"   Total concepts: {r['concepts']}")
        print(f"   Chapters with PRECEDES: {r['chapters_with_precedes']}")
        print(f"   Sections with NEXT: {r['sections_with_next']}")
    
    # 7. Sample query to show the structure
    result = await connection.execute_query("""
        MATCH path = (c:Chapter {textbook_id: 'cs_textbook_f4e2271b', chapter_number: 1})
                     -[:HAS_SECTION]->(s:Section)
        OPTIONAL MATCH (s)-[:CONTAINS_CONCEPT]->(co:Concept)
        RETURN s.section_number as section, s.title as title, count(co) as concepts
        ORDER BY s.section_number
        LIMIT 5
    """)
    
    print("\\n7. SAMPLE STRUCTURE (Chapter 1):")
    for r in result:
        print(f"   Section {r['section']}: {r['title'][:40]}... ({r['concepts']} concepts)")
    
    await connection.close()

asyncio.run(verify())
'''

# Create and run script
script_path = "/tmp/verify_final.py"
with open(script_path, 'w') as f:
    f.write(SCRIPT)

subprocess.run(f"docker cp {script_path} learntrac-api:/tmp/verify_final.py", shell=True)
result = subprocess.run("docker exec learntrac-api python /tmp/verify_final.py", shell=True, capture_output=True, text=True)

if result.stdout:
    print(result.stdout)
if result.stderr:
    print("\nLog:")
    print(result.stderr[-500:])
    
os.remove(script_path)