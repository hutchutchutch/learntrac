# -*- coding: utf-8 -*-
"""
TracLearn API Proxy
Routes requests from Python 2.7 Trac to Python 3.11 FastAPI service
"""

from __future__ import absolute_import, print_function, unicode_literals

import json
import requests
from urlparse import urljoin

from trac.web.api import HTTPBadGateway, HTTPError
from trac.config import Option
from trac.util.translation import _

def proxy_request(env, req):
    """Proxy request to Python 3.11 API service"""
    config = env.config
    
    # Get API configuration
    api_base_url = config.get('traclearn', 'api_base_url', 'http://localhost:8000/api/v1')
    api_timeout = config.getint('traclearn', 'api_timeout', 30)
    
    # Extract path after /traclearn/api
    api_path = req.path_info.replace('/traclearn/api', '')
    full_url = urljoin(api_base_url, api_path.lstrip('/'))
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json',
        'X-Trac-User': req.authname,
        'X-Trac-Session': req.session.sid if req.session else '',
        'X-Forwarded-For': req.remote_addr,
    }
    
    # Add authentication token if configured
    api_token = config.get('traclearn', 'api_token')
    if api_token:
        headers['Authorization'] = 'Bearer %s' % api_token
    
    # Prepare request data
    data = None
    if req.method in ('POST', 'PUT', 'PATCH'):
        if req.get_header('Content-Type') == 'application/json':
            data = req.read()
        else:
            # Convert form data to JSON
            data = json.dumps(dict(req.args))
    
    # Make request to API
    try:
        response = requests.request(
            method=req.method,
            url=full_url,
            headers=headers,
            data=data,
            params=req.args if req.method == 'GET' else None,
            timeout=api_timeout,
            verify=config.getbool('traclearn', 'api_verify_ssl', True)
        )
        
        # Send response back
        req.send_response(response.status_code)
        
        # Copy relevant headers
        for header in ['Content-Type', 'Content-Length', 'Cache-Control']:
            if header in response.headers:
                req.send_header(header, response.headers[header])
        
        # Send response body
        req.write(response.content)
        
    except requests.exceptions.Timeout:
        raise HTTPBadGateway(_('API service timeout'))
    except requests.exceptions.ConnectionError:
        raise HTTPBadGateway(_('API service unavailable'))
    except Exception as e:
        env.log.error("API proxy error: %s", e)
        raise HTTPBadGateway(_('API proxy error: %(error)s', error=str(e)))

def proxy_to_api(env, req, endpoint, method='POST', data=None):
    """Helper to proxy specific API endpoints"""
    config = env.config
    api_base_url = config.get('traclearn', 'api_base_url', 'http://localhost:8000/api/v1')
    
    url = urljoin(api_base_url, endpoint.lstrip('/'))
    
    headers = {
        'Content-Type': 'application/json',
        'X-Trac-User': req.authname,
    }
    
    api_token = config.get('traclearn', 'api_token')
    if api_token:
        headers['Authorization'] = 'Bearer %s' % api_token
    
    try:
        if data is None and method == 'POST':
            data = dict(req.args)
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        
        req.send_response(200)
        req.send_header('Content-Type', 'application/json')
        req.write(response.text)
        
    except requests.exceptions.HTTPError as e:
        req.send_response(e.response.status_code)
        req.send_header('Content-Type', 'application/json')
        req.write(json.dumps({'error': str(e)}))
    except Exception as e:
        req.send_response(500)
        req.send_header('Content-Type', 'application/json')
        req.write(json.dumps({'error': str(e)}))

class APIHealthChecker(object):
    """Check API service health"""
    
    def __init__(self, env):
        self.env = env
        self.config = env.config
    
    def check_health(self):
        """Check if API service is healthy"""
        api_base_url = self.config.get('traclearn', 'api_base_url')
        health_endpoint = urljoin(api_base_url, '/health')
        
        try:
            response = requests.get(health_endpoint, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_api_version(self):
        """Get API service version"""
        api_base_url = self.config.get('traclearn', 'api_base_url')
        version_endpoint = urljoin(api_base_url, '/version')
        
        try:
            response = requests.get(version_endpoint, timeout=5)
            if response.status_code == 200:
                return response.json().get('version', 'unknown')
        except:
            pass
        
        return 'unavailable'