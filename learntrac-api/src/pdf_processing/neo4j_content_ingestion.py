"""
Neo4j Content Ingestion Pipeline for Educational Content

Manages the ingestion of processed educational content into Neo4j including:
- Textbook hierarchy creation
- Chunk storage with embeddings
- Concept extraction and linking
- Relationship management
- Batch processing optimization
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import json

from .neo4j_connection_manager import Neo4jConnectionManager
from .neo4j_vector_index_manager import Neo4jVectorIndexManager, VectorIndexConfig
from .chunk_metadata import ChunkMetadata, ContentType
from .structure_detector import StructureElement, StructureType
from .pipeline import ProcessingResult

logger = logging.getLogger(__name__)


@dataclass
class TextbookMetadata:
    """Metadata for a textbook"""
    textbook_id: str
    title: str
    subject: str
    authors: List[str]
    source_file: str
    processing_date: datetime
    processing_version: str
    quality_metrics: Dict[str, float]
    statistics: Dict[str, int]


@dataclass
class IngestionResult:
    """Result of content ingestion"""
    success: bool
    textbook_id: str
    nodes_created: Dict[str, int]
    relationships_created: Dict[str, int]
    errors: List[str]
    warnings: List[str]
    processing_time: float
    
    def summary(self) -> str:
        """Generate summary string"""
        return f"""
