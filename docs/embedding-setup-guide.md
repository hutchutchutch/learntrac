# Embedding Service Setup Guide

## Overview

The LearnTrac API requires an embedding service to convert text into vectors for similarity search. Without proper configuration, the enhanced search features will not work correctly.

## Configuration Options

### Option 1: OpenAI Embeddings (Recommended)

1. **Get an OpenAI API Key**
   - Sign up at https://platform.openai.com
   - Create an API key in your account settings

2. **Set Environment Variable**
   ```bash
   export OPENAI_API_KEY="sk-your-api-key-here"
   ```

3. **Or add to `.env` file**
   ```
   OPENAI_API_KEY=sk-your-api-key-here
   ```

4. **Verify Configuration**
   ```bash
   curl -X GET "http://localhost:8001/health" | jq '.components.llm'
   ```

### Option 2: Local Sentence Transformers

1. **Install sentence-transformers**
   ```bash
   pip install sentence-transformers torch
   ```

2. **The service will automatically use local model**
   - Model: `all-MiniLM-L6-v2` (384 dimensions)
   - No API key required
   - Runs locally on CPU/GPU

3. **Note**: Neo4j vector index needs to match dimensions
   ```cypher
   CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
   FOR (c:Chunk)
   ON (c.embedding)
   OPTIONS {
     indexConfig: {
       `vector.dimensions`: 384,
       `vector.similarity_function`: 'cosine'
     }
   }
   ```

### Option 3: Development Mode (Mock Embeddings)

In development environment, the service will generate mock embeddings if no model is available:

1. **Set environment to development**
   ```bash
   export ENVIRONMENT=development
   ```

2. **Mock embeddings are:**
   - Deterministic (same text = same embedding)
   - 1536 dimensions (OpenAI compatible)
   - Not suitable for production use
   - Good for testing API functionality

## Testing Your Configuration

### 1. Basic Embedding Test
```bash
curl -X POST "http://localhost:8001/api/learntrac/vector/search" \
  -H "Content-Type: application/json" \
  -H "Cookie: trac_auth=YOUR_TOKEN" \
  -d '{
    "query": "test query",
    "min_score": 0.5,
    "limit": 5
  }'
```

### 2. Enhanced Search Test
```bash
curl -X POST "http://localhost:8001/api/learntrac/vector/search/enhanced" \
  -H "Content-Type: application/json" \
  -H "Cookie: trac_auth=YOUR_TOKEN" \
  -d '{
    "query": "machine learning",
    "generate_sentences": 5,
    "min_score": 0.7,
    "limit": 10
  }'
```

## Troubleshooting

### Error: "Failed to generate embedding"

**Causes:**
1. No OpenAI API key configured
2. Invalid API key
3. OpenAI API rate limits
4. Network connectivity issues

**Solutions:**
1. Check environment variables: `echo $OPENAI_API_KEY`
2. Verify API key is valid
3. Wait and retry (rate limits)
4. Check network/firewall settings

### Error: "No embedding model available"

**Causes:**
1. Neither OpenAI nor local model configured
2. Import error for sentence-transformers

**Solutions:**
1. Configure OpenAI API key OR
2. Install sentence-transformers: `pip install sentence-transformers`
3. Set `ENVIRONMENT=development` for mock embeddings

### Different Embedding Dimensions

**Issue:** Neo4j index dimensions don't match embedding model

**Solution:** Recreate Neo4j vector index with correct dimensions:
- OpenAI: 1536 dimensions
- all-MiniLM-L6-v2: 384 dimensions
- all-mpnet-base-v2: 768 dimensions

## Performance Considerations

### OpenAI Embeddings
- **Pros:** High quality, no local compute needed
- **Cons:** API costs, network latency, rate limits
- **Speed:** ~100-500ms per embedding
- **Cost:** ~$0.00002 per 1K tokens

### Local Embeddings
- **Pros:** Free, no network latency, no rate limits
- **Cons:** Lower quality, requires local compute
- **Speed:** ~10-50ms per embedding (CPU)
- **Memory:** ~500MB model size

### Batch Processing
```python
# Efficient: Single API call for multiple texts
embeddings = await embedding_service.generate_embeddings_batch(
    ["text1", "text2", "text3"]
)

# Inefficient: Multiple API calls
for text in texts:
    embedding = await embedding_service.generate_embedding(text)
```

## Production Recommendations

1. **Use OpenAI for quality**: Better semantic understanding
2. **Cache embeddings**: Store in database to avoid regeneration
3. **Batch operations**: Process multiple texts together
4. **Monitor costs**: Track API usage and costs
5. **Implement fallback**: Local model as backup

## Environment Variables Summary

```bash
# Required for OpenAI embeddings
OPENAI_API_KEY=sk-your-key-here

# Optional configuration
ENVIRONMENT=production  # or development
LOG_LEVEL=INFO         # or DEBUG for troubleshooting

# For LLM features (question generation)
LLM_API_KEY=sk-your-key-here  # Can be same as OPENAI_API_KEY
API_GATEWAY_URL=https://api.openai.com/v1
```

## Security Notes

1. **Never commit API keys** to version control
2. **Use environment variables** or secure vaults
3. **Rotate keys regularly**
4. **Monitor usage** for unauthorized access
5. **Set spending limits** in OpenAI dashboard