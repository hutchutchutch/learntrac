# LearnTrac Next Steps - Infrastructure & Deployment

Based on the infrastructure test results from `scripts/test-infrastructure.sh`, we have a working AWS infrastructure with the following status:

## Current Infrastructure Status ✅

### What's Working:
- **ALB (Application Load Balancer)**: Responding correctly at http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/
- **ECR Repositories**: Both repositories created and ready
  - Trac: `971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac`
  - LearnTrac: `971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac`
- **ECS Cluster**: `hutch-learntrac-dev-cluster` exists and ready
- **Redis**: Endpoint configured at `hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com`

### What Needs Attention:
- **ECS Services**: Both services show 0 running tasks (desired: 1, running: 0)
  - `hutch-learntrac-dev-trac`: No running containers
  - `hutch-learntrac-dev-learntrac`: No running containers

## Immediate Next Steps

### 1. Build and Push Docker Images (Priority: HIGH)

The ECS services have no running tasks because the ECR repositories are empty. We need to build and push the Docker images.

#### Step 1a: Create Trac Docker Image (Python 2.7)

```bash
# Create directory structure
mkdir -p trac-legacy/{scripts,config,plugins}

# Create Dockerfile for Trac
cat > trac-legacy/Dockerfile << 'EOF'
FROM python:2.7-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    git \
    subversion \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create Trac environment directory
RUN mkdir -p /var/trac/projects

# Copy startup script
COPY scripts/start-trac.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-trac.sh

EXPOSE 8000

CMD ["/usr/local/bin/start-trac.sh"]
EOF

# Create requirements.txt
cat > trac-legacy/requirements.txt << 'EOF'
Trac==1.4.4
psycopg2==2.8.6
Genshi==0.7.7
Babel==2.9.1
Pygments==2.5.2
pytz
EOF

# Create startup script
cat > trac-legacy/scripts/start-trac.sh << 'EOF'
#!/bin/bash
set -e

# For now, just return a simple response
echo "Starting Trac placeholder..."
python -m SimpleHTTPServer 8000
EOF
```

#### Step 1b: Create LearnTrac API Docker Image (Python 3.11)

```bash
# Create directory structure
mkdir -p learntrac-api/{src,scripts}

# Create Dockerfile for LearnTrac
cat > learntrac-api/Dockerfile << 'EOF'
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/start-api.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-api.sh

EXPOSE 8001

CMD ["/usr/local/bin/start-api.sh"]
EOF

# Create requirements.txt
cat > learntrac-api/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg[binary,pool]==3.1.12
pydantic==2.5.0
pydantic-settings==2.1.0
EOF

# Create minimal FastAPI app
mkdir -p learntrac-api/src
cat > learntrac-api/src/main.py << 'EOF'
from fastapi import FastAPI

app = FastAPI(title="LearnTrac API", version="1.0.0")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "learntrac-api"}

@app.get("/api/learntrac/health")
async def api_health():
    return {"status": "healthy", "python_version": "3.11"}
EOF

# Create startup script
cat > learntrac-api/scripts/start-api.sh << 'EOF'
#!/bin/bash
uvicorn src.main:app --host 0.0.0.0 --port 8001
EOF
```

#### Step 1c: Build and Push Images

```bash
# Get ECR login token
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 971422717446.dkr.ecr.us-east-2.amazonaws.com

# Build and push Trac image
docker build -t hutch-learntrac-dev-trac:latest ./trac-legacy/
docker tag hutch-learntrac-dev-trac:latest 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest
docker push 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest

# Build and push LearnTrac API image
docker build -t hutch-learntrac-dev-learntrac:latest ./learntrac-api/
docker tag hutch-learntrac-dev-learntrac:latest 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac:latest
docker push 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac:latest
```

### 2. Update ECS Services (Priority: HIGH)

After pushing images, force new deployments:

```bash
# Update Trac service
aws ecs update-service \
    --cluster hutch-learntrac-dev-cluster \
    --service hutch-learntrac-dev-trac \
    --force-new-deployment

# Update LearnTrac service
aws ecs update-service \
    --cluster hutch-learntrac-dev-cluster \
    --service hutch-learntrac-dev-learntrac \
    --force-new-deployment
```

