# LearnTrac API Documentation

## Overview

The LearnTrac API provides RESTful endpoints for managing learning paths, tracking student progress, and delivering AI-enhanced educational content. All endpoints require JWT authentication via AWS Cognito.

## Authentication

### JWT Bearer Token

All API requests (except health checks) must include a valid JWT token in the Authorization header:

```http
Authorization: Bearer <jwt_token>
```

Tokens are obtained through AWS Cognito authentication flow and include:
- User identity (`sub`, `email`, `username`)
- Groups (`cognito:groups`)
- Custom permissions (`trac_permissions`)

### Permission Levels

1. **Students** (`students` group):
   - View learning content
   - Track own progress
   - Submit practice answers
   - Search concepts

2. **Instructors** (`instructors` group):
   - All student permissions
   - Create/modify content
   - View analytics
   - Grade assignments

3. **Admins** (`admins` group):
   - Full system access
   - User management
   - System configuration

## API Endpoints

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
  "student_id": "cognito-sub",
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
    "redis": "healthy",
    "neo4j": "healthy"
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

API requests are rate-limited per user:
- Default: 100 requests per minute
- Bulk operations: 10 requests per minute

Rate limit headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time when limit resets

## Pagination

List endpoints support pagination:

```http
GET /api/learntrac/paths?page=1&size=20
```

Response includes pagination metadata:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

## WebSocket Support

Real-time features available at:
```
ws://localhost:8001/api/learntrac/ws
```

Used for:
- Live progress updates
- Collaborative learning sessions
- Real-time notifications

## Best Practices

1. **Cache responses** when appropriate (concepts, paths)
2. **Use batch operations** for multiple updates
3. **Include correlation IDs** in requests for debugging
4. **Handle pagination** for large result sets
5. **Implement exponential backoff** for retries

## SDK Examples

### Python
```python
import httpx

async with httpx.AsyncClient() as client:
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(
        "http://localhost:8001/api/learntrac/paths",
        headers=headers
    )
    paths = response.json()
```

### JavaScript
```javascript
const response = await fetch('/api/learntrac/paths', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
const paths = await response.json();
```

## Changelog

### v1.0.0 (Current)
- Initial release with core learning features
- JWT authentication via AWS Cognito
- PostgreSQL + Redis + Neo4j integration
- AI-powered content generation
- Vector similarity search