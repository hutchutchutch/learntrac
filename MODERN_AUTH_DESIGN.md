# Modern Authentication System Design for LearnTrac

## Overview
This document outlines the design for upgrading Trac's default cookie-based authentication to a modern, secure system while maintaining compatibility with Python 2.7.

## Current State vs Target State

### Current (Standard Trac Auth)
- Simple HTTP cookies
- Basic session management
- No CSRF protection
- Limited security headers
- No rate limiting
- Session data stored in files

### Target (Modern Auth System)
- Secure, signed session tokens
- CSRF protection
- Secure cookie settings (HttpOnly, Secure, SameSite)
- Rate limiting and brute force protection
- Session data in Redis with TTL
- Modern security headers
- API key support for service-to-service calls

## Architecture

### Components

1. **Enhanced Trac Auth Plugin (Python 2.7)**
   - Replaces default Trac authentication
   - Generates secure session tokens
   - Manages user authentication
   - Compatible with Python 2.7

2. **Session Management Service (Python 3.11)**
   - Redis-based session storage
   - Token validation and refresh
   - Security monitoring
   - Rate limiting

3. **API Authentication Handler (Python 3.11)**
   - Validates session tokens
   - Handles API key authentication
   - Implements CSRF protection

## Implementation Plan

### Phase 1: Secure Session Tokens

#### Python 2.7 Compatible Token Generation
```python
# Compatible with Python 2.7 - no f-strings, uses older libraries
import hashlib
import hmac
import time
import base64
import json
import uuid

class SecureTokenGenerator:
    def __init__(self, secret_key):
        self.secret_key = secret_key
    
    def generate_session_token(self, user_id, permissions):
        payload = {
            'user_id': user_id,
            'permissions': permissions,
            'issued_at': int(time.time()),
            'expires_at': int(time.time()) + 3600,  # 1 hour
            'session_id': str(uuid.uuid4()),
            'csrf_token': self._generate_csrf_token()
        }
        
        # Create signature
        payload_b64 = base64.b64encode(json.dumps(payload))
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_b64,
            hashlib.sha256
        ).hexdigest()
        
        return payload_b64 + '.' + signature
    
    def _generate_csrf_token(self):
        return hashlib.sha256(str(uuid.uuid4()) + str(time.time())).hexdigest()[:32]
```

#### Secure Cookie Settings
```python
# Python 2.7 compatible cookie settings
def set_secure_cookie(response, name, value):
    response.set_cookie(
        name,
        value,
        max_age=3600,          # 1 hour
        httponly=True,         # Prevent XSS
        secure=True,           # HTTPS only (production)
        path='/',
        domain=None,
        samesite='Lax'         # CSRF protection
    )
```

### Phase 2: Enhanced Trac Plugin

#### Modern Trac Auth Plugin Structure
```
plugins/
├── modern_auth/
│   ├── __init__.py
│   ├── auth.py              # Main authentication logic
│   ├── session_manager.py   # Session management
│   ├── security.py          # Security utilities
│   ├── rate_limiter.py      # Rate limiting
│   └── templates/
│       ├── login.html       # Modern login form
│       └── login.js         # Client-side security
└── setup.py
```

#### Key Features

1. **Secure Session Management**
```python
class ModernSessionManager:
    def authenticate_user(self, username, password, request):
        # Rate limiting check
        if self.rate_limiter.is_rate_limited(request.remote_addr):
            raise AuthenticationError("Too many attempts")
        
        # Validate credentials
        user = self.validate_credentials(username, password)
        if not user:
            self.rate_limiter.record_failed_attempt(request.remote_addr)
            raise AuthenticationError("Invalid credentials")
        
        # Generate secure session
        session_token = self.token_generator.generate_session_token(
            user.id, 
            user.permissions
        )
        
        # Store in Redis
        self.session_store.store_session(session_token, user.id)
        
        return session_token
```

2. **CSRF Protection**
```python
class CSRFProtection:
    def generate_csrf_token(self, session_token):
        # Extract session info
        session_data = self.parse_session_token(session_token)
        
        # Generate CSRF token tied to session
        csrf_data = {
            'session_id': session_data['session_id'],
            'timestamp': int(time.time()),
            'nonce': str(uuid.uuid4())
        }
        
        return self.sign_csrf_token(csrf_data)
    
    def validate_csrf_token(self, csrf_token, session_token):
        # Validate CSRF token matches session
        return self.verify_csrf_signature(csrf_token, session_token)
```

3. **Rate Limiting**
```python
class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.max_attempts = 5
        self.window_minutes = 15
    
    def is_rate_limited(self, ip_address):
        key = "rate_limit:{}".format(ip_address)
        attempts = self.redis.get(key) or 0
        return int(attempts) >= self.max_attempts
    
    def record_failed_attempt(self, ip_address):
        key = "rate_limit:{}".format(ip_address)
        self.redis.incr(key)
        self.redis.expire(key, self.window_minutes * 60)
```

