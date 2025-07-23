# First Steps: Local Docker Testing & Verification

This document outlines the process for building, testing, and verifying both Docker images locally before deploying to AWS. This ensures all containers are functioning correctly and reduces debugging time in the cloud.

## Prerequisites

- Docker Desktop installed and running
- Python 3.11 (for testing LearnTrac API locally)
- Python 2.7 (for testing Trac locally, if needed)
- AWS CLI configured with credentials
- curl or httpie for API testing
- Access to AWS RDS PostgreSQL instance (already deployed)

## Step 1: Create Docker Images with Proper Testing

### 1.1 Trac Docker Image (Python 2.7)

First, let's create a proper Trac image that will actually run:

```bash
# Create directory structure
mkdir -p docker/trac/{scripts,config,templates}

# Create Dockerfile for Trac
cat > docker/trac/Dockerfile << 'EOF'
FROM python:2.7-slim-buster

# Fix Debian archive issues for old release
RUN echo "deb http://archive.debian.org/debian/ buster main" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security buster/updates main" >> /etc/apt/sources.list && \
    echo "Acquire::Check-Valid-Until false;" > /etc/apt/apt.conf.d/99no-check-valid-until

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    git \
    subversion \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Trac and dependencies
RUN pip install --no-cache-dir \
    Trac==1.4.4 \
    psycopg2==2.8.6 \
    Genshi==0.7.7 \
    Babel==2.9.1 \
    Pygments==2.5.2 \
    pytz \
    gunicorn==19.10.0

# Create Trac environment directory
RUN mkdir -p /var/trac/projects

# Copy configuration and scripts
COPY scripts/start-trac.sh /usr/local/bin/
COPY scripts/init-trac.py /usr/local/bin/
COPY config/trac.ini.template /app/config/

RUN chmod +x /usr/local/bin/start-trac.sh

# Create health check script
COPY scripts/health-check.py /usr/local/bin/
RUN chmod +x /usr/local/bin/health-check.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python /usr/local/bin/health-check.py || exit 1

CMD ["/usr/local/bin/start-trac.sh"]
EOF

# Create startup script
cat > docker/trac/scripts/start-trac.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting Trac..."

# Initialize Trac environment if it doesn't exist
if [ ! -f /var/trac/projects/trac.db ]; then
    echo "Initializing new Trac environment..."
    python /usr/local/bin/init-trac.py
fi

# Start Trac using Gunicorn
exec gunicorn --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    trac.web.standalone:application
EOF

# Create Trac initialization script
cat > docker/trac/scripts/init-trac.py << 'EOF'
#!/usr/bin/env python
import os
import sys
from trac.admin.console import TracAdmin
from trac.env import Environment

trac_env_path = '/var/trac/projects'

# Create basic Trac environment
admin = TracAdmin(trac_env_path)
admin.do_initenv('LearnTrac Legacy', 'sqlite:db/trac.db')

# Initialize with basic configuration
env = Environment(trac_env_path)
config = env.config

# Basic settings
config.set('project', 'name', 'LearnTrac Legacy System')
config.set('project', 'descr', 'Legacy Trac instance for LearnTrac')
config.set('trac', 'base_url', 'http://localhost:8000')

# Save configuration
config.save()

print("Trac environment initialized successfully")
EOF

# Create health check script
cat > docker/trac/scripts/health-check.py << 'EOF'
#!/usr/bin/env python
import urllib2
import sys

try:
    response = urllib2.urlopen('http://localhost:8000/login', timeout=2)
    if response.getcode() == 200:
        sys.exit(0)
except:
    pass
sys.exit(1)
EOF

# Create basic trac.ini template
cat > docker/trac/config/trac.ini.template << 'EOF'
[components]
trac.web.auth.loginmodule = disabled

[project]
name = LearnTrac Legacy
descr = Legacy Trac system

[trac]
base_url = http://localhost:8000
EOF
```

### 1.2 LearnTrac API Docker Image (Python 3.11)

Create a proper FastAPI application:

