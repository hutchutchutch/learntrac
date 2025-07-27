# -*- coding: utf-8 -*-
"""
Authentication Proxy for Trac
Integrates with external auth service
"""

from trac.core import Component, implements
from trac.web.api import IAuthenticator, IRequestFilter, IRequestHandler
from trac.web.chrome import INavigationContributor, add_warning
from trac.config import Option
from trac.util.html import tag
from trac.util.translation import _

try:
    # Python 2
    import urllib2
    import json
    from urllib import urlencode
except ImportError:
    # Python 3
    import urllib.request as urllib2
    import json
    from urllib.parse import urlencode


class AuthProxyPlugin(Component):
    """Authentication proxy plugin that checks with auth service"""
    
    implements(IAuthenticator, IRequestFilter, IRequestHandler, INavigationContributor)
    
    # Configuration
    auth_service_url = Option('authproxy', 'service_url', 'http://learning-service:8001',
                            doc='URL of the learning API service with auth endpoints')
    
    # IAuthenticator methods
    def authenticate(self, req):
        """Check authentication with auth service"""
        # Get session cookie
        auth_session = req.get_cookie('auth_session')
        if not auth_session:
            return None
        
        # Verify with auth service
        try:
            verify_url = '%s/auth/verify' % self.auth_service_url
            
            # Create request with cookie
            request = urllib2.Request(verify_url)
            request.add_header('Cookie', 'auth_session=%s' % auth_session)
            
            response = urllib2.urlopen(request)
            data = json.loads(response.read())
            
            if data.get('authenticated'):
                return data.get('user')
                
        except Exception as e:
            self.log.error("Auth verification failed: %s", e)
        
        return None
    
    # IRequestHandler methods
    def match_request(self, req):
        """Match login/logout requests"""
        return req.path_info in ('/login', '/logout')
    
    def process_request(self, req):
        """Handle login/logout requests"""
        if req.path_info == '/login':
            # Redirect to auth service
            redirect_param = req.args.get('redirect', '/trac/wiki')
            login_url = '%s/auth/login?redirect=%s' % (self.auth_service_url, redirect_param)
            req.redirect(login_url)
            
        elif req.path_info == '/logout':
            # Redirect to auth service logout
            logout_url = '%s/auth/logout' % self.auth_service_url
            req.redirect(logout_url)
    
    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        """Check authentication before processing requests"""
        # Skip auth check for login/logout paths
        if req.path_info in ('/login', '/logout'):
            return handler
        
        # Skip auth check for static resources
        if req.path_info.startswith('/chrome/'):
            return handler
        
        # Check if user is authenticated
        if not req.authname or req.authname == 'anonymous':
            # Redirect to login
            redirect_url = req.href.login(redirect=req.path_info)
            req.redirect(redirect_url)
        
        return handler
    
    def post_process_request(self, req, template, data, content_type):
        """Post-process request"""
        return template, data, content_type
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        """Add login/logout links"""
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'login', _('logged in as %(user)s', user=req.authname))
            yield ('metanav', 'logout', 
                   tag.a(_('Logout'), href=req.href.logout()))
        else:
            yield ('metanav', 'login',
                   tag.a(_('Login'), href=req.href.login()))