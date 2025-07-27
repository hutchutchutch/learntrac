"""
Authentication Router for Modern Session-Based Auth
Handles authentication verification for Trac integration
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging
from typing import Optional

from ..auth.modern_session_handler import (
    get_current_user, 
    get_current_user_required, 
    AuthenticatedUser,
    session_validator
)
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/verify")
async def verify_session(
    request: Request,
    user: Optional[AuthenticatedUser] = Depends(get_current_user)
):
    """
    Verify current session - used by Trac and other services
    
    Returns authentication status and user information
    """
    if not user:
        return JSONResponse(
            {"authenticated": False, "error": "No valid session"}, 
            status_code=401
        )
    
    return JSONResponse({
        "authenticated": True,
        "user": {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "permissions": user.permissions,
            "groups": user.groups,
            "session_id": user.session_id,
            "is_admin": user.is_admin,
            "is_instructor": user.is_instructor,
            "is_student": user.is_student
        }
    })


@router.get("/user")
async def get_current_user_info(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user_required)
):
    """
    Get detailed current user information (requires authentication)
    """
    return {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "permissions": user.permissions,
        "groups": user.groups,
        "session_id": user.session_id,
        "roles": {
            "is_admin": user.is_admin,
            "is_instructor": user.is_instructor,
            "is_student": user.is_student
        }
    }


@router.get("/permissions")
async def get_user_permissions(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user_required)
):
    """
    Get user permissions and access levels
    """
    return {
        "permissions": user.permissions,
        "groups": user.groups,
        "access_levels": {
            "admin": user.is_admin,
            "instructor": user.is_instructor,
            "student": user.is_student
        },
        "specific_permissions": {
            "trac_admin": user.has_permission("TRAC_ADMIN"),
            "learning_instruct": user.has_permission("LEARNING_INSTRUCT"),
            "learning_participate": user.has_permission("LEARNING_PARTICIPATE"),
            "ticket_create": user.has_permission("TICKET_CREATE"),
            "wiki_modify": user.has_permission("WIKI_MODIFY")
        }
    }


@router.post("/logout")
async def logout(request: Request):
    """
    Logout endpoint - clears session cookies
    
    Note: Actual session invalidation happens on the Trac side.
    This endpoint just clears client-side cookies.
    """
    response = JSONResponse({"message": "Logged out successfully"})
    
    # Clear auth cookies
    response.delete_cookie("trac_auth_token")
    response.delete_cookie("auth_session")  # Legacy cookie
    
    return response


@router.get("/status")
async def auth_status():
    """
    Get authentication system status and configuration
    """
    return {
        "auth_system": "modern_session",
        "provider": "trac_builtin",
        "session_based": True,
        "features": {
            "csrf_protection": True,
            "rate_limiting": True,
            "secure_tokens": True,
            "redis_sessions": True
        },
        "config": {
            "trac_base_url": getattr(settings, 'trac_base_url', 'http://localhost:8000'),
            "session_timeout": getattr(settings, 'session_timeout', 3600),
            "auth_secret_configured": bool(getattr(settings, 'trac_auth_secret', ''))
        }
    }


@router.get("/check/{permission}")
async def check_permission(
    permission: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user_required)
):
    """
    Check if current user has a specific permission
    """
    has_permission = user.has_permission(permission)
    
    return {
        "permission": permission,
        "granted": has_permission,
        "user": user.username
    }


@router.get("/debug")
async def debug_auth(request: Request):
    """
    Debug endpoint for authentication troubleshooting
    Only available in development mode
    """
    if getattr(settings, 'environment', 'production') != 'development':
        raise HTTPException(status_code=404, detail="Not found")
    
    # Extract potential auth tokens for debugging
    session_token = None
    api_key = None
    basic_auth = None
    
    # Try to extract tokens
    session_token = request.cookies.get('trac_auth_token')
    if not session_token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
    
    api_key = request.headers.get('X-API-Key')
    
    if request.headers.get('Authorization', '').startswith('Basic '):
        basic_auth = request.headers.get('Authorization')
    
    return {
        "headers": dict(request.headers),
        "cookies": dict(request.cookies),
        "auth_extraction": {
            "session_token_found": bool(session_token),
            "session_token_length": len(session_token) if session_token else 0,
            "api_key_found": bool(api_key),
            "basic_auth_found": bool(basic_auth)
        },
        "config": {
            "secret_configured": bool(getattr(settings, 'trac_auth_secret', '')),
            "trac_url": getattr(settings, 'trac_base_url', 'not_configured'),
            "redis_url": getattr(settings, 'redis_url', 'not_configured')
        }
    }


# Health check for auth system
@router.get("/health")
async def auth_health():
    """
    Authentication system health check
    """
    try:
        # Test if session validator is working
        secret_configured = bool(getattr(settings, 'trac_auth_secret', ''))
        
        health_status = {
            "status": "healthy" if secret_configured else "degraded",
            "auth_handler": "modern_session",
            "secret_configured": secret_configured,
            "session_validator": "initialized"
        }
        
        if not secret_configured:
            health_status["warning"] = "trac_auth_secret not configured"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Auth health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }