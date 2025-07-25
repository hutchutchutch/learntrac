from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request timing"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(f"{request.method} {request.url.path} - {process_time:.3f}s")
        
        return response

class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication handling"""
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = [
        "/health",
        "/api/learntrac/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for public endpoints
        if any(request.url.path.startswith(path) for path in self.PUBLIC_PATHS):
            return await call_next(request)
        
        # For protected endpoints, authentication is handled by FastAPI dependencies
        # This middleware just adds CORS and security headers
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response