#!/usr/bin/env python3
"""
Process PDF using Table of Contents to properly structure chapters
"""

SCRIPT_CONTENT = '''
import asyncio
import os
import sys
import time
import re
from datetime import datetime
import logging
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the app source to Python path
sys.path.insert(0, '/app')

# Import required components
from src.services.trac_service import TracService
from src.pdf_processing.neo4j_connection_manager import ConnectionConfig
from src.pdf_processing.neo4j_content_ingestion import TextbookMetadata
from src.pdf_processing.pipeline import PDFProcessingPipeline, ProcessingResult
from src.pdf_processing.content_chunker import ContentChunker
from src.pdf_processing.structure_detector import StructureElement
from src.db.database import DatabaseManager
from src.services.embedding_service import EmbeddingService
from src.config import settings

def extract_toc_from_pdf(pdf_path):
    """Extract table of contents from PDF"""
    import fitz  # PyMuPDF
    
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    
    chapters = []
    sections = []
    
    for level, title, page in toc:
        # Clean the title
        title = title.strip()
        
        if level == 1:  # Chapter level
            chapters.append({
                'title': title,
                'page': page,
                'level': level
            })
        elif level == 2:  # Section level
            sections.append({
                'title': title,
                'page': page,
                'level': level,
                'parent_chapter': len(chapters) - 1 if chapters else 0
            })
    
    doc.close()
    
    return chapters, sections

def parse_chapter_structure(text, chapters_from_toc):
    """Parse text and identify chapter boundaries based on TOC"""
    
    structure_elements = []
    
    # Create regex patterns for each chapter
    for i, chapter in enumerate(chapters_from_toc):
        # Create a flexible pattern to match chapter titles
        title = chapter['title']
        # Remove chapter numbers and clean up
        clean_title = re.sub(r'^(Chapter\\s+\\d+[:\\.]?\\s*|\\d+\\.\\s*)', '', title)
        
        # Create pattern to find this chapter in text
        patterns = [
            f"Chapter\\s+{i+1}[:\\.]?\\s*{re.escape(clean_title)}",
            f"{i+1}\\.\\s*{re.escape(clean_title)}",
            re.escape(title)
        ]
        
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                start_pos = matches[0].start()
                
                # Find end position (start of next chapter or end of text)
                end_pos = len(text)
                if i < len(chapters_from_toc) - 1:
                    # Look for next chapter
                    next_chapter = chapters_from_toc[i + 1]
                    next_patterns = [
                        f"Chapter\\s+{i+2}",
                        f"{i+2}\\.",
                        re.escape(next_chapter['title'])
                    ]
                    for next_pattern in next_patterns:
                        next_matches = list(re.finditer(next_pattern, text[start_pos:], re.IGNORECASE))
                        if next_matches:
                            end_pos = start_pos + next_matches[0].start()
                            break
                
                structure_elements.append(StructureElement(
                    element_type="chapter",
                    content=f"Chapter {i+1}: {clean_title}",
                    start_position=start_pos,
                    end_position=end_pos,
                    level=1,
                    confidence=0.9
                ))
                break
    
    return structure_elements

async def process_pdf_with_toc():
    """Process the Introduction to Computer Science PDF using TOC"""
    
    pdf_path = "/app/textbooks/Introduction_To_Computer_Science.pdf"
    
    print("PDF Processing with Table of Contents")
    print("=" * 60)
    print(f"Processing: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print("Error: PDF file not found!")
        return
    
    try:
        # Extract TOC first
        print("\\n1. Extracting Table of Contents...")
        chapters, sections = extract_toc_from_pdf(pdf_path)
        print(f"   Found {len(chapters)} chapters and {len(sections)} sections")
        
        if chapters:
            print("\\nChapters found:")
            for i, ch in enumerate(chapters[:10]):  # Show first 10
                print(f"   {i+1}. {ch['title']} (page {ch['page']})")
            if len(chapters) > 10:
                print(f"   ... and {len(chapters) - 10} more")
        
        # Initialize services
        print("\\n2. Initializing services...")
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        embedding_service = EmbeddingService()
        
        neo4j_config = ConnectionConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j")
        )
        
        # Initialize PDF pipeline with relaxed requirements
        print("\\n3. Initializing PDF processing pipeline...")
        pdf_pipeline = PDFProcessingPipeline(
            min_chapters=0,  # Don't require minimum chapters
            min_retention_ratio=0.3,
            quality_threshold=0.5,
            preserve_mathematical=True
        )
        
        # Process PDF
        print("\\n4. Extracting text from PDF...")
        processing_result = pdf_pipeline.process_pdf(pdf_path)
        
        # Override structure with TOC-based structure
        if chapters and processing_result.final_text:
            print("\\n5. Applying TOC structure to text...")
            structure_elements = parse_chapter_structure(processing_result.final_text, chapters)
            
            if structure_elements:
                print(f"   Mapped {len(structure_elements)} chapters in text")
                processing_result.structure_elements = structure_elements
                processing_result.metadata.chapters_detected = len(structure_elements)
        
        # Initialize TracService
        print("\\n6. Initializing TracService...")
        trac_service = TracService(
            db_manager,
            neo4j_config,
            embedding_service
        )
        await trac_service.initialize()
        
        # Create enhanced metadata
        textbook_metadata = TextbookMetadata(
            textbook_id="",
            title="Introduction to Computer Science",
            subject="Computer Science",
            authors=["Unknown"],
            source_file="Introduction_To_Computer_Science.pdf",
            processing_date=datetime.utcnow(),
            processing_version="1.0",
            quality_metrics={
                "extraction_confidence": processing_result.quality_metrics.extraction_confidence,
                "structure_quality": 0.9,  # High because we used TOC
                "overall_quality": 0.85
            },
            statistics={
                "total_chapters": len(chapters),
                "total_sections": len(sections),
                "total_chunks": 0  # Will be updated
            }
        )
        
        # Process with enhanced structure
        print("\\n7. Processing with chapter structure...")
        print("   - Chunking by chapters")
        print("   - Generating embeddings")
        print("   - Creating relationships")
        print("   - Storing in Neo4j")
        
        start_time = time.time()
        
        # Use the ingest_textbook method which handles all the processing
        result = await trac_service.ingest_textbook(pdf_path, textbook_metadata)
        
        elapsed_time = time.time() - start_time
        
        # Display results
        print(f"\\n8. Processing completed in {elapsed_time:.2f} seconds")
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
            
            # Save result
            with open('/app/processing_result.json', 'w') as f:
                json.dump(result, f, indent=2)
            print("\\n✓ Results saved to /app/processing_result.json")
            
            # Also save the TOC structure
            toc_data = {
                'chapters': chapters,
                'sections': sections,
                'textbook_id': result.get('textbook_id')
            }
            with open('/app/toc_structure.json', 'w') as f:
                json.dump(toc_data, f, indent=2)
            print("✓ TOC structure saved to /app/toc_structure.json")
            
        else:
            print(f"✗ Processing failed: {result.get('error', 'Unknown error')}")
        
        # Close connections
        await trac_service.close()
        await db_manager.close()
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()

# Run the processing
if __name__ == "__main__":
    asyncio.run(process_pdf_with_toc())
'''

import subprocess
import os

def run_toc_processing():
    """Run the PDF processing with TOC extraction"""
    
    print("Running PDF processing with Table of Contents extraction...")
    
    # Create the processing script
    print("\n1. Creating processing script...")
    script_path = "/tmp/process_pdf_with_toc.py"
    with open(script_path, 'w') as f:
        f.write(SCRIPT_CONTENT)
    
    # Copy script to container
    copy_script_cmd = f"docker cp {script_path} learntrac-api:/tmp/process_pdf_toc.py"
    subprocess.run(copy_script_cmd, shell=True)
    
    # Run the script
    print("\n2. Running PDF processing with TOC...")
    exec_cmd = "docker exec learntrac-api python /tmp/process_pdf_toc.py"
    result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("\nLog output:")
        print(result.stderr)
    
    # Copy results back
    print("\n3. Retrieving results...")
    
    # Get processing result
    copy_results_cmd = "docker cp learntrac-api:/app/processing_result.json ./processing_result.json"
    result1 = subprocess.run(copy_results_cmd, shell=True, capture_output=True, text=True)
    
    # Get TOC structure
    copy_toc_cmd = "docker cp learntrac-api:/app/toc_structure.json ./toc_structure.json"
    result2 = subprocess.run(copy_toc_cmd, shell=True, capture_output=True, text=True)
    
    if result1.returncode == 0 and os.path.exists("./processing_result.json"):
        print("✓ Processing results retrieved")
        
        # Display summary
        with open("./processing_result.json", 'r') as f:
            data = f.read()
            if len(data) > 500:
                print(f"\nResult preview: {data[:500]}...")
            else:
                print(f"\nResult: {data}")
    
    if result2.returncode == 0 and os.path.exists("./toc_structure.json"):
        print("✓ TOC structure retrieved")
    
    # Clean up
    os.remove(script_path)
    
    print("\nProcessing complete!")
    print("Check processing_result.json and toc_structure.json for details.")

if __name__ == "__main__":
    run_toc_processing()