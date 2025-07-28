#!/usr/bin/env python3
"""
TOC-based PDF processor that:
1. Parses table of contents
2. Splits PDF by chapters
3. Removes content before Chapter 1 and after appendix
4. Extracts sections and concepts
5. Creates proper chunks and relationships
"""

SCRIPT_CONTENT = '''
import asyncio
import os
import sys
import time
import re
import json
import hashlib
from datetime import datetime
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

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

@dataclass
class Chapter:
    """Represents a chapter with its content and metadata"""
    number: int
    title: str
    start_page: int
    end_page: Optional[int]
    content: str
    sections: List['Section'] = None
    
    def __post_init__(self):
        if self.sections is None:
            self.sections = []

@dataclass
class Section:
    """Represents a section within a chapter"""
    chapter_number: int
    section_number: str  # e.g., "1.1", "1.2.3"
    title: str
    start_pos: int
    end_pos: Optional[int]
    content: str
    concepts: List['Concept'] = None
    
    def __post_init__(self):
        if self.concepts is None:
            self.concepts = []

@dataclass
class Concept:
    """Represents a concept within a section"""
    section_number: str
    concept_name: str
    start_pos: int
    end_pos: Optional[int]
    content: str
    chunk_ids: List[str] = None
    
    def __post_init__(self):
        if self.chunk_ids is None:
            self.chunk_ids = []

@dataclass
class Chunk:
    """Represents a chunk of content with metadata"""
    chunk_id: str
    textbook_id: str
    chapter_number: int
    section_number: str
    concept_name: Optional[str]
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict = None

class TOCBasedPDFProcessor:
    """Main processor class that handles TOC-based PDF processing"""
    
    def __init__(self, pdf_path: str, textbook_id: str):
        self.pdf_path = pdf_path
        self.textbook_id = textbook_id
        self.doc = None
        self.chapters: List[Chapter] = []
        self.all_chunks: List[Chunk] = []
        self.concept_patterns = [
            r'\\b(?:Definition|Theorem|Lemma|Corollary|Proposition|Example|Algorithm|Concept)\\s*\\d*\\.?\\d*:?\\s*([^\\n]+)',
            r'\\b(?:Key Concept|Important Concept|Main Idea):\\s*([^\\n]+)',
            r'^\\d+\\.\\d+\\.\\d+\\s+([^\\n]+)$',  # Subsection that might be a concept
        ]
        self.chunk_size_range = (500, 1500)  # Min and max chunk sizes in characters
        
    async def process(self):
        """Main processing pipeline"""
        try:
            # Step 1: Parse TOC and extract chapters
            print("\\n1. Parsing Table of Contents...")
            self.parse_toc()
            
            # Step 2: Remove content before Chapter 1 and after appendix
            print("\\n2. Filtering content (removing pre-Chapter 1 and post-appendix)...")
            self.filter_content()
            
            # Step 3: Extract sections and concepts in parallel for each chapter
            print("\\n3. Extracting sections and concepts from chapters...")
            await self.extract_sections_and_concepts()
            
            # Step 4: Create chunks respecting boundaries
            print("\\n4. Creating chunks (respecting concept/section boundaries)...")
            self.create_chunks()
            
            # Step 5: Generate embeddings
            print("\\n5. Generating embeddings...")
            await self.generate_embeddings()
            
            # Step 6: Store in Neo4j with relationships
            print("\\n6. Storing in Neo4j with relationships...")
            await self.store_in_neo4j()
            
            return True
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.doc:
                self.doc.close()
    
    def parse_toc(self):
        """Parse table of contents and extract chapter information"""
        self.doc = fitz.open(self.pdf_path)
        toc = self.doc.get_toc()
        
        # Extract chapters from TOC
        chapter_entries = []
        for level, title, page in toc:
            # Look for chapter entries (level 1, contains "Chapter" or starts with number)
            if level == 1 and ("Chapter" in title or re.match(r'^\\d+\\.?\\s', title)):
                # Skip appendix and everything after
                if "Appendix" in title or "Bibliography" in title or "Index" in title:
                    break
                    
                chapter_match = re.match(r'Chapter\\s+(\\d+)\\s*:?\\s*(.+)', title) or \\
                               re.match(r'^(\\d+)\\.?\\s+(.+)', title)
                if chapter_match:
                    chapter_num = int(chapter_match.group(1))
                    chapter_title = chapter_match.group(2).strip()
                    chapter_entries.append((chapter_num, chapter_title, page))
        
        # Create Chapter objects with content
        for i, (num, title, start_page) in enumerate(chapter_entries):
            # Determine end page
            end_page = chapter_entries[i+1][2] if i+1 < len(chapter_entries) else len(self.doc)
            
            # Extract chapter content
            content = ""
            for page_num in range(start_page - 1, min(end_page, len(self.doc))):
                page = self.doc[page_num]
                content += page.get_text()
            
            chapter = Chapter(
                number=num,
                title=title,
                start_page=start_page,
                end_page=end_page,
                content=content
            )
            self.chapters.append(chapter)
        
        print(f"   Found {len(self.chapters)} chapters")
        for ch in self.chapters[:5]:
            print(f"   Chapter {ch.number}: {ch.title} (pages {ch.start_page}-{ch.end_page})")
        if len(self.chapters) > 5:
            print(f"   ... and {len(self.chapters) - 5} more chapters")
    
    def filter_content(self):
        """Remove content before Chapter 1 and after appendix"""
        # Content is already filtered during TOC parsing
        # This method is here for clarity and potential additional filtering
        if self.chapters:
            print(f"   Content filtered: {len(self.chapters)} chapters retained")
            print(f"   First chapter: {self.chapters[0].title}")
            print(f"   Last chapter: {self.chapters[-1].title}")
    
    async def extract_sections_and_concepts(self):
        """Extract sections and concepts from each chapter in parallel"""
        # Process chapters in parallel
        tasks = []
        for chapter in self.chapters:
            task = self.extract_chapter_structure(chapter)
            tasks.append(task)
        
        # Wait for all chapters to be processed
        await asyncio.gather(*tasks)
        
        # Print summary
        total_sections = sum(len(ch.sections) for ch in self.chapters)
        total_concepts = sum(sum(len(s.concepts) for s in ch.sections) for ch in self.chapters)
        print(f"   Extracted {total_sections} sections and {total_concepts} concepts")
    
    async def extract_chapter_structure(self, chapter: Chapter):
        """Extract sections and concepts from a single chapter"""
        # Section patterns
        section_patterns = [
            rf'{chapter.number}\\.(\d+(?:\\.\\d+)?)\\s+([^\\n]+)',  # 1.1, 1.2.3, etc.
            rf'Section\\s+{chapter.number}\\.(\d+)\\s*:?\\s*([^\\n]+)',
            rf'^\d+\\.(\d+)\\s+([^\\n]+)$'  # Generic section pattern
        ]
        
        # Find sections
        sections = []
        for pattern in section_patterns:
            for match in re.finditer(pattern, chapter.content, re.MULTILINE):
                section_num = f"{chapter.number}.{match.group(1)}"
                section_title = match.group(2).strip()
                start_pos = match.start()
                
                section = Section(
                    chapter_number=chapter.number,
                    section_number=section_num,
                    title=section_title,
                    start_pos=start_pos,
                    end_pos=None,
                    content=""
                )
                sections.append(section)
        
        # Sort sections by position
        sections.sort(key=lambda s: s.start_pos)
        
        # Set end positions and extract content
        for i, section in enumerate(sections):
            section.end_pos = sections[i+1].start_pos if i+1 < len(sections) else len(chapter.content)
            section.content = chapter.content[section.start_pos:section.end_pos]
            
            # Extract concepts from section
            await self.extract_concepts_from_section(section)
        
        chapter.sections = sections
    
    async def extract_concepts_from_section(self, section: Section):
        """Extract concepts from a section"""
        concepts = []
        
        for pattern in self.concept_patterns:
            for match in re.finditer(pattern, section.content, re.MULTILINE | re.IGNORECASE):
                concept_name = match.group(1).strip() if match.groups() else match.group(0).strip()
                start_pos = section.start_pos + match.start()
                
                concept = Concept(
                    section_number=section.section_number,
                    concept_name=concept_name,
                    start_pos=start_pos,
                    end_pos=None,
                    content=""
                )
                concepts.append(concept)
        
        # Sort concepts by position
        concepts.sort(key=lambda c: c.start_pos)
        
        # Set end positions and extract content
        for i, concept in enumerate(concepts):
            # End at next concept or section end
            if i+1 < len(concepts):
                concept.end_pos = concepts[i+1].start_pos
            else:
                concept.end_pos = section.end_pos
            
            # Extract content relative to section
            rel_start = concept.start_pos - section.start_pos
            rel_end = concept.end_pos - section.start_pos
            concept.content = section.content[rel_start:rel_end]
        
        section.concepts = concepts
    
    def create_chunks(self):
        """Create chunks respecting concept/section/chapter boundaries"""
        chunk_count = 0
        
        for chapter in self.chapters:
            for section in chapter.sections:
                if section.concepts:
                    # Chunk each concept separately
                    for concept in section.concepts:
                        chunks = self.chunk_content(
                            concept.content,
                            chapter.number,
                            section.section_number,
                            concept.concept_name
                        )
                        for chunk in chunks:
                            chunk.chunk_id = f"{self.textbook_id}_ch{chapter.number}_s{section.section_number}_c{chunk_count}"
                            self.all_chunks.append(chunk)
                            concept.chunk_ids.append(chunk.chunk_id)
                            chunk_count += 1
                else:
                    # No concepts found, chunk the section
                    chunks = self.chunk_content(
                        section.content,
                        chapter.number,
                        section.section_number,
                        None
                    )
                    for chunk in chunks:
                        chunk.chunk_id = f"{self.textbook_id}_ch{chapter.number}_s{section.section_number}_chunk{chunk_count}"
                        self.all_chunks.append(chunk)
                        chunk_count += 1
        
        print(f"   Created {len(self.all_chunks)} chunks")
        print(f"   Average chunk size: {sum(len(c.content) for c in self.all_chunks) // len(self.all_chunks)} chars")
    
    def chunk_content(self, content: str, chapter_num: int, section_num: str, concept_name: Optional[str]) -> List[Chunk]:
        """Chunk content intelligently"""
        chunks = []
        min_size, max_size = self.chunk_size_range
        
        # Clean content
        content = content.strip()
        if not content:
            return chunks
        
        # If content is smaller than max size, return as single chunk
        if len(content) <= max_size:
            chunk = Chunk(
                chunk_id="",  # Will be set later
                textbook_id=self.textbook_id,
                chapter_number=chapter_num,
                section_number=section_num,
                concept_name=concept_name,
                content=content,
                metadata={
                    "chapter_title": next((ch.title for ch in self.chapters if ch.number == chapter_num), ""),
                    "section_title": "",  # Could be added if needed
                }
            )
            chunks.append(chunk)
            return chunks
        
        # Otherwise, chunk by paragraphs or sentences
        paragraphs = content.split('\\n\\n')
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph exceeds max size, save current chunk
            if current_chunk and len(current_chunk) + len(para) + 2 > max_size:
                chunk = Chunk(
                    chunk_id="",
                    textbook_id=self.textbook_id,
                    chapter_number=chapter_num,
                    section_number=section_num,
                    concept_name=concept_name,
                    content=current_chunk,
                    metadata={
                        "chapter_title": next((ch.title for ch in self.chapters if ch.number == chapter_num), ""),
                    }
                )
                chunks.append(chunk)
                current_chunk = para
            else:
                current_chunk = current_chunk + "\\n\\n" + para if current_chunk else para
        
        # Add remaining content
        if current_chunk:
            chunk = Chunk(
                chunk_id="",
                textbook_id=self.textbook_id,
                chapter_number=chapter_num,
                section_number=section_num,
                concept_name=concept_name,
                content=current_chunk,
                metadata={
                    "chapter_title": next((ch.title for ch in self.chapters if ch.number == chapter_num), ""),
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    async def generate_embeddings(self):
        """Generate embeddings for all chunks"""
        embedding_service = EmbeddingService()
        await embedding_service.initialize()
        
        # Process in batches
        batch_size = 20
        total_processed = 0
        
        for i in range(0, len(self.all_chunks), batch_size):
            batch = self.all_chunks[i:i+batch_size]
            texts = [chunk.content for chunk in batch]
            
            print(f"   Processing batch {i//batch_size + 1}/{(len(self.all_chunks) + batch_size - 1)//batch_size}...")
            
            # Generate embeddings for batch
            embeddings = await embedding_service.generate_embeddings_batch(texts)
            
            # Assign embeddings to chunks
            for chunk, embedding in zip(batch, embeddings):
                if embedding:
                    chunk.embedding = embedding
                    total_processed += 1
                else:
                    logger.warning(f"Failed to generate embedding for chunk {chunk.chunk_id}")
                    chunk.embedding = [0.0] * 1536  # Dummy embedding
        
        print(f"   Generated embeddings for {total_processed}/{len(self.all_chunks)} chunks")
    
    async def store_in_neo4j(self):
        """Store everything in Neo4j with proper relationships"""
        # Initialize connection
        config = ConnectionConfig(
            uri=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USER"),
            password=os.getenv("NEO4J_PASSWORD"),
            database=os.getenv("NEO4J_DATABASE", "neo4j")
        )
        
        connection = Neo4jConnectionManager(config)
        if not await connection.initialize():
            raise Exception("Failed to connect to Neo4j")
        
        try:
            # Create textbook node
            print("   Creating textbook node...")
            await connection.execute_query("""
                MERGE (t:Textbook {textbook_id: $textbook_id})
                SET t.title = $title,
                    t.subject = $subject,
                    t.processed_date = datetime(),
                    t.total_chapters = $total_chapters,
                    t.total_chunks = $total_chunks
            """, {
                "textbook_id": self.textbook_id,
                "title": "Introduction to Computer Science",
                "subject": "Computer Science",
                "total_chapters": len(self.chapters),
                "total_chunks": len(self.all_chunks)
            })
            
            # Create chapter nodes and PRECEDES relationships
            print("   Creating chapter nodes and sequential relationships...")
            for i, chapter in enumerate(self.chapters):
                # Create chapter node
                await connection.execute_query("""
                    MERGE (c:Chapter {textbook_id: $textbook_id, chapter_number: $chapter_number})
                    SET c.title = $title,
                        c.start_page = $start_page,
                        c.end_page = $end_page
                """, {
                    "textbook_id": self.textbook_id,
                    "chapter_number": chapter.number,
                    "title": chapter.title,
                    "start_page": chapter.start_page,
                    "end_page": chapter.end_page
                })
                
                # Create HAS_CHAPTER relationship
                await connection.execute_query("""
                    MATCH (t:Textbook {textbook_id: $textbook_id})
                    MATCH (c:Chapter {textbook_id: $textbook_id, chapter_number: $chapter_number})
                    MERGE (t)-[:HAS_CHAPTER]->(c)
                """, {
                    "textbook_id": self.textbook_id,
                    "chapter_number": chapter.number
                })
                
                # Create PRECEDES relationship with next chapter
                if i < len(self.chapters) - 1:
                    await connection.execute_query("""
                        MATCH (c1:Chapter {textbook_id: $textbook_id, chapter_number: $current})
                        MATCH (c2:Chapter {textbook_id: $textbook_id, chapter_number: $next})
                        MERGE (c1)-[:PRECEDES]->(c2)
                    """, {
                        "textbook_id": self.textbook_id,
                        "current": chapter.number,
                        "next": self.chapters[i+1].number
                    })
            
            # Create sections and relationships
            print("   Creating section nodes and relationships...")
            all_sections = []
            for chapter in self.chapters:
                all_sections.extend([(chapter.number, s) for s in chapter.sections])
            
            for i, (chapter_num, section) in enumerate(all_sections):
                # Create section node
                await connection.execute_query("""
                    MERGE (s:Section {textbook_id: $textbook_id, section_number: $section_number})
                    SET s.title = $title,
                        s.chapter_number = $chapter_number
                """, {
                    "textbook_id": self.textbook_id,
                    "section_number": section.section_number,
                    "title": section.title,
                    "chapter_number": chapter_num
                })
                
                # Create HAS_SECTION relationship
                await connection.execute_query("""
                    MATCH (c:Chapter {textbook_id: $textbook_id, chapter_number: $chapter_number})
                    MATCH (s:Section {textbook_id: $textbook_id, section_number: $section_number})
                    MERGE (c)-[:HAS_SECTION]->(s)
                """, {
                    "textbook_id": self.textbook_id,
                    "chapter_number": chapter_num,
                    "section_number": section.section_number
                })
                
                # Create NEXT relationship between sequential sections
                if i < len(all_sections) - 1:
                    next_section = all_sections[i+1][1]
                    await connection.execute_query("""
                        MATCH (s1:Section {textbook_id: $textbook_id, section_number: $current})
                        MATCH (s2:Section {textbook_id: $textbook_id, section_number: $next})
                        MERGE (s1)-[:NEXT]->(s2)
                    """, {
                        "textbook_id": self.textbook_id,
                        "current": section.section_number,
                        "next": next_section.section_number
                    })
            
            # Create concepts and relationships
            print("   Creating concept nodes and relationships...")
            all_concepts = []
            for chapter in self.chapters:
                for section in chapter.sections:
                    all_concepts.extend([(section.section_number, c) for c in section.concepts])
            
            for i, (section_num, concept) in enumerate(all_concepts):
                # Create concept node
                await connection.execute_query("""
                    MERGE (co:Concept {
                        textbook_id: $textbook_id,
                        section_number: $section_number,
                        concept_name: $concept_name
                    })
                    SET co.content_preview = $content_preview
                """, {
                    "textbook_id": self.textbook_id,
                    "section_number": section_num,
                    "concept_name": concept.concept_name,
                    "content_preview": concept.content[:200]
                })
                
                # Create CONTAINS_CONCEPT relationship
                await connection.execute_query("""
                    MATCH (s:Section {textbook_id: $textbook_id, section_number: $section_number})
                    MATCH (co:Concept {
                        textbook_id: $textbook_id,
                        section_number: $section_number,
                        concept_name: $concept_name
                    })
                    MERGE (s)-[:CONTAINS_CONCEPT]->(co)
                """, {
                    "textbook_id": self.textbook_id,
                    "section_number": section_num,
                    "concept_name": concept.concept_name
                })
                
                # Create NEXT relationship between sequential concepts
                if i < len(all_concepts) - 1:
                    next_concept = all_concepts[i+1][1]
                    await connection.execute_query("""
                        MATCH (co1:Concept {
                            textbook_id: $textbook_id,
                            section_number: $current_section,
                            concept_name: $current_name
                        })
                        MATCH (co2:Concept {
                            textbook_id: $textbook_id,
                            section_number: $next_section,
                            concept_name: $next_name
                        })
                        MERGE (co1)-[:NEXT]->(co2)
                    """, {
                        "textbook_id": self.textbook_id,
                        "current_section": section_num,
                        "current_name": concept.concept_name,
                        "next_section": all_concepts[i+1][0],
                        "next_name": next_concept.concept_name
                    })
            
            # Create chunks and relationships
            print("   Creating chunk nodes with embeddings...")
            batch_size = 50
            for i in range(0, len(self.all_chunks), batch_size):
                batch = self.all_chunks[i:i+batch_size]
                
                # Prepare batch data
                batch_data = []
                for chunk in batch:
                    batch_data.append({
                        "chunk_id": chunk.chunk_id,
                        "textbook_id": chunk.textbook_id,
                        "chapter_number": chunk.chapter_number,
                        "section_number": chunk.section_number,
                        "concept_name": chunk.concept_name,
                        "content": chunk.content,
                        "embedding": chunk.embedding
                    })
                
                # Execute batch insert
                await connection.execute_batch_write("""
                    CREATE (ch:Chunk {
                        chunk_id: $chunk_id,
                        textbook_id: $textbook_id,
                        chapter_number: $chapter_number,
                        section_number: $section_number,
                        concept_name: $concept_name,
                        text: $content,
                        embedding: $embedding
                    })
                """, batch_data, batch_size=batch_size)
                
                print(f"      Processed {min(i+batch_size, len(self.all_chunks))}/{len(self.all_chunks)} chunks")
            
            # Create chunk relationships
            print("   Creating chunk relationships...")
            
            # BELONGS_TO relationships with sections
            await connection.execute_query("""
                MATCH (ch:Chunk {textbook_id: $textbook_id})
                WHERE ch.section_number IS NOT NULL
                MATCH (s:Section {textbook_id: $textbook_id, section_number: ch.section_number})
                MERGE (ch)-[:BELONGS_TO]->(s)
            """, {"textbook_id": self.textbook_id})
            
            # BELONGS_TO relationships with concepts
            await connection.execute_query("""
                MATCH (ch:Chunk {textbook_id: $textbook_id})
                WHERE ch.concept_name IS NOT NULL
                MATCH (co:Concept {
                    textbook_id: $textbook_id,
                    section_number: ch.section_number,
                    concept_name: ch.concept_name
                })
                MERGE (ch)-[:BELONGS_TO]->(co)
            """, {"textbook_id": self.textbook_id})
            
            # NEXT relationships between sequential chunks
            for i in range(len(self.all_chunks) - 1):
                current = self.all_chunks[i]
                next_chunk = self.all_chunks[i+1]
                
                await connection.execute_query("""
                    MATCH (ch1:Chunk {chunk_id: $current_id})
                    MATCH (ch2:Chunk {chunk_id: $next_id})
                    MERGE (ch1)-[:NEXT]->(ch2)
                """, {
                    "current_id": current.chunk_id,
                    "next_id": next_chunk.chunk_id
                })
            
            print("\\n✓ Successfully stored all data in Neo4j!")
            print(f"  - {len(self.chapters)} chapters")
            print(f"  - {len(all_sections)} sections")
            print(f"  - {len(all_concepts)} concepts")
            print(f"  - {len(self.all_chunks)} chunks with embeddings")
            print("  - All relationships created (PRECEDES, HAS_SECTION, CONTAINS_CONCEPT, BELONGS_TO, NEXT)")
            
        finally:
            await connection.close()

async def main():
    """Main entry point"""
    pdf_path = "/app/textbooks/Introduction_To_Computer_Science.pdf"
    textbook_id = f"cs_intro_{hashlib.md5(pdf_path.encode()).hexdigest()[:8]}"
    
    print("=" * 80)
    print("TOC-BASED PDF PROCESSOR")
    print("=" * 80)
    print(f"Processing: {os.path.basename(pdf_path)}")
    print(f"Textbook ID: {textbook_id}")
    
    processor = TOCBasedPDFProcessor(pdf_path, textbook_id)
    success = await processor.process()
    
    if success:
        print("\\n✓ Processing completed successfully!")
    else:
        print("\\n✗ Processing failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
'''

