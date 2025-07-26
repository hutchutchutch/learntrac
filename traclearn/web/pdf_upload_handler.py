# -*- coding: utf-8 -*-
"""
PDF Upload Handler for Trac

Provides a bridge between the legacy Trac environment and the modern LearnTrac API
for PDF uploads and processing.
"""

from trac.core import Component, implements
from trac.web.api import IRequestHandler
from trac.web.chrome import ITemplateProvider
from trac.util.html import html
from trac.perm import IPermissionRequestor
import requests
import json
import tempfile
import os

class PDFUploadHandler(Component):
    """Handles PDF upload requests from the wiki and forwards to LearnTrac API"""
    
    implements(IRequestHandler, IPermissionRequestor)
    
    # IPermissionRequestor methods
    def get_permission_actions(self):
        """Define permissions for PDF upload"""
        return ['LEARNTRAC_UPLOAD']
    
    # IRequestHandler methods
    def match_request(self, req):
        """Match /learntrac/upload requests"""
        return req.path_info == '/learntrac/upload'
    
    def process_request(self, req):
        """Process PDF upload request"""
        
        # Check permission
        req.perm.require('LEARNTRAC_UPLOAD')
        
        if req.method == 'POST':
            # Get uploaded file
            upload = req.args.get('file')
            if not upload or not hasattr(upload, 'file'):
                req.send_response(400)
                req.send_header('Content-Type', 'application/json')
                req.end_headers()
                req.write(json.dumps({'error': 'No file uploaded'}))
                return
            
            # Get metadata
            title = req.args.get('title', 'Untitled')
            subject = req.args.get('subject', 'General')
            authors = req.args.get('authors', '').split(',') if req.args.get('authors') else []
            
            # Get API configuration
            api_endpoint = self.env.config.get('learntrac', 'api_endpoint', 
                                              'http://localhost:8000/api/trac')
            api_token = req.args.get('auth_token') or self.env.config.get('learntrac', 'api_token')
            
            try:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    upload.file.seek(0)
                    tmp_file.write(upload.file.read())
                    tmp_file.flush()
                    tmp_path = tmp_file.name
                
                # Prepare multipart upload
                files = {
                    'file': ('upload.pdf', open(tmp_path, 'rb'), 'application/pdf')
                }
                
                data = {
                    'title': title,
                    'subject': subject,
                    'authors': json.dumps(authors)
                }
                
                headers = {}
                if api_token:
                    headers['Authorization'] = 'Bearer %s' % api_token
                
                # Forward to LearnTrac API
                response = requests.post(
                    '%s/textbooks/upload' % api_endpoint,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=300  # 5 minutes for large files
                )
                
                # Clean up temp file
                os.unlink(tmp_path)
                
                # Return response
                req.send_response(response.status_code)
                req.send_header('Content-Type', 'application/json')
                req.end_headers()
                req.write(response.content)
                
            except requests.exceptions.Timeout:
                req.send_response(504)
                req.send_header('Content-Type', 'application/json')
                req.end_headers()
                req.write(json.dumps({
                    'error': 'Upload timeout - file may be too large'
                }))
                
            except Exception as e:
                self.log.error("PDF upload failed: %s", e)
                req.send_response(500)
                req.send_header('Content-Type', 'application/json')
                req.end_headers()
                req.write(json.dumps({
                    'error': 'Internal server error: %s' % str(e)
                }))
        
        else:
            # GET request - return info
            req.send_response(200)
            req.send_header('Content-Type', 'application/json')
            req.end_headers()
            req.write(json.dumps({
                'endpoint': '/learntrac/upload',
                'method': 'POST',
                'description': 'Upload PDF for processing',
                'parameters': {
                    'file': 'PDF file (required)',
                    'title': 'Textbook title (required)',
                    'subject': 'Subject area (optional)',
                    'authors': 'Comma-separated authors (optional)',
                    'auth_token': 'API authentication token (optional)'
                }
            }))