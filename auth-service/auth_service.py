#!/usr/bin/env python3
"""
Authentication Service API
Handles Cognito authentication for Trac
"""

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import jwt
from jwt import PyJWKClient
import os
import logging
from datetime import datetime, timedelta
import json
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trac Auth Service")

# Configuration from environment
COGNITO_REGION = os.getenv("COGNITO_REGION", "us-east-2")
COGNITO_DOMAIN = os.getenv("COGNITO_DOMAIN", "hutch-learntrac-dev-auth")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "5adkv019v4rcu6o87ffg46ep02")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "us-east-2_IvxzMrWwg")
TRAC_BASE_URL = os.getenv("TRAC_BASE_URL", "http://localhost:8000")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

# Cognito URLs
COGNITO_BASE_URL = f"https://{COGNITO_DOMAIN}.auth.{COGNITO_REGION}.amazoncognito.com"
JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"

# JWT validation
jwks_client = PyJWKClient(JWKS_URL)

# Session storage (in production, use Redis)
sessions = {}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Trac Auth Service"}


@app.get("/auth/login")
async def login(redirect: Optional[str] = "/trac/wiki"):
    """Redirect to Cognito login"""
    redirect_uri = f"{AUTH_SERVICE_URL}/auth/callback"
    
    params = {
        "response_type": "code",
        "client_id": COGNITO_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": redirect  # Pass the original destination
    }
    
    auth_url = f"{COGNITO_BASE_URL}/login"
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    
    logger.info(f"Redirecting to Cognito: {auth_url}?{query_string}")
    return RedirectResponse(url=f"{auth_url}?{query_string}")


@app.get("/auth/callback")
async def callback(request: Request, code: Optional[str] = None, state: Optional[str] = "/trac/wiki"):
    """Handle Cognito callback"""
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")
    
    # Exchange code for tokens
    token_url = f"{COGNITO_BASE_URL}/oauth2/token"
    redirect_uri = f"{AUTH_SERVICE_URL}/auth/callback"
    
    data = {
        "grant_type": "authorization_code",
        "client_id": COGNITO_CLIENT_ID,
        "code": code,
        "redirect_uri": redirect_uri
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise HTTPException(status_code=400, detail="Token exchange failed")
        
        tokens = response.json()
    
    # Decode ID token to get user info
    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="No ID token received")
    
    try:
        # Get the signing key from Cognito
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        
        # Decode and validate the token
        user_info = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID
        )
        
        # Create session
        session_id = os.urandom(32).hex()
        sessions[session_id] = {
            "user": user_info.get("email", user_info.get("cognito:username")),
            "tokens": tokens,
            "expires": datetime.utcnow() + timedelta(hours=1)
        }
        
        # Redirect to Trac with session cookie
        response = RedirectResponse(url=f"{TRAC_BASE_URL}{state}")
        response.set_cookie(
            key="auth_session",
            value=session_id,
            max_age=3600,
            httponly=True,
            samesite="lax"
        )
        
        logger.info(f"User {user_info.get('email')} authenticated successfully")
        return response
        
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid token")


@app.get("/auth/verify")
async def verify(request: Request):
    """Verify session for Trac"""
    session_id = request.cookies.get("auth_session")
    
    if not session_id or session_id not in sessions:
        return JSONResponse({"authenticated": False}, status_code=401)
    
    session = sessions[session_id]
    
    # Check expiration
    if datetime.utcnow() > session["expires"]:
        del sessions[session_id]
        return JSONResponse({"authenticated": False}, status_code=401)
    
    return JSONResponse({
        "authenticated": True,
        "user": session["user"]
    })


@app.get("/auth/logout")
async def logout(request: Request):
    """Logout user"""
    session_id = request.cookies.get("auth_session")
    
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    # Redirect to Cognito logout
    logout_uri = f"{AUTH_SERVICE_URL}/"
    cognito_logout = f"{COGNITO_BASE_URL}/logout?client_id={COGNITO_CLIENT_ID}&logout_uri={logout_uri}"
    
    response = RedirectResponse(url=cognito_logout)
    response.delete_cookie("auth_session")
    
    return response


@app.get("/auth/user")
async def get_user(request: Request):
    """Get current user info"""
    session_id = request.cookies.get("auth_session")
    
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = sessions[session_id]
    
    # Check expiration
    if datetime.utcnow() > session["expires"]:
        del sessions[session_id]
        raise HTTPException(status_code=401, detail="Session expired")
    
    return {"user": session["user"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)