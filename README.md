# LearnTrac - AI-Powered Learning Management System

LearnTrac is an AI-powered learning management system that combines the classic Trac project management system (Python 2.7) with a modern API (Python 3.11) for advanced features like PDF processing, vector search, and adaptive learning.

## 🏗️ Architecture Overview

LearnTrac uses a dual-container architecture:

1. **trac-legacy** - Classic Trac application (Python 2.7)
   - Traditional Trac wiki, ticket system, and project management
   - Runs on port 8000
   - Connects to AWS RDS PostgreSQL

2. **learntrac-api** - Modern API service (Python 3.11)
   - AI-powered features: PDF processing, vector search, learning recommendations
   - REST API and WebSocket support
   - Runs on port 8001
   - Connects to both AWS RDS PostgreSQL and Neo4j

## 🚀 Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- At least 8GB of RAM available for Docker
- AWS RDS PostgreSQL credentials
- OpenAI API key (optional, for AI features)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/learntrac.git
cd learntrac
```

### 2. Set Environment Variables

Copy the example environment file and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your AWS RDS credentials:

```bash
# AWS RDS PostgreSQL Configuration
RDS_HOST=hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com
RDS_PASSWORD=your_actual_rds_password_here

# Optional: Add your OpenAI API key for AI features
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Start the Services

```bash
# Start all services using Docker Compose
docker-compose up -d

# Check service health
docker-compose ps
```

### 4. Access the Applications

- **Trac Legacy Interface**: http://localhost:8000
- **LearnTrac API**: http://localhost:8001
- **API Health Check**: http://localhost:8001/health
- **Neo4j Browser**: http://localhost:7474 (username: neo4j, password: neo4jpassword)

## 📚 System Components

### Core Services

1. **Trac Legacy** (Port 8000) - Python 2.7
   - Classic Trac wiki and ticket system
   - Project management features
   - Plugin support for custom functionality
   - Connects to AWS RDS PostgreSQL

2. **LearnTrac API** (Port 8001) - Python 3.11
   - FastAPI-based REST API
   - PDF processing and vector search
   - AI-powered learning recommendations
   - JWT authentication support
   - WebSocket support for real-time features
   - Connects to AWS RDS PostgreSQL and Neo4j

3. **Neo4j** (Ports 7474/7687)
   - Graph database for knowledge representation
   - Vector similarity search for content matching
   - Relationship tracking between concepts
   - Can be replaced with Neo4j Aura for production

4. **AWS RDS PostgreSQL** (Remote)
   - Primary relational database
   - Stores user data, progress tracking, and metadata
   - Shared between Trac and LearnTrac API
   - Managed by AWS for high availability

### Optional Services

5. **Redis** (Port 6379) - Commented out in docker-compose.yml
   - Caching layer for improved performance
   - Session management
   - Can use AWS ElastiCache in production

6. **Nginx** (Ports 80/443) - Commented out in docker-compose.yml
   - Reverse proxy for production deployment
   - Routes requests between Trac and API
   - SSL/TLS termination

## 🔧 Development Setup

### Running in Development Mode

The default `docker-compose.yml` is configured for development with:
- Volume mounts for hot reloading
- Debug logging enabled
- Source code mounted into containers

```bash
# Start services with logs
docker-compose up

# Or run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f learntrac-api
```

### Building from Source

```bash
# Build the API image
docker-compose build learntrac-api

# Or build without cache
docker-compose build --no-cache learntrac-api
```

## 📋 API Documentation

### Health Check

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "neo4j": "healthy",
    "llm": "healthy",
    "tickets": "healthy",
    "evaluation": "healthy"
  }
}
```

### PDF Upload

Upload a PDF for processing:

```bash
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@path/to/your/document.pdf"
```

### Search Content

Search for content using vector similarity:

```bash
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "limit": 5
  }'
```

## 🛠️ Troubleshooting

### Common Issues

1. **Container fails to start**
   - Check logs: `docker-compose logs learntrac-api`
   - Ensure all ports are available
   - Verify environment variables

2. **Neo4j connection errors**
   - Wait for Neo4j to fully start (can take 30-60 seconds)
   - Check Neo4j logs: `docker-compose logs neo4j`
   - Ensure Neo4j password matches configuration

3. **API dependency errors**
   - All dependencies are included in the Docker image
   - If adding new dependencies, update `requirements-complete.txt`
   - Rebuild the image: `docker-compose build learntrac-api`

### Debugging

```bash
# Enter the API container
docker exec -it learntrac-api /bin/bash

# Check installed packages
docker exec learntrac-api pip list

# Run tests
docker exec learntrac-api python -m pytest

# Check Neo4j connectivity
docker exec learntrac-api python -c "from neo4j import GraphDatabase; print('Neo4j OK')"
```

## 📁 Project Structure

```
learntrac/
├── docker-compose.yml          # Main Docker Compose configuration
├── learntrac-api/             # API service
│   ├── Dockerfile             # Production Dockerfile
│   ├── requirements-complete.txt  # Complete dependency list
│   ├── src/                   # Source code
│   │   ├── main.py           # FastAPI application
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # Business logic
│   │   └── pdf_processing/   # PDF processing pipeline
│   └── tests/                # Test files
├── docker/                   # Trac-related Docker files
├── plugins/                  # Trac plugins
└── docs/                    # Documentation
```

## 🔐 Security Considerations

1. **Default Credentials** - Change these in production:
   - Neo4j: neo4j/neo4jpassword
   - PostgreSQL: learntrac/learntrac

2. **Environment Variables**:
   - Store sensitive data in `.env` file
   - Never commit `.env` to version control
   - Use Docker secrets in production

3. **Network Security**:
   - Services communicate on internal Docker network
   - Only necessary ports exposed to host
   - Consider using reverse proxy in production

## 🌐 Using Nginx Reverse Proxy

To enable Nginx as a reverse proxy (recommended for production):

1. Uncomment the nginx service in `docker-compose.yml`
2. Access all services through port 80:
   - Trac: http://localhost/
   - API: http://localhost/api/
   - WebSocket: ws://localhost/ws

The Nginx configuration in `nginx/learntrac.conf` handles:
- Request routing between Trac (Python 2.7) and API (Python 3.11)
- CORS headers for API endpoints
- WebSocket proxying
- Static file caching
- Security headers

## 🔐 AWS RDS Password Retrieval

To get your RDS password from AWS Secrets Manager:

```bash
# Run the helper script
./scripts/get-rds-password.sh

# Or manually retrieve it
aws secretsmanager get-secret-value \
  --region us-east-2 \
  --secret-id learntrac-dev-db-password \
  --query SecretString \
  --output text
```

## 🚀 Production Deployment

For production deployment:

1. Use environment-specific `.env` files
2. Enable Nginx reverse proxy for SSL/TLS
3. Use AWS services:
   - RDS for PostgreSQL (already configured)
   - ElastiCache for Redis
   - Neo4j Aura for graph database
   - ECS or EKS for container orchestration
4. Configure monitoring with CloudWatch
5. Set up automated backups

See [DOCKER_ERROR_ANALYSIS.md](./DOCKER_ERROR_ANALYSIS.md) for detailed Docker configuration and troubleshooting.

## 📖 Additional Documentation

- [API Documentation](./learntrac-api/API_DOCUMENTATION.md)
- [Docker Configuration Details](./DOCKER_ERROR_ANALYSIS.md)
- [System Architecture](./docs/core/system_architecture.md)
- [Development Guide](./docs/plan/first_steps.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

[Your License Here]

---

For more information, please refer to the documentation in the `docs/` directory.