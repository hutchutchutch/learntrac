#!/usr/bin/env python3
"""
Load sample computer science content into Neo4j for testing vector search
"""

import asyncio
import sys
import os
import hashlib
from neo4j import GraphDatabase
import openai

# Add the learntrac-api src to path
sys.path.insert(0, '/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/learntrac-api/src')

try:
    from services.embedding_service import EmbeddingService
    from services.neo4j_aura_client import Neo4jAuraClient
except ImportError:
    print("Could not import services, using standalone implementation")

# Neo4j connection
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jpassword"

# Sample computer science content for testing
SAMPLE_CS_CONTENT = [
    {
        "id": "chunk_bst_001",
        "concept": "Binary Search Trees",
        "subject": "Data Structures",
        "content": "A binary search tree (BST) is a binary tree data structure where each node has at most two children, referred to as the left child and the right child. For each node, all values in the left subtree are less than the node's value, and all values in the right subtree are greater than the node's value. This property makes BSTs efficient for search, insertion, and deletion operations, typically achieving O(log n) time complexity in balanced trees."
    },
    {
        "id": "chunk_sorting_001", 
        "concept": "Sorting Algorithms",
        "subject": "Algorithms",
        "content": "Sorting algorithms arrange elements in a particular order, typically ascending or descending. Common sorting algorithms include bubble sort (O(n²)), merge sort (O(n log n)), quick sort (average O(n log n)), and heap sort (O(n log n)). The choice of sorting algorithm depends on factors like data size, memory constraints, and stability requirements. Merge sort and heap sort guarantee O(n log n) performance, while quick sort is often faster in practice despite its O(n²) worst case."
    },
    {
        "id": "chunk_recursion_001",
        "concept": "Recursion", 
        "subject": "Programming Concepts",
        "content": "Recursion is a programming technique where a function calls itself to solve a problem by breaking it down into smaller, similar subproblems. A recursive function must have a base case to prevent infinite recursion and a recursive case that makes progress toward the base case. Classic examples include calculating factorials, Fibonacci numbers, and tree traversals. Recursion can make code more elegant and easier to understand, but it may use more memory due to function call overhead."
    },
    {
        "id": "chunk_algorithms_001",
        "concept": "Algorithm Complexity",
        "subject": "Computer Science Theory", 
        "content": "Algorithm complexity analysis measures the efficiency of algorithms in terms of time and space requirements. Big O notation describes the upper bound of an algorithm's growth rate. Common complexities include O(1) constant time, O(log n) logarithmic, O(n) linear, O(n log n) linearithmic, O(n²) quadratic, and O(2^n) exponential. Understanding complexity helps developers choose appropriate algorithms and data structures for different problem sizes and performance requirements."
    },
    {
        "id": "chunk_graphs_001",
        "concept": "Graph Data Structures",
        "subject": "Data Structures",
        "content": "Graphs are non-linear data structures consisting of vertices (nodes) connected by edges. Graphs can be directed or undirected, weighted or unweighted. Common representations include adjacency matrices and adjacency lists. Graph algorithms include depth-first search (DFS), breadth-first search (BFS), shortest path algorithms like Dijkstra's and Bellman-Ford, and minimum spanning tree algorithms like Kruskal's and Prim's. Graphs model many real-world problems including social networks, transportation systems, and computer networks."
    },
    {
        "id": "chunk_hashtables_001",
        "concept": "Hash Tables",
        "subject": "Data Structures", 
        "content": "Hash tables (hash maps) provide fast key-value storage using a hash function to map keys to array indices. Good hash functions distribute keys uniformly to minimize collisions. Collision resolution strategies include chaining (using linked lists) and open addressing (linear probing, quadratic probing). Hash tables typically provide O(1) average time complexity for insertion, deletion, and lookup operations, making them ideal for caches, databases, and sets. Load factor affects performance and should be managed through resizing."
    },
    {
        "id": "chunk_trees_001", 
        "concept": "Tree Data Structures",
        "subject": "Data Structures",
        "content": "Trees are hierarchical data structures with a root node and child nodes forming parent-child relationships. Common tree types include binary trees, binary search trees, AVL trees, red-black trees, and B-trees. Tree traversal methods include in-order, pre-order, and post-order (depth-first), and level-order (breadth-first). Trees are used in file systems, expression parsing, decision making, and database indexing. Balanced trees maintain optimal height for efficient operations."
    },
    {
        "id": "chunk_dp_001",
        "concept": "Dynamic Programming", 
        "subject": "Algorithms",
        "content": "Dynamic programming solves complex problems by breaking them into simpler subproblems and storing results to avoid redundant computations. The approach works when problems have optimal substructure and overlapping subproblems. Common techniques include memoization (top-down) and tabulation (bottom-up). Classic examples include the knapsack problem, longest common subsequence, edit distance, and coin change. Dynamic programming can transform exponential time algorithms into polynomial time solutions."
    }
]

