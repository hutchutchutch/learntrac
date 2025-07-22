from trac.core import Component, implements
from trac.web.api import IAuthenticator, IRequestHandler
from trac.web.chrome import INavigationContributor, add_notice, add_warning
from trac.config import Option
import requests
import json
from base64 import b64decode, urlsafe_b64decode
import logging

class CognitoAuthPlugin(Component):
    """AWS Cognito authentication for Trac"""
    
    implements(IAuthenticator, IRequestHandler, INavigationContributor)
    
    # Configuration options
    user_pool_id = Option('cognito', 'user_pool_id', 'us-east-2_IvxzMrWwg',
                         doc="Cognito User Pool ID")
    client_id = Option('cognito', 'client_id', '5adkv019v4rcu6o87ffg46ep02',
                      doc="Cognito App Client ID")
    cognito_domain = Option('cognito', 'domain', 'hutch-learntrac-dev-auth',
                           doc="Cognito Domain")
    region = Option('cognito', 'region', 'us-east-2',
                   doc="AWS Region")
    
    def __init__(self):
        self.log = logging.getLogger(__name__)
    
    # IAuthenticator methods
    def authenticate(self, req):
        """Extract user from Cognito session"""
        
        # Check for Cognito user in session
        cognito_user = req.session.get('cognito_username')
        if cognito_user:
            self.log.info(f"Authenticated user: {cognito_user}")
            
            # Set up permissions based on groups
            groups = req.session.get('cognito_groups', [])
            req.session['name'] = req.session.get('cognito_name', cognito_user)
            req.session['email'] = req.session.get('cognito_email', '')
            
            # Store authname for Trac
            req.authname = cognito_user
            
            return cognito_user
        
        return None
    
    # IRequestHandler methods
    def match_request(self, req):
        """Handle Cognito auth URLs"""
        return req.path_info in ('/auth/login', '/auth/callback', '/auth/logout')
    
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
                    
                    # Decode ID token to get user info
                    id_token = tokens['id_token']
                    # Split token and decode payload
                    parts = id_token.split('.')
                    payload = parts[1]
                    # Add padding if needed
                    payload += '=' * (4 - len(payload) % 4)
                    
                    user_info = json.loads(urlsafe_b64decode(payload))
                    
                    # Store in session
                    req.session['cognito_username'] = user_info.get('cognito:username', user_info.get('email'))
                    req.session['cognito_groups'] = user_info.get('cognito:groups', [])
                    req.session['cognito_email'] = user_info.get('email', '')
                    req.session['cognito_name'] = user_info.get('name', '')
                    req.session['authenticated'] = True
                    req.session.save()
                    
                    self.log.info(f"User {req.session['cognito_username']} logged in successfully")
                    add_notice(req, f"Welcome, {req.session.get('cognito_name', req.session['cognito_username'])}!")
                    
                    # Redirect to main page
                    req.redirect(req.href('/'))
                    
                except Exception as e:
                    self.log.error(f"Token exchange failed: {str(e)}")
                    add_warning(req, "Authentication failed. Please try again.")
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
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'logout', 'Logout', req.href('/auth/logout'))
        else:
            yield ('metanav', 'login', 'Login', req.href('/auth/login'))