"""
LearnTrac Authentication Handler
Provides login/logout functionality
"""

from trac.core import Component, implements
from trac.web.api import IRequestHandler, IAuthenticator
from trac.web.chrome import ITemplateProvider, add_notice, add_warning
from trac.util.html import tag
import hashlib
import time

class LearnTracAuth(Component):
    """Handle login/logout requests"""
    
    implements(IRequestHandler, IAuthenticator)
    
    # IRequestHandler methods
    def match_request(self, req):
        """Match login/logout requests"""
        return req.path_info in ('/login', '/logout')
    
    def process_request(self, req):
        """Process login/logout requests"""
        if req.path_info == '/logout':
            return self._do_logout(req)
        else:
            return self._do_login(req)
    
    def _do_login(self, req):
        """Handle login request"""
        if req.method == 'POST':
            # Get credentials
            username = req.args.get('username', '').strip()
            password = req.args.get('password', '').strip()
            
            # For demo purposes, accept any non-empty username/password
            # In production, this should validate against a real auth system
            if username and password:
                # Create session
                req.session['username'] = username
                req.session['authenticated'] = True
                req.session['auth_time'] = int(time.time())
                req.session.save()
                
                # Set auth cookie
                req.outcookie['trac_auth'] = self._generate_auth_token(username)
                req.outcookie['trac_auth']['path'] = req.href()
                req.outcookie['trac_auth']['httponly'] = True
                
                add_notice(req, 'Welcome, %s!' % username)
                
                # Redirect to original page or wiki
                redirect_url = req.session.pop('login_redirect', req.href.wiki('LearnTrac'))
                req.redirect(redirect_url)
            else:
                add_warning(req, 'Invalid username or password')
        
        # Show login form
        return 'login.html', {
            'action': req.href.login(),
            'referer': req.args.get('referer') or req.get_header('Referer') or req.href.wiki()
        }, None
    
    def _do_logout(self, req):
        """Handle logout request"""
        # Clear session
        req.session.clear()
        req.session.save()
        
        # Clear auth cookie
        req.outcookie['trac_auth'] = ''
        req.outcookie['trac_auth']['path'] = req.href()
        req.outcookie['trac_auth']['expires'] = -10000
        
        add_notice(req, 'You have been logged out')
        req.redirect(req.href.wiki())
    
    def _generate_auth_token(self, username):
        """Generate auth token"""
        # Simple token generation - should be more secure in production
        return hashlib.sha256('%s:%s' % (username, time.time())).hexdigest()
    
    # IAuthenticator methods
    def authenticate(self, req):
        """Authenticate the user"""
        # Check session
        if req.session.get('authenticated'):
            return req.session.get('username')
        
        # Check auth cookie
        auth_cookie = req.incookie.get('trac_auth')
        if auth_cookie:
            # In production, validate the auth token properly
            # For now, just check if it exists
            return req.session.get('username', 'authenticated_user')
        
        return None