Ingestion {'Successful' if self.success else 'Failed'} for {self.textbook_id}
Nodes created: {sum(self.nodes_created.values())} ({', '.join(f'{k}: {v}' for k, v in self.nodes_created.items())})
Relationships created: {sum(self.relationships_created.values())} ({', '.join(f'{k}: {v}' for k, v in self.relationships_created.items())})
Processing time: {self.processing_time:.2f}s
Errors: {len(self.errors)}
Warnings: {len(self.warnings)}
"""


class Neo4jContentIngestion:
    """
    Manages content ingestion into Neo4j for educational content.
    
    Features:
    - Hierarchical content structure creation
    - Batch processing for performance
    - Concept extraction and linking
    - Duplicate detection
    - Transaction management
    - Progress tracking
    """
    
    def __init__(
        self,
        connection_manager: Neo4jConnectionManager,
        index_manager: Neo4jVectorIndexManager,
        batch_size: int = 1000
    ):
        """
        Initialize content ingestion pipeline.
        
        Args:
            connection_manager: Neo4j connection manager
            index_manager: Vector index manager
            batch_size: Batch size for operations
        """
        self.connection = connection_manager
        self.index_manager = index_manager
        self.batch_size = batch_size
        
    async def ingest_processing_result(
        self,
        processing_result: ProcessingResult,
        chunks: List[Tuple[ChunkMetadata, str, List[float]]],
        textbook_metadata: Optional[TextbookMetadata] = None
    ) -> IngestionResult:
        """
        Ingest a complete processing result into Neo4j.
        
        Args:
            processing_result: Result from PDF processing pipeline
            chunks: List of (metadata, text, embedding) tuples
            textbook_metadata: Optional textbook metadata override
            
        Returns:
            Ingestion result with statistics
        """
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        nodes_created = {
            "textbooks": 0,
            "chapters": 0,
            "sections": 0,
            "chunks": 0,
            "concepts": 0
        }
        relationships_created = {
            "structural": 0,
            "sequential": 0,
            "conceptual": 0
        }
        
        try:
            # Generate textbook metadata if not provided
            if not textbook_metadata:
                textbook_metadata = self._create_textbook_metadata(processing_result)
            
            # Check for existing textbook
            if await self._textbook_exists(textbook_metadata.textbook_id):
                warnings.append(f"Textbook {textbook_metadata.textbook_id} already exists, updating...")
            
            # Create textbook node
            logger.info(f"Creating textbook node: {textbook_metadata.title}")
            await self._create_textbook_node(textbook_metadata)
            nodes_created["textbooks"] = 1
            
            # Process structure elements
            chapter_map = {}
            section_map = {}
            
            # Group structure elements by type
            chapters = [e for e in processing_result.structure_elements if e.element_type == "chapter"]
            sections = [e for e in processing_result.structure_elements if e.element_type == "section"]
            
            # Create chapter nodes
            logger.info(f"Creating {len(chapters)} chapter nodes")
            chapter_batch = []
            for i, chapter in enumerate(chapters):
                chapter_id = f"{textbook_metadata.textbook_id}_ch_{i+1}"
                chapter_map[chapter.start_position] = chapter_id
                
                chapter_batch.append({
                    "chapter_id": chapter_id,
                    "chapter_number": i + 1,
                    "title": chapter.content,
                    "start_position": chapter.start_position,
                    "end_position": chapter.end_position,
                    "textbook_id": textbook_metadata.textbook_id
                })
            
            await self._batch_create_chapters(chapter_batch)
            nodes_created["chapters"] = len(chapter_batch)
            
            # Create section nodes
            logger.info(f"Creating {len(sections)} section nodes")
            section_batch = []
            for i, section in enumerate(sections):
                section_id = f"{textbook_metadata.textbook_id}_sec_{i+1}"
                section_map[section.start_position] = section_id
                
                # Find parent chapter
                parent_chapter_id = self._find_parent_chapter(
                    section.start_position,
                    chapters,
                    chapter_map
                )
                
                section_batch.append({
                    "section_id": section_id,
                    "section_number": self._extract_section_number(section.content),
                    "title": section.content,
                    "level": section.level,
                    "start_position": section.start_position,
                    "end_position": section.end_position,
                    "parent_chapter_id": parent_chapter_id
                })
            
            await self._batch_create_sections(section_batch)
            nodes_created["sections"] = len(section_batch)
            
            # Create structural relationships
            rel_count = await self._create_structural_relationships(
                textbook_metadata.textbook_id,
                chapter_batch,
                section_batch
            )
            relationships_created["structural"] = rel_count
            
            # Process chunks
            logger.info(f"Processing {len(chunks)} chunks")
            chunk_batch = []
            concept_set = set()
            
            for i, (chunk_metadata, text, embedding) in enumerate(chunks):
                chunk_data = {
                    "chunk_id": chunk_metadata.chunk_id,
                    "content_type": chunk_metadata.content_type.value,
                    "text": text,
                    "embedding": embedding,
                    "textbook_id": textbook_metadata.textbook_id,
                    "chapter": chunk_metadata.chapter,
                    "section": chunk_metadata.section,
                    "difficulty_score": chunk_metadata.difficulty,
                    "confidence_score": chunk_metadata.confidence_score,
                    "start_position": chunk_metadata.start_position,
                    "end_position": chunk_metadata.end_position,
                    "metadata": asdict(chunk_metadata)
                }
                
                # Find parent chapter and section
                chunk_data["parent_chapter_id"] = self._find_parent_by_position(
                    chunk_metadata.start_position,
                    chapter_batch,
                    "chapter_id"
                )
                chunk_data["parent_section_id"] = self._find_parent_by_position(
                    chunk_metadata.start_position,
                    section_batch,
                    "section_id"
                )
                
                chunk_batch.append(chunk_data)
                
                # Collect concepts
                if hasattr(chunk_metadata, 'concepts') and chunk_metadata.concepts:
                    concept_set.update(chunk_metadata.concepts)
                
                # Process batch when full
                if len(chunk_batch) >= self.batch_size:
                    await self._batch_create_chunks(chunk_batch)
                    nodes_created["chunks"] += len(chunk_batch)
                    chunk_batch = []
            
            # Process remaining chunks
            if chunk_batch:
                await self._batch_create_chunks(chunk_batch)
                nodes_created["chunks"] += len(chunk_batch)
            
            # Create sequential relationships
            logger.info("Creating sequential relationships")
            seq_rel_count = await self._create_sequential_relationships(
                textbook_metadata.textbook_id
            )
            relationships_created["sequential"] = seq_rel_count
            
            # Process concepts
            if concept_set:
                logger.info(f"Processing {len(concept_set)} unique concepts")
                concept_count = await self._process_concepts(
                    list(concept_set),
                    textbook_metadata.textbook_id
                )
                nodes_created["concepts"] = concept_count
                
                # Link concepts to chunks
                concept_rel_count = await self._link_concepts_to_chunks(
                    textbook_metadata.textbook_id
                )
                relationships_created["conceptual"] = concept_rel_count
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Ingestion completed successfully for {textbook_metadata.textbook_id}")
            
            return IngestionResult(
                success=True,
                textbook_id=textbook_metadata.textbook_id,
                nodes_created=nodes_created,
                relationships_created=relationships_created,
                errors=errors,
                warnings=warnings,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            errors.append(str(e))
            
            return IngestionResult(
                success=False,
                textbook_id=textbook_metadata.textbook_id if textbook_metadata else "unknown",
                nodes_created=nodes_created,
                relationships_created=relationships_created,
                errors=errors,
                warnings=warnings,
                processing_time=(datetime.utcnow() - start_time).total_seconds()
            )
    
    async def update_textbook_embeddings(
        self,
        textbook_id: str,
        chunks: List[Tuple[str, List[float]]]
    ) -> bool:
        """
        Update embeddings for existing chunks.
        
        Args:
            textbook_id: Textbook identifier
            chunks: List of (chunk_id, embedding) tuples
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
                MATCH (c:Chunk {chunk_id: $chunk_id})
                WHERE c.textbook_id = $textbook_id
                SET c.embedding = $embedding
            """
            
            batch_data = [
                {
                    "chunk_id": chunk_id,
                    "embedding": embedding,
                    "textbook_id": textbook_id
                }
                for chunk_id, embedding in chunks
            ]
            
            result = await self.connection.execute_batch_write(
                query,
                batch_data,
                self.batch_size
            )
            
            return result["success_rate"] > 0.9
            
        except Exception as e:
            logger.error(f"Failed to update embeddings: {e}")
            return False
    
    async def delete_textbook(self, textbook_id: str) -> bool:
        """
        Delete a textbook and all its content.
        
        Args:
            textbook_id: Textbook identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
                MATCH (t:Textbook {textbook_id: $textbook_id})
                OPTIONAL MATCH (t)-[*]-(n)
                DETACH DELETE t, n
            """
            
            await self.connection.execute_query(
                query,
                {"textbook_id": textbook_id}
            )
            
            logger.info(f"Deleted textbook: {textbook_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete textbook: {e}")
            return False
    
    def _create_textbook_metadata(self, processing_result: ProcessingResult) -> TextbookMetadata:
        """Create textbook metadata from processing result"""
        # Generate unique ID from file path
        file_path = processing_result.metadata.file_path
        textbook_id = hashlib.md5(file_path.encode()).hexdigest()[:16]
        
        # Extract title from file name
        title = file_path.split('/')[-1].replace('.pdf', '').replace('_', ' ').title()
        
        return TextbookMetadata(
            textbook_id=textbook_id,
            title=title,
            subject="Unknown",  # Could be extracted from content
            authors=[],  # Could be extracted from metadata
            source_file=file_path,
            processing_date=datetime.utcnow(),
            processing_version=processing_result.metadata.pdf_processor_method,
            quality_metrics={
                "extraction_confidence": processing_result.quality_metrics.extraction_confidence,
                "structure_quality": processing_result.quality_metrics.structure_detection_score,
                "content_coherence": processing_result.quality_metrics.content_coherence,
                "overall_quality": processing_result.quality_metrics.overall_quality_score
            },
            statistics={
                "total_chapters": processing_result.metadata.chapters_detected,
                "total_sections": processing_result.metadata.sections_detected,
                "total_words": processing_result.metadata.filtered_text_length // 5,  # Rough estimate
                "total_chunks": 0  # Will be updated
            }
        )
    
    async def _textbook_exists(self, textbook_id: str) -> bool:
        """Check if textbook already exists"""
        query = """
            MATCH (t:Textbook {textbook_id: $textbook_id})
            RETURN count(t) > 0 as exists
        """
        
        results = await self.connection.execute_query(
            query,
            {"textbook_id": textbook_id}
        )
        
        return results[0]["exists"] if results else False
    
    async def _create_textbook_node(self, metadata: TextbookMetadata) -> None:
        """Create or update textbook node"""
        query = """
            MERGE (t:Textbook {textbook_id: $textbook_id})
            SET t += $properties
        """
        
        properties = {
            "title": metadata.title,
            "subject": metadata.subject,
            "authors": metadata.authors,
            "source_file": metadata.source_file,
            "processing_date": metadata.processing_date.isoformat(),
            "processing_version": metadata.processing_version,
            "extraction_confidence": metadata.quality_metrics["extraction_confidence"],
            "structure_quality": metadata.quality_metrics["structure_quality"],
            "content_coherence": metadata.quality_metrics["content_coherence"],
            "overall_quality": metadata.quality_metrics["overall_quality"],
            "total_chapters": metadata.statistics["total_chapters"],
            "total_sections": metadata.statistics["total_sections"],
            "total_words": metadata.statistics["total_words"],
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await self.connection.execute_query(
            query,
            {
                "textbook_id": metadata.textbook_id,
                "properties": properties
            }
        )
    
    async def _batch_create_chapters(self, chapters: List[Dict[str, Any]]) -> None:
        """Batch create chapter nodes"""
        query = """
            UNWIND $chapters as chapter
            MERGE (c:Chapter {chapter_id: chapter.chapter_id})
            SET c += {
                chapter_number: chapter.chapter_number,
                title: chapter.title,
                start_position: chapter.start_position,
                end_position: chapter.end_position,
                word_count: chapter.end_position - chapter.start_position
            }
            WITH c, chapter
            MATCH (t:Textbook {textbook_id: chapter.textbook_id})
            MERGE (t)-[:HAS_CHAPTER]->(c)
        """
        
        await self.connection.execute_query(
            query,
            {"chapters": chapters}
        )
    
    async def _batch_create_sections(self, sections: List[Dict[str, Any]]) -> None:
        """Batch create section nodes"""
        query = """
            UNWIND $sections as section
            MERGE (s:Section {section_id: section.section_id})
            SET s += {
                section_number: section.section_number,
                title: section.title,
                level: section.level,
                start_position: section.start_position,
                end_position: section.end_position,
                word_count: section.end_position - section.start_position
            }
            WITH s, section
            WHERE section.parent_chapter_id IS NOT NULL
            MATCH (c:Chapter {chapter_id: section.parent_chapter_id})
            MERGE (c)-[:HAS_SECTION]->(s)
        """
        
        await self.connection.execute_query(
            query,
            {"sections": sections}
        )
    
    async def _batch_create_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Batch create chunk nodes with embeddings"""
        query = """
            UNWIND $chunks as chunk
            MERGE (c:Chunk {chunk_id: chunk.chunk_id})
            SET c += {
                content_type: chunk.content_type,
                text: chunk.text,
                embedding: chunk.embedding,
                difficulty_score: chunk.difficulty_score,
                confidence_score: chunk.confidence_score,
                start_position: chunk.start_position,
                end_position: chunk.end_position,
                char_count: size(chunk.text),
                word_count: size(split(chunk.text, ' ')),
                created_at: datetime()
            }
            WITH c, chunk
            MATCH (t:Textbook {textbook_id: chunk.textbook_id})
            MERGE (c)-[:BELONGS_TO_TEXTBOOK]->(t)
            WITH c, chunk
            WHERE chunk.parent_chapter_id IS NOT NULL
            MATCH (ch:Chapter {chapter_id: chunk.parent_chapter_id})
            MERGE (c)-[:BELONGS_TO_CHAPTER]->(ch)
            WITH c, chunk
            WHERE chunk.parent_section_id IS NOT NULL
            MATCH (s:Section {section_id: chunk.parent_section_id})
            MERGE (c)-[:BELONGS_TO_SECTION]->(s)
            MERGE (s)-[:HAS_CHUNK]->(c)
        """
        
        await self.connection.execute_query(
            query,
            {"chunks": chunks}
        )
    
    async def _create_structural_relationships(
        self,
        textbook_id: str,
        chapters: List[Dict[str, Any]],
        sections: List[Dict[str, Any]]
    ) -> int:
        """Create structural relationships between nodes"""
        count = 0
        
        # Already created in batch operations
        count += len(chapters)  # HAS_CHAPTER relationships
        count += len(sections)  # HAS_SECTION relationships
        
        return count
    
    async def _create_sequential_relationships(self, textbook_id: str) -> int:
        """Create NEXT relationships between sequential elements"""
        count = 0
        
        # Sequential chapters
        query = """
            MATCH (t:Textbook {textbook_id: $textbook_id})-[:HAS_CHAPTER]->(c:Chapter)
            WITH c ORDER BY c.chapter_number
            WITH collect(c) as chapters
            UNWIND range(0, size(chapters)-2) as idx
            WITH chapters[idx] as c1, chapters[idx+1] as c2
            MERGE (c1)-[:NEXT]->(c2)
            RETURN count(*) as count
        """
        
        results = await self.connection.execute_query(
            query,
            {"textbook_id": textbook_id}
        )
        
        if results:
            count += results[0]["count"]
        
        # Sequential chunks within sections
        query = """
            MATCH (s:Section)-[:HAS_CHUNK]->(c:Chunk)
            WITH s, c ORDER BY c.start_position
            WITH s, collect(c) as chunks
            UNWIND range(0, size(chunks)-2) as idx
            WITH chunks[idx] as c1, chunks[idx+1] as c2
            MERGE (c1)-[:NEXT]->(c2)
            RETURN count(*) as count
        """
        
        results = await self.connection.execute_query(query)
        
        if results:
            count += results[0]["count"]
        
        return count
    
    async def _process_concepts(
        self,
        concepts: List[str],
        textbook_id: str
    ) -> int:
        """Process and create concept nodes"""
        query = """
            UNWIND $concepts as concept_name
            MERGE (c:Concept {name: concept_name})
            ON CREATE SET c += {
                concept_id: apoc.create.uuid(),
                type: 'extracted',
                subject_area: $subject_area,
                created_at: datetime()
            }
            SET c.reference_count = coalesce(c.reference_count, 0) + 1
            RETURN count(*) as count
        """
        
        # Extract subject from textbook
        textbook_query = """
            MATCH (t:Textbook {textbook_id: $textbook_id})
            RETURN t.subject as subject
        """
        
        results = await self.connection.execute_query(
            textbook_query,
            {"textbook_id": textbook_id}
        )
        
        subject = results[0]["subject"] if results else "Unknown"
        
        results = await self.connection.execute_query(
            query,
            {
                "concepts": concepts,
                "subject_area": subject
            }
        )
        
        return results[0]["count"] if results else 0
    
    async def _link_concepts_to_chunks(self, textbook_id: str) -> int:
        """Link concepts to chunks that mention them"""
        # This is a simplified version - in practice you'd extract concepts from chunk metadata
        query = """
            MATCH (c:Chunk)-[:BELONGS_TO_TEXTBOOK]->(t:Textbook {textbook_id: $textbook_id})
            MATCH (concept:Concept)
            WHERE toLower(c.text) CONTAINS toLower(concept.name)
            MERGE (c)-[:MENTIONS_CONCEPT]->(concept)
            RETURN count(*) as count
        """
        
        results = await self.connection.execute_query(
            query,
            {"textbook_id": textbook_id}
        )
        
        return results[0]["count"] if results else 0
    
    def _find_parent_chapter(
        self,
        position: int,
        chapters: List[StructureElement],
        chapter_map: Dict[int, str]
    ) -> Optional[str]:
        """Find parent chapter for a given position"""
        for chapter in reversed(chapters):
            if chapter.start_position <= position:
                return chapter_map.get(chapter.start_position)
        return None
    
    def _find_parent_by_position(
        self,
        position: int,
        elements: List[Dict[str, Any]],
        id_field: str
    ) -> Optional[str]:
        """Find parent element by position"""
        for element in reversed(elements):
            if element["start_position"] <= position <= element["end_position"]:
                return element[id_field]
        return None
    
    def _extract_section_number(self, section_title: str) -> str:
        """Extract section number from title"""
        import re
        match = re.match(r'^(\d+(?:\.\d+)*)', section_title)
        return match.group(1) if match else ""