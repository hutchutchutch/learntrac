#!/usr/bin/env python3
"""
Test TOC processor - processes first 3 chapters only
"""

import subprocess
import os

SCRIPT_CONTENT = '''
import asyncio
import os
import sys
import re
import hashlib
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the app source to Python path
sys.path.insert(0, '/app')

# Import required components
from src.pdf_processing.neo4j_connection_manager import ConnectionConfig, Neo4jConnectionManager
from src.pdf_processing.neo4j_vector_index_manager import Neo4jVectorIndexManager, VectorIndexConfig, VectorSimilarityFunction
from src.services.embedding_service import EmbeddingService
import fitz  # PyMuPDF

async def test_processing():
    """Test processing with first 3 chapters"""
    
    pdf_path = "/app/textbooks/Introduction_To_Computer_Science.pdf"
    textbook_id = f"cs_intro_test_{hashlib.md5(pdf_path.encode()).hexdigest()[:8]}"
    
    print("=" * 60)
    print("TEST: Processing first 3 chapters")
    print("=" * 60)
    
    # Open PDF
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    
    # Get first 3 chapters from TOC
    chapters = []
    for level, title, page in toc:
        if level == 1 and ("Chapter" in title):
            chapter_match = re.match(r'Chapter\\s+(\\d+)\\s*:?\\s*(.+)', title)
            if chapter_match:
                chapter_num = int(chapter_match.group(1))
                chapter_title = chapter_match.group(2).strip()
                chapters.append((chapter_num, chapter_title, page))
                if len(chapters) >= 3:
                    break
    
    print(f"\\nFound {len(chapters)} chapters to process:")
    for num, title, page in chapters:
        print(f"  Chapter {num}: {title} (page {page})")
    
    # Initialize Neo4j
    print("\\nConnecting to Neo4j...")
    config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    connection = Neo4jConnectionManager(config)
    if not await connection.initialize():
        print("Failed to connect to Neo4j!")
        return False
    
    print("✓ Connected to Neo4j")
    
    # Create textbook node
    print("\\nCreating textbook node...")
    await connection.execute_query("""
        MERGE (t:Textbook {textbook_id: $textbook_id})
        SET t.title = $title,
            t.subject = $subject,
            t.test_run = true,
            t.processed_date = datetime()
    """, {
        "textbook_id": textbook_id,
        "title": "Introduction to Computer Science (Test)",
        "subject": "Computer Science"
    })
    
    # Process each chapter
    for i, (num, title, start_page) in enumerate(chapters):
        print(f"\\nProcessing Chapter {num}...")
        
        # Create chapter node
        await connection.execute_query("""
            MERGE (c:Chapter {textbook_id: $textbook_id, chapter_number: $chapter_number})
            SET c.title = $title,
                c.start_page = $start_page
        """, {
            "textbook_id": textbook_id,
            "chapter_number": num,
            "title": title,
            "start_page": start_page
        })
        
        # Create HAS_CHAPTER relationship
        await connection.execute_query("""
            MATCH (t:Textbook {textbook_id: $textbook_id})
            MATCH (c:Chapter {textbook_id: $textbook_id, chapter_number: $chapter_number})
            MERGE (t)-[:HAS_CHAPTER]->(c)
        """, {
            "textbook_id": textbook_id,
            "chapter_number": num
        })
        
        # Create PRECEDES relationship with next chapter
        if i < len(chapters) - 1:
            next_num = chapters[i+1][0]
            await connection.execute_query("""
                MATCH (c1:Chapter {textbook_id: $textbook_id, chapter_number: $current})
                MATCH (c2:Chapter {textbook_id: $textbook_id, chapter_number: $next})
                MERGE (c1)-[:PRECEDES]->(c2)
            """, {
                "textbook_id": textbook_id,
                "current": num,
                "next": next_num
            })
            print(f"  Created PRECEDES relationship: Chapter {num} -> Chapter {next_num}")
        
        # Extract chapter content (first 5 pages only for test)
        end_page = min(start_page + 5, len(doc))
        content = ""
        for page_num in range(start_page - 1, end_page):
            page = doc[page_num]
            content += page.get_text()
        
        # Find sections (simplified pattern)
        section_pattern = rf'{num}\\.(\d+)\\s+([^\\n]+)'
        sections = []
        for match in re.finditer(section_pattern, content, re.MULTILINE):
            section_num = f"{num}.{match.group(1)}"
            section_title = match.group(2).strip()[:100]  # Limit title length
            sections.append((section_num, section_title))
        
        print(f"  Found {len(sections)} sections")
        
        # Create section nodes
        for j, (section_num, section_title) in enumerate(sections[:5]):  # Limit to 5 sections
            await connection.execute_query("""
                MERGE (s:Section {textbook_id: $textbook_id, section_number: $section_number})
                SET s.title = $title,
                    s.chapter_number = $chapter_number
            """, {
                "textbook_id": textbook_id,
                "section_number": section_num,
                "title": section_title,
                "chapter_number": num
            })
            
            # Create HAS_SECTION relationship
            await connection.execute_query("""
                MATCH (c:Chapter {textbook_id: $textbook_id, chapter_number: $chapter_number})
                MATCH (s:Section {textbook_id: $textbook_id, section_number: $section_number})
                MERGE (c)-[:HAS_SECTION]->(s)
            """, {
                "textbook_id": textbook_id,
                "chapter_number": num,
                "section_number": section_num
            })
            
            print(f"    Created section: {section_num} {section_title[:50]}...")
        
        # Create a few sample chunks
        print(f"  Creating sample chunks...")
        for j in range(3):  # Just 3 chunks per chapter for testing
            chunk_id = f"{textbook_id}_ch{num}_chunk{j}"
            chunk_content = content[j*500:(j+1)*500]  # 500 char chunks
            
            if chunk_content:
                await connection.execute_query("""
                    CREATE (ch:Chunk {
                        chunk_id: $chunk_id,
                        textbook_id: $textbook_id,
                        chapter_number: $chapter_number,
                        text: $content,
                        test_chunk: true
                    })
                """, {
                    "chunk_id": chunk_id,
                    "textbook_id": textbook_id,
                    "chapter_number": num,
                    "content": chunk_content
                })
                
                # Link chunk to chapter
                await connection.execute_query("""
                    MATCH (c:Chapter {textbook_id: $textbook_id, chapter_number: $chapter_number})
                    MATCH (ch:Chunk {chunk_id: $chunk_id})
                    MERGE (ch)-[:BELONGS_TO]->(c)
                """, {
                    "textbook_id": textbook_id,
                    "chapter_number": num,
                    "chunk_id": chunk_id
                })
    
    # Verify what was created
    print("\\nVerifying created data...")
    
    # Count nodes
    result = await connection.execute_query("""
        MATCH (t:Textbook {textbook_id: $textbook_id})
        MATCH (t)-[:HAS_CHAPTER]->(c:Chapter)
        MATCH (c)-[:HAS_SECTION]->(s:Section)
        WITH t, count(DISTINCT c) as chapters, count(DISTINCT s) as sections
        MATCH (ch:Chunk {textbook_id: $textbook_id})
        RETURN chapters, sections, count(ch) as chunks
    """, {"textbook_id": textbook_id})
    
    if result:
        stats = result[0]
        print(f"\\nCreated:")
        print(f"  - {stats['chapters']} chapters")
        print(f"  - {stats['sections']} sections")
        print(f"  - {stats['chunks']} chunks")
    
    # Check relationships
    result = await connection.execute_query("""
        MATCH (c1:Chapter {textbook_id: $textbook_id})-[r:PRECEDES]->(c2:Chapter)
        RETURN c1.chapter_number as from_chapter, c2.chapter_number as to_chapter
        ORDER BY c1.chapter_number
    """, {"textbook_id": textbook_id})
    
    if result:
        print("\\nPRECEDES relationships:")
        for rel in result:
            print(f"  Chapter {rel['from_chapter']} -> Chapter {rel['to_chapter']}")
    
    await connection.close()
    doc.close()
    
    print("\\n✓ Test processing completed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_processing())
    sys.exit(0 if success else 1)
'''

def run_test():
    """Run the test processor"""
    
    print("Running test TOC processor...")
    
    # Create script
    script_path = "/tmp/test_toc_processor.py"
    with open(script_path, 'w') as f:
        f.write(SCRIPT_CONTENT)
    
    # Copy to container
    copy_cmd = f"docker cp {script_path} learntrac-api:/tmp/test_toc_processor.py"
    subprocess.run(copy_cmd, shell=True)
    
    # Run
    exec_cmd = "docker exec learntrac-api python /tmp/test_toc_processor.py"
    result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("\nErrors:")
        print(result.stderr)
    
    # Clean up
    os.remove(script_path)
    
    return result.returncode == 0

if __name__ == "__main__":
    if run_test():
        print("\n✓ Test completed successfully!")
    else:
        print("\n✗ Test failed!")