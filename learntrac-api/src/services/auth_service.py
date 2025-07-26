"""
Authentication and User Management Service

Provides authentication and user management for Trac integration including:
- JWT-based authentication
- User registration and profile management
- Role-based access control
- Session management
- OAuth integration support
"""

import logging
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib
import jwt
from passlib.context import CryptContext
import asyncio

from ..db.database import DatabaseManager
from ..services.redis_client import RedisCache
from ..config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class User:
    """User model"""
    id: str
    email: str
    username: str
    full_name: str
    role: str  # student/instructor/admin
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    preferences: Dict[str, Any] = None
    

@dataclass
class UserSession:
    """User session model"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    device_info: Optional[str] = None
    ip_address: Optional[str] = None


@dataclass
class AuthToken:
    """Authentication token model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # seconds


class AuthService:
    """
    Authentication and user management service.
    
    Features:
    - User registration and authentication
    - JWT token generation and validation
    - Session management
    - Role-based access control
    - Password reset functionality
    - OAuth provider integration
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        redis_cache: RedisCache,
        jwt_secret: Optional[str] = None,
        jwt_algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        """
        Initialize authentication service.
        
        Args:
            db_manager: Database manager
            redis_cache: Redis cache for sessions
            jwt_secret: Secret key for JWT
            jwt_algorithm: JWT signing algorithm
            access_token_expire_minutes: Access token expiration
            refresh_token_expire_days: Refresh token expiration
        """
        self.db_manager = db_manager
        self.redis_cache = redis_cache
        self.jwt_secret = jwt_secret or settings.jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=refresh_token_expire_days)
        
        # Initialize tables if needed
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize authentication service"""
        try:
            # Create tables if they don't exist
            await self._create_tables()
            
            # Create default admin user if none exists
            await self._ensure_admin_user()
            
            self._initialized = True
            logger.info("AuthService initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AuthService: {e}")
            return False
    
    # ===== User Registration and Management =====
    
    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        full_name: str,
        role: str = "student"
    ) -> Optional[User]:
        """
        Register a new user.
        
        Args:
            email: User email
            username: Username
            password: Plain text password
            full_name: Full name
            role: User role (student/instructor/admin)
            
        Returns:
            Created user or None if failed
        """
        try:
            # Check if user already exists
            existing = await self.db_manager.fetch_one(
                "SELECT id FROM users WHERE email = $1 OR username = $2",
                email, username
            )
            
            if existing:
                logger.warning(f"User already exists: {email} or {username}")
                return None
            
            # Hash password
            hashed_password = pwd_context.hash(password)
            
            # Generate user ID
            user_id = self._generate_user_id(email)
            
            # Insert user
            await self.db_manager.execute(
                """
                INSERT INTO users 
                (id, email, username, password_hash, full_name, role, 
                 is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                user_id, email, username, hashed_password, full_name, 
                role, True, datetime.utcnow()
            )
            
            # Create user profile
            await self.db_manager.execute(
                """
                INSERT INTO user_profiles 
                (user_id, preferences, learning_stats)
                VALUES ($1, $2, $3)
                """,
                user_id, 
                '{"theme": "light", "notifications": true}',
                '{"level": "beginner", "interests": []}'
            )
            
            logger.info(f"User registered successfully: {email}")
            
            return User(
                id=user_id,
                email=email,
                username=username,
                full_name=full_name,
                role=role,
                is_active=True,
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to register user: {e}")
            return None
    
    async def authenticate_user(
        self,
        email_or_username: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user with email/username and password.
        
        Args:
            email_or_username: Email or username
            password: Plain text password
            
        Returns:
            Authenticated user or None
        """
        try:
            # Get user from database
            user_data = await self.db_manager.fetch_one(
                """
                SELECT id, email, username, password_hash, full_name, 
                       role, is_active, created_at, last_login
                FROM users
                WHERE (email = $1 OR username = $1) AND is_active = true
                """,
                email_or_username
            )
            
            if not user_data:
                return None
            
            # Verify password
            if not pwd_context.verify(password, user_data["password_hash"]):
                return None
            
            # Update last login
            await self.db_manager.execute(
                "UPDATE users SET last_login = $1 WHERE id = $2",
                datetime.utcnow(), user_data["id"]
            )
            
            # Get preferences
            profile = await self.db_manager.fetch_one(
                "SELECT preferences FROM user_profiles WHERE user_id = $1",
                user_data["id"]
            )
            
            return User(
                id=user_data["id"],
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=user_data["is_active"],
                created_at=user_data["created_at"],
                last_login=datetime.utcnow(),
                preferences=profile["preferences"] if profile else {}
            )
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            user_data = await self.db_manager.fetch_one(
                """
                SELECT u.*, up.preferences
                FROM users u
                LEFT JOIN user_profiles up ON u.id = up.user_id
                WHERE u.id = $1
                """,
                user_id
            )
            
            if not user_data:
                return None
            
            return User(
                id=user_data["id"],
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=user_data["is_active"],
                created_at=user_data["created_at"],
                last_login=user_data["last_login"],
                preferences=user_data["preferences"] or {}
            )
            
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    async def update_user(
        self,
        user_id: str,
        **updates
    ) -> bool:
        """
        Update user information.
        
        Args:
            user_id: User ID
            **updates: Fields to update
            
        Returns:
            Success status
        """
        try:
            # Build update query
            allowed_fields = ["email", "username", "full_name", "role", "is_active"]
            update_fields = []
            values = []
            
            for field, value in updates.items():
                if field in allowed_fields:
                    update_fields.append(f"{field} = ${len(values) + 2}")
                    values.append(value)
            
            if not update_fields:
                return True  # Nothing to update
            
            query = f"""
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE id = $1
            """
            
            await self.db_manager.execute(query, user_id, *values)
            
            # Invalidate user cache
            await self.redis_cache.delete(f"user:{user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return False
    
    # ===== Token Management =====
    
    async def create_tokens(self, user: User) -> AuthToken:
        """
        Create access and refresh tokens for user.
        
        Args:
            user: User object
            
        Returns:
            Authentication tokens
        """
        # Create access token
        access_token_data = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "exp": datetime.utcnow() + self.access_token_expire
        }
        access_token = jwt.encode(
            access_token_data,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )
        
        # Create refresh token
        refresh_token_data = {
            "sub": user.id,
            "type": "refresh",
            "exp": datetime.utcnow() + self.refresh_token_expire
        }
        refresh_token = jwt.encode(
            refresh_token_data,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )
        
        # Store refresh token in Redis
        await self.redis_cache.set(
            f"refresh_token:{user.id}:{refresh_token[-10:]}",
            refresh_token,
            ttl=int(self.refresh_token_expire.total_seconds())
        )
        
        return AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self.access_token_expire.total_seconds())
        )
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    async def refresh_tokens(self, refresh_token: str) -> Optional[AuthToken]:
        """
        Refresh authentication tokens.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New tokens or None if invalid
        """
        # Verify refresh token
        payload = await self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        
        # Check if refresh token is still valid in Redis
        token_key = f"refresh_token:{user_id}:{refresh_token[-10:]}"
        stored_token = await self.redis_cache.get(token_key)
        
        if not stored_token or stored_token != refresh_token:
            return None
        
        # Get user
        user = await self.get_user(user_id)
        if not user or not user.is_active:
            return None
        
        # Revoke old refresh token
        await self.redis_cache.delete(token_key)
        
        # Create new tokens
        return await self.create_tokens(user)
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
            
        Returns:
            Success status
        """
        try:
            payload = await self.verify_token(token)
            if not payload:
                return False
            
            # Add token to blacklist
            exp = payload.get("exp", 0)
            ttl = max(0, exp - int(datetime.utcnow().timestamp()))
            
            if ttl > 0:
                await self.redis_cache.set(
                    f"blacklist:{token[-20:]}",
                    "1",
                    ttl=ttl
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        result = await self.redis_cache.get(f"blacklist:{token[-20:]}")
        return result is not None
    
    # ===== Session Management =====
    
    async def create_session(
        self,
        user_id: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> UserSession:
        """
        Create a user session.
        
        Args:
            user_id: User ID
            device_info: Device information
            ip_address: IP address
            
        Returns:
            User session
        """
        session_id = secrets.token_urlsafe(32)
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            device_info=device_info,
            ip_address=ip_address
        )
        
        # Store in Redis
        await self.redis_cache.set(
            f"session:{session_id}",
            {
                "user_id": user_id,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "device_info": device_info,
                "ip_address": ip_address
            },
            ttl=86400  # 24 hours
        )
        
        # Track user sessions
        await self.redis_cache.sadd(f"user_sessions:{user_id}", session_id)
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        session_data = await self.redis_cache.get(f"session:{session_id}")
        
        if not session_data:
            return None
        
        return UserSession(
            session_id=session_id,
            user_id=session_data["user_id"],
            created_at=datetime.fromisoformat(session_data["created_at"]),
            expires_at=datetime.fromisoformat(session_data["expires_at"]),
            device_info=session_data.get("device_info"),
            ip_address=session_data.get("ip_address")
        )
    
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a session"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # Remove from Redis
        await self.redis_cache.delete(f"session:{session_id}")
        await self.redis_cache.srem(f"user_sessions:{session.user_id}", session_id)
        
        return True
    
    async def revoke_all_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user"""
        session_ids = await self.redis_cache.smembers(f"user_sessions:{user_id}")
        
        for session_id in session_ids:
            await self.redis_cache.delete(f"session:{session_id}")
        
        await self.redis_cache.delete(f"user_sessions:{user_id}")
        
        return len(session_ids)
    
    # ===== Password Management =====
    
    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
            
        Returns:
            Success status
        """
        try:
            # Get current password hash
            user_data = await self.db_manager.fetch_one(
                "SELECT password_hash FROM users WHERE id = $1",
                user_id
            )
            
            if not user_data:
                return False
            
            # Verify old password
            if not pwd_context.verify(old_password, user_data["password_hash"]):
                return False
            
            # Hash new password
            new_hash = pwd_context.hash(new_password)
            
            # Update password
            await self.db_manager.execute(
                "UPDATE users SET password_hash = $1 WHERE id = $2",
                new_hash, user_id
            )
            
            # Revoke all sessions
            await self.revoke_all_sessions(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to change password: {e}")
            return False
    
    async def request_password_reset(self, email: str) -> Optional[str]:
        """
        Request password reset.
        
        Args:
            email: User email
            
        Returns:
            Reset token or None
        """
        user = await self.db_manager.fetch_one(
            "SELECT id FROM users WHERE email = $1",
            email
        )
        
        if not user:
            return None
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Store in Redis with expiration
        await self.redis_cache.set(
            f"password_reset:{reset_token}",
            user["id"],
            ttl=3600  # 1 hour
        )
        
        return reset_token
    
    async def reset_password(
        self,
        reset_token: str,
        new_password: str
    ) -> bool:
        """
        Reset password with token.
        
        Args:
            reset_token: Reset token
            new_password: New password
            
        Returns:
            Success status
        """
        # Get user ID from token
        user_id = await self.redis_cache.get(f"password_reset:{reset_token}")
        
        if not user_id:
            return False
        
        # Hash new password
        new_hash = pwd_context.hash(new_password)
        
        # Update password
        await self.db_manager.execute(
            "UPDATE users SET password_hash = $1 WHERE id = $2",
            new_hash, user_id
        )
        
        # Delete reset token
        await self.redis_cache.delete(f"password_reset:{reset_token}")
        
        # Revoke all sessions
        await self.revoke_all_sessions(user_id)
        
        return True
    
    # ===== Role-Based Access Control =====
    
    async def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> bool:
        """
        Check if user has permission for action on resource.
        
        Args:
            user_id: User ID
            resource: Resource name
            action: Action name
            
        Returns:
            Permission status
        """
        # Get user role
        user = await self.get_user(user_id)
        if not user:
            return False
        
        # Define permissions matrix
        permissions = {
            "admin": {
                "textbook": ["create", "read", "update", "delete"],
                "user": ["create", "read", "update", "delete"],
                "learning_path": ["create", "read", "update", "delete"],
                "analytics": ["read"]
            },
            "instructor": {
                "textbook": ["create", "read", "update"],
                "user": ["read"],
                "learning_path": ["create", "read", "update"],
                "analytics": ["read"]
            },
            "student": {
                "textbook": ["read"],
                "user": ["read"],  # Own profile only
                "learning_path": ["read"],
                "analytics": ["read"]  # Own analytics only
            }
        }
        
        role_permissions = permissions.get(user.role, {})
        resource_permissions = role_permissions.get(resource, [])
        
        return action in resource_permissions
    
    async def require_role(self, user_id: str, required_roles: List[str]) -> bool:
        """Check if user has one of the required roles"""
        user = await self.get_user(user_id)
        return user and user.role in required_roles
    
    # ===== Private Helper Methods =====
    
    async def _create_tables(self) -> None:
        """Create authentication tables"""
        await self.db_manager.execute_many([
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(64) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'student',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP NOT NULL,
                last_login TIMESTAMP,
                CONSTRAINT valid_role CHECK (role IN ('student', 'instructor', 'admin'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id VARCHAR(64) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                preferences JSONB DEFAULT '{}',
                learning_stats JSONB DEFAULT '{}',
                avatar_url VARCHAR(500),
                bio TEXT,
                timezone VARCHAR(50) DEFAULT 'UTC',
                language VARCHAR(10) DEFAULT 'en',
                notifications_enabled BOOLEAN DEFAULT true,
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
            """
        ])
    
    async def _ensure_admin_user(self) -> None:
        """Ensure at least one admin user exists"""
        admin_exists = await self.db_manager.fetch_one(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
        )
        
        if not admin_exists:
            # Create default admin
            await self.register_user(
                email="admin@learntrac.local",
                username="admin",
                password="admin123!",  # Should be changed immediately
                full_name="System Administrator",
                role="admin"
            )
            logger.warning(
                "Created default admin user. "
                "Please change the password immediately!"
            )
    
    def _generate_user_id(self, email: str) -> str:
        """Generate unique user ID"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        hash_input = f"{email}:{timestamp}:{secrets.token_hex(8)}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:32]