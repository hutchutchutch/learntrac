# LearnTrac Architecture Diagrams

## High-Level System Architecture

```mermaid
graph TB
    subgraph "Internet"
        User[Users/Browsers]
        API[API Clients]
    end
    
    subgraph "AWS Cloud - us-east-2"
        subgraph "Public Subnet"
            ALB[Application Load Balancer<br/>hutch-learntrac-dev-alb]
            IGW[Internet Gateway]
        end
        
        subgraph "Private Subnet A"
            subgraph "ECS Fargate Cluster"
                Trac[Trac Service<br/>Python 2.7<br/>Port: 8000]
                LearnAPI[LearnTrac API<br/>Python 3.11<br/>Port: 8001]
            end
        end
        
        subgraph "Private Subnet B"
            subgraph "Data Layer"
                RDS[(RDS PostgreSQL 15<br/>hutch-learntrac-dev-db)]
                Redis[(ElastiCache Redis 7<br/>hutch-learntrac-dev-redis)]
            end
        end
        
        subgraph "AWS Services"
            Cognito[AWS Cognito<br/>User Pool]
            Secrets[AWS Secrets Manager]
            ECR[ECR Repositories]
            CloudWatch[CloudWatch Logs]
        end
        
        subgraph "External Services"
            Neo4j[(Neo4j Aura<br/>Vector Store)]
            OpenAI[OpenAI API<br/>GPT-4]
        end
    end
    
    User --> IGW
    API --> IGW
    IGW --> ALB
    ALB --> Trac
    ALB --> LearnAPI
    
    Trac --> RDS
    Trac --> Redis
    Trac --> Cognito
    
    LearnAPI --> RDS
    LearnAPI --> Redis
    LearnAPI --> Cognito
    LearnAPI --> Neo4j
    LearnAPI --> OpenAI
    LearnAPI --> Secrets
    
    Trac --> CloudWatch
    LearnAPI --> CloudWatch
    
    ECR --> Trac
    ECR --> LearnAPI
    
    style ALB fill:#f9f,stroke:#333,stroke-width:4px
    style RDS fill:#bbf,stroke:#333,stroke-width:2px
    style Redis fill:#fbb,stroke:#333,stroke-width:2px
    style Cognito fill:#bfb,stroke:#333,stroke-width:2px
```

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant ALB
    participant Trac
    participant LearnAPI
    participant Cognito
    participant RDS
    participant Redis
    participant Neo4j
    participant OpenAI
    
    User->>ALB: HTTP Request
    ALB->>Cognito: Validate JWT Token
    Cognito-->>ALB: Token Valid
    
    alt Trac Request
        ALB->>Trac: Forward to /trac/*
        Trac->>RDS: Query Trac Tables
        RDS-->>Trac: Return Data
        Trac->>Redis: Cache Session
        Redis-->>Trac: Session Cached
        Trac-->>ALB: HTML Response
    else Learning API Request
        ALB->>LearnAPI: Forward to /api/learntrac/*
        LearnAPI->>Neo4j: Vector Search
        Neo4j-->>LearnAPI: Similar Chunks
        LearnAPI->>OpenAI: Generate Questions
        OpenAI-->>LearnAPI: Questions
        LearnAPI->>RDS: Store Progress
        RDS-->>LearnAPI: Stored
        LearnAPI->>Redis: Cache Results
        Redis-->>LearnAPI: Cached
        LearnAPI-->>ALB: JSON Response
    end
    
    ALB-->>User: Response
```

## Database Schema Architecture

```mermaid
erDiagram
    TICKET ||--o{ TICKET_CUSTOM : has
    TICKET ||--o{ CONCEPT_METADATA : references
    TICKET ||--o{ PREREQUISITES : has
    TICKET ||--o{ PREREQUISITES : prerequisite_for
    TICKET ||--o{ PROGRESS : tracks
    
    PATHS ||--o{ CONCEPT_METADATA : contains
    COGNITO_USER ||--o{ PATHS : creates
    COGNITO_USER ||--o{ PROGRESS : has
    
    TICKET {
        int id PK
        string type
        string summary
        string description
        timestamp created
        string status
    }
    
    TICKET_CUSTOM {
        int ticket FK
        string name
        string value
    }
    
    PATHS {
        uuid id PK
        string cognito_user_id
        string title
        json metadata
        timestamp created_at
    }
    
    CONCEPT_METADATA {
        uuid id PK
        int ticket_id FK
        uuid path_id FK
        string chunk_id
        string concept
        float difficulty
        json context
    }
    
    PREREQUISITES {
        int ticket_id FK
        int prerequisite_id FK
        timestamp created_at
    }
    
    PROGRESS {
        string cognito_user_id
        int ticket_id FK
        float score
        string status
        int attempts
        json feedback
        timestamp last_attempt
    }
```

## Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        subgraph "Edge Security"
            WAF[WAF Rules<br/>Optional]
            CloudFront[CloudFront CDN<br/>Optional]
        end
        
        subgraph "Application Security"
            ALB_SG[ALB Security Group<br/>Inbound: 80, 443<br/>Outbound: 8000, 8001]
            ECS_SG[ECS Task Security Group<br/>Inbound: 8000, 8001 from ALB<br/>Outbound: 5432, 6379, 443]
        end
        
        subgraph "Data Security"
            RDS_SG[RDS Security Group<br/>Inbound: 5432 from ECS<br/>Inbound: 5432 from 162.206.172.65]
            Redis_SG[Redis Security Group<br/>Inbound: 6379 from ECS]
        end
        
        subgraph "Identity & Access"
            IAM_Roles[IAM Roles<br/>ECS Task Execution<br/>ECS Task Role]
            Cognito_Auth[Cognito Auth<br/>JWT Tokens<br/>User Groups]
        end
        
        subgraph "Encryption"
            TLS[TLS in Transit<br/>HTTPS/SSL]
            Encryption[Encryption at Rest<br/>RDS Encrypted<br/>Secrets Encrypted]
        end
    end
    
    Internet --> WAF
    WAF --> CloudFront
    CloudFront --> ALB_SG
    ALB_SG --> ECS_SG
    ECS_SG --> RDS_SG
    ECS_SG --> Redis_SG
    
    IAM_Roles --> ECS_SG
    Cognito_Auth --> ALB_SG
    
    TLS -.-> ALB_SG
    TLS -.-> ECS_SG
    Encryption -.-> RDS_SG
    
    style ALB_SG fill:#f96,stroke:#333,stroke-width:2px
    style RDS_SG fill:#69f,stroke:#333,stroke-width:2px
    style Cognito_Auth fill:#6f9,stroke:#333,stroke-width:2px
```

## Deployment Architecture

```mermaid
graph LR
    subgraph "Development"
        Dev_Code[Local Development]
        Dev_Test[Local Testing]
    end
    
    subgraph "CI/CD Pipeline"
        GitHub[GitHub Repository]
        GH_Actions[GitHub Actions]
        Docker_Build[Docker Build]
        ECR_Push[ECR Push]
    end
    
    subgraph "AWS Infrastructure"
        ECR_Repo[ECR Repositories<br/>- trac<br/>- learntrac]
        ECS_Deploy[ECS Service Update]
        Fargate[Fargate Tasks]
    end
    
    subgraph "Infrastructure as Code"
        Terraform[Terraform Files]
        TF_State[Terraform State]
        AWS_Resources[AWS Resources]
    end
    
    Dev_Code --> GitHub
    GitHub --> GH_Actions
    GH_Actions --> Docker_Build
    Docker_Build --> ECR_Push
    ECR_Push --> ECR_Repo
    ECR_Repo --> ECS_Deploy
    ECS_Deploy --> Fargate
    
    Dev_Code --> Terraform
    Terraform --> TF_State
    TF_State --> AWS_Resources
    
    style GitHub fill:#f9f,stroke:#333,stroke-width:2px
    style ECR_Repo fill:#9ff,stroke:#333,stroke-width:2px
    style Terraform fill:#f99,stroke:#333,stroke-width:2px
```

## Network Flow Diagram

```mermaid
graph TB
    subgraph "VPC - Default"
        subgraph "Availability Zone A"
            subgraph "Public Subnet A"
                ALB_A[ALB Node A]
                NAT_A[NAT Gateway A]
            end
            subgraph "Private Subnet A"
                ECS_A[ECS Tasks A]
                RDS_Primary[(RDS Primary)]
            end
        end
        
        subgraph "Availability Zone B"
            subgraph "Public Subnet B"
                ALB_B[ALB Node B]
                NAT_B[NAT Gateway B]
            end
            subgraph "Private Subnet B"
                ECS_B[ECS Tasks B]
                RDS_Standby[(RDS Standby)]
                Redis_Node[(Redis Node)]
            end
        end
        
        IGW[Internet Gateway]
        VPC_Endpoints[VPC Endpoints<br/>- S3<br/>- Secrets Manager<br/>- ECR]
    end
    
    Internet --> IGW
    IGW --> ALB_A
    IGW --> ALB_B
    
    ALB_A --> ECS_A
    ALB_B --> ECS_B
    
    ECS_A --> NAT_A
    ECS_B --> NAT_B
    NAT_A --> Internet
    NAT_B --> Internet
    
    ECS_A --> RDS_Primary
    ECS_B --> RDS_Primary
    ECS_A --> Redis_Node
    ECS_B --> Redis_Node
    
    RDS_Primary -.-> RDS_Standby
    
    ECS_A --> VPC_Endpoints
    ECS_B --> VPC_Endpoints
    
    style IGW fill:#9f9,stroke:#333,stroke-width:4px
    style RDS_Primary fill:#99f,stroke:#333,stroke-width:2px
    style Redis_Node fill:#f99,stroke:#333,stroke-width:2px
```

## Cost Optimization View

```mermaid
pie title Monthly AWS Cost Distribution (Estimated)
    "RDS PostgreSQL (db.t3.micro)" : 15
    "ECS Fargate (2 services)" : 30
    "Application Load Balancer" : 20
    "ElastiCache Redis" : 15
    "Data Transfer" : 10
    "CloudWatch Logs" : 5
    "Secrets Manager" : 3
    "ECR Storage" : 2
```

## Disaster Recovery Architecture

```mermaid
graph TB
    subgraph "Primary Region (us-east-2)"
        Primary_RDS[(RDS Primary)]
        Primary_Redis[(Redis Primary)]
        Primary_Secrets[Secrets Manager]
        Primary_Snapshots[Automated Snapshots<br/>7-day retention]
    end
    
    subgraph "Backup Storage"
        S3_Backups[S3 Backup Bucket<br/>- DB Snapshots<br/>- Terraform State<br/>- Application Configs]
        Manual_Snapshots[Manual Snapshots<br/>On-demand]
    end
    
    subgraph "Recovery Options"
        Restore_RDS[Restore from Snapshot<br/>RTO: 30 min]
        Rebuild_Infra[Terraform Apply<br/>RTO: 15 min]
        Import_Data[Data Import<br/>RTO: Variable]
    end
    
    Primary_RDS --> Primary_Snapshots
    Primary_Snapshots --> S3_Backups
    Primary_RDS --> Manual_Snapshots
    Manual_Snapshots --> S3_Backups
    
    Primary_Secrets --> S3_Backups
    
    S3_Backups --> Restore_RDS
    S3_Backups --> Rebuild_Infra
    S3_Backups --> Import_Data
    
    style Primary_RDS fill:#f96,stroke:#333,stroke-width:2px
    style S3_Backups fill:#6f9,stroke:#333,stroke-width:2px
    style Restore_RDS fill:#9f6,stroke:#333,stroke-width:2px
```

---

These diagrams provide a comprehensive view of the LearnTrac infrastructure architecture. They can be rendered using any Mermaid-compatible viewer or documentation tool.