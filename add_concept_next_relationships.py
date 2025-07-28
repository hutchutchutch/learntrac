#!/usr/bin/env python3
"""
Add missing NEXT relationships between sequential concepts
"""

import subprocess
import os

SCRIPT_CONTENT = '''
import asyncio
import os
import sys
sys.path.insert(0, '/app')

from src.pdf_processing.neo4j_connection_manager import ConnectionConfig, Neo4jConnectionManager

async def add_concept_relationships():
    """Add NEXT relationships between sequential concepts"""
    
    # Connect to Neo4j
    config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    connection = Neo4jConnectionManager(config)
    if not await connection.initialize():
        print("Failed to connect to Neo4j")
        return False
    
    print("\\n" + "=" * 60)
    print("ADDING CONCEPT NEXT RELATIONSHIPS")
    print("=" * 60)
    
    textbook_id = "cs_textbook_f4e2271b"
    
    # First, check current state
    result = await connection.execute_query("""
        MATCH (co1:Concept {textbook_id: $id})-[:NEXT]->(co2:Concept)
        RETURN count(*) as existing_count
    """, {"id": textbook_id})
    
    existing = result[0]['existing_count'] if result else 0
    print(f"\\nExisting NEXT relationships between concepts: {existing}")
    
    # Get all concepts ordered by section and position
    print("\\nFetching all concepts in order...")
    concepts = await connection.execute_query("""
        MATCH (co:Concept {textbook_id: $id})
        RETURN co.section_number as section, co.concept_name as name
        ORDER BY co.section_number, co.concept_name
    """, {"id": textbook_id})
    
    print(f"Found {len(concepts)} concepts to process")
    
    # Group concepts by section
    from collections import defaultdict
    sections_concepts = defaultdict(list)
    for concept in concepts:
        sections_concepts[concept['section']].append(concept['name'])
    
    print(f"\\nConcepts distributed across {len(sections_concepts)} sections:")
    for section in sorted(sections_concepts.keys())[:5]:
        print(f"  Section {section}: {len(sections_concepts[section])} concepts")
    if len(sections_concepts) > 5:
        print(f"  ... and {len(sections_concepts) - 5} more sections")
    
    # Create NEXT relationships within each section
    print("\\nCreating NEXT relationships within sections...")
    relationships_created = 0
    
    for section, concept_names in sections_concepts.items():
        if len(concept_names) < 2:
            continue
            
        # Create NEXT relationships for concepts in this section
        for i in range(len(concept_names) - 1):
            current = concept_names[i]
            next_concept = concept_names[i + 1]
            
            result = await connection.execute_query("""
                MATCH (co1:Concept {
                    textbook_id: $id,
                    section_number: $section,
                    concept_name: $current
                })
                MATCH (co2:Concept {
                    textbook_id: $id,
                    section_number: $section,
                    concept_name: $next
                })
                MERGE (co1)-[:NEXT]->(co2)
                RETURN co1, co2
            """, {
                "id": textbook_id,
                "section": section,
                "current": current,
                "next": next_concept
            })
            
            if result:
                relationships_created += 1
    
    print(f"  Created {relationships_created} NEXT relationships within sections")
    
    # Now create NEXT relationships between sections
    print("\\nCreating NEXT relationships between sections...")
    
    # Get the last concept of each section and first concept of next section
    section_list = sorted(sections_concepts.keys())
    cross_section_rels = 0
    
    for i in range(len(section_list) - 1):
        current_section = section_list[i]
        next_section = section_list[i + 1]
        
        # Skip if sections are not sequential (e.g., 1.1 to 2.2)
        # Extract chapter numbers
        curr_chapter = int(current_section.split('.')[0])
        next_chapter = int(next_section.split('.')[0])
        
        # Only connect if same chapter or sequential chapters
        if next_chapter - curr_chapter > 1:
            continue
        
        last_concept = sections_concepts[current_section][-1]
        first_concept = sections_concepts[next_section][0]
        
        result = await connection.execute_query("""
            MATCH (co1:Concept {
                textbook_id: $id,
                section_number: $curr_section,
                concept_name: $last
            })
            MATCH (co2:Concept {
                textbook_id: $id,
                section_number: $next_section,
                concept_name: $first
            })
            MERGE (co1)-[:NEXT]->(co2)
            RETURN co1, co2
        """, {
            "id": textbook_id,
            "curr_section": current_section,
            "last": last_concept,
            "next_section": next_section,
            "first": first_concept
        })
        
        if result:
            cross_section_rels += 1
            print(f"  Connected: Section {current_section} last concept -> Section {next_section} first concept")
    
    print(f"  Created {cross_section_rels} NEXT relationships between sections")
    
    # Verify the results
    print("\\n" + "-" * 60)
    print("VERIFICATION")
    print("-" * 60)
    
    # Count total NEXT relationships
    result = await connection.execute_query("""
        MATCH (co1:Concept {textbook_id: $id})-[:NEXT]->(co2:Concept)
        RETURN count(*) as total
    """, {"id": textbook_id})
    
    total_next = result[0]['total'] if result else 0
    print(f"\\nTotal NEXT relationships between concepts: {total_next}")
    print(f"New relationships created: {total_next - existing}")
    
    # Show sample concept chains
    print("\\nSample concept sequences:")
    
    # Get a few concept chains
    chains = await connection.execute_query("""
        MATCH path = (co1:Concept {textbook_id: $id})-[:NEXT*1..3]->(co2:Concept)
        WHERE NOT (:Concept)-[:NEXT]->(co1)  // Start nodes only
        RETURN co1.section_number as start_section, 
               [n in nodes(path) | n.concept_name] as concept_chain
        LIMIT 5
    """, {"id": textbook_id})
    
    for chain in chains:
        print(f"\\n  Section {chain['start_section']} chain:")
        for i, concept in enumerate(chain['concept_chain']):
            if i == 0:
                print(f"    → {concept[:50]}...")
            else:
                print(f"      → {concept[:50]}...")
    
    # Check for concepts without NEXT relationships
    result = await connection.execute_query("""
        MATCH (co:Concept {textbook_id: $id})
        WHERE NOT (co)-[:NEXT]->(:Concept)
          AND NOT (:Concept)-[:NEXT]->(co)
        RETURN count(co) as isolated_count
    """, {"id": textbook_id})
    
    isolated = result[0]['isolated_count'] if result else 0
    if isolated > 0:
        print(f"\\nWarning: {isolated} concepts have no NEXT relationships (likely single concepts in sections)")
    
    await connection.close()
    print("\\n✓ Concept NEXT relationships added successfully!")
    return True

if __name__ == "__main__":
    import sys
    success = asyncio.run(add_concept_relationships())
    sys.exit(0 if success else 1)
'''

def add_relationships():
    """Run the script to add concept relationships"""
    
    print("Adding NEXT relationships between concepts...")
    
    # Create script
    script_path = "/tmp/add_concept_next.py"
    with open(script_path, 'w') as f:
        f.write(SCRIPT_CONTENT)
    
    # Copy to container
    copy_cmd = f"docker cp {script_path} learntrac-api:/tmp/add_concept_next.py"
    subprocess.run(copy_cmd, shell=True)
    
    # Run script
    exec_cmd = "docker exec learntrac-api python /tmp/add_concept_next.py"
    result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("\nLog output:")
        print(result.stderr[-1000:])
    
    # Clean up
    os.remove(script_path)
    
    return result.returncode == 0

if __name__ == "__main__":
    if add_relationships():
        print("\n✓ Successfully added concept NEXT relationships!")
    else:
        print("\n✗ Failed to add relationships!")