"""AWS Cognito authentication for LearnTrac API"""
import os
import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from datetime import datetime

security = HTTPBearer()

class CognitoAuth:
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-2")
        self.user_pool_id = os.getenv("COGNITO_POOL_ID")
        self.client_id = os.getenv("COGNITO_CLIENT_ID")
        self.cognito_domain = os.getenv("COGNITO_DOMAIN", "hutch-learntrac-dev-auth")
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        self._jwks = None
    
    async def get_jwks(self):
        """Get JSON Web Key Set from Cognito"""
        if not self._jwks:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                self._jwks = response.json()
        return self._jwks
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token from Cognito"""
        try:
            # Decode token header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            # Get JWKS
            jwks = await self.get_jwks()
            
            # Find the key
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key"
                )
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            )
            
            # Check token expiration
            if payload.get("exp", 0) < datetime.now().timestamp():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            return payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def get_login_url(self, redirect_uri: str) -> str:
        """Get Cognito login URL"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "email openid profile",
            "redirect_uri": redirect_uri
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/login?{query_string}"
    
    def get_logout_url(self, redirect_uri: str) -> str:
        """Get Cognito logout URL"""
        params = {
            "client_id": self.client_id,
            "logout_uri": redirect_uri
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/logout?{query_string}"

# Initialize auth
cognito_auth = CognitoAuth()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current user from JWT token"""
    token = credentials.credentials
    user_info = await cognito_auth.verify_token(token)
    return user_info

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise None"""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None