```bash
# Create directory structure
mkdir -p docker/learntrac/{src,scripts,tests}

# Create Dockerfile for LearnTrac
cat > docker/learntrac/Dockerfile << 'EOF'
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/start-api.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-api.sh

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["/usr/local/bin/start-api.sh"]
EOF

# Create comprehensive requirements.txt
cat > docker/learntrac/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg[binary,pool]==3.1.12
pydantic==2.5.0
pydantic-settings==2.1.0
redis==5.0.1
httpx==0.25.2
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
EOF

# Create the main FastAPI application
cat > docker/learntrac/src/main.py << 'EOF'
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LearnTrac API",
    description="Modern Learning Management System API",
    version="1.0.0"
)

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime
    version: str
    environment: dict

@app.get("/")
async def root():
    return {"message": "Welcome to LearnTrac API", "version": "1.0.0"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for ALB"""
    return HealthResponse(
        status="healthy",
        service="learntrac-api",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        environment={
            "python_version": "3.11",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    )

@app.get("/api/learntrac/health")
async def api_health():
    """API-specific health check"""
    return {
        "status": "healthy",
        "api_version": "v1",
        "endpoints_available": [
            "/courses",
            "/users",
            "/enrollments",
            "/progress"
        ]
    }

@app.get("/api/learntrac/courses")
async def list_courses():
    """List available courses"""
    # Placeholder implementation
    return {
        "courses": [
            {"id": 1, "title": "Introduction to Python", "duration": "4 weeks"},
            {"id": 2, "title": "Advanced FastAPI", "duration": "3 weeks"},
            {"id": 3, "title": "Docker Mastery", "duration": "2 weeks"}
        ],
        "total": 3
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": str(type(exc).__name__)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
EOF

# Create startup script
cat > docker/learntrac/scripts/start-api.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting LearnTrac API..."
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --log-level info \
    --access-log \
    --use-colors
EOF
```

## Step 2: Local Testing Procedures

### 2.1 Build Images Locally

```bash
# Build Trac image
cd docker/trac
docker build -t learntrac/trac:test .

# Build LearnTrac API image  
cd ../learntrac
docker build -t learntrac/api:test .
```

### 2.2 Run Containers Locally with AWS RDS Connection

First, get the database credentials from AWS Secrets Manager:

```bash
# Get database credentials from Secrets Manager
DB_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id hutch-learntrac-dev-db-credentials \
  --region us-east-2 \
  --query SecretString --output text)

# Extract credentials
DB_USERNAME=$(echo $DB_SECRET | jq -r .username)
DB_PASSWORD=$(echo $DB_SECRET | jq -r .password)
DB_HOST=$(echo $DB_SECRET | jq -r .host)
DB_NAME=$(echo $DB_SECRET | jq -r .dbname)

# Get Redis endpoint
REDIS_ENDPOINT=$(cd learntrac-infrastructure && terraform output -raw redis_endpoint)
```

Run containers with AWS connections:

```bash
# Create a local network for testing
docker network create learntrac-test

# Run Trac container with RDS connection
docker run -d \
  --name trac-test \
  --network learntrac-test \
  -p 8000:8000 \
  -e TRAC_ENV=/var/trac/projects \
  -e DATABASE_URL="postgres://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}" \
  learntrac/trac:test

# Run LearnTrac API container with RDS and Redis connections
docker run -d \
  --name learntrac-test \
  --network learntrac-test \
  -p 8001:8001 \
  -e ENVIRONMENT=local \
  -e DATABASE_URL="postgresql+asyncpg://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}" \
  -e REDIS_URL="redis://${REDIS_ENDPOINT}:6379" \
  learntrac/api:test
```

Note: Your local machine must have network access to AWS RDS. The RDS security group should allow connections from your IP address.

### 2.2.1 Verify AWS Connectivity

Before running containers, verify you can connect to AWS services:

```bash
# Test RDS connectivity (requires psql)
psql "postgres://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}" -c "SELECT version();"

# Test Redis connectivity (requires redis-cli)
redis-cli -h ${REDIS_ENDPOINT} ping

# If you don't have psql or redis-cli, test with telnet
telnet ${DB_HOST} 5432
telnet ${REDIS_ENDPOINT} 6379

# Check your current IP (to add to RDS security group if needed)
curl -s https://checkip.amazonaws.com
```

If connections fail, update the RDS security group to allow your IP:

```bash
# Get your current IP
MY_IP=$(curl -s https://checkip.amazonaws.com)

# Update RDS security group (replace sg-xxx with actual security group ID)
aws ec2 authorize-security-group-ingress \
  --group-id sg-099f0e67fcf8b6870 \
  --protocol tcp \
  --port 5432 \
  --cidr ${MY_IP}/32 \
  --region us-east-2
```

### 2.3 Verify Container Health

```bash
# Check container status
docker ps --filter name=trac-test --filter name=learntrac-test

# Check container logs
docker logs trac-test
docker logs learntrac-test

# Verify health checks
docker inspect trac-test --format='{{.State.Health.Status}}'
docker inspect learntrac-test --format='{{.State.Health.Status}}'
```

## Step 3: Functional Testing

### 3.1 Test Trac Endpoints

```bash
# Test Trac root
curl -i http://localhost:8000/
# Expected: HTTP 200 with Trac interface

# Test Trac login page
curl -i http://localhost:8000/login
# Expected: HTTP 200 with login form

# Test Trac wiki
curl -i http://localhost:8000/wiki
# Expected: HTTP 200 or redirect
```

### 3.2 Test LearnTrac API Endpoints

