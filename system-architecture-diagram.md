# LearnTrac System Architecture Diagram

## High-Level System Architecture

```mermaid
graph TB
    subgraph "User Interface"
        UI1[Web Browser]
        UI2[Mobile/Progressive Web App]
    end
    
    subgraph "Authentication Layer"
        COGNITO[AWS Cognito<br/>User Pool & Identity Pool<br/>JWT Token Management]
    end
    
    subgraph "API Gateway Layer"
        APIGW[AWS API Gateway<br/>REST API<br/>Cognito Authorizer<br/>Rate Limiting]
    end
    
    subgraph "Load Balancing"
        ALB[Application Load Balancer<br/>SSL Termination<br/>Health Checks]
    end
    
    subgraph "Container Services (AWS ECS)"
        TRAC[Trac Container<br/>Python 2.7<br/>Port 8080<br/>Wiki & Ticket System]
        LEARN[Learning Service<br/>Python 3.11 FastAPI<br/>Port 8001<br/>Modern Learning Features]
    end
    
    subgraph "Data Layer"
        RDS[(AWS RDS PostgreSQL<br/>Trac Schema + Learning Schema<br/>Multi-AZ Deployment)]
        CACHE[(AWS ElastiCache Redis<br/>Search Results Cache<br/>Session Data)]
        NEO[(Neo4j Aura<br/>Vector Search<br/>Academic Content)]
    end
    
    subgraph "External Services"
        LLM[LLM APIs<br/>OpenAI/Anthropic<br/>Question Generation<br/>Answer Evaluation]
        S3[(AWS S3<br/>File Storage<br/>Generated Graphs)]
    end
    
    subgraph "Infrastructure"
        VPC[AWS VPC<br/>Private Subnets<br/>Security Groups]
        ECR[AWS ECR<br/>Container Registry]
        CLOUDWATCH[AWS CloudWatch<br/>Logging & Monitoring]
    end
    
    UI1 --> COGNITO
    UI2 --> COGNITO
    COGNITO --> APIGW
    APIGW --> ALB
    ALB --> TRAC
    ALB --> LEARN
    
    TRAC --> RDS
    LEARN --> RDS
    LEARN --> CACHE
    LEARN --> NEO
    APIGW --> LLM
    
    TRAC --> S3
    LEARN --> S3
    
    TRAC -.-> CLOUDWATCH
    LEARN -.-> CLOUDWATCH
    
    style COGNITO fill:#ff9900
    style APIGW fill:#ff9900
    style RDS fill:#ff9900
    style CACHE fill:#ff9900
    style ALB fill:#ff9900
    style NEO fill:#4caf50
    style LLM fill:#2196f3
```

## Detailed Component Architecture

### 1. Frontend & User Interface Layer

```mermaid
graph LR
    subgraph "User Interface Components"
        WIKI[Wiki Pages<br/>Learning Macros<br/>Interactive Forms]
        TICKETS[Ticket Views<br/>Question Interface<br/>Answer Submission]
        GRAPHS[Knowledge Graphs<br/>Progress Visualization<br/>GraphViz Rendered]
        DASHBOARD[Learning Dashboard<br/>Progress Tracking<br/>Analytics]
    end
    
    subgraph "Client-Side JavaScript"
        AUTH_JS[Cognito Auth SDK<br/>JWT Management<br/>Token Refresh]
        API_CLIENT[API Gateway Client<br/>HTTP Requests<br/>Error Handling]
        WEBSOCKET[WebSocket Client<br/>Real-time Updates<br/>Speech Processing]
    end
    
    WIKI --> AUTH_JS
    TICKETS --> AUTH_JS
    GRAPHS --> API_CLIENT
    DASHBOARD --> WEBSOCKET
```

### 2. Authentication & Security Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Cognito
    participant APIGateway
    participant Trac
    participant Learning
    
    User->>Browser: Access LearnTrac
    Browser->>Cognito: Login Request
    Cognito->>Browser: JWT Tokens (Access, ID, Refresh)
    Browser->>APIGateway: API Request + JWT
    APIGateway->>APIGateway: Validate JWT Token
    APIGateway->>Trac: Forward Authenticated Request
    Trac->>Learning: Internal API Call
    Learning->>APIGateway: Response
    APIGateway->>Browser: Final Response
