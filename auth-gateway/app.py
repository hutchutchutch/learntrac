from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
import secrets
import jwt
import os
from datetime import datetime, timedelta

app = FastAPI()

COGNITO_DOMAIN = "hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com"
COGNITO_REGION = "us-east-2"
USER_POOL_ID = "us-east-2_1AzmDXp0K"
CLIENT_ID = "47puc5a858179his8g5f60ij4h"
CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost/auth/callback"

# Session storage (use Redis in production)
sessions = {}

@app.get("/auth/login")
async def login(request: Request):
    state = secrets.token_urlsafe(32)
    # Store state in session
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {"state": state, "created": datetime.utcnow()}
    
    auth_url = (
        f"https://{COGNITO_DOMAIN}/oauth2/authorize?"
        f"client_id={CLIENT_ID}&"
        f"response_type=code&"
        f"scope=email+openid+profile&"
        f"redirect_uri={REDIRECT_URI}&"
        f"state={state}"
    )
    
    response = RedirectResponse(url=auth_url)
    response.set_cookie("auth_session", session_id, httponly=True)
    return response

@app.get("/auth/callback")
async def callback(request: Request, code: str = None, state: str = None):
    if not code:
        return HTMLResponse("No authorization code received", status_code=400)
    
    # Verify state
    session_id = request.cookies.get("auth_session")
    if not session_id or session_id not in sessions:
        return HTMLResponse("Invalid session", status_code=400)
    
    session = sessions.get(session_id)
    if session["state"] != state:
        return HTMLResponse("Invalid state", status_code=400)
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"https://{COGNITO_DOMAIN}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
    
    if token_response.status_code != 200:
        return HTMLResponse(f"Token exchange failed: {token_response.text}", status_code=500)
    
    tokens = token_response.json()
    
    # Decode ID token (without verification for now)
    id_token = tokens.get("id_token")
    claims = jwt.decode(id_token, options={"verify_signature": False})
    
    # Store user info in session
    sessions[session_id]["user"] = {
        "username": claims.get("cognito:username", claims.get("email")),
        "email": claims.get("email"),
        "groups": claims.get("cognito:groups", [])
    }
    
    # Redirect to Trac with session
    response = RedirectResponse(url="/projects/wiki/LearnTrac")
    response.set_cookie("auth_user", claims.get("email"), httponly=True)
    return response

@app.get("/auth/user")
async def get_user(request: Request):
    session_id = request.cookies.get("auth_session")
    if session_id and session_id in sessions:
        return sessions[session_id].get("user", {})
    return {}

@app.get("/auth/logout")
async def logout(request: Request):
    session_id = request.cookies.get("auth_session")
    if session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url="/")
    response.delete_cookie("auth_session")
    response.delete_cookie("auth_user")
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)