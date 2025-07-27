"""
Database connection and session management
Provides async database access using asyncpg and SQLAlchemy
"""

from typing import AsyncGenerator, Optional
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self):
        self.engine = None
        self.async_session_maker = None
        self.pool = None
    
    async def initialize(self):
        """Initialize database connections"""
        try:
            # Create SQLAlchemy async engine
            self.engine = create_async_engine(
                settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
                echo=False,
                poolclass=NullPool  # Let asyncpg handle pooling
            )
            
            # Create session maker
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create asyncpg pool for raw queries with SSL
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Use direct connection parameters to avoid URL parsing issues
            self.pool = await asyncpg.create_pool(
                host="hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com",
                port=5432,
                user="learntrac_admin",
                password="Vp-Sl}}D[(j&zxP5cjh%MTQtitYq2ic7",
                database="learntrac",
                min_size=10,
                max_size=20,
                command_timeout=60,
                ssl=ssl_context
            )
            
            logger.info("Database connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close all database connections"""
        if self.engine:
            await self.engine.dispose()
        if self.pool:
            await self.pool.close()
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get SQLAlchemy async session"""
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get raw asyncpg connection from pool"""
        return await self.pool.acquire()
    
    async def release_connection(self, connection: asyncpg.Connection):
        """Release connection back to pool"""
        await self.pool.release(connection)
    
    async def execute_query(self, query: str, *args) -> list:
        """Execute a raw SQL query and return results"""
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)
    
    async def execute_query_one(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Execute a raw SQL query and return single result"""
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)
    
    async def execute_command(self, query: str, *args):
        """Execute a SQL command (INSERT, UPDATE, DELETE)"""
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)


# Create singleton instance
db_manager = DatabaseManager()


# Dependency to get database session
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session"""
    async for session in db_manager.get_session():
        yield session


# Dependency to get raw connection
async def get_db_connection() -> asyncpg.Connection:
    """FastAPI dependency to get raw database connection"""
    connection = await db_manager.get_connection()
    try:
        yield connection
    finally:
        await db_manager.release_connection(connection)