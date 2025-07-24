# Docker Containers Testing Guide - Step by Step

This guide provides detailed instructions for launching and testing the two Docker containers:
- **Trac** (Python 2.7) - Legacy issue tracking system
- **LearnTrac API** (Python 3.11) - Modern API service

## Prerequisites

Before starting, ensure you have:
- Docker installed and running
- Docker Compose installed
- Terminal access to the project root directory
- AWS credentials configured (if pushing to ECR)

## Container Overview

### 1. Trac Container (Python 2.7)
- **Base Image**: `python:2.7-slim-buster`
- **Port**: 8000
- **Dockerfile**: `docker/trac/Dockerfile`
- **Purpose**: Legacy Trac issue tracking system with Cognito authentication

### 2. LearnTrac API Container (Python 3.11)
- **Base Image**: `python:3.11-slim`
- **Port**: 8001
- **Dockerfile**: `docker/learntrac/Dockerfile`
- **Purpose**: Modern FastAPI-based API service

## Step 1: Prepare the Environment

```bash
# Navigate to project root
cd /path/to/learntrac

# Create .env file if it doesn't exist
cat > .env << 'EOF'
# Database URLs
DATABASE_URL_TRAC=sqlite:///var/trac/projects/trac.db
DATABASE_URL_API=postgresql://learntrac:learntrac@postgres:5432/learntrac

# AWS Configuration
AWS_REGION=us-east-2
COGNITO_DOMAIN=hutch-learntrac-dev-auth
COGNITO_CLIENT_ID=your-client-id-here
COGNITO_POOL_ID=your-pool-id-here

# Redis Configuration
REDIS_URL=redis://redis:6379

# Environment
ENVIRONMENT=local
EOF
```

## Step 2: Build Docker Images Locally

### Build Trac Container (Python 2.7)

```bash
# Build the Trac image
docker build -t learntrac/trac:local -f docker/trac/Dockerfile docker/trac/

# Verify the image was built
docker images | grep learntrac/trac
```

### Build LearnTrac API Container (Python 3.11)

```bash
# First, ensure requirements.txt exists in docker/learntrac/
cp learntrac-api/requirements.txt docker/learntrac/requirements.txt

# Copy source code
cp -r learntrac-api/src docker/learntrac/

# Build the LearnTrac API image
docker build -t learntrac/api:local -f docker/learntrac/Dockerfile docker/learntrac/

# Verify the image was built
docker images | grep learntrac/api
```

## Step 3: Run Containers Individually (for testing)

### Test Trac Container

```bash
# Run Trac container standalone
docker run -d \
  --name trac-test \
  -p 8000:8000 \
  -e TRAC_ENV=/var/trac/projects \
  -e DATABASE_URL=sqlite:///var/trac/projects/trac.db \
  -e COGNITO_DOMAIN=hutch-learntrac-dev-auth \
  -e COGNITO_CLIENT_ID=test-client-id \
  -e AWS_REGION=us-east-2 \
  learntrac/trac:local

# Check container logs
docker logs trac-test

# Test the health check
curl http://localhost:8000/trac/login

# Stop and remove test container
docker stop trac-test && docker rm trac-test
```

### Test LearnTrac API Container

```bash
# Run LearnTrac API container standalone
docker run -d \
  --name learntrac-test \
  -p 8001:8001 \
  -e ENVIRONMENT=local \
  -e DATABASE_URL=postgresql://learntrac:learntrac@localhost:5432/learntrac \
  -e REDIS_URL=redis://localhost:6379 \
  -e AWS_REGION=us-east-2 \
  learntrac/api:local

# Check container logs
docker logs learntrac-test

# Test the health endpoint
curl http://localhost:8001/api/learntrac/health

# Stop and remove test container
docker stop learntrac-test && docker rm learntrac-test
```

## Step 4: Run Both Containers with Docker Compose

### Using the test docker-compose file

```bash
# Run both containers with docker-compose
docker-compose -f docker-compose.test.yml up -d

# View running containers
docker-compose -f docker-compose.test.yml ps

# Check logs for both services
docker-compose -f docker-compose.test.yml logs -f
```

## Step 5: Verify Container Health

### Check Container Status

```bash
# List running containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check resource usage
docker stats --no-stream
```

### Test Trac Endpoints

```bash
# Test Trac root page (shows available projects)
curl -v http://localhost:8000/

# Expected response: HTML page with "Available Projects" listing "LearnTrac Legacy"

# Note: The Trac instance uses tracd which serves projects at the root level
# Individual project pages may have authentication requirements
```

### Test LearnTrac API Endpoints

```bash
# Test health endpoint
curl -v http://localhost:8001/api/learntrac/health | python -m json.tool

# Test root endpoint
curl -v http://localhost:8001/ | python -m json.tool

# Test API documentation
curl -v http://localhost:8001/docs
```

## Step 6: Debug Common Issues

### Trac Container Issues

```bash
# Check Trac logs in detail
docker exec trac-test cat /var/trac/projects/log/trac.log

# Access Trac container shell
docker exec -it trac-test /bin/bash

# Inside container, test Trac initialization
python /usr/local/bin/init-trac.py
```

### LearnTrac API Container Issues

```bash
# Check API logs
docker logs learntrac-test --tail 50

# Access API container shell
docker exec -it learntrac-test /bin/bash

# Inside container, test API startup
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

## Step 7: Performance Testing

### Test Container Startup Time

```bash
# Time Trac container startup
time docker run --rm learntrac/trac:local python -c "print('Trac container ready')"

# Time LearnTrac API container startup
time docker run --rm learntrac/api:local python -c "print('API container ready')"
```

### Test Memory Usage

```bash
# Monitor memory usage during operation
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## Step 8: Integration Testing

### Test Container Communication

```bash
# Create a test network
docker network create test-network

# Run containers on the same network
docker run -d --name trac-net --network test-network learntrac/trac:local
docker run -d --name api-net --network test-network learntrac/api:local

# Test API can reach Trac
docker exec api-net curl http://trac-net:8000/trac/login

# Cleanup
docker stop trac-net api-net && docker rm trac-net api-net
docker network rm test-network
```

## Step 9: Push to ECR (if needed)

```bash
# Login to ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin [your-ecr-url]

# Tag images for ECR
docker tag learntrac/trac:local [your-ecr-url]/hutch-learntrac-dev-trac:latest
docker tag learntrac/api:local [your-ecr-url]/hutch-learntrac-dev-learntrac:latest

# Push to ECR
docker push [your-ecr-url]/hutch-learntrac-dev-trac:latest
docker push [your-ecr-url]/hutch-learntrac-dev-learntrac:latest
```

## Step 10: Cleanup

```bash
# Stop all containers
docker-compose -f docker-compose.test.yml down

# Remove volumes (optional - this will delete data)
docker-compose -f docker-compose.test.yml down -v

# Remove images (optional)
docker rmi learntrac/trac:local learntrac/api:local
```

## Expected Results

### Successful Trac Container (Python 2.7)
- Container starts without errors
- Health check returns HTTP 200 on `/trac/login`
- Logs show "Starting Trac..." and "Trac Test Container - Health Check OK"
- No Python 2.7 compatibility errors

### Successful LearnTrac API Container (Python 3.11)
- Container starts without errors
- Health check returns JSON response on `/api/learntrac/health`
- FastAPI documentation available at `/docs`
- Uvicorn logs show "Application startup complete"

## Troubleshooting Guide

### Common Issues and Solutions

1. **Port Already in Use**
   ```bash
   # Find process using port
   lsof -i :8000  # or :8001
   
   # Kill the process or use different ports
   docker run -p 8080:8000 ...
   ```

2. **Container Exits Immediately**
   ```bash
   # Check exit code and logs
   docker ps -a
   docker logs [container-name]
   ```

3. **Permission Issues**
   ```bash
   # Fix file permissions
   chmod +x docker/trac/scripts/start-trac.sh
   chmod +x docker/learntrac/scripts/start-api.sh
   ```

4. **Missing Dependencies**
   ```bash
   # Rebuild with no cache
   docker build --no-cache -t learntrac/trac:local -f docker/trac/Dockerfile docker/trac/
   ```

5. **Network Issues**
   ```bash
   # Check Docker network
   docker network ls
   docker network inspect bridge
   ```

## Health Check Scripts

### Create automated health check script

```bash
cat > test-containers-health.sh << 'EOF'
#!/bin/bash

echo "Testing Docker Containers Health..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Test Trac
echo -n "Testing Trac (Python 2.7) on port 8000... "
if curl -s -f http://localhost:8000/trac/login > /dev/null; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

# Test LearnTrac API
echo -n "Testing LearnTrac API (Python 3.11) on port 8001... "
if curl -s -f http://localhost:8001/api/learntrac/health > /dev/null; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

# Container status
echo -e "\nContainer Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(trac|learntrac)"
EOF

chmod +x test-containers-health.sh
./test-containers-health.sh
```

## Summary

This guide covers:
- Building and testing both Python 2.7 (Trac) and Python 3.11 (LearnTrac) containers
- Running containers individually and with docker-compose
- Testing endpoints and health checks
- Debugging common issues
- Performance monitoring
- Integration testing between containers

The key difference between the containers:
- **Trac (Python 2.7)**: Legacy system requiring special Debian archive configuration
- **LearnTrac (Python 3.11)**: Modern FastAPI application with current Python features

## Quick Test Commands

After building the images:

```bash
# Using docker-compose (recommended)
docker compose -f docker-compose.test.yml up -d

# Test Trac (Python 2.7)
curl http://localhost:8000/

# Test LearnTrac API (Python 3.11)
curl http://localhost:8001/api/learntrac/health

# View logs
docker compose -f docker-compose.test.yml logs -f

# Stop containers
docker compose -f docker-compose.test.yml down
```