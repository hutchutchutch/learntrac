from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from uuid import UUID
import logging

from ..auth.jwt_handler import get_current_user, AuthenticatedUser, require_student
from ..db.database import get_db_connection
from ..services.redis_client import redis_cache
from ..services.neo4j_client import neo4j_client
from ..services.embedding_service import embedding_service
from ..services.generation_service import generation_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for requests/responses
class ConceptResponse(BaseModel):
    concept_id: str
    ticket_id: int
    path_id: Optional[str]
    title: str
    description: str
    difficulty_score: int
    estimated_minutes: int
    prerequisites: List[str] = []
    learning_objectives: List[str] = []
    tags: List[str] = []


class ProgressUpdate(BaseModel):
    status: str = Field(..., pattern="^(not_started|in_progress|completed|mastered)$")
    mastery_score: Optional[float] = Field(None, ge=0, le=1)
    time_spent_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class PracticeSubmission(BaseModel):
    answers: List[Dict[str, any]]
    time_spent_seconds: int


@router.get("/paths", response_model=List[Dict[str, any]])
async def get_learning_paths(
    active_only: bool = True,
    user: AuthenticatedUser = Depends(get_current_user),
    conn = Depends(get_db_connection)
):
    """Get all available learning paths"""
    try:
        query = """
            SELECT 
                path_id,
                title,
                description,
                difficulty_level,
                estimated_hours,
                tags,
                (SELECT COUNT(*) FROM learning.concept_metadata WHERE path_id = p.path_id) as concept_count
            FROM learning.learning_paths p
            WHERE ($1 = false OR active = true)
            ORDER BY created_at DESC
        """
        
        rows = await conn.fetch(query, active_only)
        
        paths = []
        for row in rows:
            paths.append({
                "path_id": str(row["path_id"]),
                "title": row["title"],
                "description": row["description"],
                "difficulty_level": row["difficulty_level"],
                "estimated_hours": row["estimated_hours"],
                "tags": row["tags"] or [],
                "concept_count": row["concept_count"]
            })
        
        return paths
        
    except Exception as e:
        logger.error(f"Failed to get learning paths: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve learning paths")


@router.get("/paths/{path_id}/concepts", response_model=List[ConceptResponse])
async def get_path_concepts(
    path_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    conn = Depends(get_db_connection)
):
    """Get all concepts in a learning path"""
    try:
        # Check if path exists
        path_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM learning.learning_paths WHERE path_id = $1)",
            path_id
        )
        
        if not path_exists:
            raise HTTPException(status_code=404, detail="Learning path not found")
        
        # Get concepts with ticket information
        query = """
            SELECT 
                cm.concept_id,
                cm.ticket_id,
                cm.path_id,
                cm.sequence_order,
                cm.concept_type,
                cm.difficulty_score,
                cm.estimated_minutes,
                cm.learning_objectives,
                cm.tags,
                t.summary as title,
                t.description,
                array_agg(DISTINCT p.prereq_concept_id) FILTER (WHERE p.prereq_concept_id IS NOT NULL) as prerequisites
            FROM learning.concept_metadata cm
            JOIN public.ticket t ON cm.ticket_id = t.id
            LEFT JOIN learning.prerequisites p ON cm.concept_id = p.concept_id
            WHERE cm.path_id = $1
            GROUP BY cm.concept_id, cm.ticket_id, cm.path_id, cm.sequence_order,
                     cm.concept_type, cm.difficulty_score, cm.estimated_minutes,
                     cm.learning_objectives, cm.tags, t.summary, t.description
            ORDER BY cm.sequence_order
        """
        
        rows = await conn.fetch(query, path_id)
        
        concepts = []
        for row in rows:
            concepts.append(ConceptResponse(
                concept_id=str(row["concept_id"]),
                ticket_id=row["ticket_id"],
                path_id=str(row["path_id"]),
                title=row["title"],
                description=row["description"] or "",
                difficulty_score=row["difficulty_score"],
                estimated_minutes=row["estimated_minutes"] or 30,
                prerequisites=[str(p) for p in (row["prerequisites"] or [])],
                learning_objectives=row["learning_objectives"] or [],
                tags=row["tags"] or []
            ))
        
        return concepts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get path concepts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve concepts")


