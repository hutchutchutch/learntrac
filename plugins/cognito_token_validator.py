import jwt
from jwt import PyJWKClient
import time
from functools import lru_cache
from trac.core import Component, TracError
import requests
import json

class CognitoTokenValidator(Component):
    """Validates AWS Cognito JWT tokens with cryptographic verification"""
    
    def __init__(self):
        super().__init__()
        self.region = self.config.get('cognito', 'region', 'us-east-2')
        self.user_pool_id = self.config.get('cognito', 'user_pool_id', 'us-east-2_IvxzMrWwg')
        self.client_id = self.config.get('cognito', 'client_id', '5adkv019v4rcu6o87ffg46ep02')
        
        # JWKS URL for token verification
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        self._jwks_client = None
    
    @property
    def jwks_client(self):
        """Lazy load and cache JWKS client"""
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(self.jwks_url, cache_keys=True)
        return self._jwks_client
    
    def validate_token(self, token):
        """
        Validate and decode a Cognito JWT token
        Returns decoded claims if valid, raises TracError if invalid
        """
        try:
            # Get the signing key from Cognito's JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and verify the token
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "auth_time", "cognito:username"]
                }
            )
            
            # Additional validation
            token_use = decoded.get('token_use')
            if token_use not in ['id', 'access']:
                raise TracError(f"Invalid token_use: {token_use}")
            
            # Log successful validation
            self.log.debug(f"Token validated for user: {decoded.get('cognito:username')}")
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            raise TracError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise TracError(f"Invalid token: {str(e)}")
        except Exception as e:
            self.log.error(f"Token validation error: {str(e)}")
            raise TracError("Token validation failed")
    
    def extract_user_info(self, claims):
        """Extract user information from token claims"""
        return {
            'username': claims.get('cognito:username', claims.get('sub')),
            'email': claims.get('email'),
            'groups': claims.get('cognito:groups', []),
            'custom_permissions': claims.get('trac_permissions', '').split(','),
            'token_use': claims.get('token_use'),
            'exp': claims.get('exp'),
            'iat': claims.get('iat')
        }