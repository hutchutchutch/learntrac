"""
TOC-based PDF Processor
Based on the successful custom processing approach
"""

import re
import hashlib
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import fitz  # PyMuPDF

from .structure_detector import StructureElement, StructureType, NumberingStyle
from .content_chunker import ChunkMetadata, ContentType
from .neo4j_connection_manager import Neo4jConnectionManager
from .neo4j_vector_index_manager import Neo4jVectorIndexManager
from .neo4j_content_ingestion import Neo4jContentIngestion, TextbookMetadata
from ..services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    """Represents a chapter with its content and metadata"""
    number: int
    title: str
    start_page: int
    end_page: Optional[int]
    content: str = ""
    sections: List['Section'] = field(default_factory=list)


@dataclass
class Section:
    """Represents a section within a chapter"""
    chapter_number: int
    section_number: str  # e.g., "1.1", "1.2.3"
    title: str
    start_pos: int
    end_pos: Optional[int]
    content: str = ""
    concepts: List['Concept'] = field(default_factory=list)


@dataclass
class Concept:
    """Represents a concept within a section"""
    section_number: str
    concept_name: str
    start_pos: int
    end_pos: Optional[int]
    content: str = ""


@dataclass
class ProcessingResult:
    """Result of PDF processing"""
    success: bool
    textbook_id: str
    chapters: List[Chapter]
    sections: List[Section]
    concepts: List[Concept]
    chunks: List[Tuple[ChunkMetadata, str]]
    total_chunks: int
    embeddings_generated: int
    error: Optional[str] = None
    processing_time: float = 0.0
    
    def summary(self) -> str:
        if self.success:
            return (f"Successfully processed textbook {self.textbook_id}: "
                   f"{len(self.chapters)} chapters, {len(self.sections)} sections, "
                   f"{len(self.concepts)} concepts, {self.total_chunks} chunks")
        else:
            return f"Processing failed: {self.error}"


