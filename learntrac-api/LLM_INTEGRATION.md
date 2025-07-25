# LLM Integration for Question Generation

## Overview

The LLM Integration service provides AI-powered question generation capabilities for the LearnTrac learning platform. It uses OpenAI's GPT models through an API Gateway pattern to generate educational questions from learning content.

## Features

- **Intelligent Question Generation**: Creates questions at different difficulty levels and cognitive types
- **Multiple Question Types**: Supports comprehension, application, analysis, synthesis, and evaluation
- **Quality Validation**: Ensures generated questions meet educational standards
- **Caching**: Redis-based caching for improved performance
- **Circuit Breaker**: Prevents cascading failures with retry logic
- **Batch Processing**: Generate multiple questions efficiently

## API Endpoints

### Base URL: `/api/learntrac/llm`

#### 1. Generate Single Question

```http
POST /api/learntrac/llm/generate-question
Authorization: Bearer <jwt_token>

{
  "chunk_content": "Python functions are reusable blocks of code...",
  "concept": "Python Functions",
  "difficulty": 3,
  "context": "Introduction to Programming",
  "question_type": "comprehension"
}
```

**Response:**
```json
{
  "question": "What is the primary purpose of Python functions?",
  "expected_answer": "Python functions serve as reusable blocks of code that perform specific tasks...",
  "concept": "Python Functions",
  "difficulty": 3,
  "generated_at": "2024-01-25T10:30:00Z",
  "question_length": 45,
  "answer_length": 287
}
```

#### 2. Generate Multiple Questions

```http
POST /api/learntrac/llm/generate-multiple-questions
Authorization: Bearer <jwt_token>

{
  "chunk_content": "Python functions are reusable blocks of code...",
  "concept": "Python Functions",
  "count": 3,
  "difficulty_range": [2, 4],
  "question_types": ["comprehension", "application", "analysis"]
}
```

**Response:**
```json
{
  "concept": "Python Functions",
  "requested_count": 3,
  "generated_count": 3,
  "questions": [
    {
      "question": "What keyword is used to define a function in Python?",
      "expected_answer": "The 'def' keyword is used to define functions in Python...",
      "difficulty": 2,
      "question_type": "comprehension"
    }
  ]
}
```

#### 3. Generate from Neo4j Chunks

```http
POST /api/learntrac/llm/generate-from-chunks
Authorization: Bearer <jwt_token>

{
  "chunk_ids": ["chunk_abc123", "chunk_def456"],
  "difficulty": 3,
  "questions_per_chunk": 2
}
```

#### 4. Content Analysis

```http
POST /api/learntrac/llm/analyze-content
Authorization: Bearer <jwt_token>

{
  "content": "Python functions are reusable blocks of code...",
  "analysis_type": "difficulty"
}
```

**Analysis Types:**
- `difficulty`: Assess content difficulty level
- `concepts`: Extract main learning concepts
- `readability`: Analyze readability and clarity

#### 5. Get Question Types

```http
GET /api/learntrac/llm/question-types
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "question_types": {
    "comprehension": {
      "description": "Tests understanding of core concepts and main ideas",
      "cognitive_level": "Remember/Understand",
      "example": "What is the main purpose of Python functions?"
    }
  },
  "difficulty_levels": {
    "1": "Very Easy - Basic recall and recognition",
    "2": "Easy - Simple understanding and identification",
    "3": "Medium - Application of concepts to familiar situations",
    "4": "Hard - Analysis and synthesis of multiple concepts",
    "5": "Very Hard - Evaluation and creation of new solutions"
  }
}
```

#### 6. Health Check

```http
GET /api/learntrac/llm/health
Authorization: Bearer <jwt_token>
```

#### 7. Service Statistics (Admin Only)

```http
GET /api/learntrac/llm/stats
Authorization: Bearer <jwt_token>
```

## Configuration

### Environment Variables

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here
LLM_API_KEY=your_openai_api_key_here  # Alternative
API_GATEWAY_URL=https://api.openai.com/v1  # Default

# Redis for caching
REDIS_URL=redis://localhost:6379

# Database for chunk retrieval
DATABASE_URL=postgresql://user:pass@localhost/learntrac

