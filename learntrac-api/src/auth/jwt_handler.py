"""
JWT Token Handler for AWS Cognito Integration
Handles JWT validation and user authentication for LearnTrac API
"""

import json
import time
from typing import Dict, List, Optional
from functools import lru_cache
import httpx
from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import logging

from ..config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()


class CognitoJWTVerifier:
    """Verifies JWT tokens from AWS Cognito"""
    
    def __init__(self):
        self.region = settings.aws_region
        self.user_pool_id = settings.cognito_pool_id
        self.client_id = settings.cognito_client_id
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        self.issuer = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
        self._jwks = None
        self._jwks_last_fetched = 0
        self._jwks_cache_duration = 3600  # 1 hour
    
    @property
    def jwks(self) -> Dict:
        """Get JWKS with caching"""
        current_time = time.time()
        if (self._jwks is None or 
            current_time - self._jwks_last_fetched > self._jwks_cache_duration):
            self._jwks = self._fetch_jwks()
            self._jwks_last_fetched = current_time
        return self._jwks
    
    def _fetch_jwks(self) -> Dict:
        """Fetch JWKS from Cognito"""
        try:
            with httpx.Client() as client:
                response = client.get(self.jwks_url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch JWKS")
    
    def _get_rsa_key(self, token: str) -> Optional[Dict]:
        """Get RSA key from JWKS based on token kid"""
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError:
            return None
        
        for key in self.jwks.get("keys", []):
            if key["kid"] == unverified_header["kid"]:
                return {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        return None
    
    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token"""
        # Get RSA key
        rsa_key = self._get_rsa_key(token)
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Unable to find appropriate key")
        
        try:
            # Verify token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"verify_exp": True}
            )
            
            # Additional validation
            if payload.get("token_use") not in ["id", "access"]:
                raise HTTPException(status_code=401, detail="Invalid token use")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.JWTClaimsError:
            raise HTTPException(status_code=401, detail="Invalid token claims")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")


# Create singleton instance
jwt_verifier = CognitoJWTVerifier()


class AuthenticatedUser:
    """Represents an authenticated user with permissions"""
    
    def __init__(self, token_payload: Dict):
        self.sub = token_payload.get("sub")
        self.username = token_payload.get("cognito:username", token_payload.get("sub"))
        self.email = token_payload.get("email")
        self.groups = token_payload.get("cognito:groups", [])
        self.permissions = self._extract_permissions(token_payload)
        self.raw_payload = token_payload
    
    def _extract_permissions(self, payload: Dict) -> List[str]:
        """Extract permissions from token payload"""
        permissions = []
        
        # Get permissions from custom claim
        trac_perms = payload.get("trac_permissions", "")
        if trac_perms:
            permissions.extend([p.strip() for p in trac_perms.split(",")])
        
        # Add group-based permissions
        group_permissions = {
            'admins': [
                'TRAC_ADMIN', 'LEARNING_ADMIN', 'COURSE_CREATE', 
                'COURSE_DELETE', 'ANALYTICS_VIEW', 'USER_MANAGE'
            ],
            'instructors': [
                'LEARNING_INSTRUCT', 'COURSE_CREATE', 'ASSIGNMENT_CREATE', 
                'ASSIGNMENT_GRADE', 'ANALYTICS_VIEW'
            ],
            'students': [
                'LEARNING_PARTICIPATE', 'ASSIGNMENT_SUBMIT', 'COURSE_ENROLL'
            ]
        }
        
        for group in self.groups:
            permissions.extend(group_permissions.get(group, []))
        
        return list(set(permissions))  # Remove duplicates
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all specified permissions"""
        return all(p in self.permissions for p in permissions)
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return 'admins' in self.groups or 'TRAC_ADMIN' in self.permissions
    
    @property
    def is_instructor(self) -> bool:
        """Check if user is instructor"""
        return 'instructors' in self.groups or 'LEARNING_INSTRUCT' in self.permissions
    
    @property
    def is_student(self) -> bool:
        """Check if user is student"""
        return 'students' in self.groups or 'LEARNING_PARTICIPATE' in self.permissions


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> AuthenticatedUser:
    """
    Dependency to get current authenticated user from JWT token
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
            return {"user": user.username}
    """
    token = credentials.credentials
    
    try:
        payload = jwt_verifier.verify_token(token)
        return AuthenticatedUser(payload)
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def require_permissions(permissions: List[str], require_all: bool = True):
    """
    Dependency factory to require specific permissions
    
    Usage:
        @router.post("/admin-only")
        async def admin_route(
            user: AuthenticatedUser = Depends(require_permissions(["TRAC_ADMIN"]))
        ):
            return {"message": "Admin access granted"}
    """
    async def permission_checker(
        user: AuthenticatedUser = Security(get_current_user)
    ) -> AuthenticatedUser:
        if require_all:
            if not user.has_all_permissions(permissions):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Missing required permissions: {permissions}"
                )
        else:
            if not user.has_any_permission(permissions):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Missing any of required permissions: {permissions}"
                )
        return user
    
    return permission_checker


# Convenience dependencies
require_admin = require_permissions(["TRAC_ADMIN", "LEARNING_ADMIN"], require_all=False)
require_instructor = require_permissions(["LEARNING_INSTRUCT"])
require_student = require_permissions(["LEARNING_PARTICIPATE"])