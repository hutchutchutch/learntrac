"""
Minimal plugin to test navigation contribution only
"""

from trac.core import *
from trac.web.chrome import INavigationContributor
from trac.util.html import tag

class NavigationTestPlugin(Component):
    """Test navigation links without request handling"""
    
    implements(INavigationContributor)
    
    def __init__(self):
        Component.__init__(self)
        self.log.info("NavigationTestPlugin initialized")
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        """Add test navigation link"""
        self.log.info("NavigationTestPlugin.get_navigation_items called")
        # Just add a simple external link
        yield ('metanav', 'test-link', 
               tag.a('Test Link', href='https://example.com', target='_blank'))