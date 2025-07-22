# AWS Cognito Implementation Guide for Trac

## Overview

This guide provides detailed implementation steps for enhancing the current Cognito integration in the LearnTrac application to support full token-based authentication.

## Current Implementation Analysis

### Existing Cognito Plugin Structure

The application currently has two versions of the Cognito plugin:

1. **Primary Plugin**: `/plugins/trac_cognito_auth.py`
   - Implements IAuthenticator, IRequestFilter, IRequestHandler, INavigationContributor
   - Handles OAuth2 flow with Cognito hosted UI
   - Manages session-based authentication

2. **Secondary Plugin**: `/plugins/cognitoauth/cognitoauth/plugin.py`
   - Similar implementation with slight variations
   - Package structure for distribution

### Key Features Already Implemented

1. **OAuth2 Authorization Code Flow**
   ```python
   # Login redirect
   auth_url = f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/login?" \
              f"client_id={self.client_id}&response_type=code&scope=email+openid+profile&" \
              f"redirect_uri={redirect_uri}"
   
   # Token exchange
   response = requests.post(token_url, data={
       'grant_type': 'authorization_code',
       'client_id': self.client_id,
       'code': code,
       'redirect_uri': redirect_uri
   })
   ```

2. **ID Token Decoding**
   ```python
   # Manual JWT decoding (without verification)
   parts = id_token.split('.')
   payload = parts[1]
   payload += '=' * (4 - len(payload) % 4)
   user_info = json.loads(urlsafe_b64decode(payload))
   ```

3. **Session Management**
   ```python
   req.session['cognito_username'] = user_info.get('cognito:username')
   req.session['cognito_groups'] = user_info.get('cognito:groups', [])
   req.session['authenticated'] = True
   ```

## Enhanced Implementation Requirements

### 1. Secure Token Validation

**Current Issue**: The plugin decodes JWT tokens without cryptographic verification.

**Required Implementation**:

```python
import jwt
from jwt import PyJWKClient
import time
from functools import lru_cache

class CognitoTokenValidator:
    def __init__(self, region, user_pool_id, client_id):
        self.region = region
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        self.jwks_client = PyJWKClient(self.jwks_url)
    
    @lru_cache(maxsize=128)
    def validate_token(self, token):
        """Validate and decode a Cognito JWT token"""
        try:
            # Get the signing key
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
                    "verify_iss": True
                }
            )
            
            # Additional validation
            if decoded.get('token_use') not in ['id', 'access']:
                raise ValueError("Invalid token_use claim")
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
```

### 2. Bearer Token Authentication for APIs

```python
class BearerTokenAuthenticator(Component):
    implements(IRequestFilter)
    
    def __init__(self):
        super().__init__()
        self.token_validator = CognitoTokenValidator(
            self.config.get('cognito', 'region'),
            self.config.get('cognito', 'user_pool_id'),
            self.config.get('cognito', 'client_id')
        )
    
    def pre_process_request(self, req, handler):
        # Check for Bearer token in Authorization header
        auth_header = req.get_header('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            
            try:
                # Validate the token
                claims = self.token_validator.validate_token(token)
                
                # Set authentication info
                req.authname = claims.get('cognito:username', claims.get('sub'))
                req.token_claims = claims
                
                # Map groups to permissions
                self._set_user_permissions(req, claims.get('cognito:groups', []))
                
            except AuthenticationError as e:
                # For API endpoints, return 401
                if req.path_info.startswith('/api/'):
                    req.send_response(401)
                    req.send_header('WWW-Authenticate', 'Bearer')
                    req.send_header('Content-Type', 'application/json')
                    req.end_headers()
                    req.write(json.dumps({'error': str(e)}))
                    raise RequestDone
        
        return handler
```

### 3. Token Refresh Implementation

```python
class TokenRefreshHandler(Component):
    implements(IRequestHandler)
    
    def match_request(self, req):
        return req.path_info == '/auth/refresh'
    
    def process_request(self, req):
        """Handle token refresh requests"""
        if req.method != 'POST':
            raise HTTPBadRequest('Method not allowed')
        
        try:
            data = json.loads(req.read())
            refresh_token = data.get('refresh_token')
            
            if not refresh_token:
                raise HTTPBadRequest('Missing refresh_token')
            
            # Exchange refresh token for new tokens
            token_url = f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/oauth2/token"
            
            response = requests.post(token_url, data={
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'refresh_token': refresh_token
            }, headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            
            if response.status_code == 200:
                tokens = response.json()
                req.send_response(200)
                req.send_header('Content-Type', 'application/json')
                req.end_headers()
                req.write(json.dumps({
                    'access_token': tokens['access_token'],
                    'id_token': tokens['id_token'],
                    'expires_in': tokens['expires_in']
                }))
            else:
                raise HTTPUnauthorized('Token refresh failed')
                
        except Exception as e:
            self.log.error(f"Token refresh error: {str(e)}")
            raise HTTPInternalError('Token refresh failed')
```

### 4. Permission Mapping System

```python
class CognitoPermissionPolicy(Component):
    implements(IPermissionPolicy)
    
    # Define group to permission mappings
    GROUP_PERMISSIONS = {
        'admin': [
            'TRAC_ADMIN',
        ],
        'developers': [
            'TICKET_CREATE', 'TICKET_MODIFY', 'TICKET_VIEW',
            'MILESTONE_CREATE', 'MILESTONE_MODIFY', 'MILESTONE_VIEW',
            'WIKI_CREATE', 'WIKI_MODIFY', 'WIKI_VIEW',
            'CHANGESET_VIEW',
        ],
        'users': [
            'TICKET_VIEW', 'MILESTONE_VIEW', 
            'WIKI_VIEW', 'CHANGESET_VIEW',
        ],
        'guests': [
            'WIKI_VIEW', 'MILESTONE_VIEW',
        ]
    }
    
    def check_permission(self, action, username, resource, perm):
        # Get user's Cognito groups from session
        groups = perm.req.session.get('cognito_groups', [])
        
        # Check if any group grants the requested permission
        for group in groups:
            if action in self.GROUP_PERMISSIONS.get(group, []):
                return True
        
        return None  # Let other policies decide
```

## Implementation Steps

### Step 1: Install Required Dependencies

```bash
pip install PyJWT cryptography requests
```

### Step 2: Update the Cognito Plugin

1. Add secure token validation
2. Implement Bearer token authentication
3. Add token refresh endpoint
4. Integrate permission mapping

### Step 3: Configure Trac Components

```ini
[components]
# Enable new components
cognitoauth.token_validator = enabled
cognitoauth.bearer_auth = enabled
cognitoauth.token_refresh = enabled
cognitoauth.permission_policy = enabled

# Ensure proper order
trac.web.auth.loginmodule = disabled
```

### Step 4: Update Frontend for Token Management

```javascript
// Token management utility
class CognitoTokenManager {
    constructor() {
        this.accessToken = null;
        this.idToken = null;
        this.refreshToken = null;
        this.expiresAt = null;
    }
    
    async refreshTokens() {
        const response = await fetch('/auth/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                refresh_token: this.refreshToken
            })
        });
        
        if (response.ok) {
            const tokens = await response.json();
            this.updateTokens(tokens);
        } else {
            // Redirect to login
            window.location.href = '/auth/login';
        }
    }
    
    updateTokens(tokens) {
        this.accessToken = tokens.access_token;
        this.idToken = tokens.id_token;
        this.expiresAt = Date.now() + (tokens.expires_in * 1000);
        
        // Store securely (not in localStorage!)
        sessionStorage.setItem('cognito_tokens', JSON.stringify({
            accessToken: this.accessToken,
            idToken: this.idToken,
            expiresAt: this.expiresAt
        }));
    }
    
    async getValidToken() {
        if (Date.now() >= this.expiresAt - 60000) { // Refresh 1 min before expiry
            await this.refreshTokens();
        }
        return this.accessToken;
    }
}

// API request wrapper
async function authenticatedFetch(url, options = {}) {
    const tokenManager = new CognitoTokenManager();
    const token = await tokenManager.getValidToken();
    
    return fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        }
    });
}
```

## Testing the Implementation

### 1. Unit Tests

```python
import unittest
from unittest.mock import Mock, patch

class TestCognitoAuth(unittest.TestCase):
    def setUp(self):
        self.plugin = CognitoAuthPlugin()
        self.mock_req = Mock()
        
    def test_bearer_token_extraction(self):
        self.mock_req.get_header.return_value = 'Bearer test.token.here'
        token = self.plugin._extract_bearer_token(self.mock_req)
        self.assertEqual(token, 'test.token.here')
    
    @patch('requests.post')
    def test_token_refresh(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'access_token': 'new.access.token',
            'id_token': 'new.id.token',
            'expires_in': 3600
        }
        
        result = self.plugin.refresh_token('old.refresh.token')
        self.assertIsNotNone(result)
        self.assertEqual(result['access_token'], 'new.access.token')
```

### 2. Integration Tests

```python
def test_full_authentication_flow():
    # 1. Test login redirect
    response = client.get('/auth/login')
    assert response.status_code == 302
    assert 'amazoncognito.com' in response.headers['Location']
    
    # 2. Test callback handling
    response = client.get('/auth/callback?code=test_code')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'
    
    # 3. Test authenticated request
    response = client.get('/api/tickets', headers={
        'Authorization': 'Bearer valid.token.here'
    })
    assert response.status_code == 200
```

## Security Best Practices

1. **Token Storage**
   - Never store tokens in localStorage
   - Use httpOnly cookies or sessionStorage
   - Clear tokens on logout

2. **Token Validation**
   - Always verify token signatures
   - Check token expiration
   - Validate issuer and audience claims

3. **Error Handling**
   - Don't expose detailed error messages
   - Log security events
   - Implement rate limiting

4. **HTTPS Requirements**
   - Always use HTTPS in production
   - Set secure cookie flags
   - Enable HSTS headers

## Monitoring and Logging

```python
# Add comprehensive logging
self.log.info(f"User {username} authenticated via Cognito")
self.log.warning(f"Token validation failed for user {username}: {error}")
self.log.error(f"Cognito API error: {error}")

# Track metrics
self.env.db_transaction("""
    INSERT INTO auth_metrics (timestamp, event_type, username, success)
    VALUES (%s, %s, %s, %s)
""", (datetime.now(), 'cognito_login', username, success))
```

## Troubleshooting Common Issues

1. **Token Expiration**
   - Symptom: 401 errors after ~1 hour
   - Solution: Implement token refresh

2. **CORS Errors**
   - Symptom: Browser blocks API requests
   - Solution: Add proper CORS headers

3. **Permission Denied**
   - Symptom: Users can't access resources
   - Solution: Check group mappings

4. **Slow Token Validation**
   - Symptom: High latency on requests
   - Solution: Cache JWKS keys