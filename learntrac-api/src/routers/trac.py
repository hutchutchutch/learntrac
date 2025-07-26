"""
Trac Integration REST API Endpoints

Provides comprehensive REST API for Trac educational features including:
- Textbook management
- Content search
- Learning progress tracking
- User authentication
- Recommendations
- Analytics
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
import aiofiles
import os
import tempfile

from ..services.trac_service import TracService
from ..services.auth_service import AuthService, User
from ..db.database import DatabaseManager
from ..services.redis_client import RedisCache
from ..services.embedding_service import EmbeddingService
from ..pdf_processing.neo4j_connection_manager import ConnectionConfig

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/trac", tags=["trac"])

# Security
security = HTTPBearer()

# ===== Request/Response Models =====

class UserRegistration(BaseModel):
    """User registration request"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="student", pattern="^(student|instructor|admin)$")


class UserLogin(BaseModel):
    """User login request"""
    email_or_username: str
    password: str


class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserProfile(BaseModel):
    """User profile response"""
    id: str
    email: str
    username: str
    full_name: str
    role: str
    level: str
    interests: List[str]
    total_time_minutes: int
    concepts_mastered: List[str]
    created_at: datetime


class TextbookUpload(BaseModel):
    """Textbook upload metadata"""
    title: str
    subject: str
    authors: List[str] = []
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None


class ContentSearch(BaseModel):
    """Content search request"""
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    """Search result item"""
    chunk_id: str
    score: float
    text: str
    textbook_title: str
    chapter_title: str
    section_title: Optional[str]
    concepts: List[str]
    difficulty: float
    explanation: str


class LearningProgress(BaseModel):
    """Learning progress update"""
    chunk_id: str
    time_spent_seconds: int = Field(ge=0)
    understanding_level: float = Field(ge=0, le=1)


class LearningProgressResponse(BaseModel):
    """Learning progress response"""
    concept_id: str
    concept_name: str
    understanding_level: float
    time_spent_minutes: int
    last_accessed: datetime
    completed_chunks: List[str]
    mastery_score: float


class RecommendationResponse(BaseModel):
    """Content recommendation"""
    chunk_id: str
    score: float
    reason: str
    concept: str
    difficulty: float
    estimated_time_minutes: int
    prerequisites_met: bool


class LearningPathRequest(BaseModel):
    """Learning path creation request"""
    target_concepts: List[str]
    time_limit_hours: Optional[int] = None


class LearningPathResponse(BaseModel):
    """Learning path response"""
    path_id: str
    segments: int
    total_chunks: int
    estimated_time_hours: float
    target_concepts: List[str]


# ===== Dependencies =====

async def get_trac_service(
    request: Any = Depends()
) -> TracService:
    """Get Trac service instance"""
    app = request.app
    
    # Get dependencies
    db_manager = app.state.db_manager
    redis_cache = app.state.redis_cache
    embedding_service = app.state.embedding_service
    
    # Create Neo4j config
    neo4j_config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    # Create service
    service = TracService(
        db_manager,
        neo4j_config,
        redis_cache,
        embedding_service
    )
    
    # Initialize if needed
    if not service._initialized:
        await service.initialize()
    
    return service


