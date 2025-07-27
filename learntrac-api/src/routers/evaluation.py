"""
Answer Evaluation API Router
Provides endpoints for evaluating student answers and retrieving evaluation history
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator
import logging

from ..auth.modern_session_handler import get_current_user, get_current_user_required, AuthenticatedUser
from ..services.evaluation_service import evaluation_service

logger = logging.getLogger(__name__)

router = APIRouter()


class AnswerSubmission(BaseModel):
    """Model for answer submission requests"""
    ticket_id: int = Field(..., description="Trac ticket ID")
    answer: str = Field(..., min_length=1, max_length=5000, description="Student's answer")
    time_spent_minutes: Optional[int] = Field(None, ge=0, le=600, description="Time spent on answer")
    
    @validator('answer')
    def validate_answer(cls, v):
        # Remove excessive whitespace
        cleaned = ' '.join(v.split())
        if len(cleaned) < 10:
            raise ValueError('Answer must be at least 10 characters long')
        return v


class EvaluationResponse(BaseModel):
    """Model for evaluation response"""
    success: bool
    score: float = Field(..., ge=0.0, le=1.0)
    feedback: str
    suggestions: list[str] = []
    status: str = Field(..., description="Progress status (completed/mastered)")
    mastery_achieved: bool
    error: Optional[str] = None


class EvaluationHistoryResponse(BaseModel):
    """Model for evaluation history response"""
    ticket_id: int
    history: list[Dict[str, Any]]
    current_status: Optional[str] = None
    total_attempts: int = 0


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_answer(
    submission: AnswerSubmission,
    user: AuthenticatedUser = Depends(get_current_user)
) -> EvaluationResponse:
    """
    Evaluate a student's answer for a learning ticket
    
    This endpoint:
    - Retrieves the question and expected answer from the ticket
    - Uses LLM to evaluate the student's answer
    - Updates progress tracking in the database
    - Returns score, feedback, and improvement suggestions
    
    Requires LEARNING_READ permission (students can evaluate their own answers).
    """
    # Check permissions - students can submit their own answers
    if not user.has_any_permission(["LEARNING_READ", "LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Call evaluation service
        result = await evaluation_service.evaluate_answer(
            user_id=user.sub,
            ticket_id=submission.ticket_id,
            student_answer=submission.answer,
            time_spent_minutes=submission.time_spent_minutes
        )
        
        # Check for errors in the result
        if result.get('error'):
            logger.error(f"Evaluation error for user {user.sub}, ticket {submission.ticket_id}: {result['error']}")
            raise HTTPException(status_code=500, detail=result['error'])
        
        return EvaluationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error evaluating answer: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate answer")


@router.get("/history/{ticket_id}", response_model=EvaluationHistoryResponse)
async def get_evaluation_history(
    ticket_id: int,
    user: AuthenticatedUser = Depends(get_current_user)
) -> EvaluationHistoryResponse:
    """
    Get evaluation history for a specific ticket
    
    Returns the user's attempt history including:
    - Previous scores and feedback
    - Number of attempts
    - Current progress status
    - Time spent
    
    Students can only view their own history.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_READ", "LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Get evaluation history
        history = await evaluation_service.get_evaluation_history(
            user_id=user.sub,
            ticket_id=ticket_id
        )
        
        # Calculate summary statistics
        current_status = None
        total_attempts = 0
        
        if history:
            current_status = history[0].get('status')
            total_attempts = history[0].get('attempt_count', 0)
        
        return EvaluationHistoryResponse(
            ticket_id=ticket_id,
            history=history,
            current_status=current_status,
            total_attempts=total_attempts
        )
        
    except Exception as e:
        logger.error(f"Error getting evaluation history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve evaluation history")


