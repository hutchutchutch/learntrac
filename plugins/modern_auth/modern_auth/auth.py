"""
Modern Authentication Handler for Trac
Python 2.7 Compatible

Replaces Trac's default authentication with a modern, secure system.
"""

import hashlib
import hmac
import time
import base64
import json
import uuid
import os
from trac.core import Component, implements
from trac.web.api import IAuthenticator, IRequestHandler
from trac.web.chrome import INavigationContributor, add_warning, add_notice
from trac.util.text import exception_to_unicode
from trac.config import Option

from .session_manager import ModernSessionManager
from .security import SecurityUtils
from .rate_limiter import RateLimiter


class ModernAuthenticator(Component):
    """
    Modern authentication system for Trac
    
    Provides secure session tokens, CSRF protection, and rate limiting
    while maintaining Python 2.7 compatibility.
    """
    
    implements(IAuthenticator, IRequestHandler, INavigationContributor)
    
    # Configuration options
    secret_key = Option('modern_auth', 'secret_key', '', 
                       doc='Secret key for token signing (required)')
    
    redis_host = Option('modern_auth', 'redis_host', 'localhost',
                       doc='Redis server host')
    
    redis_port = Option('modern_auth', 'redis_port', '6379',
                       doc='Redis server port')
    
    session_timeout = Option('modern_auth', 'session_timeout', '3600',
                           doc='Session timeout in seconds (default: 1 hour)')
    
    max_login_attempts = Option('modern_auth', 'max_login_attempts', '5',
                              doc='Maximum login attempts per IP')
    
    rate_limit_window = Option('modern_auth', 'rate_limit_window', '900',
                             doc='Rate limit window in seconds (default: 15 minutes)')
    
    def __init__(self):
        # Initialize components
        self.session_manager = ModernSessionManager(self.env, self)
        self.security_utils = SecurityUtils()
        self.rate_limiter = RateLimiter(
            redis_host=self.redis_host,
            redis_port=int(self.redis_port),
            max_attempts=int(self.max_login_attempts),
            window_seconds=int(self.rate_limit_window)
        )
        
        # Validate configuration
        if not self.secret_key:
            self.env.log.error("modern_auth.secret_key is required but not configured")
    
    # IAuthenticator methods
    
    def authenticate(self, req):
        """Authenticate request using modern session tokens"""
        try:
            # Skip authentication for login/logout pages
            if req.path_info.startswith('/login') or req.path_info.startswith('/logout'):
                return None
            
            # Check for session token in cookies
            session_token = req.incookie.get('trac_auth_token')
            if not session_token:
                return None
            
            # Validate session token
            user_info = self.session_manager.validate_session_token(session_token.value)
            if not user_info:
                # Invalid token - clear cookie
                self._clear_auth_cookie(req)
                return None
            
            # Update last activity
            self.session_manager.update_session_activity(session_token.value)
            
            # Store user info in request for later use
            req.session_user_info = user_info
            
            return user_info['username']
            
        except Exception as e:
            self.env.log.error("Authentication error: %s", exception_to_unicode(e))
            return None
    
    # IRequestHandler methods
    
    def match_request(self, req):
        """Handle login/logout requests"""
        return req.path_info in ['/login', '/logout', '/auth/csrf']
    
    def process_request(self, req):
        """Process authentication requests"""
        if req.path_info == '/login':
            return self._handle_login(req)
        elif req.path_info == '/logout':
            return self._handle_logout(req)
        elif req.path_info == '/auth/csrf':
            return self._handle_csrf_token(req)
        
        return 'login.html', {}, None
    
    def _handle_login(self, req):
        """Handle login requests"""
        if req.method == 'POST':
            return self._process_login(req)
        else:
            # Show login form
            csrf_token = self.security_utils.generate_csrf_token()
            req.session['csrf_token'] = csrf_token
            
            return 'login.html', {
                'csrf_token': csrf_token,
                'login_url': req.href.login(),
                'referer': req.args.get('referer', req.href())
            }, None
    
    def _process_login(self, req):
        """Process login form submission"""
        username = req.args.get('username', '').strip()
        password = req.args.get('password', '')
        csrf_token = req.args.get('csrf_token', '')
        referer = req.args.get('referer', req.href())
        
        # Validate CSRF token
        expected_csrf = req.session.get('csrf_token')
        if not csrf_token or csrf_token != expected_csrf:
            add_warning(req, 'Invalid CSRF token. Please try again.')
            return self._redirect_to_login(req, referer)
        
        # Clear CSRF token
        req.session.pop('csrf_token', None)
        
        # Validate input
        if not username or not password:
            add_warning(req, 'Username and password are required.')
            return self._redirect_to_login(req, referer)
        
        # Check rate limiting
        client_ip = req.environ.get('REMOTE_ADDR', 'unknown')
        if self.rate_limiter.is_rate_limited(client_ip):
            add_warning(req, 'Too many login attempts. Please try again later.')
            return self._redirect_to_login(req, referer)
        
        try:
            # Authenticate user
            session_token = self.session_manager.authenticate_user(
                username, password, client_ip
            )
            
            if session_token:
                # Set secure authentication cookie
                self._set_auth_cookie(req, session_token)
                
                # Log successful login
                self.env.log.info("User '%s' logged in from %s", username, client_ip)
                
                # Reset rate limiting for this IP
                self.rate_limiter.reset_attempts(client_ip)
                
                # Redirect to original destination
                req.redirect(referer)
            else:
                # Authentication failed
                self.rate_limiter.record_failed_attempt(client_ip)
                add_warning(req, 'Invalid username or password.')
                return self._redirect_to_login(req, referer)
                
        except Exception as e:
            self.env.log.error("Login error for user '%s': %s", username, exception_to_unicode(e))
            add_warning(req, 'Login failed. Please try again.')
            return self._redirect_to_login(req, referer)
    
    def _handle_logout(self, req):
        """Handle logout requests"""
        # Get session token
        session_token = req.incookie.get('trac_auth_token')
        if session_token:
            # Invalidate session
            self.session_manager.invalidate_session(session_token.value)
        
        # Clear authentication cookie
        self._clear_auth_cookie(req)
        
        # Log logout
        username = getattr(req, 'authname', 'anonymous')
        if username != 'anonymous':
            self.env.log.info("User '%s' logged out", username)
        
        add_notice(req, 'You have been logged out.')
        req.redirect(req.href())
    
    def _handle_csrf_token(self, req):
        """Handle CSRF token requests for AJAX"""
        if req.method == 'GET':
            # Generate new CSRF token
            csrf_token = self.security_utils.generate_csrf_token()
            req.session['csrf_token'] = csrf_token
            
            req.send_response(200)
            req.send_header('Content-Type', 'application/json')
            req.end_headers()
            req.write(json.dumps({'csrf_token': csrf_token}))
        else:
            req.send_error(405, 'Method not allowed')
    
    # INavigationContributor methods
    
    def get_active_navigation_item(self, req):
        return 'login'
    
    def get_navigation_items(self, req):
        if req.authname == 'anonymous':
            yield ('metanav', 'login', 
                   '<a href="%s">Login</a>' % req.href.login())
        else:
            yield ('metanav', 'logout',
                   '<a href="%s">Logout (%s)</a>' % (req.href.logout(), req.authname))
    
    # Helper methods
    
    def _set_auth_cookie(self, req, session_token):
        """Set secure authentication cookie"""
        # Use secure cookie settings
        req.outcookie['trac_auth_token'] = session_token
        req.outcookie['trac_auth_token']['path'] = req.href()
        req.outcookie['trac_auth_token']['httponly'] = True
        
        # Set secure flag for HTTPS
        if req.scheme == 'https':
            req.outcookie['trac_auth_token']['secure'] = True
        
        # Set SameSite for CSRF protection (if supported)
        try:
            req.outcookie['trac_auth_token']['samesite'] = 'Lax'
        except:
            # SameSite not supported in older Python versions
            pass
        
        # Set max age
        req.outcookie['trac_auth_token']['max-age'] = self.session_timeout
    
    def _clear_auth_cookie(self, req):
        """Clear authentication cookie"""
        req.outcookie['trac_auth_token'] = ''
        req.outcookie['trac_auth_token']['path'] = req.href()
        req.outcookie['trac_auth_token']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        req.outcookie['trac_auth_token']['max-age'] = '0'
    
    def _redirect_to_login(self, req, referer):
        """Redirect to login page"""
        login_url = req.href.login()
        if referer and referer != login_url:
            login_url += '?referer=' + req.href.escape(referer)
        req.redirect(login_url)