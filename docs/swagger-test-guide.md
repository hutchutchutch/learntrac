# LearnTrac Swagger UI Testing Guide

Access the Swagger UI at: http://localhost:8001/docs

## Quick Test Sequence

### 1. Authentication
First, authenticate using the `/auth/login` endpoint or ensure you have a valid session cookie.

### 2. Test LLM Endpoints

#### Generate Question (Most Common)
**Endpoint:** `POST /api/learntrac/llm/generate-question`

Quick test payload:
```json
{
  "chunk_content": "Python lists are ordered, mutable collections that can contain different data types. They support operations like append, remove, and indexing.",
  "concept": "Python Lists",
  "difficulty": 3,
  "question_type": "comprehension"
}
```

#### Analyze Content
**Endpoint:** `POST /api/learntrac/llm/analyze-content`

Quick test:
```json
{
  "content": "Quantum computing uses quantum bits (qubits) that can exist in superposition states.",
  "analysis_type": "difficulty"
}
```

### 3. Test Vector Search

#### Basic Search
**Endpoint:** `POST /api/learntrac/vector/search`

Quick test:
```json
{
  "query": "explain database indexing",
  "min_score": 0.65,
  "limit": 10
}
```

#### Enhanced Search (Recommended)
**Endpoint:** `POST /api/learntrac/vector/search/enhanced`

Quick test:
```json
{
  "query": "machine learning",
  "generate_sentences": 5,
  "min_score": 0.7,
  "limit": 15,
  "include_generated_context": true
}
```

#### Compare Search Methods
**Endpoint:** `POST /api/learntrac/vector/search/compare`

Quick test:
```json
{
  "query": "neural networks",
  "min_score": 0.65,
  "limit": 10
}
```

#### Create Chunk (Requires Instructor/Admin)
**Endpoint:** `POST /api/learntrac/vector/chunks`

Quick test:
```json
{
  "content": "Binary search is an efficient algorithm for finding items in sorted lists.",
  "subject": "Algorithms",
  "concept": "Binary Search"
}
```

## Common Test Scenarios

### Scenario 1: Generate Questions for a Quiz
1. Create or find relevant chunks using vector search
2. Generate multiple questions with varying difficulty
3. Analyze the content difficulty to ensure appropriate level

### Scenario 2: Build Learning Path
1. Create chunks for different concepts
2. Establish prerequisite relationships
3. Search with prerequisites included to see learning paths

### Scenario 3: Content Analysis
1. Submit various content for difficulty analysis
2. Extract concepts from content
3. Generate questions based on the analysis

## Response Validation

### Successful Question Generation
- `question` should be 100-500 characters
- `expected_answer` should be 200-1000 characters
- `difficulty` matches requested level (1-5)
- No `error` field or `error` is null

### Successful Vector Search
- `results` array contains matched chunks
- Each result has a `score` >= min_score
- Results are ordered by score (descending)

## Error Testing

### Test Authentication Errors
Remove auth headers/cookies to test 401 responses

### Test Permission Errors
Try creating chunks with read-only user to test 403 responses

### Test Invalid Data
- Send difficulty > 5 or < 1
- Send empty content
- Send invalid analysis_type

## Performance Testing

### Circuit Breaker Test
1. Make rapid requests to trigger rate limiting
2. Check `/api/learntrac/llm/health` for circuit breaker state
3. Wait for timeout period and verify recovery

### Bulk Operations
1. Use bulk vector search with 10+ queries
2. Generate multiple questions (count: 10)
3. Monitor response times

## Tips for Swagger UI

1. **Authorize First**: Click the "Authorize" button and add your credentials
2. **Try It Out**: Click "Try it out" button to enable editing
3. **Execute**: Click "Execute" to send the request
4. **Copy Response**: Use the copy button to save responses
5. **Download**: Use "Download" to save response as file

## Health Monitoring

Always check these endpoints first:
- `GET /api/learntrac/llm/health` - LLM service status
- `GET /api/learntrac/vector/health` - Neo4j connection status
- `GET /health` - Overall API health

## Minimal Working Examples

### LLM Question (Copy & Paste)
```json
{
  "chunk_content": "Functions are reusable code blocks",
  "concept": "Functions",
  "difficulty": 2
}
```

### Vector Search (Copy & Paste)
```json
{
  "query": "python functions",
  "min_score": 0.6,
  "limit": 5
}
```