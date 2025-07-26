from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from .config import settings
from .routers import learning, chat, analytics, voice, vector_search, llm, tickets, evaluation, trac
from .middleware import TimingMiddleware, AuthMiddleware
from .db.database import db_manager
from .services.redis_client import redis_cache
from .services.neo4j_client import neo4j_client
from .services.neo4j_aura_client import neo4j_aura_client
from .services.embedding_service import embedding_service
from .services.generation_service import generation_service
from .services.llm_service import llm_service
from .services.ticket_service import ticket_service
from .services.evaluation_service import evaluation_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting LearnTrac API...")
    
    # Initialize database
    await db_manager.initialize()
    app.state.db_manager = db_manager
    
    # Initialize Redis
    await redis_cache.initialize()
    app.state.redis_cache = redis_cache
    
    # Initialize Neo4j (only if URI is provided)
    await neo4j_client.initialize()
    app.state.neo4j_client = neo4j_client
    
    # Initialize Neo4j Aura client for vector search
    app.state.neo4j_aura_client = neo4j_aura_client
    
    # Initialize embedding service
    await embedding_service.initialize()
    app.state.embedding_service = embedding_service
    
    # Initialize generation service
    await generation_service.initialize()
    app.state.generation_service = generation_service
    
    # Initialize LLM service
    await llm_service.initialize()
    app.state.llm_service = llm_service
    
    # Initialize ticket service
    await ticket_service.initialize()
    app.state.ticket_service = ticket_service
    
    # Initialize evaluation service
    await evaluation_service.initialize(db_manager.pool)
    app.state.evaluation_service = evaluation_service
    
    logger.info("LearnTrac API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LearnTrac API...")
    await db_manager.close()
    await redis_cache.close()
    await neo4j_client.close()
    await neo4j_aura_client.close()
    await llm_service.close()
    await ticket_service.close()

app = FastAPI(
    title="LearnTrac API",
    description="Modern learning features for Trac",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(TimingMiddleware)
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(learning.router, prefix="/api/learntrac", tags=["learning"])
app.include_router(vector_search.router, prefix="/api/learntrac/vector", tags=["vector-search"])
app.include_router(llm.router, prefix="/api/learntrac/llm", tags=["llm"])
app.include_router(tickets.router, prefix="/api/learntrac/tickets", tags=["tickets"])
app.include_router(evaluation.router, prefix="/api/learntrac/evaluation", tags=["evaluation"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(trac.router)  # Main Trac integration router

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        await db_manager.execute_query("SELECT 1")
        db_status = "healthy"
        
        # Check Redis
        await redis_cache.redis.ping()
        redis_status = "healthy"
        
        # Check Neo4j (optional)
        neo4j_status = "not_configured"
        if neo4j_client._initialized:
            neo4j_status = "healthy"
        
        # Check LLM service
        llm_status = "not_configured"
        if llm_service.session and llm_service.api_key:
            llm_status = "healthy"
        elif llm_service.api_key:
            llm_status = "degraded"
        
        # Check ticket service
        ticket_status = "healthy" if ticket_service.db_pool else "not_configured"
        
        # Check evaluation service
        evaluation_status = "healthy" if evaluation_service.db_pool else "not_configured"
        
        return {
            "status": "healthy",
            "version": "1.0.0",
            "components": {
                "database": db_status,
                "redis": redis_status,
                "neo4j": neo4j_status,
                "llm": llm_status,
                "tickets": ticket_status,
                "evaluation": evaluation_status
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/api/learntrac/health")
async def api_health():
    """LearnTrac-specific health check"
    return {
        "status": "healthy",
        "service": "learntrac-api",
        "features": {
            "learning": "enabled",
            "chat": "enabled",
            "voice": "enabled",
            "analytics": "enabled"
        }
    }