### 3. Monitor Service Health (Priority: HIGH)

Check CloudWatch logs for any startup issues:

```bash
# View Trac logs
aws logs tail /ecs/hutch-learntrac-dev-trac --follow

# View LearnTrac logs
aws logs tail /ecs/hutch-learntrac-dev-learntrac --follow
```

### 4. Configure ALB Path Routing (Priority: MEDIUM)

Verify ALB routing rules are correctly configured:

```bash
# Test Trac paths
curl http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/trac/
curl http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/ticket/

# Test LearnTrac API paths
curl http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/api/learntrac/health
curl http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/health
```

## Next Development Phase

### Phase 1: Basic Services Running (Week 1)
- [ ] Get both containers running with health checks passing
- [ ] Verify ALB routing works correctly
- [ ] Set up basic monitoring and alerts
- [ ] Create deployment pipeline script

### Phase 2: Database Integration (Week 2)
- [ ] Set up RDS PostgreSQL instance
- [ ] Configure database connections for both services
- [ ] Implement TracDatabaseBridge for Python 3.11
- [ ] Test cross-service database access

### Phase 3: Trac Migration (Week 3)
- [ ] Export existing Trac data
- [ ] Import Trac environment into container
- [ ] Configure authentication
- [ ] Test all Trac functionality

### Phase 4: LearnTrac Features (Week 4-6)
- [ ] Implement core learning API endpoints
- [ ] Add Redis session management
- [ ] Integrate Neo4j for knowledge graphs
- [ ] Build voice tutor Lambda functions
- [ ] Create AI chat integration

### Phase 5: Production Readiness (Week 7-8)
- [ ] Security audit and hardening
- [ ] Performance testing and optimization
- [ ] Backup and disaster recovery setup
- [ ] Documentation and training

## Deployment Checklist

### Before Each Deployment:
1. [ ] Run tests locally
2. [ ] Build Docker images
3. [ ] Push to ECR
4. [ ] Update ECS service
5. [ ] Monitor logs for errors
6. [ ] Verify health checks
7. [ ] Test all endpoints

### Production Deployment:
1. [ ] Create production ECR repositories
2. [ ] Set up production ECS cluster
3. [ ] Configure production ALB with SSL
4. [ ] Set up production RDS with Multi-AZ
5. [ ] Configure production Redis cluster
6. [ ] Set up CloudWatch dashboards
7. [ ] Configure auto-scaling policies
8. [ ] Set up backup schedules

## Troubleshooting Guide

### If ECS tasks won't start:
1. Check CloudWatch logs: `aws logs tail /ecs/service-name --follow`
2. Check task definition CPU/memory settings
3. Verify security group rules
4. Check IAM roles and permissions
5. Verify environment variables

### If ALB returns 503:
1. Check target group health: All targets unhealthy
2. Verify container health check endpoints
3. Check security group allows ALB → ECS traffic
4. Verify ECS tasks are in RUNNING state

### If database connection fails:
1. Verify RDS security group rules
2. Check database credentials in Secrets Manager
3. Verify subnet routing
4. Test connection from ECS task subnet

## Success Metrics

### Technical Metrics:
- ECS tasks running: 2/2 ✅
- Health checks passing: 100%
- Response time: < 200ms (p95)
- Error rate: < 0.1%
- Uptime: > 99.9%

### Business Metrics:
- Trac functionality preserved: 100%
- New LearnTrac features deployed: 0% → 100%
- API response time improvement: Target 50%
- User adoption rate: Track after launch

## Contact & Resources

- **Infrastructure Issues**: Check CloudWatch logs first
- **Deployment Questions**: Review Terraform outputs
- **Architecture Decisions**: Refer to `/docs/plan.md`
- **API Documentation**: Will be at `/api/learntrac/docs`

---

**Current Status**: Infrastructure ready, awaiting container deployment
**Next Action**: Build and push Docker images (Step 1)
**Timeline**: 8 weeks to full production deployment