"""
Trac API Service Layer

Provides a unified interface for Trac integration including:
- Textbook content management
- Learning progress tracking
- Concept relationship management
- User progress analytics
- Recommendation generation
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
import json

from ..db.database import DatabaseManager
from ..db.trac_bridge import TracDatabaseBridge
# Redis removed - from ..services.redis_client import RedisCache
from ..pdf_processing.neo4j_connection_manager import Neo4jConnectionManager, ConnectionConfig
from ..pdf_processing.neo4j_vector_index_manager import Neo4jVectorIndexManager
from ..pdf_processing.neo4j_content_ingestion import Neo4jContentIngestion, TextbookMetadata
from ..pdf_processing.neo4j_vector_search import (
    Neo4jVectorSearch, SearchMode, SearchFilters, 
    SearchContext, SearchResults
)
from ..pdf_processing.neo4j_relationship_manager import Neo4jRelationshipManager
from ..pdf_processing.neo4j_query_optimizer import Neo4jQueryOptimizer, CacheStrategy
from ..pdf_processing.pipeline import PDFProcessingPipeline
from ..pdf_processing.content_chunker import ContentChunker
from ..pdf_processing.embedding_pipeline import EmbeddingPipeline
from ..pdf_processing.toc_pdf_processor import TOCPDFProcessor
from ..services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class LearningProgress:
    """User's learning progress for a concept or topic"""
    user_id: str
    concept_id: str
    concept_name: str
    understanding_level: float  # 0-1
    time_spent_minutes: int
    last_accessed: datetime
    completed_chunks: List[str]
    mastery_score: float  # 0-1
    
    
@dataclass
class UserProfile:
    """User learning profile"""
    user_id: str
    email: str
    name: str
    level: str  # beginner/intermediate/advanced
    interests: List[str]
    learning_history: List[str]  # chunk IDs
    total_time_minutes: int
    concepts_mastered: List[str]
    current_learning_path: Optional[str]
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentRecommendation:
    """Content recommendation for a user"""
    chunk_id: str
    score: float
    reason: str
    concept: str
    difficulty: float
    estimated_time_minutes: int
    prerequisites_met: bool


