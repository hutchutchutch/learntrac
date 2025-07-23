# LearnTrac API Specification v1.0

## Overview

LearnTrac extends the traditional Trac ticketing system with modern learning management capabilities. This API provides endpoints for AI-powered tutoring, adaptive learning paths, voice interactions, and comprehensive analytics while maintaining compatibility with the existing Trac (Python 2.7) infrastructure.

### Architecture Summary

- **Base URL**: `https://api.learntrac.com`
- **Trac Legacy**: `/trac/*` (Python 2.7, port 8000)
- **LearnTrac API**: `/api/learntrac/*` (Python 3.11+, port 8001)
- **WebSocket**: `wss://api.learntrac.com/ws` (Voice/Real-time features)
- **API Version**: v1 (included in URL path)

### Technology Stack

- **API Framework**: FastAPI (Python 3.11+)
- **Authentication**: JWT with OAuth2.0 support
- **Database**: PostgreSQL (shared with Trac)
- **Cache**: Redis
- **Knowledge Graph**: Neo4j
- **Real-time**: WebSocket via AWS API Gateway
- **AI Integration**: OpenAI API, AWS Bedrock

## Authentication & Authorization

### POST /api/learntrac/v1/auth/login
Login with username and password

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "grant_type": "password"
}
```

**Response 200:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "string",
    "username": "string",
    "email": "string",
    "roles": ["student", "instructor"],
    "preferences": {}
  }
}
```

### POST /api/learntrac/v1/auth/refresh
Refresh access token

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

**Response 200:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### POST /api/learntrac/v1/auth/logout
Logout and invalidate tokens

**Headers:**
- Authorization: Bearer {access_token}

**Response 200:**
```json
{
  "message": "Successfully logged out"
}
```

### GET /api/learntrac/v1/auth/me
Get current user profile

**Headers:**
- Authorization: Bearer {access_token}