@router.post("/evaluate/bulk")
async def evaluate_multiple_answers(
    submissions: list[AnswerSubmission] = Body(..., max_items=10),
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Evaluate multiple answers in a single request
    
    Useful for batch processing or when students complete multiple questions.
    Limited to 10 evaluations per request to prevent overload.
    
    Requires LEARNING_INSTRUCT or LEARNING_ADMIN permission.
    """
    # Check permissions - only instructors/admins can bulk evaluate
    if not user.has_any_permission(["LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Bulk evaluation requires instructor permissions")
    
    results = []
    errors = []
    
    for i, submission in enumerate(submissions):
        try:
            result = await evaluation_service.evaluate_answer(
                user_id=user.sub,
                ticket_id=submission.ticket_id,
                student_answer=submission.answer,
                time_spent_minutes=submission.time_spent_minutes
            )
            
            results.append({
                'ticket_id': submission.ticket_id,
                'success': not result.get('error'),
                'score': result.get('score', 0.0),
                'status': result.get('status')
            })
            
        except Exception as e:
            logger.error(f"Error in bulk evaluation for ticket {submission.ticket_id}: {e}")
            errors.append({
                'ticket_id': submission.ticket_id,
                'error': str(e)
            })
    
    return {
        'evaluated': len(results),
        'failed': len(errors),
        'results': results,
        'errors': errors
    }


@router.get("/stats/personal")
async def get_personal_evaluation_stats(
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get personal evaluation statistics for the current user
    
    Returns:
    - Total evaluations
    - Average score
    - Mastery rate
    - Time invested
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_READ", "LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        from ..db.database import db_manager
        
        async with db_manager.pool.acquire() as conn:
            # Get aggregated stats for the user
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_evaluations,
                    AVG(mastery_score) as average_score,
                    SUM(CASE WHEN status = 'mastered' THEN 1 ELSE 0 END)::float / 
                        NULLIF(COUNT(*), 0) as mastery_rate,
                    SUM(time_spent_minutes) as total_time_minutes,
                    MAX(last_accessed) as last_activity
                FROM learning.progress
                WHERE student_id = $1
            """, user.sub)
            
            if not stats or stats['total_evaluations'] == 0:
                return {
                    'total_evaluations': 0,
                    'average_score': 0.0,
                    'mastery_rate': 0.0,
                    'total_time_hours': 0.0,
                    'last_activity': None
                }
            
            return {
                'total_evaluations': stats['total_evaluations'],
                'average_score': round(float(stats['average_score'] or 0), 2),
                'mastery_rate': round(float(stats['mastery_rate'] or 0), 2),
                'total_time_hours': round((stats['total_time_minutes'] or 0) / 60.0, 1),
                'last_activity': stats['last_activity'].isoformat() if stats['last_activity'] else None
            }
            
    except Exception as e:
        logger.error(f"Error getting personal stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/leaderboard")
async def get_evaluation_leaderboard(
    limit: int = 10,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get evaluation leaderboard (anonymized)
    
    Shows top performers based on mastery rate and average scores.
    User identities are anonymized for privacy.
    
    Requires any learning permission.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_READ", "LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        from ..db.database import db_manager
        
        async with db_manager.pool.acquire() as conn:
            # Get top performers
            leaders = await conn.fetch("""
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY mastery_rate DESC, avg_score DESC) as rank,
                    student_id,
                    COUNT(*) as total_completed,
                    AVG(mastery_score) as avg_score,
                    SUM(CASE WHEN status = 'mastered' THEN 1 ELSE 0 END)::float / 
                        NULLIF(COUNT(*), 0) as mastery_rate,
                    SUM(time_spent_minutes) as total_time
                FROM learning.progress
                WHERE status IN ('completed', 'mastered')
                GROUP BY student_id
                HAVING COUNT(*) >= 5  -- Minimum 5 evaluations to appear
                ORDER BY mastery_rate DESC, avg_score DESC
                LIMIT $1
            """, limit)
            
            # Anonymize and format results
            leaderboard = []
            for i, leader in enumerate(leaders):
                # Check if this is the current user
                is_current_user = leader['student_id'] == user.sub
                
                leaderboard.append({
                    'rank': i + 1,
                    'display_name': 'You' if is_current_user else f'Learner {i + 1}',
                    'is_you': is_current_user,
                    'total_completed': leader['total_completed'],
                    'average_score': round(float(leader['avg_score'] or 0), 2),
                    'mastery_rate': round(float(leader['mastery_rate'] or 0), 2),
                    'total_hours': round((leader['total_time'] or 0) / 60.0, 1)
                })
            
            return {
                'leaderboard': leaderboard,
                'total_participants': len(leaders)
            }
            
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve leaderboard")