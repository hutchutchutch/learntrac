# LearnTrac API Docker Image

This directory contains the Docker setup for the LearnTrac API using Python 3.11 and FastAPI.

## Structure

```
docker/learntrac/
├── Dockerfile           # Python 3.11 slim image with FastAPI
├── requirements.txt     # Python dependencies
├── scripts/
│   └── start-api.sh    # Startup script for the API
├── src/
│   └── main.py         # FastAPI application
└── tests/
    └── test_endpoints.py  # Endpoint tests
```

## Endpoints

- `/` - Root endpoint returning welcome message
- `/health` - Health check for ALB (returns detailed health response)
- `/api/learntrac/health` - API-specific health check
- `/api/learntrac/courses` - List available courses (placeholder implementation)

## Building the Image

```bash
cd docker/learntrac
docker build -t learntrac-api:latest .
```

## Running the Container

```bash
docker run -p 8001:8001 learntrac-api:latest
```

## Testing

To run the tests:

```bash
cd docker/learntrac
pip install pytest
python -m pytest tests/
```

## Dependencies

- FastAPI 0.104.1
- Uvicorn 0.24.0 with standard extras
- PostgreSQL adapter (psycopg 3.1.12)
- Redis client 5.0.1
- Authentication libraries (python-jose, passlib)
- HTTP client (httpx)

The API runs on port 8001 and includes health checks for container orchestration.