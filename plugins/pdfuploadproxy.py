"""
PDF Upload Proxy for LearnTrac
Proxies upload requests from browser to learntrac-api container
"""

from trac.core import Component, implements
from trac.web.api import IRequestHandler
from trac.web.chrome import ITemplateProvider
import urllib2
import json

class PDFUploadProxy(Component):
    """Proxy handler for PDF uploads to learntrac-api"""
    
    implements(IRequestHandler)
    
    # IRequestHandler methods
    def match_request(self, req):
        """Match /learntrac/upload requests"""
        return req.path_info == '/learntrac/upload'
    
    def process_request(self, req):
        """Proxy upload request to learntrac-api container"""
        
        if req.method != 'POST':
            req.send_response(405)
            req.send_header('Content-Type', 'text/plain')
            req.end_headers()
            req.write('Method not allowed')
            return
        
        # Read uploaded file from request
        upload = req.args.get('file')
        if not upload or not hasattr(upload, 'file'):
            req.send_response(400)
            req.send_header('Content-Type', 'application/json')
            req.end_headers()
            req.write(json.dumps({'error': 'No file uploaded'}))
            return
        
        # Forward to learntrac-api container
        try:
            # Create multipart form data
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            body = []
            
            # Add file part
            body.append('--' + boundary)
            body.append('Content-Disposition: form-data; name="file"; filename="%s"' % upload.filename)
            body.append('Content-Type: application/pdf')
            body.append('')
            body.append(upload.file.read())
            body.append('--' + boundary + '--')
            body.append('')
            
            body_bytes = '\r\n'.join(body)
            
            # Make request to internal API
            request = urllib2.Request(
                'http://learntrac-api:8001/api/trac/textbooks/upload-dev',
                data=body_bytes,
                headers={
                    'Content-Type': 'multipart/form-data; boundary=' + boundary,
                    'Content-Length': str(len(body_bytes)),
                    'X-Trac-Session': req.session.sid if hasattr(req.session, 'sid') else 'anonymous'
                }
            )
            
            response = urllib2.urlopen(request)
            result = response.read()
            
            # Return response to browser
            req.send_response(200)
            req.send_header('Content-Type', 'application/json')
            req.send_header('Access-Control-Allow-Origin', '*')
            req.end_headers()
            req.write(result)
            
        except urllib2.HTTPError as e:
            req.send_response(e.code)
            req.send_header('Content-Type', 'application/json')
            req.end_headers()
            req.write(json.dumps({'error': 'Upload failed: ' + str(e)}))
            
        except Exception as e:
            req.send_response(500)
            req.send_header('Content-Type', 'application/json')
            req.end_headers()
            req.write(json.dumps({'error': 'Internal error: ' + str(e)}))