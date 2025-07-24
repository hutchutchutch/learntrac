"""
TracLearn FastAPI Application
Main entry point for the Python 3.11 API service
"""

from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router
from app.middleware.auth import AuthMiddleware
from app.middleware.logging import LoggingMiddleware
from app.core.exceptions import TracLearnException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print(f"Starting TracLearn API v{settings.VERSION}")
    await init_db()
    yield
    # Shutdown
    print("Shutting down TracLearn API")


# Create FastAPI app
app = FastAPI(
    title="TracLearn API",
    description="Educational Learning Management API for Trac",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(AuthMiddleware)
app.add_middleware(LoggingMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Root endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint"""
    return {
        "message": "TracLearn API Service",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "service": "traclearn-api"
    }


# Version endpoint
@app.get("/version")
async def version() -> Dict[str, Any]:
    """Get API version information"""
    return {
        "version": settings.VERSION,
        "api_version": "v1",
        "python_version": "3.11"
    }


# Global exception handler
@app.exception_handler(TracLearnException)
async def traclearn_exception_handler(
    request: Request, 
    exc: TracLearnException
) -> JSONResponse:
    """Handle TracLearn custom exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


# Generic exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.DEBUG else None
        }
    )


if __name__ == "__main__":
    # Run with uvicorn for development
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )