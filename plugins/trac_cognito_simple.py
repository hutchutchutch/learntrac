"""
Simplified Cognito Authentication Plugin for Trac
Minimal implementation to debug the issue
"""

from trac.core import *
from trac.web.chrome import INavigationContributor
from trac.util.html import tag

class SimpleCognitoPlugin(Component):
    """Simplified Cognito authentication - just add login link"""
    
    implements(INavigationContributor)
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        """Add login/logout links"""
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'logout', 
                   tag.a('Logout (%s)' % req.authname, href='/auth/logout'))
        else:
            yield ('metanav', 'login', 
                   tag.a('Login', href='/auth/login'))