async def get_auth_service(
    request: Any = Depends()
) -> AuthService:
    """Get auth service instance"""
    app = request.app
    
    # Get dependencies
    db_manager = app.state.db_manager
    redis_cache = app.state.redis_cache
    
    # Create service
    service = AuthService(db_manager, redis_cache)
    
    # Initialize if needed
    if not service._initialized:
        await service.initialize()
    
    return service


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    
    # Check if token is blacklisted
    if await auth_service.is_token_blacklisted(token):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    
    # Verify token
    payload = await auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get user
    user = await auth_service.get_user(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user


# ===== Authentication Endpoints =====

@router.post("/auth/register", response_model=UserProfile)
async def register(
    registration: UserRegistration,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user"""
    user = await auth_service.register_user(
        email=registration.email,
        username=registration.username,
        password=registration.password,
        full_name=registration.full_name,
        role=registration.role
    )
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="User with this email or username already exists"
        )
    
    return UserProfile(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        level="beginner",
        interests=[],
        total_time_minutes=0,
        concepts_mastered=[],
        created_at=user.created_at
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login and get authentication tokens"""
    user = await auth_service.authenticate_user(
        login_data.email_or_username,
        login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
    
    # Create tokens
    tokens = await auth_service.create_tokens(user)
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh authentication tokens"""
    tokens = await auth_service.refresh_tokens(refresh_token)
    
    if not tokens:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in
    )


@router.post("/auth/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout and revoke current token"""
    await auth_service.revoke_token(credentials.credentials)
    return {"message": "Logged out successfully"}


# ===== User Profile Endpoints =====

@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """Get current user's profile"""
    profile = await trac_service.get_user_profile(current_user.id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return UserProfile(
        id=profile.user_id,
        email=profile.email,
        username=current_user.username,
        full_name=profile.name,
        role=current_user.role,
        level=profile.level,
        interests=profile.interests,
        total_time_minutes=profile.total_time_minutes,
        concepts_mastered=profile.concepts_mastered,
        created_at=current_user.created_at
    )


@router.put("/profile")
async def update_profile(
    updates: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update user profile"""
    allowed_fields = ["full_name", "interests", "level", "preferences"]
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    success = await auth_service.update_user(current_user.id, **filtered_updates)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update profile")
    
    return {"message": "Profile updated successfully"}


# ===== Textbook Management Endpoints =====

@router.post("/textbooks/upload")
async def upload_textbook(
    file: UploadFile = File(...),
    metadata: TextbookUpload = Depends(),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    trac_service: TracService = Depends(get_trac_service)
):
    """Upload and process a textbook PDF"""
    # Check permission
    if not await auth_service.check_permission(
        current_user.id, "textbook", "create"
    ):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to upload textbooks"
        )
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    # Save uploaded file temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            await aiofiles.write(tmp_file.name, content)
            temp_path = tmp_file.name
        
        # Create metadata
        from ..pdf_processing.neo4j_content_ingestion import TextbookMetadata
        
        textbook_metadata = TextbookMetadata(
            textbook_id="",  # Will be generated
            title=metadata.title,
            subject=metadata.subject,
            authors=metadata.authors,
            source_file=file.filename,
            processing_date=datetime.utcnow(),
            processing_version="1.0",
            quality_metrics={},
            statistics={}
        )
        
        # Process textbook
        result = await trac_service.ingest_textbook(temp_path, textbook_metadata)
        
        return result
        
    finally:
        # Clean up temp file
        if 'temp_path' in locals():
            os.unlink(temp_path)


@router.get("/textbooks")
async def list_textbooks(
    subject: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """List available textbooks"""
    # Query textbooks from Neo4j
    query = """
        MATCH (t:Textbook)
        WHERE $subject IS NULL OR t.subject = $subject
        RETURN t
        ORDER BY t.title
        SKIP $offset LIMIT $limit
    """
    
    results = await trac_service.neo4j_connection.execute_query(
        query,
        {"subject": subject, "offset": offset, "limit": limit}
    )
    
    textbooks = []
    for record in results:
        t = record["t"]
        textbooks.append({
            "textbook_id": t["textbook_id"],
            "title": t["title"],
            "subject": t["subject"],
            "authors": t.get("authors", []),
            "quality_score": t.get("overall_quality", 0),
            "chapters": t.get("total_chapters", 0),
            "processing_date": t.get("processing_date")
        })
    
    return {"textbooks": textbooks, "total": len(textbooks)}


# ===== Content Search Endpoints =====

@router.post("/search", response_model=List[SearchResult])
async def search_content(
    search_request: ContentSearch,
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """Search educational content"""
    results = await trac_service.search_content(
        query=search_request.query,
        user_id=current_user.id,
        filters=search_request.filters,
        limit=search_request.limit
    )
    
    return [
        SearchResult(
            chunk_id=r.chunk_id,
            score=r.score,
            text=r.text[:500] + "..." if len(r.text) > 500 else r.text,
            textbook_title=r.textbook_title,
            chapter_title=r.chapter_title,
            section_title=r.section_title,
            concepts=r.concepts[:5],  # Limit concepts
            difficulty=r.chunk_metadata.difficulty,
            explanation=r.explanation
        )
        for r in results.results
    ]


@router.get("/content/{chunk_id}")
async def get_content(
    chunk_id: str,
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """Get specific content chunk"""
    query = """
        MATCH (c:Chunk {chunk_id: $chunk_id})
        OPTIONAL MATCH (c)-[:BELONGS_TO_TEXTBOOK]->(t:Textbook)
        OPTIONAL MATCH (c)-[:BELONGS_TO_CHAPTER]->(ch:Chapter)
        OPTIONAL MATCH (c)-[:BELONGS_TO_SECTION]->(s:Section)
        OPTIONAL MATCH (c)-[:MENTIONS_CONCEPT]->(concept:Concept)
        RETURN c, t.title as textbook, ch.title as chapter, 
               s.title as section, collect(concept.name) as concepts
    """
    
    results = await trac_service.neo4j_connection.execute_query(
        query,
        {"chunk_id": chunk_id}
    )
    
    if not results:
        raise HTTPException(status_code=404, detail="Content not found")
    
    record = results[0]
    chunk = record["c"]
    
    return {
        "chunk_id": chunk["chunk_id"],
        "text": chunk["text"],
        "content_type": chunk["content_type"],
        "difficulty": chunk.get("difficulty_score", 0.5),
        "textbook": record["textbook"],
        "chapter": record["chapter"],
        "section": record["section"],
        "concepts": record["concepts"],
        "metadata": {
            "word_count": chunk.get("word_count", 0),
            "confidence_score": chunk.get("confidence_score", 0)
        }
    }


# ===== Learning Progress Endpoints =====

@router.post("/progress/track")
async def track_progress(
    progress: LearningProgress,
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """Track learning progress"""
    success = await trac_service.track_learning_progress(
        user_id=current_user.id,
        chunk_id=progress.chunk_id,
        time_spent_seconds=progress.time_spent_seconds,
        understanding_level=progress.understanding_level
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to track progress"
        )
    
    return {"message": "Progress tracked successfully"}


@router.get("/progress", response_model=List[LearningProgressResponse])
async def get_progress(
    concept_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """Get learning progress"""
    progress_list = await trac_service.get_learning_progress(
        user_id=current_user.id,
        concept_id=concept_id
    )
    
    return [
        LearningProgressResponse(
            concept_id=p.concept_id,
            concept_name=p.concept_name,
            understanding_level=p.understanding_level,
            time_spent_minutes=p.time_spent_minutes,
            last_accessed=p.last_accessed,
            completed_chunks=p.completed_chunks,
            mastery_score=p.mastery_score
        )
        for p in progress_list
    ]


# ===== Recommendations Endpoints =====

@router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """Get personalized content recommendations"""
    recommendations = await trac_service.get_recommendations(
        user_id=current_user.id,
        limit=limit
    )
    
    return [
        RecommendationResponse(
            chunk_id=r.chunk_id,
            score=r.score,
            reason=r.reason,
            concept=r.concept,
            difficulty=r.difficulty,
            estimated_time_minutes=r.estimated_time_minutes,
            prerequisites_met=r.prerequisites_met
        )
        for r in recommendations
    ]


# ===== Learning Path Endpoints =====

@router.post("/learning-paths", response_model=LearningPathResponse)
async def create_learning_path(
    request: LearningPathRequest,
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """Create a personalized learning path"""
    result = await trac_service.create_learning_path(
        user_id=current_user.id,
        target_concepts=request.target_concepts,
        time_limit_hours=request.time_limit_hours
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return LearningPathResponse(**result)


@router.get("/learning-paths/current")
async def get_current_learning_path(
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """Get current learning path"""
    profile = await trac_service.get_user_profile(current_user.id)
    
    if not profile or not profile.current_learning_path:
        raise HTTPException(
            status_code=404,
            detail="No active learning path"
        )
    
    # Get learning path details
    path_data = await trac_service.db_manager.fetch_one(
        """
        SELECT * FROM learning_paths
        WHERE path_id = $1 AND user_id = $2
        """,
        profile.current_learning_path,
        current_user.id
    )
    
    if not path_data:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    return {
        "path_id": path_data["path_id"],
        "target_concepts": path_data["target_concepts"],
        "segments": path_data["segments"],
        "created_at": path_data["created_at"],
        "progress": await _calculate_path_progress(
            path_data["segments"],
            current_user.id,
            trac_service
        )
    }


# ===== Analytics Endpoints =====

@router.get("/analytics/overview")
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    trac_service: TracService = Depends(get_trac_service)
):
    """Get learning analytics overview"""
    profile = await trac_service.get_user_profile(current_user.id)
    progress_list = await trac_service.get_learning_progress(current_user.id)
    
    # Calculate statistics
    total_concepts = len(progress_list)
    mastered_concepts = len([p for p in progress_list if p.mastery_score >= 0.8])
    avg_understanding = sum(p.understanding_level for p in progress_list) / total_concepts if total_concepts > 0 else 0
    
    return {
        "user_level": profile.level if profile else "beginner",
        "total_time_hours": profile.total_time_minutes / 60 if profile else 0,
        "total_concepts_studied": total_concepts,
        "concepts_mastered": mastered_concepts,
        "average_understanding": avg_understanding,
        "learning_streak_days": await _calculate_learning_streak(current_user.id, trac_service),
        "recent_activity": await _get_recent_activity(current_user.id, trac_service)
    }


# ===== Helper Functions =====

async def _calculate_path_progress(
    segments: Dict[str, Any],
    user_id: str,
    trac_service: TracService
) -> Dict[str, Any]:
    """Calculate learning path progress"""
    total_chunks = 0
    completed_chunks = 0
    
    for segment in segments:
        total_chunks += len(segment["chunks"])
        
        # Check which chunks are completed
        for chunk_id in segment["chunks"]:
            progress = await trac_service.db_manager.fetch_one(
                """
                SELECT understanding_level
                FROM user_learning_progress
                WHERE user_id = $1 AND chunk_id = $2
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                user_id, chunk_id
            )
            
            if progress and progress["understanding_level"] >= 0.7:
                completed_chunks += 1
    
    return {
        "total_chunks": total_chunks,
        "completed_chunks": completed_chunks,
        "percentage": (completed_chunks / total_chunks * 100) if total_chunks > 0 else 0
    }


async def _calculate_learning_streak(
    user_id: str,
    trac_service: TracService
) -> int:
    """Calculate consecutive days of learning"""
    results = await trac_service.db_manager.fetch_all(
        """
        SELECT DISTINCT DATE(timestamp) as learning_date
        FROM user_learning_progress
        WHERE user_id = $1
        AND timestamp > NOW() - INTERVAL '30 days'
        ORDER BY learning_date DESC
        """,
        user_id
    )
    
    if not results:
        return 0
    
    # Calculate streak
    streak = 1
    for i in range(1, len(results)):
        if (results[i-1]["learning_date"] - results[i]["learning_date"]).days == 1:
            streak += 1
        else:
            break
    
    return streak


async def _get_recent_activity(
    user_id: str,
    trac_service: TracService,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get recent learning activity"""
    results = await trac_service.db_manager.fetch_all(
        """
        SELECT 
            ulp.chunk_id,
            ulp.timestamp,
            ulp.understanding_level,
            c.concepts
        FROM user_learning_progress ulp
        JOIN chunks c ON c.chunk_id = ulp.chunk_id
        WHERE ulp.user_id = $1
        ORDER BY ulp.timestamp DESC
        LIMIT $2
        """,
        user_id, limit
    )
    
    return [
        {
            "chunk_id": r["chunk_id"],
            "timestamp": r["timestamp"],
            "understanding_level": r["understanding_level"],
            "concepts": r["concepts"][:3]  # Limit concepts
        }
        for r in results
    ]