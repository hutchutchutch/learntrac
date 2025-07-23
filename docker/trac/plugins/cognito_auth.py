#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Trac plugin for AWS Cognito authentication
"""

from trac.core import Component, implements
from trac.web.api import IAuthenticator, IRequestHandler
from trac.web.chrome import INavigationContributor, add_notice, add_warning
from trac.util.translation import _
from trac.util.html import tag
import urllib
import urllib2
import json
import base64
import os

class CognitoAuthPlugin(Component):
    """AWS Cognito authentication plugin for Trac"""
    
    implements(IAuthenticator, IRequestHandler, INavigationContributor)
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'login'
    
    def get_navigation_items(self, req):
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'login', _('logged in as %(user)s', user=req.authname))
            yield ('metanav', 'logout', 
                   tag.a(_('Logout'), href=req.href.logout()))
        else:
            yield ('metanav', 'login', tag.a(_('Login'), href=req.href.login()))
    
    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info in ('/login', '/logout', '/auth/callback')
    
    def process_request(self, req):
        if req.path_info == '/login':
            return self._do_login(req)
        elif req.path_info == '/logout':
            return self._do_logout(req)
        elif req.path_info == '/auth/callback':
            return self._handle_callback(req)
            
    def _do_login(self, req):
        """Redirect to Cognito login page"""
        # Get Cognito configuration from environment
        cognito_domain = os.environ.get('COGNITO_DOMAIN', 'hutch-learntrac-dev-auth')
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        redirect_uri = req.abs_href('/auth/callback')
        aws_region = os.environ.get('AWS_REGION', 'us-east-2')
        
        # Build Cognito login URL
        cognito_url = 'https://%s.auth.%s.amazoncognito.com/login' % (cognito_domain, aws_region)
        params = {
            'client_id': client_id,
            'response_type': 'code',
            'scope': 'email openid profile',
            'redirect_uri': redirect_uri
        }
        
        login_url = '%s?%s' % (cognito_url, urllib.urlencode(params))
        req.redirect(login_url)
        
    def _do_logout(self, req):
        """Handle logout"""
        if req.authname and req.authname != 'anonymous':
            # Clear session
            req.session.clear()
            req.authname = 'anonymous'
            
        # Redirect to Cognito logout
        cognito_domain = os.environ.get('COGNITO_DOMAIN', 'hutch-learntrac-dev-auth')
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        logout_uri = req.abs_href('/')
        aws_region = os.environ.get('AWS_REGION', 'us-east-2')
        
        cognito_logout_url = 'https://%s.auth.%s.amazoncognito.com/logout' % (cognito_domain, aws_region)
        params = {
            'client_id': client_id,
            'logout_uri': logout_uri
        }
        
        logout_url = '%s?%s' % (cognito_logout_url, urllib.urlencode(params))
        req.redirect(logout_url)
        
    def _handle_callback(self, req):
        """Handle OAuth callback from Cognito"""
        code = req.args.get('code')
        if not code:
            add_warning(req, _('No authorization code received'))
            req.redirect(req.href('/'))
            
        # Exchange code for tokens
        try:
            tokens = self._exchange_code_for_tokens(req, code)
            
            # Decode ID token to get user info
            id_token = tokens.get('id_token')
            if id_token:
                user_info = self._decode_id_token(id_token)
                
                # Set authentication
                req.authname = user_info.get('email', 'unknown')
                req.session['cognito_user'] = user_info
                req.session['cognito_groups'] = user_info.get('cognito:groups', [])
                req.session['trac_permissions'] = user_info.get('trac_permissions', '').split(',')
                req.session.save()
                
                add_notice(req, _('Successfully logged in as %(user)s', user=req.authname))
                
                # Redirect to original page or home
                redirect_url = req.session.get('redirect_after_login', req.href('/'))
                req.redirect(redirect_url)
            else:
                add_warning(req, _('No ID token received'))
                req.redirect(req.href('/'))
                
        except Exception as e:
            self.log.error('Cognito authentication failed: %s', e)
            add_warning(req, _('Authentication failed: %(error)s', error=str(e)))
            req.redirect(req.href('/'))
            
    def _exchange_code_for_tokens(self, req, code):
        """Exchange authorization code for tokens"""
        cognito_domain = os.environ.get('COGNITO_DOMAIN', 'hutch-learntrac-dev-auth')
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        redirect_uri = req.abs_href('/auth/callback')
        aws_region = os.environ.get('AWS_REGION', 'us-east-2')
        
        token_url = 'https://%s.auth.%s.amazoncognito.com/oauth2/token' % (cognito_domain, aws_region)
        
        data = urllib.urlencode({
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'code': code,
            'redirect_uri': redirect_uri
        })
        
        req = urllib2.Request(token_url, data)
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        response = urllib2.urlopen(req)
        return json.loads(response.read())
        
    def _decode_id_token(self, id_token):
        """Decode JWT ID token (simplified - in production use proper JWT library)"""
        # Split token
        parts = id_token.split('.')
        if len(parts) != 3:
            raise ValueError('Invalid ID token format')
            
        # Decode payload (skip signature verification for now)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding
            
        decoded = base64.b64decode(payload)
        return json.loads(decoded)
        
    # IAuthenticator methods
    def authenticate(self, req):
        """Check if user is authenticated via Cognito"""
        if 'cognito_user' in req.session:
            return req.session.get('authname', 'anonymous')
        return None