@router.get("/concepts/{concept_id}", response_model=ConceptResponse)
async def get_concept(
    concept_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    conn = Depends(get_db_connection)
):
    """Get detailed information about a specific concept"""
    # Try cache first
    cache_key = f"concept:{concept_id}"
    cached = await redis_cache.get_json(cache_key)
    if cached:
        return ConceptResponse(**cached)
    
    try:
        query = """
            SELECT 
                cm.concept_id,
                cm.ticket_id,
                cm.path_id,
                cm.concept_type,
                cm.difficulty_score,
                cm.estimated_minutes,
                cm.practice_questions,
                cm.learning_objectives,
                cm.resources,
                cm.tags,
                t.summary as title,
                t.description,
                array_agg(DISTINCT p.prereq_concept_id) FILTER (WHERE p.prereq_concept_id IS NOT NULL) as prerequisites
            FROM learning.concept_metadata cm
            JOIN public.ticket t ON cm.ticket_id = t.id
            LEFT JOIN learning.prerequisites p ON cm.concept_id = p.concept_id
            WHERE cm.concept_id = $1
            GROUP BY cm.concept_id, cm.ticket_id, cm.path_id, cm.concept_type,
                     cm.difficulty_score, cm.estimated_minutes, cm.practice_questions,
                     cm.learning_objectives, cm.resources, cm.tags, t.summary, t.description
        """
        
        row = await conn.fetchrow(query, concept_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Concept not found")
        
        concept_data = {
            "concept_id": str(row["concept_id"]),
            "ticket_id": row["ticket_id"],
            "path_id": str(row["path_id"]) if row["path_id"] else None,
            "title": row["title"],
            "description": row["description"] or "",
            "difficulty_score": row["difficulty_score"],
            "estimated_minutes": row["estimated_minutes"] or 30,
            "prerequisites": [str(p) for p in (row["prerequisites"] or [])],
            "learning_objectives": row["learning_objectives"] or [],
            "tags": row["tags"] or []
        }
        
        # Cache for 1 hour
        await redis_cache.set_json(cache_key, concept_data, 3600)
        
        return ConceptResponse(**concept_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get concept: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve concept")


@router.get("/concepts/{concept_id}/practice")
async def get_practice_questions(
    concept_id: UUID,
    regenerate: bool = False,
    user: AuthenticatedUser = Depends(get_current_user),
    conn = Depends(get_db_connection)
):
    """Get practice questions for a concept"""
    try:
        # Get concept info
        concept = await conn.fetchrow(
            """
            SELECT cm.*, t.summary as title, t.description
            FROM learning.concept_metadata cm
            JOIN public.ticket t ON cm.ticket_id = t.id
            WHERE cm.concept_id = $1
            """,
            concept_id
        )
        
        if not concept:
            raise HTTPException(status_code=404, detail="Concept not found")
        
        # Check if we have cached questions
        if concept["practice_questions"] and not regenerate:
            return {
                "concept_id": str(concept_id),
                "title": concept["title"],
                "questions": concept["practice_questions"]
            }
        
        # Generate new questions
        questions = await generation_service.generate_practice_questions(
            concept=concept["title"],
            description=concept["description"] or "",
            difficulty="intermediate" if concept["difficulty_score"] == 5 else "advanced"
        )
        
        if questions:
            # Store in database
            await conn.execute(
                """
                UPDATE learning.concept_metadata 
                SET practice_questions = $2
                WHERE concept_id = $1
                """,
                concept_id, questions
            )
        
        return {
            "concept_id": str(concept_id),
            "title": concept["title"],
            "questions": questions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get practice questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve practice questions")


@router.post("/concepts/{concept_id}/practice")
async def submit_practice_answers(
    concept_id: UUID,
    submission: PracticeSubmission,
    user: AuthenticatedUser = Depends(require_student),
    conn = Depends(get_db_connection)
):
    """Submit practice answers and update progress"""
    try:
        # Calculate score
        correct_count = sum(1 for answer in submission.answers if answer.get("is_correct", False))
        total_questions = len(submission.answers)
        score = correct_count / total_questions if total_questions > 0 else 0
        
        # Update progress
        await conn.execute(
            """
            INSERT INTO learning.progress (student_id, concept_id, ticket_id, status, mastery_score, 
                                         time_spent_minutes, attempt_count, practice_results)
            VALUES ($1, $2, 
                    (SELECT ticket_id FROM learning.concept_metadata WHERE concept_id = $2),
                    'in_progress', $3, $4, 1, $5)
            ON CONFLICT (student_id, concept_id) 
            DO UPDATE SET 
                mastery_score = GREATEST(progress.mastery_score, $3),
                time_spent_minutes = progress.time_spent_minutes + $4,
                attempt_count = progress.attempt_count + 1,
                practice_results = $5,
                last_accessed = CURRENT_TIMESTAMP,
                status = CASE 
                    WHEN GREATEST(progress.mastery_score, $3) >= 0.8 THEN 'completed'
                    ELSE 'in_progress'
                END
            """,
            user.sub, concept_id, score, submission.time_spent_seconds // 60, submission.dict()
        )
        
        return {
            "score": score,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "mastery_achieved": score >= 0.8,
            "message": "Practice results recorded successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit practice answers: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit practice answers")


@router.get("/progress")
async def get_my_progress(
    path_id: Optional[UUID] = None,
    user: AuthenticatedUser = Depends(require_student),
    conn = Depends(get_db_connection)
):
    """Get current user's learning progress"""
    try:
        if path_id:
            # Get progress for specific path
            query = """
                SELECT 
                    COUNT(DISTINCT cm.concept_id) as total_concepts,
                    COUNT(DISTINCT p.concept_id) FILTER (WHERE p.status = 'completed') as completed,
                    COUNT(DISTINCT p.concept_id) FILTER (WHERE p.status = 'in_progress') as in_progress,
                    COUNT(DISTINCT p.concept_id) FILTER (WHERE p.status = 'mastered') as mastered,
                    AVG(p.mastery_score) FILTER (WHERE p.mastery_score IS NOT NULL) as avg_mastery,
                    SUM(p.time_spent_minutes) as total_time_minutes
                FROM learning.concept_metadata cm
                LEFT JOIN learning.progress p ON cm.concept_id = p.concept_id AND p.student_id = $1
                WHERE cm.path_id = $2
            """
            stats = await conn.fetchrow(query, user.sub, path_id)
        else:
            # Get overall progress
            query = """
                SELECT 
                    COUNT(DISTINCT cm.concept_id) as total_concepts,
                    COUNT(DISTINCT p.concept_id) FILTER (WHERE p.status = 'completed') as completed,
                    COUNT(DISTINCT p.concept_id) FILTER (WHERE p.status = 'in_progress') as in_progress,
                    COUNT(DISTINCT p.concept_id) FILTER (WHERE p.status = 'mastered') as mastered,
                    AVG(p.mastery_score) FILTER (WHERE p.mastery_score IS NOT NULL) as avg_mastery,
                    SUM(p.time_spent_minutes) as total_time_minutes
                FROM learning.concept_metadata cm
                LEFT JOIN learning.progress p ON cm.concept_id = p.concept_id AND p.student_id = $1
            """
            stats = await conn.fetchrow(query, user.sub)
        
        # Get recent activity
        recent_query = """
            SELECT 
                p.concept_id,
                p.status,
                p.mastery_score,
                p.last_accessed,
                cm.ticket_id,
                t.summary as concept_title
            FROM learning.progress p
            JOIN learning.concept_metadata cm ON p.concept_id = cm.concept_id
            JOIN public.ticket t ON cm.ticket_id = t.id
            WHERE p.student_id = $1
            ORDER BY p.last_accessed DESC
            LIMIT 5
        """
        recent = await conn.fetch(recent_query, user.sub)
        
        return {
            "student_id": user.sub,
            "statistics": {
                "total_concepts": stats["total_concepts"],
                "completed": stats["completed"],
                "in_progress": stats["in_progress"],
                "mastered": stats["mastered"],
                "average_mastery": float(stats["avg_mastery"]) if stats["avg_mastery"] else 0,
                "total_time_hours": round((stats["total_time_minutes"] or 0) / 60, 1),
                "completion_percentage": round(
                    (stats["completed"] / stats["total_concepts"] * 100) if stats["total_concepts"] > 0 else 0,
                    1
                )
            },
            "recent_activity": [
                {
                    "concept_id": str(r["concept_id"]),
                    "concept_title": r["concept_title"],
                    "status": r["status"],
                    "mastery_score": float(r["mastery_score"]) if r["mastery_score"] else 0,
                    "last_accessed": r["last_accessed"].isoformat() if r["last_accessed"] else None
                }
                for r in recent
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve progress")


@router.put("/progress/{concept_id}")
async def update_progress(
    concept_id: UUID,
    update: ProgressUpdate,
    user: AuthenticatedUser = Depends(require_student),
    conn = Depends(get_db_connection)
):
    """Update progress for a specific concept"""
    try:
        # Get ticket_id for the concept
        ticket_id = await conn.fetchval(
            "SELECT ticket_id FROM learning.concept_metadata WHERE concept_id = $1",
            concept_id
        )
        
        if not ticket_id:
            raise HTTPException(status_code=404, detail="Concept not found")
        
        # Update progress
        await conn.execute(
            """
            INSERT INTO learning.progress (student_id, concept_id, ticket_id, status, mastery_score, 
                                         time_spent_minutes, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (student_id, concept_id) 
            DO UPDATE SET 
                status = $4,
                mastery_score = COALESCE($5, progress.mastery_score),
                time_spent_minutes = progress.time_spent_minutes + COALESCE($6, 0),
                notes = COALESCE($7, progress.notes),
                last_accessed = CURRENT_TIMESTAMP,
                completed_at = CASE WHEN $4 IN ('completed', 'mastered') THEN CURRENT_TIMESTAMP ELSE NULL END
            """,
            user.sub, concept_id, ticket_id, update.status, update.mastery_score,
            update.time_spent_minutes, update.notes
        )
        
        return {"message": "Progress updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to update progress")


@router.get("/search")
async def search_concepts(
    q: str = Query(..., min_length=3, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    user: AuthenticatedUser = Depends(get_current_user),
    conn = Depends(get_db_connection)
):
    """Search for concepts using vector similarity"""
    try:
        # Generate embedding for query
        query_embedding = await embedding_service.generate_query_embedding(q)
        
        if query_embedding and neo4j_client._initialized:
            # Vector search in Neo4j
            similar_content = await neo4j_client.find_similar_content(
                query_embedding=query_embedding,
                limit=limit,
                threshold=0.7,
                content_type="concept"
            )
            
            if similar_content:
                # Get concept details for similar content
                concept_ids = [item["concept_id"] for item in similar_content if item["concept_id"]]
                
                if concept_ids:
                    query = """
                        SELECT 
                            cm.concept_id,
                            cm.ticket_id,
                            t.summary as title,
                            t.description,
                            cm.difficulty_score,
                            cm.tags
                        FROM learning.concept_metadata cm
                        JOIN public.ticket t ON cm.ticket_id = t.id
                        WHERE cm.concept_id = ANY($1)
                    """
                    
                    rows = await conn.fetch(query, concept_ids)
                    
                    # Combine with similarity scores
                    results = []
                    for row in rows:
                        concept_id = str(row["concept_id"])
                        score = next((item["score"] for item in similar_content 
                                    if item["concept_id"] == concept_id), 0)
                        
                        results.append({
                            "concept_id": concept_id,
                            "ticket_id": row["ticket_id"],
                            "title": row["title"],
                            "description": row["description"] or "",
                            "difficulty_score": row["difficulty_score"],
                            "tags": row["tags"] or [],
                            "similarity_score": score
                        })
                    
                    results.sort(key=lambda x: x["similarity_score"], reverse=True)
                    return {"results": results, "search_type": "vector"}
        
        # Fallback to text search
        query = """
            SELECT 
                cm.concept_id,
                cm.ticket_id,
                t.summary as title,
                t.description,
                cm.difficulty_score,
                cm.tags,
                ts_rank(
                    to_tsvector('english', t.summary || ' ' || COALESCE(t.description, '')),
                    plainto_tsquery('english', $1)
                ) as relevance
            FROM learning.concept_metadata cm
            JOIN public.ticket t ON cm.ticket_id = t.id
            WHERE to_tsvector('english', t.summary || ' ' || COALESCE(t.description, '')) 
                  @@ plainto_tsquery('english', $1)
            ORDER BY relevance DESC
            LIMIT $2
        """
        
        rows = await conn.fetch(query, q, limit)
        
        results = [
            {
                "concept_id": str(row["concept_id"]),
                "ticket_id": row["ticket_id"],
                "title": row["title"],
                "description": row["description"] or "",
                "difficulty_score": row["difficulty_score"],
                "tags": row["tags"] or [],
                "relevance_score": float(row["relevance"])
            }
            for row in rows
        ]
        
        return {"results": results, "search_type": "text"}
        
    except Exception as e:
        logger.error(f"Failed to search concepts: {e}")
        raise HTTPException(status_code=500, detail="Failed to search concepts")