#!/usr/bin/env python3
"""
Direct test of PDF processing pipeline without going through the API
This script tests the PDF processing components directly
"""

import asyncio
import sys
import os
from pathlib import Path
import time

# Add the learntrac-api source to Python path
sys.path.insert(0, '/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/learntrac-api')

# Import required components
from src.pdf_processing.pipeline import PDFProcessingPipeline
from src.pdf_processing.content_chunker import ContentChunker
from src.pdf_processing.neo4j_connection_manager import Neo4jConnectionManager, ConnectionConfig
from src.pdf_processing.neo4j_vector_index_manager import Neo4jVectorIndexManager, VectorIndexConfig
from src.pdf_processing.neo4j_content_ingestion import Neo4jContentIngestion, TextbookMetadata
from src.services.embedding_pipeline import EmbeddingPipeline
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
PDF_FILE = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/textbooks/Introduction_To_Computer_Science.pdf"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4jpassword")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def test_pdf_processing():
    """Test the PDF processing pipeline directly"""
    
    print("Direct PDF Processing Pipeline Test")
    print("=" * 60)
    
    # Check if file exists
    if not os.path.exists(PDF_FILE):
        print(f"Error: PDF file not found at {PDF_FILE}")
        sys.exit(1)
    
    # Check OpenAI API key
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    file_size = os.path.getsize(PDF_FILE) / (1024 * 1024)  # MB
    print(f"Processing PDF: {Path(PDF_FILE).name}")
    print(f"File size: {file_size:.2f} MB")
    
    try:
        # Step 1: Initialize PDF processing pipeline
        print("\n1. Initializing PDF processing pipeline...")
        pdf_pipeline = PDFProcessingPipeline(
            min_chapters=3,
            min_retention_ratio=0.5,
            quality_threshold=0.6,
            preserve_mathematical=True
        )
        
        # Step 2: Process the PDF
        print("\n2. Processing PDF (this may take a few minutes)...")
        start_time = time.time()
        processing_result = pdf_pipeline.process_pdf(PDF_FILE)
        processing_time = time.time() - start_time
        
        print(f"\nProcessing completed in {processing_time:.2f} seconds")
        print(f"Status: {processing_result.status.value}")
        print("\nProcessing Summary:")
        print(processing_result.processing_summary)
        
        if processing_result.status.value not in ["success", "partial_success"]:
            print("\nProcessing failed. Exiting.")
            return
        
        # Step 3: Chunk the content
        print("\n3. Chunking content...")
        chunker = ContentChunker(
            min_chunk_size=500,
            max_chunk_size=2000,
            overlap_size=200
        )
        
        chunks = chunker.chunk_text(
            processing_result.final_text,
            processing_result.structure_elements
        )
        
        print(f"Created {len(chunks)} chunks")
        
        # Step 4: Generate embeddings
        print("\n4. Generating embeddings for chunks...")
        embedding_pipeline = EmbeddingPipeline(
            openai_api_key=OPENAI_API_KEY,
            model="text-embedding-3-small"
        )
        
        embeddings = []
        for i, chunk in enumerate(chunks[:5]):  # Process only first 5 chunks for testing
            print(f"  Processing chunk {i+1}/5...")
            embedding_result = await embedding_pipeline.process_chunk(
                chunk.chunk_id,
                chunk.text,
                chunk
            )
            embeddings.append((chunk, chunk.text, embedding_result.embedding))
        
        print(f"Generated embeddings for {len(embeddings)} chunks (limited to 5 for testing)")
        
        # Step 5: Connect to Neo4j
        print("\n5. Connecting to Neo4j...")
        connection_config = ConnectionConfig(
            uri=NEO4J_URI,
            username="neo4j",
            password=NEO4J_PASSWORD,
            database="neo4j"
        )
        
        connection_manager = Neo4jConnectionManager(connection_config)
        await connection_manager.connect()
        
        # Verify connection
        if await connection_manager.verify_connection():
            print("✓ Neo4j connection successful")
        else:
            print("✗ Neo4j connection failed")
            return
        
        # Step 6: Initialize vector index
        print("\n6. Setting up vector index...")
        index_config = VectorIndexConfig(
            index_name="chunk_embeddings",
            node_label="Chunk",
            embedding_property="embedding",
            dimension=1536,
            similarity_function="cosine"
        )
        
        index_manager = Neo4jVectorIndexManager(connection_manager)
        if await index_manager.create_or_update_index(index_config):
            print("✓ Vector index created/updated successfully")
        
        # Step 7: Ingest content into Neo4j
        print("\n7. Ingesting content into Neo4j...")
        
        # Create textbook metadata
        textbook_metadata = TextbookMetadata(
            textbook_id=f"cs_intro_{int(time.time())}",
            title="Introduction to Computer Science",
            subject="Computer Science",
            authors=["Unknown"],
            source_file=PDF_FILE,
            processing_date=datetime.utcnow(),
            processing_version="1.0",
            quality_metrics={
                "extraction_confidence": processing_result.quality_metrics.extraction_confidence,
                "structure_quality": processing_result.quality_metrics.structure_detection_score,
                "overall_quality": processing_result.quality_metrics.overall_quality_score
            },
            statistics={
                "total_chapters": processing_result.metadata.chapters_detected,
                "total_sections": processing_result.metadata.sections_detected,
                "total_chunks": len(chunks)
            }
        )
        
        ingestion = Neo4jContentIngestion(connection_manager, index_manager)
        ingestion_result = await ingestion.ingest_processing_result(
            processing_result,
            embeddings,
            textbook_metadata
        )
        
        print("\nIngestion Result:")
        print(ingestion_result.summary())
        
        # Step 8: Test vector search
        print("\n8. Testing vector search...")
        test_query = "What is computer science?"
        print(f"Query: '{test_query}'")
        
        # Generate embedding for query
        query_embedding_result = await embedding_pipeline.process_text(test_query)
        
        # Search for similar chunks
        search_query = """
        CALL db.index.vector.queryNodes('chunk_embeddings', 5, $embedding)
        YIELD node, score
        RETURN node.chunk_id as chunk_id, node.text as text, score
        ORDER BY score DESC
        """
        
        results = await connection_manager.execute_query(
            search_query,
            {"embedding": query_embedding_result.embedding}
        )
        
        if results:
            print(f"\nFound {len(results)} similar chunks:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Chunk ID: {result['chunk_id']}")
                print(f"   Score: {result['score']:.4f}")
                print(f"   Text preview: {result['text'][:100]}...")
        else:
            print("No similar chunks found")
        
        # Clean up
        await connection_manager.close()
        print("\n✓ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_pdf_processing())