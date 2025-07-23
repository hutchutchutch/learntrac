# AWS Cognito Integration for LearnTrac

## Overview

This document describes the AWS Cognito authentication integration for both Trac (Python 2.7) and LearnTrac API (Python 3.11) applications.

## Current Status

✅ **Successfully Implemented:**
- Trac legacy system with Cognito OAuth plugin
- LearnTrac API with JWT token verification
- Both containers running and healthy
- Connected to AWS RDS PostgreSQL
- Connected to AWS ElastiCache Redis
- Cognito configuration loaded from Terraform

## Architecture

```
┌─────────────┐     ┌────────────────┐     ┌─────────────┐
│   Browser   │────▶│  AWS Cognito   │────▶│    Trac     │
└─────────────┘     │  Hosted UI     │     │  Port 8000  │
                    └────────────────┘     └─────────────┘
                            │
                            │ JWT
                            ▼
                    ┌────────────────┐     ┌─────────────┐
                    │  LearnTrac API │────▶│   AWS RDS   │
                    │   Port 8001    │     │ PostgreSQL  │
                    └────────────────┘     └─────────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │  AWS Redis     │
                    │  ElastiCache   │
                    └────────────────┘
```

## Configuration

### Environment Variables

**Common:**
- `AWS_REGION`: us-east-2
- `COGNITO_USER_POOL_ID`: us-east-2_IvxzMrWwg
- `COGNITO_CLIENT_ID`: 5adkv019v4rcu6o87ffg46ep02
- `COGNITO_DOMAIN`: hutch-learntrac-dev-auth

**Trac Specific:**
- `DATABASE_URL`: postgres://[username]:[password]@[host]/[database]
- `TRAC_ENV`: /var/trac/projects

**LearnTrac API Specific:**
- `DATABASE_URL`: postgresql+asyncpg://[username]:[password]@[host]/[database]
- `REDIS_URL`: redis://[redis-endpoint]:6379
- `COGNITO_POOL_ID`: Same as COGNITO_USER_POOL_ID

## Authentication Flow

### 1. Trac Authentication
1. User visits http://localhost:8000
2. Clicks "Login" → Redirected to Cognito hosted UI
3. After login, redirected back to /auth/callback
4. Trac plugin validates OAuth code and creates session
5. User permissions assigned based on Cognito groups

### 2. LearnTrac API Authentication
1. User obtains JWT token from Cognito
2. Includes token in Authorization header: `Bearer <token>`
3. API validates token using Cognito JWKS
4. Extracts user info and groups from token
5. Enforces permissions based on groups

## User Groups & Permissions

### Cognito Groups
- **admins**: Full system access
- **instructors**: Create/modify content
- **students**: View content, enroll in courses

### Trac Permissions Mapping
- admins → TRAC_ADMIN
- instructors → TICKET_CREATE, TICKET_MODIFY, WIKI_CREATE, WIKI_MODIFY
- students → TICKET_VIEW, WIKI_VIEW

### API Endpoints by Group
- `/api/learntrac/admin/*` - Admins only
- `/api/learntrac/courses/{id}/enroll` - Authenticated users
- `/api/learntrac/courses` - Public (optional auth for filtering)

## Testing Authentication

### 1. Test Trac Login
```bash
# Visit in browser
http://localhost:8000/login

# This redirects to:
https://hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com/login?client_id=...
```

### 2. Test API Authentication
```bash
# Get token from Cognito (requires user credentials)
# Then test protected endpoint:
curl -H "Authorization: Bearer <token>" http://localhost:8001/api/learntrac/me
```

### 3. Test API Documentation
Visit http://localhost:8001/docs for interactive API documentation with authentication support.

## Local Development

### Building Images
```bash
cd docker
docker build -t learntrac/trac:test ./trac
docker build -t learntrac/api:test ./learntrac
```

### Running Containers
```bash
./test-local.sh
```

### Viewing Logs
```bash
docker logs -f trac-test
docker logs -f learntrac-test
```

### Stopping Containers
```bash
docker stop trac-test learntrac-test
docker rm trac-test learntrac-test
docker network rm learntrac-test
```

## Deployment to AWS

### 1. Tag Images
```bash
docker tag learntrac/trac:test 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest
docker tag learntrac/api:test 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac:latest
```

### 2. Push to ECR
```bash
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 971422717446.dkr.ecr.us-east-2.amazonaws.com
docker push 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac:latest
docker push 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac:latest
```

### 3. Update ECS Services
```bash
aws ecs update-service --cluster hutch-learntrac-dev-cluster --service hutch-learntrac-dev-trac --force-new-deployment --region us-east-2
aws ecs update-service --cluster hutch-learntrac-dev-cluster --service hutch-learntrac-dev-learntrac --force-new-deployment --region us-east-2
```

## Security Considerations

1. **JWT Verification**: Always verify JWT signatures using Cognito JWKS
2. **HTTPS Required**: In production, all traffic should use HTTPS
3. **Token Expiration**: Tokens expire after 1 hour by default
4. **CORS Configuration**: Configure CORS appropriately for your frontend
5. **Secrets Management**: Use AWS Secrets Manager for sensitive data

## Troubleshooting

### Common Issues

1. **"Invalid token" error**
   - Check token expiration
   - Verify COGNITO_CLIENT_ID matches
   - Ensure JWKS URL is accessible

2. **Login redirect fails**
   - Verify redirect_uri is registered in Cognito
   - Check COGNITO_DOMAIN configuration

3. **Database connection errors**
   - Verify RDS security group allows ECS tasks
   - Check credentials in Secrets Manager

4. **Redis connection errors**
   - Verify ElastiCache security group
   - Check Redis endpoint configuration

## Next Steps

1. Create test users in AWS Cognito console
2. Configure production redirect URIs
3. Set up monitoring and alerts
4. Implement refresh token handling
5. Add multi-factor authentication