# Neo4j for vector search
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
```

## Question Types and Cognitive Levels

Based on Bloom's Taxonomy:

### 1. Comprehension (Remember/Understand)
- Tests basic understanding of concepts
- Example: "What is a Python function?"

### 2. Application (Apply)
- Requires applying concepts to solve problems
- Example: "How would you create a function to calculate area?"

### 3. Analysis (Analyze)
- Requires breaking down concepts into components
- Example: "Compare list comprehensions vs for loops"

### 4. Synthesis (Create)
- Requires combining concepts for new solutions
- Example: "Design a class with both iteration and context management"

### 5. Evaluation (Evaluate)
- Requires judging or critiquing approaches
- Example: "Evaluate the pros and cons of recursion vs iteration"

## Difficulty Levels

1. **Very Easy**: Basic recall and recognition
2. **Easy**: Simple understanding and identification
3. **Medium**: Application to familiar situations
4. **Hard**: Analysis and synthesis of multiple concepts
5. **Very Hard**: Evaluation and creation of new solutions

## Quality Validation

Generated questions are validated for:

- **Length**: Questions 100-500 chars, answers 200-1000 chars
- **Format**: Questions end with question marks
- **Completeness**: No incomplete indicators (TODO, etc.)
- **Relevance**: Concept keywords appear in content
- **Educational Value**: Appropriate for difficulty level

## Caching Strategy

- **Cache Key**: Based on content hash, concept, difficulty, and type
- **TTL**: 1 hour for generated questions
- **Storage**: Redis with JSON serialization
- **Hit Rate**: Monitored via stats endpoint

## Error Handling

### Circuit Breaker
- **Failure Threshold**: 5 consecutive failures
- **Timeout**: 60 seconds before retry
- **States**: CLOSED (normal), OPEN (failing), HALF_OPEN (testing)

### Retry Logic
- **Max Retries**: 3 attempts
- **Backoff**: Exponential (1s, 2s, 4s)
- **Rate Limits**: Automatic handling with delays

### Fallback Behavior
- Returns error messages instead of failing completely
- Maintains service availability during LLM outages
- Logs all failures for monitoring

## Performance

### Benchmarks
- **Single Question**: ~2-5 seconds
- **Multiple Questions**: ~8-15 seconds (parallel)
- **Cache Hit**: <100ms
- **Batch Processing**: 3-5 questions/second

### Optimization
- Connection pooling with persistent sessions
- Concurrent question generation
- Intelligent caching based on content similarity
- Circuit breaker prevents resource waste

## Testing

### Run Test Suite

```bash
cd learntrac-api
python test_llm_integration.py
```

### Manual Testing

```bash
# Test health
curl -H "Authorization: Bearer <token>" \
  http://localhost:8001/api/learntrac/llm/health

# Generate question
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_content": "Python functions are reusable blocks of code...",
    "concept": "Python Functions",
    "difficulty": 3
  }' \
  http://localhost:8001/api/learntrac/llm/generate-question
```

## Integration with Learning System

### Workflow
1. User studies content in Neo4j chunks
2. System selects relevant chunks for assessment
3. LLM generates questions based on chunk content
4. Questions cached for reuse across students
5. Student answers evaluated against expected responses

### Learning Path Integration
- Generate questions for prerequisite concepts
- Create progressive difficulty assessments
- Adapt question types based on learning objectives
- Track concept mastery through question performance

## Monitoring and Observability

### Key Metrics
- Question generation success rate
- Average response time
- Cache hit rate
- Circuit breaker state changes
- API error rates

### Logging
- All generation requests with metadata
- Performance timing for optimization
- Error details for debugging
- Cache performance statistics

### Health Checks
- LLM API connectivity
- Circuit breaker status
- Cache system health
- Question quality validation rates

## Security and Privacy

### Authentication
- JWT token required for all endpoints
- Permission-based access control
- Rate limiting by user/organization

### Data Handling
- Content not stored permanently in LLM service
- Generated questions cached with TTL expiration
- No personally identifiable information sent to LLM
- Audit logging for compliance

## Production Deployment

### Prerequisites
1. OpenAI API key with GPT-4 access
2. Redis instance for caching
3. Neo4j Aura for content chunks
4. PostgreSQL for user data

### Scaling Considerations
- Multiple worker processes for FastAPI
- Redis cluster for cache distribution
- Load balancing for high availability
- Circuit breaker prevents cascade failures

### Monitoring Setup
- Health check endpoints for load balancer
- Metrics collection for performance tracking
- Alerting on circuit breaker state changes
- Cost monitoring for LLM API usage

## Troubleshooting

### Common Issues

1. **"LLM service not available"**
   - Check OPENAI_API_KEY environment variable
   - Verify API key has sufficient credits
   - Check circuit breaker state

2. **"Failed to generate embedding"**
   - Ensure embedding service is initialized
   - Check Neo4j connectivity
   - Verify content format

3. **"Question failed quality validation"**
   - Review generated content for completeness
   - Check concept relevance in content
   - Adjust difficulty or question type

4. **High response times**
   - Check cache hit rates
   - Monitor LLM API latency
   - Consider increasing cache TTL

### Debug Mode

Set environment variable for detailed logging:
```env
LOG_LEVEL=DEBUG
```

## Future Enhancements

- Multi-language question generation
- Custom prompt templates per subject
- Integration with learning analytics
- Real-time question difficulty adjustment
- Automated question bank management