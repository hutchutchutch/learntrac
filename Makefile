# Makefile for LearnTrac Docker deployment

.PHONY: help dev prod build up down logs clean test

# Default target
help:
	@echo "LearnTrac Docker Management"
	@echo "=========================="
	@echo "make dev       - Start development environment with hot reloading"
	@echo "make prod      - Start production environment"
	@echo "make build     - Build all Docker images"
	@echo "make up        - Start services (basic)"
	@echo "make down      - Stop all services"
	@echo "make logs      - Show logs from all services"
	@echo "make clean     - Clean up volumes and images"
	@echo "make test      - Run tests in containers"
	@echo "make shell-trac - Open shell in Trac container"
	@echo "make shell-api  - Open shell in API container"

# Development environment with hot reloading
dev:
	@echo "Starting development environment..."
	docker compose -f docker compose.yml -f docker compose.dev.yml up

# Development environment in background
dev-d:
	@echo "Starting development environment in background..."
	docker compose -f docker compose.yml -f docker compose.dev.yml up -d

# Production environment
prod:
	@echo "Starting production environment..."
	docker compose -f docker compose.yml -f docker compose.prod.yml up -d

# Build all images
build:
	@echo "Building Docker images..."
	docker compose build --no-cache

# Build specific service
build-%:
	@echo "Building $* image..."
	docker compose build --no-cache $*

# Start services (basic configuration)
up:
	@echo "Starting services..."
	docker compose up -d

# Stop all services
down:
	@echo "Stopping services..."
	docker compose down

# Stop and remove volumes
down-v:
	@echo "Stopping services and removing volumes..."
	docker compose down -v

# Show logs from all services
logs:
	docker compose logs -f

# Show logs from specific service
logs-%:
	docker compose logs -f $*

# Clean up everything
clean:
	@echo "Cleaning up Docker resources..."
	docker compose down -v
	docker system prune -f
	@echo "Clean complete!"

# Run tests in containers
test:
	@echo "Running tests..."
	docker compose -f docker compose.yml -f docker compose.dev.yml run --rm trac python -m pytest /app/tests
	docker compose -f docker compose.yml -f docker compose.dev.yml run --rm learning-service python -m pytest /app/tests

# Shell access to containers
shell-trac:
	docker compose exec trac /bin/bash

shell-api:
	docker compose exec learning-service /bin/bash

shell-neo4j:
	docker compose exec neo4j-dev cypher-shell -u neo4j

shell-redis:
	docker compose exec redis-dev redis-cli

# Database operations
db-migrate:
	@echo "Running database migrations..."
	docker compose exec learning-service alembic upgrade head

db-rollback:
	@echo "Rolling back last migration..."
	docker compose exec learning-service alembic downgrade -1

# Health checks
health:
	@echo "Checking service health..."
	@docker compose ps
	@echo ""
	@echo "Trac health:"
	@curl -f http://localhost:8080/login || echo "Trac is not healthy"
	@echo ""
	@echo "API health:"
	@curl -f http://localhost:8001/health || echo "API is not healthy"

# Initialize development environment
init-dev:
	@echo "Initializing development environment..."
	@cp .env.docker.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run 'make dev' to start the development environment"

# Deploy to AWS ECS (requires AWS CLI configured)
deploy-ecs:
	@echo "Deploying to AWS ECS..."
	@./deploy/deploy-ecs.sh

# Build and push to ECR
push-ecr:
	@echo "Building and pushing to ECR..."
	@./deploy/push-to-ecr.sh