def generate_mock_embedding(text, dimension=1536):
    """Generate a mock embedding vector for testing"""
    # Create a deterministic hash-based embedding for testing
    hash_val = hashlib.md5(text.encode()).hexdigest()
    # Convert hex to numbers and normalize
    embedding = []
    for i in range(0, len(hash_val), 8):
        chunk = hash_val[i:i+8]
        val = int(chunk, 16) / (16**8)  # Normalize to [0,1]
        embedding.append(val * 2 - 1)  # Scale to [-1,1]
    
    # Pad or truncate to desired dimension
    while len(embedding) < dimension:
        embedding.extend(embedding[:min(dimension - len(embedding), len(embedding))])
    
    return embedding[:dimension]

async def load_sample_content():
    """Load sample CS content into Neo4j"""
    print("🔧 Loading Sample Computer Science Content into Neo4j")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 1. Clear existing data
            print("\n🧹 Clearing existing data...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # 2. Create textbook node
            print("📚 Creating textbook node...")
            session.run("""
                CREATE (t:Textbook {
                    textbook_id: 'cs_intro_sample',
                    title: 'Introduction to Computer Science - Sample Content',
                    description: 'Sample content for testing vector search functionality',
                    created_at: datetime()
                })
            """)
            
            # 3. Load chunks with embeddings
            print(f"📄 Loading {len(SAMPLE_CS_CONTENT)} content chunks...")
            
            for i, chunk_data in enumerate(SAMPLE_CS_CONTENT, 1):
                print(f"   Processing chunk {i}: {chunk_data['concept']}")
                
                # Generate embedding
                embedding = generate_mock_embedding(chunk_data['content'])
                
                # Create chunk node
                session.run("""
                    MATCH (t:Textbook {textbook_id: 'cs_intro_sample'})
                    CREATE (c:Chunk {
                        id: $chunk_id,
                        content: $content,
                        concept: $concept,
                        subject: $subject,
                        embedding: $embedding,
                        textbook_id: 'cs_intro_sample',
                        created_at: datetime(),
                        chunk_index: $index
                    })
                    CREATE (t)-[:HAS_CHUNK]->(c)
                """, 
                chunk_id=chunk_data['id'],
                content=chunk_data['content'],
                concept=chunk_data['concept'], 
                subject=chunk_data['subject'],
                embedding=embedding,
                index=i
                )
                
                # Create concept node if not exists
                session.run("""
                    MERGE (concept:Concept {name: $concept_name})
                    ON CREATE SET concept.created_at = datetime()
                    WITH concept
                    MATCH (c:Chunk {id: $chunk_id})
                    CREATE (c)-[:MENTIONS_CONCEPT]->(concept)
                """,
                concept_name=chunk_data['concept'],
                chunk_id=chunk_data['id']
                )
            
            # 4. Create some prerequisite relationships
            print("🔗 Creating prerequisite relationships...")
            prerequisites = [
                ("chunk_bst_001", "chunk_trees_001"),  # BST requires understanding of trees
                ("chunk_sorting_001", "chunk_algorithms_001"),  # Sorting requires algorithm knowledge
                ("chunk_dp_001", "chunk_recursion_001"),  # DP often uses recursion
                ("chunk_graphs_001", "chunk_algorithms_001"),  # Graphs need algorithm understanding
            ]
            
            for dependent, prerequisite in prerequisites:
                session.run("""
                    MATCH (from:Chunk {id: $dependent}), (to:Chunk {id: $prerequisite})
                    CREATE (from)-[:HAS_PREREQUISITE {relationship_type: 'STRONG'}]->(to)
                """, dependent=dependent, prerequisite=prerequisite)
            
            # 5. Verify data was loaded
            result = session.run("MATCH (c:Chunk) RETURN count(c) as chunk_count")
            chunk_count = result.single()["chunk_count"]
            
            result = session.run("MATCH (concept:Concept) RETURN count(concept) as concept_count") 
            concept_count = result.single()["concept_count"]
            
            result = session.run("MATCH ()-[r:HAS_PREREQUISITE]->() RETURN count(r) as prereq_count")
            prereq_count = result.single()["prereq_count"]
            
            print(f"\n✅ Successfully loaded:")
            print(f"   📄 Chunks: {chunk_count}")
            print(f"   🧠 Concepts: {concept_count}")
            print(f"   🔗 Prerequisites: {prereq_count}")
            
            # 6. Test a sample vector search
            print(f"\n🔍 Testing vector search with sample query...")
            test_embedding = generate_mock_embedding("binary search tree data structure")
            
            result = session.run("""
                MATCH (c:Chunk)
                WHERE c.embedding IS NOT NULL
                WITH c, gds.similarity.cosine(c.embedding, $embedding) AS score
                WHERE score > 0.1
                RETURN c.id, c.concept, c.content, score
                ORDER BY score DESC
                LIMIT 3
            """, embedding=test_embedding)
            
            results = list(result)
            if results:
                print(f"   Found {len(results)} similar chunks:")
                for r in results:
                    print(f"   - {r['concept']} (score: {r['score']:.3f})")
            else:
                print("   No results found - vector search may need different similarity function")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        driver.close()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(load_sample_content())
    if success:
        print(f"\n🎉 Sample content loaded successfully!")
        print(f"You can now test the vector search API with queries like:")
        print(f"  - 'What are binary search trees?'")
        print(f"  - 'Explain sorting algorithms'") 
        print(f"  - 'How does recursion work?'")
    else:
        print(f"\n❌ Failed to load sample content")