class TracService:
    """
    Main service layer for Trac integration.
    
    Coordinates between:
    - PDF processing pipeline
    - Neo4j graph database
    - Trac ticket system
    - User management
    - Learning analytics
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        neo4j_config: ConnectionConfig,
        # redis_cache: RedisCache,  # Redis removed
        embedding_service: EmbeddingService
    ):
        """
        Initialize Trac service.
        
        Args:
            db_manager: Database manager for PostgreSQL
            neo4j_config: Neo4j connection configuration
            embedding_service: Embedding generation service
        """
        self.db_manager = db_manager
        # self.redis_cache = redis_cache  # Redis removed
        self.embedding_service = embedding_service
        
        # Initialize Trac bridge
        self.trac_bridge = TracDatabaseBridge(db_manager.pool)
        
        # Initialize Neo4j components
        self.neo4j_connection = Neo4jConnectionManager(neo4j_config)
        self.neo4j_index_manager = Neo4jVectorIndexManager(self.neo4j_connection)
        self.neo4j_ingestion = Neo4jContentIngestion(
            self.neo4j_connection,
            self.neo4j_index_manager
        )
        self.neo4j_search = Neo4jVectorSearch(
            self.neo4j_connection,
            self.neo4j_index_manager
        )
        self.neo4j_relationships = Neo4jRelationshipManager(self.neo4j_connection)
        self.neo4j_optimizer = Neo4jQueryOptimizer(
            self.neo4j_connection,
            cache_strategy=CacheStrategy.ADAPTIVE
        )
        
        # Initialize PDF processing components
        self.pdf_pipeline = PDFProcessingPipeline()
        self.content_chunker = ContentChunker()
        self.embedding_pipeline = EmbeddingPipeline()
        self.toc_processor = TOCPDFProcessor()
        
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize all service components"""
        try:
            # Initialize Neo4j connection
            if not await self.neo4j_connection.initialize():
                logger.error("Failed to initialize Neo4j connection")
                return False
            
            # Create required indexes
            indexes_created = await self.neo4j_index_manager.create_educational_indexes()
            logger.info(f"Created indexes: {indexes_created}")
            
            # Warm up cache with common queries
            await self._warm_cache()
            
            self._initialized = True
            logger.info("TracService initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TracService: {e}")
            return False
    
    async def close(self) -> None:
        """Close all service connections"""
        await self.neo4j_connection.close()
        self._initialized = False
    
    # ===== Textbook Management =====
    
    async def ingest_textbook(
        self,
        pdf_path: str,
        metadata: Optional[TextbookMetadata] = None
    ) -> Dict[str, Any]:
        """
        Ingest a textbook PDF into the system using TOC-based processing.
        
        Args:
            pdf_path: Path to PDF file
            metadata: Optional textbook metadata
            
        Returns:
            Ingestion result with statistics
        """
        try:
            # Use TOC-based processor for textbook PDFs
            logger.info(f"Processing PDF using TOC-based approach: {pdf_path}")
            
            # Get embedding dimensions from the service
            embedding_dimensions = self.embedding_service.get_embedding_dimension()
            logger.info(f"Using embedding dimensions: {embedding_dimensions}")
            
            # Ensure vector indexes exist for embeddings
            logger.info("Ensuring vector indexes exist...")
            index_results = await self.neo4j_index_manager.create_educational_indexes(
                embedding_dimensions=embedding_dimensions
            )
            logger.info(f"Vector index creation results: {index_results}")
            
            # Process the PDF with TOC extraction and embedding
            processing_result = await self.toc_processor.process_pdf(
                pdf_path=pdf_path,
                connection_manager=self.neo4j_connection,
                index_manager=self.neo4j_index_manager,
                embedding_service=self.embedding_service,
                max_chunks_to_embed=None  # Embed all chunks
            )
            
            if not processing_result.success:
                return {
                    "success": False,
                    "error": processing_result.error or "PDF processing failed",
                    "details": {}
                }
            
            # Create Trac tickets for main concepts
            await self._create_concept_tickets(processing_result.textbook_id)
            
            # Cache textbook metadata if provided
            if metadata:
                await self._cache_textbook_metadata(
                    processing_result.textbook_id,
                    metadata
                )
            
            return {
                "success": processing_result.success,
                "textbook_id": processing_result.textbook_id,
                "statistics": {
                    "chapters": len(processing_result.chapters),
                    "sections": len(processing_result.sections),
                    "concepts": len(processing_result.concepts),
                    "chunks": processing_result.total_chunks,
                    "embeddings_generated": processing_result.embeddings_generated,
                    "processing_time": processing_result.processing_time,
                    "embedding_dimensions": embedding_dimensions,
                    "vector_indexes_created": sum(index_results.values()) if 'index_results' in locals() else 0
                },
                "summary": processing_result.summary(),
                "details": {
                    "chapters_processed": [
                        {
                            "number": ch.number,
                            "title": ch.title,
                            "sections": len(ch.sections)
                        }
                        for ch in processing_result.chapters[:5]  # First 5 chapters
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest textbook: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_content(
        self,
        query: str,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> SearchResults:
        """
        Search educational content.
        
        Args:
            query: Search query text
            user_id: Optional user ID for personalization
            filters: Search filters
            limit: Maximum results
            
        Returns:
            Search results
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)
        
        # Build search context if user provided
        context = None
        if user_id:
            user_profile = await self.get_user_profile(user_id)
            if user_profile:
                context = SearchContext(
                    user_level=user_profile.level,
                    learning_history=user_profile.learning_history[-50:],
                    current_concepts=await self._get_user_current_concepts(user_id)
                )
        
        # Build search filters
        search_filters = SearchFilters()
        if filters:
            if "difficulty_range" in filters:
                search_filters.difficulty_range = tuple(filters["difficulty_range"])
            if "content_types" in filters:
                search_filters.content_types = filters["content_types"]
            if "textbook_ids" in filters:
                search_filters.textbook_ids = filters["textbook_ids"]
        
        # Perform search
        results = await self.neo4j_search.search(
            query_embedding,
            mode=SearchMode.HYBRID,
            filters=search_filters,
            context=context,
            limit=limit
        )
        
        # Log search for analytics
        await self._log_search(user_id, query, len(results.results))
        
        return results
    
    # ===== Learning Progress Management =====
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user learning profile"""
        # Redis removed - skip cache check
        # cached = await self.redis_cache.get(f"user_profile:{user_id}")
        # if cached:
        #     return UserProfile(**json.loads(cached))
        
        # Query database
        user_data = await self.db_manager.fetch_one(
            """
            SELECT u.*, up.preferences, up.learning_stats
            FROM users u
            LEFT JOIN user_profiles up ON u.id = up.user_id
            WHERE u.id = $1
            """,
            user_id
        )
        
        if not user_data:
            return None
        
        # Get learning history
        history = await self.db_manager.fetch_all(
            """
            SELECT chunk_id
            FROM user_learning_history
            WHERE user_id = $1
            ORDER BY accessed_at DESC
            LIMIT 100
            """,
            user_id
        )
        
        profile = UserProfile(
            user_id=user_id,
            email=user_data["email"],
            name=user_data["name"],
            level=user_data.get("level", "beginner"),
            interests=user_data.get("interests", []),
            learning_history=[h["chunk_id"] for h in history],
            total_time_minutes=user_data.get("total_time_minutes", 0),
            concepts_mastered=user_data.get("concepts_mastered", []),
            current_learning_path=user_data.get("current_learning_path"),
            preferences=user_data.get("preferences", {})
        )
        
        # Redis removed - skip caching
        # await self.redis_cache.set(
        #     f"user_profile:{user_id}",
        #     json.dumps(profile.__dict__, default=str),
        #     ttl=3600
        # )
        
        return profile
    
    async def track_learning_progress(
        self,
        user_id: str,
        chunk_id: str,
        time_spent_seconds: int,
        understanding_level: float
    ) -> bool:
        """
        Track user's learning progress.
        
        Args:
            user_id: User identifier
            chunk_id: Chunk being studied
            time_spent_seconds: Time spent on chunk
            understanding_level: Self-reported understanding (0-1)
            
        Returns:
            Success status
        """
        try:
            # Record in database
            await self.db_manager.execute(
                """
                INSERT INTO user_learning_progress
                (user_id, chunk_id, time_spent_seconds, understanding_level, timestamp)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id, chunk_id, time_spent_seconds, 
                understanding_level, datetime.utcnow()
            )
            
            # Update learning history
            await self.db_manager.execute(
                """
                INSERT INTO user_learning_history (user_id, chunk_id, accessed_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, chunk_id) 
                DO UPDATE SET accessed_at = EXCLUDED.accessed_at
                """,
                user_id, chunk_id, datetime.utcnow()
            )
            
            # Update concept mastery
            await self._update_concept_mastery(user_id, chunk_id, understanding_level)
            
            # Redis removed - skip cache invalidation
            # await self.redis_cache.delete(f"user_profile:{user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to track learning progress: {e}")
            return False
    
    async def get_learning_progress(
        self,
        user_id: str,
        concept_id: Optional[str] = None
    ) -> List[LearningProgress]:
        """
        Get user's learning progress.
        
        Args:
            user_id: User identifier
            concept_id: Optional specific concept
            
        Returns:
            List of learning progress records
        """
        query = """
            SELECT 
                c.concept_id,
                c.name as concept_name,
                COALESCE(AVG(ulp.understanding_level), 0) as understanding_level,
                COALESCE(SUM(ulp.time_spent_seconds) / 60, 0) as time_spent_minutes,
                MAX(ulp.timestamp) as last_accessed,
                COUNT(DISTINCT ulp.chunk_id) as chunks_studied,
                COALESCE(ucm.mastery_score, 0) as mastery_score
            FROM concepts c
            LEFT JOIN chunks ch ON ch.concepts @> ARRAY[c.name]
            LEFT JOIN user_learning_progress ulp ON ulp.chunk_id = ch.chunk_id 
                AND ulp.user_id = $1
            LEFT JOIN user_concept_mastery ucm ON ucm.concept_id = c.concept_id 
                AND ucm.user_id = $1
            WHERE ($2::text IS NULL OR c.concept_id = $2)
            GROUP BY c.concept_id, c.name, ucm.mastery_score
            HAVING COUNT(ulp.chunk_id) > 0
            ORDER BY last_accessed DESC
        """
        
        results = await self.db_manager.fetch_all(query, user_id, concept_id)
        
        progress_list = []
        for row in results:
            # Get completed chunks
            chunks_query = """
                SELECT DISTINCT ulp.chunk_id
                FROM user_learning_progress ulp
                JOIN chunks ch ON ch.chunk_id = ulp.chunk_id
                WHERE ulp.user_id = $1 
                AND ch.concepts @> ARRAY[$2]
                AND ulp.understanding_level >= 0.7
            """
            chunks = await self.db_manager.fetch_all(
                chunks_query, 
                user_id, 
                row["concept_name"]
            )
            
            progress_list.append(LearningProgress(
                user_id=user_id,
                concept_id=row["concept_id"],
                concept_name=row["concept_name"],
                understanding_level=float(row["understanding_level"]),
                time_spent_minutes=int(row["time_spent_minutes"]),
                last_accessed=row["last_accessed"],
                completed_chunks=[c["chunk_id"] for c in chunks],
                mastery_score=float(row["mastery_score"])
            ))
        
        return progress_list
    
    # ===== Recommendations =====
    
    async def get_recommendations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[ContentRecommendation]:
        """
        Get personalized content recommendations.
        
        Args:
            user_id: User identifier
            limit: Maximum recommendations
            
        Returns:
            List of content recommendations
        """
        # Get user profile
        profile = await self.get_user_profile(user_id)
        if not profile:
            return []
        
        # Get user's current concepts
        current_concepts = await self._get_user_current_concepts(user_id)
        
        # Find next logical concepts
        next_concepts = []
        for concept in current_concepts:
            # Get concepts that build upon current ones
            query = """
                MATCH (current:Concept {name: $concept})
                MATCH (next:Concept)-[:REQUIRES]->(current)
                WHERE NOT next.name IN $mastered
                RETURN DISTINCT next.name as concept
                LIMIT 5
            """
            
            results = await self.neo4j_optimizer.execute_query(
                query,
                {
                    "concept": concept,
                    "mastered": profile.concepts_mastered
                }
            )
            
            next_concepts.extend([r["concept"] for r in results[0]])
        
        # Get chunks for recommended concepts
        recommendations = []
        
        for concept in set(next_concepts[:limit]):
            # Find best chunk for this concept
            chunk_query = """
                MATCH (c:Chunk)-[:INTRODUCES_CONCEPT|EXPLAINS_CONCEPT]->(concept:Concept {name: $concept})
                WHERE c.difficulty_score >= $min_diff AND c.difficulty_score <= $max_diff
                AND NOT c.chunk_id IN $history
                RETURN c.chunk_id as chunk_id,
                       c.difficulty_score as difficulty,
                       c.confidence_score as quality
                ORDER BY quality DESC
                LIMIT 1
            """
            
            # Determine difficulty range based on user level
            diff_ranges = {
                "beginner": (0.0, 0.4),
                "intermediate": (0.3, 0.7),
                "advanced": (0.6, 1.0)
            }
            min_diff, max_diff = diff_ranges.get(profile.level, (0.0, 1.0))
            
            chunk_results = await self.neo4j_optimizer.execute_query(
                chunk_query,
                {
                    "concept": concept,
                    "min_diff": min_diff,
                    "max_diff": max_diff,
                    "history": profile.learning_history
                }
            )
            
            if chunk_results[0]:
                chunk = chunk_results[0][0]
                
                # Check prerequisites
                prereqs_met = await self._check_prerequisites(user_id, concept)
                
                recommendations.append(ContentRecommendation(
                    chunk_id=chunk["chunk_id"],
                    score=0.8 if prereqs_met else 0.5,
                    reason=f"Next logical step in learning {concept}",
                    concept=concept,
                    difficulty=chunk["difficulty"],
                    estimated_time_minutes=5,
                    prerequisites_met=prereqs_met
                ))
        
        # Sort by score and prerequisites
        recommendations.sort(
            key=lambda r: (r.prerequisites_met, r.score),
            reverse=True
        )
        
        return recommendations[:limit]
    
    # ===== Learning Paths =====
    
    async def create_learning_path(
        self,
        user_id: str,
        target_concepts: List[str],
        time_limit_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a personalized learning path.
        
        Args:
            user_id: User identifier
            target_concepts: Concepts to master
            time_limit_hours: Optional time constraint
            
        Returns:
            Learning path details
        """
        # Get user profile
        profile = await self.get_user_profile(user_id)
        if not profile:
            return {"error": "User not found"}
        
        # Generate learning path
        path_segments = await self.neo4j_relationships.suggest_learning_path(
            target_concepts,
            profile.level,
            max_chunks=100 if not time_limit_hours else time_limit_hours * 10
        )
        
        # Store learning path
        path_id = f"path_{user_id}_{datetime.utcnow().timestamp()}"
        
        await self.db_manager.execute(
            """
            INSERT INTO learning_paths
            (path_id, user_id, target_concepts, segments, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            path_id,
            user_id,
            target_concepts,
            json.dumps([
                {
                    "segment_id": seg.segment_id,
                    "concepts": seg.concepts,
                    "chunks": seg.chunks,
                    "prerequisites": seg.prerequisites,
                    "estimated_time": seg.estimated_time_minutes
                }
                for seg in path_segments
            ]),
            datetime.utcnow()
        )
        
        # Update user profile
        await self.db_manager.execute(
            """
            UPDATE user_profiles
            SET current_learning_path = $1
            WHERE user_id = $2
            """,
            path_id,
            user_id
        )
        
        return {
            "path_id": path_id,
            "segments": len(path_segments),
            "total_chunks": sum(len(seg.chunks) for seg in path_segments),
            "estimated_time_hours": sum(seg.estimated_time_minutes for seg in path_segments) / 60,
            "target_concepts": target_concepts
        }
    
    # ===== Private Helper Methods =====
    
    async def _warm_cache(self) -> None:
        """Warm up query cache with common queries"""
        common_queries = [
            (
                "MATCH (c:Concept) RETURN count(c) as count",
                {}
            ),
            (
                "MATCH (t:Textbook) RETURN t.title, t.subject, t.textbook_id",
                {}
            )
        ]
        
        await self.neo4j_optimizer.cache.warm_cache(
            common_queries,
            self.neo4j_connection
        )
    
    async def _create_concept_tickets(self, textbook_id: str) -> None:
        """Create Trac tickets for main concepts"""
        # Get main concepts from textbook using our new structure
        query = """
            MATCH (t:Textbook {textbook_id: $textbook_id})
            MATCH (c:Concept {textbook_id: $textbook_id})
            MATCH (s:Section {textbook_id: $textbook_id})-[:CONTAINS_CONCEPT]->(c)
            RETURN DISTINCT c.concept_name as name,
                   s.section_number as section,
                   count(DISTINCT c) as concept_count
            ORDER BY section
            LIMIT 20
        """
        
        results = await self.neo4j_connection.execute_query(
            query,
            {"textbook_id": textbook_id}
        )
        
        # Create tickets for top concepts
        for concept in results:
            await self.trac_bridge.create_learning_ticket(
                title=f"Learn: {concept['name'][:100]}",  # Limit title length
                description=f"Master the concept from section {concept['section']}: {concept['name']}",
                component="learning",
                type="concept",
                custom_fields={
                    "learning_difficulty": "2.0",
                    "mastery_threshold": "0.8",
                    "concept_type": "textbook_concept",
                    "textbook_id": textbook_id,
                    "section_number": concept['section']
                }
            )
    
    async def _cache_textbook_metadata(
        self,
        textbook_id: str,
        metadata: TextbookMetadata
    ) -> None:
        """Cache textbook metadata"""
        # Redis removed - skip caching
        # await self.redis_cache.set(
        #     f"textbook:{textbook_id}",
        #     json.dumps({
        #         "title": metadata.title,
        #         "subject": metadata.subject,
        #         "authors": metadata.authors,
        #         "processing_date": metadata.processing_date.isoformat(),
        #         "quality_metrics": metadata.quality_metrics,
        #         "statistics": metadata.statistics
        #     }),
        #     ttl=86400  # 24 hours
        # )
    
    def _extract_metadata(self, processing_result) -> TextbookMetadata:
        """Extract metadata from processing result"""
        # This is a simplified version - would be more sophisticated in practice
        return TextbookMetadata(
            textbook_id="",  # Will be set by ingestion
            title="Unknown",
            subject="Unknown",
            authors=[],
            source_file=processing_result.metadata.file_path,
            processing_date=datetime.utcnow(),
            processing_version="1.0",
            quality_metrics=processing_result.quality_metrics.__dict__,
            statistics={
                "chapters": processing_result.metadata.chapters_detected,
                "sections": processing_result.metadata.sections_detected,
                "words": processing_result.metadata.filtered_text_length // 5
            }
        )
    
    async def _get_user_current_concepts(self, user_id: str) -> List[str]:
        """Get user's currently active concepts"""
        results = await self.db_manager.fetch_all(
            """
            SELECT DISTINCT c.name
            FROM user_learning_progress ulp
            JOIN chunks ch ON ch.chunk_id = ulp.chunk_id
            JOIN concepts c ON c.name = ANY(ch.concepts)
            WHERE ulp.user_id = $1
            AND ulp.timestamp > $2
            ORDER BY ulp.timestamp DESC
            LIMIT 10
            """,
            user_id,
            datetime.utcnow() - timedelta(days=7)
        )
        
        return [r["name"] for r in results]
    
    async def _update_concept_mastery(
        self,
        user_id: str,
        chunk_id: str,
        understanding_level: float
    ) -> None:
        """Update concept mastery based on chunk understanding"""
        # Get concepts from chunk
        chunk_data = await self.db_manager.fetch_one(
            "SELECT concepts FROM chunks WHERE chunk_id = $1",
            chunk_id
        )
        
        if not chunk_data or not chunk_data["concepts"]:
            return
        
        for concept in chunk_data["concepts"]:
            # Calculate new mastery score
            current = await self.db_manager.fetch_one(
                """
                SELECT mastery_score, total_chunks, completed_chunks
                FROM user_concept_mastery
                WHERE user_id = $1 AND concept_name = $2
                """,
                user_id, concept
            )
            
            if current:
                # Update existing
                new_completed = current["completed_chunks"] + (1 if understanding_level >= 0.7 else 0)
                new_score = new_completed / current["total_chunks"] if current["total_chunks"] > 0 else 0
                
                await self.db_manager.execute(
                    """
                    UPDATE user_concept_mastery
                    SET mastery_score = $1,
                        completed_chunks = $2,
                        last_updated = $3
                    WHERE user_id = $4 AND concept_name = $5
                    """,
                    new_score, new_completed, datetime.utcnow(),
                    user_id, concept
                )
            else:
                # Create new
                total_chunks = await self._get_concept_chunk_count(concept)
                
                await self.db_manager.execute(
                    """
                    INSERT INTO user_concept_mastery
                    (user_id, concept_name, mastery_score, total_chunks, 
                     completed_chunks, last_updated)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    user_id, concept,
                    1.0 / total_chunks if total_chunks > 0 and understanding_level >= 0.7 else 0,
                    total_chunks,
                    1 if understanding_level >= 0.7 else 0,
                    datetime.utcnow()
                )
    
    async def _get_concept_chunk_count(self, concept: str) -> int:
        """Get total chunks for a concept"""
        result = await self.neo4j_connection.execute_query(
            """
            MATCH (c:Chunk)-[:MENTIONS_CONCEPT]->(concept:Concept {name: $concept})
            RETURN count(c) as count
            """,
            {"concept": concept}
        )
        
        return result[0]["count"] if result else 0
    
    async def _check_prerequisites(self, user_id: str, concept: str) -> bool:
        """Check if user has met prerequisites for a concept"""
        # Get prerequisites
        prereq_result = await self.neo4j_connection.execute_query(
            """
            MATCH (c:Concept {name: $concept})
            MATCH (c)-[:REQUIRES]->(prereq:Concept)
            RETURN collect(prereq.name) as prerequisites
            """,
            {"concept": concept}
        )
        
        if not prereq_result or not prereq_result[0]["prerequisites"]:
            return True  # No prerequisites
        
        prerequisites = prereq_result[0]["prerequisites"]
        
        # Check user's mastery
        mastered = await self.db_manager.fetch_all(
            """
            SELECT concept_name
            FROM user_concept_mastery
            WHERE user_id = $1 
            AND concept_name = ANY($2)
            AND mastery_score >= 0.7
            """,
            user_id, prerequisites
        )
        
        mastered_concepts = {m["concept_name"] for m in mastered}
        return len(mastered_concepts) == len(prerequisites)
    
    async def _log_search(
        self,
        user_id: Optional[str],
        query: str,
        result_count: int
    ) -> None:
        """Log search for analytics"""
        await self.db_manager.execute(
            """
            INSERT INTO search_logs
            (user_id, query, result_count, timestamp)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, query, result_count, datetime.utcnow()
        )