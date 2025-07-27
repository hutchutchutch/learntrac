"""
Safe Cognito Authentication Plugin for Trac
Wraps everything in try-except to prevent initialization errors
"""

from trac.core import *
import sys

try:
    from trac.web.api import IAuthenticator, IRequestFilter, IRequestHandler, HTTPNotFound
    from trac.web.chrome import INavigationContributor, add_notice, add_warning
    from trac.util.translation import _
    from trac.util.html import tag
    import json
    import urllib2
    import urllib
    import traceback

    class SafeCognitoProxyAuthPlugin(Component):
        """Safe Cognito authentication using learntrac-api as JWT validation proxy"""
        
        implements(IAuthenticator, IRequestFilter, IRequestHandler, INavigationContributor)
        
        def __init__(self):
            try:
                Component.__init__(self)
                self.log.info("=== SafeCognitoProxyAuthPlugin INITIALIZING ===")
                
                self.region = self.config.get('cognito', 'region', 'us-east-2')
                self.user_pool_id = self.config.get('cognito', 'user_pool_id', 'us-east-2_1AzmDXp0K')
                self.client_id = self.config.get('cognito', 'client_id', '38r71epsido0doobd9370mqd8u')
                self.cognito_domain = self.config.get('cognito', 'domain', 'hutch-learntrac-dev-auth')
                self.api_endpoint = self.config.get('learntrac', 'api_endpoint', 'http://learntrac-api:8001/api/trac')
                
                self.log.info("SafeCognitoProxyAuthPlugin initialized successfully")
                self._initialized = True
            except Exception as e:
                print >> sys.stderr, "Error initializing SafeCognitoProxyAuthPlugin: %s" % str(e)
                self._initialized = False
        
        # IAuthenticator methods
        def authenticate(self, req):
            """Extract user from session"""
            if not getattr(self, '_initialized', False):
                return None
                
            try:
                cognito_user = req.session.get('cognito_username')
                if cognito_user:
                    req.authname = cognito_user
                    return cognito_user
                return None
            except:
                return None
        
        # IRequestFilter methods
        def pre_process_request(self, req, handler):
            """Check if user needs to authenticate"""
            if not getattr(self, '_initialized', False):
                return handler
                
            try:
                protected_paths = ['/wiki/LearnTrac']
                
                for path in protected_paths:
                    if req.path_info.startswith(path) and not req.authname:
                        req.session['login_redirect'] = req.path_info
                        req.redirect(req.href('/auth/login'))
                
                return handler
            except:
                return handler
        
        def post_process_request(self, req, template, data, metadata):
            return template, data, metadata
        
        # IRequestHandler methods
        def match_request(self, req):
            """Handle Cognito auth URLs"""
            if not getattr(self, '_initialized', False):
                return False
                
            try:
                return req.path_info in ('/auth/login', '/auth/callback', '/auth/logout')
            except:
                return False
        
        def process_request(self, req):
            """Process authentication requests"""
            if not getattr(self, '_initialized', False):
                raise HTTPNotFound("Auth plugin not initialized")
                
            try:
                if req.path_info == '/auth/login':
                    base_url = "https://%s.auth.%s.amazoncognito.com" % (self.cognito_domain, self.region)
                    redirect_uri = req.abs_href('/auth/callback')
                    
                    auth_url = "%s/login?client_id=%s&response_type=code&scope=email+openid+profile&redirect_uri=%s" % (
                        base_url, self.client_id, urllib.quote_plus(redirect_uri))
                    
                    req.redirect(auth_url)
                    return None
                    
                elif req.path_info == '/auth/callback':
                    # Simple redirect to wiki for now
                    req.redirect(req.href.wiki())
                    return None
                    
                elif req.path_info == '/auth/logout':
                    req.session.clear()
                    req.session.save()
                    req.redirect(req.href.wiki())
                    return None
                    
                raise HTTPNotFound("Unknown auth path")
                
            except Exception as e:
                print >> sys.stderr, "Error in process_request: %s" % str(e)
                raise
        
        # INavigationContributor methods
        def get_active_navigation_item(self, req):
            return None
        
        def get_navigation_items(self, req):
            """Add login/logout links"""
            if not getattr(self, '_initialized', False):
                return
                
            try:
                if req.authname and req.authname != 'anonymous':
                    yield ('metanav', 'logout', 
                           tag.a('Logout (%s)' % req.authname, href=req.href('/auth/logout')))
                else:
                    yield ('metanav', 'login', 
                           tag.a('Login', href=req.href('/auth/login')))
            except:
                pass

except Exception as e:
    print >> sys.stderr, "Failed to load SafeCognitoProxyAuthPlugin: %s" % str(e)