"""
Rate Limiter for Modern Auth
Python 2.7 Compatible

Provides rate limiting and brute force protection.
"""

import time
import json
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RateLimiter(object):
    """
    Rate limiter with Redis backend and fallback storage
    
    Features:
    - IP-based rate limiting
    - Progressive delays
    - Automatic cleanup
    - Fallback to memory storage
    """
    
    def __init__(self, redis_host='localhost', redis_port=6379, 
                 max_attempts=5, window_seconds=900):
        """
        Initialize rate limiter
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            max_attempts: Maximum attempts per window
            window_seconds: Time window in seconds
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        
        # Initialize Redis connection
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                self.use_redis = True
            except Exception:
                self.redis_client = None
                self.use_redis = False
        else:
            self.redis_client = None
            self.use_redis = False
        
        # Fallback: in-memory storage
        self._memory_storage = {}
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def is_rate_limited(self, identifier):
        """
        Check if identifier is rate limited
        
        Args:
            identifier: IP address or user identifier
            
        Returns:
            True if rate limited, False otherwise
        """
        try:
            attempts = self._get_attempts(identifier)
            return attempts >= self.max_attempts
        except Exception:
            # If we can't check, allow the request (fail open)
            return False
    
    def record_failed_attempt(self, identifier):
        """
        Record a failed attempt
        
        Args:
            identifier: IP address or user identifier
        """
        try:
            current_attempts = self._get_attempts(identifier)
            new_attempts = current_attempts + 1
            
            self._set_attempts(identifier, new_attempts)
            
            # Set expiration for the rate limit window
            self._set_expiration(identifier, self.window_seconds)
            
        except Exception:
            # If we can't record, continue (fail open)
            pass
    
    def reset_attempts(self, identifier):
        """
        Reset attempts for identifier (after successful login)
        
        Args:
            identifier: IP address or user identifier
        """
        try:
            self._delete_attempts(identifier)
        except Exception:
            # If we can't reset, continue
            pass
    
    def get_remaining_attempts(self, identifier):
        """
        Get remaining attempts before rate limiting
        
        Args:
            identifier: IP address or user identifier
            
        Returns:
            Number of remaining attempts
        """
        try:
            current_attempts = self._get_attempts(identifier)
            return max(0, self.max_attempts - current_attempts)
        except Exception:
            return self.max_attempts
    
    def get_lockout_time_remaining(self, identifier):
        """
        Get remaining lockout time in seconds
        
        Args:
            identifier: IP address or user identifier
            
        Returns:
            Seconds remaining in lockout, 0 if not locked out
        """
        try:
            if not self.is_rate_limited(identifier):
                return 0
            
            return self._get_ttl(identifier)
        except Exception:
            return 0
    
    def cleanup_expired_entries(self):
        """Clean up expired entries (for memory storage)"""
        if self.use_redis:
            # Redis handles TTL automatically
            return
        
        current_time = time.time()
        
        # Only cleanup periodically
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        # Clean expired entries
        expired_keys = []
        for key, data in self._memory_storage.items():
            if data.get('expires_at', 0) < current_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._memory_storage[key]
        
        self._last_cleanup = current_time
    
    # Private methods
    
    def _get_attempts(self, identifier):
        """Get current attempt count"""
        key = self._make_key(identifier)
        
        if self.use_redis:
            attempts = self.redis_client.get(key)
            return int(attempts) if attempts else 0
        else:
            # Clean up expired entries
            self.cleanup_expired_entries()
            
            data = self._memory_storage.get(key, {})
            if data.get('expires_at', 0) < time.time():
                # Expired
                return 0
            return data.get('attempts', 0)
    
    def _set_attempts(self, identifier, attempts):
        """Set attempt count"""
        key = self._make_key(identifier)
        
        if self.use_redis:
            self.redis_client.set(key, attempts)
        else:
            expires_at = time.time() + self.window_seconds
            self._memory_storage[key] = {
                'attempts': attempts,
                'expires_at': expires_at
            }
    
    def _set_expiration(self, identifier, seconds):
        """Set expiration time"""
        key = self._make_key(identifier)
        
        if self.use_redis:
            self.redis_client.expire(key, seconds)
        # Memory storage expiration is handled in _set_attempts
    
    def _delete_attempts(self, identifier):
        """Delete attempt record"""
        key = self._make_key(identifier)
        
        if self.use_redis:
            self.redis_client.delete(key)
        else:
            self._memory_storage.pop(key, None)
    
    def _get_ttl(self, identifier):
        """Get time to live for key"""
        key = self._make_key(identifier)
        
        if self.use_redis:
            ttl = self.redis_client.ttl(key)
            return max(0, ttl) if ttl > 0 else 0
        else:
            data = self._memory_storage.get(key, {})
            expires_at = data.get('expires_at', 0)
            remaining = expires_at - time.time()
            return max(0, int(remaining))
    
    def _make_key(self, identifier):
        """Create storage key for identifier"""
        return 'rate_limit:{}'.format(identifier)


class ProgressiveRateLimiter(RateLimiter):
    """
    Rate limiter with progressive delays
    
    Increases lockout time with each subsequent failure.
    """
    
    def __init__(self, redis_host='localhost', redis_port=6379, 
                 base_window=900, max_window=3600):
        """
        Initialize progressive rate limiter
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port  
            base_window: Base window in seconds (15 minutes)
            max_window: Maximum window in seconds (1 hour)
        """
        super(ProgressiveRateLimiter, self).__init__(
            redis_host=redis_host,
            redis_port=redis_port,
            max_attempts=3,  # Lower threshold for progressive limiting
            window_seconds=base_window
        )
        
        self.base_window = base_window
        self.max_window = max_window
    
    def record_failed_attempt(self, identifier):
        """Record failed attempt with progressive penalty"""
        try:
            # Get failure count
            failure_count = self._get_failure_count(identifier)
            failure_count += 1
            
            # Calculate progressive window
            window = min(
                self.base_window * (2 ** (failure_count - 1)),
                self.max_window
            )
            
            # Store failure count
            self._set_failure_count(identifier, failure_count)
            
            # Set attempts with progressive window
            self._set_attempts(identifier, self.max_attempts)
            self._set_expiration(identifier, window)
            
        except Exception:
            # Fallback to parent implementation
            super(ProgressiveRateLimiter, self).record_failed_attempt(identifier)
    
    def reset_attempts(self, identifier):
        """Reset both attempts and failure count"""
        super(ProgressiveRateLimiter, self).reset_attempts(identifier)
        self._delete_failure_count(identifier)
    
    def _get_failure_count(self, identifier):
        """Get progressive failure count"""
        key = self._make_failure_key(identifier)
        
        if self.use_redis:
            count = self.redis_client.get(key)
            return int(count) if count else 0
        else:
            data = self._memory_storage.get(key, {})
            # Failure count doesn't expire automatically
            return data.get('failure_count', 0)
    
    def _set_failure_count(self, identifier, count):
        """Set progressive failure count"""
        key = self._make_failure_key(identifier)
        
        if self.use_redis:
            # Store failure count for 24 hours
            self.redis_client.setex(key, 86400, count)
        else:
            expires_at = time.time() + 86400  # 24 hours
            self._memory_storage[key] = {
                'failure_count': count,
                'expires_at': expires_at
            }
    
    def _delete_failure_count(self, identifier):
        """Delete progressive failure count"""
        key = self._make_failure_key(identifier)
        
        if self.use_redis:
            self.redis_client.delete(key)
        else:
            self._memory_storage.pop(key, None)
    
    def _make_failure_key(self, identifier):
        """Create storage key for failure count"""
        return 'failure_count:{}'.format(identifier)