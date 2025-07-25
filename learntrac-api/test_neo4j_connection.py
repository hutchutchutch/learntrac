#!/usr/bin/env python3
"""
Test script for Neo4j Aura connection and vector search
Tests the implementation from Task 5
"""

import asyncio
import os
import sys
from typing import List
import numpy as np

# Add the src directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.neo4j_aura_client import neo4j_aura_client


async def test_connection():
    """Test basic Neo4j connection"""
    print("Testing Neo4j Aura Connection...\n")
    
    # Check if environment variables are set
    neo4j_uri = os.getenv('NEO4J_URI')
    neo4j_user = os.getenv('NEO4J_USER')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        print("❌ Neo4j environment variables not set!")
        print("Please set: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        return False
    
    print(f"✓ Neo4j URI: {neo4j_uri}")
    print(f"✓ Neo4j User: {neo4j_user}")
    print(f"✓ Neo4j Password: {'*' * len(neo4j_password)}")
    
    # Test health check
    print("\nTesting health check...")
    health = await neo4j_aura_client.health_check()
    
    if health['status'] == 'healthy':
        print(f"✓ Connection healthy!")
        print(f"  Server time: {health.get('server_time')}")
        print(f"  Chunk count: {health.get('chunk_count')}")
        print(f"  GDS version: {health.get('gds_version')}")
        return True
    else:
        print(f"❌ Connection unhealthy: {health.get('error')}")
        return False


async def test_create_indexes():
    """Test creating vector indexes"""
    print("\nTesting index creation...")
    
    success = await neo4j_aura_client.create_vector_index()
    if success:
        print("✓ Indexes created successfully")
    else:
        print("❌ Failed to create indexes")
    
    return success


async def create_sample_chunks():
    """Create sample chunks for testing"""
    print("\nCreating sample chunks...")
    
    # Sample data
    chunks = [
        {
            "id": "chunk_001",
            "content": "Python functions are reusable blocks of code that perform specific tasks.",
            "subject": "Python Programming",
            "concept": "Functions",
            "embedding": np.random.rand(1536).tolist()  # Random embedding for testing
        },
        {
            "id": "chunk_002",
            "content": "Variables in Python store data values and can be of different types.",
            "subject": "Python Programming",
            "concept": "Variables",
            "embedding": np.random.rand(1536).tolist()
        },
        {
            "id": "chunk_003",
            "content": "Control flow statements like if-else help make decisions in code.",
            "subject": "Python Programming",
            "concept": "Control Flow",
            "embedding": np.random.rand(1536).tolist()
        }
    ]
    
    # Create chunks
    for chunk in chunks:
        success = await neo4j_aura_client.create_chunk(
            chunk_id=chunk["id"],
            content=chunk["content"],
            embedding=chunk["embedding"],
            subject=chunk["subject"],
            concept=chunk["concept"]
        )
        if success:
            print(f"✓ Created chunk: {chunk['id']}")
        else:
            print(f"❌ Failed to create chunk: {chunk['id']}")
    
    # Create prerequisite relationships
    print("\nCreating prerequisite relationships...")
    
    # Functions require understanding of Variables
    rel1 = await neo4j_aura_client.create_prerequisite_relationship(
        "chunk_001", "chunk_002", "STRONG"
    )
    if rel1:
        print("✓ Created: Functions -> Variables")
    
    # Control Flow requires understanding of Variables
    rel2 = await neo4j_aura_client.create_prerequisite_relationship(
        "chunk_003", "chunk_002", "STRONG"
    )
    if rel2:
        print("✓ Created: Control Flow -> Variables")


async def test_vector_search():
    """Test vector similarity search"""
    print("\nTesting vector search...")
    
    # Create a query embedding (random for testing)
    query_embedding = np.random.rand(1536).tolist()
    
    # Perform search
    results = await neo4j_aura_client.vector_search(
        embedding=query_embedding,
        min_score=0.0,  # Low threshold for testing with random embeddings
        limit=5
    )
    
    if results:
        print(f"✓ Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n  {i}. {result['id']}")
            print(f"     Content: {result['content'][:60]}...")
            print(f"     Score: {result['score']:.4f}")
            print(f"     Subject: {result.get('subject')}")
            print(f"     Concept: {result.get('concept')}")
    else:
        print("❌ No results found")
    
    return len(results) > 0


async def test_prerequisite_traversal():
    """Test prerequisite chain traversal"""
    print("\nTesting prerequisite traversal...")
    
    # Get prerequisites for Functions
    prereqs = await neo4j_aura_client.get_prerequisite_chain("chunk_001", max_depth=3)
    
    if prereqs:
        print(f"✓ Prerequisites for 'Functions':")
        for prereq in prereqs:
            print(f"  - {prereq['concept']} (depth: {prereq['depth']})")
    else:
        print("  No prerequisites found")
    
    # Get dependents for Variables
    dependents = await neo4j_aura_client.get_dependent_concepts("chunk_002", max_depth=3)
    
    if dependents:
        print(f"\n✓ Concepts that depend on 'Variables':")
        for dep in dependents:
            print(f"  - {dep['concept']} (depth: {dep['depth']})")
    else:
        print("  No dependents found")


async def test_bulk_search():
    """Test bulk vector search"""
    print("\nTesting bulk vector search...")
    
    # Create multiple query embeddings
    embeddings = [np.random.rand(1536).tolist() for _ in range(3)]
    
    results = await neo4j_aura_client.bulk_vector_search(
        embeddings=embeddings,
        min_score=0.0,
        limit_per_query=2
    )
    
    print(f"✓ Performed {len(results)} bulk searches")
    for i, batch in enumerate(results, 1):
        print(f"  Query {i}: Found {len(batch)} results")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Neo4j Aura Vector Search Test Suite")
    print("=" * 60)
    
    try:
        # Test connection
        if not await test_connection():
            print("\n❌ Connection test failed. Please check your Neo4j credentials.")
            return 1
        
        # Create indexes
        await test_create_indexes()
        
        # Create sample data
        await create_sample_chunks()
        
        # Test vector search
        await test_vector_search()
        
        # Test prerequisite traversal
        await test_prerequisite_traversal()
        
        # Test bulk search
        await test_bulk_search()
        
        print("\n" + "=" * 60)
        print("✓ All tests completed!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return 1
    
    finally:
        # Clean up
        await neo4j_aura_client.close()


if __name__ == "__main__":
    # Load environment variables from .env if it exists
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
    
    sys.exit(asyncio.run(main()))