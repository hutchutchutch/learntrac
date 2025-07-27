# LearnTrac Docker Scripts

These scripts help manage the LearnTrac application with Cognito authentication.

## Prerequisites

- Docker installed and running
- Project dependencies in place
- Environment variables set (optional):
  - `OPENAI_API_KEY`
  - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`

## Scripts

### 🚀 start-learntrac.sh
Starts all services in the correct order:
1. Creates Docker network
2. Starts PostgreSQL and Redis (if needed)
3. Starts Learning API (Python 3.11)
4. Builds and installs Trac plugins
5. Starts Trac (Python 2.7)
6. Verifies all services are healthy

```bash
./scripts/start-learntrac.sh
```

### 🛑 stop-learntrac.sh
Stops all services gracefully:
- Stops Trac and Learning API
- Optionally stops PostgreSQL and Redis
- Optionally removes containers

```bash
./scripts/stop-learntrac.sh
```

### 📋 status-learntrac.sh
Shows the status of all services:
- Container status (running/stopped)
- Health check results
- Available endpoints
- Quick command reference

```bash
./scripts/status-learntrac.sh
```

### 📜 logs-learntrac.sh
View logs for services:
- View specific service logs
- Follow logs in real-time
- Split view with tmux (if available)

```bash
# View all logs
./scripts/logs-learntrac.sh

# View specific service
./scripts/logs-learntrac.sh trac
./scripts/logs-learntrac.sh learning
./scripts/logs-learntrac.sh postgres
./scripts/logs-learntrac.sh redis
```

### 🔨 rebuild-learntrac.sh
Rebuild and restart services:
- Stops all services
- Removes old images
- Optionally cleans build cache
- Rebuilds and starts fresh

```bash
./scripts/rebuild-learntrac.sh
```

## Service URLs

After starting, services are available at:
- **Trac Wiki**: http://localhost:8000/trac/wiki
- **Learning API**: http://localhost:8001/docs
- **Auth Login**: http://localhost:8001/auth/login

## Authentication Flow

1. Access Trac at http://localhost:8000/trac/wiki
2. If not authenticated, redirected to Learning API auth
3. Learning API redirects to AWS Cognito
4. After login, returned to Trac with session

## Troubleshooting

### Services won't start
```bash
# Check status
./scripts/status-learntrac.sh

# View logs
./scripts/logs-learntrac.sh

# Rebuild everything
./scripts/rebuild-learntrac.sh
```

### Port conflicts
```bash
# Check what's using ports
lsof -i :8000
lsof -i :8001
lsof -i :5432
lsof -i :6379
```

### Clean start
```bash
# Stop everything
./scripts/stop-learntrac.sh

# Remove all data volumes
docker volume rm trac-data

# Start fresh
./scripts/start-learntrac.sh
```