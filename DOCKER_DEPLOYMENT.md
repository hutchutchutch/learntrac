# LearnTrac Docker Deployment Guide

This guide covers the Docker-based deployment of LearnTrac, including both the Trac system and the Learning Service API.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 1.29+
- AWS credentials (for production deployment)
- At least 4GB of available RAM

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/learntrac.git
cd learntrac
```

### 2. Set Up Environment Variables

```bash
cp .env.docker.example .env
# Edit .env with your configuration
```

### 3. Start Development Environment

```bash
make dev
```

This starts:
- Trac on http://localhost:8080
- Learning Service API on http://localhost:8001
- Neo4j Browser on http://localhost:7474 (development only)
- Redis on localhost:6379 (development only)

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│                 │     │                  │
│   Trac (8080)   │────▶│ Learning API     │
│   Python 2.7    │     │ (8001)           │
│                 │     │ Python 3.11      │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │                       │
         │   PostgreSQL (RDS)    │
         │   Neo4j               │
         │   Redis/ElastiCache   │
         └───────────────────────┘
```

## Services

### Trac Service
- **Port**: 8080
- **Image**: Python 2.7 with Trac 1.4.4
- **Features**:
  - Cognito authentication
  - Learning question display
  - Knowledge graph generation
  - Custom plugins

### Learning Service API
- **Port**: 8001
- **Image**: Python 3.11 with FastAPI
- **Features**:
  - RESTful API
  - LLM integration (OpenAI)
  - Neo4j graph database
  - Redis caching

### Development Services
- **Neo4j**: Graph database (port 7474/7687)
- **Redis**: Caching layer (port 6379)

## Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
# Database
RDS_ENDPOINT=your-rds-endpoint.amazonaws.com:5432
DB_NAME=learntrac
DB_USER=learntrac_user
DB_PASSWORD=secure-password

# AWS Services
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx

# Neo4j
NEO4J_URI=bolt://neo4j-dev:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Development vs Production

**Development** (`docker-compose.dev.yml`):
- Hot reloading enabled
- Source code mounted as volumes
- Debug logging
- Local Neo4j and Redis

**Production** (`docker-compose.prod.yml`):
- Optimized images
- Resource limits
- Production logging
- External services only

## Common Operations

### Building Images

```bash
# Build all images
make build

# Build specific service
make build-trac
make build-learning-service
```

### Managing Services

```bash
# Start services
make up

# Stop services
make down

# View logs
make logs
make logs-trac
make logs-learning-service

# Access container shell
make shell-trac
make shell-api
```

### Database Operations

```bash
# Run migrations
make db-migrate

# Rollback migration
make db-rollback
```

### Health Checks

```bash
# Check service health
make health
```

## Deployment

### Local Development

1. Use `make dev` for development with hot reloading
2. Access services at:
   - Trac: http://localhost:8080
   - API: http://localhost:8001
   - Neo4j: http://localhost:7474

### Production Deployment

#### Option 1: Docker Compose on EC2

```bash
# On production server
make prod
```

#### Option 2: AWS ECS

1. Build and push images to ECR:
```bash
./deploy/push-to-ecr.sh
```

2. Deploy to ECS:
```bash
./deploy/deploy-ecs.sh
```

#### Option 3: Kubernetes

See `k8s/` directory for Kubernetes manifests.

## Troubleshooting

### Container Won't Start

1. Check logs: `docker-compose logs <service-name>`
2. Verify environment variables: `docker-compose config`
3. Check port conflicts: `lsof -i :8080` or `lsof -i :8001`

### Database Connection Issues

1. Verify RDS endpoint and credentials
2. Check security group allows connection
3. Test connection: 
   ```bash
   docker-compose exec trac psql -h $RDS_ENDPOINT -U $DB_USER -d $DB_NAME
   ```

### Memory Issues

Increase Docker memory allocation:
- Docker Desktop: Preferences → Resources → Memory
- Linux: Check `docker system info`

### Permission Issues

Fix volume permissions:
```bash
sudo chown -R $USER:$USER ./logs
```

## Monitoring

### Logs

Logs are stored in:
- `./logs/trac/` - Trac logs
- `./logs/api/` - API logs

### Metrics

For production, integrate with:
- CloudWatch (AWS)
- Prometheus/Grafana
- ELK Stack

## Security Considerations

1. **Never commit `.env` files**
2. Use secrets management in production:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Kubernetes Secrets
3. Enable HTTPS in production
4. Regular security updates:
   ```bash
   docker-compose pull
   make build
   ```

## Backup and Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker-compose exec -T trac pg_dump -h $RDS_ENDPOINT -U $DB_USER $DB_NAME > backup.sql

# Backup Neo4j
docker-compose exec neo4j-dev neo4j-admin dump --to=/backup/neo4j.dump
```

### Volume Backup

```bash
# Backup Trac data
docker run --rm -v learntrac_trac-data:/data -v $(pwd):/backup alpine tar czf /backup/trac-data.tar.gz -C /data .
```

## Performance Tuning

### Docker Settings

1. Increase memory limits in `docker-compose.prod.yml`
2. Enable BuildKit: `export DOCKER_BUILDKIT=1`
3. Use multi-stage builds for smaller images

### Application Settings

1. Adjust worker processes in Trac
2. Configure connection pooling in API
3. Tune PostgreSQL parameters
4. Optimize Neo4j heap size

## Support

For issues:
1. Check logs: `make logs`
2. Review this documentation
3. Check GitHub issues
4. Contact the development team

## License

See LICENSE file in the repository root.