"""
Ticket Creation API Router
Provides endpoints for creating learning tickets from chunks with prerequisites
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
import logging
import uuid

from ..auth.jwt_handler import get_current_user, AuthenticatedUser
from ..services.ticket_service import ticket_service, TicketCreationError

logger = logging.getLogger(__name__)

router = APIRouter()


class ChunkInput(BaseModel):
    """Input model for learning chunks"""
    id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., min_length=1, max_length=10000, description="Learning content")
    concept: str = Field(..., min_length=1, max_length=200, description="Concept name")
    subject: str = Field(..., min_length=1, max_length=100, description="Subject area")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    has_prerequisite: Optional[List[str]] = Field(None, description="List of prerequisite concept names")
    prerequisite_for: Optional[List[str]] = Field(None, description="List of dependent concept names")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional chunk metadata")


class LearningPathRequest(BaseModel):
    """Request model for creating learning paths"""
    query: str = Field(..., min_length=1, max_length=1000, description="Learning query text")
    chunks: List[ChunkInput] = Field(..., min_items=1, max_items=50, description="Learning chunks")
    path_title: Optional[str] = Field(None, max_length=200, description="Custom path title")
    difficulty_level: str = Field("intermediate", description="Difficulty level")
    
    @validator('difficulty_level')
    def validate_difficulty(cls, v):
        allowed = ['beginner', 'intermediate', 'advanced']
        if v not in allowed:
            raise ValueError(f'difficulty_level must be one of: {allowed}')
        return v


class ProgressUpdateRequest(BaseModel):
    """Request model for updating ticket progress"""
    status: str = Field(..., description="Progress status")
    mastery_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Mastery score")
    time_spent_minutes: Optional[int] = Field(None, ge=0, description="Time spent in minutes")
    notes: Optional[str] = Field(None, max_length=1000, description="Progress notes")
    
    @validator('status')
    def validate_status(cls, v):
        allowed = ['not_started', 'in_progress', 'completed', 'mastered']
        if v not in allowed:
            raise ValueError(f'status must be one of: {allowed}')
        return v


class LearningPathResponse(BaseModel):
    """Response model for learning path creation"""
    path_id: str
    message: str
    ticket_count: int
    prerequisite_count: int


@router.post("/learning-paths", status_code=201)
async def create_learning_path(
    request: LearningPathRequest,
    user: AuthenticatedUser = Depends(get_current_user)
) -> LearningPathResponse:
    """
    Create a learning path with tickets from chunks
    
    Creates Trac tickets for each chunk with:
    - Generated questions using LLM service
    - Learning metadata and custom fields
    - Prerequisite relationships between concepts
    - Progress tracking integration
    
    Requires learning instruction permissions.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Convert Pydantic models to dictionaries
        chunks_data = [chunk.dict() for chunk in request.chunks]
        
        # Create learning path
        path_id = await ticket_service.create_learning_path(
            user_id=user.sub,
            query=request.query,
            chunks=chunks_data,
            path_title=request.path_title,
            difficulty_level=request.difficulty_level
        )
        
        # Count prerequisites for response
        prerequisite_count = sum(
            len(chunk.has_prerequisite or []) 
            for chunk in request.chunks
        )
        
        logger.info(f"Created learning path {path_id} with {len(request.chunks)} tickets for user {user.sub}")
        
        return LearningPathResponse(
            path_id=str(path_id),
            message="Learning path created successfully",
            ticket_count=len(request.chunks),
            prerequisite_count=prerequisite_count
        )
        
    except TicketCreationError as e:
        logger.error(f"Ticket creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating learning path: {e}")
        raise HTTPException(status_code=500, detail="Failed to create learning path")


