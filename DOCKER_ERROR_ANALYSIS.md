# LearnTrac API Docker Error Analysis

## Summary of Issues Found

### 1. Missing Python Dependencies
The API has cascading dependency issues when running in Docker. Each time we fix one missing module, another appears:

- Initial: `PyJWT` → Added
- Then: `email-validator` → Added  
- Then: `numpy` → Added
- Then: `aiofiles` → Added
- Then: `networkx` → Added
- Then: `jose` (from `python-jose`) → Added
- Then: `passlib` → Added

### 2. Neo4j Version Compatibility
- Neo4j 5.12 doesn't support `CREATE VECTOR INDEX` syntax
- We updated the code to use regular indexes and in-memory cosine similarity

### 3. Root Causes

1. **Incomplete requirements.txt**: The original requirements.txt is missing many dependencies that are imported in the code
2. **Import order**: Dependencies are discovered one by one as imports fail
3. **Different dependency names**: Some packages have different names than their imports (e.g., `python-jose` vs `jose`)

### 4. Current Status

We've created multiple approaches to get the API running:

1. **run-api-simple.sh**: Basic dependency installation
2. **run-api-comprehensive.sh**: More complete dependency list
3. **run-api-final.sh**: Final version with all discovered dependencies including `passlib`

## Recommended Solution

### Option 1: Create a Complete requirements.txt

```bash
# Generate a complete requirements.txt from the running environment
pip freeze > learntrac-api/requirements-complete.txt
```

### Option 2: Use a Pre-built Docker Image

Create a Dockerfile that includes all dependencies:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-complete.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-complete.txt

WORKDIR /app
COPY . /app

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Option 3: Use Poetry or Pipenv

Move to a more robust dependency management system that handles transitive dependencies better.

## Next Steps

1. Once the API starts successfully, we need to:
   - Test the PDF upload functionality
   - Process the Introduction_To_Computer_Science.pdf
   - Verify vector storage in Neo4j
   - Test the learning endpoints

2. Consider creating a development environment that's easier to work with:
   - Use docker-compose with volume mounts for hot reloading
   - Pre-build base image with all dependencies
   - Use environment-specific configuration files

## Temporary Workaround

For immediate testing, you can run the API locally (outside Docker) with:

```bash
cd learntrac-api
pip install -r requirements.txt
pip install PyJWT email-validator numpy aiofiles networkx python-jose passlib
python -m uvicorn src.main:app --reload --port 8001
```

This avoids the Docker complexity while we fix the dependency issues properly.