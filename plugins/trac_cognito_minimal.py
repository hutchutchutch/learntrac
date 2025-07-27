"""Minimal Cognito plugin that works"""
from trac.core import *
from trac.web.api import IAuthenticator, IRequestHandler
from trac.web.chrome import INavigationContributor, add_notice, add_warning
from trac.util.html import tag
import urllib

class CognitoMinimalPlugin(Component):
    implements(IAuthenticator, IRequestHandler, INavigationContributor)
    
    def __init__(self):
        Component.__init__(self)
        self.log.info("CognitoMinimalPlugin initialized")
    
    # IAuthenticator - just check session
    def authenticate(self, req):
        return req.session.get('cognito_user')
    
    # IRequestHandler - handle auth URLs carefully
    def match_request(self, req):
        self.log.info("CognitoMinimal: match_request called for path: %s", req.path_info)
        return req.path_info in ('/auth/login', '/auth/callback', '/auth/logout')
    
    def process_request(self, req):
        if req.path_info == '/auth/login':
            # Simple redirect to Cognito
            cognito_url = "https://hutch-learntrac-dev-auth.auth.us-east-2.amazoncognito.com/login"
            params = {
                'client_id': '38r71epsido0doobd9370mqd8u',
                'response_type': 'code',
                'scope': 'email openid profile',
                'redirect_uri': req.abs_href('/auth/callback')
            }
            full_url = "%s?%s" % (cognito_url, urllib.urlencode(params))
            req.redirect(full_url)
            
        elif req.path_info == '/auth/callback':
            # For now, just simulate success
            code = req.args.get('code')
            if code:
                # Simulate successful auth
                req.session['cognito_user'] = 'test@example.com'
                req.session.save()
                add_notice(req, "Login successful!")
                req.redirect(req.href.wiki('LearnTrac'))
            else:
                add_warning(req, "Login failed")
                req.redirect(req.href.wiki())
                
        elif req.path_info == '/auth/logout':
            req.session.clear()
            req.session.save()
            req.redirect(req.href.wiki())
    
    # INavigationContributor - add login/logout links
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        self.log.info("CognitoMinimal: get_navigation_items called, authname: %s", getattr(req, 'authname', 'None'))
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'logout', 
                   tag.a('Logout (%s)' % req.authname, href='/auth/logout'))
        else:
            yield ('metanav', 'login', 
                   tag.a('Login', href='/auth/login'))