### Phase 3: API Integration

#### Modern API Authentication Handler
```python
# learntrac-api/src/auth/modern_auth_handler.py
class ModernAuthHandler:
    def __init__(self):
        self.session_validator = SessionValidator()
        self.csrf_validator = CSRFValidator()
        self.api_key_validator = APIKeyValidator()
    
    async def authenticate_request(self, request: Request) -> AuthenticatedUser:
        # Try session token authentication
        session_token = self.extract_session_token(request)
        if session_token:
            user = await self.validate_session_token(session_token)
            if user:
                # Validate CSRF for state-changing requests
                if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                    self.validate_csrf_token(request, session_token)
                return user
        
        # Try API key authentication
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return await self.validate_api_key(api_key)
        
        # No valid authentication
        raise HTTPException(status_code=401, detail="Authentication required")
```

### Phase 4: Security Enhancements

#### Security Headers
```python
class SecurityHeadersMiddleware:
    def add_security_headers(self, response):
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for header, value in headers.items():
            response.headers[header] = value
```

#### Session Storage with Redis
```python
class RedisSessionStore:
    def store_session(self, session_token, user_id, ttl=3600):
        session_key = "session:{}".format(self.hash_token(session_token))
        session_data = {
            'user_id': user_id,
            'created_at': int(time.time()),
            'last_activity': int(time.time())
        }
        
        self.redis.setex(session_key, ttl, json.dumps(session_data))
    
    def validate_session(self, session_token):
        session_key = "session:{}".format(self.hash_token(session_token))
        session_data = self.redis.get(session_key)
        
        if not session_data:
            return None
        
        # Update last activity
        data = json.loads(session_data)
        data['last_activity'] = int(time.time())
        self.redis.setex(session_key, 3600, json.dumps(data))
        
        return data
```

## Security Features

### 1. Secure Token Design
- **Signed tokens**: HMAC-SHA256 signatures prevent tampering
- **Time-based expiration**: Tokens expire after 1 hour
- **Session binding**: Tokens tied to specific sessions
- **CSRF tokens**: Built-in CSRF protection

### 2. Modern Cookie Security
- **HttpOnly**: Prevents XSS attacks
- **Secure**: HTTPS-only transmission
- **SameSite**: CSRF protection
- **Path/Domain restrictions**: Limits cookie scope

### 3. Rate Limiting
- **IP-based limiting**: 5 attempts per 15 minutes
- **User-based limiting**: Account lockout after multiple failures
- **Progressive delays**: Increasing delays after failures

### 4. Session Management
- **Redis storage**: Fast, scalable session storage
- **Automatic cleanup**: TTL-based session expiration
- **Activity tracking**: Last activity timestamps
- **Concurrent session limits**: Limit active sessions per user

## Python 2.7 Compatibility

### Required Libraries (Available in Python 2.7)
```
hashlib      # Standard library
hmac         # Standard library
time         # Standard library
base64       # Standard library
json         # Standard library (or simplejson)
uuid         # Standard library
redis==2.10.6  # Last version supporting Python 2.7
```

### Code Patterns for Python 2.7
```python
# Use .format() instead of f-strings
message = "User {} logged in at {}".format(username, timestamp)

# Use explicit exception handling
try:
    result = authenticate_user(username, password)
except AuthenticationError as e:
    log_error("Authentication failed: {}".format(str(e)))

# Use dict() instead of dict comprehensions in some cases
permissions = dict((k, v) for k, v in user_perms.items() if v)
```

## Migration Strategy

### Phase 1: Parallel Implementation
1. Deploy new auth system alongside existing
2. Use feature flag to switch between systems
3. Test with subset of users

### Phase 2: Gradual Migration
1. Migrate admin users first
2. Monitor for issues
3. Gradually migrate all users

### Phase 3: Full Deployment
1. Switch all traffic to new system
2. Remove old authentication code
3. Monitor and optimize

## Benefits

### Security Improvements
- **Modern token-based authentication**
- **CSRF protection**
- **Rate limiting and brute force protection**
- **Secure session management**
- **Security headers**

### Performance Improvements
- **Redis-based session storage**
- **Reduced database queries**
- **Efficient token validation**

### Developer Experience
- **Modern API authentication**
- **Better error handling**
- **Comprehensive logging**
- **Easy integration with external services**

## Conclusion

This modern authentication system provides enterprise-grade security while maintaining full compatibility with Trac's Python 2.7 environment. The hybrid approach allows for gradual migration and modern API integration without disrupting existing workflows.

The system is designed to be:
- **Secure**: Modern cryptographic practices
- **Scalable**: Redis-based session management
- **Compatible**: Works with Python 2.7 and 3.11
- **Maintainable**: Clear separation of concerns
- **Extensible**: Easy to add new authentication methods