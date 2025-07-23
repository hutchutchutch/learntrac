from fastapi import FastAPI, HTTPException, Depends, WebSocket
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import os
import logging
from typing import Optional, Dict, Any
from .auth import cognito_auth, get_current_user, get_optional_user
from .websocket_handlers import handle_audio_websocket, handle_debug_websocket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LearnTrac API",
    description="Modern Learning Management System API",
    version="1.0.0"
)

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime
    version: str
    environment: dict

@app.get("/")
async def root():
    return {"message": "Welcome to LearnTrac API", "version": "1.0.0"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for ALB"""
    return HealthResponse(
        status="healthy",
        service="learntrac-api",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        environment={
            "python_version": "3.11",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    )

@app.get("/api/learntrac/health")
async def api_health():
    """API-specific health check"""
    return {
        "status": "healthy",
        "api_version": "v1",
        "endpoints_available": [
            "/courses",
            "/users",
            "/enrollments",
            "/progress"
        ]
    }

@app.get("/api/learntrac/courses")
async def list_courses():
    """List available courses"""
    # Placeholder implementation
    return {
        "courses": [
            {"id": 1, "title": "Introduction to Python", "duration": "4 weeks"},
            {"id": 2, "title": "Advanced FastAPI", "duration": "3 weeks"},
            {"id": 3, "title": "Docker Mastery", "duration": "2 weeks"}
        ],
        "total": 3
    }

@app.post("/api/learntrac/test-data")
async def create_test_data(data: dict):
    """Test endpoint for inter-container communication"""
    return {
        "received": data,
        "processed_at": datetime.utcnow().isoformat(),
        "container": "learntrac-api"
    }

@app.get("/api/learntrac/trac-status")
async def check_trac_status():
    """Check if Trac is accessible from API container"""
    import httpx
    trac_url = os.getenv("TRAC_URL", "http://trac:8000")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(trac_url, timeout=5.0)
            return {
                "trac_accessible": True,
                "status_code": response.status_code,
                "trac_url": trac_url
            }
    except Exception as e:
        return {
            "trac_accessible": False,
            "error": str(e),
            "trac_url": trac_url
        }

@app.get("/login")
async def login():
    """Redirect to Cognito login"""
    redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8001/auth/callback")
    login_url = cognito_auth.get_login_url(redirect_uri)
    return RedirectResponse(url=login_url)

@app.get("/logout")
async def logout():
    """Redirect to Cognito logout"""
    redirect_uri = os.getenv("LOGOUT_URI", "http://localhost:8001/")
    logout_url = cognito_auth.get_logout_url(redirect_uri)
    return RedirectResponse(url=logout_url)

@app.get("/auth/callback")
async def auth_callback(code: str):
    """Handle OAuth callback from Cognito"""
    # In a real app, exchange code for tokens here
    # For now, redirect to home with a message
    return JSONResponse(
        content={
            "message": "Authentication callback received",
            "code": code,
            "next_step": "Exchange code for tokens at Cognito token endpoint"
        }
    )

@app.get("/api/learntrac/user")
async def get_user_info(user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information"""
    return {
        "username": user.get("cognito:username"),
        "email": user.get("email"),
        "groups": user.get("cognito:groups", []),
        "permissions": user.get("trac_permissions", "").split(",")
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": str(type(exc).__name__)}
    )

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/debug-console", response_class=HTMLResponse)
async def debug_console():
    """Serve the debug console interface"""
    with open("static/debug-console.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """WebSocket endpoint for audio streaming"""
    await handle_audio_websocket(websocket)

@app.websocket("/ws/debug")
async def websocket_debug_endpoint(websocket: WebSocket):
    """WebSocket endpoint for debug console"""
    await handle_debug_websocket(websocket)

@app.get("/api/speech/status")
async def speech_status():
    """Get speech processing system status"""
    from .speech_processing import speech_debugger
    return {
        "status": "operational",
        "active_sessions": len(speech_debugger.active_sessions),
        "total_events": len(speech_debugger.events),
        "subscribers": len(speech_debugger.subscribers)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)