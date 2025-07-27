"""
LLM Integration API Router
Provides endpoints for AI-powered question generation and content analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from ..auth.modern_session_handler import get_current_user, get_current_user_required, AuthenticatedUser
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)

router = APIRouter()


class QuestionGenerationRequest(BaseModel):
    """Request model for question generation"""
    chunk_content: str = Field(..., description="Learning content to generate question from")
    concept: str = Field(..., description="Specific concept being tested")
    difficulty: int = Field(3, ge=1, le=5, description="Difficulty level (1-5 scale)")
    context: Optional[str] = Field("", description="Additional learning context")
    question_type: str = Field("comprehension", description="Type of question to generate")


class MultipleQuestionsRequest(BaseModel):
    """Request model for generating multiple questions"""
    chunk_content: str = Field(..., description="Learning content to generate questions from")
    concept: str = Field(..., description="Specific concept being tested")
    count: int = Field(3, ge=1, le=10, description="Number of questions to generate")
    difficulty_range: tuple = Field((2, 4), description="Difficulty range (min, max)")
    question_types: Optional[List[str]] = Field(None, description="Types of questions to generate")


class QuestionResponse(BaseModel):
    """Response model for generated questions"""
    question: Optional[str]
    expected_answer: Optional[str]
    concept: str
    difficulty: int
    generated_at: str
    question_length: int
    answer_length: int
    error: Optional[str] = None


@router.post("/generate-question")
async def generate_question(
    request: QuestionGenerationRequest,
    user: AuthenticatedUser = Depends(get_current_user)
) -> QuestionResponse:
    """
    Generate a single question based on learning content
    
    Requires learning permissions to access.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_READ", "LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        result = await llm_service.generate_question(
            chunk_content=request.chunk_content,
            concept=request.concept,
            difficulty=request.difficulty,
            context=request.context,
            question_type=request.question_type
        )
        
        return QuestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        raise HTTPException(status_code=500, detail="Question generation failed")


