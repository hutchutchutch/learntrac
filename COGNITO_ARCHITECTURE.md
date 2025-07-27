# AWS Cognito Authentication Architecture for LearnTrac

## Overview

The authentication system integrates AWS Cognito with Trac using a two-container architecture that works within the constraints of Trac's Python 2.7 environment.

## Architecture Components

### 1. Learning API Service (Python 3.11)
- **Location**: `learntrac-api` container
- **Port**: 8001
- **Responsibilities**:
  - Handles all Cognito OAuth 2.0 flow
  - JWT token validation using PyJWT
  - Session management
  - Provides auth endpoints: `/auth/login`, `/auth/callback`, `/auth/verify`, `/auth/logout`

### 2. Trac Service (Python 2.7)
- **Location**: `trac` container  
- **Port**: 8000
- **Components**:
  - AuthProxy Plugin: Simple authentication proxy that delegates to Learning API
  - No complex JWT handling in Python 2.7

## Authentication Flow

```
1. User → http://localhost:8000/trac/wiki
2. Trac AuthProxy → Checks session cookie
3. If not authenticated → Redirect to http://localhost:8001/auth/login
4. Learning API → Redirect to https://hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com/login
5. User → Authenticates with Cognito
6. Cognito → Redirects to http://localhost:8001/auth/callback?code=xxx
7. Learning API → Exchanges code for JWT tokens
8. Learning API → Creates session, sets cookie
9. Learning API → Redirects to http://localhost:8000/trac/wiki
10. User → Accesses Trac with valid session
```

## Configuration

### Cognito Settings (in both services)
```
- Region: us-east-2
- Domain: hutch-learntrac-dev-auth
- Client ID: 5adkv019v4rcu6o87ffg46ep02
- User Pool ID: us-east-2_IvxzMrWwg
```

### Learning API Auth Router
- **File**: `learntrac-api/src/routers/auth.py`
- **Endpoints**:
  - `GET /auth/login` - Initiates Cognito login
  - `GET /auth/callback` - Handles OAuth callback
  - `GET /auth/verify` - Verifies session for Trac
  - `GET /auth/logout` - Logs out user
  - `GET /auth/user` - Gets current user info

### Trac AuthProxy Plugin
- **Location**: `plugins/authproxy/`
- **Configuration**: Points to `http://learning-service:8001`
- **Functionality**: 
  - Checks authentication via `/auth/verify`
  - Redirects login/logout to Learning API

## Benefits of This Architecture

1. **Python 2.7 Compatibility**: Keeps complex JWT/OAuth logic in Python 3.11 container
2. **Separation of Concerns**: Authentication logic isolated from Trac
3. **Scalability**: Auth service can be scaled independently
4. **Security**: JWT validation happens in modern Python environment
5. **Maintainability**: Easy to update auth logic without touching Trac

## Testing

Use the provided `test-auth-flow.html` to:
1. Test direct Cognito authentication
2. Verify Learning API endpoints
3. Test full Trac integration flow
4. Check authentication status

## Deployment Notes

1. Both containers must be on same network for inter-service communication
2. Session cookies use `httponly` and `samesite=lax` for security
3. In production, use Redis for session storage instead of in-memory
4. Configure HTTPS for all endpoints
5. Set proper CORS headers for cross-origin requests