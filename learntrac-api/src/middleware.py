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
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for health checks
        if request.url.path in ["/health", "/api/learntrac/health"]:
            return await call_next(request)
        
        # TODO: Implement actual authentication logic
        # For now, just pass through
        return await call_next(request)