@router.post("/generate-multiple-questions")
async def generate_multiple_questions(
    request: MultipleQuestionsRequest,
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate multiple questions for the same content
    
    Useful for creating comprehensive assessments.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        questions = await llm_service.generate_multiple_questions(
            chunk_content=request.chunk_content,
            concept=request.concept,
            count=request.count,
            difficulty_range=request.difficulty_range,
            question_types=request.question_types
        )
        
        return {
            "concept": request.concept,
            "requested_count": request.count,
            "generated_count": len(questions),
            "questions": questions
        }
        
    except Exception as e:
        logger.error(f"Multiple question generation failed: {e}")
        raise HTTPException(status_code=500, detail="Multiple question generation failed")


@router.post("/generate-from-chunks")
async def generate_from_chunks(
    chunk_ids: List[str] = Body(..., description="List of chunk IDs to generate questions from"),
    difficulty: int = Body(3, ge=1, le=5, description="Question difficulty level"),
    questions_per_chunk: int = Body(1, ge=1, le=5, description="Questions per chunk"),
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate questions from multiple Neo4j chunks
    
    Combines vector search results with question generation.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        from ..services.neo4j_aura_client import neo4j_aura_client
        
        all_questions = []
        failed_chunks = []
        
        for chunk_id in chunk_ids:
            try:
                # Get chunk content from Neo4j
                chunk_data = await neo4j_aura_client.get_chunk_by_id(chunk_id)
                
                if not chunk_data:
                    failed_chunks.append({"chunk_id": chunk_id, "error": "Chunk not found"})
                    continue
                
                # Generate questions for this chunk
                questions = await llm_service.generate_multiple_questions(
                    chunk_content=chunk_data.get('content', ''),
                    concept=chunk_data.get('concept', 'General Knowledge'),
                    count=questions_per_chunk,
                    difficulty_range=(difficulty, difficulty)
                )
                
                # Add chunk metadata to questions
                for question in questions:
                    question['chunk_id'] = chunk_id
                    question['subject'] = chunk_data.get('subject')
                
                all_questions.extend(questions)
                
            except Exception as e:
                logger.error(f"Failed to process chunk {chunk_id}: {e}")
                failed_chunks.append({"chunk_id": chunk_id, "error": str(e)})
        
        return {
            "total_chunks_requested": len(chunk_ids),
            "successful_chunks": len(chunk_ids) - len(failed_chunks),
            "failed_chunks": failed_chunks,
            "total_questions_generated": len(all_questions),
            "questions": all_questions
        }
        
    except Exception as e:
        logger.error(f"Chunk-based question generation failed: {e}")
        raise HTTPException(status_code=500, detail="Chunk-based question generation failed")


@router.post("/analyze-content")
async def analyze_content(
    content: str = Body(..., description="Content to analyze"),
    analysis_type: str = Body("difficulty", description="Type of analysis (difficulty, concepts, readability)"),
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Analyze content using LLM for educational insights
    
    Provides difficulty assessment, concept extraction, and readability analysis.
    """
    # Check permissions
    if not user.has_any_permission(["LEARNING_READ", "LEARNING_INSTRUCT", "LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Create analysis prompt based on type
        if analysis_type == "difficulty":
            prompt = f"""Analyze the following educational content and assess its difficulty level on a scale of 1-5:

Content: {content}

Provide:
1. Difficulty rating (1-5)
2. Reasoning for the rating
3. Prerequisites needed
4. Target audience level

Format as JSON."""
            
        elif analysis_type == "concepts":
            prompt = f"""Extract the main learning concepts from this content:

Content: {content}

Provide:
1. Primary concepts (3-5 main topics)
2. Secondary concepts (supporting topics)
3. Prerequisites for understanding
4. Related concepts to explore

Format as JSON."""
            
        elif analysis_type == "readability":
            prompt = f"""Analyze the readability and educational quality of this content:

Content: {content}

Provide:
1. Reading level (grade level)
2. Clarity score (1-10)
3. Educational effectiveness
4. Suggestions for improvement

Format as JSON."""
            
        else:
            raise HTTPException(status_code=400, detail="Invalid analysis type")
        
        # Generate analysis using LLM service's internal method
        result = await llm_service._make_llm_request(prompt)
        
        if result.get('error'):
            raise HTTPException(status_code=500, detail=result['error'])
        
        # Parse response
        if 'choices' in result:
            analysis = result['choices'][0]['message']['content']
        else:
            analysis = str(result)
        
        return {
            "content_length": len(content),
            "analysis_type": analysis_type,
            "analysis": analysis,
            "generated_at": llm_service._generate_cache_key(content, analysis_type, 1, "", "analysis")[:16]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Content analysis failed")


@router.get("/question-types")
async def get_question_types(
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get available question types and their descriptions
    """
    return {
        "question_types": {
            "comprehension": {
                "description": "Tests understanding of core concepts and main ideas",
                "cognitive_level": "Remember/Understand",
                "example": "What is the main purpose of Python functions?"
            },
            "application": {
                "description": "Requires applying concepts to solve problems",
                "cognitive_level": "Apply",
                "example": "How would you use a Python function to calculate the area of a circle?"
            },
            "analysis": {
                "description": "Requires breaking down concepts into components",
                "cognitive_level": "Analyze",
                "example": "Compare and contrast list comprehensions vs for loops in Python"
            },
            "synthesis": {
                "description": "Requires combining concepts to create new solutions",
                "cognitive_level": "Create",
                "example": "Design a Python class that implements both iteration and context management"
            },
            "evaluation": {
                "description": "Requires judging or critiquing concepts and approaches",
                "cognitive_level": "Evaluate",
                "example": "Evaluate the pros and cons of using recursion vs iteration for this problem"
            }
        },
        "difficulty_levels": {
            1: "Very Easy - Basic recall and recognition",
            2: "Easy - Simple understanding and identification",
            3: "Medium - Application of concepts to familiar situations",
            4: "Hard - Analysis and synthesis of multiple concepts",
            5: "Very Hard - Evaluation and creation of new solutions"
        }
    }


@router.get("/health")
async def llm_health_check(
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check LLM service health and configuration
    """
    try:
        # Basic service health
        health_status = {
            "service": "llm",
            "status": "healthy" if llm_service.session and llm_service.api_key else "degraded",
            "api_configured": bool(llm_service.api_key),
            "session_active": bool(llm_service.session),
            "circuit_breaker_state": llm_service.circuit_breaker.state,
            "failure_count": llm_service.circuit_breaker.failure_count
        }
        
        # Test basic functionality if healthy
        if health_status["status"] == "healthy":
            try:
                test_result = await llm_service.generate_question(
                    chunk_content="Test content for health check",
                    concept="Health Check",
                    difficulty=1
                )
                health_status["test_generation"] = "success" if test_result.get('question') else "failed"
            except Exception as e:
                health_status["test_generation"] = f"failed: {str(e)}"
                health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {
            "service": "llm",
            "status": "error",
            "error": str(e)
        }


@router.get("/stats")
async def get_llm_stats(
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get LLM service usage statistics
    
    Requires admin permissions.
    """
    if not user.has_any_permission(["LEARNING_ADMIN"]):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    try:
        # Redis removed - skip cache statistics
        # from ..services.redis_client import redis_cache
        
        # Get cache statistics
        # cache_keys = await redis_cache.redis.keys("llm_question:*")
        cache_count = 0  # Redis removed
        
        return {
            "circuit_breaker": {
                "state": llm_service.circuit_breaker.state,
                "failure_count": llm_service.circuit_breaker.failure_count,
                "failure_threshold": llm_service.circuit_breaker.failure_threshold,
                "timeout": llm_service.circuit_breaker.timeout
            },
            "cache": {
                "cached_questions": cache_count,
                "cache_prefix": "llm_question:"
            },
            "configuration": {
                "api_gateway_configured": bool(llm_service.api_gateway_url),
                "retry_config": llm_service.retry_config,
                "timeout_seconds": llm_service.timeout.total
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get LLM stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")