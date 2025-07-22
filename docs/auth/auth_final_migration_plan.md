Complete AWS Cognito Token-Based Authentication Migration Guide for LearnTrac
Executive Summary
This guide provides step-by-step instructions to complete the migration from HTTP Basic Authentication to AWS Cognito token-based authentication for the LearnTrac application. The infrastructure has been deployed via Terraform, and now the application code needs to be updated to support full token-based authentication.
Current State
✅ Completed Infrastructure

AWS Cognito User Pool: us-east-2_IvxzMrWwg
Client ID: 5adkv019v4rcu6o87ffg46ep02
Domain: hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com
Lambda Pre-token Generation: hutch-learntrac-dev-cognito-pre-token
API Gateway: Created with Cognito Authorizer
User Groups: admins, instructors, students

✅ Existing Implementation

OAuth2 login flow via Cognito Hosted UI
Session-based authentication after login
Basic ID token decoding (without cryptographic verification)

❌ Missing Components

Secure JWT token validation
Bearer token authentication for API endpoints
Token refresh mechanism
Permission mapping from Cognito groups to Trac permissions
Client-side token management

Implementation Plan
Phase 1: Backend Token Validation (Priority: HIGH)
Step 1.1: Install Required Dependencies
bashcd /path/to/learntrac
pip install PyJWT>=2.8.0 cryptography>=41.0.0 requests-cache>=1.1.0
Step 1.2: Create Secure Token Validator
Create a new file: plugins/cognito_token_validator.py
pythonimport jwt
from jwt import PyJWKClient
import time
from functools import lru_cache
from trac.core import Component, TracError
import requests
import json

class CognitoTokenValidator(Component):
    """Validates AWS Cognito JWT tokens with cryptographic verification"""
    
    def __init__(self):
        super().__init__()
        self.region = self.config.get('cognito', 'region', 'us-east-2')
        self.user_pool_id = self.config.get('cognito', 'user_pool_id', 'us-east-2_IvxzMrWwg')
        self.client_id = self.config.get('cognito', 'client_id', '5adkv019v4rcu6o87ffg46ep02')
        
        # JWKS URL for token verification
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        self._jwks_client = None
    
    @property
    def jwks_client(self):
        """Lazy load and cache JWKS client"""
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(self.jwks_url, cache_keys=True)
        return self._jwks_client
    
    def validate_token(self, token):
        """
        Validate and decode a Cognito JWT token
        Returns decoded claims if valid, raises TracError if invalid
        """
        try:
            # Get the signing key from Cognito's JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and verify the token
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "auth_time", "cognito:username"]
                }
            )
            
            # Additional validation
            token_use = decoded.get('token_use')
            if token_use not in ['id', 'access']:
                raise TracError(f"Invalid token_use: {token_use}")
            
            # Log successful validation
            self.log.debug(f"Token validated for user: {decoded.get('cognito:username')}")
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            raise TracError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise TracError(f"Invalid token: {str(e)}")
        except Exception as e:
            self.log.error(f"Token validation error: {str(e)}")
            raise TracError("Token validation failed")
    
    def extract_user_info(self, claims):
        """Extract user information from token claims"""
        return {
            'username': claims.get('cognito:username', claims.get('sub')),
            'email': claims.get('email'),
            'groups': claims.get('cognito:groups', []),
            'custom_permissions': claims.get('trac_permissions', '').split(','),
            'token_use': claims.get('token_use'),
            'exp': claims.get('exp'),
            'iat': claims.get('iat')
        }
Step 1.3: Update Main Cognito Plugin
Modify plugins/trac_cognito_auth.py to use the secure validator:
pythonfrom trac.core import *
from trac.web.api import IAuthenticator, IRequestFilter, IRequestHandler
from trac.web.chrome import INavigationContributor
from trac.util.translation import _
from cognito_token_validator import CognitoTokenValidator
import json

