# LearnTrac Docker Setup

This directory contains everything needed to run LearnTrac locally with Docker.

## Quick Start

### Option 1: Full Local Environment (Recommended)
```bash
# Run with local PostgreSQL and Redis
./run-local-integrated.sh

# Access services at:
# - Trac: http://localhost:8000
# - API: http://localhost:8001
# - API Docs: http://localhost:8001/docs
```

### Option 2: Using AWS Services
```bash
# Run with AWS RDS and ElastiCache
./run-local-integrated.sh --aws-db
```

### Option 3: Quick Test (No Database)
```bash
# Just run the containers for basic testing
./quick-test.sh
```

## Directory Structure

```
docker/
├── docker-compose.yml           # Full stack configuration
├── run-local-integrated.sh      # Main run script
├── test-inter-communication.sh  # Communication tests
├── test-local.sh               # AWS-connected test script
├── quick-test.sh               # Basic container test
├── .env.example                # Environment template
│
├── trac/                       # Trac Legacy System
│   ├── Dockerfile
│   ├── config/
│   ├── plugins/               # Cognito auth plugin
│   ├── scripts/               # Startup scripts
│   └── templates/
│
└── learntrac/                  # Modern API
    ├── Dockerfile
    ├── requirements.txt
    ├── src/                    # API source code
    └── scripts/                # Startup scripts
```

## Key Features

### 🔗 Inter-Container Communication
- Containers can communicate using service names
- Shared Docker network for internal communication
- Environment variables for service discovery

### 🔐 Authentication
- AWS Cognito integration for both services
- Shared authentication configuration
- OAuth 2.0 for Trac, JWT for API

### 📊 Database & Cache
- Local PostgreSQL or AWS RDS
- Local Redis or AWS ElastiCache
- Automatic health checks

### 🧪 Testing
- Comprehensive test suite for communication
- Health check endpoints
- Performance testing

## Common Commands

### Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild images
docker-compose build
```

### Container Access
```bash
# Shell access
docker exec -it trac-local /bin/bash
docker exec -it learntrac-api-local /bin/bash

# Database access
docker exec -it postgres-local psql -U learntrac

# Redis access
docker exec -it redis-local redis-cli
```

### Testing
```bash
# Test inter-container communication
./test-inter-communication.sh

# Test specific endpoint from Trac to API
docker exec trac-local curl http://learntrac-api:8001/api/learntrac/courses

# Test API to Trac connection
docker exec learntrac-api-local curl http://trac:8000
```

## Environment Variables

Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
# Edit .env with your Cognito credentials
```

## Troubleshooting

### Containers won't start
```bash
# Check if ports are in use
lsof -i :8000,8001

# Clean up and retry
docker-compose down -v
./run-local-integrated.sh
```

### Communication issues
```bash
# Check network
docker network inspect docker_learntrac-network

# Test DNS
docker exec trac-local ping learntrac-api
```

### Database issues
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker exec postgres-local pg_isready
```

## Documentation

- [Local Development Guide](LOCAL_DEVELOPMENT_GUIDE.md) - Detailed development instructions
- [AWS Cognito Integration](AWS_COGNITO_INTEGRATION.md) - Authentication setup
- [Authentication Test Results](AUTHENTICATION_TEST_RESULTS.md) - Test outcomes
- [Deployment Status](DEPLOYMENT_STATUS.md) - AWS deployment information

## Next Steps

1. Run the local environment
2. Test inter-container communication
3. Verify authentication flow
4. Make code changes and test
5. Push to ECR when ready

For production deployment, see the main project documentation.