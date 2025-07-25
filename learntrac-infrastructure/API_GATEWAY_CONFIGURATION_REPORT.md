# API Gateway Configuration Report

**Date:** 2025-07-25  
**Task:** 1.3 - Configure API Gateway with Cognito Authorizer  
**Status:** Completed

## Executive Summary

The API Gateway has been enhanced with comprehensive Cognito authorization, proper resource structure, CORS configuration, and example Lambda integrations. The configuration now provides a secure REST API foundation for the LearnTrac system.

## Configuration Overview

### 1. API Gateway Structure
- **API Name:** `hutch-learntrac-dev-api`
- **Stage:** Development (dev)
- **Region:** us-east-2
- **Authorizer:** Cognito User Pools

### 2. Resource Hierarchy

```
/
├── /auth (Public endpoints)
│   ├── /login    [POST] - User authentication
│   ├── /refresh  [POST] - Token refresh
│   └── /logout   [POST] - User logout
│
├── /api
│   └── /v1 (Protected endpoints - require JWT)
│       ├── /learning
│       │   ├── /courses         [GET, POST] - Course management
│       │   ├── /courses/{id}    [GET, PUT, DELETE] - Specific course
│       │   └── /assignments     [GET, POST] - Assignment management
│       │
│       └── /trac
│           ├── /tickets         [GET, POST] - Ticket management
│           └── /wiki           [GET, POST] - Wiki pages
```

### 3. Authorization Configuration

#### Cognito Authorizer Settings:
- **Type:** COGNITO_USER_POOLS
- **Identity Source:** `method.request.header.Authorization`
- **Token Validation:** Automatic JWT signature verification
- **Provider ARN:** Points to LearnTrac User Pool

#### Authorization Scopes:
- `learntrac-api/read` - Read access to protected resources
- `learntrac-api/write` - Write access to protected resources
- `learntrac-api/admin` - Administrative access

### 4. CORS Configuration

CORS is properly configured for all endpoints with:
- **Allowed Origins:** `*` (configure for specific domains in production)
- **Allowed Methods:** `GET, POST, PUT, DELETE, OPTIONS`
- **Allowed Headers:** `Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token`
- **Preflight Caching:** 300 seconds

### 5. Security Features

#### Request Validation:
- Body validation enabled
- Parameter validation enabled
- Custom request validators configured

#### Throttling:
- **Rate Limit:** 100 requests per second
- **Burst Limit:** 200 requests
- **Daily Quota:** 10,000 requests per API key

#### Logging:
- CloudWatch logs enabled
- Structured JSON logging format
- 7-day retention (dev) / 30-day retention (prod)
- X-Ray tracing available for production

### 6. Lambda Integration

Created example Lambda handler demonstrating:
- JWT claims extraction
- Permission-based authorization
- Role-based content filtering
- Proper error handling
- CORS response headers

## Files Created/Modified

### New Files:
1. `api-gateway-enhanced.tf` - Complete API Gateway configuration
2. `lambda/api-handler-example.py` - Example Lambda function for API endpoints
3. `test-api-gateway.sh` - Testing script for API endpoints
4. `API_GATEWAY_CONFIGURATION_REPORT.md` - This documentation

### Integration Points:
- Integrates with existing Cognito User Pool
- References Cognito authorizer from main.tf
- Compatible with existing VPC and security groups

## Testing Instructions

### 1. Deploy the Configuration:
```bash
cd /learntrac-infrastructure
terraform plan -target=aws_api_gateway_rest_api.learntrac_api
terraform apply -target=aws_api_gateway_rest_api.learntrac_api
```

### 2. Get API Gateway URL:
```bash
terraform output api_gateway_url
```

### 3. Test Public Endpoints:
```bash
# Health check (if implemented)
curl https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/health

# Login endpoint (if Lambda connected)
curl -X POST https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"password"}'
```

### 4. Test Protected Endpoints:

First, obtain a JWT token from Cognito:
```bash
# Using AWS CLI
aws cognito-idp initiate-auth \
  --client-id 5adkv019v4rcu6o87ffg46ep02 \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=testuser,PASSWORD=TestPass123!
```

Then test with the token:
```bash
# Get courses
curl https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/api/v1/learning/courses \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Create course (requires instructor/admin role)
curl -X POST https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/api/v1/learning/courses \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"New Course","description":"Description","duration":"4 weeks"}'
```

### 5. Verify CORS:
```bash
# Preflight request
curl -X OPTIONS https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/api/v1/learning/courses \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization"
```

## JWT Token Structure

When a request is made with a valid JWT token, the Lambda function receives:

```json
{
  "requestContext": {
    "authorizer": {
      "claims": {
        "sub": "user-uuid",
        "email": "user@example.com",
        "trac_permissions": "TICKET_VIEW,WIKI_VIEW,LEARNING_PARTICIPATE",
        "custom:groups": "students",
        "custom:primary_role": "student",
        "custom:course_enrollments": "course-001,course-002",
        "custom:session_id": "user_20250125120000"
      }
    }
  }
}
```

## Next Steps

1. **Connect Lambda Functions:**
   - Deploy actual Lambda functions for each endpoint
   - Update API Gateway integrations to point to Lambda ARNs
   - Implement database connections in Lambda functions

2. **Configure Custom Domain:**
   - Set up Route 53 domain
   - Create ACM certificate
   - Configure custom domain in API Gateway

3. **Production Hardening:**
   - Restrict CORS origins to specific domains
   - Implement API key requirements
   - Enable AWS WAF for additional protection
   - Configure CloudFront distribution

4. **Monitoring Setup:**
   - Create CloudWatch dashboards
   - Set up alarms for error rates
   - Configure X-Ray service map
   - Enable detailed metrics

## Environment Variables for Integration

Applications connecting to the API should use:
```bash
# API Configuration
API_GATEWAY_URL=https://your-api-id.execute-api.us-east-2.amazonaws.com/dev
API_VERSION=v1

# Authentication
COGNITO_POOL_ID=us-east-2_IvxzMrWwg
COGNITO_CLIENT_ID=5adkv019v4rcu6o87ffg46ep02
COGNITO_DOMAIN=hutch-learntrac-dev-auth
```

## Security Considerations

1. **Token Validation:**
   - JWT tokens are automatically validated by API Gateway
   - Signature verification against Cognito's public keys
   - Expiration time checked on every request

2. **Permission Checking:**
   - Lambda functions must verify user permissions from JWT claims
   - Implement principle of least privilege
   - Log all authorization decisions

3. **Rate Limiting:**
   - Usage plan enforces rate limits
   - Consider implementing per-user rate limiting
   - Monitor for abuse patterns

4. **Data Protection:**
   - Enable encryption in transit (TLS 1.2+)
   - Sanitize all user inputs
   - Implement request/response validation

## Conclusion

The API Gateway is now properly configured with Cognito authorization, providing a secure foundation for the LearnTrac API. The configuration includes proper CORS handling, request validation, and example implementations for common patterns. The next phase involves connecting actual Lambda functions and implementing the business logic for each endpoint.