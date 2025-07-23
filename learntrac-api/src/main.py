from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
from redis import asyncio as aioredis
from neo4j import AsyncGraphDatabase
import logging
import os

from .config import settings
from .routers import learning, chat, analytics, voice
from .middleware import TimingMiddleware, AuthMiddleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting LearnTrac API..."
    
    # Initialize database pool
    app.state.db_pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=10,
        max_size=20,
        command_timeout=60
    )
    
    # Initialize Redis
    app.state.redis = await aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    
    # Initialize Neo4j (only if URL is provided)
    if settings.neo4j_url:
        app.state.neo4j = AsyncGraphDatabase.driver(
            settings.neo4j_url,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
    else:
        app.state.neo4j = None
    
    logger.info("LearnTrac API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LearnTrac API..."
    await app.state.db_pool.close()
    await app.state.redis.close()
    if app.state.neo4j:
        await app.state.neo4j.close()

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
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        async with app.state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Check Redis
        await app.state.redis.ping()
        
        # Check Neo4j (optional)
        neo4j_status = "not_configured"
        if app.state.neo4j:
            async with app.state.neo4j.session() as session:
                await session.run("RETURN 1")
                neo4j_status = "healthy"
        
        return {
            "status": "healthy",
            "version": "1.0.0",
            "python_version": "3.11",
            "neo4j": neo4j_status
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