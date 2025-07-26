"""
Neo4j Connection Manager for Educational Content

Manages connections to Neo4j database with support for:
- Connection pooling and health checks
- Automatic retry logic
- Transaction management
- Batch operations
- Performance monitoring
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import time

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, AsyncTransaction
from neo4j.exceptions import (
    Neo4jError, ServiceUnavailable, SessionExpired,
    TransientError, DatabaseUnavailable
)

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for Neo4j connection"""
    uri: str
    username: str
    password: str
    database: str = "neo4j"
    
    # Connection pool settings
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60
    
    # Retry settings
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    retry_backoff_factor: float = 2.0
    
    # Performance settings
    batch_size: int = 1000
    query_timeout_seconds: int = 30


@dataclass
class ConnectionStats:
    """Statistics for connection monitoring"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_transactions: int = 0
    successful_transactions: int = 0
    failed_transactions: int = 0
    retry_count: int = 0
    total_query_time: float = 0.0
    connection_errors: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None


class Neo4jConnectionManager:
    """
    Manages Neo4j database connections with advanced features.
    
    Features:
    - Async connection pooling
    - Automatic retry with exponential backoff
    - Transaction management
    - Batch operation support
    - Health monitoring
    - Performance tracking
    """
    
    def __init__(self, config: ConnectionConfig):
        """
        Initialize connection manager.
        
        Args:
            config: Connection configuration
        """
        self.config = config
        self.driver: Optional[AsyncDriver] = None
        self._initialized = False
        self.stats = ConnectionStats()
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> bool:
        """
        Initialize Neo4j connection.
        
        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            if self._initialized:
                return True
            
            try:
                logger.info(f"Initializing Neo4j connection to {self.config.uri}")
                
                self.driver = AsyncGraphDatabase.driver(
                    self.config.uri,
                    auth=(self.config.username, self.config.password),
                    max_connection_lifetime=self.config.max_connection_lifetime,
                    max_connection_pool_size=self.config.max_connection_pool_size,
                    connection_acquisition_timeout=self.config.connection_acquisition_timeout
                )
                
                # Verify connection
                await self.verify_connectivity()
                
                self._initialized = True
                logger.info("Neo4j connection initialized successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j connection: {e}")
                self._record_error(str(e))
                return False
    
    async def close(self) -> None:
        """Close Neo4j connection"""
        async with self._lock:
            if self.driver:
                await self.driver.close()
                self.driver = None
                self._initialized = False
                logger.info("Neo4j connection closed")
    
    async def verify_connectivity(self) -> bool:
        """
        Verify database connectivity.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                return record["test"] == 1
        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")
            self._record_error(str(e))
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health status dictionary
        """
        health = {
            "status": "unhealthy",
            "connected": False,
            "database": self.config.database,
            "stats": {
                "total_queries": self.stats.total_queries,
                "success_rate": self._calculate_success_rate(),
                "average_query_time": self._calculate_average_query_time(),
                "connection_errors": self.stats.connection_errors,
                "last_error": self.stats.last_error,
                "last_error_time": self.stats.last_error_time.isoformat() if self.stats.last_error_time else None
            }
        }
        
        try:
            if await self.verify_connectivity():
                # Get database info
                async with self.driver.session(database=self.config.database) as session:
                    result = await session.run("""
                        CALL dbms.components()
                        YIELD name, versions, edition
                        WHERE name = 'Neo4j Kernel'
                        RETURN versions[0] as version, edition
                    """)
                    record = await result.single()
                    
                    if record:
                        health["version"] = record["version"]
                        health["edition"] = record["edition"]
                    
                    health["status"] = "healthy"
                    health["connected"] = True
                    
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health["error"] = str(e)
        
        return health
    
    @asynccontextmanager
    async def session(self, **kwargs):
        """
        Create a database session with automatic retry.
        
        Yields:
            AsyncSession object
        """
        if not self._initialized:
            await self.initialize()
        
        session_kwargs = {"database": self.config.database}
        session_kwargs.update(kwargs)
        
        session = None
        try:
            session = self.driver.session(**session_kwargs)
            yield session
        finally:
            if session:
                await session.close()
    
    @asynccontextmanager
    async def transaction(self, session: AsyncSession):
        """
        Create a transaction with automatic retry and error handling.
        
        Args:
            session: Database session
            
        Yields:
            AsyncTransaction object
        """
        tx = None
        try:
            tx = await session.begin_transaction()
            self.stats.total_transactions += 1
            yield tx
            await tx.commit()
            self.stats.successful_transactions += 1
        except Exception as e:
            self.stats.failed_transactions += 1
            if tx:
                try:
                    await tx.rollback()
                except:
                    pass
            raise
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a query with automatic retry.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            List of result records as dictionaries
        """
        timeout = timeout or self.config.query_timeout_seconds
        start_time = time.time()
        
        for attempt in range(self.config.max_retry_attempts):
            try:
                self.stats.total_queries += 1
                
                async with self.session() as session:
                    result = await session.run(
                        query,
                        parameters or {},
                        timeout=timeout
                    )
                    records = [dict(record) async for record in result]
                    
                    self.stats.successful_queries += 1
                    self.stats.total_query_time += time.time() - start_time
                    
                    return records
                    
            except (ServiceUnavailable, SessionExpired, TransientError) as e:
                # Retryable errors
                self.stats.retry_count += 1
                if attempt < self.config.max_retry_attempts - 1:
                    delay = self.config.retry_delay_seconds * (self.config.retry_backoff_factor ** attempt)
                    logger.warning(f"Query failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    self.stats.failed_queries += 1
                    self._record_error(str(e))
                    raise
                    
            except Exception as e:
                # Non-retryable errors
                self.stats.failed_queries += 1
                self._record_error(str(e))
                raise
    
    async def execute_write_transaction(
        self,
        transaction_function,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a write transaction with automatic retry.
        
        Args:
            transaction_function: Async function that performs the transaction
            *args, **kwargs: Arguments for the transaction function
            
        Returns:
            Transaction result
        """
        for attempt in range(self.config.max_retry_attempts):
            try:
                async with self.session() as session:
                    async with self.transaction(session) as tx:
                        result = await transaction_function(tx, *args, **kwargs)
                        return result
                        
            except (ServiceUnavailable, SessionExpired, TransientError) as e:
                self.stats.retry_count += 1
                if attempt < self.config.max_retry_attempts - 1:
                    delay = self.config.retry_delay_seconds * (self.config.retry_backoff_factor ** attempt)
                    logger.warning(f"Transaction failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    self._record_error(str(e))
                    raise
                    
            except Exception as e:
                self._record_error(str(e))
                raise
    
    async def execute_batch_write(
        self,
        query: str,
        data: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute batch write operations.
        
        Args:
            query: Cypher query with parameters
            data: List of parameter dictionaries
            batch_size: Batch size (uses config default if not specified)
            
        Returns:
            Summary of batch execution
        """
        batch_size = batch_size or self.config.batch_size
        total_records = len(data)
        processed = 0
        failed = 0
        errors = []
        
        logger.info(f"Starting batch write of {total_records} records in batches of {batch_size}")
        
        for i in range(0, total_records, batch_size):
            batch = data[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            try:
                async with self.session() as session:
                    async with self.transaction(session) as tx:
                        for params in batch:
                            await tx.run(query, params)
                
                processed += len(batch)
                logger.debug(f"Batch {batch_num} completed: {len(batch)} records")
                
            except Exception as e:
                failed += len(batch)
                error_msg = f"Batch {batch_num} failed: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        summary = {
            "total": total_records,
            "processed": processed,
            "failed": failed,
            "success_rate": processed / total_records if total_records > 0 else 0,
            "errors": errors
        }
        
        logger.info(f"Batch write completed: {processed}/{total_records} successful")
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_queries": self.stats.total_queries,
            "successful_queries": self.stats.successful_queries,
            "failed_queries": self.stats.failed_queries,
            "query_success_rate": self._calculate_success_rate(),
            "average_query_time": self._calculate_average_query_time(),
            "total_transactions": self.stats.total_transactions,
            "successful_transactions": self.stats.successful_transactions,
            "failed_transactions": self.stats.failed_transactions,
            "retry_count": self.stats.retry_count,
            "connection_errors": self.stats.connection_errors,
            "last_error": self.stats.last_error,
            "last_error_time": self.stats.last_error_time.isoformat() if self.stats.last_error_time else None
        }
    
    def reset_stats(self) -> None:
        """Reset connection statistics"""
        self.stats = ConnectionStats()
    
    def _calculate_success_rate(self) -> float:
        """Calculate query success rate"""
        if self.stats.total_queries == 0:
            return 0.0
        return self.stats.successful_queries / self.stats.total_queries
    
    def _calculate_average_query_time(self) -> float:
        """Calculate average query execution time"""
        if self.stats.successful_queries == 0:
            return 0.0
        return self.stats.total_query_time / self.stats.successful_queries
    
    def _record_error(self, error: str) -> None:
        """Record error information"""
        self.stats.connection_errors += 1
        self.stats.last_error = error
        self.stats.last_error_time = datetime.utcnow()


class Neo4jConnectionPool:
    """
    Connection pool manager for multiple database connections.
    
    Useful for multi-database or multi-tenant scenarios.
    """
    
    def __init__(self):
        """Initialize connection pool"""
        self.connections: Dict[str, Neo4jConnectionManager] = {}
        self._lock = asyncio.Lock()
    
    async def add_connection(
        self,
        name: str,
        config: ConnectionConfig
    ) -> Neo4jConnectionManager:
        """
        Add a new connection to the pool.
        
        Args:
            name: Connection name
            config: Connection configuration
            
        Returns:
            Connection manager instance
        """
        async with self._lock:
            if name in self.connections:
                raise ValueError(f"Connection '{name}' already exists")
            
            manager = Neo4jConnectionManager(config)
            if await manager.initialize():
                self.connections[name] = manager
                logger.info(f"Added connection '{name}' to pool")
                return manager
            else:
                raise RuntimeError(f"Failed to initialize connection '{name}'")
    
    def get_connection(self, name: str) -> Neo4jConnectionManager:
        """
        Get a connection from the pool.
        
        Args:
            name: Connection name
            
        Returns:
            Connection manager instance
        """
        if name not in self.connections:
            raise ValueError(f"Connection '{name}' not found")
        return self.connections[name]
    
    async def remove_connection(self, name: str) -> None:
        """
        Remove a connection from the pool.
        
        Args:
            name: Connection name
        """
        async with self._lock:
            if name in self.connections:
                await self.connections[name].close()
                del self.connections[name]
                logger.info(f"Removed connection '{name}' from pool")
    
    async def close_all(self) -> None:
        """Close all connections in the pool"""
        async with self._lock:
            for name, manager in self.connections.items():
                await manager.close()
            self.connections.clear()
            logger.info("Closed all connections in pool")
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all connections.
        
        Returns:
            Health status for each connection
        """
        results = {}
        for name, manager in self.connections.items():
            results[name] = await manager.health_check()
        return results