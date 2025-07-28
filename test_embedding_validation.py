#!/usr/bin/env python3
"""
Test to validate that embeddings were created successfully
"""

import os
import asyncio
import sys
sys.path.append('./learntrac-api/src')

from pdf_processing.neo4j_connection_manager import Neo4jConnectionManager, ConnectionConfig

async def test_embeddings():
    """Test that embeddings were created in Neo4j"""
    print("Testing embedding validation...")
    
    # Create connection config from environment
    config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    connection = Neo4jConnectionManager(config)
    await connection.connect()
    
    try:
        # Check chunks with embeddings
        print("1. Checking chunks with embeddings...")
        query = """
            MATCH (c:Chunk)
            WHERE c.textbook_id = 'textbook_8ee79876'
            RETURN 
                count(c) as total_chunks,
                count(CASE WHEN c.embedding IS NOT NULL THEN 1 END) as chunks_with_embeddings,
                count(CASE WHEN c.has_embedding = true THEN 1 END) as chunks_marked_with_embeddings
        """
        
        result = await connection.execute_query(query)
        if result:
            stats = result[0]
            print(f"  Total chunks: {stats['total_chunks']}")
            print(f"  Chunks with embeddings: {stats['chunks_with_embeddings']}")
            print(f"  Chunks marked with embeddings: {stats['chunks_marked_with_embeddings']}")
        
        # Get sample chunk with embedding
        print("\n2. Getting sample chunk with embedding...")
        query = """
            MATCH (c:Chunk)
            WHERE c.textbook_id = 'textbook_8ee79876' 
            AND c.embedding IS NOT NULL
            RETURN c.chunk_id, c.text[..100] as text_preview, size(c.embedding) as embedding_size
            LIMIT 3
        """
        
        result = await connection.execute_query(query)
        for chunk in result:
            print(f"  Chunk ID: {chunk['chunk_id']}")
            print(f"  Text: {chunk['text_preview']}...")
            print(f"  Embedding size: {chunk['embedding_size']}")
            print()
        
        # Check vector indexes
        print("3. Checking indexes...")
        query = "SHOW INDEXES"
        result = await connection.execute_query(query)
        
        vector_indexes = [idx for idx in result if 'embedding' in idx.get('name', '').lower()]
        print(f"  Found {len(vector_indexes)} embedding-related indexes:")
        for idx in vector_indexes:
            print(f"    - {idx['name']}: {idx['state']}")
        
        # Test basic similarity calculation
        print("\n4. Testing manual similarity search...")
        query = """
            MATCH (c:Chunk)
            WHERE c.textbook_id = 'textbook_8ee79876' 
            AND c.embedding IS NOT NULL
            AND toLower(c.text) CONTAINS 'algorithm'
            RETURN c.chunk_id, c.text[..150] as text_preview
            LIMIT 3
        """
        
        result = await connection.execute_query(query)
        print(f"  Found {len(result)} chunks containing 'algorithm':")
        for chunk in result:
            print(f"    - {chunk['chunk_id']}: {chunk['text_preview']}...")
        
    finally:
        await connection.close()

if __name__ == "__main__":
    asyncio.run(test_embeddings())