```

### 3. Learning Service Microservice Architecture

```mermaid
graph TB
    subgraph "Learning Service (FastAPI)"
        MAIN[main.py<br/>FastAPI App<br/>Middleware Stack]
        CONFIG[config.py<br/>Settings Management<br/>Environment Variables]
        
        subgraph "API Routers"
            LEARNING_R[learning.py<br/>Path Generation<br/>Concept Creation]
            CHAT_R[chat.py<br/>AI Chat Interface<br/>Context Management]
            VOICE_R[voice.py<br/>Speech Processing<br/>Audio Analysis]
            EVAL_R[evaluation.py<br/>Answer Evaluation<br/>Progress Tracking]
            VECTOR_R[vector_search.py<br/>Neo4j Integration<br/>Similarity Search]
        end
        
        subgraph "Services Layer"
            NEO4J_S[neo4j_client.py<br/>Vector Database<br/>Academic Content]
            REDIS_S[redis_client.py<br/>Caching Layer<br/>Session Management]
            LLM_S[llm_service.py<br/>AI Integration<br/>Question Generation]
            TICKET_S[ticket_service.py<br/>Trac Integration<br/>Ticket Management]
        end
        
        subgraph "Database Layer"
            DB_MGR[database.py<br/>PostgreSQL Pool<br/>Connection Management]
            MODELS[models.py<br/>SQLAlchemy Models<br/>Schema Definitions]
        end
    end
    
    MAIN --> LEARNING_R
    MAIN --> CHAT_R
    MAIN --> VOICE_R
    MAIN --> EVAL_R
    MAIN --> VECTOR_R
    
    LEARNING_R --> NEO4J_S
    CHAT_R --> LLM_S
    VOICE_R --> REDIS_S
    EVAL_R --> TICKET_S
    VECTOR_R --> NEO4J_S
    
    NEO4J_S --> DB_MGR
    REDIS_S --> DB_MGR
    LLM_S --> DB_MGR
    TICKET_S --> MODELS
```

### 4. Trac Legacy System Integration

```mermaid
graph TB
    subgraph "Trac Container (Python 2.7)"
        TRAC_CORE[Trac Core<br/>Wiki Engine<br/>Ticket System]
        
        subgraph "Custom Plugins"
            COGNITO_PLUGIN[cognito_auth.py<br/>AWS Cognito Integration<br/>JWT Validation]
            LEARNING_PLUGIN[learning_macros.py<br/>Wiki Macros<br/>Learning Interface]
            DISPLAY_PLUGIN[learntrac_display/<br/>Knowledge Graphs<br/>Progress Views]
        end
        
        subgraph "Templates & Static"
            TEMPLATES[Custom Templates<br/>Learning UI<br/>Enhanced Views]
            STATIC[JavaScript & CSS<br/>Interactive Elements<br/>API Integration]
        end
    end
    
    TRAC_CORE --> COGNITO_PLUGIN
    TRAC_CORE --> LEARNING_PLUGIN
    TRAC_CORE --> DISPLAY_PLUGIN
    
    LEARNING_PLUGIN --> TEMPLATES
    DISPLAY_PLUGIN --> STATIC
```

### 5. Data Flow Architecture

```mermaid
flowchart LR
    subgraph "Data Sources"
        NEO4J[(Neo4j Aura<br/>Academic Chunks<br/>Vector Embeddings)]
        PDF[PDF Documents<br/>Textbook Content<br/>Learning Materials]
    end
    
    subgraph "Processing Pipeline"
        EXTRACT[PDF Extraction<br/>Content Chunking<br/>Structure Detection]
        EMBED[Embedding Generation<br/>OpenAI API<br/>Vector Creation]
        SEARCH[Vector Search<br/>Similarity Matching<br/>Relevance Scoring]
    end
    
    subgraph "Learning Generation"
        QUESTIONS[Question Generation<br/>LLM Processing<br/>Context Analysis]
        TICKETS[Ticket Creation<br/>Learning Concepts<br/>Progress Tracking]
        GRAPH[Knowledge Graph<br/>GraphViz Rendering<br/>Visual Progress]
    end
    
    subgraph "Persistence"
        RDS[(PostgreSQL<br/>Trac Schema<br/>Learning Schema)]
        CACHE[(Redis Cache<br/>Search Results<br/>User Sessions)]
    end
    
    PDF --> EXTRACT
    EXTRACT --> EMBED
    EMBED --> NEO4J
    NEO4J --> SEARCH
    SEARCH --> QUESTIONS
    QUESTIONS --> TICKETS
    TICKETS --> RDS
    TICKETS --> GRAPH
    
    SEARCH --> CACHE
    QUESTIONS --> CACHE
```

### 6. AWS Infrastructure Deployment

```mermaid
graph TB
    subgraph "AWS Cloud Infrastructure"
        subgraph "Compute Layer"
            ECS[AWS ECS Cluster<br/>Fargate Tasks<br/>Auto Scaling]
            LAMBDA[AWS Lambda<br/>Serverless Functions<br/>Event Processing]
        end
        
        subgraph "Networking"
            VPC[AWS VPC<br/>Private Subnets<br/>NAT Gateway<br/>Internet Gateway]
            ALB[Application Load Balancer<br/>SSL Termination<br/>Path-based Routing]
            SG[Security Groups<br/>Firewall Rules<br/>Access Control]
        end
        
        subgraph "Storage & Data"
            RDS[AWS RDS PostgreSQL<br/>Multi-AZ<br/>Automated Backups<br/>Read Replicas]
            ELASTICACHE[AWS ElastiCache<br/>Redis Cluster<br/>High Availability]
            S3[AWS S3<br/>Static Assets<br/>File Storage<br/>Backups]
        end
        
        subgraph "Security & Identity"
            COGNITO[AWS Cognito<br/>User Pool<br/>Identity Provider<br/>MFA Support]
            IAM[AWS IAM<br/>Roles & Policies<br/>Service Authentication]
            SECRETS[AWS Secrets Manager<br/>Database Credentials<br/>API Keys]
        end
        
        subgraph "Monitoring & Logging"
            CLOUDWATCH[AWS CloudWatch<br/>Metrics & Logs<br/>Alarms & Alerts]
            XRAY[AWS X-Ray<br/>Distributed Tracing<br/>Performance Insights]
        end
    end
    
    ECS --> VPC
    ALB --> ECS
    RDS --> VPC
    ELASTICACHE --> VPC
    COGNITO --> IAM
    ECS --> CLOUDWATCH
    LAMBDA --> XRAY
