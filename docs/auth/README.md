# Authentication Documentation

This directory contains comprehensive documentation for the LearnTrac authentication system and migration from HTTP Basic Auth to AWS Cognito token-based authentication.

## Documents

### 1. [auth_migration.md](./auth_migration.md)
**Main migration guide** - Comprehensive analysis of current authentication and migration strategy
- Current HTTP Basic Auth architecture
- Component-by-component analysis
- AWS Cognito integration status
- Detailed migration steps
- Security considerations
- Testing and rollback plans

### 2. [cognito_implementation_guide.md](./cognito_implementation_guide.md)
**Technical implementation details** - Deep dive into Cognito integration
- Current plugin analysis
- Enhanced implementation requirements
- Secure token validation
- Bearer token authentication
- Permission mapping system
- Code examples and best practices

### 3. [api_authentication_examples.md](./api_authentication_examples.md)
**Practical API usage examples** - How to authenticate with the API
- Session-based authentication (current)
- Bearer token authentication (future)
- Client examples (Python, JavaScript, cURL)
- Postman collection
- Error handling patterns
- Testing strategies

## Quick Summary

### Current State
- **Traditional Auth**: HTTP Basic Auth via web server (DISABLED)
- **Current Auth**: AWS Cognito OAuth2 flow (ENABLED)
- **Session Management**: Cookie-based sessions after Cognito login
- **API Auth**: Session-based (no Bearer token support yet)

### Migration Status
✅ **Completed**:
- Cognito OAuth2 integration
- Login/logout flow via Cognito hosted UI
- Session management
- Basic user attribute mapping

⏳ **Pending**:
- Bearer token validation for APIs
- Token refresh mechanism
- Cognito groups to Trac permissions mapping
- Secure JWT validation
- API endpoint protection

### Key Configuration
```ini
[cognito]
client_id = 5adkv019v4rcu6o87ffg46ep02
domain = hutch-learntrac-dev-auth
region = us-east-2
user_pool_id = us-east-2_IvxzMrWwg

[components]
cognitoauth.* = enabled
trac.web.auth.loginmodule = disabled
```

### Next Steps
1. Implement secure JWT token validation
2. Add Bearer token support for API endpoints
3. Implement token refresh mechanism
4. Map Cognito groups to Trac permissions
5. Add comprehensive logging and monitoring
6. Perform security testing
7. Create rollback procedures

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│  Trac App   │────▶│  AWS RDS    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │
       │                    │
       ▼                    ▼
┌─────────────┐     ┌─────────────┐
│  Cognito    │     │  Session    │
│  Hosted UI  │     │   Store     │
└─────────────┘     └─────────────┘
```

## Security Considerations

1. **Token Storage**: Use httpOnly cookies or sessionStorage, never localStorage
2. **HTTPS**: Always required for production
3. **Token Validation**: Must verify JWT signatures
4. **CORS**: Properly configure for API access
5. **Rate Limiting**: Implement to prevent abuse

## Support

For questions or issues related to authentication:
1. Check the detailed documentation in this directory
2. Review the Trac logs at `/workspaces/learntrac/log/trac.log`
3. Test authentication flow using examples in `api_authentication_examples.md`
4. Contact the development team with specific error messages and steps to reproduce