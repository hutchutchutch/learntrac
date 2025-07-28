"""
Vector search endpoints using Neo4j Aura
Implements vector similarity search for learning content
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from ..auth.modern_session_handler import get_current_user, get_current_user_required, AuthenticatedUser
from ..services.neo4j_aura_client import neo4j_aura_client
from ..services.embedding_service import embedding_service
from ..services.llm_service import llm_service
# Redis removed - from ..services.redis_client import redis_cache

logger = logging.getLogger(__name__)

router = APIRouter()


class VectorSearchRequest(BaseModel):
    """Request model for vector search"""
    query: str = Field(..., description="Search query text")
    embedding: Optional[List[float]] = Field(None, description="Pre-computed embedding vector")
    min_score: float = Field(0.65, ge=0.0, le=1.0, description="Minimum similarity score")
    limit: int = Field(20, ge=1, le=100, description="Maximum results to return")
    include_prerequisites: bool = Field(False, description="Include prerequisite chains")
    include_dependents: bool = Field(False, description="Include dependent concepts")


class ChunkCreate(BaseModel):
    """Model for creating a new chunk"""
    content: str = Field(..., description="Content of the chunk")
    subject: Optional[str] = Field(None, description="Subject area")
    concept: Optional[str] = Field(None, description="Concept name")
    has_prerequisite: Optional[List[str]] = Field(None, description="List of prerequisite chunk IDs")
    prerequisite_for: Optional[List[str]] = Field(None, description="List of dependent chunk IDs")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class PrerequisiteRelation(BaseModel):
    """Model for creating prerequisite relationships"""
    from_chunk_id: str = Field(..., description="Chunk that has the prerequisite")
    to_chunk_id: str = Field(..., description="Prerequisite chunk")
    relationship_type: str = Field("STRONG", description="Type of relationship (STRONG, WEAK, OPTIONAL)")


class EnhancedSearchRequest(BaseModel):
    """Request model for enhanced vector search with LLM expansion"""
    query: str = Field(..., description="User's search query")
    generate_sentences: int = Field(5, ge=3, le=10, description="Number of academic sentences to generate")
    min_score: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    limit: int = Field(20, ge=1, le=100, description="Maximum results to return")
    include_prerequisites: bool = Field(True, description="Include prerequisite chains")
    include_generated_context: bool = Field(True, description="Include the generated sentences in response")


@router.post("/search")
async def vector_search(
    request: VectorSearchRequest,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Perform vector similarity search on learning chunks
    
    If embedding is not provided, it will be generated from the query text.
    """
    try:
        # Get or generate embedding
        if request.embedding:
            query_embedding = request.embedding
        else:
            # Generate embedding from query
            query_embedding = await embedding_service.generate_query_embedding(request.query)
            if not query_embedding:
                raise HTTPException(status_code=500, detail="Failed to generate embedding")
        
        # Redis removed - skip cache check
        # cache_key = f"vector_search:{hash(str(query_embedding))}:{request.min_score}:{request.limit}"
        # cached_results = await redis_cache.get_json(cache_key)
        # if cached_results:
        #     return cached_results
        
        # Perform vector search
        results = await neo4j_aura_client.vector_search(
            embedding=query_embedding,
            min_score=request.min_score,
            limit=request.limit
        )
        
        # Enhance results with prerequisites/dependents if requested
        if request.include_prerequisites or request.include_dependents:
            for result in results:
                if request.include_prerequisites:
                    result['prerequisites'] = await neo4j_aura_client.get_prerequisite_chain(
                        result['id'], max_depth=3
                    )
                if request.include_dependents:
                    result['dependents'] = await neo4j_aura_client.get_dependent_concepts(
                        result['id'], max_depth=3
                    )
        
        response = {
            "query": request.query,
            "results": results,
            "count": len(results),
            "min_score_used": request.min_score
        }
        
        # Redis removed - skip caching
        # await redis_cache.set_json(cache_key, response, 3600)
        
        return response
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail="Vector search failed")


@router.post("/chunks", status_code=201)
async def create_chunk(
    chunk: ChunkCreate,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new chunk with embedding
    
    Requires instructor or admin permissions.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Generate embedding for content
        embedding = await embedding_service.generate_concept_embedding({
            'title': chunk.concept or '',
            'description': chunk.content,
            'tags': [chunk.subject] if chunk.subject else []
        })
        
        if not embedding:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
        
        # Generate chunk ID
        import hashlib
        chunk_id = f"chunk_{hashlib.md5(chunk.content.encode()).hexdigest()[:12]}"
        
        # Create chunk in Neo4j
        success = await neo4j_aura_client.create_chunk(
            chunk_id=chunk_id,
            content=chunk.content,
            embedding=embedding,
            subject=chunk.subject,
            concept=chunk.concept,
            has_prerequisite=chunk.has_prerequisite,
            prerequisite_for=chunk.prerequisite_for,
            metadata=chunk.metadata
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create chunk")
        
        # Create prerequisite relationships if specified
        if chunk.has_prerequisite:
            for prereq_id in chunk.has_prerequisite:
                await neo4j_aura_client.create_prerequisite_relationship(
                    chunk_id, prereq_id, "STRONG"
                )
        
        return {
            "chunk_id": chunk_id,
            "message": "Chunk created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chunk: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chunk")


@router.post("/prerequisites")
async def create_prerequisite(
    relation: PrerequisiteRelation,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Create a prerequisite relationship between chunks
    
    Requires instructor or admin permissions.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        success = await neo4j_aura_client.create_prerequisite_relationship(
            relation.from_chunk_id,
            relation.to_chunk_id,
            relation.relationship_type
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create relationship")
        
        return {"message": "Prerequisite relationship created successfully"}
        
    except Exception as e:
        logger.error(f"Failed to create prerequisite: {e}")
        raise HTTPException(status_code=500, detail="Failed to create prerequisite")


@router.get("/chunks/{chunk_id}/prerequisites")
async def get_prerequisites(
    chunk_id: str,
    max_depth: int = 5,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get prerequisite chain for a chunk"""
    try:
        prerequisites = await neo4j_aura_client.get_prerequisite_chain(chunk_id, max_depth)
        
        return {
            "chunk_id": chunk_id,
            "prerequisites": prerequisites,
            "count": len(prerequisites),
            "max_depth": max_depth
        }
        
    except Exception as e:
        logger.error(f"Failed to get prerequisites: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prerequisites")


@router.get("/chunks/{chunk_id}/dependents")
async def get_dependents(
    chunk_id: str,
    max_depth: int = 3,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get concepts that depend on this chunk"""
    try:
        dependents = await neo4j_aura_client.get_dependent_concepts(chunk_id, max_depth)
        
        return {
            "chunk_id": chunk_id,
            "dependents": dependents,
            "count": len(dependents),
            "max_depth": max_depth
        }
        
    except Exception as e:
        logger.error(f"Failed to get dependents: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dependents")


@router.post("/search/bulk")
async def bulk_vector_search(
    queries: List[str] = Body(..., description="List of search queries"),
    min_score: float = Body(0.65, ge=0.0, le=1.0),
    limit_per_query: int = Body(10, ge=1, le=50),
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Perform multiple vector searches in one request
    
    Useful for finding related content for multiple concepts at once.
    """
    try:
        # Generate embeddings for all queries
        embeddings = []
        for query in queries:
            embedding = await embedding_service.generate_query_embedding(query)
            if embedding:
                embeddings.append(embedding)
            else:
                embeddings.append(None)
        
        # Filter out None embeddings
        valid_embeddings = [e for e in embeddings if e is not None]
        
        if not valid_embeddings:
            raise HTTPException(status_code=500, detail="Failed to generate any embeddings")
        
        # Perform bulk search
        results = await neo4j_aura_client.bulk_vector_search(
            embeddings=valid_embeddings,
            min_score=min_score,
            limit_per_query=limit_per_query
        )
        
        # Combine with original queries
        response_data = []
        result_idx = 0
        for i, query in enumerate(queries):
            if embeddings[i] is not None:
                response_data.append({
                    "query": query,
                    "results": results[result_idx] if result_idx < len(results) else [],
                    "count": len(results[result_idx]) if result_idx < len(results) else 0
                })
                result_idx += 1
            else:
                response_data.append({
                    "query": query,
                    "results": [],
                    "count": 0,
                    "error": "Failed to generate embedding"
                })
        
        return {
            "searches": response_data,
            "total_queries": len(queries),
            "successful_queries": len(valid_embeddings)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk vector search failed: {e}")
        raise HTTPException(status_code=500, detail="Bulk vector search failed")


@router.post("/search/enhanced")
async def enhanced_vector_search(
    request: EnhancedSearchRequest,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Perform enhanced vector search with LLM-generated academic context
    
    This endpoint:
    1. Takes the user's input query
    2. Uses LLM to generate 5 academic sentences expanding on the topic
    3. Embeds the combined sentences
    4. Performs vector search using the enhanced embedding
    
    This approach improves search relevance by capturing broader academic context.
    """
    try:
        # Step 1: Generate academic context using LLM
        logger.info(f"Generating academic context for query: {request.query}")
        academic_context = await llm_service.generate_academic_context(
            user_input=request.query,
            num_sentences=request.generate_sentences
        )
        
        if academic_context.get('error'):
            # Fallback to regular search if LLM fails
            logger.warning(f"LLM generation failed, falling back to regular search: {academic_context['error']}")
            query_embedding = await embedding_service.generate_query_embedding(request.query)
        else:
            # Step 2: Generate embedding from the combined academic sentences
            combined_text = academic_context.get('combined_text')
            if not combined_text:
                # Fallback if no sentences were generated
                logger.warning("No sentences generated, using original query")
                query_embedding = await embedding_service.generate_query_embedding(request.query)
            else:
                logger.info(f"Generating embedding for {academic_context.get('sentence_count')} sentences")
                query_embedding = await embedding_service.generate_query_embedding(combined_text)
        
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
        
        # Step 3: Perform vector search with the enhanced embedding
        results = await neo4j_aura_client.vector_search(
            embedding=query_embedding,
            min_score=request.min_score,
            limit=request.limit
        )
        
        # Step 4: Enhance results with prerequisites if requested
        if request.include_prerequisites:
            for result in results:
                result['prerequisites'] = await neo4j_aura_client.get_prerequisite_chain(
                    result['id'], max_depth=3
                )
        
        # Prepare response
        response = {
            "original_query": request.query,
            "search_method": "enhanced" if not academic_context.get('error') else "fallback",
            "results": results,
            "result_count": len(results),
            "min_score_used": request.min_score
        }
        
        # Include generated context if requested and available
        if request.include_generated_context and not academic_context.get('error'):
            response["generated_context"] = {
                "sentences": academic_context.get('sentences', []),
                "sentence_count": academic_context.get('sentence_count', 0),
                "combined_text": academic_context.get('combined_text'),
                "total_length": academic_context.get('total_length', 0)
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced vector search failed: {e}")
        raise HTTPException(status_code=500, detail="Enhanced vector search failed")


@router.post("/search/compare")
async def compare_search_methods(
    query: str = Body(..., description="Search query to test"),
    min_score: float = Body(0.65, ge=0.0, le=1.0),
    limit: int = Body(10, ge=1, le=50),
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Compare regular vs enhanced search results for the same query
    
    Useful for testing and understanding the impact of LLM-enhanced search.
    """
    try:
        # Perform regular search
        regular_embedding = await embedding_service.generate_query_embedding(query)
        regular_results = await neo4j_aura_client.vector_search(
            embedding=regular_embedding,
            min_score=min_score,
            limit=limit
        ) if regular_embedding else []
        
        # Perform enhanced search
        academic_context = await llm_service.generate_academic_context(query, num_sentences=5)
        
        if academic_context.get('combined_text'):
            enhanced_embedding = await embedding_service.generate_query_embedding(
                academic_context['combined_text']
            )
            enhanced_results = await neo4j_aura_client.vector_search(
                embedding=enhanced_embedding,
                min_score=min_score,
                limit=limit
            ) if enhanced_embedding else []
        else:
            enhanced_results = []
        
        # Find unique results in each method
        regular_ids = {r['id'] for r in regular_results}
        enhanced_ids = {r['id'] for r in enhanced_results}
        
        unique_to_regular = regular_ids - enhanced_ids
        unique_to_enhanced = enhanced_ids - regular_ids
        common_results = regular_ids & enhanced_ids
        
        return {
            "query": query,
            "comparison": {
                "regular_search": {
                    "result_count": len(regular_results),
                    "top_scores": [r['score'] for r in regular_results[:5]],
                    "unique_results": len(unique_to_regular)
                },
                "enhanced_search": {
                    "result_count": len(enhanced_results),
                    "top_scores": [r['score'] for r in enhanced_results[:5]],
                    "unique_results": len(unique_to_enhanced),
                    "generated_sentences": academic_context.get('sentences', [])
                },
                "overlap": {
                    "common_results": len(common_results),
                    "percentage": (len(common_results) / max(len(regular_ids), len(enhanced_ids), 1)) * 100
                }
            },
            "regular_results": regular_results[:5],  # Top 5 for brevity
            "enhanced_results": enhanced_results[:5]  # Top 5 for brevity
        }
        
    except Exception as e:
        logger.error(f"Search comparison failed: {e}")
        raise HTTPException(status_code=500, detail="Search comparison failed")


@router.get("/health")
async def neo4j_health(user: AuthenticatedUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Check Neo4j Aura connection health"""
    try:
        health = await neo4j_aura_client.health_check()
        return health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }