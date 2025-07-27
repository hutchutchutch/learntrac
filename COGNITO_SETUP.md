# AWS Cognito Authentication Setup for LearnTrac

This document explains how to configure AWS Cognito authentication for LearnTrac's Trac interface.

## Overview

The Cognito authentication plugin replaces Trac's default login system with AWS Cognito, providing:
- Centralized user management
- OAuth 2.0 / OpenID Connect authentication
- JWT token-based sessions
- Integration with other AWS services

## Current Configuration

### Cognito User Pool Settings (from Terraform)
- **User Pool**: `hutch-learntrac-dev-users`
- **Domain**: `hutch-learntrac-dev-auth`
- **Region**: `us-east-2`
- **Client ID**: `5adkv019v4rcu6o87ffg46ep02`

### Callback URLs
- **Login Callback**: `http://localhost:8000/auth/callback`
- **Logout URL**: `http://localhost:8000/logout`

## How It Works

### 1. Login Flow
1. User accesses `/trac/login` or any protected page
2. Plugin redirects to Cognito hosted UI:
   ```
   https://hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com/login
   ```
3. User authenticates with Cognito
4. Cognito redirects back to `/auth/callback` with authorization code
5. Plugin exchanges code for JWT tokens
6. User is redirected to `/trac/wiki` (or original destination)

### 2. Session Management
- JWT tokens are stored in browser cookies
- Tokens are validated on each request
- Sessions expire based on Cognito settings (1 hour access token, 30 day refresh)

### 3. Logout Flow
1. User accesses `/trac/logout`
2. Cookies are cleared
3. User is redirected to Cognito logout endpoint
4. Cognito redirects back to application root

## Testing the Authentication

### 1. Start the Application
```bash
docker compose up
```

### 2. Access the Application
Navigate to: http://localhost:8000/trac/wiki

You should be redirected to the Cognito login page.

### 3. Create a Test User (if needed)
```bash
# Create user in Cognito
aws cognito-idp admin-create-user \
  --user-pool-id us-east-2_IvxzMrWwg \
  --username testuser@example.com \
  --user-attributes Name=email,Value=testuser@example.com \
  --temporary-password TempPass123! \
  --region us-east-2

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-2_IvxzMrWwg \
  --username testuser@example.com \
  --password YourSecurePassword123! \
  --permanent \
  --region us-east-2
```

## Troubleshooting

### Common Issues

1. **500 Error on /login**
   - Check trac.ini has correct Cognito settings
   - Verify plugin is installed and enabled
   - Check Docker logs: `docker logs trac-aws`

2. **Redirect Loop**
   - Ensure callback URL matches Cognito configuration
   - Check browser cookies are enabled
   - Verify JWT validation is working

3. **"Cognito authentication is not configured"**
   - Verify all Cognito settings in trac.ini
   - Ensure environment variables are set if using them

### Debug Mode

Enable debug logging in trac.ini:
```ini
[logging]
log_level = DEBUG
```

## Configuration Options

Add these to your `trac.ini` under `[cognito]`:

```ini
[cognito]
# AWS Region
region = us-east-2

# Cognito User Pool ID
user_pool_id = us-east-2_IvxzMrWwg

# Cognito App Client ID
client_id = 5adkv019v4rcu6o87ffg46ep02

# Cognito Domain (without .auth.<region>.amazoncognito.com)
domain = hutch-learntrac-dev-auth

# Path to redirect after login (default: /trac/wiki)
login_redirect_path = /trac/wiki

# Token expiry buffer in seconds (default: 300)
token_expiry_buffer = 300

# Enable token caching (default: true)
enable_token_caching = true

# JWKS cache TTL in seconds (default: 3600)
jwks_cache_ttl = 3600
```

## Security Considerations

1. **HTTPS in Production**: Always use HTTPS in production to protect JWT tokens
2. **Token Storage**: Tokens are stored in HTTP-only cookies
3. **CORS**: Configure CORS appropriately for your domain
4. **Secrets**: Never commit client secrets to version control

## Integration with Learning API

The Learning API can validate Cognito tokens for API requests:
- Include JWT in Authorization header: `Bearer <token>`
- API validates token with same JWKS endpoint
- User groups/roles are included in token claims

## Next Steps

1. Configure HTTPS for production deployment
2. Set up custom Cognito UI branding
3. Implement group-based permissions
4. Add MFA support
5. Configure password policies