import subprocess
import os

def run_toc_processor():
    """Run the TOC-based PDF processor"""
    
    print("Creating TOC-based PDF processor...")
    
    # Create the script
    script_path = "/tmp/toc_based_processor.py"
    with open(script_path, 'w') as f:
        f.write(SCRIPT_CONTENT)
    
    # Copy to container
    copy_cmd = f"docker cp {script_path} learntrac-api:/tmp/toc_based_processor.py"
    subprocess.run(copy_cmd, shell=True)
    
    # Run the processor
    print("\nRunning TOC-based PDF processor...")
    print("This will:")
    print("  1. Parse table of contents")
    print("  2. Split by chapters (removing pre-Chapter 1 and post-appendix)")
    print("  3. Extract sections and concepts")
    print("  4. Create chunks respecting boundaries")
    print("  5. Generate embeddings")
    print("  6. Create all relationships in Neo4j")
    print("\nProcessing...")
    
    exec_cmd = "docker exec learntrac-api python /tmp/toc_based_processor.py"
    result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("\nLog output:")
        print(result.stderr)
    
    # Clean up
    os.remove(script_path)
    
    return result.returncode == 0

if __name__ == "__main__":
    success = run_toc_processor()
    if success:
        print("\n✓ TOC-based processing completed successfully!")
    else:
        print("\n✗ TOC-based processing failed!")