# -*- coding: utf-8 -*-
"""
Cognito Authenticator for Trac
Handles JWT token validation and user authentication
"""

from trac.core import Component, implements
from trac.web.api import IAuthenticator, IRequestHandler
from trac.config import Option
from trac.util.translation import _

import json
import time
import base64
import jwt
from jwt.algorithms import RSAAlgorithm

try:
    # Python 2
    from urllib2 import urlopen
    from urlparse import urljoin
except ImportError:
    # Python 3
    from urllib.request import urlopen
    from urllib.parse import urljoin


class CognitoAuthenticator(Component):
    """AWS Cognito authenticator for Trac"""
    
    implements(IAuthenticator)
    
    # Configuration options
    cognito_region = Option('cognito', 'region', 'us-east-2',
                           doc='AWS region for Cognito')
    cognito_user_pool_id = Option('cognito', 'user_pool_id', '',
                                 doc='Cognito User Pool ID')
    cognito_client_id = Option('cognito', 'client_id', '',
                              doc='Cognito App Client ID')
    cognito_domain = Option('cognito', 'domain', '',
                           doc='Cognito domain (without .auth.<region>.amazoncognito.com)')
    
    def __init__(self):
        self.jwks_cache = {}
        self.jwks_cache_time = 0
        self.jwks_cache_ttl = 3600  # 1 hour
        
    def authenticate(self, req):
        """Extract user from JWT token in Authorization header or cookie"""
        
        # Check for JWT token in Authorization header
        auth_header = req.get_header('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            user_info = self._validate_jwt_token(token)
            if user_info:
                return user_info.get('username', user_info.get('email'))
        
        # Check for token in cookie (for browser sessions)
        token = req.get_cookie('cognito_id_token')
        if token:
            user_info = self._validate_jwt_token(token.value)
            if user_info:
                return user_info.get('username', user_info.get('email'))
        
        # Check for Cognito authorization code in request
        code = req.args.get('code')
        if code:
            # Exchange authorization code for tokens
            tokens = self._exchange_code_for_tokens(code, req)
            if tokens:
                # Set cookies for tokens
                req.send_cookie('cognito_id_token', tokens['id_token'], 
                               max_age=3600, path='/')
                req.send_cookie('cognito_access_token', tokens['access_token'], 
                               max_age=3600, path='/')
                
                # Validate and extract user info from ID token
                user_info = self._validate_jwt_token(tokens['id_token'])
                if user_info:
                    return user_info.get('username', user_info.get('email'))
        
        return None
    
    def _get_jwks(self):
        """Fetch JWKS from Cognito with caching"""
        current_time = time.time()
        
        # Check cache
        if self.jwks_cache and (current_time - self.jwks_cache_time) < self.jwks_cache_ttl:
            return self.jwks_cache
        
        # Fetch JWKS
        jwks_url = 'https://cognito-idp.%s.amazonaws.com/%s/.well-known/jwks.json' % (
            self.cognito_region, self.cognito_user_pool_id)
        
        try:
            response = urlopen(jwks_url)
            jwks_data = json.loads(response.read())
            
            # Cache the JWKS
            self.jwks_cache = jwks_data
            self.jwks_cache_time = current_time
            
            return jwks_data
        except Exception as e:
            self.log.error("Failed to fetch JWKS: %s", e)
            return None
    
    def _validate_jwt_token(self, token):
        """Validate JWT token and return user info"""
        try:
            # Get JWKS
            jwks = self._get_jwks()
            if not jwks:
                return None
            
            # Decode token header to get kid
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')
            
            # Find the key
            key = None
            for k in jwks.get('keys', []):
                if k['kid'] == kid:
                    key = k
                    break
            
            if not key:
                self.log.error("Key with kid %s not found in JWKS", kid)
                return None
            
            # Convert JWK to PEM
            public_key = RSAAlgorithm.from_jwk(json.dumps(key))
            
            # Verify token
            issuer = 'https://cognito-idp.%s.amazonaws.com/%s' % (
                self.cognito_region, self.cognito_user_pool_id)
            
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                issuer=issuer,
                audience=self.cognito_client_id,
                options={"verify_exp": True}
            )
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            self.log.warning("Token has expired")
        except jwt.InvalidTokenError as e:
            self.log.warning("Invalid token: %s", e)
        except Exception as e:
            self.log.error("Token validation error: %s", e)
        
        return None
    
    def _exchange_code_for_tokens(self, code, req):
        """Exchange authorization code for tokens"""
        try:
            import urllib
            
            # Build token endpoint URL
            token_url = 'https://%s.auth.%s.amazoncognito.com/oauth2/token' % (
                self.cognito_domain, self.cognito_region)
            
            # Build redirect URI
            redirect_uri = req.abs_href('auth/callback')
            
            # Prepare data
            data = {
                'grant_type': 'authorization_code',
                'client_id': self.cognito_client_id,
                'code': code,
                'redirect_uri': redirect_uri
            }
            
            # Make request
            data_encoded = urllib.urlencode(data)
            request = urllib2.Request(token_url, data_encoded)
            request.add_header('Content-Type', 'application/x-www-form-urlencoded')
            
            response = urllib2.urlopen(request)
            tokens = json.loads(response.read())
            
            return tokens
            
        except Exception as e:
            self.log.error("Failed to exchange code for tokens: %s", e)
            return None