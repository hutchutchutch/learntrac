#!/usr/bin/env python3
"""
Generate a visualization of the Neo4j graph structure
"""

import subprocess
import os

SCRIPT = '''
import asyncio
import os
import sys
sys.path.insert(0, '/app')

from src.pdf_processing.neo4j_connection_manager import ConnectionConfig, Neo4jConnectionManager

async def visualize():
    config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    connection = Neo4jConnectionManager(config)
    if not await connection.initialize():
        return
    
    print("\\n" + "=" * 80)
    print("NEO4J GRAPH STRUCTURE VISUALIZATION")
    print("=" * 80)
    
    textbook_id = "cs_textbook_f4e2271b"
    
    # 1. Show overall structure
    print("\\n1. HIERARCHICAL STRUCTURE:")
    print("```")
    print("Textbook: Introduction to Computer Science")
    print("|")
    
    # Get chapters
    chapters = await connection.execute_query("""
        MATCH (t:Textbook {textbook_id: $id})-[:HAS_CHAPTER]->(c:Chapter)
        RETURN c.chapter_number as num, c.title as title
        ORDER BY c.chapter_number
        LIMIT 3
    """, {"id": textbook_id})
    
    for ch in chapters:
        print(f"├── Chapter {ch['num']}: {ch['title'][:40]}...")
        
        # Get sections for this chapter
        sections = await connection.execute_query("""
            MATCH (c:Chapter {textbook_id: $id, chapter_number: $num})-[:HAS_SECTION]->(s:Section)
            RETURN s.section_number as num, s.title as title
            ORDER BY s.section_number
            LIMIT 2
        """, {"id": textbook_id, "num": ch['num']})
        
        for i, sec in enumerate(sections):
            is_last_section = (i == len(sections) - 1)
            section_prefix = "    └──" if is_last_section else "    ├──"
            print(f"{section_prefix} Section {sec['num']}: {sec['title'][:30] if sec['title'] else 'N/A'}...")
            
            # Get concepts for this section
            concepts = await connection.execute_query("""
                MATCH (s:Section {textbook_id: $id, section_number: $num})-[:CONTAINS_CONCEPT]->(co:Concept)
                RETURN co.concept_name as name
                LIMIT 3
            """, {"id": textbook_id, "num": sec['num']})
            
            for j, con in enumerate(concepts):
                is_last_concept = (j == len(concepts) - 1)
                concept_prefix = "        └──" if is_last_concept else "        ├──"
                if not is_last_section:
                    concept_prefix = "    " + concept_prefix
                print(f"{concept_prefix} Concept: {con['name'][:40]}...")
    
    print("└── ... (11 more chapters)")
    print("```")
    
    # 2. Show sequential relationships
    print("\\n2. SEQUENTIAL RELATIONSHIPS (PRECEDES):")
    print("```")
    
    precedes = await connection.execute_query("""
        MATCH (c1:Chapter {textbook_id: $id})-[:PRECEDES]->(c2:Chapter)
        RETURN c1.chapter_number as from_ch, c2.chapter_number as to_ch
        ORDER BY c1.chapter_number
        LIMIT 5
    """, {"id": textbook_id})
    
    for rel in precedes:
        print(f"Chapter {rel['from_ch']} ──PRECEDES──> Chapter {rel['to_ch']}")
    print("... (continuing through all 14 chapters)")
    print("```")
    
    # 3. Show chunk relationships
    print("\\n3. CHUNK RELATIONSHIPS:")
    print("```")
    
    # Sample chunk with all its relationships
    chunk_rels = await connection.execute_query("""
        MATCH (ch:Chunk {textbook_id: $id})
        OPTIONAL MATCH (ch)-[:BELONGS_TO]->(s:Section)
        OPTIONAL MATCH (ch)-[:BELONGS_TO]->(co:Concept)
        OPTIONAL MATCH (ch)-[:NEXT]->(next:Chunk)
        RETURN ch.chunk_id as chunk_id, 
               s.section_number as section,
               co.concept_name as concept,
               next.chunk_id as next_chunk
        LIMIT 3
    """, {"id": textbook_id})
    
    for chunk in chunk_rels:
        print(f"Chunk: {chunk['chunk_id']}")
        if chunk['section']:
            print(f"  └── BELONGS_TO ──> Section {chunk['section']}")
        if chunk['concept']:
            print(f"  └── BELONGS_TO ──> Concept: {chunk['concept'][:30]}...")
        if chunk['next_chunk']:
            print(f"  └── NEXT ──> {chunk['next_chunk']}")
        print()
    print("```")
    
    # 4. Statistics
    print("\\n4. GRAPH STATISTICS:")
    
    # Count all nodes
    node_counts = await connection.execute_query("""
        MATCH (n)
        WHERE n.textbook_id = $id OR n:Textbook
        WITH labels(n)[0] as label, count(n) as count
        RETURN label, count
        ORDER BY label
    """, {"id": textbook_id})
    
    print("\\nNode Counts:")
    total_nodes = 0
    for nc in node_counts:
        print(f"  {nc['label']}: {nc['count']}")
        total_nodes += nc['count']
    print(f"  TOTAL: {total_nodes}")
    
    # Count all relationships
    rel_counts = await connection.execute_query("""
        MATCH (n)-[r]-(m)
        WHERE (n.textbook_id = $id OR n:Textbook) 
          AND (m.textbook_id = $id OR m:Textbook)
        WITH type(r) as rel_type, count(r) as count
        RETURN rel_type, count/2 as count  // Divide by 2 to avoid double counting
        ORDER BY rel_type
    """, {"id": textbook_id})
    
    print("\\nRelationship Counts:")
    total_rels = 0
    for rc in rel_counts:
        print(f"  {rc['rel_type']}: {int(rc['count'])}")
        total_rels += int(rc['count'])
    print(f"  TOTAL: {total_rels}")
    
    # 5. Sample Cypher queries
    print("\\n5. USEFUL CYPHER QUERIES:")
    print("```cypher")
    print("// Get all content for Chapter 1")
    print("MATCH (c:Chapter {textbook_id: 'cs_textbook_f4e2271b', chapter_number: 1})")
    print("      -[:HAS_SECTION]->(s:Section)")
    print("OPTIONAL MATCH (s)-[:CONTAINS_CONCEPT]->(co:Concept)")
    print("OPTIONAL MATCH (ch:Chunk)-[:BELONGS_TO]->(s)")
    print("RETURN c, s, co, ch")
    print()
    print("// Follow reading sequence through sections")
    print("MATCH path = (s1:Section {section_number: '1.1'})-[:NEXT*..5]->(s2:Section)")
    print("WHERE s1.textbook_id = 'cs_textbook_f4e2271b'")
    print("RETURN path")
    print()
    print("// Find all Algorithm concepts")
    print("MATCH (co:Concept)")
    print("WHERE co.textbook_id = 'cs_textbook_f4e2271b'")
    print("  AND co.concept_name CONTAINS 'Algorithm'")
    print("RETURN co")
    print("```")
    
    await connection.close()

asyncio.run(visualize())
'''

# Create and run script
script_path = "/tmp/visualize_graph.py"
with open(script_path, 'w') as f:
    f.write(SCRIPT)

subprocess.run(f"docker cp {script_path} learntrac-api:/tmp/visualize_graph.py", shell=True)
result = subprocess.run("docker exec learntrac-api python /tmp/visualize_graph.py", shell=True, capture_output=True, text=True)

if result.stdout:
    print(result.stdout)
if result.stderr:
    print("\nLog output:")
    print(result.stderr[-500:])
    
os.remove(script_path)