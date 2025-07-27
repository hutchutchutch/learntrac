#!/usr/bin/env python3
"""Test Neo4j vector operations with Neo4j 5.12 compatibility"""

import asyncio
import random
from neo4j import AsyncGraphDatabase
import os
import sys

# Add the API source to path
sys.path.insert(0, '/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/learntrac-api')

from src.services.neo4j_client import Neo4jVectorStore

async def test_neo4j_vector():
    """Test Neo4j vector operations"""
    print("Testing Neo4j 5.12 compatible vector operations...")
    
    # Initialize client
    client = Neo4jVectorStore()
    
    try:
        # Initialize connection
        await client.initialize()
        print("✅ Neo4j connection initialized")
        
        # Test storing a content embedding
        test_embedding = [random.random() for _ in range(1536)]  # Random 1536-dim vector
        test_content_id = "test_content_001"
        
        success = await client.store_content_embedding(
            content_id=test_content_id,
            content_type="test",
            text="This is a test content for vector storage",
            embedding=test_embedding,
            metadata={
                "source": "test",
                "timestamp": "2024-01-01"
            }
        )
        
        if success:
            print("✅ Successfully stored content with embedding")
        else:
            print("❌ Failed to store content")
            return
        
        # Test similarity search
        query_embedding = [random.random() for _ in range(1536)]
        
        results = await client.find_similar_content(
            query_embedding=query_embedding,
            limit=5,
            threshold=0.0  # Low threshold since we're using random vectors
        )
        
        print(f"\n📊 Found {len(results)} similar content items")
        for i, result in enumerate(results):
            print(f"  {i+1}. Content ID: {result['content_id']}, Score: {result['score']:.4f}")
        
        # Clean up test data
        success = await client.delete_content(test_content_id)
        if success:
            print("\n✅ Cleaned up test data")
        
        print("\n✅ All vector operations working with Neo4j 5.12!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()

if __name__ == "__main__":
    # Set environment variables if not already set
    if not os.getenv('NEO4J_URI'):
        os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    if not os.getenv('NEO4J_USER'):
        os.environ['NEO4J_USER'] = 'neo4j'
    if not os.getenv('NEO4J_PASSWORD'):
        os.environ['NEO4J_PASSWORD'] = '8pQcA75CGQYcUNaZTHKYZSAo8tO9h-Z5oqkxk_G1c1o'
    
    asyncio.run(test_neo4j_vector())