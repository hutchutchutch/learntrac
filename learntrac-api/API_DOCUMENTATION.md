# LearnTrac API Documentation

## Overview

The LearnTrac API provides RESTful endpoints for managing learning paths, tracking student progress, and delivering AI-enhanced educational content. The API uses modern session-based authentication that integrates seamlessly with Trac's authentication system.

## Authentication

### Modern Session-Based Authentication

LearnTrac uses a **modern session-based authentication system** that significantly upgrades Trac's original HTTP cookie-based auth. This new system provides enterprise-grade security while maintaining full compatibility with Trac's Python 2.7 environment.

#### Key Improvements Over Original Trac Auth:

1. **Secure Token Design**
   - **Original**: Simple MD5-hashed cookies with username and IP address
   - **Modern**: HMAC-SHA256 signed tokens with cryptographic signatures
   - **Benefit**: Tokens cannot be forged or tampered with, even if intercepted

2. **Enhanced Security Features**
   - **CSRF Protection**: All state-changing requests require CSRF tokens
   - **Rate Limiting**: Progressive delays prevent brute-force attacks (15min → 1hr lockouts)
   - **Secure Headers**: Modern security headers (CSP, HSTS, X-Frame-Options)
   - **Session Encryption**: Sensitive data never exposed in cookies

3. **Session Management**
   - **Original**: Sessions stored in browser cookies only
   - **Modern**: Redis-backed sessions with automatic expiration
   - **Benefit**: Sessions can be revoked server-side, better scalability

4. **Token Structure**
   ```
   Original Cookie: "username:timestamp:md5hash"
   Modern Token: "base64(payload).hmac_signature"
   
   Payload includes:
   - user_id: Username
   - permissions: List of Trac permissions
   - groups: User groups
   - session_id: Unique session identifier
   - issued_at: Token creation time
   - expires_at: Token expiration
   - client_ip: IP validation
   ```

### Authentication Methods

#### 1. Session Token (Primary)

Session tokens are automatically set by Trac when users log in through the modern auth plugin:

```http
Cookie: trac_auth_token=<secure_session_token>
```

Alternatively, for API clients:

```http
Authorization: Bearer <secure_session_token>
X-Session-Token: <secure_session_token>
```

#### 2. API Key Authentication

For service-to-service calls:

```http
X-API-Key: <api_key>
```

#### 3. Development Mode

In development environments only:

```http
Authorization: Basic <base64(username:password)>
```

### Permission System

The modern auth system integrates with Trac's permission model:

1. **Students** (`students` group):
   - `LEARNING_PARTICIPATE` - Access learning content
   - `TICKET_VIEW` - View tickets
   - `WIKI_VIEW` - Read wiki pages

2. **Instructors** (`instructors` group):
   - All student permissions plus:
   - `LEARNING_INSTRUCT` - Create/modify content
   - `TICKET_CREATE` - Create new tickets
   - `WIKI_MODIFY` - Edit wiki pages

3. **Admins** (`admins` group):
   - `TRAC_ADMIN` - Full system access
   - All other permissions

### CSRF Protection

For POST, PUT, DELETE, and PATCH requests, include a CSRF token:

```http
X-CSRF-Token: <csrf_token>
```

Or in form data:
```json
{
  "csrf_token": "<csrf_token>",
  "other_data": "..."
}
```

## API Endpoints

### Authentication Endpoints

#### Verify Session
```http
GET /auth/verify
```

Verifies the current session and returns user information.

Response:
```json
{
  "authenticated": true,
  "user": {
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "permissions": ["LEARNING_PARTICIPATE", "TICKET_VIEW"],
    "groups": ["students"],
    "session_id": "uuid",
    "is_admin": false,
    "is_instructor": false,
    "is_student": true
  }
}
```

#### Get Current User
```http
GET /auth/user
```

Returns detailed information about the authenticated user.

#### Check Permissions
```http
GET /auth/permissions
```

Returns user's permissions and access levels:
```json
{
  "permissions": ["LEARNING_PARTICIPATE", "TICKET_VIEW"],
  "groups": ["students"],
  "access_levels": {
    "admin": false,
    "instructor": false,
    "student": true
  },
  "specific_permissions": {
    "trac_admin": false,
    "learning_instruct": false,
    "learning_participate": true,
    "ticket_create": false,
    "wiki_modify": false
  }
}
```

