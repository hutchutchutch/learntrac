"""
Neo4j Vector Similarity Search for Educational Content

Provides advanced vector search capabilities including:
- Multi-modal similarity search (content, concepts, topics)
- Contextual search with educational filters
- Learning path-aware search
- Search result ranking and re-ranking
- Query expansion and refinement
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np
import asyncio

from .neo4j_connection_manager import Neo4jConnectionManager
from .neo4j_vector_index_manager import Neo4jVectorIndexManager, VectorSearchResult
from .chunk_metadata import ChunkMetadata, ContentType

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """Different search modes for educational content"""
    SEMANTIC = "semantic"  # Pure vector similarity
    CONTEXTUAL = "contextual"  # Consider chapter/section context
    CONCEPTUAL = "conceptual"  # Focus on concept relationships
    LEARNING_PATH = "learning_path"  # Follow learning sequences
    HYBRID = "hybrid"  # Combine multiple modes


class RelevanceType(Enum):
    """Types of relevance for educational search"""
    SEMANTIC_SIMILARITY = "semantic_similarity"
    PREREQUISITE = "prerequisite"
    BUILDS_UPON = "builds_upon"
    RELATED_CONCEPT = "related_concept"
    SAME_TOPIC = "same_topic"
    DIFFICULTY_APPROPRIATE = "difficulty_appropriate"


@dataclass
class SearchFilters:
    """Filters for educational content search"""
    content_types: Optional[List[ContentType]] = None
    difficulty_range: Optional[Tuple[float, float]] = None
    textbook_ids: Optional[List[str]] = None
    chapter_ids: Optional[List[str]] = None
    concepts: Optional[List[str]] = None
    exclude_chunk_ids: Optional[Set[str]] = None
    min_quality_score: float = 0.7
    require_prerequisites: bool = False
    

@dataclass
class SearchContext:
    """Context for search operations"""
    user_level: Optional[str] = None  # beginner/intermediate/advanced
    current_chunk_id: Optional[str] = None
    current_concepts: List[str] = field(default_factory=list)
    learning_history: List[str] = field(default_factory=list)
    search_intent: Optional[str] = None  # explanation/example/practice/theory


@dataclass
class SearchResult:
    """Enhanced search result with educational metadata"""
    chunk_id: str
    score: float
    text: str
    chunk_metadata: ChunkMetadata
    
    # Educational relevance
    relevance_types: List[RelevanceType]
    relevance_scores: Dict[RelevanceType, float]
    
    # Context
    textbook_title: str
    chapter_title: str
    section_title: Optional[str]
    
    # Relationships
    concepts: List[str]
    prerequisites: List[str]
    
    # Additional metadata
    explanation: str  # Why this result is relevant
    difficulty_match: float  # How well difficulty matches user level
    

@dataclass
class SearchResults:
    """Container for search results with metadata"""
    query: str
    query_embedding: List[float]
    mode: SearchMode
    results: List[SearchResult]
    total_found: int
    search_time: float
    filters_applied: SearchFilters
    context: Optional[SearchContext]
    suggestions: List[str]  # Query refinement suggestions
    related_concepts: List[str]  # Discovered related concepts


class Neo4jVectorSearch:
    """
    Advanced vector similarity search for educational content.
    
    Features:
    - Multi-modal search strategies
    - Educational context awareness
    - Learning path integration
    - Result re-ranking based on pedagogy
    - Query expansion and refinement
    """
    
    def __init__(
        self,
        connection_manager: Neo4jConnectionManager,
        index_manager: Neo4jVectorIndexManager,
        embedding_dimension: int = 768
    ):
        """
        Initialize vector search engine.
        
        Args:
            connection_manager: Neo4j connection manager
            index_manager: Vector index manager
            embedding_dimension: Dimension of embeddings
        """
        self.connection = connection_manager
        self.index_manager = index_manager
        self.embedding_dimension = embedding_dimension
        
    async def search(
        self,
        query_embedding: List[float],
        mode: SearchMode = SearchMode.HYBRID,
        filters: Optional[SearchFilters] = None,
        context: Optional[SearchContext] = None,
        limit: int = 20,
        expand_query: bool = True
    ) -> SearchResults:
        """
        Perform vector similarity search with educational enhancements.
        
        Args:
            query_embedding: Query vector embedding
            mode: Search mode to use
            filters: Search filters
            context: Search context
            limit: Maximum results to return
            expand_query: Whether to expand query with related concepts
            
        Returns:
            Search results with educational metadata
        """
        start_time = datetime.utcnow()
        filters = filters or SearchFilters()
        
        try:
            # Validate embedding dimension
            if len(query_embedding) != self.embedding_dimension:
                raise ValueError(
                    f"Query embedding dimension {len(query_embedding)} "
                    f"doesn't match expected {self.embedding_dimension}"
                )
            
            # Perform search based on mode
            if mode == SearchMode.SEMANTIC:
                raw_results = await self._semantic_search(
                    query_embedding, filters, limit * 2  # Get more for filtering
                )
            elif mode == SearchMode.CONTEXTUAL:
                raw_results = await self._contextual_search(
                    query_embedding, filters, context, limit * 2
                )
            elif mode == SearchMode.CONCEPTUAL:
                raw_results = await self._conceptual_search(
                    query_embedding, filters, context, limit * 2
                )
            elif mode == SearchMode.LEARNING_PATH:
                raw_results = await self._learning_path_search(
                    query_embedding, filters, context, limit * 2
                )
            else:  # HYBRID
                raw_results = await self._hybrid_search(
                    query_embedding, filters, context, limit * 3
                )
            
            # Enhance results with educational metadata
            enhanced_results = await self._enhance_results(
                raw_results, query_embedding, context
            )
            
            # Re-rank based on educational relevance
            if context:
                enhanced_results = self._rerank_by_education(
                    enhanced_results, context
                )
            
            # Apply final limit
            final_results = enhanced_results[:limit]
            
            # Generate suggestions
            suggestions = self._generate_suggestions(
                final_results, filters, context
            )
            
            # Extract related concepts
            related_concepts = self._extract_related_concepts(final_results)
            
            # Calculate search time
            search_time = (datetime.utcnow() - start_time).total_seconds()
            
            return SearchResults(
                query="",  # Would be set by caller
                query_embedding=query_embedding,
                mode=mode,
                results=final_results,
                total_found=len(raw_results),
                search_time=search_time,
                filters_applied=filters,
                context=context,
                suggestions=suggestions,
                related_concepts=related_concepts
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def _semantic_search(
        self,
        query_embedding: List[float],
        filters: SearchFilters,
        limit: int
    ) -> List[VectorSearchResult]:
        """Perform pure semantic similarity search"""
        # Build property filters
        property_filters = self._build_property_filters(filters)
        
        # Perform vector search
        results = await self.index_manager.vector_search(
            index_name="chunkEmbedding",
            query_vector=query_embedding,
            limit=limit,
            min_score=0.5,  # Minimum cosine similarity
            filters=property_filters
        )
        
        return results
    
    async def _contextual_search(
        self,
        query_embedding: List[float],
        filters: SearchFilters,
        context: Optional[SearchContext],
        limit: int
    ) -> List[VectorSearchResult]:
        """Search considering document context"""
        # Get base results
        base_results = await self._semantic_search(
            query_embedding, filters, limit
        )
        
        if not context or not context.current_chunk_id:
            return base_results
        
        # Get context information
        context_query = """
            MATCH (current:Chunk {chunk_id: $current_id})
            OPTIONAL MATCH (current)-[:BELONGS_TO_SECTION]->(section:Section)
            OPTIONAL MATCH (current)-[:BELONGS_TO_CHAPTER]->(chapter:Chapter)
            RETURN section.section_id as section_id,
                   chapter.chapter_id as chapter_id
        """
        
        context_results = await self.connection.execute_query(
            context_query,
            {"current_id": context.current_chunk_id}
        )
        
        if context_results:
            section_id = context_results[0].get("section_id")
            chapter_id = context_results[0].get("chapter_id")
            
            # Boost results from same section/chapter
            boosted_results = []
            for result in base_results:
                boost = 1.0
                node_props = result.node_properties
                
                if section_id and node_props.get("parent_section_id") == section_id:
                    boost = 1.3  # 30% boost for same section
                elif chapter_id and node_props.get("parent_chapter_id") == chapter_id:
                    boost = 1.15  # 15% boost for same chapter
                
                # Apply boost to score
                boosted_result = VectorSearchResult(
                    node_id=result.node_id,
                    score=min(1.0, result.score * boost),
                    node_properties=result.node_properties,
                    metadata=result.metadata
                )
                boosted_results.append(boosted_result)
            
            # Re-sort by boosted scores
            boosted_results.sort(key=lambda x: x.score, reverse=True)
            return boosted_results
        
        return base_results
    
    async def _conceptual_search(
        self,
        query_embedding: List[float],
        filters: SearchFilters,
        context: Optional[SearchContext],
        limit: int
    ) -> List[VectorSearchResult]:
        """Search based on concept relationships"""
        # Get base semantic results
        base_results = await self._semantic_search(
            query_embedding, filters, limit // 2
        )
        
        # Extract concepts from top results
        concepts = set()
        for result in base_results[:5]:
            if "concepts" in result.node_properties:
                concepts.update(result.node_properties["concepts"])
        
        if not concepts:
            return base_results
        
        # Find chunks with related concepts
        concept_query = """
            MATCH (c:Chunk)-[:MENTIONS_CONCEPT]->(concept:Concept)
            WHERE concept.name IN $concepts
            AND c.chunk_id NOT IN $exclude_ids
            WITH c, count(distinct concept) as concept_matches
            WHERE concept_matches >= 2
            RETURN c.chunk_id as chunk_id,
                   c.embedding as embedding,
                   c as node,
                   concept_matches
            ORDER BY concept_matches DESC
            LIMIT $limit
        """
        
        exclude_ids = [r.node_id for r in base_results]
        exclude_ids.extend(list(filters.exclude_chunk_ids or []))
        
        concept_results = await self.connection.execute_query(
            concept_query,
            {
                "concepts": list(concepts),
                "exclude_ids": exclude_ids,
                "limit": limit // 2
            }
        )
        
        # Calculate similarity scores for concept-based results
        concept_search_results = []
        for record in concept_results:
            if record["embedding"]:
                similarity = self._cosine_similarity(
                    query_embedding,
                    record["embedding"]
                )
                
                # Boost score based on concept matches
                boost = 1 + (0.1 * record["concept_matches"])
                final_score = min(1.0, similarity * boost)
                
                concept_search_results.append(VectorSearchResult(
                    node_id=record["chunk_id"],
                    score=final_score,
                    node_properties=dict(record["node"]),
                    metadata={"concept_matches": record["concept_matches"]}
                ))
        
        # Merge results
        all_results = base_results + concept_search_results
        
        # Remove duplicates and sort
        seen = set()
        unique_results = []
        for result in sorted(all_results, key=lambda x: x.score, reverse=True):
            if result.node_id not in seen:
                seen.add(result.node_id)
                unique_results.append(result)
        
        return unique_results[:limit]
    
    async def _learning_path_search(
        self,
        query_embedding: List[float],
        filters: SearchFilters,
        context: Optional[SearchContext],
        limit: int
    ) -> List[VectorSearchResult]:
        """Search following learning path sequences"""
        # Get base results
        base_results = await self._semantic_search(
            query_embedding, filters, limit // 2
        )
        
        if not context or not context.learning_history:
            return base_results
        
        # Find chunks that follow learned content
        path_query = """
            MATCH (learned:Chunk)
            WHERE learned.chunk_id IN $history
            MATCH (learned)-[:NEXT*1..3]->(next:Chunk)
            WHERE next.chunk_id NOT IN $exclude_ids
            WITH next, count(distinct learned) as precedent_count
            RETURN next.chunk_id as chunk_id,
                   next.embedding as embedding,
                   next as node,
                   precedent_count
            ORDER BY precedent_count DESC
            LIMIT $limit
        """
        
        exclude_ids = [r.node_id for r in base_results]
        exclude_ids.extend(list(filters.exclude_chunk_ids or []))
        exclude_ids.extend(context.learning_history)
        
        path_results = await self.connection.execute_query(
            path_query,
            {
                "history": context.learning_history[-10:],  # Last 10 items
                "exclude_ids": exclude_ids,
                "limit": limit // 2
            }
        )
        
        # Calculate scores for path-based results
        path_search_results = []
        for record in path_results:
            if record["embedding"]:
                similarity = self._cosine_similarity(
                    query_embedding,
                    record["embedding"]
                )
                
                # Boost based on learning path
                boost = 1.2  # Base boost for being in path
                final_score = min(1.0, similarity * boost)
                
                path_search_results.append(VectorSearchResult(
                    node_id=record["chunk_id"],
                    score=final_score,
                    node_properties=dict(record["node"]),
                    metadata={"in_learning_path": True}
                ))
        
        # Merge and deduplicate
        all_results = base_results + path_search_results
        seen = set()
        unique_results = []
        for result in sorted(all_results, key=lambda x: x.score, reverse=True):
            if result.node_id not in seen:
                seen.add(result.node_id)
                unique_results.append(result)
        
        return unique_results[:limit]
    
    async def _hybrid_search(
        self,
        query_embedding: List[float],
        filters: SearchFilters,
        context: Optional[SearchContext],
        limit: int
    ) -> List[VectorSearchResult]:
        """Combine multiple search strategies"""
        # Run searches in parallel
        search_tasks = [
            self._semantic_search(query_embedding, filters, limit),
            self._contextual_search(query_embedding, filters, context, limit),
            self._conceptual_search(query_embedding, filters, context, limit)
        ]
        
        if context and context.learning_history:
            search_tasks.append(
                self._learning_path_search(query_embedding, filters, context, limit)
            )
        
        all_results = await asyncio.gather(*search_tasks)
        
        # Merge results with weighted scoring
        merged_results = {}
        weights = [0.4, 0.2, 0.3, 0.1]  # Weights for each search type
        
        for i, results in enumerate(all_results):
            weight = weights[i] if i < len(weights) else 0.1
            
            for result in results:
                if result.node_id in merged_results:
                    # Average the scores with weights
                    existing = merged_results[result.node_id]
                    total_weight = existing["weight"] + weight
                    new_score = (
                        existing["score"] * existing["weight"] + 
                        result.score * weight
                    ) / total_weight
                    
                    merged_results[result.node_id] = {
                        "result": result,
                        "score": new_score,
                        "weight": total_weight
                    }
                else:
                    merged_results[result.node_id] = {
                        "result": result,
                        "score": result.score,
                        "weight": weight
                    }
        
        # Extract and sort final results
        final_results = []
        for node_id, data in merged_results.items():
            result = data["result"]
            final_results.append(VectorSearchResult(
                node_id=result.node_id,
                score=data["score"],
                node_properties=result.node_properties,
                metadata=result.metadata
            ))
        
        final_results.sort(key=lambda x: x.score, reverse=True)
        return final_results[:limit]
    
    async def _enhance_results(
        self,
        raw_results: List[VectorSearchResult],
        query_embedding: List[float],
        context: Optional[SearchContext]
    ) -> List[SearchResult]:
        """Enhance raw results with educational metadata"""
        if not raw_results:
            return []
        
        # Batch fetch additional data
        chunk_ids = [r.node_id for r in raw_results]
        
        enhancement_query = """
            UNWIND $chunk_ids as chunk_id
            MATCH (c:Chunk {chunk_id: chunk_id})
            OPTIONAL MATCH (c)-[:BELONGS_TO_TEXTBOOK]->(t:Textbook)
            OPTIONAL MATCH (c)-[:BELONGS_TO_CHAPTER]->(ch:Chapter)
            OPTIONAL MATCH (c)-[:BELONGS_TO_SECTION]->(s:Section)
            OPTIONAL MATCH (c)-[:MENTIONS_CONCEPT]->(concept:Concept)
            OPTIONAL MATCH (c)-[:REQUIRES_CONCEPT]->(prereq:Concept)
            RETURN c.chunk_id as chunk_id,
                   c.text as text,
                   c.content_type as content_type,
                   c.difficulty_score as difficulty,
                   c.concepts as chunk_concepts,
                   c.start_position as start_position,
                   c.end_position as end_position,
                   c.confidence_score as confidence_score,
                   t.title as textbook_title,
                   ch.title as chapter_title,
                   s.title as section_title,
                   collect(distinct concept.name) as concepts,
                   collect(distinct prereq.name) as prerequisites
        """
        
        enhancements = await self.connection.execute_query(
            enhancement_query,
            {"chunk_ids": chunk_ids}
        )
        
        # Create enhancement lookup
        enhancement_map = {e["chunk_id"]: e for e in enhancements}
        
        # Build enhanced results
        enhanced_results = []
        for raw_result in raw_results:
            enhancement = enhancement_map.get(raw_result.node_id, {})
            
            # Determine relevance types
            relevance_types, relevance_scores = self._determine_relevance(
                raw_result, enhancement, context
            )
            
            # Calculate difficulty match
            difficulty_match = self._calculate_difficulty_match(
                enhancement.get("difficulty", 0.5),
                context
            )
            
            # Generate explanation
            explanation = self._generate_explanation(
                raw_result.score,
                relevance_types,
                enhancement
            )
            
            # Create chunk metadata
            chunk_metadata = ChunkMetadata(
                chunk_id=raw_result.node_id,
                content_type=ContentType(enhancement.get("content_type", "text")),
                start_position=enhancement.get("start_position", 0),
                end_position=enhancement.get("end_position", 0),
                confidence_score=enhancement.get("confidence_score", 0.8)
            )
            
            enhanced_results.append(SearchResult(
                chunk_id=raw_result.node_id,
                score=raw_result.score,
                text=enhancement.get("text", ""),
                chunk_metadata=chunk_metadata,
                relevance_types=relevance_types,
                relevance_scores=relevance_scores,
                textbook_title=enhancement.get("textbook_title", "Unknown"),
                chapter_title=enhancement.get("chapter_title", "Unknown"),
                section_title=enhancement.get("section_title"),
                concepts=enhancement.get("concepts", []),
                prerequisites=enhancement.get("prerequisites", []),
                explanation=explanation,
                difficulty_match=difficulty_match
            ))
        
        return enhanced_results
    
    def _rerank_by_education(
        self,
        results: List[SearchResult],
        context: SearchContext
    ) -> List[SearchResult]:
        """Re-rank results based on educational criteria"""
        for result in results:
            # Calculate educational score components
            prereq_score = self._calculate_prerequisite_score(
                result.prerequisites,
                context.learning_history
            )
            
            difficulty_score = result.difficulty_match
            
            intent_score = self._calculate_intent_match(
                result,
                context.search_intent
            )
            
            # Combine scores
            education_boost = (
                prereq_score * 0.3 +
                difficulty_score * 0.3 +
                intent_score * 0.4
            )
            
            # Apply boost
            result.score = min(1.0, result.score * (1 + education_boost * 0.5))
        
        # Re-sort by new scores
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def _build_property_filters(
        self,
        filters: SearchFilters
    ) -> Dict[str, Any]:
        """Build property filters for Cypher queries"""
        property_filters = {}
        
        if filters.textbook_ids:
            property_filters["textbook_id"] = filters.textbook_ids
        
        if filters.chapter_ids:
            property_filters["parent_chapter_id"] = filters.chapter_ids
        
        if filters.min_quality_score:
            property_filters["quality_score_min"] = filters.min_quality_score
        
        return property_filters
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def _determine_relevance(
        self,
        raw_result: VectorSearchResult,
        enhancement: Dict[str, Any],
        context: Optional[SearchContext]
    ) -> Tuple[List[RelevanceType], Dict[RelevanceType, float]]:
        """Determine relevance types and scores"""
        relevance_types = []
        relevance_scores = {}
        
        # Always has semantic similarity
        relevance_types.append(RelevanceType.SEMANTIC_SIMILARITY)
        relevance_scores[RelevanceType.SEMANTIC_SIMILARITY] = raw_result.score
        
        # Check for concept overlap
        if context and context.current_concepts:
            concepts = set(enhancement.get("concepts", []))
            current = set(context.current_concepts)
            
            if concepts & current:
                relevance_types.append(RelevanceType.RELATED_CONCEPT)
                overlap_ratio = len(concepts & current) / len(current)
                relevance_scores[RelevanceType.RELATED_CONCEPT] = overlap_ratio
        
        # Check prerequisites
        if enhancement.get("prerequisites"):
            relevance_types.append(RelevanceType.PREREQUISITE)
            relevance_scores[RelevanceType.PREREQUISITE] = 0.8
        
        return relevance_types, relevance_scores
    
    def _calculate_difficulty_match(
        self,
        chunk_difficulty: float,
        context: Optional[SearchContext]
    ) -> float:
        """Calculate how well difficulty matches user level"""
        if not context or not context.user_level:
            return 0.5  # Neutral match
        
        # Map user levels to difficulty ranges
        level_ranges = {
            "beginner": (0.0, 0.4),
            "intermediate": (0.3, 0.7),
            "advanced": (0.6, 1.0)
        }
        
        min_diff, max_diff = level_ranges.get(
            context.user_level,
            (0.0, 1.0)
        )
        
        if min_diff <= chunk_difficulty <= max_diff:
            # Perfect match in the middle of range
            range_middle = (min_diff + max_diff) / 2
            distance = abs(chunk_difficulty - range_middle)
            max_distance = (max_diff - min_diff) / 2
            return 1.0 - (distance / max_distance)
        else:
            # Outside range - calculate penalty
            if chunk_difficulty < min_diff:
                return max(0.0, 1.0 - (min_diff - chunk_difficulty) * 2)
            else:
                return max(0.0, 1.0 - (chunk_difficulty - max_diff) * 2)
    
    def _calculate_prerequisite_score(
        self,
        prerequisites: List[str],
        learning_history: List[str]
    ) -> float:
        """Calculate prerequisite fulfillment score"""
        if not prerequisites:
            return 1.0  # No prerequisites needed
        
        if not learning_history:
            return 0.0  # Has prerequisites but no history
        
        # Check how many prerequisites are in learning history
        # (This is simplified - in practice, would check concept coverage)
        fulfilled = sum(1 for p in prerequisites if p in learning_history)
        return fulfilled / len(prerequisites)
    
    def _calculate_intent_match(
        self,
        result: SearchResult,
        intent: Optional[str]
    ) -> float:
        """Calculate how well result matches search intent"""
        if not intent:
            return 0.5  # Neutral
        
        content_type = result.chunk_metadata.content_type
        
        intent_type_map = {
            "explanation": [ContentType.DEFINITION, ContentType.THEORY],
            "example": [ContentType.EXAMPLE, ContentType.CODE],
            "practice": [ContentType.EXERCISE, ContentType.PROBLEM],
            "theory": [ContentType.THEORY, ContentType.MATHEMATICAL]
        }
        
        preferred_types = intent_type_map.get(intent, [])
        
        if content_type in preferred_types:
            return 1.0
        else:
            return 0.3  # Partial match
    
    def _generate_explanation(
        self,
        score: float,
        relevance_types: List[RelevanceType],
        enhancement: Dict[str, Any]
    ) -> str:
        """Generate explanation for why result is relevant"""
        explanations = []
        
        if score > 0.9:
            explanations.append("Very high semantic similarity")
        elif score > 0.8:
            explanations.append("High semantic similarity")
        elif score > 0.7:
            explanations.append("Good semantic similarity")
        
        if RelevanceType.RELATED_CONCEPT in relevance_types:
            concepts = enhancement.get("concepts", [])[:3]
            if concepts:
                explanations.append(
                    f"Related concepts: {', '.join(concepts)}"
                )
        
        if RelevanceType.PREREQUISITE in relevance_types:
            explanations.append("Contains prerequisite information")
        
        if RelevanceType.SAME_TOPIC in relevance_types:
            explanations.append("From the same topic area")
        
        return "; ".join(explanations) if explanations else "Relevant content"
    
    def _generate_suggestions(
        self,
        results: List[SearchResult],
        filters: SearchFilters,
        context: Optional[SearchContext]
    ) -> List[str]:
        """Generate query refinement suggestions"""
        suggestions = []
        
        if not results:
            suggestions.append("Try broadening your search criteria")
            if filters.difficulty_range:
                suggestions.append("Consider removing difficulty filters")
        
        elif len(results) < 5:
            suggestions.append("Try related concepts for more results")
        
        # Suggest concepts from top results
        top_concepts = set()
        for result in results[:5]:
            top_concepts.update(result.concepts[:2])
        
        if top_concepts:
            suggestions.append(
                f"Related concepts: {', '.join(list(top_concepts)[:3])}"
            )
        
        # Suggest difficulty adjustment
        if context and context.user_level and results:
            avg_difficulty = np.mean([
                r.chunk_metadata.difficulty
                for r in results[:10]
                if hasattr(r.chunk_metadata, 'difficulty')
            ])
            
            if context.user_level == "beginner" and avg_difficulty > 0.7:
                suggestions.append("Consider searching for introductory content")
            elif context.user_level == "advanced" and avg_difficulty < 0.3:
                suggestions.append("Consider searching for advanced topics")
        
        return suggestions
    
    def _extract_related_concepts(
        self,
        results: List[SearchResult]
    ) -> List[str]:
        """Extract frequently occurring concepts from results"""
        concept_counts = {}
        
        for result in results:
            for concept in result.concepts:
                concept_counts[concept] = concept_counts.get(concept, 0) + 1
        
        # Sort by frequency
        sorted_concepts = sorted(
            concept_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return top concepts
        return [concept for concept, _ in sorted_concepts[:10]]
    
    async def find_similar_chunks(
        self,
        chunk_id: str,
        limit: int = 10,
        min_similarity: float = 0.7
    ) -> List[SearchResult]:
        """
        Find chunks similar to a given chunk.
        
        Args:
            chunk_id: ID of the source chunk
            limit: Maximum results
            min_similarity: Minimum similarity threshold
            
        Returns:
            Similar chunks
        """
        # Get source chunk embedding
        query = """
            MATCH (c:Chunk {chunk_id: $chunk_id})
            RETURN c.embedding as embedding
        """
        
        results = await self.connection.execute_query(
            query,
            {"chunk_id": chunk_id}
        )
        
        if not results or not results[0]["embedding"]:
            return []
        
        source_embedding = results[0]["embedding"]
        
        # Search for similar chunks
        filters = SearchFilters(
            exclude_chunk_ids={chunk_id},
            min_quality_score=min_similarity
        )
        
        search_results = await self.search(
            source_embedding,
            mode=SearchMode.SEMANTIC,
            filters=filters,
            limit=limit
        )
        
        return search_results.results
    
    async def find_prerequisites(
        self,
        chunk_id: str,
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find prerequisite content for a chunk.
        
        Args:
            chunk_id: Target chunk ID
            max_depth: Maximum prerequisite depth
            
        Returns:
            List of prerequisite chunks with paths
        """
        query = """
            MATCH (target:Chunk {chunk_id: $chunk_id})
            OPTIONAL MATCH (target)-[:REQUIRES_CONCEPT]->(concept:Concept)
            OPTIONAL MATCH path = (prereq:Chunk)-[:INTRODUCES_CONCEPT|EXPLAINS_CONCEPT*1..%d]->(concept)
            WHERE prereq.chunk_id <> $chunk_id
            WITH prereq, concept, path,
                 length(path) as path_length
            ORDER BY path_length ASC
            RETURN DISTINCT prereq.chunk_id as chunk_id,
                   prereq.text as text,
                   collect(distinct concept.name) as concepts,
                   min(path_length) as distance
            LIMIT 20
        """ % max_depth
        
        results = await self.connection.execute_query(
            query,
            {"chunk_id": chunk_id}
        )
        
        return results