**Response 200:**
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "roles": ["student", "instructor"],
  "created_at": "2024-01-15T10:00:00Z",
  "learning_profile": {
    "level": "intermediate",
    "preferred_learning_style": "visual",
    "strengths": ["problem-solving", "debugging"],
    "areas_for_improvement": ["documentation", "testing"]
  }
}
```

## Learning Concepts Management

### GET /api/learntrac/v1/concepts
List all learning concepts (transformed from Trac tickets)

**Query Parameters:**
- `status`: Filter by status (new, learning, practicing, mastered)
- `type`: Filter by concept type (task, bug, feature, enhancement)
- `difficulty`: Filter by difficulty (1-5)
- `component`: Filter by component/module
- `milestone`: Filter by milestone
- `owner`: Filter by assigned student
- `limit`: Number of results (default: 20, max: 100)
- `offset`: Pagination offset

**Response 200:**
```json
{
  "concepts": [
    {
      "id": 1234,
      "title": "Understanding REST API Design",
      "description": "Learn the principles of RESTful API design...",
      "type": "task",
      "status": "learning",
      "difficulty": 3.5,
      "mastery_threshold": 0.8,
      "component": "backend",
      "milestone": "API Development",
      "prerequisites": [1230, 1231],
      "estimated_time": "2 hours",
      "tags": ["api", "rest", "design-patterns"],
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-16T14:30:00Z"
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

### GET /api/learntrac/v1/concepts/{concept_id}
Get detailed concept information

**Response 200:**
```json
{
  "id": 1234,
  "title": "Understanding REST API Design",
  "description": "Learn the principles of RESTful API design...",
  "type": "task",
  "status": "learning",
  "difficulty": 3.5,
  "mastery_threshold": 0.8,
  "component": "backend",
  "milestone": "API Development",
  "prerequisites": [
    {
      "id": 1230,
      "title": "HTTP Protocol Basics",
      "status": "mastered"
    },
    {
      "id": 1231,
      "title": "JSON Data Format",
      "status": "mastered"
    }
  ],
  "learning_objectives": [
    "Understand REST principles",
    "Design resource-based URLs",
    "Choose appropriate HTTP methods",
    "Implement proper status codes"
  ],
  "resources": [
    {
      "type": "documentation",
      "title": "REST API Tutorial",
      "url": "/wiki/RESTAPITutorial"
    },
    {
      "type": "video",
      "title": "REST API Design Best Practices",
      "url": "https://example.com/rest-video"
    }
  ],
  "exercises": [
    {
      "id": "ex1",
      "title": "Design a User API",
      "type": "practical",
      "points": 10
    }
  ],
  "metadata": {
    "trac_ticket_id": 1234,
    "custom_fields": {
      "learning_difficulty": "3.5",
      "time_estimate": "2h"
    }
  }
}
```

### POST /api/learntrac/v1/concepts/{concept_id}/start
Start learning a concept

**Headers:**
- Authorization: Bearer {access_token}

**Request Body:**
```json
{
  "learning_mode": "guided",  // guided, self-paced, challenge
  "time_commitment": 120,     // minutes
  "preferred_resources": ["documentation", "video"]
}
```

**Response 200:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "concept_id": 1234,
  "status": "active",
  "started_at": "2024-01-20T10:00:00Z",
  "learning_path": [
    {
      "step": 1,
      "type": "read",
      "resource": {
        "type": "documentation",
        "title": "REST API Tutorial",
        "url": "/wiki/RESTAPITutorial",
        "estimated_time": 15
      }
    },
    {
      "step": 2,
      "type": "watch",
      "resource": {
        "type": "video",
        "title": "REST API Design Best Practices",
        "url": "https://example.com/rest-video",
        "estimated_time": 20
      }
    },
    {
      "step": 3,
      "type": "practice",
      "exercise": {
        "id": "ex1",
        "title": "Design a User API",
        "instructions": "Create a RESTful API design for user management..."
      }
    }
  ],
  "ai_tutor_available": true
}
```

### POST /api/learntrac/v1/concepts/{concept_id}/complete
Mark concept as completed/mastered

**Headers:**
- Authorization: Bearer {access_token}

**Request Body:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "completion_type": "mastered",  // completed, mastered, abandoned
  "time_spent": 7200,  // seconds
  "exercises_completed": ["ex1", "ex2"],
  "quiz_score": 0.85,
  "feedback": "Great tutorial, very clear explanations"
}
```

**Response 200:**
```json
{
  "concept_id": 1234,
  "status": "mastered",
  "mastery_score": 0.85,
  "time_spent": 7200,
  "completion_date": "2024-01-20T12:00:00Z",
  "achievements_unlocked": [
    {
      "id": "fast_learner",
      "title": "Fast Learner",
      "description": "Completed concept in under 2 hours"
    }
  ],
  "next_concepts": [1235, 1236],
  "certificate_url": "/certificates/1234-550e8400.pdf"
}
```

## Student Progress Tracking

### GET /api/learntrac/v1/progress
Get overall learning progress for current user

**Headers:**
- Authorization: Bearer {access_token}

**Query Parameters:**
- `timeframe`: Period to analyze (week, month, quarter, year, all)
- `milestone`: Filter by specific milestone

**Response 200:**
```json
{
  "user_id": "user123",
  "overall_progress": {
    "total_concepts": 150,
    "completed_concepts": 45,
    "mastered_concepts": 38,
    "in_progress_concepts": 7,
    "completion_percentage": 30.0,
    "mastery_percentage": 25.3
  },
  "milestones": [
    {
      "name": "API Development",
      "total_concepts": 25,
      "completed": 15,
      "progress_percentage": 60.0,
      "estimated_completion": "2024-02-15"
    }
  ],
  "recent_activity": [
    {
      "concept_id": 1234,
      "title": "Understanding REST API Design",
      "action": "completed",
      "timestamp": "2024-01-20T12:00:00Z",
      "time_spent": 7200
    }
  ],
  "learning_velocity": {
    "concepts_per_week": 3.5,
    "hours_per_week": 10.2,
    "trend": "increasing"
  },
  "strengths": [
    {
      "area": "backend-development",
      "mastery_level": 0.82,
      "concepts_mastered": 12
    }
  ],
  "recommendations": [
    {
      "concept_id": 1235,
      "title": "Advanced REST API Security",
      "reason": "Natural progression from completed concepts",
      "difficulty_match": 0.9
    }
  ]
}
```

### GET /api/learntrac/v1/progress/{user_id}
Get learning progress for specific user (instructor view)

**Headers:**
- Authorization: Bearer {access_token}
- Required Role: instructor

**Response:** Same as above but for specified user

### GET /api/learntrac/v1/progress/history
Get detailed progress history

**Headers:**
- Authorization: Bearer {access_token}

**Query Parameters:**
- `start_date`: ISO 8601 date
- `end_date`: ISO 8601 date
- `granularity`: day, week, month

**Response 200:**
```json
{
  "history": [
    {
      "date": "2024-01-20",
      "concepts_started": 2,
      "concepts_completed": 1,
      "concepts_mastered": 1,
      "time_spent": 10800,
      "exercises_completed": 5,
      "quiz_average": 0.87
    }
  ],
  "totals": {
    "concepts_completed": 15,
    "concepts_mastered": 12,
    "total_time_spent": 54000,
    "average_mastery_score": 0.85
  }
}
```

## AI Chat Interface

### POST /api/learntrac/v1/chat/start
Start a new AI tutoring session

**Headers:**
- Authorization: Bearer {access_token}

**Request Body:**
```json
{
  "context": {
    "concept_id": 1234,
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "mode": "tutoring"  // tutoring, debugging, explaining, practice
  },
  "initial_message": "I'm having trouble understanding REST API versioning"
}
```

**Response 200:**
```json
{
  "chat_id": "chat-123456",
  "status": "active",
  "ai_model": "gpt-4",
  "context_loaded": true,
  "initial_response": {
    "message": "I'd be happy to help you understand REST API versioning! This is an important concept...",
    "suggestions": [
      "What are the different versioning strategies?",
      "Show me examples of URL versioning",
      "Why is API versioning important?"
    ],
    "resources": [
      {
        "type": "example",
        "title": "API Versioning Examples",
        "content": "```\nGET /api/v1/users\nGET /api/v2/users\n```"
      }
    ]
  }
}
```

### POST /api/learntrac/v1/chat/{chat_id}/message
Send a message in existing chat session

**Headers:**
- Authorization: Bearer {access_token}

**Request Body:**
```json
{
  "message": "Can you show me how to implement versioning in FastAPI?",
  "include_code_examples": true
}
```

**Response 200:**
```json
{
  "message_id": "msg-789",
  "response": {
    "message": "Certainly! Here's how to implement API versioning in FastAPI...",
    "code_examples": [
      {
        "language": "python",
        "title": "URL Path Versioning",
        "code": "from fastapi import FastAPI\n\napp = FastAPI()\n\n# Version 1 endpoints\n@app.get(\"/api/v1/users\")\nasync def get_users_v1():\n    return {\"version\": 1, \"users\": []}\n\n# Version 2 endpoints\n@app.get(\"/api/v2/users\")\nasync def get_users_v2():\n    return {\"version\": 2, \"users\": [], \"total\": 0}"
      }
    ],
    "follow_up_questions": [
      "Would you like to see header-based versioning?",
      "Should I explain the pros and cons of each approach?",
      "Do you want to practice implementing this?"
    ]
  },
  "tokens_used": 245,
  "context_retention": 0.95
}
```

### GET /api/learntrac/v1/chat/{chat_id}/history
Get chat history

**Headers:**
- Authorization: Bearer {access_token}

**Response 200:**
```json
{
  "chat_id": "chat-123456",
  "started_at": "2024-01-20T10:00:00Z",
  "messages": [
    {
      "message_id": "msg-001",
      "role": "user",
      "content": "I'm having trouble understanding REST API versioning",
      "timestamp": "2024-01-20T10:00:00Z"
    },
    {
      "message_id": "msg-002",
      "role": "assistant",
      "content": "I'd be happy to help you understand REST API versioning!...",
      "timestamp": "2024-01-20T10:00:05Z"
    }
  ],
  "total_messages": 10,
  "concept_coverage": ["api-versioning", "rest-design", "backward-compatibility"]
}
```

### POST /api/learntrac/v1/chat/{chat_id}/feedback
Provide feedback on AI responses

**Headers:**
- Authorization: Bearer {access_token}

**Request Body:**
```json
{
  "message_id": "msg-789",
  "rating": 5,
  "helpful": true,
  "feedback": "Clear explanation with great examples",
  "improvement_suggestions": "Could include more real-world scenarios"
}
```

**Response 200:**
```json
{
  "feedback_recorded": true,
  "thank_you_message": "Thank you for your feedback! This helps improve our AI tutoring."
}
```

## Voice Interaction (WebSocket)

### WebSocket /ws/voice
Real-time voice tutoring session

**Connection URL:** `wss://api.learntrac.com/ws/voice?token={access_token}`

**Connection Message:**
```json
{
  "action": "connect",
  "data": {
    "session_type": "voice_tutoring",
    "concept_id": 1234,
    "preferred_voice": "alloy",
    "language": "en-US"
  }
}
```

**Server Response:**
```json
{
  "type": "connection_established",
  "data": {
    "session_id": "voice-session-123",
    "status": "ready",
    "voice_enabled": true,
    "features": ["transcription", "real-time-feedback", "code-dictation"]
  }
}
```

**Audio Stream Message:**
```json
{
  "action": "audio_stream",
  "data": {
    "audio": "base64_encoded_audio_chunk",
    "chunk_id": 1,
    "is_final": false
  }
}
```

**Transcription Response:**
```json
{
  "type": "transcription",
  "data": {
    "text": "Can you explain how to handle errors in REST APIs?",
    "confidence": 0.95,
    "is_final": true
  }
}
```

**AI Voice Response:**
```json
{
  "type": "voice_response",
  "data": {
    "text": "Of course! Error handling in REST APIs is crucial...",
    "audio_url": "https://cdn.learntrac.com/audio/response-123.mp3",
    "duration": 15.5,
    "visual_aids": [
      {
        "type": "code_snippet",
        "content": "try:\n    result = process_request()\nexcept ValidationError as e:\n    return {\"error\": str(e)}, 400"
      }
    ]
  }
}
```

### POST /api/learntrac/v1/voice/transcribe
Transcribe audio file for learning

**Headers:**
- Authorization: Bearer {access_token}
- Content-Type: multipart/form-data

**Request Body:**
- audio_file: Binary audio file (mp3, wav, m4a)
- context: Optional concept_id for better accuracy

**Response 200:**
```json
{
  "transcription": {
    "text": "Can you explain the difference between PUT and PATCH methods?",
    "confidence": 0.97,
    "duration": 5.2,
    "language": "en-US"
  },
  "ai_response": {
    "answer": "PUT and PATCH are both HTTP methods used for updating resources...",
    "related_concepts": [1245, 1246]
  }
}
```

## Analytics & Reporting

### GET /api/learntrac/v1/analytics/dashboard
Get analytics dashboard data

**Headers:**
- Authorization: Bearer {access_token}

**Query Parameters:**
- `timeframe`: week, month, quarter, year
- `user_id`: Specific user (instructor only)

**Response 200:**
```json
{
  "summary": {
    "active_learners": 145,
    "concepts_completed": 523,
    "average_mastery_score": 0.83,
    "total_learning_hours": 1250.5
  },
  "trends": {
    "completion_rate": {
      "current": 0.75,
      "previous": 0.68,
      "change_percentage": 10.3
    },
    "engagement_score": {
      "current": 0.82,
      "previous": 0.78,
      "change_percentage": 5.1
    }
  },
  "top_concepts": [
    {
      "concept_id": 1234,
      "title": "Understanding REST API Design",
      "completions": 89,
      "average_time": 6800,
      "average_score": 0.87
    }
  ],
  "struggling_areas": [
    {
      "concept_id": 1567,
      "title": "Advanced Database Optimization",
      "failure_rate": 0.35,
      "average_attempts": 2.8,
      "common_issues": ["query optimization", "indexing strategies"]
    }
  ],
  "learning_paths": {
    "most_successful": [
      {
        "path": [1230, 1231, 1234, 1235],
        "success_rate": 0.92,
        "average_time": 14400
      }
    ]
  }
}
```

### GET /api/learntrac/v1/analytics/learner/{user_id}
Get detailed learner analytics

**Headers:**
- Authorization: Bearer {access_token}
- Required Role: instructor (or self)

**Response 200:**
```json
{
  "user_id": "user123",
  "learning_profile": {
    "preferred_time": "morning",
    "average_session_length": 45,
    "learning_style": "visual",
    "strength_areas": ["backend", "databases"],
    "improvement_areas": ["frontend", "testing"]
  },
  "performance_metrics": {
    "overall_mastery": 0.78,
    "concepts_per_week": 2.5,
    "exercise_success_rate": 0.85,
    "quiz_average": 0.82
  },
  "engagement_patterns": {
    "most_active_days": ["Tuesday", "Thursday"],
    "peak_hours": ["10:00", "14:00"],
    "resource_preferences": {
      "documentation": 0.45,
      "video": 0.35,
      "interactive": 0.20
    }
  },
  "milestone_progress": [
    {
      "milestone": "API Development",
      "start_date": "2024-01-01",
      "target_date": "2024-03-01",
      "progress": 0.65,
      "on_track": true
    }
  ],
  "recommendations": {
    "next_concepts": [1236, 1237],
    "suggested_pace_adjustment": "increase",
    "focus_areas": ["practice more exercises", "review prerequisites"]
  }
}
```

### POST /api/learntrac/v1/analytics/export
Export analytics data

**Headers:**
- Authorization: Bearer {access_token}
- Required Role: instructor

**Request Body:**
```json
{
  "report_type": "learner_progress",  // learner_progress, concept_analytics, milestone_summary
  "format": "pdf",  // pdf, csv, xlsx
  "filters": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "user_ids": ["user123", "user456"],
    "milestones": ["API Development"]
  },
  "include_sections": ["summary", "detailed_progress", "recommendations"]
}
```

**Response 200:**
```json
{
  "export_id": "export-789",
  "status": "processing",
  "estimated_time": 30,
  "download_url": null,
  "webhook_url": "https://api.learntrac.com/api/learntrac/v1/analytics/export/export-789/status"
}
```

## Knowledge Graph

### GET /api/learntrac/v1/knowledge/graph
Get knowledge graph visualization data

**Headers:**
- Authorization: Bearer {access_token}

**Query Parameters:**
- `center_concept`: Concept ID to center the graph on
- `depth`: How many levels to include (default: 2, max: 5)
- `include_mastery`: Include user's mastery data

**Response 200:**
```json
{
  "nodes": [
    {
      "id": "concept-1234",
      "label": "REST API Design",
      "type": "concept",
      "mastery": 0.85,
      "status": "mastered",
      "properties": {
        "difficulty": 3.5,
        "estimated_time": "2h",
        "component": "backend"
      }
    },
    {
      "id": "concept-1235",
      "label": "API Security",
      "type": "concept",
      "mastery": 0.0,
      "status": "locked",
      "properties": {
        "difficulty": 4.0,
        "estimated_time": "3h",
        "component": "backend"
      }
    }
  ],
  "edges": [
    {
      "source": "concept-1234",
      "target": "concept-1235",
      "relationship": "prerequisite_for",
      "weight": 0.9
    }
  ],
  "clusters": [
    {
      "id": "backend-cluster",
      "label": "Backend Development",
      "concepts": ["concept-1234", "concept-1235"],
      "mastery": 0.65
    }
  ]
}
```

### GET /api/learntrac/v1/knowledge/path
Get optimal learning path

**Headers:**
- Authorization: Bearer {access_token}

**Query Parameters:**
- `from`: Starting concept ID (optional, defaults to current level)
- `to`: Target concept ID
- `optimize_for`: time, difficulty, prerequisites

**Response 200:**
```json
{
  "path": [
    {
      "step": 1,
      "concept_id": 1234,
      "title": "REST API Design",
      "status": "mastered",
      "estimated_time": 0
    },
    {
      "step": 2,
      "concept_id": 1240,
      "title": "Authentication Basics",
      "status": "available",
      "estimated_time": 90,
      "reason": "Required prerequisite"
    },
    {
      "step": 3,
      "concept_id": 1235,
      "title": "API Security",
      "status": "locked",
      "estimated_time": 180,
      "reason": "Target concept"
    }
  ],
  "total_concepts": 3,
  "total_estimated_time": 270,
  "difficulty_progression": [3.5, 3.0, 4.0],
  "alternative_paths": [
    {
      "path": [1234, 1241, 1235],
      "total_time": 300,
      "difficulty_score": 3.7
    }
  ]
}
```

### POST /api/learntrac/v1/knowledge/relationships
Add custom concept relationships

**Headers:**
- Authorization: Bearer {access_token}
- Required Role: instructor

**Request Body:**
```json
{
  "source_concept": 1234,
  "target_concept": 1235,
  "relationship_type": "related_to",  // prerequisite_for, related_to, alternative_to
  "weight": 0.7,
  "bidirectional": false,
  "notes": "These concepts share similar patterns"
}
```

**Response 201:**
```json
{
  "relationship_id": "rel-456",
  "source": 1234,
  "target": 1235,
  "type": "related_to",
  "created_at": "2024-01-20T15:00:00Z"
}
```

## Practice & Exercises

### GET /api/learntrac/v1/exercises
List available exercises

**Headers:**
- Authorization: Bearer {access_token}

**Query Parameters:**
- `concept_id`: Filter by concept
- `difficulty`: Filter by difficulty (1-5)
- `type`: coding, quiz, design, debug
- `status`: available, completed, in_progress

**Response 200:**
```json
{
  "exercises": [
    {
      "id": "ex-123",
      "title": "Design a RESTful User API",
      "concept_id": 1234,
      "type": "design",
      "difficulty": 3,
      "points": 10,
      "estimated_time": 30,
      "status": "available",
      "completion_rate": 0.0,
      "prerequisites_met": true
    }
  ],
  "total": 25,
  "available": 15,
  "completed": 10
}
```

### POST /api/learntrac/v1/exercises/{exercise_id}/start
Start an exercise

**Headers:**
- Authorization: Bearer {access_token}

**Response 200:**
```json
{
  "session_id": "ex-session-789",
  "exercise": {
    "id": "ex-123",
    "title": "Design a RESTful User API",
    "instructions": "Design a complete RESTful API for user management including...",
    "requirements": [
      "Support CRUD operations",
      "Include proper HTTP status codes",
      "Design resource URLs following REST principles",
      "Include authentication considerations"
    ],
    "starter_code": "# Define your API endpoints here\n# Example: GET /api/v1/users\n",
    "test_cases": 5,
    "time_limit": 1800
  },
  "started_at": "2024-01-20T15:00:00Z"
}
```

### POST /api/learntrac/v1/exercises/{exercise_id}/submit
Submit exercise solution

**Headers:**
- Authorization: Bearer {access_token}

**Request Body:**
```json
{
  "session_id": "ex-session-789",
  "solution": {
    "code": "# User API Design\n\n## Endpoints\n\n### GET /api/v1/users\n...",
    "language": "markdown",
    "tests_passed": 4,
    "execution_time": 1250
  },
  "request_feedback": true
}
```

**Response 200:**
```json
{
  "result": {
    "score": 8.5,
    "max_score": 10,
    "tests_passed": 4,
    "tests_total": 5,
    "status": "passed",
    "execution_time": 1250
  },
  "feedback": {
    "strengths": [
      "Good URL design following REST principles",
      "Appropriate HTTP methods used",
      "Clear resource naming"
    ],
    "improvements": [
      "Missing error response examples",
      "Could include rate limiting considerations"
    ],
    "detailed_feedback": "Your API design shows good understanding...",
    "suggested_reading": [
      {
        "concept_id": 1245,
        "title": "API Error Handling Best Practices"
      }
    ]
  },
  "achievements": [
    {
      "id": "first_api_design",
      "title": "API Designer",
      "description": "Completed your first API design exercise"
    }
  ]
}
```

## Adaptive Learning

### GET /api/learntrac/v1/adaptive/recommendations
Get personalized learning recommendations

**Headers:**
- Authorization: Bearer {access_token}

**Query Parameters:**
- `count`: Number of recommendations (default: 5)
- `timeframe`: How much time available (minutes)

**Response 200:**
```json
{
  "recommendations": [
    {
      "concept_id": 1236,
      "title": "API Rate Limiting",
      "reason": "Natural progression from completed REST API concepts",
      "confidence": 0.92,
      "estimated_time": 45,
      "difficulty_match": 0.88,
      "prerequisites_ready": true,
      "learning_style_match": 0.85
    }
  ],
  "learning_insights": {
    "current_level": "intermediate",
    "momentum": "high",
    "suggested_pace": "maintain",
    "strength_areas": ["api-design", "backend"],
    "focus_areas": ["security", "performance"]
  },
  "adaptive_path": {
    "short_term": [1236, 1237],
    "medium_term": [1250, 1251, 1252],
    "long_term_goal": "Full-Stack API Development Mastery"
  }
}
```

### POST /api/learntrac/v1/adaptive/feedback
Provide learning feedback for adaptation

**Headers:**
- Authorization: Bearer {access_token}

**Request Body:**
```json
{
  "concept_id": 1234,
  "difficulty_rating": 3,  // 1-5, was it too easy/hard?
  "clarity_rating": 4,     // 1-5, how clear was the content?
  "pace_feedback": "just_right",  // too_slow, just_right, too_fast
  "preferred_resources": ["video", "exercises"],
  "time_sufficient": true,
  "additional_comments": "Would like more real-world examples"
}
```

**Response 200:**
```json
{
  "feedback_recorded": true,
  "profile_updated": true,
  "adjustments": {
    "difficulty_preference": "slightly_increased",
    "resource_weights": {
      "video": 0.4,
      "documentation": 0.3,
      "exercises": 0.3
    },
    "pace_adjustment": "maintained"
  }
}
```

## Error Handling

All endpoints follow consistent error response format:

**Error Response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "concept_id",
        "message": "Concept ID must be a positive integer"
      }
    ],
    "request_id": "req-123456",
    "timestamp": "2024-01-20T15:00:00Z"
  }
}
```

### Common Error Codes:
- `AUTHENTICATION_ERROR` (401): Invalid or missing authentication
- `AUTHORIZATION_ERROR` (403): Insufficient permissions
- `NOT_FOUND` (404): Resource not found
- `VALIDATION_ERROR` (400): Invalid request parameters
- `CONFLICT` (409): Resource conflict (e.g., already started)
- `RATE_LIMIT_EXCEEDED` (429): Too many requests
- `SERVER_ERROR` (500): Internal server error

## Rate Limiting

API implements rate limiting per user:
- **Authenticated users**: 1000 requests per hour
- **Chat API**: 100 messages per hour
- **Voice API**: 60 minutes per day
- **Analytics exports**: 10 per day

Rate limit information included in response headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1705765200
```

