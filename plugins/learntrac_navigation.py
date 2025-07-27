"""
LearnTrac Navigation Component
Adds login/logout links to navigation
"""

from trac.core import Component, implements
from trac.web.api import IRequestFilter
from trac.web.chrome import INavigationContributor, add_ctxtnav
from trac.util.html import tag

class LearnTracNavigation(Component):
    """Add login/logout links to Trac navigation"""
    
    implements(INavigationContributor, IRequestFilter)
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        """Add login/logout to metanav"""
        if req.authname and req.authname != 'anonymous':
            # User is logged in
            yield ('metanav', 'logout', 
                   tag.a('Logout (%s)' % req.authname, 
                         href=req.href.logout(),
                         title='Logout from LearnTrac'))
        else:
            # User is not logged in
            yield ('metanav', 'login', 
                   tag.a('Login', 
                         href=req.href.login(),
                         title='Login to LearnTrac'))
    
    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        """Redirect to login if accessing protected pages"""
        # Check if user is accessing LearnTrac features
        if req.path_info.startswith('/wiki/LearnTrac') and req.authname == 'anonymous':
            # Store the original URL to redirect back after login
            req.session['login_redirect'] = req.path_info
            req.redirect(req.href.login())
        return handler
    
    def post_process_request(self, req, template, data, metadata):
        """Process after request"""
        # Check if user just logged in and has a redirect URL
        if req.authname != 'anonymous' and 'login_redirect' in req.session:
            redirect_url = req.session.pop('login_redirect')
            req.redirect(req.href(redirect_url))
        return template, data, metadata