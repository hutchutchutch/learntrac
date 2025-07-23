# AWS Cognito Integration for LearnTrac

## 🔐 Authentication Architecture

Both Trac (Python 2.7) and LearnTrac API (Python 3.11) have been integrated with AWS Cognito for centralized authentication.

### AWS Cognito Infrastructure (from Terraform)

1. **User Pool**: `hutch-learntrac-dev-users`
   - Password policy: 8+ chars, requires uppercase, lowercase, numbers, symbols
   - User attributes: email (required), name (required), role (custom)
   - Auto-verified attributes: email

2. **User Groups**:
   - `admins` - Full administrative access
   - `instructors` - Teaching and content management
   - `students` - Learning and participation

3. **Cognito Domain**: `hutch-learntrac-dev-auth`
   - Login URL: `https://hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com/login`
   - Logout URL: `https://hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com/logout`

4. **Lambda Trigger**: Pre-token generation
   - Maps Cognito groups to Trac permissions
   - Adds custom claims to JWT tokens

## 🚀 Implementation Details

### Trac Legacy (Python 2.7)

**Plugin Location**: `/docker/trac/plugins/cognito_auth.py`

Features:
- Custom IAuthenticator implementation
- Redirects `/login` to AWS Cognito
- Handles OAuth callback at `/auth/callback`
- Stores user info and permissions in session
- Custom login template with AWS branding

**Configuration**: `/docker/trac/config/trac.ini`
- Disables default login module
- Enables Cognito auth plugin
- Sets auth cookie parameters

### LearnTrac API (Python 3.11)

**Auth Module**: `/docker/learntrac/src/auth.py`

Features:
- JWT token verification with JWKS
- FastAPI dependency injection for auth
- Protected endpoints with `get_current_user`
- Optional auth with `get_optional_user`

**New Endpoints**:
- `GET /login` - Redirect to Cognito login
- `GET /logout` - Redirect to Cognito logout
- `GET /auth/callback` - OAuth callback handler
- `GET /api/learntrac/user` - Get current user info (protected)

## 🔧 Environment Variables

Both services require these environment variables:

```bash
# Required
COGNITO_CLIENT_ID=<from terraform output>
COGNITO_POOL_ID=<from terraform output>
AWS_REGION=us-east-2

# Optional (with defaults)
COGNITO_DOMAIN=hutch-learntrac-dev-auth
```

## 🛡️ Security Features

1. **JWT Verification**: All API requests verify JWT signatures against Cognito JWKS
2. **Permission Mapping**: Lambda function maps groups to granular permissions
3. **Session Security**: Trac uses secure session cookies
4. **HTTPS Redirect**: Ready for production HTTPS deployment

## 📝 User Permissions Mapping

From the Lambda function:

**Admins**:
- TRAC_ADMIN, TICKET_ADMIN, WIKI_ADMIN
- MILESTONE_ADMIN, LEARNING_ADMIN

**Instructors**:
- TICKET_CREATE, TICKET_MODIFY
- WIKI_CREATE, WIKI_MODIFY
- LEARNING_INSTRUCT, LEARNING_MENTOR

**Students**:
- TICKET_VIEW, WIKI_VIEW, TICKET_CREATE
- LEARNING_PARTICIPATE, LEARNING_PRACTICE

## 🧪 Testing Authentication

1. **Get Cognito credentials from Terraform**:
   ```bash
   cd learntrac-infrastructure
   terraform output cognito_client_id
   terraform output cognito_user_pool_id
   ```

2. **Set environment variables**:
   ```bash
   export COGNITO_CLIENT_ID=<client-id>
   export COGNITO_POOL_ID=<pool-id>
   ```

3. **Start services**:
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

4. **Test login flows**:
   - Trac: Visit http://localhost:8000/login
   - API: Visit http://localhost:8001/login

## 🚀 Production Deployment

For AWS ECS deployment:

1. The Terraform already sets these environment variables in ECS task definitions
2. Update callback URLs in Cognito to use ALB URLs
3. Enable HTTPS on ALB for secure authentication
4. Configure Cognito to use custom domain if needed

## 📊 Authentication Flow

```
User → App Login → Redirect to Cognito → User Auth → Callback with Code 
→ Exchange Code for Tokens → Verify JWT → Set Session → Access Granted
```

## 🔍 Troubleshooting

1. **Invalid redirect_uri**: Ensure callback URLs match Cognito client settings
2. **Token verification fails**: Check COGNITO_POOL_ID is correct
3. **Missing permissions**: Verify user is in correct Cognito group
4. **Session issues**: Check cookie settings and domain configuration

## 🎯 Next Steps

1. Create Cognito users via AWS Console or API
2. Test authentication flows end-to-end
3. Implement token refresh logic
4. Add user registration flow if needed
5. Configure MFA for enhanced security