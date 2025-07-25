System Architecture - Question-Based Learning MVP for Trac 1.4.4
1. Overview
This document describes the system architecture for implementing question-based learning paths in Trac 1.4.4 using AWS managed services. The system leverages Neo4j Aura for vector search, AWS RDS PostgreSQL for data persistence, AWS Cognito for authentication, AWS API Gateway for service orchestration, and AWS ElastiCache for caching.
2. Architecture Principles
2.1 MVP Principles

Cloud-Native: Leverage AWS managed services for reliability
Secure by Design: AWS Cognito authentication on all endpoints
Service Oriented: API Gateway manages all inter-service communication
Zero Trac Modification: All features via plugins and external services
Clear Separation: Python 2.7 for Trac UI, Python 3.11 for modern features

2.2 Technical Decisions

Two-container architecture (Trac + Learning Service)
AWS RDS PostgreSQL for all persistent data
Neo4j Aura for vector search (external managed service)
AWS ElastiCache Redis for caching
AWS Cognito for authentication
AWS API Gateway for service orchestration
GraphViz for knowledge graph visualization

3. High-Level Architecture
mermaidgraph TB
    subgraph "User Browser"
        UI1[Wiki Pages<br/>with Macros]
        UI2[Ticket Views]
        UI3[Knowledge Graphs]
    end
    
    UI1 --> COGNITO[AWS Cognito<br/>Authentication]
    UI2 --> COGNITO
    UI3 --> COGNITO
    
    COGNITO --> APIGW[AWS API Gateway<br/>With Cognito Authorizer]
    
    APIGW --> ALB[Application Load Balancer]
    
    ALB --> TRAC[Trac Container<br/>Python 2.7<br/>Port 8080]
    ALB --> LEARN[Learning Service<br/>Python 3.11<br/>Port 8000]
    
    subgraph "AWS Managed Services"
        RDS[(AWS RDS PostgreSQL<br/>• Trac Schema<br/>• Learning Schema)]
        CACHE[(AWS ElastiCache<br/>Redis Cluster)]
    end
    
    subgraph "External Services"
        NEO[(Neo4j Aura<br/>Vector Search)]
        LLM[LLM API<br/>OpenAI/Anthropic]
    end
    
    TRAC --> RDS
    LEARN --> RDS
    LEARN --> CACHE
    LEARN --> NEO
    APIGW --> LLM
    
    style COGNITO fill:#ff9900
    style APIGW fill:#ff9900
    style RDS fill:#ff9900
    style CACHE fill:#ff9900
    style ALB fill:#ff9900
4. Component Architecture
4.1 AWS Cognito Configuration
yamlUserPool:
  Name: TracLearnUsers
  Attributes:
    - email (required, unique)
    - name (required)
    - sub (Cognito user ID)
  
AppClient:
  Name: TracLearnWebClient
  TokenValidity:
    AccessToken: 1 hour
    IdToken: 1 hour
    RefreshToken: 30 days
  
IdentityPool:
  AllowUnauthenticated: false
  AuthProviders:
    - Cognito User Pool
4.2 AWS API Gateway Routes
yamlRestAPI: TracLearnAPI
Authorizer: CognitoUserPoolAuthorizer

