#!/usr/bin/env python3

import subprocess
import os

SCRIPT = '''
import asyncio
import os
import sys
sys.path.insert(0, '/app')

from src.pdf_processing.neo4j_connection_manager import ConnectionConfig, Neo4jConnectionManager

async def verify_complete():
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
    print("COMPLETE GRAPH STRUCTURE VERIFICATION")
    print("=" * 80)
    
    textbook_id = "cs_textbook_f4e2271b"
    
    # Get all relationship counts
    print("\\n1. ALL RELATIONSHIPS IN THE GRAPH:")
    print("-" * 50)
    
    relationships = [
        ("Textbook", "HAS_CHAPTER", "Chapter"),
        ("Chapter", "HAS_SECTION", "Section"),
        ("Section", "CONTAINS_CONCEPT", "Concept"),
        ("Chunk", "BELONGS_TO", "Section"),
        ("Chapter", "PRECEDES", "Chapter"),
        ("Section", "NEXT", "Section"),
        ("Concept", "NEXT", "Concept"),
        ("Chunk", "NEXT", "Chunk")
    ]
    
    total_rels = 0
    for from_node, rel_type, to_node in relationships:
        query = f"""
            MATCH (n:{from_node})-[r:{rel_type}]->(m:{to_node})
            WHERE (n.textbook_id = $id OR n:Textbook) 
              AND (m.textbook_id = $id OR m:Textbook)
            RETURN count(r) as count
        """
        
        result = await connection.execute_query(query, {"id": textbook_id})
        count = result[0]['count'] if result else 0
        if count > 0:
            print(f"  ({from_node})-[:{rel_type}]->({to_node}): {count}")
            total_rels += count
    
    print(f"\\n  TOTAL RELATIONSHIPS: {total_rels}")
    
    # Show sequential paths
    print("\\n2. SEQUENTIAL READING PATHS:")
    print("-" * 50)
    
    # Chapter sequence
    result = await connection.execute_query("""
        MATCH path = (c1:Chapter {textbook_id: $id, chapter_number: 1})
                     -[:PRECEDES*]->(c2:Chapter)
        RETURN length(path) as path_length
        ORDER BY path_length DESC
        LIMIT 1
    """, {"id": textbook_id})
    
    if result:
        print(f"  Chapter sequence: Chapter 1 -> ... -> Chapter 14 ({result[0]['path_length']} PRECEDES links)")
    
    # Section sequence
    result = await connection.execute_query("""
        MATCH (s:Section {textbook_id: $id})-[:NEXT]->(s2:Section)
        RETURN count(*) as count
    """, {"id": textbook_id})
    
    section_links = result[0]['count'] if result else 0
    print(f"  Section sequence: {section_links} NEXT links between sections")
    
    # Concept sequence
    result = await connection.execute_query("""
        MATCH (co:Concept {textbook_id: $id})-[:NEXT]->(co2:Concept)
        RETURN count(*) as count
    """, {"id": textbook_id})
    
    concept_links = result[0]['count'] if result else 0
    print(f"  Concept sequence: {concept_links} NEXT links between concepts")
    
    # Show longest concept chain
    result = await connection.execute_query("""
        MATCH path = (co:Concept {textbook_id: $id})-[:NEXT*]->(co2:Concept)
        WHERE NOT (:Concept)-[:NEXT]->(co)
        RETURN co.section_number as start_section, length(path) as chain_length
        ORDER BY chain_length DESC
        LIMIT 1
    """, {"id": textbook_id})
    
    if result:
        print(f"  Longest concept chain: {result[0]['chain_length']} concepts starting from section {result[0]['start_section']}")
    
    # Show graph connectivity
    print("\\n3. GRAPH CONNECTIVITY:")
    print("-" * 50)
    
    # Check if all chapters are connected
    result = await connection.execute_query("""
        MATCH (c:Chapter {textbook_id: $id})
        OPTIONAL MATCH (c)-[:PRECEDES]->(next:Chapter)
        OPTIONAL MATCH (prev:Chapter)-[:PRECEDES]->(c)
        WITH c, next IS NOT NULL as has_next, prev IS NOT NULL as has_prev
        RETURN 
            sum(CASE WHEN has_next OR has_prev THEN 1 ELSE 0 END) as connected,
            count(c) as total
    """, {"id": textbook_id})
    
    if result:
        r = result[0]
        print(f"  Chapters: {r['connected']}/{r['total']} connected via PRECEDES")
    
    # Check section connectivity
    result = await connection.execute_query("""
        MATCH (s:Section {textbook_id: $id})
        OPTIONAL MATCH (s)-[:NEXT]->(next:Section)
        OPTIONAL MATCH (prev:Section)-[:NEXT]->(s)
        OPTIONAL MATCH (c:Chapter)-[:HAS_SECTION]->(s)
        WITH s, 
             (next IS NOT NULL OR prev IS NOT NULL) as has_sequential,
             c IS NOT NULL as has_parent
        RETURN 
            sum(CASE WHEN has_sequential THEN 1 ELSE 0 END) as sequential,
            sum(CASE WHEN has_parent THEN 1 ELSE 0 END) as hierarchical,
            count(s) as total
    """, {"id": textbook_id})
    
    if result:
        r = result[0]
        print(f"  Sections: {r['sequential']}/{r['total']} in sequence, {r['hierarchical']}/{r['total']} linked to chapters")
    
    # Check concept connectivity
    result = await connection.execute_query("""
        MATCH (co:Concept {textbook_id: $id})
        OPTIONAL MATCH (co)-[:NEXT]->(next:Concept)
        OPTIONAL MATCH (prev:Concept)-[:NEXT]->(co)
        OPTIONAL MATCH (s:Section)-[:CONTAINS_CONCEPT]->(co)
        WITH co,
             (next IS NOT NULL OR prev IS NOT NULL) as has_sequential,
             s IS NOT NULL as has_parent
        RETURN 
            sum(CASE WHEN has_sequential THEN 1 ELSE 0 END) as sequential,
            sum(CASE WHEN has_parent THEN 1 ELSE 0 END) as hierarchical,
            count(co) as total
    """, {"id": textbook_id})
    
    if result:
        r = result[0]
        print(f"  Concepts: {r['sequential']}/{r['total']} in sequence, {r['hierarchical']}/{r['total']} linked to sections")
    
    # Sample traversal
    print("\\n4. SAMPLE COMPLETE TRAVERSAL:")
    print("-" * 50)
    
    # Get a complete path from textbook to chunk through all levels
    result = await connection.execute_query("""
        MATCH path = (t:Textbook {textbook_id: $id})
                     -[:HAS_CHAPTER]->(c:Chapter {chapter_number: 1})
                     -[:HAS_SECTION]->(s:Section)
                     -[:CONTAINS_CONCEPT]->(co:Concept)
        MATCH (ch:Chunk)-[:BELONGS_TO]->(s)
        RETURN t.title as textbook,
               c.title as chapter,
               s.section_number as section,
               co.concept_name as concept,
               substring(ch.text, 0, 50) as chunk_preview
        LIMIT 1
    """, {"id": textbook_id})
    
    if result:
        r = result[0]
        print("  Complete path example:")
        print(f"    Textbook: {r['textbook']}")
        print(f"    └─> Chapter: {r['chapter']}")
        print(f"        └─> Section: {r['section']}")
        print(f"            └─> Concept: {r['concept'][:50]}...")
        print(f"            └─> Chunk: {r['chunk_preview']}...")
    
    # Summary statistics
    print("\\n5. FINAL STATISTICS:")
    print("-" * 50)
    
    # Node counts
    node_types = ['Textbook', 'Chapter', 'Section', 'Concept', 'Chunk']
    print("\\nNodes:")
    total_nodes = 0
    for node_type in node_types:
        if node_type == 'Textbook':
            query = f"MATCH (n:{node_type}) WHERE n.textbook_id = $id RETURN count(n) as count"
        else:
            query = f"MATCH (n:{node_type} {{textbook_id: $id}}) RETURN count(n) as count"
        
        result = await connection.execute_query(query, {"id": textbook_id})
        count = result[0]['count'] if result else 0
        print(f"  {node_type}: {count}")
        total_nodes += count
    print(f"  TOTAL: {total_nodes}")
    
    print(f"\\nRelationships: {total_rels}")
    print(f"\\nGraph Density: {total_rels / (total_nodes * (total_nodes - 1)) * 100:.2f}%")
    
    await connection.close()

asyncio.run(verify_complete())
'''

# Create and run
script_path = "/tmp/verify_complete.py"
with open(script_path, 'w') as f:
    f.write(SCRIPT)

subprocess.run(f"docker cp {script_path} learntrac-api:/tmp/verify_complete.py", shell=True)
result = subprocess.run("docker exec learntrac-api python /tmp/verify_complete.py", shell=True, capture_output=True, text=True)

if result.stdout:
    print(result.stdout)
    
os.remove(script_path)