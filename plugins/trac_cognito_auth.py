# -*- coding: utf-8 -*-
from trac.core import Component, implements
from trac.config import Option
from trac.web.api import IAuthenticator, IRequestFilter, IRequestHandler
from trac.web.chrome import INavigationContributor, add_notice, add_warning
from trac.util.translation import _
import requests
import json
import logging
from base64 import urlsafe_b64decode

class CognitoAuthPlugin(Component):
    """AWS Cognito authentication for Trac"""
    
    implements(IAuthenticator, IRequestFilter, IRequestHandler, INavigationContributor)
    
    # Configuration
    user_pool_id = Option('cognito', 'user_pool_id', 'us-east-2_IvxzMrWwg')
    client_id = Option('cognito', 'client_id', '5adkv019v4rcu6o87ffg46ep02')
    cognito_domain = Option('cognito', 'domain', 'hutch-learntrac-dev-auth')
    region = Option('cognito', 'region', 'us-east-2')
    
    def __init__(self):
        self.log.info("=== CognitoAuthPlugin initialized ===")
        super().__init__()
    
    # IRequestFilter methods - intercept ALL requests
    def pre_process_request(self, req, handler):
        self.log.debug(f"Cognito pre-processing: {req.path_info}")
        
        # Skip auth for static resources and auth endpoints
        if req.path_info.startswith('/chrome/') or req.path_info.startswith('/auth/'):
            return handler
            
        # Check if user is authenticated
        if req.authname and req.authname != 'anonymous':
            return handler
            
        # Try to authenticate from session
        cognito_user = req.session.get('cognito_username')
        if cognito_user:
            req.authname = cognito_user
            self.log.info(f"Authenticated user from session: {cognito_user}")
            
        return handler
    
    def post_process_request(self, req, template, data, content_type):
        return template, data, content_type
    
    # IAuthenticator methods
    def authenticate(self, req):
        self.log.info("=== Cognito authenticate called ===")
        
        # Check session for Cognito user
        cognito_user = req.session.get('cognito_username')
        if cognito_user:
            self.log.info(f"Found Cognito user in session: {cognito_user}")
            return cognito_user
            
        return None
    
    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info in ('/auth/login', '/auth/callback', '/auth/logout')
    
    def process_request(self, req):
        self.log.info(f"=== Processing auth request: {req.path_info} ===")
        
        if req.path_info == '/auth/login':
            # Build login URL
            redirect_uri = req.abs_href('/auth/callback')
            auth_url = (f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/login?"
                       f"client_id={self.client_id}&"
                       f"response_type=code&"
                       f"scope=email+openid+profile&"
                       f"redirect_uri={redirect_uri}")
            
            self.log.info(f"Redirecting to Cognito: {auth_url}")
            req.redirect(auth_url)
            
        elif req.path_info == '/auth/callback':
            code = req.args.get('code')
            if code:
                # Exchange code for tokens
                self.log.info("Got authorization code, exchanging for tokens")
                
                token_url = f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/oauth2/token"
                redirect_uri = req.abs_href('/auth/callback')
                
                data = {
                    'grant_type': 'authorization_code',
                    'client_id': self.client_id,
                    'code': code,
                    'redirect_uri': redirect_uri
                }
                
                try:
                    response = requests.post(token_url, data=data, 
                                           headers={'Content-Type': 'application/x-www-form-urlencoded'})
                    response.raise_for_status()
                    
                    tokens = response.json()
                    id_token = tokens['id_token']
                    
                    # Decode token
                    parts = id_token.split('.')
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    user_info = json.loads(urlsafe_b64decode(payload))
                    
                    # Store in session
                    username = user_info.get('cognito:username', user_info.get('email'))
                    req.session['cognito_username'] = username
                    req.session['cognito_groups'] = user_info.get('cognito:groups', [])
                    req.session['authenticated'] = True
                    req.session.save()
                    
                    # Set authname
                    req.authname = username
                    
                    self.log.info(f"User {username} authenticated successfully")
                    add_notice(req, f"Welcome, {username}!")
                    
                    req.redirect(req.abs_href('/'))
                    
                except Exception as e:
                    self.log.error(f"Token exchange failed: {str(e)}")
                    add_warning(req, "Authentication failed")
                    req.redirect(req.abs_href('/'))
                    
        elif req.path_info == '/auth/logout':
            # Clear session
            req.session.clear()
            logout_uri = req.abs_href('/')
            logout_url = (f"https://{self.cognito_domain}.auth.{self.region}.amazoncognito.com/logout?"
                         f"client_id={self.client_id}&logout_uri={logout_uri}")
            self.log.info(f"Logging out, redirecting to: {logout_url}")
            req.redirect(logout_url)
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'logout', _('Logout'), req.href('/auth/logout'))
        else:
            yield ('metanav', 'login', _('Login'), req.href('/auth/login'))
