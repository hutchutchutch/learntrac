# LearnTrac API Docker Configuration - Source of Truth

## Overview

This document serves as the definitive source for the LearnTrac API Docker configuration. After extensive troubleshooting, we have identified all dependency issues and created a working configuration.

## ✅ Current Working Configuration

### Environment Requirements

- **Neo4j**: Version 5.12.0 (running on port 7474/7687)
- **PostgreSQL**: Version 16 (running on port 5432)
- **Python**: Version 3.11-slim
- **API Port**: 8001

### Working Container

The API is currently running successfully in the `learntrac-api-final` container using:
- Docker Compose: `docker-compose.api-final.yml`
- Startup Script: `run-api-final.sh`

## 📋 Complete Dependencies

The following dependencies are required for the API to function properly:

```txt
aiofiles==23.2.1
aiohttp==3.9.0
aiosignal==1.4.0
alembic==1.12.0
annotated-types==0.7.0
anyio==3.7.1
async-timeout==5.0.1
asyncpg==0.29.0
attrs==25.3.0
bcrypt==4.1.2
certifi==2025.7.14
cffi==1.17.1
charset-normalizer==3.4.2
click==8.2.1
cryptography==41.0.0
distro==1.9.0
dnspython==2.7.0
ecdsa==0.18.0
email-validator==2.0.0
fastapi==0.104.0
frozenlist==1.7.0
greenlet==3.0.0
h11==0.14.0
httpcore==0.18.0
httptools==0.6.4
httpx==0.25.0
idna==3.10
Mako==1.3.0
MarkupSafe==3.0.2
multidict==6.6.3
neo4j==5.14.0
networkx==3.2
numpy==1.26.0
openai==1.3.0
pandas==2.1.0
passlib==1.7.4
pdfminer.six==20221105
pdfplumber==0.10.0
pillow==11.3.0
propcache==0.3.2
psycopg==3.2.9
psycopg-binary==3.2.9
psycopg-pool==3.2.6
pyasn1==0.5.0
pycparser==2.22
pydantic==2.5.0
pydantic-settings==2.1.0
pydantic_core==2.14.1
PyJWT==2.8.0
PyMuPDF==1.23.0
PyMuPDFb==1.23.0
pypdf==3.17.0
pypdfium2==4.30.0
python-dateutil==2.9.0.post0
python-dotenv==1.0.0
python-jose==3.3.0
python-multipart==0.0.6
pytz==2025.2
PyYAML==6.0.2
redis==5.0.0
rsa==4.9
six==1.17.0
sniffio==1.3.1
SQLAlchemy==2.0.0
starlette==0.27.0
tqdm==4.67.1
typing_extensions==4.8.0
tzdata==2025.2
uvicorn==0.24.0
uvloop==0.21.0
watchfiles==1.1.0
websockets==15.0.1
yarl==1.20.1
```

## 🐛 Issues Discovered and Fixed

### 1. Missing Python Dependencies

The original `requirements.txt` was missing several critical dependencies:
- `PyJWT` - Required for JWT authentication
- `email-validator` - Required for email validation in Pydantic
- `numpy` - Required for vector operations
- `aiofiles` - Required for async file operations
- `networkx` - Required for graph operations
- `python-jose` - Required for JWT operations
- `passlib` - Required for password hashing

### 2. Neo4j Compatibility Issues

- Neo4j 5.12 doesn't support `CREATE VECTOR INDEX` syntax
- Fixed by using regular indexes and in-memory cosine similarity calculations
- Index creation conflicts handled gracefully

### 3. Dependency Discovery Process

Dependencies were discovered iteratively as the container startup failed with import errors. Each missing module was identified through Docker logs and added to the requirements.

## 🚀 Recommended Production Setup

### Option 1: Pre-built Docker Image (Recommended)

Create a production Dockerfile with all dependencies:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
WORKDIR /app
COPY requirements-complete.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-complete.txt

# Copy application code
COPY . /app

# Set environment variables
ENV PYTHONPATH=/app
ENV NEO4J_URI=bolt://neo4j:7687
ENV NEO4J_PASSWORD=neo4jpassword
ENV DATABASE_URL=postgresql://learntrac:learntrac@postgres:5432/learntrac

# Expose API port
EXPOSE 8001

# Start the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Option 2: Docker Compose Configuration

Use the consolidated `docker-compose.yml`:

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.12.0
    environment:
      - NEO4J_AUTH=neo4j/neo4jpassword
      - NEO4J_PLUGINS=["apoc"]
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "wget -O /dev/null -q http://localhost:7474 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=learntrac
      - POSTGRES_PASSWORD=learntrac
      - POSTGRES_DB=learntrac
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U learntrac"]
      interval: 10s
      timeout: 5s
      retries: 5

  learntrac-api:
    build:
      context: ./learntrac-api
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=neo4jpassword
      - DATABASE_URL=postgresql://learntrac:learntrac@postgres:5432/learntrac
    depends_on:
      neo4j:
        condition: service_healthy
      postgres:
        condition: service_healthy
    volumes:
      - ./learntrac-api:/app
    command: ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

volumes:
  neo4j_data:
  postgres_data:
```

## 📁 File Structure

### Essential Files to Keep

1. **`/learntrac-api/requirements-complete.txt`** - Complete dependency list
2. **`/learntrac-api/Dockerfile`** - Production Dockerfile
3. **`/docker-compose.yml`** - Main Docker Compose configuration
4. **`/DOCKER_ERROR_ANALYSIS.md`** - This documentation (source of truth)

### Files to Remove (Redundant)

- All `run-api-*.sh` scripts in root directory
- Multiple `docker-compose.api-*.yml` variations
- Test and temporary Docker configurations
- Duplicate Dockerfiles in various directories

## 🧪 Testing the Setup

### 1. Start the Services

```bash
docker-compose up -d
```

### 2. Verify Health

```bash
# Check API health
curl http://localhost:8001/health

# Check Neo4j
curl http://localhost:7474

# Check PostgreSQL
docker exec -it learntrac_postgres_1 pg_isready
```

### 3. Test PDF Upload

```bash
# Upload a PDF
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@Introduction_To_Computer_Science.pdf"
```

## 🔧 Development Tips

### Hot Reloading

The development setup includes volume mounts for hot reloading. Changes to the API code will automatically restart the server.

### Debugging

To debug dependency issues:

```bash
# Check logs
docker-compose logs learntrac-api

# Enter container shell
docker exec -it learntrac-api /bin/bash

# Check installed packages
docker exec learntrac-api pip list
```

### Adding New Dependencies

1. Add to `requirements-complete.txt`
2. Rebuild the Docker image: `docker-compose build learntrac-api`
3. Restart the container: `docker-compose restart learntrac-api`

## 🚦 Next Steps

1. Test PDF upload functionality with Introduction_To_Computer_Science.pdf
2. Verify vector storage in Neo4j
3. Test learning endpoints
4. Set up CI/CD pipeline with proper Docker image building
5. Configure production environment variables
6. Set up monitoring and logging

## 📝 Notes

- The API requires both Neo4j and PostgreSQL to be running
- Vector similarity search is handled in-memory due to Neo4j 5.12 limitations
- All sensitive credentials should be moved to environment variables in production
- Consider using Docker secrets for password management in production

---

Last Updated: $(date)
Container Status: ✅ Running Successfully