from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LearnTrac API",
    description="Modern learning features for Trac",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "python_version": "3.11",
        "service": "learntrac-api"
    }

@app.get("/api/learntrac/health")
async def api_health():
    """LearnTrac-specific health check"""
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to LearnTrac API",
        "docs": "/docs",
        "health": "/health"
    }