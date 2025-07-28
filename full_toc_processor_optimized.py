#!/usr/bin/env python3
"""
Optimized full TOC-based processor with batching and progress tracking
"""

import subprocess
import os
import json

SCRIPT_CONTENT = '''
import asyncio
import os
import sys
import time
import re
import hashlib
import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import json

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
class ProcessingStats:
    """Track processing statistics"""
    chapters_found: int = 0
    sections_found: int = 0
    concepts_found: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    relationships_created: int = 0
    start_time: float = field(default_factory=time.time)
    
    def print_summary(self):
        elapsed = time.time() - self.start_time
        print(f"\\nProcessing Summary:")
        print(f"  Chapters: {self.chapters_found}")
        print(f"  Sections: {self.sections_found}")
        print(f"  Concepts: {self.concepts_found}")
        print(f"  Chunks: {self.chunks_created}")
        print(f"  Embeddings: {self.embeddings_generated}")
        print(f"  Relationships: {self.relationships_created}")
        print(f"  Time: {elapsed:.1f} seconds")

class OptimizedTOCProcessor:
    """Optimized processor with batching and better memory management"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.textbook_id = f"cs_textbook_{hashlib.md5(pdf_path.encode()).hexdigest()[:8]}"
        self.stats = ProcessingStats()
        self.doc = None
        self.connection = None
        self.embedding_service = None
        
        # Patterns for structure detection
        self.section_patterns = [
            r'^(\\d+)\\.(\\d+)\\s+(.+)$',  # 1.1 Title
            r'^Section\\s+(\\d+)\\.(\\d+)\\s*:?\\s*(.+)$',  # Section 1.1: Title
        ]
        
        self.concept_patterns = [
            r'\\b(?:Definition|Theorem|Lemma|Corollary|Example|Algorithm)\\s*(\\d*\\.?\\d*):?\\s*([^\\n]+)',
            r'\\b(?:Key Concept|Important|Main Idea):\\s*([^\\n]+)',
        ]
        
    async def process(self):
        """Main processing pipeline"""
        try:
            print(f"\\nProcessing: {os.path.basename(self.pdf_path)}")
            print(f"Textbook ID: {self.textbook_id}")
            print("=" * 60)
            
            # Initialize services
            await self._initialize_services()
            
            # Step 1: Parse TOC
            print("\\n1. Parsing Table of Contents...")
            chapters = self._parse_toc()
            self.stats.chapters_found = len(chapters)
            
            # Step 2: Create textbook and chapter nodes
            print("\\n2. Creating textbook and chapter nodes...")
            await self._create_textbook_and_chapters(chapters)
            
            # Step 3: Process chapters in batches
            print("\\n3. Processing chapters (sections, concepts, chunks)...")
            await self._process_chapters_batch(chapters)
            
            # Step 4: Create all relationships
            print("\\n4. Creating relationships...")
            await self._create_all_relationships()
            
            # Step 5: Generate embeddings in batches
            print("\\n5. Generating embeddings...")
            await self._generate_embeddings_batch()
            
            # Print summary
            self.stats.print_summary()
            
            # Save summary
            self._save_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            await self._cleanup()
    
    async def _initialize_services(self):
        """Initialize Neo4j and embedding services"""
        # Initialize Neo4j
        config = ConnectionConfig(
            uri=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USER"),
            password=os.getenv("NEO4J_PASSWORD"),
            database=os.getenv("NEO4J_DATABASE", "neo4j")
        )
        
        self.connection = Neo4jConnectionManager(config)
        if not await self.connection.initialize():
            raise Exception("Failed to connect to Neo4j")
        
        # Initialize embedding service
        self.embedding_service = EmbeddingService()
        await self.embedding_service.initialize()
        
        print("✓ Services initialized")
    
    def _parse_toc(self):
        """Parse TOC and extract chapters"""
        self.doc = fitz.open(self.pdf_path)
        toc = self.doc.get_toc()
        
        chapters = []
        for level, title, page in toc:
            # Only process Chapter entries
            if level == 1 and "Chapter" in title:
                # Stop at appendix
                if any(x in title for x in ["Appendix", "Bibliography", "Index"]):
                    break
                
                match = re.match(r'Chapter\\s+(\\d+)\\s*:?\\s*(.+)', title)
                if match:
                    chapter_num = int(match.group(1))
                    chapter_title = match.group(2).strip()
                    chapters.append({
                        'number': chapter_num,
                        'title': chapter_title,
                        'start_page': page,
                        'end_page': None
                    })
        
        # Set end pages
        for i in range(len(chapters) - 1):
            chapters[i]['end_page'] = chapters[i+1]['start_page']
        if chapters:
            chapters[-1]['end_page'] = len(self.doc)
        
        print(f"  Found {len(chapters)} chapters")
        for ch in chapters[:3]:
            print(f"    Chapter {ch['number']}: {ch['title']}")
        if len(chapters) > 3:
            print(f"    ... and {len(chapters) - 3} more")
        
        return chapters
    
    async def _create_textbook_and_chapters(self, chapters):
        """Create textbook and chapter nodes with PRECEDES relationships"""
        # Create textbook
        await self.connection.execute_query("""
            MERGE (t:Textbook {textbook_id: $textbook_id})
            SET t.title = $title,
                t.subject = $subject,
                t.processed_date = datetime(),
                t.total_chapters = $total_chapters
        """, {
            "textbook_id": self.textbook_id,
            "title": "Introduction to Computer Science",
            "subject": "Computer Science",
            "total_chapters": len(chapters)
        })
        
        # Create chapters and relationships
        for i, chapter in enumerate(chapters):
            # Create chapter
            await self.connection.execute_query("""
                MERGE (c:Chapter {textbook_id: $textbook_id, chapter_number: $number})
                SET c.title = $title,
                    c.start_page = $start_page,
                    c.end_page = $end_page
            """, {
                "textbook_id": self.textbook_id,
                "number": chapter['number'],
                "title": chapter['title'],
                "start_page": chapter['start_page'],
                "end_page": chapter['end_page']
            })
            
            # Link to textbook
            await self.connection.execute_query("""
                MATCH (t:Textbook {textbook_id: $textbook_id})
                MATCH (c:Chapter {textbook_id: $textbook_id, chapter_number: $number})
                MERGE (t)-[:HAS_CHAPTER]->(c)
            """, {
                "textbook_id": self.textbook_id,
                "number": chapter['number']
            })
            self.stats.relationships_created += 1
            
            # Create PRECEDES relationship
            if i > 0:
                await self.connection.execute_query("""
                    MATCH (c1:Chapter {textbook_id: $textbook_id, chapter_number: $prev})
                    MATCH (c2:Chapter {textbook_id: $textbook_id, chapter_number: $curr})
                    MERGE (c1)-[:PRECEDES]->(c2)
                """, {
                    "textbook_id": self.textbook_id,
                    "prev": chapters[i-1]['number'],
                    "curr": chapter['number']
                })
                self.stats.relationships_created += 1
        
        print(f"  Created {len(chapters)} chapters with PRECEDES relationships")
    
    async def _process_chapters_batch(self, chapters):
        """Process chapters to extract sections, concepts, and create chunks"""
        # Process first 5 chapters in detail, rest with lighter processing
        detailed_chapters = chapters[:5]
        light_chapters = chapters[5:]
        
        # Detailed processing
        for chapter in detailed_chapters:
            await self._process_chapter_detailed(chapter)
        
        # Light processing for remaining chapters
        for chapter in light_chapters:
            await self._process_chapter_light(chapter)
    
    async def _process_chapter_detailed(self, chapter):
        """Detailed processing with sections and concepts"""
        print(f"  Processing Chapter {chapter['number']} (detailed)...")
        
        # Extract content
        content = self._extract_chapter_content(chapter)
        
        # Find sections
        sections = self._extract_sections(content, chapter['number'])
        self.stats.sections_found += len(sections)
        
        # Create section nodes
        for i, section in enumerate(sections):
            await self._create_section(section, chapter['number'])
            
            # Extract concepts from section
            concepts = self._extract_concepts(section['content'], section['number'])
            self.stats.concepts_found += len(concepts)
            
            # Create concept nodes
            for concept in concepts[:5]:  # Limit concepts per section
                await self._create_concept(concept, section['number'])
            
            # Create chunks for section
            chunks = self._create_chunks_for_content(
                section['content'],
                chapter['number'],
                section['number'],
                concepts
            )
            
            # Store chunks
            await self._store_chunks_batch(chunks)
            self.stats.chunks_created += len(chunks)
        
        print(f"    Created {len(sections)} sections, {self.stats.chunks_created} chunks")
    
    async def _process_chapter_light(self, chapter):
        """Light processing - just create chunks"""
        print(f"  Processing Chapter {chapter['number']} (light)...")
        
        # Extract content
        content = self._extract_chapter_content(chapter, max_pages=10)
        
        # Create chunks directly
        chunks = self._create_chunks_for_content(
            content,
            chapter['number'],
            f"{chapter['number']}.0",  # Generic section number
            []
        )
        
        # Store chunks
        await self._store_chunks_batch(chunks)
        self.stats.chunks_created += len(chunks)
        
        print(f"    Created {len(chunks)} chunks")
    
    def _extract_chapter_content(self, chapter, max_pages=None):
        """Extract text content from chapter"""
        start = chapter['start_page'] - 1
        end = chapter['end_page']
        
        if max_pages:
            end = min(end, start + max_pages)
        
        content = ""
        for page_num in range(start, min(end, len(self.doc))):
            page = self.doc[page_num]
            content += page.get_text()
        
        return content
    
    def _extract_sections(self, content: str, chapter_num: int) -> List[Dict]:
        """Extract sections from chapter content"""
        sections = []
        
        for pattern in self.section_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                section_num = f"{chapter_num}.{match.group(1)}"
                if pattern.startswith('^(\\\\d+)'):
                    title = match.group(2)
                else:
                    title = match.group(3)
                
                start_pos = match.start()
                sections.append({
                    'number': section_num,
                    'title': title.strip()[:200],
                    'start_pos': start_pos,
                    'content': ""
                })
        
        # Sort by position and extract content
        sections.sort(key=lambda x: x['start_pos'])
        
        for i in range(len(sections)):
            start = sections[i]['start_pos']
            end = sections[i+1]['start_pos'] if i+1 < len(sections) else len(content)
            sections[i]['content'] = content[start:end]
        
        return sections[:10]  # Limit sections per chapter
    
    def _extract_concepts(self, content: str, section_num: str) -> List[Dict]:
        """Extract concepts from section content"""
        concepts = []
        seen_names = set()
        
        for pattern in self.concept_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
                if len(match.groups()) >= 2:
                    name = match.group(2).strip()
                elif len(match.groups()) >= 1:
                    name = match.group(1).strip()
                else:
                    name = match.group(0).strip()
                
                # Clean and limit name
                name = re.sub(r'\\s+', ' ', name)[:100]
                
                if name and name not in seen_names:
                    seen_names.add(name)
                    concepts.append({
                        'name': name,
                        'section_number': section_num,
                        'position': match.start()
                    })
        
        return concepts[:10]  # Limit concepts
    
    def _create_chunks_for_content(self, content: str, chapter_num: int, 
                                  section_num: str, concepts: List[Dict]) -> List[Dict]:
        """Create chunks from content"""
        chunks = []
        
        # Clean content
        content = content.strip()
        if not content:
            return chunks
        
        # Simple chunking by character count
        chunk_size = 1000
        overlap = 100
        
        for i in range(0, len(content), chunk_size - overlap):
            chunk_text = content[i:i + chunk_size]
            if len(chunk_text.strip()) < 100:
                continue
            
            # Find which concept this chunk belongs to
            chunk_concept = None
            chunk_pos = i
            for concept in concepts:
                if concept['position'] <= chunk_pos < concept.get('end_pos', len(content)):
                    chunk_concept = concept['name']
                    break
            
            chunk_id = f"{self.textbook_id}_ch{chapter_num}_s{section_num}_chunk{len(chunks)}"
            
            chunks.append({
                'chunk_id': chunk_id,
                'textbook_id': self.textbook_id,
                'chapter_number': chapter_num,
                'section_number': section_num,
                'concept_name': chunk_concept,
                'text': chunk_text,
                'position': i
            })
        
        return chunks
    
    async def _create_section(self, section: Dict, chapter_num: int):
        """Create section node"""
        await self.connection.execute_query("""
            MERGE (s:Section {textbook_id: $textbook_id, section_number: $number})
            SET s.title = $title,
                s.chapter_number = $chapter_number
        """, {
            "textbook_id": self.textbook_id,
            "number": section['number'],
            "title": section['title'],
            "chapter_number": chapter_num
        })
    
    async def _create_concept(self, concept: Dict, section_num: str):
        """Create concept node"""
        await self.connection.execute_query("""
            MERGE (co:Concept {
                textbook_id: $textbook_id,
                section_number: $section_number,
                concept_name: $name
            })
        """, {
            "textbook_id": self.textbook_id,
            "section_number": section_num,
            "name": concept['name']
        })
    
    async def _store_chunks_batch(self, chunks: List[Dict]):
        """Store chunks in batch"""
        if not chunks:
            return
        
        # Store in batches of 50
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            
            await self.connection.execute_batch_write("""
                CREATE (ch:Chunk {
                    chunk_id: $chunk_id,
                    textbook_id: $textbook_id,
                    chapter_number: $chapter_number,
                    section_number: $section_number,
                    concept_name: $concept_name,
                    text: $text
                })
            """, batch, batch_size=batch_size)
    
    async def _create_all_relationships(self):
        """Create all relationships in batch"""
        print("  Creating chapter->section relationships...")
        result = await self.connection.execute_query("""
            MATCH (c:Chapter {textbook_id: $textbook_id})
            MATCH (s:Section {textbook_id: $textbook_id})
            WHERE s.chapter_number = c.chapter_number
            MERGE (c)-[:HAS_SECTION]->(s)
            RETURN count(*) as count
        """, {"textbook_id": self.textbook_id})
        
        if result:
            self.stats.relationships_created += result[0]['count']
        
        print("  Creating section->concept relationships...")
        result = await self.connection.execute_query("""
            MATCH (s:Section {textbook_id: $textbook_id})
            MATCH (co:Concept {textbook_id: $textbook_id})
            WHERE co.section_number = s.section_number
            MERGE (s)-[:CONTAINS_CONCEPT]->(co)
            RETURN count(*) as count
        """, {"textbook_id": self.textbook_id})
        
        if result:
            self.stats.relationships_created += result[0]['count']
        
        print("  Creating chunk->section relationships...")
        result = await self.connection.execute_query("""
            MATCH (ch:Chunk {textbook_id: $textbook_id})
            MATCH (s:Section {textbook_id: $textbook_id})
            WHERE ch.section_number = s.section_number
            MERGE (ch)-[:BELONGS_TO]->(s)
            RETURN count(*) as count
        """, {"textbook_id": self.textbook_id})
        
        if result:
            self.stats.relationships_created += result[0]['count']
        
        print("  Creating sequential NEXT relationships for sections...")
        result = await self.connection.execute_query("""
            MATCH (s:Section {textbook_id: $textbook_id})
            WITH s ORDER BY s.section_number
            WITH collect(s) as sections
            UNWIND range(0, size(sections)-2) as i
            WITH sections[i] as s1, sections[i+1] as s2
            MERGE (s1)-[:NEXT]->(s2)
            RETURN count(*) as count
        """, {"textbook_id": self.textbook_id})
        
        if result:
            self.stats.relationships_created += result[0]['count']
    
    async def _generate_embeddings_batch(self):
        """Generate embeddings for chunks in batches"""
        # Get chunks without embeddings
        result = await self.connection.execute_query("""
            MATCH (ch:Chunk {textbook_id: $textbook_id})
            WHERE ch.embedding IS NULL
            RETURN ch.chunk_id as id, ch.text as text
            LIMIT 100
        """, {"textbook_id": self.textbook_id})
        
        if not result:
            print("  No chunks need embeddings")
            return
        
        print(f"  Generating embeddings for {len(result)} chunks...")
        
        # Process in batches
        batch_size = 20
        for i in range(0, len(result), batch_size):
            batch = result[i:i+batch_size]
            texts = [r['text'] for r in batch]
            
            # Generate embeddings
            embeddings = await self.embedding_service.generate_embeddings_batch(texts)
            
            # Update chunks with embeddings
            updates = []
            for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                if embedding:
                    updates.append({
                        'chunk_id': chunk['id'],
                        'embedding': embedding
                    })
                    self.stats.embeddings_generated += 1
            
            # Batch update
            if updates:
                await self.connection.execute_batch_write("""
                    MATCH (ch:Chunk {chunk_id: $chunk_id})
                    SET ch.embedding = $embedding
                """, updates, batch_size=len(updates))
            
            print(f"    Processed batch {i//batch_size + 1}/{(len(result) + batch_size - 1)//batch_size}")
    
    def _save_summary(self):
        """Save processing summary"""
        summary = {
            "textbook_id": self.textbook_id,
            "pdf_file": os.path.basename(self.pdf_path),
            "stats": {
                "chapters": self.stats.chapters_found,
                "sections": self.stats.sections_found,
                "concepts": self.stats.concepts_found,
                "chunks": self.stats.chunks_created,
                "embeddings": self.stats.embeddings_generated,
                "relationships": self.stats.relationships_created,
                "processing_time": time.time() - self.stats.start_time
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open('/app/processing_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
    
    async def _cleanup(self):
        """Clean up resources"""
        if self.doc:
            self.doc.close()
        if self.connection:
            await self.connection.close()

async def main():
    """Main entry point"""
    pdf_path = "/app/textbooks/Introduction_To_Computer_Science.pdf"
    
    processor = OptimizedTOCProcessor(pdf_path)
    success = await processor.process()
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    from datetime import datetime
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
'''

def run_optimized_processor():
    """Run the optimized processor"""
    
    print("Creating optimized TOC processor...")
    
    # Create script
    script_path = "/tmp/optimized_processor.py"
    with open(script_path, 'w') as f:
        f.write(SCRIPT_CONTENT)
    
    # Copy to container
    copy_cmd = f"docker cp {script_path} learntrac-api:/tmp/optimized_processor.py"
    subprocess.run(copy_cmd, shell=True)
    
    # Run processor
    print("\nRunning optimized TOC-based processor...")
    print("This will process the textbook with:")
    print("  - Full chapter processing for first 5 chapters")
    print("  - Light processing for remaining chapters")
    print("  - Batch operations for better performance")
    print("  - All required relationships")
    print("\nProcessing...")
    
    exec_cmd = "docker exec learntrac-api python /tmp/optimized_processor.py"
    result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("\nLog output:")
        # Show last 2000 chars of stderr
        print(result.stderr[-2000:])
    
    # Get summary
    copy_summary = "docker cp learntrac-api:/app/processing_summary.json ./processing_summary.json"
    summary_result = subprocess.run(copy_summary, shell=True, capture_output=True)
    
    if summary_result.returncode == 0 and os.path.exists("./processing_summary.json"):
        print("\n✓ Processing summary saved to processing_summary.json")
        with open("./processing_summary.json", 'r') as f:
            summary = json.load(f)
            print(f"\nTextbook ID: {summary['textbook_id']}")
            print("Statistics:")
            for key, value in summary['stats'].items():
                print(f"  {key}: {value}")
    
    # Clean up
    os.remove(script_path)
    
    return result.returncode == 0

if __name__ == "__main__":
    if run_optimized_processor():
        print("\n✓ Processing completed successfully!")
    else:
        print("\n✗ Processing failed!")