# Learning Path Macro - Cognito Authentication Integration

## Overview

The Learning Path Macro has been integrated with AWS Cognito authentication to ensure that only authenticated users can access learning paths. This integration leverages the existing Cognito authentication plugin in Trac.

## Authentication Flow

1. **User Access**: When a user tries to use the `[[LearningPath]]` macro in a wiki page
2. **Authentication Check**: The macro checks if the user is authenticated via Cognito
3. **Authenticated Users**: If authenticated, the learning path content is displayed with personalized welcome message
4. **Unauthenticated Users**: If not authenticated, a friendly message is shown with a login link

## Implementation Details

### Authentication Check

The macro performs the following checks:
- Verifies `cognito_username` exists in the session
- Confirms `authenticated` flag is set to `true`
- Ensures `req.authname` is not `anonymous`

```python
def _is_authenticated(self, req):
    cognito_username = req.session.get('cognito_username')
    authenticated = req.session.get('authenticated', False)
    has_authname = req.authname and req.authname != 'anonymous'
    return authenticated and cognito_username and has_authname
```

### User Information

The macro retrieves and uses the following user information:
- Username (Cognito username)
- Email address
- Display name
- User groups

### Authentication Required Display

When authentication is required, users see:
- Clear message explaining authentication is needed
- Direct link to the Cognito login page
- Benefits of authentication (progress tracking, personalized content, etc.)

## Testing

Run the authentication integration tests:

```bash
cd /path/to/plugins/learningpathmacro
python test_auth_integration.py
```

## Configuration

The authentication integration uses the existing Cognito configuration in `trac.ini`:

```ini
[cognito]
user_pool_id = us-east-2_IvxzMrWwg
client_id = 5adkv019v4rcu6o87ffg46ep02
domain = hutch-learntrac-dev-auth
region = us-east-2
```

## Error Handling

The macro handles various authentication scenarios:
- Missing session data
- Expired sessions
- Anonymous users
- Invalid authentication states

## Security Considerations

1. **Session Validation**: Always validates the Cognito session data
2. **Permission Checks**: Maintains existing Trac permission system
3. **No Direct Token Handling**: Relies on the Cognito auth plugin for token management
4. **Secure Redirects**: Uses Trac's built-in URL generation for login links

## Future Enhancements

- Role-based content filtering based on Cognito groups
- Progress tracking tied to Cognito user ID
- Personalized learning recommendations
- Multi-factor authentication support