class TOCPDFProcessor:
    """
    PDF processor that uses Table of Contents for structure extraction
    """
    
    def __init__(self):
        self.doc = None
        self.concept_patterns = [
            r'\b(?:Definition|Theorem|Lemma|Corollary|Proposition|Example|Algorithm|Concept)\s*\d*\.?\d*:?\s*([^\n]+)',
            r'\b(?:Key Concept|Important Concept|Main Idea):\s*([^\n]+)',
            r'^(\d+\.\d+\.\d+)\s+([^\n]+)$',  # Subsection that might be a concept
        ]
        self.section_patterns = [
            r'^(\d+)\.(\d+)\s+(.+)$',  # 1.1 Title
            r'^Section\s+(\d+)\.(\d+)\s*:?\s*(.+)$',  # Section 1.1: Title
        ]
        self.min_chunk_size = 500
        self.max_chunk_size = 1500
        self.chunk_overlap = 200
        
    async def process_pdf(self, 
                         pdf_path: str, 
                         connection_manager: Neo4jConnectionManager,
                         index_manager: Optional['Neo4jVectorIndexManager'] = None,
                         embedding_service: Optional[EmbeddingService] = None,
                         max_chunks_to_embed: Optional[int] = None) -> ProcessingResult:
        """
        Process PDF using TOC-based approach
        
        Args:
            pdf_path: Path to PDF file
            connection_manager: Neo4j connection manager
            index_manager: Neo4j vector index manager
            embedding_service: Optional embedding service
            max_chunks_to_embed: Limit embeddings for testing
            
        Returns:
            ProcessingResult with all extracted data
        """
        import time
        start_time = time.time()
        
        try:
            # Generate textbook ID
            textbook_id = f"textbook_{hashlib.md5(pdf_path.encode()).hexdigest()[:8]}"
            
            logger.info(f"Processing PDF: {pdf_path}")
            logger.info(f"Textbook ID: {textbook_id}")
            
            # Extract chapters using TOC
            chapters = self._extract_chapters_from_toc(pdf_path)
            if not chapters:
                return ProcessingResult(
                    success=False,
                    textbook_id=textbook_id,
                    chapters=[],
                    sections=[],
                    concepts=[],
                    chunks=[],
                    total_chunks=0,
                    embeddings_generated=0,
                    error="No chapters found in table of contents"
                )
            
            # Extract sections and concepts from each chapter
            all_sections = []
            all_concepts = []
            
            for chapter in chapters:
                sections = self._extract_sections_from_chapter(chapter)
                chapter.sections = sections
                all_sections.extend(sections)
                
                for section in sections:
                    concepts = self._extract_concepts_from_section(section)
                    section.concepts = concepts
                    all_concepts.extend(concepts)
            
            # Create chunks
            all_chunks = self._create_chunks(chapters, textbook_id)
            
            # Generate embeddings if service provided
            embeddings_generated = 0
            if embedding_service:
                embeddings_generated = await self._generate_embeddings(
                    all_chunks, 
                    embedding_service, 
                    max_chunks_to_embed
                )
            
            # Store in Neo4j
            await self._store_in_neo4j(
                textbook_id,
                chapters,
                all_sections,
                all_concepts,
                all_chunks,
                connection_manager
            )
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                success=True,
                textbook_id=textbook_id,
                chapters=chapters,
                sections=all_sections,
                concepts=all_concepts,
                chunks=all_chunks,
                total_chunks=len(all_chunks),
                embeddings_generated=embeddings_generated,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            import traceback
            traceback.print_exc()
            
            return ProcessingResult(
                success=False,
                textbook_id=textbook_id if 'textbook_id' in locals() else "",
                chapters=[],
                sections=[],
                concepts=[],
                chunks=[],
                total_chunks=0,
                embeddings_generated=0,
                error=str(e),
                processing_time=time.time() - start_time
            )
        finally:
            if self.doc:
                self.doc.close()
    
    def _extract_chapters_from_toc(self, pdf_path: str) -> List[Chapter]:
        """Extract chapters from PDF table of contents"""
        self.doc = fitz.open(pdf_path)
        toc = self.doc.get_toc()
        
        chapters = []
        chapter_entries = []
        
        # Extract chapter entries from TOC
        for level, title, page in toc:
            # Only process level 1 entries that look like chapters
            if level == 1 and ("Chapter" in title or re.match(r'^\d+\.?\s', title)):
                # Skip appendix and similar
                if any(x in title for x in ["Appendix", "Bibliography", "Index"]):
                    break
                
                chapter_match = re.match(r'Chapter\s+(\d+)\s*:?\s*(.+)', title) or \
                               re.match(r'^(\d+)\.?\s+(.+)', title)
                if chapter_match:
                    chapter_num = int(chapter_match.group(1))
                    chapter_title = chapter_match.group(2).strip()
                    chapter_entries.append((chapter_num, chapter_title, page))
        
        # Create Chapter objects with content
        for i, (num, title, start_page) in enumerate(chapter_entries):
            # Determine end page
            end_page = chapter_entries[i+1][2] if i+1 < len(chapter_entries) else len(self.doc)
            
            # Extract chapter content
            content = self._extract_page_range(start_page - 1, end_page)
            
            chapter = Chapter(
                number=num,
                title=title,
                start_page=start_page,
                end_page=end_page,
                content=content
            )
            chapters.append(chapter)
        
        logger.info(f"Extracted {len(chapters)} chapters from TOC")
        return chapters
    
    def _extract_page_range(self, start_page: int, end_page: int) -> str:
        """Extract text from page range"""
        content = ""
        for page_num in range(start_page, min(end_page, len(self.doc))):
            page = self.doc[page_num]
            content += page.get_text()
        return content
    
    def _extract_sections_from_chapter(self, chapter: Chapter) -> List[Section]:
        """Extract sections from chapter content"""
        sections = []
        
        for pattern in self.section_patterns:
            regex = re.compile(pattern, re.MULTILINE)
            for match in regex.finditer(chapter.content):
                if pattern.startswith('^(\d+)'):
                    section_num = f"{chapter.number}.{match.group(1)}"
                    title = match.group(2)
                else:
                    section_num = f"{chapter.number}.{match.group(2)}"
                    title = match.group(3)
                
                section = Section(
                    chapter_number=chapter.number,
                    section_number=section_num,
                    title=title.strip()[:200],  # Limit title length
                    start_pos=match.start(),
                    end_pos=None,
                    content=""
                )
                sections.append(section)
        
        # Sort by position and set end positions
        sections.sort(key=lambda s: s.start_pos)
        for i in range(len(sections)):
            sections[i].end_pos = sections[i+1].start_pos if i+1 < len(sections) else len(chapter.content)
            sections[i].content = chapter.content[sections[i].start_pos:sections[i].end_pos]
        
        return sections[:10]  # Limit sections per chapter
    
    def _extract_concepts_from_section(self, section: Section) -> List[Concept]:
        """Extract concepts from section content"""
        concepts = []
        seen_names = set()
        
        for pattern in self.concept_patterns:
            regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
            for match in regex.finditer(section.content):
                # Extract concept name
                if match.groups():
                    name = match.group(1).strip() if len(match.groups()) >= 1 else match.group(0).strip()
                else:
                    name = match.group(0).strip()
                
                # Clean and limit name
                name = re.sub(r'\s+', ' ', name)[:100]
                
                if name and name not in seen_names:
                    seen_names.add(name)
                    concept = Concept(
                        section_number=section.section_number,
                        concept_name=name,
                        start_pos=section.start_pos + match.start(),
                        end_pos=None,
                        content=""
                    )
                    concepts.append(concept)
        
        # Sort by position and set content
        concepts.sort(key=lambda c: c.start_pos)
        for i in range(len(concepts)):
            if i+1 < len(concepts):
                concepts[i].end_pos = concepts[i+1].start_pos
            else:
                concepts[i].end_pos = section.end_pos
            
            # Extract content relative to section
            rel_start = concepts[i].start_pos - section.start_pos
            rel_end = concepts[i].end_pos - section.start_pos if concepts[i].end_pos else len(section.content)
            concepts[i].content = section.content[rel_start:rel_end]
        
        return concepts[:10]  # Limit concepts per section
    
    def _create_chunks(self, chapters: List[Chapter], textbook_id: str) -> List[Tuple[ChunkMetadata, str]]:
        """Create chunks from chapters, respecting boundaries"""
        all_chunks = []
        chunk_count = 0
        
        for chapter in chapters:
            for section in chapter.sections:
                if section.concepts:
                    # Chunk each concept separately
                    for concept in section.concepts:
                        # Create a simple chunk for the concept
                        if concept.content.strip():
                            chunk_metadata = ChunkMetadata(
                                book_id=textbook_id,
                                chunk_id=f"{textbook_id}_ch{chapter.number}_s{section.section_number}_c{chunk_count}",
                                title=concept.concept_name[:100],  # Limit title length
                                chapter=f"Chapter {chapter.number}",
                                section=section.section_number,
                                content_type=ContentType.TEXT,
                                char_count=len(concept.content),
                                word_count=len(concept.content.split())
                            )
                            all_chunks.append((chunk_metadata, concept.content))
                            chunk_count += 1
                else:
                    # No concepts, chunk the section
                    if section.content.strip():
                        chunk_metadata = ChunkMetadata(
                            book_id=textbook_id,
                            chunk_id=f"{textbook_id}_ch{chapter.number}_s{section.section_number}_chunk{chunk_count}",
                            title=f"Section {section.section_number}",
                            chapter=f"Chapter {chapter.number}",
                            section=section.section_number,
                            content_type=ContentType.TEXT,
                            char_count=len(section.content),
                            word_count=len(section.content.split())
                        )
                        all_chunks.append((chunk_metadata, section.content))
                        chunk_count += 1
        
        logger.info(f"Created {len(all_chunks)} chunks")
        return all_chunks
    
    def _chunk_text(self, content: str, textbook_id: str, chapter_num: int, 
                    section_num: str, concept_name: Optional[str]) -> List[ChunkMetadata]:
        """Chunk text into appropriate sizes"""
        chunks = []
        
        # Clean content
        content = content.strip()
        if not content:
            return chunks
        
        # If content is small enough, return as single chunk
        if len(content) <= self.max_chunk_size:
            chunk = ChunkMetadata(
                book_id=textbook_id,
                chunk_id="",  # Will be set later
                title=concept_name or f"Section {section_num}",
                chapter=f"Chapter {chapter_num}",
                section=section_num,
                content_type=ContentType.TEXT,
                char_count=len(content),
                word_count=len(content.split())
            )
            chunks.append(chunk)
            return chunks
        
        # Otherwise, chunk by paragraphs
        paragraphs = content.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph exceeds max size, save current chunk
            if current_chunk and len(current_chunk) + len(para) + 2 > self.max_chunk_size:
                chunk = ChunkMetadata(
                    book_id=textbook_id,
                    chunk_id="",
                    title=concept_name or f"Section {section_num}",
                    chapter=f"Chapter {chapter_num}",
                    section=section_num,
                    content_type=ContentType.TEXT,
                    char_count=len(current_chunk),
                    word_count=len(current_chunk.split())
                )
                chunks.append(chunk)
                current_chunk = para
            else:
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para
        
        # Add remaining content
        if current_chunk:
            chunk = ChunkMetadata(
                book_id=textbook_id,
                chunk_id="",
                title=concept_name or f"Section {section_num}",
                chapter=f"Chapter {chapter_num}",
                section=section_num,
                content_type=ContentType.TEXT,
                char_count=len(current_chunk),
                word_count=len(current_chunk.split())
            )
            chunks.append(chunk)
        
        return chunks
    
    async def _generate_embeddings(self, chunks: List[Tuple[ChunkMetadata, str]], 
                                  embedding_service: EmbeddingService,
                                  max_chunks: Optional[int] = None) -> int:
        """Generate embeddings for chunks"""
        chunks_to_process = chunks[:max_chunks] if max_chunks else chunks
        batch_size = 20
        embeddings_generated = 0
        
        logger.info(f"Generating embeddings for {len(chunks_to_process)} chunks...")
        
        for i in range(0, len(chunks_to_process), batch_size):
            batch = chunks_to_process[i:i+batch_size]
            texts = [text for _, text in batch]
            
            # Log what we're embedding
            logger.debug(f"Embedding batch {i//batch_size + 1}/{(len(chunks_to_process)-1)//batch_size + 1}")
            
            embeddings = await embedding_service.generate_embeddings_batch(texts)
            
            for (chunk_metadata, text), embedding in zip(batch, embeddings):
                if embedding:
                    # Store embedding in metadata
                    chunk_metadata.embedding = embedding
                    embeddings_generated += 1
                    logger.debug(f"Generated embedding for chunk {chunk_metadata.chunk_id} (dim: {len(embedding)})")
                else:
                    logger.warning(f"Failed to generate embedding for chunk {chunk_metadata.chunk_id}")
        
        logger.info(f"Generated {embeddings_generated}/{len(chunks_to_process)} embeddings successfully")
        return embeddings_generated
    
    async def _store_in_neo4j(self, textbook_id: str, chapters: List[Chapter],
                             sections: List[Section], concepts: List[Concept],
                             chunks: List[Tuple[ChunkMetadata, str]],
                             connection: Neo4jConnectionManager):
        """Store all data in Neo4j with relationships"""
        logger.info("Storing data in Neo4j...")
        
        # Create textbook node
        await connection.execute_query("""
            MERGE (t:Textbook {textbook_id: $textbook_id})
            SET t.title = $title,
                t.subject = $subject,
                t.processed_date = datetime(),
                t.total_chapters = $total_chapters,
                t.total_chunks = $total_chunks
        """, {
            "textbook_id": textbook_id,
            "title": "Uploaded Textbook",  # Can be extracted from metadata
            "subject": "Unknown",
            "total_chapters": len(chapters),
            "total_chunks": len(chunks)
        })
        
        # Create chapters and PRECEDES relationships
        for i, chapter in enumerate(chapters):
            await connection.execute_query("""
                MERGE (c:Chapter {textbook_id: $textbook_id, chapter_number: $number})
                SET c.title = $title,
                    c.start_page = $start_page,
                    c.end_page = $end_page
            """, {
                "textbook_id": textbook_id,
                "number": chapter.number,
                "title": chapter.title,
                "start_page": chapter.start_page,
                "end_page": chapter.end_page
            })
            
            # Link to textbook
            await connection.execute_query("""
                MATCH (t:Textbook {textbook_id: $textbook_id})
                MATCH (c:Chapter {textbook_id: $textbook_id, chapter_number: $number})
                MERGE (t)-[:HAS_CHAPTER]->(c)
            """, {
                "textbook_id": textbook_id,
                "number": chapter.number
            })
            
            # Create PRECEDES relationship
            if i > 0:
                await connection.execute_query("""
                    MATCH (c1:Chapter {textbook_id: $textbook_id, chapter_number: $prev})
                    MATCH (c2:Chapter {textbook_id: $textbook_id, chapter_number: $curr})
                    MERGE (c1)-[:PRECEDES]->(c2)
                """, {
                    "textbook_id": textbook_id,
                    "prev": chapters[i-1].number,
                    "curr": chapter.number
                })
        
        # Create sections with relationships
        for i, section in enumerate(sections):
            await connection.execute_query("""
                MERGE (s:Section {textbook_id: $textbook_id, section_number: $number})
                SET s.title = $title,
                    s.chapter_number = $chapter_number
            """, {
                "textbook_id": textbook_id,
                "number": section.section_number,
                "title": section.title,
                "chapter_number": section.chapter_number
            })
            
            # HAS_SECTION relationship
            await connection.execute_query("""
                MATCH (c:Chapter {textbook_id: $textbook_id, chapter_number: $chapter_number})
                MATCH (s:Section {textbook_id: $textbook_id, section_number: $section_number})
                MERGE (c)-[:HAS_SECTION]->(s)
            """, {
                "textbook_id": textbook_id,
                "chapter_number": section.chapter_number,
                "section_number": section.section_number
            })
            
            # NEXT relationship between sections
            if i > 0:
                await connection.execute_query("""
                    MATCH (s1:Section {textbook_id: $textbook_id, section_number: $prev})
                    MATCH (s2:Section {textbook_id: $textbook_id, section_number: $curr})
                    MERGE (s1)-[:NEXT]->(s2)
                """, {
                    "textbook_id": textbook_id,
                    "prev": sections[i-1].section_number,
                    "curr": section.section_number
                })
        
        # Create concepts with relationships
        for i, concept in enumerate(concepts):
            await connection.execute_query("""
                MERGE (co:Concept {
                    textbook_id: $textbook_id,
                    section_number: $section_number,
                    concept_name: $concept_name
                })
            """, {
                "textbook_id": textbook_id,
                "section_number": concept.section_number,
                "concept_name": concept.concept_name
            })
            
            # CONTAINS_CONCEPT relationship
            await connection.execute_query("""
                MATCH (s:Section {textbook_id: $textbook_id, section_number: $section_number})
                MATCH (co:Concept {
                    textbook_id: $textbook_id,
                    section_number: $section_number,
                    concept_name: $concept_name
                })
                MERGE (s)-[:CONTAINS_CONCEPT]->(co)
            """, {
                "textbook_id": textbook_id,
                "section_number": concept.section_number,
                "concept_name": concept.concept_name
            })
            
            # NEXT relationship between concepts
            if i > 0 and concepts[i-1].section_number == concept.section_number:
                await connection.execute_query("""
                    MATCH (co1:Concept {
                        textbook_id: $textbook_id,
                        section_number: $section_number,
                        concept_name: $prev_name
                    })
                    MATCH (co2:Concept {
                        textbook_id: $textbook_id,
                        section_number: $section_number,
                        concept_name: $curr_name
                    })
                    MERGE (co1)-[:NEXT]->(co2)
                """, {
                    "textbook_id": textbook_id,
                    "section_number": concept.section_number,
                    "prev_name": concepts[i-1].concept_name,
                    "curr_name": concept.concept_name
                })
        
        # Create chunks with relationships and embeddings
        batch_size = 50
        chunks_with_embeddings = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            
            # Prepare batch data
            batch_data = []
            for chunk_metadata, chunk_text in batch:
                # Get embedding if available
                embedding = getattr(chunk_metadata, 'embedding', None)
                if embedding:
                    chunks_with_embeddings += 1
                
                batch_data.append({
                    "chunk_id": chunk_metadata.chunk_id,
                    "textbook_id": textbook_id,
                    "chapter_number": int(chunk_metadata.chapter.split()[1]),
                    "section_number": chunk_metadata.section,
                    "concept_name": chunk_metadata.title if "Section" not in chunk_metadata.title else None,
                    "text": chunk_text,
                    "embedding": embedding,
                    "has_embedding": embedding is not None,
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split())
                })
            
            # Batch insert chunks with embeddings
            await connection.execute_batch_write("""
                CREATE (ch:Chunk {
                    chunk_id: $chunk_id,
                    textbook_id: $textbook_id,
                    chapter_number: $chapter_number,
                    section_number: $section_number,
                    concept_name: $concept_name,
                    text: $text,
                    embedding: $embedding,
                    has_embedding: $has_embedding,
                    char_count: $char_count,
                    word_count: $word_count,
                    created_at: datetime()
                })
            """, batch_data, batch_size=batch_size)
        
        logger.info(f"Stored {len(chunks)} chunks, {chunks_with_embeddings} with embeddings")
        
        # Create chunk relationships
        await connection.execute_query("""
            MATCH (ch:Chunk {textbook_id: $textbook_id})
            MATCH (s:Section {textbook_id: $textbook_id, section_number: ch.section_number})
            MERGE (ch)-[:BELONGS_TO]->(s)
        """, {"textbook_id": textbook_id})
        
        # Create vector index for chunks if embeddings are present
        if chunks_with_embeddings > 0:
            try:
                logger.info("Creating vector index for chunk embeddings...")
                
                # Check if index already exists
                index_exists_query = """
                    SHOW INDEXES
                    YIELD name
                    WHERE name = 'chunkEmbeddingIndex'
                    RETURN count(*) > 0 as exists
                """
                
                result = await connection.execute_query(index_exists_query)
                index_exists = result[0]["exists"] if result else False
                
                if not index_exists:
                    # Create index for embedding property
                    create_index_query = """
                        CREATE INDEX chunkEmbeddingIndex IF NOT EXISTS
                        FOR (c:Chunk)
                        ON (c.embedding)
                    """
                    await connection.execute_query(create_index_query)
                    logger.info("Created chunkEmbeddingIndex for vector similarity searches")
                else:
                    logger.info("Vector index chunkEmbeddingIndex already exists")
                    
            except Exception as e:
                logger.warning(f"Failed to create vector index: {e}")
        
        logger.info("Neo4j storage completed")