#### Check Specific Permission
```http
GET /auth/check/{permission}
```

Example: `/auth/check/LEARNING_INSTRUCT`

Response:
```json
{
  "permission": "LEARNING_INSTRUCT",
  "granted": false,
  "user": "john_doe"
}
```

#### Logout
```http
POST /auth/logout
```

Clears authentication cookies. Note: Actual session invalidation happens on the Trac side.

#### Authentication Status
```http
GET /auth/status
```

Returns authentication system configuration:
```json
{
  "auth_system": "modern_session",
  "provider": "trac_builtin",
  "session_based": true,
  "features": {
    "csrf_protection": true,
    "rate_limiting": true,
    "secure_tokens": true,
    "redis_sessions": true
  }
}
```

### Learning Paths

#### List Learning Paths
```http
GET /api/learntrac/paths?active_only=true
```

Response:
```json
[
  {
    "path_id": "uuid",
    "title": "Introduction to Python",
    "description": "Learn Python fundamentals",
    "difficulty_level": "beginner",
    "estimated_hours": 20,
    "tags": ["python", "programming"],
    "concept_count": 15
  }
]
```

#### Get Path Concepts
```http
GET /api/learntrac/paths/{path_id}/concepts
```

Response:
```json
[
  {
    "concept_id": "uuid",
    "ticket_id": 123,
    "path_id": "uuid",
    "title": "Variables and Data Types",
    "description": "Understanding Python variables",
    "difficulty_score": 3,
    "estimated_minutes": 30,
    "prerequisites": ["uuid1", "uuid2"],
    "learning_objectives": ["Define variables", "Use data types"],
    "tags": ["basics", "variables"]
  }
]
```

### Concepts

#### Get Concept Details
```http
GET /api/learntrac/concepts/{concept_id}
```

Response includes full concept information with caching for performance.

#### Get Practice Questions
```http
GET /api/learntrac/concepts/{concept_id}/practice?regenerate=false
```

Response:
```json
{
  "concept_id": "uuid",
  "title": "Variables and Data Types",
  "questions": [
    {
      "question": "What is a variable in Python?",
      "type": "multiple_choice",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "Variables store data values"
    }
  ]
}
```

#### Submit Practice Answers
```http
POST /api/learntrac/concepts/{concept_id}/practice
```

Request:
```json
{
  "answers": [
    {
      "question_id": 1,
      "answer": "A",
      "is_correct": true
    }
  ],
  "time_spent_seconds": 300
}
```

Response:
```json
{
  "score": 0.8,
  "correct_count": 4,
  "total_questions": 5,
  "mastery_achieved": true,
  "message": "Practice results recorded successfully"
}
```

### Progress Tracking

#### Get My Progress
```http
GET /api/learntrac/progress?path_id=uuid
```

Response:
```json
{
  "student_id": "john_doe",
  "statistics": {
    "total_concepts": 50,
    "completed": 20,
    "in_progress": 5,
    "mastered": 15,
    "average_mastery": 0.75,
    "total_time_hours": 25.5,
    "completion_percentage": 40.0
  },
  "recent_activity": [
    {
      "concept_id": "uuid",
      "concept_title": "Functions in Python",
      "status": "in_progress",
      "mastery_score": 0.6,
      "last_accessed": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### Update Progress
```http
PUT /api/learntrac/progress/{concept_id}
```

Request:
```json
{
  "status": "completed",
  "mastery_score": 0.85,
  "time_spent_minutes": 45,
  "notes": "Struggled with recursion examples"
}
```

### Search

#### Search Concepts
```http
GET /api/learntrac/search?q=python+functions&limit=10
```

Response:
```json
{
  "results": [
    {
      "concept_id": "uuid",
      "ticket_id": 125,
      "title": "Python Functions",
      "description": "Learn to create and use functions",
      "difficulty_score": 4,
      "tags": ["functions", "python"],
      "similarity_score": 0.92
    }
  ],
  "search_type": "vector"
}
```

Search uses vector similarity if Neo4j is configured, otherwise falls back to PostgreSQL full-text search.

### Health Checks

#### System Health
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "neo4j": "not_configured",
    "llm": "healthy",
    "tickets": "healthy",
    "evaluation": "healthy"
  }
}
```

