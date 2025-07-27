"""
Modern Session Manager for Trac
Python 2.7 Compatible

Handles secure session token generation, validation, and storage.
"""

import hashlib
import hmac
import time
import base64
import json
import uuid
import os
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from trac.util.text import exception_to_unicode


class ModernSessionManager(object):
    """
    Manages secure session tokens with Redis backend
    
    Features:
    - HMAC-signed session tokens
    - Redis storage with TTL
    - Automatic session cleanup
    - Activity tracking
    """
    
    def __init__(self, env, auth_component):
        self.env = env
        self.auth = auth_component
        self.secret_key = auth_component.secret_key
        
        # Initialize Redis connection
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=auth_component.redis_host,
                    port=int(auth_component.redis_port),
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                self.env.log.info("Connected to Redis at %s:%s", 
                                auth_component.redis_host, auth_component.redis_port)
            except Exception as e:
                self.env.log.warning("Redis connection failed: %s. Using fallback storage.", 
                                   exception_to_unicode(e))
                self.redis_client = None
        else:
            self.env.log.warning("Redis not available. Using fallback session storage.")
            self.redis_client = None
        
        # Fallback: in-memory session storage (not recommended for production)
        self._fallback_sessions = {}
    
    def authenticate_user(self, username, password, client_ip):
        """
        Authenticate user and create session token
        
        Args:
            username: Username
            password: Password
            client_ip: Client IP address
            
        Returns:
            Session token if authentication successful, None otherwise
        """
        try:
            # Validate credentials against Trac's user database
            if not self._validate_credentials(username, password):
                return None
            
            # Get user information
            user_info = self._get_user_info(username)
            if not user_info:
                return None
            
            # Generate session token
            session_token = self._generate_session_token(user_info, client_ip)
            
            # Store session
            self._store_session(session_token, user_info, client_ip)
            
            return session_token
            
        except Exception as e:
            self.env.log.error("Authentication error for user '%s': %s", 
                             username, exception_to_unicode(e))
            return None
    
    def validate_session_token(self, session_token):
        """
        Validate session token and return user information
        
        Args:
            session_token: Session token to validate
            
        Returns:
            User information dict if valid, None otherwise
        """
        try:
            # Parse and verify token signature
            if not self._verify_token_signature(session_token):
                return None
            
            # Extract payload
            payload = self._extract_token_payload(session_token)
            if not payload:
                return None
            
            # Check expiration
            if payload.get('expires_at', 0) < int(time.time()):
                # Token expired - clean up
                self._remove_session(session_token)
                return None
            
            # Retrieve session data
            session_data = self._get_session_data(session_token)
            if not session_data:
                return None
            
            return session_data.get('user_info')
            
        except Exception as e:
            self.env.log.error("Token validation error: %s", exception_to_unicode(e))
            return None
    
    def update_session_activity(self, session_token):
        """Update last activity timestamp for session"""
        try:
            session_data = self._get_session_data(session_token)
            if session_data:
                session_data['last_activity'] = int(time.time())
                self._store_session_data(session_token, session_data)
        except Exception as e:
            self.env.log.error("Failed to update session activity: %s", exception_to_unicode(e))
    
    def invalidate_session(self, session_token):
        """Invalidate session token"""
        try:
            self._remove_session(session_token)
        except Exception as e:
            self.env.log.error("Failed to invalidate session: %s", exception_to_unicode(e))
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions (called periodically)"""
        # Redis handles TTL automatically, but we can clean up fallback storage
        if not self.redis_client:
            current_time = int(time.time())
            expired_tokens = []
            
            for token, data in self._fallback_sessions.items():
                if data.get('expires_at', 0) < current_time:
                    expired_tokens.append(token)
            
            for token in expired_tokens:
                del self._fallback_sessions[token]
            
            if expired_tokens:
                self.env.log.info("Cleaned up %d expired sessions", len(expired_tokens))
    
    # Private methods
    
    def _validate_credentials(self, username, password):
        """Validate user credentials against Trac's authentication"""
        try:
            # Use Trac's built-in password checking
            # This works with whatever password store Trac is configured to use
            from trac.web.auth import LoginModule
            
            # Check if user exists
            if not self._user_exists(username):
                return False
            
            # For now, we'll use a simple approach
            # In production, this should integrate with Trac's password stores
            # (htpasswd, database, LDAP, etc.)
            
            # This is a placeholder - replace with actual password validation
            # based on your Trac configuration
            return self._check_password_hash(username, password)
            
        except Exception as e:
            self.env.log.error("Credential validation error: %s", exception_to_unicode(e))
            return False
    
    def _user_exists(self, username):
        """Check if user exists in Trac"""
        try:
            # Query Trac's session table to check if user exists
            with self.env.db_transaction as db:
                cursor = db.cursor()
                cursor.execute("SELECT sid FROM session WHERE authenticated=1 AND sid=%s", (username,))
                return cursor.fetchone() is not None
        except:
            # Fallback: assume user exists if we can't check
            return True
    
    def _check_password_hash(self, username, password):
        """
        Check password hash - this needs to be configured based on your setup
        
        This is a placeholder implementation. In practice, you would:
        1. For htpasswd: read and verify against htpasswd file
        2. For database: query user table and verify hash
        3. For LDAP: perform LDAP bind
        """
        # Placeholder implementation
        # TODO: Integrate with actual Trac password storage
        
        # For development/testing
        test_users = {
            'admin': 'admin',
            'test': 'test',
            'user': 'password'
        }
        
        return test_users.get(username) == password
    
    def _get_user_info(self, username):
        """Get user information from Trac"""
        try:
            # Get user's session data and permissions
            user_info = {
                'username': username,
                'permissions': self._get_user_permissions(username),
                'groups': self._get_user_groups(username),
                'full_name': self._get_user_full_name(username),
                'email': self._get_user_email(username)
            }
            return user_info
            
        except Exception as e:
            self.env.log.error("Failed to get user info for '%s': %s", 
                             username, exception_to_unicode(e))
            return None
    
    def _get_user_permissions(self, username):
        """Get user's permissions from Trac"""
        try:
            perm_system = self.env[PermissionSystem]
            return list(perm_system.get_user_permissions(username))
        except:
            # Basic permissions fallback
            return ['WIKI_VIEW', 'TICKET_VIEW']
    
    def _get_user_groups(self, username):
        """Get user's groups"""
        try:
            # This depends on your group configuration
            # Placeholder implementation
            if username == 'admin':
                return ['admin']
            else:
                return ['users']
        except:
            return []
    
    def _get_user_full_name(self, username):
        """Get user's full name from session"""
        try:
            with self.env.db_transaction as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT value FROM session_attribute 
                    WHERE sid=%s AND authenticated=1 AND name='name'
                """, (username,))
                result = cursor.fetchone()
                return result[0] if result else username
        except:
            return username
    
    def _get_user_email(self, username):
        """Get user's email from session"""
        try:
            with self.env.db_transaction as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT value FROM session_attribute 
                    WHERE sid=%s AND authenticated=1 AND name='email'
                """, (username,))
                result = cursor.fetchone()
                return result[0] if result else None
        except:
            return None
    
    def _generate_session_token(self, user_info, client_ip):
        """Generate secure session token"""
        # Create payload
        payload = {
            'user_id': user_info['username'],
            'permissions': user_info['permissions'],
            'groups': user_info['groups'],
            'issued_at': int(time.time()),
            'expires_at': int(time.time()) + int(self.auth.session_timeout),
            'session_id': str(uuid.uuid4()),
            'client_ip': client_ip
        }
        
        # Encode payload
        payload_json = json.dumps(payload, sort_keys=True)
        payload_b64 = base64.b64encode(payload_json.encode('utf-8')).decode('ascii')
        
        # Create signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Combine payload and signature
        return payload_b64 + '.' + signature
    
    def _verify_token_signature(self, session_token):
        """Verify token signature"""
        try:
            parts = session_token.split('.')
            if len(parts) != 2:
                return False
            
            payload_b64, signature = parts
            
            # Recalculate signature
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                payload_b64.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Constant-time comparison
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            self.env.log.error("Token signature verification failed: %s", exception_to_unicode(e))
            return False
    
    def _extract_token_payload(self, session_token):
        """Extract payload from token"""
        try:
            payload_b64 = session_token.split('.')[0]
            payload_json = base64.b64decode(payload_b64.encode('ascii')).decode('utf-8')
            return json.loads(payload_json)
        except Exception as e:
            self.env.log.error("Failed to extract token payload: %s", exception_to_unicode(e))
            return None
    
    def _store_session(self, session_token, user_info, client_ip):
        """Store session data"""
        session_data = {
            'user_info': user_info,
            'client_ip': client_ip,
            'created_at': int(time.time()),
            'last_activity': int(time.time())
        }
        
        self._store_session_data(session_token, session_data)
    
    def _store_session_data(self, session_token, session_data):
        """Store session data in Redis or fallback storage"""
        try:
            session_key = self._get_session_key(session_token)
            
            if self.redis_client:
                # Store in Redis with TTL
                self.redis_client.setex(
                    session_key,
                    int(self.auth.session_timeout),
                    json.dumps(session_data)
                )
            else:
                # Store in fallback storage
                session_data['expires_at'] = int(time.time()) + int(self.auth.session_timeout)
                self._fallback_sessions[session_key] = session_data
                
        except Exception as e:
            self.env.log.error("Failed to store session data: %s", exception_to_unicode(e))
    
    def _get_session_data(self, session_token):
        """Get session data from storage"""
        try:
            session_key = self._get_session_key(session_token)
            
            if self.redis_client:
                # Get from Redis
                data = self.redis_client.get(session_key)
                return json.loads(data) if data else None
            else:
                # Get from fallback storage
                return self._fallback_sessions.get(session_key)
                
        except Exception as e:
            self.env.log.error("Failed to get session data: %s", exception_to_unicode(e))
            return None
    
    def _remove_session(self, session_token):
        """Remove session from storage"""
        try:
            session_key = self._get_session_key(session_token)
            
            if self.redis_client:
                self.redis_client.delete(session_key)
            else:
                self._fallback_sessions.pop(session_key, None)
                
        except Exception as e:
            self.env.log.error("Failed to remove session: %s", exception_to_unicode(e))
    
    def _get_session_key(self, session_token):
        """Generate Redis key for session"""
        # Use hash of token for privacy
        token_hash = hashlib.sha256(session_token.encode('utf-8')).hexdigest()[:32]
        return 'trac_session:{}'.format(token_hash)


# Import PermissionSystem if available
try:
    from trac.perm import PermissionSystem
except ImportError:
    PermissionSystem = None