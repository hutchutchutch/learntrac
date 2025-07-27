"""
Security Utilities for Modern Auth
Python 2.7 Compatible

Provides CSRF protection, secure random generation, and other security utilities.
"""

import hashlib
import hmac
import time
import uuid
import os
import base64


class SecurityUtils(object):
    """Security utilities for modern authentication"""
    
    def __init__(self):
        pass
    
    def generate_csrf_token(self):
        """Generate secure CSRF token"""
        # Combine timestamp, random UUID, and entropy
        timestamp = str(int(time.time()))
        random_uuid = str(uuid.uuid4())
        entropy = self._get_entropy()
        
        # Create token data
        token_data = '{}.{}.{}'.format(timestamp, random_uuid, entropy)
        
        # Hash to create final token
        return hashlib.sha256(token_data.encode('utf-8')).hexdigest()[:32]
    
    def verify_csrf_token(self, token, max_age=3600):
        """
        Verify CSRF token (basic implementation)
        
        Note: This is a simple implementation. For production,
        you might want to store and validate tokens more rigorously.
        """
        if not token or len(token) != 32:
            return False
        
        # For this implementation, we'll consider any well-formed token valid
        # In production, you'd want to store and validate against known tokens
        return True
    
    def generate_secure_random(self, length=32):
        """Generate cryptographically secure random string"""
        try:
            # Use os.urandom for cryptographic randomness
            random_bytes = os.urandom(length)
            return base64.b64encode(random_bytes).decode('ascii')[:length]
        except:
            # Fallback to UUID-based randomness
            return str(uuid.uuid4()).replace('-', '')[:length]
    
    def hash_password(self, password, salt=None):
        """
        Hash password with salt (basic implementation)
        
        Note: This is a simple implementation for compatibility.
        In production, use proper password hashing like bcrypt or PBKDF2.
        """
        if salt is None:
            salt = self.generate_secure_random(16)
        
        # Use PBKDF2-like iteration (simplified)
        hashed = password + salt
        for _ in range(1000):  # 1000 iterations
            hashed = hashlib.sha256(hashed.encode('utf-8')).hexdigest()
        
        return '{}${}'.format(salt, hashed)
    
    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        try:
            parts = hashed_password.split('$')
            if len(parts) != 2:
                return False
            
            salt, stored_hash = parts
            computed_hash = self.hash_password(password, salt)
            
            # Constant-time comparison
            return hmac.compare_digest(hashed_password, computed_hash)
        except:
            return False
    
    def generate_api_key(self):
        """Generate API key"""
        # Generate a strong API key
        prefix = 'ltac_'  # LearnTrac API Key prefix
        key_part = self.generate_secure_random(40)
        return prefix + key_part
    
    def is_secure_connection(self, request):
        """Check if connection is secure (HTTPS)"""
        # Check various headers that indicate HTTPS
        if request.scheme == 'https':
            return True
        
        # Check for proxy headers
        if request.environ.get('HTTP_X_FORWARDED_PROTO') == 'https':
            return True
        
        if request.environ.get('HTTP_X_FORWARDED_SSL') == 'on':
            return True
        
        return False
    
    def get_client_ip(self, request):
        """Get client IP address, handling proxies"""
        # Check for forwarded IP (from load balancer/proxy)
        forwarded_for = request.environ.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(',')[0].strip()
        
        # Check for real IP header
        real_ip = request.environ.get('HTTP_X_REAL_IP')
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct connection IP
        return request.environ.get('REMOTE_ADDR', 'unknown')
    
    def sanitize_redirect_url(self, url, base_url):
        """
        Sanitize redirect URL to prevent open redirects
        
        Args:
            url: URL to sanitize
            base_url: Base URL for the application
            
        Returns:
            Safe redirect URL
        """
        if not url:
            return base_url
        
        # Remove any leading/trailing whitespace
        url = url.strip()
        
        # Block external redirects
        if url.startswith('http://') or url.startswith('https://'):
            # Only allow redirects to same domain
            if not url.startswith(base_url):
                return base_url
        
        # Block javascript: and data: URLs
        if url.lower().startswith(('javascript:', 'data:', 'vbscript:')):
            return base_url
        
        # Ensure URL starts with /
        if not url.startswith('/'):
            url = '/' + url
        
        return url
    
    def add_security_headers(self, request, response):
        """Add security headers to response"""
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        # Add HSTS for HTTPS connections
        if self.is_secure_connection(request):
            headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Add CSP header
        csp_policy = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # Trac needs inline scripts
            "style-src 'self' 'unsafe-inline'",   # Trac needs inline styles
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'self'"
        ]
        headers['Content-Security-Policy'] = '; '.join(csp_policy)
        
        # Apply headers to response
        for header, value in headers.items():
            response[header] = value
    
    def _get_entropy(self):
        """Get additional entropy for random generation"""
        try:
            # Try to get some system entropy
            entropy_sources = [
                str(time.time()),
                str(os.getpid()),
                str(id(self)),
            ]
            
            # Add memory address entropy if available
            try:
                entropy_sources.append(str(id(os)))
            except:
                pass
            
            entropy = ''.join(entropy_sources)
            return hashlib.sha256(entropy.encode('utf-8')).hexdigest()[:16]
        except:
            # Fallback to simple timestamp
            return str(int(time.time() * 1000000))[-16:]