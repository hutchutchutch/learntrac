# LearnTrac Testing Documentation

This document provides comprehensive instructions for testing the LearnTrac application, including unit tests, integration tests, and deployment testing.

## Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Running Tests](#running-tests)
4. [Test Types](#test-types)
5. [Docker Testing](#docker-testing)
6. [Troubleshooting](#troubleshooting)

## Overview

LearnTrac testing infrastructure includes:
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end system testing
- **API Tests**: REST API endpoint validation
- **Trac Tests**: Trac system functionality testing
- **Docker Tests**: Container build and deployment testing

## Test Environment Setup

### 1. Prerequisites

- Docker and Docker Compose installed
- AWS CLI configured (for deployment tests)
- Python 3.9+ (for local testing)
- Node.js (for API testing tools)

### 2. Environment Configuration

1. Copy the environment template:
   ```bash
   cp .env.template .env
   ```

2. Edit `.env` and fill in your values:
   ```bash
   # Database Configuration
   DB_USERNAME=your_username
   DB_PASSWORD=your_password
   DB_HOST=your_host
   DB_NAME=learntrac
   
   # Redis Configuration
   REDIS_ENDPOINT=your_redis_endpoint
   
   # AWS Configuration
   AWS_REGION=us-east-2
   AWS_ACCOUNT_ID=your_account_id
   ```

### 3. Directory Structure

```
/workspaces/learntrac/
├── docker-compose.test.yml    # Test environment composition
├── .env.template             # Environment template
├── scripts/
│   └── integration-test.sh   # Main integration test runner
├── tests/
│   ├── api/
│   │   └── test_api_endpoints.sh
│   └── trac/
│       └── test_trac_endpoints.sh
└── api_tests/               # Existing API test suite
    ├── run_all_tests.sh
    └── ...
```

## Running Tests

### Quick Start

1. **Run all integration tests**:
   ```bash
   # Start test environment
   docker-compose -f docker-compose.test.yml up -d
   
   # Run integration tests
   ./scripts/integration-test.sh
   
   # Stop test environment
   docker-compose -f docker-compose.test.yml down
   ```

2. **Run specific test suites**:
   ```bash
   # API tests only
   ./tests/api/test_api_endpoints.sh
   
   # Trac tests only
   ./tests/trac/test_trac_endpoints.sh
   
   # Existing API test suite
   cd api_tests && ./run_all_tests.sh
   ```

### Detailed Test Execution

#### 1. Docker Environment Tests

```bash
# Build and start containers
docker-compose -f docker-compose.test.yml build
docker-compose -f docker-compose.test.yml up -d

# Check container health
docker-compose -f docker-compose.test.yml ps

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Run integration tests
./scripts/integration-test.sh

# Clean up
docker-compose -f docker-compose.test.yml down -v
```

#### 2. API Endpoint Tests

```bash
# Basic API test
./tests/api/test_api_endpoints.sh

# With authentication token
AUTH_TOKEN="your-token" ./tests/api/test_api_endpoints.sh

# Verbose mode
VERBOSE=true ./tests/api/test_api_endpoints.sh

# Custom API URL
API_URL="http://localhost:3000" ./tests/api/test_api_endpoints.sh
```

#### 3. Trac System Tests

```bash
# Basic Trac test
./tests/trac/test_trac_endpoints.sh

# Verbose mode
VERBOSE=true ./tests/trac/test_trac_endpoints.sh

# Custom Trac URL
TRAC_URL="http://localhost:8080" ./tests/trac/test_trac_endpoints.sh
```

## Test Types

### Integration Tests

The main integration test script (`scripts/integration-test.sh`) performs:

1. **Service Health Checks**
   - Waits for API and Trac services to be ready
   - Validates health endpoints
   - Checks service availability

2. **API Endpoint Validation**
   - Tests all major API endpoints
   - Validates response codes
   - Checks API documentation endpoints

3. **Trac Endpoint Validation**
   - Tests Trac main pages
   - Validates login functionality
   - Checks static resources

4. **Container Connectivity**
   - Tests API → Trac connectivity
   - Validates inter-container communication
   - Checks host.docker.internal resolution

5. **Database Connectivity**
   - Tests database connections from containers
   - Validates connection strings
   - Checks async database operations

### API Tests

The API test suite (`tests/api/test_api_endpoints.sh`) covers:

- **Health & Status**: `/health`, `/api/v1/status`
- **Authentication**: Login, logout, token refresh
- **Concepts**: CRUD operations, search, filtering
- **Analytics**: Progress, performance, insights
- **Chat/AI**: Chat completion, history
- **Learning Paths**: Paths, recommendations, progress
- **Documentation**: Swagger UI, ReDoc, OpenAPI schema
- **Rate Limiting**: Request throttling
- **CORS**: Cross-origin headers

### Trac Tests

The Trac test suite (`tests/trac/test_trac_endpoints.sh`) covers:

- **Core Pages**: Main, wiki, timeline, roadmap
- **Functionality**: Login, search, reports
- **Resources**: CSS, JavaScript assets
- **API Endpoints**: JSON-RPC, XML-RPC
- **Health Check**: Custom health endpoint

## Docker Testing

### Pre-Push Checklist

Before deploying to AWS ECR:

1. **Build Verification**
   ```bash
   docker-compose -f docker-compose.test.yml build
   ```

2. **Runtime Verification**
   ```bash
   # Start containers
   docker-compose -f docker-compose.test.yml up -d
   
   # Monitor for 5 minutes
   sleep 300
   docker-compose -f docker-compose.test.yml ps
   ```

3. **Health Check Verification**
   ```bash
   # Check health status
   docker inspect learntrac-trac-1 | grep -A 5 "Health"
   docker inspect learntrac-api-1 | grep -A 5 "Health"
   ```

4. **Resource Usage**
   ```bash
   # Check memory usage
   docker stats --no-stream
   
   # Should be <500MB per container
   ```

5. **Log Analysis**
   ```bash
   # Check for errors
   docker-compose -f docker-compose.test.yml logs | grep -i error
   ```

### AWS Deployment Testing

1. **ECR Push Test**
   ```bash
   # Tag images
   docker tag learntrac-api:latest $ECR_REGISTRY/learntrac-api:test
   docker tag learntrac-trac:latest $ECR_REGISTRY/learntrac-trac:test
   
   # Push to ECR
   aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
   docker push $ECR_REGISTRY/learntrac-api:test
   docker push $ECR_REGISTRY/learntrac-trac:test
   ```

2. **ECS Deployment Test**
   ```bash
   # Update task definition with test tags
   aws ecs update-service --cluster learntrac-cluster \
     --service learntrac-service \
     --force-new-deployment
   ```

## Troubleshooting

### Common Issues

1. **Container won't start**
   - Check logs: `docker-compose -f docker-compose.test.yml logs [service]`
   - Verify .env file exists and has correct values
   - Check port conflicts: `lsof -i :8000` or `lsof -i :8001`

2. **Database connection fails**
   - Verify DATABASE_URL format in .env
   - Check network connectivity to RDS
   - Ensure security groups allow connections

3. **Health checks fail**
   - Check if health check scripts exist in containers
   - Verify health check endpoints return correct status
   - Increase health check timeout if needed

4. **Integration tests fail**
   - Run in verbose mode: `VERBOSE=true ./scripts/integration-test.sh`
   - Check individual service health first
   - Verify all environment variables are set

### Debug Commands

```bash
# Interactive container shell
docker-compose -f docker-compose.test.yml exec api /bin/bash
docker-compose -f docker-compose.test.yml exec trac /bin/bash

# Check environment variables
docker-compose -f docker-compose.test.yml exec api env
docker-compose -f docker-compose.test.yml exec trac env

# Test database connection manually
docker-compose -f docker-compose.test.yml exec api python -c "
import asyncpg
import asyncio
import os

async def test():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://'))
    result = await conn.fetchval('SELECT version()')
    print(f'Connected to: {result}')
    await conn.close()

asyncio.run(test())
"

# Check network connectivity
docker-compose -f docker-compose.test.yml exec api ping -c 3 host.docker.internal
docker-compose -f docker-compose.test.yml exec api curl http://trac:8000
```

## Continuous Integration

For CI/CD pipelines, use:

```bash
#!/bin/bash
# ci-test.sh

set -e

# Build images
docker-compose -f docker-compose.test.yml build

# Run tests
docker-compose -f docker-compose.test.yml up -d
./scripts/integration-test.sh
TEST_RESULT=$?

# Cleanup
docker-compose -f docker-compose.test.yml down -v

exit $TEST_RESULT
```

## Best Practices

1. **Always test locally** before pushing to AWS
2. **Monitor resource usage** during tests
3. **Check logs for errors** even if tests pass
4. **Use verbose mode** when debugging failures
5. **Keep test data isolated** from production
6. **Document any test failures** and resolutions

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [AWS ECS Testing Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-task-definition.html)
- [API Testing Best Practices](https://swagger.io/solutions/api-testing/)
- [Trac Administration Guide](https://trac.edgewall.org/wiki/TracAdmin)