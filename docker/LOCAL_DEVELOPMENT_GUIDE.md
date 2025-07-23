# Local Development Guide for LearnTrac

This guide explains how to run both Trac and LearnTrac API containers locally with inter-container communication.

## Overview

The LearnTrac system consists of two main components:
- **Trac Legacy System** (Port 8000) - Python 2.7 based issue tracking system
- **LearnTrac API** (Port 8001) - Modern FastAPI-based learning management API

## Quick Start

### 1. Basic Local Setup (with local PostgreSQL & Redis)

```bash
cd docker
./run-local-integrated.sh
```

This will:
- Start local PostgreSQL and Redis containers
- Build and start Trac and LearnTrac API containers
- Set up inter-container networking
- Run health checks
- Display service URLs

### 2. Using AWS Resources (RDS & ElastiCache)

```bash
cd docker
./run-local-integrated.sh --aws-db
```

This will:
- Connect to AWS RDS PostgreSQL instead of local
- Connect to AWS ElastiCache Redis instead of local
- Requires AWS credentials configured

## Container Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Network: learntrac-network      │
├─────────────────┬───────────────┬───────────┬──────────┤
│                 │               │           │          │
│   Trac          │  LearnTrac    │  Postgres │  Redis   │
│   (trac:8000)   │  (api:8001)   │  (5432)   │  (6379)  │
│                 │               │           │          │
│   ↓ ↑           │    ↓ ↑        │     ↑     │    ↑     │
│   Can communicate internally using container names      │
└─────────────────────────────────────────────────────────┘
         ↓                ↓
   localhost:8000   localhost:8001  (External access)
```

## Inter-Container Communication

### Container Names and Internal URLs

Within the Docker network, containers can reach each other using:

- **Trac → API**: `http://learntrac-api:8001`
- **API → Trac**: `http://trac:8000`
- **Both → PostgreSQL**: `postgres:5432`
- **Both → Redis**: `redis:6379`

### Testing Communication

Run the comprehensive test suite:

```bash
./test-inter-communication.sh
```

This tests:
- Network connectivity between containers
- HTTP endpoint accessibility
- Shared database access
- DNS resolution
- Authentication configuration

## Development Workflows

### 1. Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f trac
docker-compose logs -f learntrac-api

# Last 100 lines
docker-compose logs --tail=100 trac
```

### 2. Accessing Container Shell

```bash
# Trac container
docker exec -it trac-local /bin/bash

# API container
docker exec -it learntrac-api-local /bin/bash

# PostgreSQL
docker exec -it postgres-local psql -U learntrac

# Redis
docker exec -it redis-local redis-cli
```

### 3. Testing API Endpoints

From host machine:
```bash
# API health check
curl http://localhost:8001/health | jq .

# Get courses
curl http://localhost:8001/api/learntrac/courses | jq .

# API documentation
open http://localhost:8001/docs
```

From Trac container (inter-container):
```bash
docker exec trac-local curl http://learntrac-api:8001/api/learntrac/courses
```

### 4. Testing Database Connectivity

```bash
# From API container
docker exec learntrac-api-local python -c "
import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect('postgresql://learntrac:localpass123@postgres/learntrac')
    version = await conn.fetchval('SELECT version()')
    print(f'Connected to: {version}')
    await conn.close()

asyncio.run(test())
"

# Direct PostgreSQL access
docker exec -it postgres-local psql -U learntrac -c "SELECT current_database();"
```

### 5. Testing Redis Connectivity

```bash
# From API container
docker exec learntrac-api-local python -c "
import redis
r = redis.Redis(host='redis', port=6379)
r.set('test', 'hello')
print(f'Redis test: {r.get(\"test\").decode()}')
"

# Direct Redis access
docker exec redis-local redis-cli PING
```

## Environment Variables

### Required for Both Services
- `COGNITO_USER_POOL_ID` - AWS Cognito User Pool ID
- `COGNITO_CLIENT_ID` - AWS Cognito App Client ID
- `COGNITO_DOMAIN` - Cognito hosted UI domain
- `AWS_REGION` - AWS region for Cognito

### Trac-Specific
- `DATABASE_URL` - PostgreSQL connection string
- `TRAC_ENV` - Trac environment path
- `LEARNTRAC_API_URL` - Internal URL to reach LearnTrac API

### API-Specific
- `DATABASE_URL` - PostgreSQL connection (asyncpg format)
- `REDIS_URL` - Redis connection string
- `BASE_URL` - Public base URL for the API
- `TRAC_URL` - Internal URL to reach Trac

## Debugging

### 1. Container Won't Start

```bash
# Check logs
docker-compose logs trac

# Check if port is already in use
lsof -i :8000
lsof -i :8001

# Rebuild image
docker-compose build --no-cache trac
```

### 2. Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Test connection
docker exec postgres-local pg_isready

# Check credentials
docker-compose exec postgres psql -U learntrac -c "\l"
```

### 3. Inter-Container Communication Issues

```bash
# Check network
docker network ls
docker network inspect docker_learntrac-network

# Test DNS resolution
docker exec trac-local ping -c 1 learntrac-api
docker exec learntrac-api-local ping -c 1 trac

# Check container IPs
docker inspect trac-local | jq '.[0].NetworkSettings.Networks'
```

### 4. Authentication Issues

```bash
# Verify Cognito configuration
docker exec trac-local printenv | grep COGNITO
docker exec learntrac-api-local printenv | grep COGNITO

# Test login redirect
curl -v http://localhost:8000/login
curl -v http://localhost:8001/login
```

## Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Restart a specific service
docker-compose restart trac

# View service status
docker-compose ps

# Build images
docker-compose build

# Pull latest base images
docker-compose pull

# Execute command in service
docker-compose exec trac /bin/bash
```

## Adding Inter-Service Communication

To enable Trac to call LearnTrac API:

```python
# In Trac plugin
import urllib2
import json

api_url = os.environ.get('LEARNTRAC_API_URL', 'http://learntrac-api:8001')
response = urllib2.urlopen(f"{api_url}/api/learntrac/courses")
courses = json.loads(response.read())
```

To enable API to call Trac:

```python
# In LearnTrac API
import httpx

trac_url = os.environ.get('TRAC_URL', 'http://trac:8000')
async with httpx.AsyncClient() as client:
    response = await client.get(f"{trac_url}/wiki/SomePage")
```

## Production Considerations

When deploying to production:

1. **Remove hardcoded passwords** - Use AWS Secrets Manager
2. **Enable HTTPS** - Add SSL certificates
3. **Update Cognito URLs** - Use production domain
4. **Set proper CORS** - Configure allowed origins
5. **Add monitoring** - CloudWatch, DataDog, etc.
6. **Scale services** - Multiple container instances
7. **Use managed services** - RDS, ElastiCache, etc.

## Troubleshooting Checklist

- [ ] All containers are running: `docker-compose ps`
- [ ] Containers are healthy: Check health status
- [ ] Network exists: `docker network ls | grep learntrac`
- [ ] Ports are not blocked: `lsof -i :8000,8001`
- [ ] Environment variables are set: Check `.env` file
- [ ] Database is accessible: Test with psql
- [ ] Redis is accessible: Test with redis-cli
- [ ] Logs show no errors: `docker-compose logs`
- [ ] Inter-container DNS works: Test with ping
- [ ] HTTP endpoints respond: Test with curl