Routes:
  # Trac Routes
  - Path: /trac/*
    Method: ANY
    Integration: HTTP_PROXY to ALB/trac
    Authorization: Required
    
  # Learning Service Routes  
  - Path: /api/v1/learning-paths/generate
    Method: POST
    Integration: HTTP to ALB/learning-service
    Authorization: Required
    
  - Path: /api/v1/learning-paths/create
    Method: POST
    Integration: HTTP to ALB/learning-service
    Authorization: Required
    
  - Path: /api/v1/progress/{ticket_id}/submit-answer
    Method: PUT
    Integration: HTTP to ALB/learning-service
    Authorization: Required
    
  # LLM Integration
  - Path: /api/v1/llm/*
    Method: POST
    Integration: Lambda to LLM services
    Authorization: Required
    RateLimit: 100 requests/minute per user
4.3 Trac Container Architecture
trac/
├── Dockerfile
├── requirements.txt          # Python 2.7 dependencies
├── plugins/
│   ├── learning_auth.py      # Cognito integration
│   ├── learning_macros.py    # Wiki macros
│   ├── learning_ticket.py    # Custom ticket display
│   ├── learning_graph.py     # GraphViz generation
│   └── learning_api.py       # API Gateway client
├── templates/
│   ├── learning_path.html    
│   ├── learning_ticket.html  
│   └── knowledge_graph.html  
└── static/
    ├── js/
    │   ├── cognito-auth.js   # Cognito SDK integration
    │   └── api-client.js     # API Gateway requests
    └── css/
        └── learning.css
4.3.1 Cognito Authentication Plugin
python# plugins/learning_auth.py
from trac.core import Component, implements
from trac.web.api import IAuthenticator, IRequestHandler
import jwt
import requests

class CognitoAuthenticator(Component):
    """AWS Cognito authentication for Trac."""
    
    implements(IAuthenticator, IRequestHandler)
    
    def authenticate(self, req):
        """Validate Cognito JWT token."""
        auth_header = req.get_header('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        try:
            # Verify JWT with Cognito public keys
            claims = self._verify_cognito_token(token)
            
            # Create/update Trac session
            req.session['cognito_sub'] = claims['sub']
            req.session['email'] = claims['email']
            req.session['name'] = claims['name']
            req.session.save()
            
            return claims['email']  # Return username
            
        except Exception as e:
            self.log.error("Cognito auth failed: %s", e)
            return None
    
    def _verify_cognito_token(self, token):
        """Verify JWT token with Cognito."""
        # Get Cognito JWKS
        region = self.config.get('cognito', 'region')
        user_pool_id = self.config.get('cognito', 'user_pool_id')
        
        jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        jwks = requests.get(jwks_url).json()
        
        # Verify token
        return jwt.decode(
            token,
            jwks,
            algorithms=['RS256'],
            audience=self.config.get('cognito', 'client_id')
        )
4.3.2 API Gateway Client
python# plugins/learning_api.py
import requests
from aws_requests_auth.aws_auth import AWSRequestsAuth

class APIGatewayClient:
    """Client for AWS API Gateway requests."""
    
    def __init__(self, env):
        self.api_url = env.config.get('aws', 'api_gateway_url')
        self.region = env.config.get('aws', 'region')
    
    def call_learning_service(self, endpoint, method='GET', data=None, token=None):
        """Make authenticated request to Learning Service via API Gateway."""
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        url = f"{self.api_url}{endpoint}"
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data
        )
        
        response.raise_for_status()
        return response.json()
4.4 Learning Service Architecture
learning-service/
├── Dockerfile
├── requirements.txt          # Python 3.11 dependencies
├── app/
│   ├── main.py              # FastAPI application
│   ├── auth/
│   │   └── cognito.py       # Token validation
│   ├── api/
│   │   ├── learning_paths.py
│   │   └── progress.py
│   ├── core/
│   │   ├── neo4j_client.py  # Neo4j Aura connection
│   │   ├── rds_client.py    # RDS operations
│   │   ├── cache_client.py  # ElastiCache operations
│   │   └── api_gateway.py   # Outbound API calls
│   └── models/
│       └── schemas.py
└── alembic/
    └── versions/            # RDS schema migrations
4.4.1 FastAPI Application with Cognito
python# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.cognito import verify_cognito_token
import boto3

app = FastAPI(title="TracLearn Learning Service")
security = HTTPBearer()

# AWS Clients
rds_client = boto3.client('rds-data')
elasticache_client = boto3.client('elasticache')

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate Cognito token and return user claims."""
    token = credentials.credentials
    
    try:
        claims = await verify_cognito_token(token)
        return claims
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication")

@app.get("/health")
async def health_check():
    """Health check endpoint for ALB."""
    return {"status": "healthy", "service": "learning-service"}

@app.post("/api/v1/learning-paths/generate")
async def generate_learning_path(
    request: LearningPathRequest,
    user = Depends(get_current_user)
):
    """Generate learning path with Cognito authentication."""
    # User ID from Cognito token
    user_id = user['sub']
    
    # Implementation continues...
4.4.2 RDS Schema Initialization
python# alembic/versions/001_initial_trac_schema.py
"""Initialize Trac schema in RDS PostgreSQL"""

def upgrade():
    # Create Trac tables
    op.create_table('ticket',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('type', sa.Text),
        sa.Column('time', sa.Integer),
        sa.Column('changetime', sa.Integer),
        sa.Column('component', sa.Text),
        sa.Column('severity', sa.Text),
        sa.Column('priority', sa.Text),
        sa.Column('owner', sa.Text),
        sa.Column('reporter', sa.Text),
        sa.Column('cc', sa.Text),
        sa.Column('version', sa.Text),
        sa.Column('milestone', sa.Text),
        sa.Column('status', sa.Text),
        sa.Column('resolution', sa.Text),
        sa.Column('summary', sa.Text),
        sa.Column('description', sa.Text),
        sa.Column('keywords', sa.Text)
    )
    
    op.create_table('ticket_custom',
        sa.Column('ticket', sa.Integer, sa.ForeignKey('ticket.id')),
        sa.Column('name', sa.Text),
        sa.Column('value', sa.Text),
        sa.PrimaryKeyConstraint('ticket', 'name')
    )
    
    # Additional Trac tables...
    
# alembic/versions/002_learning_schema.py
"""Create learning schema"""

def upgrade():
    # Create learning schema
    op.execute('CREATE SCHEMA IF NOT EXISTS learning')
    
    # Learning tables
    op.create_table('paths',
        sa.Column('id', sa.UUID, primary_key=True),
        sa.Column('title', sa.String(255)),
        sa.Column('query_text', sa.Text),
        sa.Column('cognito_user_id', sa.String(100)),
        sa.Column('created_at', sa.DateTime),
        schema='learning'
    )
    
    # Additional learning tables...
4.5 AWS Service Integration
4.5.1 Neo4j Aura Connection
python# app/core/neo4j_client.py
from neo4j import AsyncGraphDatabase
import os

class Neo4jAuraClient:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            os.environ['NEO4J_URI'],
            auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD'])
        )
    
    async def vector_search(self, embedding, min_score=0.65, limit=20):
        """Search Neo4j Aura for similar chunks."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (c:Chunk)
                WITH c, gds.similarity.cosine(c.embedding, $embedding) AS score
                WHERE score >= $min_score
                RETURN c.id, c.content, c.subject, c.concept,
                       c.has_prerequisite, c.prerequisite_for, score
                ORDER BY score DESC
                LIMIT $limit
            """, embedding=embedding, min_score=min_score, limit=limit)
            
            return [record.data() async for record in result]
4.5.2 ElastiCache Integration
python# app/core/cache_client.py
import redis
import json
from typing import Optional

class ElastiCacheClient:
    def __init__(self):
        self.redis = redis.Redis(
            host=os.environ['ELASTICACHE_ENDPOINT'],
            port=6379,
            decode_responses=True
        )
    
    async def get_cached_search(self, query: str, user_id: str) -> Optional[dict]:
        """Get cached search results."""
        key = f"search:{query}:{user_id}"
        result = self.redis.get(key)
        return json.loads(result) if result else None
    
    async def cache_search_results(self, query: str, user_id: str, results: dict, ttl=3600):
        """Cache search results for 1 hour."""
        key = f"search:{query}:{user_id}"
        self.redis.setex(key, ttl, json.dumps(results))
4.6 Database Schema (RDS PostgreSQL)
sql-- Standard Trac schema tables (created by migration)
-- ... (all standard Trac tables)

-- Learning schema
CREATE SCHEMA IF NOT EXISTS learning;

-- Learning paths with Cognito user association
CREATE TABLE learning.paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    query_text TEXT NOT NULL,
    cognito_user_id VARCHAR(100) NOT NULL,  -- Cognito sub
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_chunks INTEGER DEFAULT 0,
    question_difficulty INTEGER DEFAULT 3
);

-- User progress linked to Cognito ID
CREATE TABLE learning.progress (
    cognito_user_id VARCHAR(100) NOT NULL,  -- Cognito sub
    ticket_id INTEGER REFERENCES public.ticket(id),
    status VARCHAR(20) DEFAULT 'not_started',
    started_at TIMESTAMP,
    last_accessed TIMESTAMP,
    completed_at TIMESTAMP,
    time_spent_minutes INTEGER DEFAULT 0,
    notes TEXT,
    last_answer TEXT,
    answer_score FLOAT,
    answer_feedback TEXT,
    PRIMARY KEY (cognito_user_id, ticket_id)
);

-- Indexes for performance
CREATE INDEX idx_paths_user ON learning.paths(cognito_user_id);
CREATE INDEX idx_progress_user ON learning.progress(cognito_user_id);
CREATE INDEX idx_progress_status ON learning.progress(status);
5. Deployment Architecture
5.1 AWS Infrastructure
yaml# Infrastructure components (managed by Terraform)
Resources:
  # Networking
  VPC:
    Type: AWS::EC2::VPC
    CidrBlock: 10.0.0.0/16
    
  # Container hosting
  ECS:
    Cluster: TracLearnCluster
    Services:
      - TracService (Trac container)
      - LearningService (Learning API)
    
  # Load balancing
  ALB:
    Type: Application
    Listeners:
      - Port: 443
        Protocol: HTTPS
        Certificate: ACM
    TargetGroups:
      - Name: trac-targets
        Port: 8080
      - Name: learning-targets
        Port: 8000
        
  # API Gateway
  APIGateway:
    Type: REST
    Authorizers:
      - Type: COGNITO_USER_POOLS
        UserPool: TracLearnUsers
    
  # Data stores
  RDS:
    Engine: postgres
    Version: "15"
    MultiAZ: true (production)
    BackupRetention: 30 days
    
  ElastiCache:
    Engine: redis
    Version: "7.0"
    NodeType: cache.r6g.large
    ClusterMode: enabled
5.2 Container Deployment
yaml# docker-compose.yml for local development
version: '3.8'

services:
  trac:
    build: ./trac
    environment:
      - TRAC_ENV=/var/trac/myproject
      - DATABASE_URL=postgresql://user:pass@localhost/trac
      - API_GATEWAY_URL=http://localhost:4566/restapis/local/
      - COGNITO_REGION=us-east-1
      - COGNITO_USER_POOL_ID=local_pool
    ports:
      - "8080:8080"
      
  learning-service:
    build: ./learning-service
    environment:
      - DATABASE_URL=postgresql://user:pass@localhost/trac
      - NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
      - ELASTICACHE_ENDPOINT=localhost:6379
      - COGNITO_REGION=us-east-1
    ports:
      - "8000:8000"
      
  # Local services for development
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=trac
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      
  redis:
    image: redis:7-alpine
    
  localstack:
    image: localstack/localstack
    environment:
      - SERVICES=apigateway,cognito
6. Security Architecture
6.1 Authentication Flow
mermaidsequenceDiagram
    participant User
    participant Browser
    participant Cognito
    participant APIGateway
    participant Trac
    participant Learning
    
    User->>Browser: Access TracLearn
    Browser->>Cognito: Login request
    Cognito->>Browser: JWT tokens
    Browser->>APIGateway: Request + JWT
    APIGateway->>APIGateway: Validate JWT
    APIGateway->>Trac: Forward request
    Trac->>Learning: API call via Gateway
    Learning->>APIGateway: Response
    APIGateway->>Browser: Final response
6.2 Security Layers

Network Security

VPC with private subnets
Security groups limiting access
NACLs for additional protection


Authentication

AWS Cognito User Pools
JWT token validation
Token refresh handling


Authorization

API Gateway authorizers
User context in all requests
Row-level security in RDS


Data Security

RDS encryption at rest
TLS for all connections
ElastiCache encryption
Secrets Manager for credentials



7. Monitoring and Observability
7.1 CloudWatch Integration
python# Structured logging
import json
import logging
from aws_lambda_powertools import Logger

logger = Logger(service="learning-service")

@logger.inject_lambda_context
def handle_request(event, context):
    logger.info("Processing learning path generation",
        user_id=event['requestContext']['authorizer']['claims']['sub'],
        query=event['body']['query']
    )
7.2 Key Metrics

API Gateway: Request count, latency, 4XX/5XX errors
ECS: CPU/memory utilization, task health
RDS: Connection count, query performance, storage
ElastiCache: Hit rate, evictions, memory usage
Neo4j Aura: Query latency (custom metrics)

8. Error Handling and Resilience
8.1 Circuit Breakers
pythonfrom circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_neo4j_aura(query):
    """Circuit breaker for Neo4j Aura calls."""
    try:
        return await neo4j_client.vector_search(query)
    except Exception as e:
        logger.error("Neo4j Aura call failed", error=str(e))
        raise
8.2 Graceful Degradation

Cache fallback when Neo4j Aura unavailable
Cached responses from ElastiCache
Static error pages via CloudFront
Queue requests during outages

9. Performance Optimization
9.1 Caching Strategy
Cache Layers:
1. CloudFront: Static assets (1 hour)
2. API Gateway: Response caching (5 minutes)
3. ElastiCache: Search results (1 hour), progress (15 min)
4. Application: In-memory caching for hot data
9.2 Database Optimization

RDS Performance Insights enabled
Read replicas for query scaling
Connection pooling in applications
Prepared statements for common queries

10. Operational Procedures
10.1 Deployment Process

Build containers and push to ECR
Update ECS task definitions
Blue-green deployment via ALB
Run database migrations
Update API Gateway stages
Invalidate CloudFront cache

10.2 Backup and Recovery

RDS automated backups (30 days)
ElastiCache snapshots (daily)
Neo4j Aura managed backups
Infrastructure as Code in Git
