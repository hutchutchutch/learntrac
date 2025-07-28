#!/usr/bin/env python3
"""
Check Neo4j vector store contents
"""

from neo4j import GraphDatabase
import json

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jpassword"

def check_vector_store():
    """Check what data exists in Neo4j vector store"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🔍 Checking Neo4j Vector Store Contents")
            print("="*60)
            
            # 1. Check for Chunk nodes
            result = session.run("MATCH (c:Chunk) RETURN count(c) as chunk_count")
            chunk_count = result.single()["chunk_count"]
            print(f"\n📊 Chunk nodes in database: {chunk_count}")
            
            # 2. Check for chunks with embeddings
            result = session.run("""
                MATCH (c:Chunk)
                WHERE c.embedding IS NOT NULL
                RETURN count(c) as embedded_count
            """)
            embedded_count = result.single()["embedded_count"]
            print(f"📊 Chunks with embeddings: {embedded_count}")
            
            # 3. Get sample chunks
            if chunk_count > 0:
                print("\n📋 Sample Chunks:")
                result = session.run("""
                    MATCH (c:Chunk)
                    RETURN c.id as id, c.content as content, 
                           c.subject as subject, c.concept as concept,
                           size(c.embedding) as embedding_size
                    LIMIT 5
                """)
                
                for i, record in enumerate(result, 1):
                    print(f"\n  {i}. ID: {record['id']}")
                    print(f"     Subject: {record['subject']}")
                    print(f"     Concept: {record['concept']}")
                    print(f"     Content: {record['content'][:100] if record['content'] else 'None'}...")
                    print(f"     Embedding Size: {record['embedding_size'] if record['embedding_size'] else 'None'}")
            
            # 4. Check for Concept nodes
            result = session.run("MATCH (c:Concept) RETURN count(c) as concept_count")
            concept_count = result.single()["concept_count"]
            print(f"\n📊 Concept nodes in database: {concept_count}")
            
            # 5. Check for Section nodes
            result = session.run("MATCH (s:Section) RETURN count(s) as section_count")
            section_count = result.single()["section_count"]
            print(f"📊 Section nodes in database: {section_count}")
            
            # 6. Check for Document nodes
            result = session.run("MATCH (d:Document) RETURN count(d) as doc_count")
            doc_count = result.single()["doc_count"]
            print(f"📊 Document nodes in database: {doc_count}")
            
            # 7. Check relationships
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as count
                ORDER BY count DESC
            """)
            
            print("\n📊 Relationships in database:")
            for record in result:
                print(f"   - {record['rel_type']}: {record['count']}")
            
            # 8. Check if vector index exists
            result = session.run("SHOW INDEXES")
            print("\n📊 Indexes in database:")
            for record in result:
                print(f"   - {record}")
            
            # 9. Test a simple vector search
            if embedded_count > 0:
                print("\n🧪 Testing vector search capability...")
                # Get a sample embedding
                result = session.run("""
                    MATCH (c:Chunk)
                    WHERE c.embedding IS NOT NULL
                    RETURN c.embedding as embedding
                    LIMIT 1
                """)
                sample_embedding = result.single()["embedding"]
                
                if sample_embedding:
                    # Try a vector search with the sample embedding
                    result = session.run("""
                        MATCH (c:Chunk)
                        WHERE c.embedding IS NOT NULL
                        WITH c, 
                             gds.similarity.cosine(c.embedding, $embedding) AS score
                        WHERE score > 0.5
                        RETURN c.id, score
                        ORDER BY score DESC
                        LIMIT 3
                    """, embedding=sample_embedding)
                    
                    matches = list(result)
                    print(f"   Vector search returned {len(matches)} results")
                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPossible issues:")
        print("1. Neo4j is not running")
        print("2. Incorrect credentials")
        print("3. Database schema not initialized")
        
    finally:
        driver.close()

if __name__ == "__main__":
    check_vector_store()