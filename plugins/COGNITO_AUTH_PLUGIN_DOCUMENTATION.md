# Cognito Authentication Plugin for Trac

## Overview

The Cognito Authentication Plugin integrates AWS Cognito with Trac, providing JWT-based authentication and authorization. This plugin replaces Trac's default authentication system with AWS Cognito's secure, scalable authentication service.

## Features

- **JWT Token Validation**: Cryptographically secure validation of Cognito JWT tokens
- **OAuth2 Flow Support**: Full OAuth2 authorization code flow with Cognito hosted UI
- **Bearer Token Authentication**: API authentication via Authorization header
- **Group-Based Permissions**: Automatic mapping of Cognito groups to Trac permissions
- **Session Management**: Secure session handling with token refresh support
- **Custom Claims Support**: Integration with Lambda-generated custom claims
- **Metrics & Logging**: Comprehensive authentication event tracking

## Architecture

The plugin consists of several components:

1. **Main Plugin** (`trac_cognito_auth.py`): Core authentication logic
2. **Token Validator** (`cognito_token_validator.py`): JWT validation with JWKS
3. **Permission Policy** (`cognito_permission_policy.py`): Group-to-permission mapping
4. **Metrics** (`cognito_metrics.py`): Authentication event tracking

## Installation

### Prerequisites

- Trac 1.4+ installed and configured
- Python 3.7+
- AWS Cognito User Pool configured
- Required Python packages: `pyjwt`, `requests`, `cryptography`

### Installation Steps

1. **Install the plugin**:
   ```bash
   cd /path/to/trac/plugins
   python setup.py bdist_egg
   cp dist/TracCognitoAuth-*.egg /path/to/trac/environment/plugins/
   ```

2. **Configure trac.ini**:
   ```ini
   [components]
   cognitoauth.* = enabled
   trac.web.auth.loginmodule = disabled
   
   [cognito]
   region = us-east-2
   user_pool_id = us-east-2_IvxzMrWwg
   client_id = 5adkv019v4rcu6o87ffg46ep02
   domain = hutch-learntrac-dev-auth
   
   [trac]
   permission_policies = CognitoPermissionPolicy, DefaultPermissionPolicy
   ```

3. **Restart Trac**:
   ```bash
   sudo systemctl restart trac
   ```

## Configuration

### Required Settings (trac.ini)

```ini
[cognito]
# AWS Region where Cognito User Pool is located
region = us-east-2

# Cognito User Pool ID
user_pool_id = us-east-2_IvxzMrWwg

# App Client ID from Cognito
client_id = 5adkv019v4rcu6o87ffg46ep02

# Cognito domain (without .auth.region.amazoncognito.com)
domain = hutch-learntrac-dev-auth
```

### Optional Settings

```ini
[cognito]
# Enable debug logging
debug = true

# Token cache TTL (seconds)
jwks_cache_ttl = 3600

# Custom permission mappings (JSON)
custom_permissions = {"special_group": ["SPECIAL_PERM1", "SPECIAL_PERM2"]}
```

## Authentication Flows

### 1. Web Browser Authentication

```
User → /auth/login → Cognito Hosted UI → /auth/callback → Trac Session
```

1. User clicks "Login" link
2. Redirected to Cognito hosted UI
3. User authenticates with Cognito
4. Redirected back with authorization code
5. Plugin exchanges code for tokens
6. Session created with user info and permissions

### 2. API Bearer Token Authentication

```
Client → API Request (Bearer Token) → Token Validation → Access Granted/Denied
```

1. Client includes JWT in Authorization header
2. Plugin validates token with JWKS
3. Extracts user info and permissions
4. Grants or denies access based on permissions

## Permission Mapping

### Default Group Mappings

| Cognito Group | Trac Permissions |
|---------------|------------------|
| admins | TRAC_ADMIN, TICKET_ADMIN, MILESTONE_ADMIN, WIKI_ADMIN, PERMISSION_GRANT, PERMISSION_REVOKE |
| instructors | TICKET_CREATE, TICKET_MODIFY, TICKET_VIEW, MILESTONE_CREATE, MILESTONE_MODIFY, MILESTONE_VIEW, WIKI_CREATE, WIKI_MODIFY, WIKI_VIEW, etc. |
| students | TICKET_CREATE, TICKET_VIEW, MILESTONE_VIEW, WIKI_VIEW, CHANGESET_VIEW, TIMELINE_VIEW, SEARCH_VIEW, REPORT_VIEW |