class CognitoAuthPlugin(Component):
    implements(IAuthenticator, IRequestFilter, IRequestHandler, INavigationContributor)
    
    def __init__(self):
        super().__init__()
        self.token_validator = CognitoTokenValidator(self.env)
        
    # Add Bearer token support to pre_process_request
    def pre_process_request(self, req, handler):
        # Check for Bearer token in Authorization header
        auth_header = req.get_header('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            
            try:
                # Validate the token
                claims = self.token_validator.validate_token(token)
                user_info = self.token_validator.extract_user_info(claims)
                
                # Set authentication info
                req.authname = user_info['username']
                req.session['email'] = user_info['email']
                req.session['cognito_groups'] = json.dumps(user_info['groups'])
                req.session['cognito_permissions'] = json.dumps(user_info['custom_permissions'])
                req.session['authenticated'] = True
                req.session['token_auth'] = True  # Mark as token-based auth
                
                # Set token expiry for refresh handling
                req.session['token_exp'] = user_info['exp']
                
                self.log.info(f"User {user_info['username']} authenticated via Bearer token")
                
            except TracError as e:
                # For API endpoints, return 401
                if req.path_info.startswith('/api/'):
                    self._send_auth_challenge(req, str(e))
                    raise RequestDone
                # For web pages, let normal auth flow handle it
                else:
                    self.log.debug(f"Bearer token validation failed: {e}")
        
        # Existing session check code continues here...
        return handler
    
    def _send_auth_challenge(self, req, error_message):
        """Send 401 Unauthorized response with WWW-Authenticate header"""
        req.send_response(401)
        req.send_header('WWW-Authenticate', 'Bearer realm="Trac API"')
        req.send_header('Content-Type', 'application/json')
        req.end_headers()
        
        error_response = {
            'error': 'unauthorized',
            'message': error_message,
            'auth_url': f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/login?client_id={self.client_id}&response_type=code&scope=email+openid+profile&redirect_uri={req.base_url}/auth/callback"
        }
        
        req.write(json.dumps(error_response).encode('utf-8'))
Phase 2: Token Refresh Implementation
Step 2.1: Create Token Refresh Handler
Add to plugins/trac_cognito_auth.py:
pythonclass TokenRefreshHandler(Component):
    implements(IRequestHandler)
    
    def match_request(self, req):
        return req.path_info == '/auth/refresh'
    
    def process_request(self, req):
        """Handle token refresh requests"""
        if req.method != 'POST':
            req.send_response(405)
            req.send_header('Allow', 'POST')
            req.end_headers()
            raise RequestDone
        
        try:
            # Parse request body
            content_length = int(req.get_header('Content-Length', 0))
            body = req.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
            
            refresh_token = data.get('refresh_token')
            if not refresh_token:
                raise TracError('Missing refresh_token')
            
            # Exchange refresh token for new tokens
            token_url = f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/oauth2/token"
            
            response = requests.post(
                token_url,
                data={
                    'grant_type': 'refresh_token',
                    'client_id': self.client_id,
                    'refresh_token': refresh_token
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            if response.status_code == 200:
                tokens = response.json()
                
                # Return new tokens
                req.send_response(200)
                req.send_header('Content-Type', 'application/json')
                req.send_header('Cache-Control', 'no-store')
                req.end_headers()
                
                req.write(json.dumps({
                    'access_token': tokens.get('access_token'),
                    'id_token': tokens.get('id_token'),
                    'expires_in': tokens.get('expires_in', 3600),
                    'token_type': 'Bearer'
                }).encode('utf-8'))
                
            else:
                error_data = response.json()
                raise TracError(f"Token refresh failed: {error_data.get('error_description', 'Unknown error')}")
                
        except json.JSONDecodeError:
            self._send_error(req, 400, 'Invalid JSON')
        except TracError as e:
            self._send_error(req, 401, str(e))
        except Exception as e:
            self.log.error(f"Token refresh error: {str(e)}")
            self._send_error(req, 500, 'Internal server error')
        
        raise RequestDone
    
    def _send_error(self, req, status_code, message):
        """Send error response"""
        req.send_response(status_code)
        req.send_header('Content-Type', 'application/json')
        req.end_headers()
        req.write(json.dumps({'error': message}).encode('utf-8'))
Phase 3: Permission Mapping System
Step 3.1: Create Permission Policy
Create plugins/cognito_permission_policy.py:
pythonfrom trac.core import Component, implements
from trac.perm import IPermissionPolicy
import json

class CognitoPermissionPolicy(Component):
    implements(IPermissionPolicy)
    
    # Map Cognito groups to Trac permissions
    GROUP_PERMISSIONS = {
        'admins': [
            'TRAC_ADMIN',
            'TICKET_ADMIN',
            'MILESTONE_ADMIN',
            'WIKI_ADMIN',
            'PERMISSION_GRANT',
            'PERMISSION_REVOKE'
        ],
        'instructors': [
            'TICKET_CREATE',
            'TICKET_MODIFY',
            'TICKET_VIEW',
            'MILESTONE_CREATE',
            'MILESTONE_MODIFY',
            'MILESTONE_VIEW',
            'WIKI_CREATE',
            'WIKI_MODIFY',
            'WIKI_VIEW',
            'CHANGESET_VIEW',
            'TIMELINE_VIEW',
            'SEARCH_VIEW',
            'REPORT_CREATE',
            'REPORT_MODIFY',
            'REPORT_VIEW'
        ],
        'students': [
            'TICKET_CREATE',
            'TICKET_VIEW',
            'MILESTONE_VIEW',
            'WIKI_VIEW',
            'CHANGESET_VIEW',
            'TIMELINE_VIEW',
            'SEARCH_VIEW',
            'REPORT_VIEW'
        ]
    }
    
    def check_permission(self, action, username, resource, perm):
        """Check if user has permission based on Cognito groups"""
        if not hasattr(perm, 'req') or not perm.req:
            return None
        
        # Get user's Cognito groups from session
        groups_json = perm.req.session.get('cognito_groups', '[]')
        try:
            groups = json.loads(groups_json)
        except:
            groups = []
        
        # Get custom permissions from token
        perms_json = perm.req.session.get('cognito_permissions', '[]')
        try:
            custom_perms = json.loads(perms_json)
        except:
            custom_perms = []
        
        # Check if action is in custom permissions (from Lambda)
        if action in custom_perms:
            self.log.debug(f"Permission {action} granted to {username} via custom token claims")
            return True
        
        # Check if any group grants the requested permission
        for group in groups:
            if action in self.GROUP_PERMISSIONS.get(group, []):
                self.log.debug(f"Permission {action} granted to {username} via group {group}")
                return True
        
        # Let other policies decide
        return None
Phase 4: Frontend Token Management
Step 4.1: Create Token Manager JavaScript
Create htdocs/js/cognito-token-manager.js:
javascript/**
 * Cognito Token Manager for Trac
 * Handles token storage, refresh, and API authentication
 */
class CognitoTokenManager {
    constructor() {
        this.accessToken = null;
        this.idToken = null;
        this.refreshToken = null;
        this.expiresAt = null;
        this.refreshTimer = null;
        
        // Load tokens from session storage
        this.loadTokens();
        
        // Set up automatic refresh
        this.scheduleRefresh();
    }
    
    loadTokens() {
        const stored = sessionStorage.getItem('cognito_tokens');
        if (stored) {
            try {
                const tokens = JSON.parse(stored);
                this.accessToken = tokens.accessToken;
                this.idToken = tokens.idToken;
                this.refreshToken = tokens.refreshToken;
                this.expiresAt = tokens.expiresAt;
            } catch (e) {
                console.error('Failed to load tokens:', e);
            }
        }
    }
    
    saveTokens(tokens) {
        this.accessToken = tokens.access_token || tokens.accessToken;
        this.idToken = tokens.id_token || tokens.idToken;
        this.refreshToken = tokens.refresh_token || tokens.refreshToken;
        
        // Calculate expiration time
        const expiresIn = tokens.expires_in || 3600;
        this.expiresAt = Date.now() + (expiresIn * 1000);
        
        // Store in session storage (not localStorage for security)
        sessionStorage.setItem('cognito_tokens', JSON.stringify({
            accessToken: this.accessToken,
            idToken: this.idToken,
            refreshToken: this.refreshToken,
            expiresAt: this.expiresAt
        }));
        
        // Schedule next refresh
        this.scheduleRefresh();
    }
    
    async refreshTokens() {
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }
        
        try {
            const response = await fetch('/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    refresh_token: this.refreshToken
                })
            });
            
            if (!response.ok) {
                throw new Error('Token refresh failed');
            }
            
            const tokens = await response.json();
            this.saveTokens(tokens);
            
            console.log('Tokens refreshed successfully');
            return tokens;
            
        } catch (error) {
            console.error('Token refresh failed:', error);
            // Clear tokens and redirect to login
            this.clearTokens();
            window.location.href = '/auth/login';
            throw error;
        }
    }
    
    scheduleRefresh() {
        // Clear existing timer
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }
        
        if (!this.expiresAt || !this.refreshToken) {
            return;
        }
        
        // Schedule refresh 5 minutes before expiry
        const refreshTime = this.expiresAt - Date.now() - (5 * 60 * 1000);
        
        if (refreshTime > 0) {
            this.refreshTimer = setTimeout(() => {
                this.refreshTokens().catch(console.error);
            }, refreshTime);
        } else {
            // Token already expired or about to expire
            this.refreshTokens().catch(console.error);
        }
    }
    
    async getValidToken() {
        // Check if token needs refresh
        if (!this.accessToken || Date.now() >= this.expiresAt - 60000) {
            await this.refreshTokens();
        }
        
        return this.accessToken;
    }
    
    clearTokens() {
        this.accessToken = null;
        this.idToken = null;
        this.refreshToken = null;
        this.expiresAt = null;
        sessionStorage.removeItem('cognito_tokens');
        
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }
    }
    
    // Helper method to make authenticated API calls
    async authenticatedFetch(url, options = {}) {
        const token = await this.getValidToken();
        
        return fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`
            }
        });
    }
}

// Create global instance
window.tracTokenManager = new CognitoTokenManager();

// Override jQuery AJAX to add authentication
if (typeof jQuery !== 'undefined') {
    jQuery.ajaxSetup({
        beforeSend: function(xhr, settings) {
            // Only add auth header for API calls
            if (settings.url && settings.url.startsWith('/api/')) {
                const token = window.tracTokenManager.accessToken;
                if (token) {
                    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
                }
            }
        }
    });
}

// Handle authentication errors globally
window.addEventListener('fetch', function(event) {
    event.respondWith(
        fetch(event.request).then(response => {
            if (response.status === 401) {
                // Token might be expired, try to refresh
                return window.tracTokenManager.refreshTokens().then(() => {
                    // Retry the request with new token
                    const token = window.tracTokenManager.accessToken;
                    const newRequest = new Request(event.request, {
                        headers: new Headers({
                            ...event.request.headers,
                            'Authorization': `Bearer ${token}`
                        })
                    });
                    return fetch(newRequest);
                });
            }
            return response;
        })
    );
});
Phase 5: Update trac.ini Configuration
Step 5.1: Update Component Configuration
Edit conf/trac.ini:
ini[components]
# Disable traditional login module
trac.web.auth.loginmodule = disabled

# Enable Cognito components
cognitoauth.* = enabled
trac_cognito_auth.* = enabled
cognito_token_validator.* = enabled
cognito_permission_policy.* = enabled

[trac]
# Update permission policies to include Cognito
permission_policies = CognitoPermissionPolicy, DefaultWikiPolicy, DefaultTicketPolicy, DefaultPermissionPolicy, LegacyAttachmentPolicy

[cognito]
# AWS Cognito configuration
client_id = 5adkv019v4rcu6o87ffg46ep02
domain = hutch-learntrac-dev-auth
region = us-east-2
user_pool_id = us-east-2_IvxzMrWwg

# Token settings
token_expiry_buffer = 300  # Refresh tokens 5 minutes before expiry
enable_token_caching = true
jwks_cache_ttl = 3600  # Cache JWKS for 1 hour

# API Authentication
api_paths = /api/*, /jsonrpc
require_token_for_api = true
Phase 6: Testing and Validation
Step 6.1: Create Test Script
Create test_cognito_auth.py:
python#!/usr/bin/env python
import requests
import json
import sys
import boto3
from datetime import datetime

class CognitoAuthTester:
    def __init__(self, base_url, client_id, region, user_pool_id):
        self.base_url = base_url
        self.client_id = client_id
        self.region = region
        self.user_pool_id = user_pool_id
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        self.session = requests.Session()
    
    def test_login_flow(self, username, password):
        """Test the complete login flow"""
        print(f"\n1. Testing login for user: {username}")
        
        try:
            # Authenticate with Cognito
            response = self.cognito_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            tokens = response['AuthenticationResult']
            print("✓ Successfully authenticated with Cognito")
            print(f"  - Access Token: {tokens['AccessToken'][:50]}...")
            print(f"  - ID Token: {tokens['IdToken'][:50]}...")
            print(f"  - Expires In: {tokens['ExpiresIn']} seconds")
            
            return tokens
            
        except Exception as e:
            print(f"✗ Login failed: {str(e)}")
            return None
    
    def test_api_with_token(self, token):
        """Test API access with Bearer token"""
        print("\n2. Testing API access with Bearer token")
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test various endpoints
        endpoints = [
            '/api/tickets',
            '/api/wiki',
            '/api/milestones'
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print(f"✓ {endpoint}: Success (200)")
                else:
                    print(f"✗ {endpoint}: Failed ({response.status_code})")
                    print(f"  Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"✗ {endpoint}: Error - {str(e)}")
    
    def test_token_refresh(self, refresh_token):
        """Test token refresh endpoint"""
        print("\n3. Testing token refresh")
        
        try:
            response = self.session.post(
                f"{self.base_url}/auth/refresh",
                json={'refresh_token': refresh_token}
            )
            
            if response.status_code == 200:
                new_tokens = response.json()
                print("✓ Token refresh successful")
                print(f"  - New Access Token: {new_tokens['access_token'][:50]}...")
                return new_tokens
            else:
                print(f"✗ Token refresh failed ({response.status_code})")
                print(f"  Response: {response.text}")
                
        except Exception as e:
            print(f"✗ Token refresh error: {str(e)}")
        
        return None
    
    def test_invalid_token(self):
        """Test API response to invalid token"""
        print("\n4. Testing invalid token handling")
        
        headers = {'Authorization': 'Bearer invalid.token.here'}
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/tickets",
                headers=headers
            )
            
            if response.status_code == 401:
                print("✓ Invalid token correctly rejected (401)")
                auth_header = response.headers.get('WWW-Authenticate')
                if auth_header and 'Bearer' in auth_header:
                    print("✓ WWW-Authenticate header present")
            else:
                print(f"✗ Unexpected status code: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    def test_permission_mapping(self, token, expected_group):
        """Test that Cognito groups map to Trac permissions"""
        print(f"\n5. Testing permission mapping for group: {expected_group}")
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test operations based on group
        if expected_group == 'admins':
            # Admins should be able to delete
            response = self.session.delete(
                f"{self.base_url}/api/tickets/99999",
                headers=headers
            )
            if response.status_code in [200, 404]:  # 404 is ok, means auth worked
                print("✓ Admin permission check passed")
            else:
                print(f"✗ Admin permission check failed ({response.status_code})")
                
        elif expected_group == 'students':
            # Students should NOT be able to delete
            response = self.session.delete(
                f"{self.base_url}/api/tickets/99999",
                headers=headers
            )
            if response.status_code == 403:
                print("✓ Student permission restriction working")
            else:
                print(f"✗ Student permission check failed ({response.status_code})")
    
    def run_all_tests(self, username, password, expected_group='students'):
        """Run all authentication tests"""
        print("=" * 60)
        print("COGNITO AUTHENTICATION TEST SUITE")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print(f"User Pool ID: {self.user_pool_id}")
        print(f"Client ID: {self.client_id}")
        print(f"Testing as: {username} (group: {expected_group})")
        
        # Test 1: Login
        tokens = self.test_login_flow(username, password)
        if not tokens:
            print("\n❌ Cannot proceed without valid tokens")
            return False
        
        # Test 2: API Access
        self.test_api_with_token(tokens['AccessToken'])
        
        # Test 3: Token Refresh
        if 'RefreshToken' in tokens:
            new_tokens = self.test_token_refresh(tokens['RefreshToken'])
        
        # Test 4: Invalid Token
        self.test_invalid_token()
        
        # Test 5: Permissions
        self.test_permission_mapping(tokens['AccessToken'], expected_group)
        
        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETE")
        print("=" * 60)
        
        return True

# Usage
if __name__ == "__main__":
    tester = CognitoAuthTester(
        base_url='http://localhost:8000',
        client_id='5adkv019v4rcu6o87ffg46ep02',
        region='us-east-2',
        user_pool_id='us-east-2_IvxzMrWwg'
    )
    
    # Test with different users
    tester.run_all_tests('student@example.com', 'StudentPass123!', 'students')
    tester.run_all_tests('admin@example.com', 'AdminPass123!', 'admins')
Phase 7: Migration Rollout
Step 7.1: Gradual Rollout Plan

Development Environment (Week 1)

Deploy all components
Run test suite
Fix any issues


Staging Environment (Week 2)

Deploy to staging
Test with real user accounts
Performance testing


Production Rollout (Week 3)

Enable token validation for API endpoints only
Monitor for 24 hours
Enable for all endpoints
Remove old authentication code



Step 7.2: Monitoring and Alerts
Add to your monitoring system:
python# Add to plugins/cognito_metrics.py
from trac.core import Component
from datetime import datetime

class CognitoMetrics(Component):
    """Track Cognito authentication metrics"""
    
    def record_auth_event(self, event_type, username, success, details=None):
        """Record authentication events for monitoring"""
        
        with self.env.db_transaction as db:
            db("""
                INSERT INTO auth_metrics 
                (timestamp, event_type, username, success, details)
                VALUES (%s, %s, %s, %s, %s)
            """, (datetime.now(), event_type, username, success, 
                  json.dumps(details) if details else None))
        
        # Log for immediate monitoring
        if success:
            self.log.info(f"Auth success: {event_type} for {username}")
        else:
            self.log.warning(f"Auth failure: {event_type} for {username} - {details}")
Final Checklist
Backend Implementation

 Install PyJWT and dependencies
 Create CognitoTokenValidator component
 Update CognitoAuthPlugin with Bearer token support
 Implement token refresh endpoint
 Create CognitoPermissionPolicy
 Update trac.ini configuration
 Deploy Lambda function changes

Frontend Implementation

 Add cognito-token-manager.js
 Update existing JavaScript to use token manager
 Test token refresh mechanism
 Ensure tokens are stored securely (sessionStorage)

Testing

 Run unit tests for token validation
 Test complete authentication flow
 Verify API endpoints require authentication
 Test token refresh mechanism
 Validate permission mapping
 Load test token validation performance

Security

 Verify JWT signatures are validated
 Ensure tokens expire properly
 Test invalid token rejection
 Verify HTTPS is enforced
 Check for token leakage in logs

Monitoring

 Set up authentication metrics
 Configure alerts for auth failures
 Monitor token validation latency
 Track refresh token usage

Documentation

 Update API documentation with auth requirements
 Create user migration guide
 Document troubleshooting steps
 Update developer setup instructions

Success Criteria
The migration is complete when:

All API endpoints require and validate Bearer tokens
Token refresh works automatically without user intervention
Cognito groups correctly map to Trac permissions
Session-based auth continues to work for web UI
No regression in existing functionality
Authentication latency < 100ms for cached tokens
Zero token validation errors in production for 48 hours

This completes the comprehensive migration plan from HTTP Basic Authentication to AWS Cognito token-based authentication for LearnTrac.