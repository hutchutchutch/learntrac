"""
Simplified Cognito Authentication Plugin for Trac - Debug Version
Minimal implementation to isolate response handling issue
"""

from trac.core import *
from trac.web.api import IAuthenticator
from trac.util.html import tag
import json
import urllib2
import traceback

class SimpleCognitoAuthPlugin(Component):
    """Simplified Cognito authentication for debugging"""
    
    implements(IAuthenticator)
    
    def __init__(self):
        Component.__init__(self)
        self.log.info("SimpleCognitoAuthPlugin initialized")
        # Test that we can access config
        test_config = self.config.get('cognito', 'region', 'default')
        self.log.info("Test config access - region: %s", test_config)
    
    def authenticate(self, req):
        """Minimal authenticate implementation"""
        self.log.info("SimpleCognitoAuthPlugin.authenticate called")
        self.log.info("Request path: %s", getattr(req, 'path_info', 'unknown'))
        
        # Always return None (anonymous) for now
        return None