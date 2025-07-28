#!/usr/bin/env python3
"""
Find all existing data in Neo4j - comprehensive search
"""

from neo4j import GraphDatabase

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jpassword"

def find_all_data():
    """Find all data in Neo4j database"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🔍 Comprehensive Search for Existing Data in Neo4j")
            print("="*60)
            
            # 1. Get total node count
            result = session.run("MATCH (n) RETURN count(n) as total_nodes")
            total_nodes = result.single()["total_nodes"]
            print(f"\n📊 Total nodes in database: {total_nodes}")
            
            if total_nodes == 0:
                print("❌ Database appears to be empty")
                return
            
            # 2. Get all distinct labels
            result = session.run("MATCH (n) RETURN DISTINCT labels(n) as labels, count(n) as count ORDER BY count DESC")
            print("\n📊 All node labels and counts:")
            all_labels = []
            for record in result:
                labels = record["labels"]
                count = record["count"]
                print(f"   - {labels}: {count}")
                all_labels.extend(labels)
            
            # 3. For each label, show sample nodes
            unique_labels = list(set(all_labels))
            for label in unique_labels:
                print(f"\n📋 Sample nodes with label '{label}':")
                result = session.run(f"""
                    MATCH (n:{label})
                    WITH n, keys(n) as node_keys
                    RETURN n, node_keys
                    LIMIT 3
                """)
                
                for i, record in enumerate(result, 1):
                    node = record["n"]
                    keys = record["node_keys"]
                    props = dict(node)
                    
                    print(f"   {i}. Keys: {keys}")
                    for key, value in props.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"      {key}: {value[:100]}...")
                        elif isinstance(value, list) and len(value) > 5:
                            if key.lower().find('embed') != -1 or key.lower().find('vector') != -1:
                                print(f"      {key}: [vector with {len(value)} dimensions]")
                            else:
                                print(f"      {key}: [list with {len(value)} items: {value[:3]}...]")
                        else:
                            print(f"      {key}: {value}")
            
            # 4. Check for any embedding or vector properties
            print(f"\n🧠 Searching for embedding/vector properties:")
            result = session.run("""
                MATCH (n)
                WITH n, keys(n) as node_keys
                UNWIND node_keys as key
                WITH DISTINCT key
                WHERE key CONTAINS 'embed' OR key CONTAINS 'vector' OR key CONTAINS 'Embed' OR key CONTAINS 'Vector'
                RETURN key
            """)
            
            embedding_keys = [record["key"] for record in result]
            if embedding_keys:
                print(f"   Found embedding properties: {embedding_keys}")
                
                # Count nodes with embeddings
                for key in embedding_keys:
                    result = session.run(f"""
                        MATCH (n)
                        WHERE n.`{key}` IS NOT NULL
                        RETURN labels(n) as labels, count(n) as count
                    """)
                    for record in result:
                        print(f"   - Nodes with {key}: {record['labels']} ({record['count']} nodes)")
            else:
                print("   No embedding properties found")
            
            # 5. Check all relationships
            result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count ORDER BY count DESC")
            print(f"\n🔗 All relationships:")
            for record in result:
                print(f"   - {record['rel_type']}: {record['count']}")
            
            # 6. Search for text content
            print(f"\n📄 Searching for text content:")
            text_props = ['content', 'text', 'description', 'title', 'name']
            
            for prop in text_props:
                result = session.run(f"""
                    MATCH (n)
                    WHERE n.`{prop}` IS NOT NULL
                    RETURN labels(n) as labels, count(n) as count
                """)
                
                for record in result:
                    if record['count'] > 0:
                        print(f"   - Nodes with '{prop}': {record['labels']} ({record['count']} nodes)")
                        
                        # Show sample content
                        sample_result = session.run(f"""
                            MATCH (n)
                            WHERE n.`{prop}` IS NOT NULL
                            RETURN n.`{prop}` as content
                            LIMIT 1
                        """)
                        sample = sample_result.single()
                        if sample:
                            content = sample["content"]
                            if isinstance(content, str) and len(content) > 50:
                                print(f"     Sample: {content[:100]}...")
            
            # 7. Look for any computer science related content
            print(f"\n💻 Searching for CS-related content:")
            cs_terms = ['computer', 'algorithm', 'data', 'programming', 'binary', 'tree', 'sort', 'search']
            
            for term in cs_terms:
                # Check all text properties for this term
                for prop in text_props:
                    result = session.run(f"""
                        MATCH (n)
                        WHERE n.`{prop}` CONTAINS '{term}'
                        RETURN labels(n) as labels, count(n) as count
                    """)
                    
                    for record in result:
                        if record['count'] > 0:
                            print(f"   - Found '{term}' in {prop}: {record['labels']} ({record['count']} nodes)")
                            break  # Found it, move to next term
                else:
                    continue
                break  # Found this term, move to next term
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        driver.close()

if __name__ == "__main__":
    find_all_data()