#### Service Health
```http
GET /api/learntrac/health
```

Response:
```json
{
  "status": "healthy",
  "service": "learntrac-api",
  "features": {
    "learning": "enabled",
    "chat": "enabled",
    "voice": "enabled",
    "analytics": "enabled"
  }
}
```

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `422` - Unprocessable Entity (validation error)
- `500` - Internal Server Error

## Rate Limiting

The modern auth system includes built-in rate limiting:

- **Login attempts**: 5 attempts per 15 minutes
- **Progressive delays**: Failed attempts increase lockout time (15min → 30min → 1hr)
- **API requests**: 100 requests per minute per user
- **Bulk operations**: 10 requests per minute

Rate limit information in response:
```json
{
  "error": "Too many login attempts",
  "lockout_time": 900,
  "message": "Please wait 15 minutes before trying again"
}
```

## Security Headers

All API responses include modern security headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN  
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...
Referrer-Policy: strict-origin-when-cross-origin
```

## Configuration

### Environment Variables

```bash
# Required for session validation
TRAC_AUTH_SECRET=your-secret-key-min-32-chars

# Trac integration
TRAC_BASE_URL=http://localhost:8000
SESSION_TIMEOUT=3600  # 1 hour

# API Keys (comma-separated)
VALID_API_KEYS=key1,key2,key3
INTERNAL_API_KEY=internal-service-key

# Development
ENVIRONMENT=development  # or production
```

## Migration from Cognito

The modern session-based auth is a drop-in replacement for the previous Cognito JWT authentication:

1. **No client changes needed** - Session tokens work with existing cookie mechanisms
2. **Permissions preserved** - Same permission model as before
3. **API compatibility** - All endpoints work the same way
4. **Enhanced security** - Better protection without complexity

### Key Differences:

| Feature | Cognito JWT | Modern Session |
|---------|-------------|----------------|
| Token Type | JWT | HMAC-signed session |
| Token Storage | Bearer header | Cookie + optional header |
| Session Storage | Stateless | Redis with fallback |
| Python Compatibility | 3.x only | 2.7 and 3.x |
| Infrastructure | AWS managed | Self-managed |
| CSRF Protection | Manual | Built-in |
| Rate Limiting | External | Built-in |

## Best Practices

1. **Session Management**
   - Sessions expire after 1 hour by default
   - Renew sessions by re-authenticating through Trac
   - Logout properly to clear server-side sessions

2. **CSRF Protection**
   - Always include CSRF tokens for state-changing requests
   - Tokens are provided by the Trac auth system
   - Validate tokens on every POST/PUT/DELETE

3. **Error Handling**
   - Check for 401 errors and re-authenticate
   - Handle rate limiting with exponential backoff
   - Log session IDs for debugging (not tokens)

4. **Performance**
   - Session validation is cached for 5 minutes
   - Use connection pooling for API clients
   - Batch operations when possible

## SDK Examples

### Python
```python
import httpx

# Session-based auth (automatic from browser)
async with httpx.AsyncClient(cookies={"trac_auth_token": token}) as client:
    response = await client.get("http://localhost:8001/api/learntrac/paths")
    paths = response.json()

# API key auth
async with httpx.AsyncClient() as client:
    headers = {"X-API-Key": api_key}
    response = await client.get(
        "http://localhost:8001/api/learntrac/paths",
        headers=headers
    )
```

### JavaScript
```javascript
// Browser (cookies sent automatically)
const response = await fetch('/api/learntrac/paths', {
  credentials: 'include'
});

// API key
const response = await fetch('/api/learntrac/paths', {
  headers: {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json'
  }
});
```

## Changelog

### v2.0.0 (Current)
- **BREAKING**: Replaced AWS Cognito with modern session-based auth
- Added HMAC-signed secure session tokens
- Implemented CSRF protection
- Added progressive rate limiting
- Improved Python 2.7 compatibility
- Enhanced security headers
- Redis session storage with fallback

### v1.0.0
- Initial release with core learning features
- JWT authentication via AWS Cognito
- PostgreSQL + Redis + Neo4j integration
- AI-powered content generation
- Vector similarity search