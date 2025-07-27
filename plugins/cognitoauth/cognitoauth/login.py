# -*- coding: utf-8 -*-
"""
Cognito Login Module for Trac
Handles login/logout redirects to AWS Cognito
"""

from trac.core import Component, implements
from trac.web.api import IRequestHandler, IRequestFilter
from trac.web.chrome import INavigationContributor, add_notice, add_warning
from trac.config import Option
from trac.util import Ranges
from trac.util.translation import _
from trac.util.html import tag

try:
    # Python 2
    from urllib import urlencode
    from urlparse import urljoin
except ImportError:
    # Python 3
    from urllib.parse import urlencode, urljoin


class CognitoLoginModule(Component):
    """Cognito login module that replaces Trac's default login"""
    
    implements(IRequestHandler, IRequestFilter, INavigationContributor)
    
    # Configuration
    cognito_region = Option('cognito', 'region', 'us-east-2',
                           doc='AWS region for Cognito')
    cognito_domain = Option('cognito', 'domain', '',
                           doc='Cognito domain (without .auth.<region>.amazoncognito.com)')
    cognito_client_id = Option('cognito', 'client_id', '',
                              doc='Cognito App Client ID')
    login_redirect_path = Option('cognito', 'login_redirect_path', '/trac/wiki',
                                doc='Path to redirect after successful login')
    
    # IRequestHandler methods
    def match_request(self, req):
        """Match login/logout and auth callback requests"""
        return req.path_info in ('/login', '/logout', '/auth/callback')
    
    def process_request(self, req):
        """Process login, logout, and callback requests"""
        
        if req.path_info == '/login':
            return self._handle_login(req)
        elif req.path_info == '/logout':
            return self._handle_logout(req)
        elif req.path_info == '/auth/callback':
            return self._handle_callback(req)
    
    def _handle_login(self, req):
        """Redirect to Cognito login page"""
        try:
            # Validate configuration
            if not self.cognito_domain or not self.cognito_client_id:
                add_warning(req, _('Cognito authentication is not configured. Please contact administrator.'))
                req.redirect(req.href.wiki())
                return
            
            # Build Cognito auth URL
            cognito_base = 'https://%s.auth.%s.amazoncognito.com' % (
                self.cognito_domain, self.cognito_region)
            
            # Build redirect URI
            redirect_uri = req.abs_href('auth/callback')
            
            # Build authorization URL
            params = {
                'response_type': 'code',
                'client_id': self.cognito_client_id,
                'redirect_uri': redirect_uri,
                'scope': 'openid email profile',
                'state': req.args.get('redirect', self.login_redirect_path)
            }
            
            auth_url = '%s/login?%s' % (cognito_base, urlencode(params))
            
            # Redirect to Cognito
            req.redirect(auth_url)
        except Exception as e:
            self.log.error("Login error: %s", e)
            add_warning(req, _('Login failed: %s' % str(e)))
            req.redirect(req.href.wiki())
    
    def _handle_logout(self, req):
        """Handle logout and redirect to Cognito logout"""
        # Clear cookies
        req.send_cookie('cognito_id_token', '', max_age=0, path='/')
        req.send_cookie('cognito_access_token', '', max_age=0, path='/')
        req.send_cookie('trac_auth', '', max_age=0, path='/')
        
        # Build Cognito logout URL
        cognito_base = 'https://%s.auth.%s.amazoncognito.com' % (
            self.cognito_domain, self.cognito_region)
        
        logout_uri = req.abs_href('')
        
        params = {
            'client_id': self.cognito_client_id,
            'logout_uri': logout_uri
        }
        
        logout_url = '%s/logout?%s' % (cognito_base, urlencode(params))
        
        # Redirect to Cognito logout
        req.redirect(logout_url)
    
    def _handle_callback(self, req):
        """Handle OAuth callback from Cognito"""
        code = req.args.get('code')
        state = req.args.get('state', self.login_redirect_path)
        error = req.args.get('error')
        
        if error:
            add_warning(req, _('Login failed: %s' % req.args.get('error_description', error)))
            req.redirect(req.href.wiki())
            return
        
        if not code:
            add_warning(req, _('Login failed: No authorization code received'))
            req.redirect(req.href.wiki())
            return
        
        # The CognitoAuthenticator will handle the code exchange
        # when it processes this request
        
        # Set a temporary session marker
        req.send_cookie('cognito_auth_pending', '1', max_age=60, path='/')
        
        # Redirect to the original destination or wiki
        req.redirect(req.href(state))
    
    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        """Check authentication before processing requests"""
        # Skip auth check for login/logout/callback paths
        if req.path_info in ('/login', '/logout', '/auth/callback'):
            return handler
        
        # Skip auth check for static resources
        if req.path_info.startswith('/chrome/'):
            return handler
        
        # Check if user is authenticated
        if not req.authname or req.authname == 'anonymous':
            # Check for pending auth
            if req.get_cookie('cognito_auth_pending'):
                req.send_cookie('cognito_auth_pending', '', max_age=0, path='/')
                return handler
            
            # Redirect to login
            redirect_url = req.href.login(redirect=req.path_info)
            req.redirect(redirect_url)
        
        return handler
    
    def post_process_request(self, req, template, data, content_type):
        """Post-process to ensure user info is available"""
        if data and req.authname and req.authname != 'anonymous':
            # Add user info to template data
            data['cognito_user'] = req.authname
        return template, data, content_type
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        """Replace default login/logout links"""
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'login', _('logged in as %(user)s', user=req.authname))
            yield ('metanav', 'logout', 
                   tag.a(_('Logout'), href=req.href.logout()))
        else:
            yield ('metanav', 'login',
                   tag.a(_('Login'), href=req.href.login()))