### Custom Permissions

Permissions can also be set via Lambda in the JWT token:

```python
# In Lambda pre-token generation
event['response']['claimsOverrideDetails']['claimsToAddOrOverride']['trac_permissions'] = 'TICKET_CREATE,WIKI_MODIFY,CUSTOM_PERM'
```

## API Usage

### Bearer Token Authentication

```bash
# Include JWT in Authorization header
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     https://trac.example.com/api/tickets
```

### Token Refresh

```bash
# Refresh expired tokens
curl -X POST https://trac.example.com/auth/refresh \
     -H "Content-Type: application/json" \
     -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

## Troubleshooting

### Common Issues

1. **"Token validation failed"**
   - Check token expiration
   - Verify JWKS URL is accessible
   - Ensure client_id matches token audience

2. **"No permissions granted"**
   - Verify user is in appropriate Cognito group
   - Check group-to-permission mappings
   - Review Lambda custom claims

3. **"Authentication loop"**
   - Clear browser cookies
   - Check redirect_uri configuration
   - Verify Cognito app client settings

### Debug Mode

Enable debug logging:

```ini
[logging]
log_type = file
log_level = DEBUG
log_file = trac.log

[cognito]
debug = true
```

### Logs to Check

1. **Trac log**: General authentication flow
2. **Cognito CloudWatch**: Lambda execution and errors
3. **Browser console**: OAuth redirect issues

## Security Considerations

1. **Token Storage**: Tokens are stored in secure session storage
2. **HTTPS Required**: Always use HTTPS in production
3. **Token Validation**: All tokens are cryptographically verified
4. **CORS**: Configure CORS appropriately for API access
5. **Session Security**: Sessions expire with token expiration

## Metrics and Monitoring

The plugin tracks authentication events:

- Successful/failed login attempts
- Token validation performance
- Permission check statistics
- Group membership distribution

Access metrics via Trac's admin panel or CloudWatch integration.

## Development

### Running Tests

```bash
cd /path/to/plugin
python -m pytest tests/
```

### Adding Custom Permissions

1. Modify `cognito_permission_policy.py`:
   ```python
   GROUP_PERMISSIONS['new_group'] = ['NEW_PERM1', 'NEW_PERM2']
   ```

2. Update Lambda for custom claims
3. Restart Trac

### Extending the Plugin

Key extension points:

- `IAuthenticator`: Modify authentication logic
- `IPermissionPolicy`: Customize permission checks
- `IRequestFilter`: Add request preprocessing
- `IRequestHandler`: Add new endpoints

## Migration from Default Auth

1. **Backup existing data**:
   ```bash
   trac-admin /path/to/env hotcopy /path/to/backup
   ```

2. **Map existing users** to Cognito
3. **Update permissions** in Cognito groups
4. **Enable plugin** and disable default auth
5. **Test thoroughly** before production

## Support and Maintenance

### Version Compatibility

| Plugin Version | Trac Version | Cognito Features |
|----------------|--------------|------------------|
| 0.1 | 1.4+ | Basic OAuth2, JWT validation |
| 0.2 | 1.4+ | Bearer tokens, custom claims |
| 0.3 | 1.5+ | Token refresh, metrics |

### Known Limitations

- No automatic user provisioning (users must exist in Cognito)
- Groups must be pre-configured in Cognito
- Token size limited by HTTP header constraints

### Getting Help

1. Check Trac logs for detailed error messages
2. Enable debug mode for verbose logging
3. Verify Cognito configuration in AWS Console
4. Review JWT token contents at jwt.io

## License

This plugin is distributed under the same license as Trac (BSD-like).

## Credits

Developed for the LearnTrac project to integrate AWS Cognito authentication with Trac's ticket and wiki system.