```

## System Integration Patterns

### 1. Event-Driven Architecture

```mermaid
graph LR
    subgraph "Event Sources"
        USER_ACTION[User Actions<br/>Answer Submission<br/>Progress Updates]
        SYSTEM_EVENT[System Events<br/>Ticket Creation<br/>Status Changes]
    end
    
    subgraph "Event Processing"
        EVENT_BUS[Event Bus<br/>Redis Pub/Sub<br/>Message Queue]
        HANDLERS[Event Handlers<br/>Business Logic<br/>Side Effects]
    end
    
    subgraph "Event Consumers"
        CACHE_UPDATE[Cache Updates<br/>Search Invalidation<br/>Graph Regeneration]
        NOTIFICATIONS[Notifications<br/>Progress Alerts<br/>Achievements]
        ANALYTICS[Analytics<br/>Usage Tracking<br/>Learning Insights]
    end
    
    USER_ACTION --> EVENT_BUS
    SYSTEM_EVENT --> EVENT_BUS
    EVENT_BUS --> HANDLERS
    HANDLERS --> CACHE_UPDATE
    HANDLERS --> NOTIFICATIONS
    HANDLERS --> ANALYTICS
```

### 2. Caching Strategy

```mermaid
graph TD
    subgraph "Cache Layers"
        CDN[CloudFront CDN<br/>Static Assets<br/>Global Distribution]
        API_CACHE[API Gateway Cache<br/>Response Caching<br/>5 minute TTL]
        REDIS[ElastiCache Redis<br/>Application Cache<br/>Session Storage]
        APP_CACHE[Application Cache<br/>In-Memory Cache<br/>Hot Data]
    end
    
    subgraph "Cache Patterns"
        WRITE_THROUGH[Write-Through<br/>Update Cache on Write<br/>Consistency Guarantee]
        WRITE_BEHIND[Write-Behind<br/>Async Cache Updates<br/>Performance Optimized]
        CACHE_ASIDE[Cache-Aside<br/>Lazy Loading<br/>Fault Tolerant]
    end
    
    CDN --> API_CACHE
    API_CACHE --> REDIS
    REDIS --> APP_CACHE
    
    WRITE_THROUGH --> REDIS
    WRITE_BEHIND --> REDIS
    CACHE_ASIDE --> REDIS
```

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | HTML5, JavaScript, CSS3 | User Interface |
| **Authentication** | AWS Cognito, JWT | User Management |
| **API Gateway** | AWS API Gateway | Request Routing |
| **Load Balancer** | AWS ALB | Traffic Distribution |
| **Legacy System** | Trac 1.4.4, Python 2.7 | Wiki & Tickets |
| **Modern API** | FastAPI, Python 3.11 | Learning Features |
| **Vector Database** | Neo4j Aura | Content Search |
| **Primary Database** | AWS RDS PostgreSQL | Data Persistence |
| **Cache** | AWS ElastiCache Redis | Performance |
| **Container Platform** | AWS ECS Fargate | Orchestration |
| **AI/ML** | OpenAI GPT-4, Anthropic Claude | Content Generation |
| **Monitoring** | AWS CloudWatch, X-Ray | Observability |
| **Storage** | AWS S3 | File Storage |

## Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        WAF[AWS WAF<br/>Web Application Firewall<br/>DDoS Protection]
        COGNITO_AUTH[AWS Cognito<br/>Multi-Factor Authentication<br/>Social Login Integration]
        API_AUTH[API Gateway Authorizer<br/>JWT Validation<br/>Rate Limiting]
        VPC_SEC[VPC Security<br/>Private Subnets<br/>Security Groups<br/>NACLs]
        ENCRYPTION[Encryption<br/>TLS in Transit<br/>AES-256 at Rest]
    end
    
    subgraph "Security Controls"
        IAM_ROLES[IAM Roles<br/>Least Privilege<br/>Service-to-Service Auth]
        SECRETS_MGR[Secrets Manager<br/>Credential Rotation<br/>Secure Storage]
        AUDIT_LOG[Audit Logging<br/>CloudTrail<br/>Access Monitoring]
    end
    
    WAF --> COGNITO_AUTH
    COGNITO_AUTH --> API_AUTH
    API_AUTH --> VPC_SEC
    VPC_SEC --> ENCRYPTION
    
    IAM_ROLES --> SECRETS_MGR
    SECRETS_MGR --> AUDIT_LOG
```

This comprehensive system architecture diagram illustrates the LearnTrac learning management system built on AWS infrastructure, integrating legacy Trac capabilities with modern learning features through a cloud-native, microservices approach.