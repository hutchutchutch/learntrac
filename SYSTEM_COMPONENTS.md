# LearnTrac System Components Documentation

## Overview

LearnTrac is a cloud-native learning management system built on AWS infrastructure that extends Trac 1.4.4 with modern AI-powered learning capabilities. The system uses a hybrid architecture combining legacy Trac functionality with modern microservices for advanced learning features.

## Core System Components

### 1. Authentication & Identity Management

#### AWS Cognito User Pool
- **Purpose**: Centralized user authentication and identity management
- **Technology**: AWS Cognito User Pools with JWT tokens
- **Features**:
  - Multi-factor authentication (MFA)
  - Social login integration
  - Password policies and recovery
  - User attribute management
- **Integration**: All API endpoints require valid Cognito JWT tokens

#### Cognito Authentication Plugin (`plugins/cognito_auth.py`)
- **Purpose**: Integrates AWS Cognito with legacy Trac system
- **Technology**: Python 2.7 Trac plugin
- **Responsibilities**:
  - JWT token validation
  - Trac session creation
  - User mapping between Cognito and Trac
  - Authorization enforcement

### 2. API Gateway & Routing

#### AWS API Gateway
- **Purpose**: Centralized API management and routing
- **Features**:
  - Cognito authorizer integration
  - Rate limiting (100 requests/minute per user)
  - Request/response transformation
  - CORS handling
- **Routes**:
  - `/trac/*` → Trac Container (legacy system)
  - `/api/v1/learning-paths/*` → Learning Service
  - `/api/v1/llm/*` → Lambda LLM integration

#### Application Load Balancer (ALB)
- **Purpose**: Traffic distribution between containers
- **Features**:
  - SSL termination
  - Health checks
  - Path-based routing
  - Auto-scaling integration

### 3. Container Services

#### Trac Container (Legacy System)
- **Technology**: Python 2.7, Trac 1.4.4
- **Port**: 8080
- **Components**:
  - Wiki engine with custom macros
  - Ticket management system
  - Custom authentication plugin
  - Learning display plugins
  - GraphViz integration for knowledge graphs

**Key Files**:
```
docker/trac/
├── plugins/
│   ├── cognito_auth.py          # AWS Cognito integration
│   └── learntrac_display/       # Learning visualization plugins
├── templates/                   # Custom HTML templates
└── static/                      # JavaScript and CSS assets
```

#### Learning Service Container (Modern API)
- **Technology**: Python 3.11, FastAPI
- **Port**: 8001
- **Architecture**: Microservice with layered architecture

**Core Structure**:
```
learntrac-api/src/
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management
├── routers/                     # API endpoint definitions
│   ├── learning.py              # Learning path generation
│   ├── chat.py                  # AI chat interface
│   ├── voice.py                 # Speech processing
│   └── evaluation.py            # Answer evaluation
├── services/                    # Business logic layer
│   ├── neo4j_client.py          # Vector database integration
│   ├── redis_client.py          # Caching layer
│   ├── llm_service.py           # AI/LLM integration
│   └── ticket_service.py        # Trac integration
└── db/                          # Data access layer
    ├── database.py              # PostgreSQL connection management
    └── models.py                # SQLAlchemy models
```

### 4. Data Storage Layer

#### AWS RDS PostgreSQL
- **Purpose**: Primary data persistence
- **Configuration**: Multi-AZ deployment with automated backups
- **Schemas**:
  - `public`: Standard Trac 1.4.4 schema
  - `learning`: Custom learning features schema

**Key Tables**:
```sql
-- Public Schema (Trac)
public.ticket                    -- Learning concepts as tickets
public.ticket_custom             -- Custom learning fields
public.milestone                 -- Subject groupings
public.session                   -- User sessions

-- Learning Schema
learning.paths                   -- Generated learning paths
learning.progress                -- User progress tracking
learning.prerequisites           -- Concept dependencies
learning.concept_metadata        -- Neo4j chunk references
```

#### AWS ElastiCache Redis
- **Purpose**: High-performance caching and session storage
- **Configuration**: Redis cluster mode for high availability
- **Cache Patterns**:
  - Search results: 1 hour TTL
  - User progress: 15 minute TTL
  - Knowledge graphs: Invalidated on progress changes
  - API responses: 5 minute TTL

#### Neo4j Aura (External Service)
- **Purpose**: Vector database for academic content
- **Technology**: Neo4j cloud instance with vector search capabilities
- **Data Structure**:
  - Academic content chunks with embeddings
  - Subject and concept metadata
  - Prerequisite relationships
  - 1536-dimension OpenAI embeddings

### 5. AI & Machine Learning Integration

#### LLM Service Integration
- **Supported Providers**: OpenAI GPT-4, Anthropic Claude
- **Use Cases**:
  - Question generation from academic content
  - Answer evaluation and scoring
  - Learning path personalization
  - Chat-based learning assistance

#### Embedding Service
- **Technology**: OpenAI text-embedding-ada-002
- **Purpose**: Convert text to vector embeddings for similarity search
- **Integration**: Real-time embedding generation for user queries

#### PDF Processing Pipeline
- **Location**: `pdf_parse/` and `learntrac-api/src/pdf_processing/`
- **Components**:
  - Content extraction and chunking
  - Structure detection (chapters, sections)
  - Metadata extraction
  - Quality assessment
  - Vector embedding generation

