"""
Redis client for caching and session management
Provides async Redis operations with connection pooling
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import timedelta
import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from ..config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis client for caching operations"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self._pool: Optional[ConnectionPool] = None
    
    async def initialize(self):
        """Initialize Redis connection pool"""
        try:
            self._pool = aioredis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=50,
                decode_responses=True
            )
            
            self.redis = aioredis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self.redis.ping()
            
            logger.info("Redis connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
        if self._pool:
            await self._pool.disconnect()
    
    # Basic operations
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Union[str, int, float],
        expire: Optional[int] = None
    ) -> bool:
        """Set key-value with optional expiration (seconds)"""
        try:
            if expire:
                return await self.redis.setex(key, expire, value)
            else:
                return await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys"""
        try:
            return await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return 0
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        try:
            return await self.redis.exists(*keys)
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key"""
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False
    
    # JSON operations
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value"""
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis get_json error: {e}")
            return None
    
    async def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        expire: Optional[int] = None
    ) -> bool:
        """Set JSON value with optional expiration"""
        try:
            json_str = json.dumps(value)
            return await self.set(key, json_str, expire)
        except Exception as e:
            logger.error(f"Redis set_json error: {e}")
            return False
    
    # List operations
    
    async def lpush(self, key: str, *values: str) -> int:
        """Push values to the left of a list"""
        try:
            return await self.redis.lpush(key, *values)
        except Exception as e:
            logger.error(f"Redis lpush error: {e}")
            return 0
    
    async def rpush(self, key: str, *values: str) -> int:
        """Push values to the right of a list"""
        try:
            return await self.redis.rpush(key, *values)
        except Exception as e:
            logger.error(f"Redis rpush error: {e}")
            return 0
    
    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        """Get range of elements from list"""
        try:
            return await self.redis.lrange(key, start, stop)
        except Exception as e:
            logger.error(f"Redis lrange error: {e}")
            return []
    
    async def llen(self, key: str) -> int:
        """Get length of list"""
        try:
            return await self.redis.llen(key)
        except Exception as e:
            logger.error(f"Redis llen error: {e}")
            return 0
    
    # Hash operations
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field"""
        try:
            return await self.redis.hset(name, key, value)
        except Exception as e:
            logger.error(f"Redis hset error: {e}")
            return 0
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value"""
        try:
            return await self.redis.hget(name, key)
        except Exception as e:
            logger.error(f"Redis hget error: {e}")
            return None
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields and values"""
        try:
            return await self.redis.hgetall(name)
        except Exception as e:
            logger.error(f"Redis hgetall error: {e}")
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields"""
        try:
            return await self.redis.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis hdel error: {e}")
            return 0
    
    # Set operations
    
    async def sadd(self, key: str, *values: str) -> int:
        """Add members to a set"""
        try:
            return await self.redis.sadd(key, *values)
        except Exception as e:
            logger.error(f"Redis sadd error: {e}")
            return 0
    
    async def srem(self, key: str, *values: str) -> int:
        """Remove members from a set"""
        try:
            return await self.redis.srem(key, *values)
        except Exception as e:
            logger.error(f"Redis srem error: {e}")
            return 0
    
    async def smembers(self, key: str) -> set:
        """Get all members of a set"""
        try:
            return await self.redis.smembers(key)
        except Exception as e:
            logger.error(f"Redis smembers error: {e}")
            return set()
    
    async def sismember(self, key: str, value: str) -> bool:
        """Check if value is a member of set"""
        try:
            return await self.redis.sismember(key, value)
        except Exception as e:
            logger.error(f"Redis sismember error: {e}")
            return False
    
    # Cache helpers
    
    async def cache_get_or_set(
        self,
        key: str,
        func,
        expire: int = 3600
    ) -> Any:
        """Get from cache or compute and set"""
        # Try to get from cache
        cached = await self.get(key)
        if cached is not None:
            return json.loads(cached) if cached.startswith('{') else cached
        
        # Compute value
        value = await func() if callable(func) else func
        
        # Cache the result
        if value is not None:
            if isinstance(value, (dict, list)):
                await self.set_json(key, value, expire)
            else:
                await self.set(key, str(value), expire)
        
        return value
    
    # Session management
    
    async def create_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """Create a session with data"""
        key = f"session:{session_id}"
        return await self.set_json(key, data, ttl)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        key = f"session:{session_id}"
        return await self.get_json(key)
    
    async def update_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        extend_ttl: bool = True
    ) -> bool:
        """Update session data"""
        key = f"session:{session_id}"
        
        # Get existing session
        existing = await self.get_json(key)
        if not existing:
            return False
        
        # Merge data
        existing.update(data)
        
        # Save back
        success = await self.set_json(key, existing)
        
        # Extend TTL if requested
        if success and extend_ttl:
            await self.expire(key, 86400)  # 24 hours
        
        return success
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        key = f"session:{session_id}"
        return await self.delete(key) > 0
    
    # Rate limiting
    
    async def is_rate_limited(
        self,
        identifier: str,
        limit: int,
        window: int = 60
    ) -> bool:
        """Check if identifier is rate limited"""
        key = f"rate_limit:{identifier}"
        
        try:
            # Increment counter
            current = await self.redis.incr(key)
            
            # Set expiration on first request
            if current == 1:
                await self.expire(key, window)
            
            return current > limit
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return False


# Create singleton instance
redis_cache = RedisCache()