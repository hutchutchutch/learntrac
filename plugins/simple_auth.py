"""
Simple authentication plugin for local development
Provides basic authentication without external dependencies
"""

from trac.core import Component, implements
from trac.web.api import IAuthenticator, IRequestHandler
from trac.web.chrome import INavigationContributor
from trac.util.html import tag
from trac.util.translation import _
import hashlib
import time
import json
import os
from datetime import datetime, timedelta

class SimpleAuthPlugin(Component):
    implements(IAuthenticator, IRequestHandler, INavigationContributor)
    
    # Simple in-memory user store for development
    _users = {
        'admin': {
            'password': 'admin123',  # In production, use hashed passwords
            'name': 'Administrator',
            'email': 'admin@learntrac.local',
            'permissions': ['TRAC_ADMIN', 'LEARNING_ADMIN']
        },
        'user': {
            'password': 'user123',
            'name': 'Test User',
            'email': 'user@learntrac.local',
            'permissions': ['WIKI_VIEW', 'LEARNING_VIEW']
        },
        'instructor': {
            'password': 'instructor123',
            'name': 'Test Instructor',
            'email': 'instructor@learntrac.local',
            'permissions': ['WIKI_VIEW', 'LEARNING_VIEW', 'LEARNING_INSTRUCT']
        }
    }
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'login'
    
    def get_navigation_items(self, req):
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'login', _('logged in as %(user)s', 
                                         user=req.authname))
            yield ('metanav', 'logout', 
                   tag.a(_('Logout'), href=req.href.logout()))
        else:
            yield ('metanav', 'login',
                   tag.a(_('Login'), href=req.href.login()))
    
    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info in ('/login', '/logout')
    
    def process_request(self, req):
        if req.path_info == '/logout':
            self._do_logout(req)
        else:
            self._do_login(req)
    
    # IAuthenticator methods
    def authenticate(self, req):
        # Check for existing session
        authname = req.session.get('authname')
        if authname and authname != 'anonymous':
            # Validate session is still valid
            session_data = req.session.get('auth_data')
            if session_data:
                try:
                    data = json.loads(session_data)
                    if data.get('expires', 0) > time.time():
                        # Set user info in request
                        req.perm.username = authname
                        self._set_user_permissions(req, authname)
                        return authname
                except:
                    pass
            
            # Session expired or invalid
            req.session.clear()
        
        # Check for login form submission
        if req.method == 'POST' and 'username' in req.args:
            username = req.args.get('username', '').strip()
            password = req.args.get('password', '').strip()
            
            if self._check_password(username, password):
                # Create session
                req.session['authname'] = username
                req.session['auth_data'] = json.dumps({
                    'username': username,
                    'name': self._users[username]['name'],
                    'email': self._users[username]['email'],
                    'permissions': self._users[username]['permissions'],
                    'expires': time.time() + 3600  # 1 hour
                })
                req.session.save()
                
                # Set user info
                req.perm.username = username
                self._set_user_permissions(req, username)
                
                return username
        
        return 'anonymous'
    
    def _check_password(self, username, password):
        """Verify username and password"""
        if username in self._users:
            return self._users[username]['password'] == password
        return False
    
    def _set_user_permissions(self, req, username):
        """Set user permissions on request"""
        if username in self._users:
            user_data = self._users[username]
            # Store user data for API access
            req.environ['trac.auth.user_data'] = {
                'username': username,
                'name': user_data['name'],
                'email': user_data['email'],
                'permissions': user_data['permissions']
            }
    
    def _do_login(self, req):
        """Handle login page and form submission"""
        if req.authname and req.authname != 'anonymous':
            # Already logged in, redirect to wiki
            req.redirect(req.href.wiki())
            return
        
        data = {
            'action': req.href.login(),
            'message': None,
            'username': req.args.get('username', '')
        }
        
        if req.method == 'POST':
            username = req.args.get('username', '').strip()
            password = req.args.get('password', '').strip()
            
            if self._check_password(username, password):
                # Set session
                req.session['authname'] = username
                req.session['auth_data'] = json.dumps({
                    'username': username,
                    'name': self._users[username]['name'],
                    'email': self._users[username]['email'],
                    'permissions': self._users[username]['permissions'],
                    'expires': time.time() + 3600
                })
                req.session.save()
                
                # Redirect to original page or wiki
                redirect_url = req.args.get('referer') or req.href.wiki()
                req.redirect(redirect_url)
                return
            else:
                data['message'] = 'Invalid username or password'
        
        # Add request to data for template
        data['req'] = req
        
        # Return template info for Trac to render
        return 'login.html', data, None
    
    def _do_logout(self, req):
        """Handle logout"""
        if req.authname and req.authname != 'anonymous':
            req.session.clear()
            req.session.save()
        req.redirect(req.href.wiki())