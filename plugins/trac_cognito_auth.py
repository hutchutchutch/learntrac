from trac.core import *
from trac.web.api import IAuthenticator, IRequestFilter, IRequestHandler
from trac.web.chrome import INavigationContributor, add_notice, add_warning
from trac.util.translation import _
from cognito_token_validator import CognitoTokenValidator
from cognito_metrics import CognitoMetrics
import json
import requests
from base64 import urlsafe_b64decode

class CognitoAuthPlugin(Component):
    implements(IAuthenticator, IRequestFilter, IRequestHandler, INavigationContributor)
    
    def __init__(self):
        super().__init__()
        self.token_validator = CognitoTokenValidator(self.env)
        self.metrics = CognitoMetrics(self.env)
        self.region = self.config.get('cognito', 'region', 'us-east-2')
        self.user_pool_id = self.config.get('cognito', 'user_pool_id', 'us-east-2_IvxzMrWwg')
        self.client_id = self.config.get('cognito', 'client_id', '5adkv019v4rcu6o87ffg46ep02')
        self.cognito_domain = self.config.get('cognito', 'domain', 'hutch-learntrac-dev-auth')
    
    # IAuthenticator methods
    def authenticate(self, req):
        """Extract user from Cognito session or Bearer token"""
        # Check if already authenticated via Bearer token
        if req.session.get('token_auth'):
            return req.authname
        
        # Check for Cognito user in session
        cognito_user = req.session.get('cognito_username')
        if cognito_user:
            self.log.info(f"Authenticated user: {cognito_user}")
            req.authname = cognito_user
            return cognito_user
        
        return None
    
    # IRequestFilter methods
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
                self.metrics.record_auth_event('bearer_auth', user_info['username'], True, 
                                             {'groups': user_info['groups']})
                
            except TracError as e:
                # For API endpoints, return 401
                if req.path_info.startswith('/api/'):
                    self._send_auth_challenge(req, str(e))
                    raise RequestDone
                # For web pages, let normal auth flow handle it
                else:
                    self.log.debug(f"Bearer token validation failed: {e}")
                    self.metrics.record_auth_event('bearer_auth', 'unknown', False, 
                                                 {'error': str(e)})
        
        return handler
    
    def post_process_request(self, req, template, data, metadata):
        return template, data, metadata
    
    # IRequestHandler methods
    def match_request(self, req):
        """Handle Cognito auth URLs"""
        return req.path_info in ('/auth/login', '/auth/callback', '/auth/logout', '/auth/refresh')
    
    def process_request(self, req):
        """Process authentication requests"""
        
        if req.path_info == '/auth/login':
            # Build Cognito hosted UI URL
            base_url = f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com"
            redirect_uri = req.abs_href('/auth/callback')
            
            auth_url = f"{base_url}/login?" + \
                      f"client_id={self.client_id}&" + \
                      f"response_type=code&" + \
                      f"scope=email+openid+profile&" + \
                      f"redirect_uri={redirect_uri}"
            
            self.log.info(f"Redirecting to Cognito: {auth_url}")
            req.redirect(auth_url)
            
        elif req.path_info == '/auth/callback':
            # Handle OAuth callback
            code = req.args.get('code')
            error = req.args.get('error')
            
            if error:
                add_warning(req, f"Authentication failed: {error}")
                req.redirect(req.href('/'))
                
            if code:
                # Exchange code for tokens
                token_url = f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/oauth2/token"
                redirect_uri = req.abs_href('/auth/callback')
                
                data = {
                    'grant_type': 'authorization_code',
                    'client_id': self.client_id,
                    'code': code,
                    'redirect_uri': redirect_uri
                }
                
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                try:
                    response = requests.post(token_url, data=data, headers=headers)
                    response.raise_for_status()
                    
                    tokens = response.json()
                    
                    # Validate and decode ID token using secure validator
                    id_token = tokens['id_token']
                    claims = self.token_validator.validate_token(id_token)
                    user_info = self.token_validator.extract_user_info(claims)
                    
                    # Store in session
                    req.session['cognito_username'] = user_info['username']
                    req.session['cognito_groups'] = user_info['groups']
                    req.session['cognito_email'] = user_info['email']
                    req.session['cognito_name'] = claims.get('name', '')
                    req.session['authenticated'] = True
                    req.session['cognito_tokens'] = {
                        'access_token': tokens.get('access_token'),
                        'id_token': id_token,
                        'refresh_token': tokens.get('refresh_token'),
                        'expires_in': tokens.get('expires_in', 3600)
                    }
                    req.session.save()
                    
                    self.log.info(f"User {user_info['username']} logged in successfully")
                    add_notice(req, f"Welcome, {req.session.get('cognito_name', user_info['username'])}!")
                    self.metrics.record_auth_event('oauth_login', user_info['username'], True, 
                                                 {'groups': user_info['groups']})
                    
                    # Redirect to main page
                    req.redirect(req.href('/'))
                    
                except Exception as e:
                    self.log.error(f"Token exchange failed: {str(e)}")
                    add_warning(req, "Authentication failed. Please try again.")
                    self.metrics.record_auth_event('oauth_login', 'unknown', False, 
                                                 {'error': str(e)})
                    req.redirect(req.href('/'))
            
            return 'Authentication callback processed', 'text/plain'
            
        elif req.path_info == '/auth/logout':
            # Clear session
            req.session.clear()
            
            # Build logout URL
            logout_uri = req.abs_href('/')
            logout_url = f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/logout?" + \
                        f"client_id={self.client_id}&" + \
                        f"logout_uri={logout_uri}"
            
            self.log.info(f"Logging out user, redirecting to: {logout_url}")
            req.redirect(logout_url)
            
        elif req.path_info == '/auth/refresh':
            # Handle token refresh
            return self._handle_token_refresh(req)
    
    def _handle_token_refresh(self, req):
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
    
    def _send_error(self, req, status_code, message):
        """Send error response"""
        req.send_response(status_code)
        req.send_header('Content-Type', 'application/json')
        req.end_headers()
        req.write(json.dumps({'error': message}).encode('utf-8'))
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'logout', 'Logout', req.href('/auth/logout'))
        else:
            yield ('metanav', 'login', 'Login', req.href('/auth/login'))