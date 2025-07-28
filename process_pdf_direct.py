#!/usr/bin/env python3
"""
Direct PDF processing script to run inside the container
This bypasses API authentication and processes the PDF directly
"""

SCRIPT_CONTENT = '''
import asyncio
import os
import sys
import time
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the app source to Python path
sys.path.insert(0, '/app')

# Import required components
from src.services.trac_service import TracService
from src.pdf_processing.neo4j_connection_manager import ConnectionConfig
from src.pdf_processing.neo4j_content_ingestion import TextbookMetadata
from src.db.database import DatabaseManager
from src.services.embedding_service import EmbeddingService
from src.config import settings

async def process_pdf():
    """Process the Introduction to Computer Science PDF"""
    
    pdf_path = "/app/textbooks/Introduction_To_Computer_Science.pdf"
    
    print("Direct PDF Processing")
    print("=" * 60)
    print(f"Processing: {pdf_path}")
    print(f"File exists: {os.path.exists(pdf_path)}")
    
    if not os.path.exists(pdf_path):
        print("Error: PDF file not found!")
        return
    
    try:
        # Initialize database manager
        print("\\n1. Initializing database manager...")
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Initialize embedding service
        print("\\n2. Initializing embedding service...")
        embedding_service = EmbeddingService()
        
        # Create Neo4j config from environment
        print("\\n3. Setting up Neo4j connection...")
        neo4j_config = ConnectionConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j")
        )
        
        print(f"   Neo4j URI: {neo4j_config.uri}")
        print(f"   Database: {neo4j_config.database}")
        
        # Create TracService
        print("\\n4. Initializing TracService...")
        trac_service = TracService(
            db_manager,
            neo4j_config,
            embedding_service
        )
        
        await trac_service.initialize()
        
        # Create textbook metadata
        print("\\n5. Creating textbook metadata...")
        textbook_metadata = TextbookMetadata(
            textbook_id="",  # Will be generated
            title="Introduction to Computer Science",
            subject="Computer Science",
            authors=["Unknown"],
            source_file="Introduction_To_Computer_Science.pdf",
            processing_date=datetime.utcnow(),
            processing_version="1.0",
            quality_metrics={},
            statistics={}
        )
        
        # Process the textbook
        print("\\n6. Processing PDF (this may take several minutes)...")
        print("   - Extracting text from PDF")
        print("   - Cleaning and normalizing text")
        print("   - Detecting document structure")
        print("   - Chunking content")
        print("   - Generating embeddings")
        print("   - Storing in Neo4j")
        
        start_time = time.time()
        result = await trac_service.ingest_textbook(pdf_path, textbook_metadata)
        elapsed_time = time.time() - start_time
        
        # Display results
        print(f"\\n7. Processing completed in {elapsed_time:.2f} seconds")
        print("\\nResults:")
        print("-" * 40)
        
        if result.get('success'):
            print(f"✓ Success: {result['success']}")
            print(f"✓ Textbook ID: {result.get('textbook_id', 'N/A')}")
            
            if 'statistics' in result:
                stats = result['statistics']
                print("\\nStatistics:")
                print(f"  - Chapters: {stats.get('chapters', 0)}")
                print(f"  - Sections: {stats.get('sections', 0)}")
                print(f"  - Chunks: {stats.get('chunks', 0)}")
                print(f"  - Concepts: {stats.get('concepts', 0)}")
                print(f"  - Processing time: {stats.get('processing_time', 0):.2f} seconds")
            
            if 'summary' in result:
                print(f"\\nSummary:\\n{result['summary']}")
                
            # Save result to file
            import json
            with open('/app/processing_result.json', 'w') as f:
                json.dump(result, f, indent=2)
            print("\\n✓ Results saved to /app/processing_result.json")
            
        else:
            print(f"✗ Processing failed: {result.get('error', 'Unknown error')}")
            if 'details' in result:
                print(f"Details: {result['details']}")
        
        # Close connections
        await trac_service.close()
        await db_manager.close()
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()

# Run the processing
if __name__ == "__main__":
    asyncio.run(process_pdf())
'''

import subprocess
import os

def run_direct_processing():
    """Run the PDF processing directly in the container"""
    
    print("Running direct PDF processing in Docker container...")
    
    # First, copy the PDF to the container
    print("\n1. Copying PDF to container...")
    pdf_path = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/textbooks/Introduction_To_Computer_Science.pdf"
    
    copy_cmd = f"docker cp {pdf_path} learntrac-api:/app/textbooks/"
    result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Failed to copy PDF: {result.stderr}")
        return
    
    print("✓ PDF copied to container")
    
    # Create the processing script
    print("\n2. Creating processing script...")
    script_path = "/tmp/process_pdf_in_container.py"
    with open(script_path, 'w') as f:
        f.write(SCRIPT_CONTENT)
    
    # Copy script to container
    copy_script_cmd = f"docker cp {script_path} learntrac-api:/tmp/process_pdf.py"
    subprocess.run(copy_script_cmd, shell=True)
    
    # Run the script
    print("\n3. Running PDF processing...")
    exec_cmd = "docker exec learntrac-api python /tmp/process_pdf.py"
    result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    # Copy results back
    print("\n4. Retrieving results...")
    copy_results_cmd = "docker cp learntrac-api:/app/processing_result.json ./processing_result.json"
    result = subprocess.run(copy_results_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0 and os.path.exists("./processing_result.json"):
        print("✓ Results retrieved successfully")
        print("\nProcessing complete! Check processing_result.json for details.")
    else:
        print("⚠️ Could not retrieve results file")
    
    # Clean up
    os.remove(script_path)

if __name__ == "__main__":
    run_direct_processing()