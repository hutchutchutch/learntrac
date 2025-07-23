from fastapi import FastAPI
import os
import socket
from datetime import datetime

app = FastAPI(title="LearnTrac Test API")

@app.get("/api/learntrac/health")
def health():
    """Health check endpoint expected by ALB"""
    return {
        "status": "healthy",
        "service": "learntrac-test",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
def root():
    return {
        "service": "learntrac-test",
        "version": "test",
        "hostname": socket.gethostname(),
        "environment": os.environ.get("ENVIRONMENT", "unknown")
    }

@app.get("/api/learntrac/info")
def info():
    return {
        "name": "LearnTrac Test Container",
        "description": "Test container for LearnTrac API",
        "endpoints": [
            "/api/learntrac/health",
            "/api/learntrac/info",
            "/api/chat/test",
            "/api/voice/test",
            "/api/analytics/test"
        ]
    }

@app.get("/api/chat/test")
def chat_test():
    return {"endpoint": "chat", "status": "test endpoint active"}

@app.get("/api/voice/test")
def voice_test():
    return {"endpoint": "voice", "status": "test endpoint active"}

@app.get("/api/analytics/test")
def analytics_test():
    return {"endpoint": "analytics", "status": "test endpoint active"}