@router.get("/learning-paths/{path_id}/tickets")
async def get_learning_path_tickets(
    path_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get all tickets for a learning path
    
    Returns tickets with their metadata, custom fields, and prerequisites.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_READ", "LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Validate UUID
        try:
            path_uuid = uuid.UUID(path_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid path ID format")
        
        # Get tickets
        tickets = await ticket_service.get_learning_path_tickets(path_uuid, user.sub)
        
        return {
            "path_id": path_id,
            "ticket_count": len(tickets),
            "tickets": tickets
        }
        
    except TicketCreationError as e:
        logger.error(f"Failed to get learning path tickets: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting learning path tickets: {e}")
        raise HTTPException(status_code=500, detail="Failed to get learning path tickets")


@router.put("/tickets/{ticket_id}/progress")
async def update_ticket_progress(
    ticket_id: int,
    request: ProgressUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Update progress for a learning ticket
    
    Updates both the learning progress tracking and Trac ticket status.
    Students can update their own progress.
    """
    # Check permissions - students can update their own progress
    if not user.has_any_permission(["LEARNING_READ", "LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        await ticket_service.update_ticket_progress(
            ticket_id=ticket_id,
            user_id=user.sub,
            status=request.status,
            mastery_score=request.mastery_score,
            time_spent_minutes=request.time_spent_minutes,
            notes=request.notes
        )
        
        logger.info(f"Updated progress for ticket {ticket_id}, user {user.sub}, status {request.status}")
        
        return {
            "message": "Progress updated successfully",
            "ticket_id": str(ticket_id),
            "status": request.status
        }
        
    except TicketCreationError as e:
        logger.error(f"Failed to update ticket progress: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating ticket progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to update progress")


@router.post("/learning-paths/from-vector-search")
async def create_learning_path_from_search(
    query: str = Body(..., embed=True, description="Search query"),
    min_score: float = Body(0.65, embed=True, ge=0.0, le=1.0, description="Minimum similarity score"),
    max_chunks: int = Body(20, embed=True, ge=1, le=50, description="Maximum chunks to include"),
    path_title: Optional[str] = Body(None, embed=True, description="Custom path title"),
    difficulty_level: str = Body("intermediate", embed=True, description="Difficulty level"),
    user: AuthenticatedUser = Depends(get_current_user)
) -> LearningPathResponse:
    """
    Create learning path from vector search results
    
    Performs vector search on Neo4j chunks and creates a learning path
    with tickets for the most relevant results.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        from ..services.neo4j_aura_client import neo4j_aura_client
        from ..services.embedding_service import embedding_service
        
        # Generate embedding for query
        query_embedding = await embedding_service.generate_query_embedding(query)
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        # Perform vector search
        search_results = await neo4j_aura_client.vector_search(
            embedding=query_embedding,
            min_score=min_score,
            limit=max_chunks
        )
        
        if not search_results:
            raise HTTPException(status_code=404, detail="No relevant chunks found for query")
        
        # Transform search results to chunks
        chunks_data = []
        for result in search_results:
            chunk_data = {
                'id': result['id'],
                'content': result['content'],
                'concept': result.get('concept', 'Unknown Concept'),
                'subject': result.get('subject', 'General'),
                'score': result['score'],
                'has_prerequisite': result.get('has_prerequisite'),
                'prerequisite_for': result.get('prerequisite_for'),
                'metadata': {
                    'source': 'vector_search',
                    'search_score': result['score']
                }
            }
            chunks_data.append(chunk_data)
        
        # Create learning path
        path_id = await ticket_service.create_learning_path(
            user_id=user.sub,
            query=query,
            chunks=chunks_data,
            path_title=path_title or f"Search: {query}",
            difficulty_level=difficulty_level
        )
        
        # Count prerequisites
        prerequisite_count = sum(
            len(chunk.get('has_prerequisite', [])) 
            for chunk in chunks_data
        )
        
        logger.info(f"Created learning path {path_id} from vector search with {len(chunks_data)} chunks")
        
        return LearningPathResponse(
            path_id=str(path_id),
            message=f"Learning path created from {len(chunks_data)} search results",
            ticket_count=len(chunks_data),
            prerequisite_count=prerequisite_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create learning path from search: {e}")
        raise HTTPException(status_code=500, detail="Failed to create learning path from search")


@router.get("/tickets/{ticket_id}/details")
async def get_ticket_details(
    ticket_id: int,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed information for a learning ticket
    
    Includes Trac ticket data, custom fields, learning metadata, and progress.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_READ", "LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        async with ticket_service.db_pool.acquire() as conn:
            # Get ticket with all related data
            ticket_data = await conn.fetchrow("""
                SELECT 
                    t.id, t.summary, t.description, t.status, t.milestone,
                    t.time as created_time, t.changetime as updated_time,
                    t.owner, t.reporter, t.keywords,
                    cm.concept_id, cm.path_id, cm.sequence_order,
                    cm.concept_type, cm.difficulty_score, cm.mastery_threshold,
                    cm.estimated_minutes, cm.tags, cm.resources,
                    p.status as progress_status, p.mastery_score,
                    p.time_spent_minutes, p.attempt_count,
                    p.last_accessed, p.completed_at, p.notes as progress_notes,
                    -- Custom fields as JSON object
                    json_object_agg(
                        tc.name, tc.value
                    ) FILTER (WHERE tc.name IS NOT NULL) as custom_fields
                FROM ticket t
                LEFT JOIN learning.concept_metadata cm ON t.id = cm.ticket_id
                LEFT JOIN learning.progress p ON cm.concept_id = p.concept_id AND p.student_id = $2
                LEFT JOIN ticket_custom tc ON t.id = tc.ticket
                WHERE t.id = $1
                GROUP BY 
                    t.id, t.summary, t.description, t.status, t.milestone,
                    t.time, t.changetime, t.owner, t.reporter, t.keywords,
                    cm.concept_id, cm.path_id, cm.sequence_order,
                    cm.concept_type, cm.difficulty_score, cm.mastery_threshold,
                    cm.estimated_minutes, cm.tags, cm.resources,
                    p.status, p.mastery_score, p.time_spent_minutes,
                    p.attempt_count, p.last_accessed, p.completed_at, p.notes
            """, ticket_id, user.sub)
            
            if not ticket_data:
                raise HTTPException(status_code=404, detail="Ticket not found")
            
            result = dict(ticket_data)
            
            # Get prerequisites if concept exists
            if result.get('concept_id'):
                prerequisites = await conn.fetch("""
                    SELECT 
                        prereq_cm.ticket_id as prereq_ticket_id,
                        prereq_t.summary as prereq_summary,
                        p.requirement_type
                    FROM learning.prerequisites p
                    JOIN learning.concept_metadata prereq_cm ON p.prereq_concept_id = prereq_cm.concept_id
                    JOIN ticket prereq_t ON prereq_cm.ticket_id = prereq_t.id
                    WHERE p.concept_id = $1
                """, result['concept_id'])
                
                result['prerequisites'] = [dict(row) for row in prerequisites]
            else:
                result['prerequisites'] = []
            
            return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ticket details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ticket details")


@router.get("/stats/service")
async def get_service_stats(
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get ticket service statistics
    
    Requires admin permissions.
    """
    if not user.has_any_permission(["LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    try:
        async with ticket_service.db_pool.acquire() as conn:
            # Get various statistics
            stats = {}
            
            # Learning paths count
            stats['total_learning_paths'] = await conn.fetchval("""
                SELECT COUNT(*) FROM learning.learning_paths
            """)
            
            # Active learning paths
            stats['active_learning_paths'] = await conn.fetchval("""
                SELECT COUNT(*) FROM learning.learning_paths WHERE active = true
            """)
            
            # Total learning tickets
            stats['total_learning_tickets'] = await conn.fetchval("""
                SELECT COUNT(*) FROM ticket WHERE type = 'learning_concept'
            """)
            
            # Tickets by status
            ticket_statuses = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM ticket 
                WHERE type = 'learning_concept'
                GROUP BY status
            """)
            stats['tickets_by_status'] = {row['status']: row['count'] for row in ticket_statuses}
            
            # Prerequisites count
            stats['total_prerequisites'] = await conn.fetchval("""
                SELECT COUNT(*) FROM learning.prerequisites
            """)
            
            # Progress records count
            stats['total_progress_records'] = await conn.fetchval("""
                SELECT COUNT(*) FROM learning.progress
            """)
            
            # Active students
            stats['active_students'] = await conn.fetchval("""
                SELECT COUNT(DISTINCT student_id) FROM learning.progress
            """)
            
            return stats
            
    except Exception as e:
        logger.error(f"Failed to get service stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")