```bash
# Test API root
curl -i http://localhost:8001/
# Expected: {"message": "Welcome to LearnTrac API", "version": "1.0.0"}

# Test health endpoint
curl -i http://localhost:8001/health
# Expected: JSON with status "healthy"

# Test API health
curl -i http://localhost:8001/api/learntrac/health
# Expected: JSON with api_version and endpoints

# Test courses endpoint
curl -i http://localhost:8001/api/learntrac/courses
# Expected: JSON with course list

# Test API documentation
curl -i http://localhost:8001/docs
# Expected: FastAPI automatic documentation
```

### 3.3 Load Testing

```bash
# Simple load test for Trac
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" http://localhost:8000/ &
done
wait

# Simple load test for API
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" http://localhost:8001/health &
done
wait
```

## Step 4: Docker Compose Testing with AWS Services

Create a docker-compose file for integrated testing with AWS RDS and Redis:

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  trac:
    build: ./docker/trac
    ports:
      - "8000:8000"
    environment:
      - TRAC_ENV=/var/trac/projects
      - DATABASE_URL=${DATABASE_URL_TRAC}
    healthcheck:
      test: ["CMD", "python", "/usr/local/bin/health-check.py"]
      interval: 30s
      timeout: 3s
      retries: 3
    extra_hosts:
      - "host.docker.internal:host-gateway"

  api:
    build: ./docker/learntrac
    ports:
      - "8001:8001"
    environment:
      - ENVIRONMENT=local
      - DATABASE_URL=${DATABASE_URL_API}
      - REDIS_URL=${REDIS_URL}
      - AWS_REGION=us-east-2
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 3s
      retries: 3
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Create an `.env` file with AWS credentials:

```bash
# Create .env file for docker-compose
cat > .env << EOF
DATABASE_URL_TRAC=postgres://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}
DATABASE_URL_API=postgresql+asyncpg://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}
REDIS_URL=redis://${REDIS_ENDPOINT}:6379
EOF
```

Run integrated tests:

```bash
# Start all services
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be healthy
docker-compose -f docker-compose.test.yml ps

# Run integration tests
./scripts/integration-test.sh

# View logs
docker-compose -f docker-compose.test.yml logs

# Stop services
docker-compose -f docker-compose.test.yml down
```

## Step 5: Pre-Push Checklist

Before pushing to AWS ECR, verify:

### Container Checks:
- [ ] Both containers build without errors
- [ ] Both containers start and remain running for >5 minutes
- [ ] Health checks pass consistently
- [ ] No error logs in container output
- [ ] Memory usage is reasonable (<500MB for each)
- [ ] CPU usage is reasonable (<50% on average)

### Endpoint Checks:
- [ ] Trac responds on port 8000
- [ ] API responds on port 8001  
- [ ] Health endpoints return correct status
- [ ] All expected paths return valid responses
- [ ] Error handling works (test 404s)

### Integration Checks:
- [ ] Containers can communicate on same network
- [ ] Database connections work (if configured)
- [ ] Redis connections work (if configured)
- [ ] Environment variables are properly used
- [ ] Logs are properly formatted and useful

## Step 6: Push to ECR

Only after all local tests pass:

```bash
# Tag images for ECR
docker tag learntrac/trac:test 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest
docker tag learntrac/api:test 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac:latest

# Login to ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 971422717446.dkr.ecr.us-east-2.amazonaws.com

# Push images
docker push 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest
docker push 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac:latest
```

## Troubleshooting Common Issues

### Container Exits Immediately
- Check logs: `docker logs container-name`
- Verify CMD/ENTRYPOINT syntax
- Check file permissions on scripts
- Ensure all required files are COPYed

### Health Check Fails
- Exec into container: `docker exec -it container-name /bin/bash`
- Test health endpoint manually
- Check if service is actually listening on port
- Verify health check command syntax

### Cannot Connect to Container
- Check port mapping: `docker port container-name`
- Verify service binds to 0.0.0.0, not localhost
- Check firewall rules
- Test from inside container first

### Memory/CPU Issues
- Monitor with: `docker stats`
- Check for memory leaks
- Optimize application startup
- Consider multi-stage builds

## Important Notes on AWS Resources

### RDS PostgreSQL Database
- **Endpoint**: `hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com:5432`
- **Database Name**: `learntrac`
- **Credentials**: Stored in AWS Secrets Manager (`hutch-learntrac-dev-db-credentials`)
- **Security Group**: Must allow inbound PostgreSQL (5432) from your IP and ECS tasks

### Redis Cluster
- **Endpoint**: Available via Terraform output
- **Port**: 6379
- **Security Group**: Must allow inbound Redis (6379) from ECS tasks

### Environment Variables in ECS
The ECS task definitions automatically inject these environment variables:
- Trac: `DATABASE_URL` with postgres:// format
- LearnTrac API: `DATABASE_URL` with postgresql+asyncpg:// format, `REDIS_URL`, Cognito settings

## Next Steps

After successful local testing:
1. Push images to ECR
2. Update ECS services
3. Monitor CloudWatch logs
4. Test via ALB endpoints
5. Set up automated CI/CD pipeline

Remember: Time spent testing locally saves hours of debugging in AWS!