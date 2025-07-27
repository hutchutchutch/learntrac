"""
Test plugin to debug response handling in Trac
"""

from trac.core import *
from trac.web.api import IRequestHandler
from trac.web.chrome import Chrome

class TestResponsePlugin(Component):
    """Test response handling"""
    
    implements(IRequestHandler)
    
    def match_request(self, req):
        """Match /test/* URLs"""
        return req.path_info.startswith('/test/')
    
    def process_request(self, req):
        """Process test requests"""
        self.log.info("TestResponsePlugin processing: %s", req.path_info)
        
        if req.path_info == '/test/simple':
            # Simple text response
            req.send_response(200)
            req.send_header('Content-Type', 'text/plain')
            req.end_headers()
            req.write('Simple test response')
            
        elif req.path_info == '/test/html':
            # HTML response using Chrome
            data = {'message': 'Test HTML response'}
            return 'test_response.html', data, None
            
        elif req.path_info == '/test/redirect':
            # Test redirect
            req.redirect(req.href.wiki())
            
        elif req.path_info == '/test/json':
            # JSON response
            import json
            req.send_response(200)
            req.send_header('Content-Type', 'application/json')
            req.end_headers()
            req.write(json.dumps({'status': 'ok', 'message': 'JSON test'}))
            
        else:
            # 404 response
            req.send_error(404, 'Test page not found')