"""
Answer Evaluation Service for Learning System
Uses LLM to evaluate student answers and update progress tracking
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import asyncpg

from .llm_service import llm_service
from .redis_client import redis_cache

logger = logging.getLogger(__name__)


class AnswerEvaluationService:
    """Service for evaluating student answers using LLM and tracking progress"""
    
    def __init__(self, db_pool: asyncpg.Pool = None):
        self.db_pool = db_pool
        self.llm_service = llm_service
        self.cache_client = redis_cache
        self.mastery_threshold = 0.8
        
    async def initialize(self, db_pool: asyncpg.Pool):
        """Initialize the evaluation service with database pool"""
        self.db_pool = db_pool
        logger.info("Answer evaluation service initialized")
    
    async def evaluate_answer(
        self, 
        user_id: str, 
        ticket_id: int, 
        student_answer: str,
        time_spent_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a student's answer for a learning ticket
        
        Args:
            user_id: Cognito user ID
            ticket_id: Trac ticket ID
            student_answer: The student's submitted answer
            time_spent_minutes: Optional time spent on the answer
            
        Returns:
            Dict containing evaluation results including score, feedback, and status
        """
        if not self.db_pool:
            logger.error("Database pool not initialized")
            return {
                'error': 'Service not properly initialized',
                'score': 0.0,
                'feedback': 'Unable to evaluate answer at this time'
            }
        
        try:
            # Get question data from database
            question_data = await self._get_question_data(ticket_id)
            if not question_data:
                return {
                    'error': 'Question not found',
                    'score': 0.0,
                    'feedback': 'Unable to find question data for this ticket'
                }
            
            # Evaluate answer using LLM
            evaluation = await self._evaluate_with_llm(
                question=question_data['question'],
                expected_answer=question_data['expected_answer'],
                student_answer=student_answer,
                context=question_data.get('context', ''),
                difficulty=question_data.get('difficulty', 3)
            )
            
            # Determine status based on score
            status = 'mastered' if evaluation['score'] >= self.mastery_threshold else 'completed'
            
            # Update progress in database
            await self._update_progress(
                user_id=user_id,
                ticket_id=ticket_id,
                status=status,
                student_answer=student_answer,
                score=evaluation['score'],
                feedback=evaluation['feedback'],
                time_spent_minutes=time_spent_minutes
            )
            
            # Update ticket status if mastered
            if status == 'mastered':
                await self._update_ticket_status(ticket_id)
            
            # Cache the evaluation result
            await self._cache_evaluation(user_id, ticket_id, evaluation)
            
            # Invalidate related caches
            await self._invalidate_caches(user_id, ticket_id)
            
            logger.info(f"Successfully evaluated answer for user {user_id}, ticket {ticket_id}, score: {evaluation['score']}")
            
            return {
                'success': True,
                'score': evaluation['score'],
                'feedback': evaluation['feedback'],
                'suggestions': evaluation.get('suggestions', []),
                'status': status,
                'mastery_achieved': status == 'mastered'
            }
            
        except Exception as e:
            logger.error(f"Error evaluating answer: {e}")
            return {
                'error': f'Evaluation failed: {str(e)}',
                'score': 0.0,
                'feedback': 'Unable to evaluate answer due to an error'
            }
    
    async def _get_question_data(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve question data from Trac ticket custom fields"""
        try:
            async with self.db_pool.acquire() as conn:
                # Query to get all custom fields for the ticket
                result = await conn.fetchrow("""
                    SELECT 
                        MAX(CASE WHEN tc.name = 'question' THEN tc.value END) as question,
                        MAX(CASE WHEN tc.name = 'expected_answer' THEN tc.value END) as expected_answer,
                        MAX(CASE WHEN tc.name = 'question_context' THEN tc.value END) as context,
                        MAX(CASE WHEN tc.name = 'question_difficulty' THEN tc.value END) as difficulty
                    FROM ticket_custom tc
                    WHERE tc.ticket = $1
                    GROUP BY tc.ticket
                """, ticket_id)
                
                if not result or not result['question']:
                    logger.warning(f"No question data found for ticket {ticket_id}")
                    return None
                
                return {
                    'question': result['question'],
                    'expected_answer': result['expected_answer'] or '',
                    'context': result['context'] or '',
                    'difficulty': int(result['difficulty']) if result['difficulty'] else 3
                }
                
        except Exception as e:
            logger.error(f"Error retrieving question data: {e}")
            return None
    
    async def _evaluate_with_llm(
        self,
        question: str,
        expected_answer: str,
        student_answer: str,
        context: str,
        difficulty: int
    ) -> Dict[str, Any]:
        """Use LLM to evaluate the student's answer"""
        
        # Create evaluation prompt
        evaluation_prompt = f"""You are an expert educator evaluating a student's answer.

QUESTION: {question}

EXPECTED ANSWER: {expected_answer}

STUDENT ANSWER: {student_answer}

CONTEXT: {context if context else "General learning assessment"}
DIFFICULTY LEVEL: {difficulty}/5

TASK: Evaluate the student's answer based on:
1. Correctness - Does it accurately answer the question?
2. Completeness - Does it cover all key points from the expected answer?
3. Understanding - Does it demonstrate comprehension of the concept?
4. Clarity - Is it well-expressed and clear?

PROVIDE:
1. A score from 0.0 to 1.0 (where 0.8+ indicates mastery)
2. Specific feedback on what was done well
3. Specific feedback on what could be improved
4. 1-3 suggestions for improvement (only if score < 0.8)

FORMAT YOUR RESPONSE EXACTLY AS:
SCORE: [decimal between 0.0 and 1.0]
FEEDBACK: [Detailed feedback combining strengths and areas for improvement]
SUGGESTIONS: [Comma-separated list of suggestions, or "None" if score >= 0.8]

SCORING GUIDELINES:
- 0.9-1.0: Excellent answer that exceeds expectations
- 0.8-0.89: Good answer showing mastery of the concept
- 0.6-0.79: Adequate answer with room for improvement
- 0.4-0.59: Partial understanding demonstrated
- 0.2-0.39: Minimal understanding shown
- 0.0-0.19: Answer misses the point or is incorrect"""

        try:
            # Make LLM request
            response = await self.llm_service._make_llm_request(evaluation_prompt)
            
            if response.get('error'):
                logger.error(f"LLM request failed: {response['error']}")
                return self._fallback_evaluation(student_answer, expected_answer)
            
            # Parse the response
            parsed_result = self._parse_evaluation_response(response)
            
            # Validate the parsed result
            if self._validate_evaluation(parsed_result):
                return parsed_result
            else:
                logger.warning("Evaluation failed validation, using fallback")
                return self._fallback_evaluation(student_answer, expected_answer)
                
        except Exception as e:
            logger.error(f"Error in LLM evaluation: {e}")
            return self._fallback_evaluation(student_answer, expected_answer)
    
    def _parse_evaluation_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the LLM response to extract evaluation components"""
        try:
            # Extract content from response
            if 'choices' in response:
                content = response['choices'][0]['message']['content']
            elif 'response' in response:
                content = response['response']
            else:
                content = str(response)
            
            # Extract score
            score_match = re.search(r'SCORE:\s*([\d.]+)', content, re.IGNORECASE)
            score = float(score_match.group(1)) if score_match else 0.5
            
            # Ensure score is in valid range
            score = max(0.0, min(1.0, score))
            
            # Extract feedback
            feedback_match = re.search(r'FEEDBACK:\s*(.+?)(?=SUGGESTIONS:|$)', content, re.DOTALL | re.IGNORECASE)
            feedback = feedback_match.group(1).strip() if feedback_match else "Your answer has been evaluated."
            
            # Extract suggestions
            suggestions_match = re.search(r'SUGGESTIONS:\s*(.+?)(?=$)', content, re.DOTALL | re.IGNORECASE)
            suggestions_text = suggestions_match.group(1).strip() if suggestions_match else ""
            
            suggestions = []
            if suggestions_text and suggestions_text.lower() != 'none':
                # Split by common delimiters
                suggestion_list = re.split(r'[,;]|\d+\.|\n-', suggestions_text)
                suggestions = [s.strip() for s in suggestion_list if s.strip() and len(s.strip()) > 10]
                suggestions = suggestions[:3]  # Limit to 3 suggestions
            
            return {
                'score': score,
                'feedback': feedback,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Error parsing evaluation response: {e}")
            return {
                'score': 0.5,
                'feedback': 'Unable to parse evaluation response',
                'suggestions': []
            }
    
    def _validate_evaluation(self, evaluation: Dict[str, Any]) -> bool:
        """Validate that the evaluation meets quality standards"""
        
        # Check required fields
        if not all(key in evaluation for key in ['score', 'feedback']):
            return False
        
        # Validate score
        if not isinstance(evaluation['score'], (int, float)):
            return False
        if not 0.0 <= evaluation['score'] <= 1.0:
            return False
        
        # Validate feedback
        if not isinstance(evaluation['feedback'], str):
            return False
        if len(evaluation['feedback']) < 20:  # Minimum feedback length
            return False
        
        # Validate suggestions
        if 'suggestions' in evaluation:
            if not isinstance(evaluation['suggestions'], list):
                return False
            # If score < 0.8, should have suggestions
            if evaluation['score'] < 0.8 and len(evaluation['suggestions']) == 0:
                return False
        
        return True
    
    def _fallback_evaluation(self, student_answer: str, expected_answer: str) -> Dict[str, Any]:
        """Simple fallback evaluation when LLM is unavailable"""
        
        # Basic similarity check
        student_lower = student_answer.lower().strip()
        expected_lower = expected_answer.lower().strip()
        
        # Calculate simple word overlap score
        student_words = set(student_lower.split())
        expected_words = set(expected_lower.split())
        
        if not expected_words:
            score = 0.5
        else:
            overlap = len(student_words & expected_words)
            score = min(0.9, overlap / len(expected_words))
        
        # Adjust score based on answer length
        if len(student_answer) < 50:
            score *= 0.8
        
        feedback = "Your answer has been automatically evaluated. "
        if score >= 0.8:
            feedback += "Good job! You've demonstrated understanding of the concept."
        elif score >= 0.6:
            feedback += "You're on the right track. Consider expanding your answer with more detail."
        else:
            feedback += "Your answer needs more work. Review the material and try to address all aspects of the question."
        
        suggestions = []
        if score < 0.8:
            suggestions = [
                "Review the learning material for this concept",
                "Try to include more specific details in your answer",
                "Consider all aspects mentioned in the question"
            ]
        
        return {
            'score': round(score, 2),
            'feedback': feedback,
            'suggestions': suggestions[:2]
        }
    
    async def _update_progress(
        self,
        user_id: str,
        ticket_id: int,
        status: str,
        student_answer: str,
        score: float,
        feedback: str,
        time_spent_minutes: Optional[int] = None
    ):
        """Update or insert progress record in the database"""
        try:
            async with self.db_pool.acquire() as conn:
                # First get the concept_id from concept_metadata
                concept_id = await conn.fetchval("""
                    SELECT concept_id 
                    FROM learning.concept_metadata 
                    WHERE ticket_id = $1
                """, ticket_id)
                
                if not concept_id:
                    logger.warning(f"No concept_id found for ticket {ticket_id}")
                    # If no concept metadata exists, we'll still track progress by ticket
                
                # Update or insert progress record
                await conn.execute("""
                    INSERT INTO learning.progress (
                        student_id, concept_id, status, mastery_score,
                        time_spent_minutes, attempt_count, last_accessed, 
                        completed_at, notes
                    ) VALUES (
                        $1, $2, $3, $4, $5, 
                        1, CURRENT_TIMESTAMP,
                        CASE WHEN $3 IN ('completed', 'mastered') THEN CURRENT_TIMESTAMP ELSE NULL END,
                        $6
                    )
                    ON CONFLICT (student_id, concept_id) DO UPDATE SET
                        status = $3,
                        mastery_score = $4,
                        time_spent_minutes = COALESCE(progress.time_spent_minutes, 0) + COALESCE($5, 0),
                        attempt_count = progress.attempt_count + 1,
                        last_accessed = CURRENT_TIMESTAMP,
                        completed_at = CASE 
                            WHEN $3 IN ('completed', 'mastered') AND progress.completed_at IS NULL 
                            THEN CURRENT_TIMESTAMP 
                            ELSE progress.completed_at 
                        END,
                        notes = $6
                """, 
                user_id, concept_id, status, score, 
                time_spent_minutes or 0,
                json.dumps({
                    'last_answer': student_answer,
                    'last_feedback': feedback,
                    'last_evaluated': datetime.utcnow().isoformat()
                })
                )
                
                logger.info(f"Updated progress for user {user_id}, concept {concept_id}, status: {status}")
                
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            raise
    
    async def _update_ticket_status(self, ticket_id: int):
        """Update Trac ticket status when mastery is achieved"""
        try:
            async with self.db_pool.acquire() as conn:
                # Update ticket status to closed with resolution fixed
                await conn.execute("""
                    UPDATE ticket 
                    SET status = 'closed', 
                        resolution = 'fixed',
                        changetime = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, ticket_id)
                
                # Add a ticket change record for audit trail
                await conn.execute("""
                    INSERT INTO ticket_change (ticket, time, author, field, oldvalue, newvalue)
                    VALUES 
                        ($1, CURRENT_TIMESTAMP, 'learntrac-system', 'status', 
                         (SELECT status FROM ticket WHERE id = $1), 'closed'),
                        ($1, CURRENT_TIMESTAMP, 'learntrac-system', 'resolution', 
                         '', 'fixed'),
                        ($1, CURRENT_TIMESTAMP, 'learntrac-system', 'comment', 
                         '', 'Automatically closed: Student achieved mastery on this learning concept.')
                """, ticket_id)
                
                logger.info(f"Updated ticket {ticket_id} status to closed (mastery achieved)")
                
        except Exception as e:
            logger.error(f"Error updating ticket status: {e}")
            # Don't raise - this is not critical for the evaluation flow
    
    async def _cache_evaluation(self, user_id: str, ticket_id: int, evaluation: Dict[str, Any]):
        """Cache evaluation result for quick retrieval"""
        try:
            cache_key = f"evaluation:{user_id}:{ticket_id}"
            cache_data = {
                'score': evaluation['score'],
                'feedback': evaluation['feedback'],
                'suggestions': evaluation.get('suggestions', []),
                'evaluated_at': datetime.utcnow().isoformat()
            }
            
            # Cache for 1 hour
            await self.cache_client.set_json(cache_key, cache_data, ttl=3600)
            
        except Exception as e:
            logger.error(f"Error caching evaluation: {e}")
            # Don't raise - caching is not critical
    
    async def _invalidate_caches(self, user_id: str, ticket_id: int):
        """Invalidate related caches after progress update"""
        try:
            # Get milestone for the ticket to invalidate graph cache
            async with self.db_pool.acquire() as conn:
                milestone = await conn.fetchval(
                    "SELECT milestone FROM ticket WHERE id = $1", 
                    ticket_id
                )
            
            if milestone:
                # Invalidate graph cache for this milestone
                graph_cache_key = f"learning_graph:{milestone}:{user_id}"
                await self.cache_client.delete(graph_cache_key)
                
                # Also invalidate the general milestone graph
                milestone_cache_key = f"milestone_graph:{milestone}"
                await self.cache_client.delete(milestone_cache_key)
            
            # Invalidate user progress cache
            progress_cache_key = f"user_progress:{user_id}"
            await self.cache_client.delete(progress_cache_key)
            
            # Invalidate ticket progress cache (used by Trac plugin)
            ticket_cache_key = f"learntrac_progress:{ticket_id}_{user_id}"
            await self.cache_client.delete(ticket_cache_key)
            
            logger.info(f"Invalidated caches for user {user_id}, ticket {ticket_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating caches: {e}")
            # Don't raise - cache invalidation is not critical
    
    async def get_evaluation_history(self, user_id: str, ticket_id: int) -> List[Dict[str, Any]]:
        """Get evaluation history for a user and ticket"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get concept_id for the ticket
                concept_id = await conn.fetchval("""
                    SELECT concept_id 
                    FROM learning.concept_metadata 
                    WHERE ticket_id = $1
                """, ticket_id)
                
                if not concept_id:
                    return []
                
                # Get progress record with parsed notes
                result = await conn.fetchrow("""
                    SELECT status, mastery_score, time_spent_minutes,
                           attempt_count, last_accessed, completed_at, notes
                    FROM learning.progress
                    WHERE student_id = $1 AND concept_id = $2
                """, user_id, concept_id)
                
                if not result:
                    return []
                
                history = [{
                    'status': result['status'],
                    'score': result['mastery_score'],
                    'time_spent_minutes': result['time_spent_minutes'],
                    'attempt_count': result['attempt_count'],
                    'last_accessed': result['last_accessed'].isoformat() if result['last_accessed'] else None,
                    'completed_at': result['completed_at'].isoformat() if result['completed_at'] else None
                }]
                
                # Parse notes if available
                if result['notes']:
                    try:
                        notes_data = json.loads(result['notes'])
                        history[0].update({
                            'last_answer': notes_data.get('last_answer'),
                            'last_feedback': notes_data.get('last_feedback'),
                            'last_evaluated': notes_data.get('last_evaluated')
                        })
                    except json.JSONDecodeError:
                        pass
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting evaluation history: {e}")
            return []


# Create singleton instance
evaluation_service = AnswerEvaluationService()