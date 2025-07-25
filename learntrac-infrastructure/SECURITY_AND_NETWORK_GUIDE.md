# LearnTrac Security and Network Flow Documentation

**Last Updated:** 2025-07-25  
**Environment:** Development (dev)  
**AWS Region:** us-east-2

## Table of Contents

1. [Security Overview](#security-overview)
2. [Network Architecture](#network-architecture)
3. [Security Group Rules](#security-group-rules)
4. [Network Traffic Flow](#network-traffic-flow)
5. [IAM Roles and Policies](#iam-roles-and-policies)
6. [Encryption Standards](#encryption-standards)
7. [Access Control Matrix](#access-control-matrix)
8. [Security Best Practices](#security-best-practices)
9. [Compliance Checklist](#compliance-checklist)

## Security Overview

The LearnTrac infrastructure implements defense-in-depth security with multiple layers:

1. **Network Security**: VPC isolation, security groups, NACLs
2. **Identity & Access**: AWS Cognito, IAM roles, JWT tokens
3. **Data Protection**: Encryption at rest and in transit
4. **Secrets Management**: AWS Secrets Manager
5. **Monitoring**: CloudWatch logs and metrics

## Network Architecture

### VPC Configuration

```
VPC Type: Default VPC
Region: us-east-2
DNS Resolution: Enabled
DNS Hostnames: Enabled
```

### Subnet Layout

```
┌─────────────────────────────────────────────────────┐
│                    VPC (Default)                     │
├─────────────────────────┬───────────────────────────┤
│    Public Subnets       │      Private Subnets       │
├─────────────────────────┼───────────────────────────┤
│ • ALB                   │ • ECS Tasks               │
│ • NAT Gateway           │ • RDS Instance            │
│ • Internet Gateway      │ • ElastiCache Redis       │
└─────────────────────────┴───────────────────────────┘
```

### VPC Endpoints (Security & Performance)

| Endpoint | Type | Purpose |
|----------|------|---------|
| S3 | Gateway | Direct S3 access without internet |
| ECR API | Interface | Private container registry access |
| ECR DKR | Interface | Private Docker registry access |
| Secrets Manager | Interface | Secure secrets retrieval |
| CloudWatch Logs | Interface | Private log streaming |

## Security Group Rules

### 1. ALB Security Group

**ID:** `sg-[alb-security-group-id]`  
**Name:** `hutch-learntrac-dev-alb-sg`

| Direction | Port | Protocol | Source/Dest | Description |
|-----------|------|----------|-------------|-------------|
| Ingress | 80 | TCP | 0.0.0.0/0 | HTTP from internet |
| Ingress | 443 | TCP | 0.0.0.0/0 | HTTPS from internet |
| Egress | 8000 | TCP | ECS SG | To Trac service |
| Egress | 8001 | TCP | ECS SG | To LearnTrac API |

### 2. ECS Task Security Group

**ID:** `sg-[ecs-task-security-group-id]`  
**Name:** `hutch-learntrac-dev-ecs-task-sg`

| Direction | Port | Protocol | Source/Dest | Description |
|-----------|------|----------|-------------|-------------|
| Ingress | 8000 | TCP | ALB SG | From ALB to Trac |
| Ingress | 8001 | TCP | ALB SG | From ALB to API |
| Egress | 5432 | TCP | RDS SG | To PostgreSQL |
| Egress | 6379 | TCP | Redis SG | To Redis cache |
| Egress | 443 | TCP | 0.0.0.0/0 | HTTPS to AWS services |
| Egress | 80 | TCP | 0.0.0.0/0 | HTTP for package updates |

### 3. RDS Security Group

**ID:** `sg-0456074f9f3016cdf`  
**Name:** `hutch-learntrac-dev-rds-sg`

| Direction | Port | Protocol | Source/Dest | Description |
|-----------|------|----------|-------------|-------------|
| Ingress | 5432 | TCP | 162.206.172.65/32 | Developer access |
| Ingress | 5432 | TCP | ECS Task SG | From ECS services |
| Egress | All | All | 0.0.0.0/0 | All outbound |

### 4. ElastiCache Redis Security Group

**ID:** `sg-[redis-security-group-id]`  
**Name:** `hutch-learntrac-dev-redis-sg`

| Direction | Port | Protocol | Source/Dest | Description |
|-----------|------|----------|-------------|-------------|
| Ingress | 6379 | TCP | ECS Task SG | From ECS services |
| Egress | All | All | 0.0.0.0/0 | All outbound |

## Network Traffic Flow

### 1. User Authentication Flow

```
User Browser → ALB (Port 80/443)
    ↓
ALB → Cognito Hosted UI
    ↓
Cognito → User Browser (Redirect with JWT)
    ↓
User Browser → ALB (with JWT Bearer token)
    ↓
ALB → ECS Task (Port 8000/8001)
    ↓
ECS Task → Cognito (JWT validation via HTTPS)
```

### 2. Database Query Flow

```
ECS Task → RDS PostgreSQL (Port 5432)
    - Connection via private subnet
    - SSL/TLS encrypted connection
    - Uses connection pooling
```

### 3. Cache Operations Flow

```
ECS Task → ElastiCache Redis (Port 6379)
    - Connection via private subnet
    - Used for session storage
    - Used for query result caching
```

### 4. External API Flow

```
ECS Task → NAT Gateway → Internet Gateway → External APIs
    - Neo4j Aura (HTTPS Port 443)
    - OpenAI API (HTTPS Port 443)
    - All traffic goes through NAT for security
```

## IAM Roles and Policies

### ECS Task Execution Role

**Role Name:** `hutch-learntrac-dev-ecs-task-execution-role`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-2:*:log-group:/ecs/hutch-learntrac-dev/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-2:*:secret:hutch-learntrac-dev-*"
      ]
    }
  ]
}
```

### ECS Task Role

**Role Name:** `hutch-learntrac-dev-ecs-task-role`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds-data:ExecuteStatement",
        "rds-data:BatchExecuteStatement"
      ],
      "Resource": "arn:aws:rds:us-east-2:*:cluster:hutch-learntrac-dev-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-2:*:secret:hutch-learntrac-dev-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticache:DescribeCacheClusters"
      ],
      "Resource": "*"
    }
  ]
}
```

### Lambda Execution Role (Future)

**Role Name:** `hutch-learntrac-dev-lambda-execution-role`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-2:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-2:*:secret:hutch-learntrac-dev-openai-*"
    }
  ]
}
```

## Encryption Standards

### Data at Rest

| Service | Encryption Type | Key Management |
|---------|----------------|----------------|
| RDS PostgreSQL | AES-256 | AWS managed keys |
| Secrets Manager | AES-256 | AWS managed keys |
| CloudWatch Logs | AES-256 | AWS managed keys |
| S3 (future) | AES-256 | AWS managed keys |

### Data in Transit

| Connection | Protocol | Certificate |
|------------|----------|-------------|
| User → ALB | HTTPS/TLS 1.2+ | ACM certificate (future) |
| ALB → ECS | HTTP | Internal VPC (secure) |
| ECS → RDS | SSL/TLS | RDS certificate |
| ECS → Redis | TLS | ElastiCache managed |
| ECS → External | HTTPS/TLS 1.2+ | Public CA certificates |

## Access Control Matrix

| Resource | Admin Access | Developer Access | Application Access | User Access |
|----------|--------------|------------------|-------------------|-------------|
| AWS Console | Full | Read-only | None | None |
| RDS Database | Full via IP | Query via IP | Full via ECS | None |
| ElastiCache | Console only | None | Read/Write via ECS | None |
| ECS Tasks | Full | View logs | N/A | None |
| Secrets | Full | None | Read via IAM | None |
| ALB | Full | View only | N/A | HTTP/HTTPS |
| Cognito | Full | Manage users | Validate tokens | Auth only |

## Security Best Practices

### 1. Network Security

- ✅ Use VPC endpoints for AWS services
- ✅ Implement least privilege security groups
- ✅ Enable VPC Flow Logs (recommended)
- ✅ Use private subnets for databases
- ⚠️ Review RDS public accessibility
- ⚠️ Implement Network ACLs for additional security

### 2. Identity and Access

- ✅ Use Cognito for user authentication
- ✅ Implement JWT token validation
- ✅ Use IAM roles, not access keys
- ✅ Enable MFA for AWS console access
- ⚠️ Implement API rate limiting
- ⚠️ Add IP allowlisting for admin access

### 3. Data Protection

- ✅ Encrypt data at rest
- ✅ Use SSL/TLS for data in transit
- ✅ Store secrets in Secrets Manager
- ✅ Enable RDS backup encryption
- ⚠️ Implement database audit logging
- ⚠️ Add data masking for PII

### 4. Monitoring and Compliance

- ✅ Enable CloudWatch logging
- ✅ Set up basic metrics
- ⚠️ Implement CloudTrail for API auditing
- ⚠️ Configure AWS Config for compliance
- ⚠️ Set up security alerts
- ⚠️ Perform regular security assessments

## Compliance Checklist

### AWS Well-Architected Framework - Security Pillar

- [x] **Identity and Access Management**
  - Cognito for user management
  - IAM roles for service access
  - No hardcoded credentials

- [x] **Detective Controls**
  - CloudWatch logging enabled
  - VPC Flow Logs available

- [x] **Infrastructure Protection**
  - Security groups configured
  - Private subnets for data layer
  - VPC endpoints implemented

- [x] **Data Protection**
  - Encryption at rest enabled
  - TLS for data in transit
  - Secrets properly managed

- [ ] **Incident Response** (To Do)
  - Create incident response plan
  - Set up automated alerts
  - Define escalation procedures

### Security Recommendations

1. **Immediate Actions**
   - Review and restrict RDS public accessibility
   - Implement CloudTrail logging
   - Add WAF for ALB protection

2. **Short-term Improvements**
   - Set up AWS Config rules
   - Implement automated security scanning
   - Add network flow monitoring

3. **Long-term Enhancements**
   - Achieve SOC 2 compliance
   - Implement zero-trust architecture
   - Add advanced threat detection

## Security Incident Response

### Incident Types and Response

1. **Unauthorized Access Attempt**
   ```bash
   # Check CloudWatch logs
   aws logs filter-log-events --log-group-name /ecs/hutch-learntrac-dev/trac \
     --filter-pattern "unauthorized OR 401 OR 403"
   
   # Review Cognito events
   aws cognito-idp admin-list-user-auth-events --user-pool-id us-east-2_IvxzMrWwg \
     --username [USERNAME]
   ```

2. **Database Breach Attempt**
   ```bash
   # Check RDS logs
   aws rds describe-db-log-files --db-instance-identifier hutch-learntrac-dev-db
   
   # Review security group changes
   aws ec2 describe-security-groups --group-ids sg-0456074f9f3016cdf \
     --query 'SecurityGroups[0].IpPermissions'
   ```

3. **DDoS Attack**
   ```bash
   # Check ALB metrics
   aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
     --metric-name RequestCount --dimensions Name=LoadBalancer,Value=[ALB_NAME] \
     --start-time [TIME] --end-time [TIME] --period 300 --statistics Sum
   ```

### Emergency Contacts

- **AWS Support:** [Support case URL]
- **Security Team:** [Contact information]
- **On-call Engineer:** [Contact information]

---

This security documentation should be reviewed and updated regularly as the infrastructure evolves.