## Webhooks

### POST /api/learntrac/v1/webhooks
Register a webhook

**Headers:**
- Authorization: Bearer {access_token}
- Required Role: instructor

**Request Body:**
```json
{
  "url": "https://example.com/webhook",
  "events": ["concept.completed", "milestone.achieved", "user.struggled"],
  "secret": "webhook_secret_key",
  "active": true
}
```

**Response 201:**
```json
{
  "webhook_id": "webhook-123",
  "url": "https://example.com/webhook",
  "events": ["concept.completed", "milestone.achieved", "user.struggled"],
  "created_at": "2024-01-20T15:00:00Z",
  "status": "active"
}
```

### Webhook Event Payload:
```json
{
  "event": "concept.completed",
  "timestamp": "2024-01-20T15:00:00Z",
  "data": {
    "user_id": "user123",
    "concept_id": 1234,
    "mastery_score": 0.85,
    "time_spent": 7200
  },
  "signature": "sha256=..."
}
```

## API Versioning

The API uses URL path versioning:
- Current version: v1
- Version included in all endpoints: `/api/learntrac/v1/...`
- Deprecation notices provided 6 months in advance
- Backward compatibility maintained for 12 months

## SDK Support

Official SDKs available for:
- Python: `pip install learntrac-sdk`
- JavaScript/TypeScript: `npm install @learntrac/sdk`
- Go: `go get github.com/learntrac/sdk-go`

## Health & Status

### GET /api/learntrac/v1/health
Basic health check

**Response 200:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-20T15:00:00Z"
}
```

### GET /api/learntrac/v1/status
Detailed system status

**Response 200:**
```json
{
  "status": "operational",
  "services": {
    "api": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "neo4j": "healthy",
    "ai_service": "healthy"
  },
  "response_time_ms": 45,
  "uptime_seconds": 864000
}
```