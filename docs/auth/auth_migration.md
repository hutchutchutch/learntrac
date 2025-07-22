# Trac HTTP Authentication to AWS Cognito Migration Guide

## Executive Summary

This document provides a comprehensive analysis of the current HTTP authentication implementation in the LearnTrac application and outlines the migration path to AWS Cognito token-based authentication.

## Table of Contents

1. [Current Authentication Architecture](#current-authentication-architecture)
2. [Component Analysis](#component-analysis)
3. [AWS Cognito Integration Status](#aws-cognito-integration-status)
4. [Migration Strategy](#migration-strategy)
5. [Component-Specific Migration Steps](#component-specific-migration-steps)
6. [Security Considerations](#security-considerations)
7. [Testing and Rollback Plan](#testing-and-rollback-plan)

## Current Authentication Architecture

### Traditional Trac HTTP Basic Authentication

Trac traditionally delegates authentication to the web server layer using HTTP Basic Authentication. Here's how it currently works:

#### Authentication Flow

```
User → Browser → Web Server (Apache/nginx) → Trac Application
         ↓              ↓                          ↓
    Credentials    HTTP Basic Auth          LoginModule
         ↓              ↓                          ↓
    Auth Popup     htpasswd file           trac_auth cookie
```

#### Key Components

1. **Web Server Layer**
   - Handles HTTP Basic Authentication challenges
   - Validates credentials against htpasswd file
   - Sets REMOTE_USER environment variable

2. **LoginModule** (`trac.web.auth.LoginModule`)
   - Manages authentication cookies
   - Provides Login/Logout navigation links
   - Currently DISABLED in configuration: `trac.web.auth.loginmodule = disabled`

3. **Database Layer**
   - `auth_cookie` table stores session tokens
   - PostgreSQL connection with its own authentication

### Current Configuration

From `trac.ini`:
```ini
[components]
trac.web.auth.loginmodule = disabled  # Traditional auth is disabled
cognitoauth.* = enabled               # Cognito auth is enabled

[trac]
database = postgres://learntrac_admin:***@hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com:5432/learntrac
```

## Component Analysis

### 1. Frontend (Web Interface)

**Current State:**
- Browser-based interface with navigation bar
- Login/Logout links in the metanav section
- No JavaScript-based authentication handling
- Relies on server-side session management

**Authentication Points:**
- `/login` - Protected by web server auth (traditional)
- `/auth/login` - Redirects to Cognito (new implementation)
- `/auth/callback` - OAuth2 callback handler
- `/auth/logout` - Clears session and redirects to Cognito logout

### 2. Backend (Trac Core)

**Current State:**
- Python-based application using Trac framework
- Session-based authentication using `req.authname`
- IAuthenticator interface for pluggable authentication

**Key Authentication Components:**
- `CognitoAuthPlugin` - Custom plugin implementing IAuthenticator
- Session management via `req.session`
- Request filtering via IRequestFilter

### 3. Database Layer

**Current State:**
- PostgreSQL database on AWS RDS
- Connection string includes database credentials
- No application-level database authentication

**Authentication Tables:**
- `session` - Stores user sessions
- `session_attribute` - Stores session data including Cognito attributes
- `auth_cookie` - Legacy table for traditional auth (may still exist)

## AWS Cognito Integration Status

### Already Implemented

The codebase already includes a functional Cognito authentication plugin with the following features:

1. **OAuth2 Flow Implementation**
   ```python
   # Current implementation in trac_cognito_auth.py
   - Login redirect to Cognito hosted UI
   - Authorization code exchange
   - ID token decoding and validation
   - Session storage of user attributes
   ```

2. **Configuration**
   ```ini
   [cognito]
   client_id = 5adkv019v4rcu6o87ffg46ep02
   domain = hutch-learntrac-dev-auth
   region = us-east-2
   user_pool_id = us-east-2_IvxzMrWwg
   ```

3. **User Attributes Mapping**
   - `cognito:username` → `req.authname`
   - `cognito:groups` → Session attribute for permissions
   - `email` → Session attribute
   - `name` → Display name

### Missing Components

1. **Token Refresh Logic**
   - No implementation for refreshing expired tokens
   - Sessions rely on Trac's cookie lifetime

2. **API Authentication**
   - No Bearer token validation for API endpoints
   - All requests use session-based auth

3. **Fine-grained Permissions**
   - Group-based permissions not fully integrated
   - No mapping of Cognito groups to Trac permissions

## Migration Strategy

### Phase 1: Current State Assessment ✅

**Status: COMPLETE**
- Traditional LoginModule is disabled
- Cognito plugin is enabled and functional
- OAuth2 flow is working

### Phase 2: Token-Based Authentication Enhancement

**Required Changes:**

1. **Add Token Validation Middleware**
   ```python
   class TokenAuthMiddleware(Component):
       implements(IRequestFilter)
       
       def pre_process_request(self, req, handler):
           # Check for Bearer token in Authorization header
           auth_header = req.get_header('Authorization')
           if auth_header and auth_header.startswith('Bearer '):
               token = auth_header[7:]
               # Validate token with Cognito
               user_info = self.validate_cognito_token(token)
               if user_info:
                   req.authname = user_info['username']
   ```

2. **Implement Token Refresh**
   ```python
   def refresh_access_token(self, refresh_token):
       token_url = f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/oauth2/token"
       data = {
           'grant_type': 'refresh_token',
           'client_id': self.client_id,
           'refresh_token': refresh_token
       }
       # Exchange refresh token for new access token
   ```

3. **Add API Endpoint Protection**
   - Validate Bearer tokens for all API requests
   - Support both session and token authentication
   - Return 401 for invalid/expired tokens

### Phase 3: Permission System Integration

**Map Cognito Groups to Trac Permissions:**

```python
def map_cognito_groups_to_permissions(self, groups):
    permission_map = {
        'admin': ['TRAC_ADMIN'],
        'developers': ['TICKET_CREATE', 'TICKET_MODIFY', 'WIKI_CREATE', 'WIKI_MODIFY'],
        'users': ['TICKET_VIEW', 'WIKI_VIEW']
    }
    
    permissions = []
    for group in groups:
        permissions.extend(permission_map.get(group, []))
    
    return permissions
```

## Component-Specific Migration Steps

### 1. Frontend Migration

**No Changes Required** - The current implementation already:
- Uses Cognito hosted UI for login
- Handles OAuth2 callbacks
- Manages logout flow

**Optional Enhancements:**
- Add JavaScript SDK for client-side token management
- Implement automatic token refresh
- Add loading states during authentication

### 2. Backend Migration

**Step 1: Enhance Token Validation**
```python
# Add to CognitoAuthPlugin
import jwt
from jwt import PyJWKClient

def validate_cognito_token(self, token):
    jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
    jwks_client = PyJWKClient(jwks_url)
    
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.client_id,
            options={"verify_exp": True}
        )
        return decoded
    except Exception as e:
        self.log.error(f"Token validation failed: {e}")
        return None
```

**Step 2: Add Request Filter for API Authentication**
```python
def pre_process_request(self, req, handler):
    # Existing session check...
    
    # Add API token authentication
    if req.path_info.startswith('/api/'):
        auth_header = req.get_header('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            user_info = self.validate_cognito_token(token)
            if user_info:
                req.authname = user_info['cognito:username']
                req.perm = self.get_user_permissions(user_info)
            else:
                raise HTTPUnauthorized('Invalid or expired token')
```

### 3. Database Migration

**No Changes Required** - Database authentication remains unchanged as it's infrastructure-level.

**Security Enhancement:**
- Consider implementing IAM database authentication
- Rotate database passwords regularly
- Use AWS Secrets Manager for credential storage

## Security Considerations

### 1. Token Security
- **Storage**: Never store tokens in localStorage (use sessionStorage or cookies with httpOnly flag)
- **Transmission**: Always use HTTPS
- **Validation**: Validate tokens on every request
- **Expiration**: Implement proper token refresh logic

### 2. CORS Configuration
```python
# Add CORS headers for API endpoints
def post_process_request(self, req, template, data, content_type):
    if req.path_info.startswith('/api/'):
        req.send_header('Access-Control-Allow-Origin', '*')
        req.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        req.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return template, data, content_type
```

### 3. Session Security
- Set secure cookie flags
- Implement CSRF protection
- Use SameSite cookie attribute

## Testing and Rollback Plan

### Testing Strategy

1. **Unit Tests**
   ```python
   def test_cognito_token_validation():
       plugin = CognitoAuthPlugin()
       valid_token = generate_test_token()
       assert plugin.validate_cognito_token(valid_token) is not None
       
   def test_invalid_token_rejection():
       plugin = CognitoAuthPlugin()
       invalid_token = "invalid.token.here"
       assert plugin.validate_cognito_token(invalid_token) is None
   ```

2. **Integration Tests**
   - Test login flow end-to-end
   - Verify token refresh mechanism
   - Test API authentication
   - Verify permission mapping

3. **Load Testing**
   - Test token validation performance
   - Measure impact on request latency
   - Verify token caching effectiveness

### Rollback Plan

1. **Configuration Toggle**
   ```ini
   [components]
   # Quick rollback by toggling components
   cognitoauth.* = disabled
   trac.web.auth.loginmodule = enabled
   ```

2. **Database Backup**
   - Backup session tables before migration
   - Document rollback SQL scripts

3. **Monitoring**
   - Track authentication success/failure rates
   - Monitor token validation performance
   - Alert on authentication anomalies

## Conclusion

The LearnTrac application has already made significant progress in migrating from HTTP Basic Authentication to AWS Cognito. The current implementation handles the OAuth2 flow successfully. The remaining work involves:

1. Implementing token-based API authentication
2. Adding token refresh logic
3. Integrating Cognito groups with Trac's permission system
4. Enhancing security with proper token validation

The migration can be completed incrementally with minimal risk, as the current session-based approach continues to work alongside token-based authentication.