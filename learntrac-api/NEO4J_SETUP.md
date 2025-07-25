# Neo4j Aura Setup Guide for LearnTrac

## Overview

LearnTrac uses Neo4j Aura for vector similarity search and graph-based prerequisite management. This guide covers setting up Neo4j Aura and configuring the LearnTrac API to use it.

## Neo4j Aura Setup

### 1. Create Neo4j Aura Instance

1. Go to [Neo4j Aura](https://neo4j.com/cloud/aura/)
2. Sign up or log in
3. Create a new database:
   - Choose **AuraDB Free** for development/testing
   - Select your preferred region (closest to your AWS infrastructure)
   - Save the generated password securely

### 2. Configure Instance

After creation, you'll receive:
- **Connection URI**: `neo4j+s://xxxxx.databases.neo4j.io`
- **Username**: `neo4j` (default)
- **Password**: Generated password from step 1

### 3. Enable GDS (Graph Data Science)

For vector similarity search, ensure your instance supports GDS:
- AuraDB Free includes basic GDS functions
- For production, consider AuraDB Professional for full GDS support

## Environment Configuration

### 1. Update .env File

Add your Neo4j credentials to `.env`:

```env
# Neo4j Configuration
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here
```

### 2. Test Connection

Run the test script to verify connectivity:

```bash
cd learntrac-api
python test_neo4j_connection.py
```

Expected output:
```
✓ Connection healthy!
  Server time: 2024-01-25T10:30:00
  Chunk count: 0
  GDS version: 2.x.x
```

## Data Model

### Chunk Node Structure

```cypher
(:Chunk {
  id: String,           // Unique identifier
  content: String,      // Learning content text
  embedding: Float[],   // 1536-dimension vector (OpenAI)
  subject: String,      // Subject area (e.g., "Python Programming")
  concept: String,      // Specific concept (e.g., "Functions")
  has_prerequisite: String[],    // Array of prerequisite chunk IDs
  prerequisite_for: String[],    // Array of dependent chunk IDs
  metadata: Map,        // Additional properties
  updated_at: DateTime
})
```

### Relationships

```cypher
(chunk1:Chunk)-[:HAS_PREREQUISITE {type: "STRONG"}]->(chunk2:Chunk)
```

## API Endpoints

### Vector Search

```http
POST /api/learntrac/vector/search
Authorization: Bearer <jwt_token>

{
  "query": "Python functions and parameters",
  "min_score": 0.65,
  "limit": 20,
  "include_prerequisites": true
}
```

### Create Chunk

```http
POST /api/learntrac/vector/chunks
Authorization: Bearer <jwt_token>

{
  "content": "Python functions are reusable blocks of code...",
  "subject": "Python Programming",
  "concept": "Functions",
  "has_prerequisite": ["chunk_variables_001"]
}
```

### Create Prerequisite

```http
POST /api/learntrac/vector/prerequisites
Authorization: Bearer <jwt_token>

{
  "from_chunk_id": "chunk_functions_001",
  "to_chunk_id": "chunk_variables_001",
  "relationship_type": "STRONG"
}
```

## Cypher Queries

### Create Vector Index

```cypher
CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
FOR (c:Chunk)
ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
}
```

### Vector Similarity Search

```cypher
MATCH (c:Chunk)
WITH c, gds.similarity.cosine(c.embedding, $embedding) AS score
WHERE score >= 0.65
RETURN c.id, c.content, c.subject, c.concept, score
ORDER BY score DESC
LIMIT 20
```

### Find Prerequisites

```cypher
MATCH (start:Chunk {id: $chunk_id})
OPTIONAL MATCH path = (start)-[:HAS_PREREQUISITE*1..5]->(prereq:Chunk)
RETURN prereq, length(path) as depth
ORDER BY depth
```

## Performance Optimization

### 1. Indexes

Create these indexes for optimal performance:

```cypher
CREATE INDEX chunk_id FOR (c:Chunk) ON (c.id);
CREATE INDEX chunk_subject FOR (c:Chunk) ON (c.subject);
CREATE INDEX chunk_concept FOR (c:Chunk) ON (c.concept);
```

### 2. Connection Pooling

The API uses connection pooling with these settings:
- `max_connection_lifetime`: 3600 seconds
- `max_connection_pool_size`: 50
- `connection_acquisition_timeout`: 60 seconds

### 3. Caching

Vector search results are cached in Redis:
- Cache key: `vector_search:{embedding_hash}:{min_score}:{limit}`
- TTL: 1 hour

## Monitoring

### Health Check

```bash
curl http://localhost:8001/api/learntrac/vector/health \
  -H "Authorization: Bearer <jwt_token>"
```

Response:
```json
{
  "status": "healthy",
  "server_time": "2024-01-25T10:30:00",
  "chunk_count": 150,
  "gds_version": "2.x.x"
}
```

### Metrics to Monitor

1. **Query Performance**
   - Vector search response time
   - Number of results returned
   - Cache hit rate

2. **Database Health**
   - Connection pool usage
   - Query execution time
   - Node/relationship count

3. **Data Quality**
   - Embedding dimension consistency
   - Prerequisite cycle detection
   - Orphaned chunks

## Troubleshooting

### Connection Issues

1. **"Connection refused"**
   - Check Neo4j URI format: `neo4j+s://` for encrypted connections
   - Verify instance is running in Neo4j Aura console
   - Check network connectivity

2. **"Authentication failed"**
   - Verify username/password
   - Check for special characters in password that need escaping
   - Try resetting password in Neo4j Aura console

### Query Issues

1. **"GDS function not found"**
   - Ensure your Neo4j Aura tier supports GDS
   - Check GDS version with: `CALL gds.version()`

2. **"Vector index not found"**
   - Run index creation queries from this guide
   - Wait for index to be populated (check with `SHOW INDEXES`)

3. **"No results returned"**
   - Lower `min_score` threshold (try 0.5 for testing)
   - Verify embeddings are properly stored
   - Check embedding dimensions match (1536 for OpenAI)

## Best Practices

1. **Chunk Size**: Keep content chunks focused on single concepts (100-500 words)
2. **Embeddings**: Regenerate embeddings if changing models or content significantly
3. **Prerequisites**: Avoid circular dependencies in prerequisite relationships
4. **Batch Operations**: Use bulk endpoints for multiple chunks
5. **Monitoring**: Set up alerts for connection failures and slow queries

## Migration from Development to Production

1. **Export Data**: Use `apoc.export.json.all()` to export development data
2. **Create Production Instance**: Choose AuraDB Professional for production
3. **Import Data**: Use `apoc.import.json()` to import data
4. **Update Connection**: Change environment variables to production URI
5. **Test Thoroughly**: Verify all queries work with production data volume