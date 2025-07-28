#!/usr/bin/env python3
"""
Script to run PDF ingestion inside the learntrac-api Docker container
This ensures all dependencies and environment variables are properly set
"""

import subprocess
import sys
import os

# Configuration
PDF_FILE = "textbooks/Introduction_To_Computer_Science.pdf"
CONTAINER_NAME = "learntrac-api"

# Python script to run inside container
INGESTION_SCRIPT = '''
import asyncio
import os
import time
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import required components
from src.pdf_processing.pipeline import PDFProcessingPipeline
from src.pdf_processing.content_chunker import ContentChunker
from src.pdf_processing.neo4j_connection_manager import Neo4jConnectionManager, ConnectionConfig
from src.pdf_processing.neo4j_vector_index_manager import Neo4jVectorIndexManager, VectorIndexConfig
from src.pdf_processing.neo4j_content_ingestion import Neo4jContentIngestion, TextbookMetadata
from src.pdf_processing.embedding_pipeline import EmbeddingPipeline

async def ingest_pdf():
    pdf_path = "/app/textbooks/Introduction_To_Computer_Science.pdf"
    
    print("PDF Ingestion Test")
    print("=" * 60)
    print(f"Processing: {pdf_path}")
    
    try:
        # Initialize components
        print("\\n1. Initializing PDF processing pipeline...")
        pdf_pipeline = PDFProcessingPipeline(
            min_chapters=3,
            min_retention_ratio=0.5,
            quality_threshold=0.6
        )
        
        # Process PDF
        print("\\n2. Processing PDF...")
        start_time = time.time()
        processing_result = pdf_pipeline.process_pdf(pdf_path)
        print(f"Processing took {time.time() - start_time:.2f} seconds")
        print(f"Status: {processing_result.status.value}")
        
        if processing_result.status.value not in ["success", "partial_success"]:
            print("Processing failed!")
            return
        
        # Chunk content
        print("\\n3. Chunking content...")
        chunker = ContentChunker()
        chunks = chunker.chunk_text(
            processing_result.final_text,
            processing_result.structure_elements
        )
        print(f"Created {len(chunks)} chunks")
        
        # Generate embeddings for first 10 chunks
        print("\\n4. Generating embeddings (first 10 chunks)...")
        embedding_pipeline = EmbeddingPipeline()
        
        embeddings = []
        for i, chunk in enumerate(chunks[:10]):
            print(f"  Processing chunk {i+1}/10...")
            result = await embedding_pipeline.process_chunk(
                chunk.chunk_id,
                chunk.text,
                chunk
            )
            embeddings.append((chunk, chunk.text, result.embedding))
        
        # Connect to Neo4j
        print("\\n5. Connecting to Neo4j...")
        config = ConnectionConfig(
            uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            username="neo4j",
            password=os.getenv("NEO4J_PASSWORD", "neo4jpassword"),
            database="neo4j"
        )
        
        connection = Neo4jConnectionManager(config)
        await connection.connect()
        
        # Setup vector index
        print("\\n6. Setting up vector index...")
        index_manager = Neo4jVectorIndexManager(connection)
        index_config = VectorIndexConfig(
            index_name="chunk_embeddings",
            node_label="Chunk",
            embedding_property="embedding",
            dimension=1536,
            similarity_function="cosine"
        )
        await index_manager.create_or_update_index(index_config)
        
        # Ingest content
        print("\\n7. Ingesting content into Neo4j...")
        metadata = TextbookMetadata(
            textbook_id=f"cs_intro_{int(time.time())}",
            title="Introduction to Computer Science",
            subject="Computer Science",
            authors=["Unknown"],
            source_file=pdf_path,
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
        
        ingestion = Neo4jContentIngestion(connection, index_manager)
        result = await ingestion.ingest_processing_result(
            processing_result,
            embeddings,
            metadata
        )
        
        print("\\nIngestion Result:")
        print(result.summary())
        
        # Test search
        print("\\n8. Testing vector search...")
        query = "What is computer science?"
        query_result = await embedding_pipeline.process_text(query)
        
        search_query = """
        CALL db.index.vector.queryNodes('chunk_embeddings', 3, $embedding)
        YIELD node, score
        RETURN node.chunk_id as id, node.text as text, score
        """
        
        results = await connection.execute_query(
            search_query,
            {"embedding": query_result.embedding}
        )
        
        if results:
            print(f"\\nFound {len(results)} similar chunks for '{query}':")
            for r in results:
                print(f"\\n- Score: {r['score']:.4f}")
                print(f"  Text: {r['text'][:150]}...")
        
        await connection.close()
        print("\\n✓ Ingestion completed successfully!")
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        import traceback
        traceback.print_exc()

# Run the ingestion
asyncio.run(ingest_pdf())
'''

def run_ingestion():
    """Run the PDF ingestion inside Docker container"""
    
    print("Running PDF ingestion in Docker container...")
    print(f"Container: {CONTAINER_NAME}")
    print(f"PDF: {PDF_FILE}")
    
    # Check if container is running
    check_cmd = f"docker ps --filter name={CONTAINER_NAME} --format '{{{{.Names}}}}'"
    result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
    
    if CONTAINER_NAME not in result.stdout:
        print(f"Error: Container '{CONTAINER_NAME}' is not running")
        print("Please start it with: docker-compose up learntrac-api")
        sys.exit(1)
    
    # Copy the PDF file to container if needed
    print("\nCopying PDF to container...")
    copy_cmd = f"docker cp {PDF_FILE} {CONTAINER_NAME}:/app/textbooks/"
    subprocess.run(copy_cmd, shell=True)
    
    # Create a temporary Python script
    script_path = "/tmp/ingest_pdf.py"
    with open(script_path, 'w') as f:
        f.write(INGESTION_SCRIPT)
    
    # Copy script to container
    subprocess.run(f"docker cp {script_path} {CONTAINER_NAME}:/tmp/ingest_pdf.py", shell=True)
    
    # Run the script inside container
    print("\nRunning ingestion script...")
    exec_cmd = f"docker exec -it {CONTAINER_NAME} python /tmp/ingest_pdf.py"
    subprocess.run(exec_cmd, shell=True)
    
    # Clean up
    os.remove(script_path)

if __name__ == "__main__":
    run_ingestion()