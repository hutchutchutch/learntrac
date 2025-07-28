#!/usr/bin/env python3
"""
Comprehensive check of all nodes and relationships in Neo4j
"""

from neo4j import GraphDatabase
import json

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jpassword"

def check_all_neo4j_content():
    """Check all content in Neo4j database"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🔍 Comprehensive Neo4j Database Check")
            print("="*60)
            
            # 1. Get all node labels
            result = session.run("CALL db.labels()")
            labels = [record[0] for record in result]
            print(f"\n📊 Node Labels in database: {labels}")
            
            # 2. Count nodes for each label
            print("\n📊 Node counts by label:")
            for label in labels:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                count = result.single()["count"]
                print(f"   - {label}: {count}")
                
                # Get sample nodes
                if count > 0:
                    result = session.run(f"""
                        MATCH (n:{label})
                        RETURN n
                        LIMIT 3
                    """)
                    print(f"     Sample {label} nodes:")
                    for i, record in enumerate(result, 1):
                        node = record["n"]
                        props = dict(node)
                        # Truncate large properties
                        for key, value in props.items():
                            if isinstance(value, (str, bytes)) and len(str(value)) > 100:
                                props[key] = str(value)[:100] + "..."
                            elif isinstance(value, list) and len(value) > 5:
                                props[key] = f"[List with {len(value)} items]"
                        print(f"       {i}. {props}")
            
            # 3. Check for nodes with embeddings (any property containing 'embed')
            print("\n📊 Checking for embedding properties:")
            for label in labels:
                result = session.run(f"""
                    MATCH (n:{label})
                    WITH n, keys(n) as props
                    UNWIND props as prop
                    WITH DISTINCT prop
                    WHERE prop CONTAINS 'embed' OR prop CONTAINS 'vector'
                    RETURN collect(prop) as embedding_props
                """)
                embedding_props = result.single()["embedding_props"]
                if embedding_props:
                    print(f"   - {label} has embedding properties: {embedding_props}")
                    
                    # Count nodes with embeddings
                    for prop in embedding_props:
                        result = session.run(f"""
                            MATCH (n:{label})
                            WHERE n.{prop} IS NOT NULL
                            RETURN count(n) as count
                        """)
                        count = result.single()["count"]
                        print(f"     * Nodes with {prop}: {count}")
            
            # 4. Check all relationship types
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [record[0] for record in result]
            print(f"\n📊 Relationship types: {rel_types}")
            
            # 5. Count relationships
            if rel_types:
                print("\n📊 Relationship counts:")
                for rel_type in rel_types:
                    result = session.run(f"""
                        MATCH ()-[r:{rel_type}]->()
                        RETURN count(r) as count
                    """)
                    count = result.single()["count"]
                    print(f"   - {rel_type}: {count}")
            
            # 6. Check for specific textbook-related nodes
            print("\n📊 Checking for textbook-related content:")
            
            # Check for nodes with textbook properties
            result = session.run("""
                MATCH (n)
                WHERE n.textbook_id IS NOT NULL OR n.textbook IS NOT NULL OR n.source CONTAINS 'textbook'
                RETURN labels(n) as labels, count(n) as count
                ORDER BY count DESC
            """)
            
            textbook_nodes = list(result)
            if textbook_nodes:
                print("   Found textbook-related nodes:")
                for record in textbook_nodes:
                    print(f"   - {record['labels']}: {record['count']}")
            
            # 7. Look for any PDF or document references
            result = session.run("""
                MATCH (n)
                WHERE n.filename CONTAINS '.pdf' OR n.document_name CONTAINS '.pdf' 
                   OR n.source CONTAINS '.pdf' OR n.pdf_path IS NOT NULL
                RETURN n
                LIMIT 5
            """)
            
            pdf_nodes = list(result)
            if pdf_nodes:
                print("\n   Found PDF-related nodes:")
                for record in pdf_nodes:
                    node = record["n"]
                    print(f"   - Labels: {list(node.labels)}")
                    print(f"     Properties: {dict(node)}")
            
            # 8. Search for any computer science content
            print("\n📊 Searching for computer science content:")
            result = session.run("""
                MATCH (n)
                WHERE n.content CONTAINS 'computer' OR n.content CONTAINS 'algorithm' 
                   OR n.content CONTAINS 'data structure' OR n.text CONTAINS 'computer'
                   OR n.description CONTAINS 'computer'
                RETURN labels(n) as labels, count(n) as count
            """)
            
            cs_content = list(result)
            if cs_content:
                print("   Found CS-related content:")
                for record in cs_content:
                    print(f"   - {record['labels']}: {record['count']} nodes")
                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        driver.close()

if __name__ == "__main__":
    check_all_neo4j_content()