### 6. Infrastructure & Deployment

#### AWS ECS Fargate
- **Purpose**: Container orchestration and management
- **Features**:
  - Auto-scaling based on CPU/memory metrics
  - Health checks and automatic recovery
  - Blue-green deployments
  - Service discovery

#### AWS VPC & Networking
- **Configuration**: Private subnets with NAT gateway
- **Security**: Security groups and NACLs for network isolation
- **Monitoring**: VPC Flow Logs for network analysis

#### Infrastructure as Code
- **Location**: `learntrac-infrastructure/`
- **Technology**: Terraform
- **Components**:
  - VPC and networking
  - ECS cluster and services
  - RDS and ElastiCache
  - API Gateway and Cognito
  - Monitoring and logging

### 7. Monitoring & Observability

#### AWS CloudWatch
- **Metrics**: Container CPU/memory, database performance, API latency
- **Logs**: Structured application logs with correlation IDs
- **Alarms**: Automated alerts for system health issues

#### Health Check System
- **Endpoints**: `/health` and `/api/learntrac/health`
- **Checks**: Database connectivity, Redis availability, service status
- **Integration**: ECS health checks and ALB target health

### 8. Learning Feature Components

#### Learning Path Generation
- **Process Flow**:
  1. User submits learning query via wiki macro
  2. LLM generates academic sentences from query
  3. Sentences converted to embeddings
  4. Vector search against Neo4j Aura
  5. Relevant chunks returned and cached
  6. Questions generated for each chunk
  7. Trac tickets created for learning concepts

#### Progress Tracking System
- **Components**:
  - Answer submission interface
  - LLM-based evaluation
  - Progress scoring (0.0-1.0 scale)
  - Prerequisite validation
  - Knowledge graph updates

#### Knowledge Graph Visualization
- **Technology**: GraphViz with server-side rendering
- **Features**:
  - Visual progress representation
  - Clickable nodes linking to tickets
  - Color-coded progress status
  - Prerequisite relationship display

### 9. External Integrations

#### PDF Document Processing
- **Purpose**: Extract and process learning materials
- **Components**:
  - Text extraction from PDFs
  - Content chunking strategies
  - Structure detection algorithms
  - Metadata enrichment

#### Speech Processing (Voice Interface)
- **Location**: `docker/learntrac/src/speech_processing.py`
- **Features**:
  - Real-time speech-to-text
  - Audio analysis and processing
  - WebSocket-based communication

### 10. Security & Compliance

#### Security Layers
1. **Network Security**: VPC, security groups, private subnets
2. **Authentication**: AWS Cognito with MFA support
3. **Authorization**: JWT token validation on all endpoints
4. **Data Encryption**: TLS in transit, AES-256 at rest
5. **Access Control**: IAM roles with least privilege

#### Compliance Features
- **Audit Logging**: All user actions and system events
- **Data Privacy**: User data isolation and GDPR compliance
- **Backup & Recovery**: Automated backups with point-in-time recovery

## Component Relationships

### Data Flow Between Components

1. **User Authentication Flow**:
   - User → Cognito → JWT Token → API Gateway → Services

2. **Learning Path Generation Flow**:
   - Wiki Macro → Learning Service → Neo4j Aura → Cache → Ticket Creation

3. **Progress Tracking Flow**:
   - Answer Submission → LLM Evaluation → Database Update → Graph Refresh

4. **Content Processing Flow**:
   - PDF Upload → Processing Pipeline → Neo4j Storage → Search Index

### Inter-Service Communication

- **Trac ↔ Learning Service**: Direct HTTP API calls for ticket management
- **Learning Service ↔ Neo4j**: Cypher queries for vector search
- **All Services ↔ Redis**: Caching and session management
- **All Services ↔ RDS**: Data persistence and retrieval

## Deployment Architecture

### Development Environment
- **Local Docker Compose**: Full stack with local Neo4j and Redis
- **Hot Reloading**: Development containers with volume mounts
- **Debug Support**: Integrated logging and debugging tools

### Production Environment
- **AWS ECS**: Managed container deployment
- **Auto Scaling**: CPU/memory based scaling policies
- **High Availability**: Multi-AZ deployment across availability zones
- **Monitoring**: Comprehensive CloudWatch integration

## Performance Characteristics

### Scalability
- **Horizontal Scaling**: ECS services can scale to handle increased load
- **Database Scaling**: RDS read replicas for query performance
- **Cache Scaling**: ElastiCache cluster mode for high throughput

### Performance Targets
- **API Latency**: <2 seconds for learning path generation
- **Vector Search**: <2 seconds for Neo4j Aura queries
- **Database Queries**: <100ms for indexed operations
- **Cache Operations**: <10ms for Redis operations

## Maintenance & Operations

### Backup Strategy
- **RDS**: Automated daily backups with 30-day retention
- **Neo4j Aura**: Managed backup service
- **Configuration**: Infrastructure as Code in Git

### Update Process
- **Rolling Deployments**: Blue-green deployment strategy
- **Database Migrations**: Alembic-based schema versioning
- **Container Updates**: ECR-based image management

This comprehensive documentation provides a complete overview of all system components and their relationships within the LearnTrac learning management system.