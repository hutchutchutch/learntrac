"""
Neo4j Query Optimizer and Cache Manager

Provides query optimization and caching for Neo4j operations including:
- Query plan analysis and optimization
- Result caching with TTL and LRU eviction
- Query pattern recognition and rewriting
- Batch query optimization
- Performance monitoring and statistics
"""

import logging
import hashlib
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import OrderedDict, defaultdict
import time

from .neo4j_connection_manager import Neo4jConnectionManager

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Caching strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Combines multiple strategies


class QueryType(Enum):
    """Types of queries for optimization"""
    VECTOR_SEARCH = "vector_search"
    GRAPH_TRAVERSAL = "graph_traversal"
    AGGREGATION = "aggregation"
    PATTERN_MATCH = "pattern_match"
    BATCH_OPERATION = "batch_operation"


@dataclass
class CacheEntry:
    """Entry in the query cache"""
    key: str
    query: str
    parameters: Dict[str, Any]
    result: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 1
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl_seconds is None:
            return False
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    def touch(self) -> None:
        """Update last accessed time and count"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


@dataclass
class QueryStats:
    """Statistics for a query pattern"""
    pattern: str
    execution_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    last_executed: Optional[datetime] = None
    
    def record_execution(self, execution_time: float, cache_hit: bool) -> None:
        """Record a query execution"""
        self.execution_count += 1
        self.total_execution_time += execution_time
        self.avg_execution_time = self.total_execution_time / self.execution_count
        self.last_executed = datetime.utcnow()
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1


@dataclass
class OptimizationHint:
    """Optimization hint for queries"""
    hint_type: str
    description: str
    suggested_query: Optional[str] = None
    estimated_improvement: float = 0.0


class QueryOptimizer:
    """
    Query optimization engine for Neo4j.
    
    Features:
    - Query pattern analysis
    - Query rewriting for performance
    - Index usage optimization
    - Batch query detection
    """
    
    def __init__(self):
        """Initialize query optimizer"""
        self.optimization_rules = self._load_optimization_rules()
        self.query_patterns = self._compile_query_patterns()
        
    def optimize_query(
        self,
        query: str,
        parameters: Dict[str, Any],
        query_type: Optional[QueryType] = None
    ) -> Tuple[str, List[OptimizationHint]]:
        """
        Optimize a query and return optimized version with hints.
        
        Args:
            query: Original Cypher query
            parameters: Query parameters
            query_type: Type of query for targeted optimization
            
        Returns:
            Optimized query and optimization hints
        """
        hints = []
        optimized_query = query
        
        # Detect query type if not provided
        if not query_type:
            query_type = self._detect_query_type(query)
        
        # Apply type-specific optimizations
        if query_type == QueryType.VECTOR_SEARCH:
            optimized_query, type_hints = self._optimize_vector_search(query, parameters)
            hints.extend(type_hints)
        elif query_type == QueryType.GRAPH_TRAVERSAL:
            optimized_query, type_hints = self._optimize_graph_traversal(query, parameters)
            hints.extend(type_hints)
        elif query_type == QueryType.AGGREGATION:
            optimized_query, type_hints = self._optimize_aggregation(query, parameters)
            hints.extend(type_hints)
        
        # Apply general optimizations
        optimized_query, general_hints = self._apply_general_optimizations(optimized_query)
        hints.extend(general_hints)
        
        return optimized_query, hints
    
    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the type of query"""
        query_lower = query.lower()
        
        if "db.index.vector.querynodes" in query_lower:
            return QueryType.VECTOR_SEARCH
        elif any(pattern in query_lower for pattern in ["*...", "path =", "shortestpath"]):
            return QueryType.GRAPH_TRAVERSAL
        elif any(func in query_lower for func in ["count(", "sum(", "avg(", "collect("]):
            return QueryType.AGGREGATION
        elif "unwind" in query_lower and any(op in query_lower for op in ["create", "merge"]):
            return QueryType.BATCH_OPERATION
        else:
            return QueryType.PATTERN_MATCH
    
    def _optimize_vector_search(
        self,
        query: str,
        parameters: Dict[str, Any]
    ) -> Tuple[str, List[OptimizationHint]]:
        """Optimize vector search queries"""
        hints = []
        optimized = query
        
        # Check for filter pushdown opportunity
        if "where" in query.lower() and "db.index.vector" in query.lower():
            lines = query.split('\n')
            vector_line_idx = -1
            where_line_idx = -1
            
            for i, line in enumerate(lines):
                if "db.index.vector" in line.lower():
                    vector_line_idx = i
                elif "where" in line.lower() and vector_line_idx >= 0:
                    where_line_idx = i
                    break
            
            if vector_line_idx >= 0 and where_line_idx > vector_line_idx:
                # Can potentially push filters before vector search
                hints.append(OptimizationHint(
                    hint_type="filter_pushdown",
                    description="Consider filtering nodes before vector search to reduce search space",
                    estimated_improvement=0.3
                ))
        
        # Check for appropriate limit
        if "limit" not in query.lower():
            hints.append(OptimizationHint(
                hint_type="missing_limit",
                description="Add LIMIT clause to vector search for better performance",
                estimated_improvement=0.2
            ))
        
        return optimized, hints
    
    def _optimize_graph_traversal(
        self,
        query: str,
        parameters: Dict[str, Any]
    ) -> Tuple[str, List[OptimizationHint]]:
        """Optimize graph traversal queries"""
        hints = []
        optimized = query
        
        # Check for unbounded traversals
        import re
        unbounded_pattern = r'\[\*\]|\[\*\.\.\]'
        if re.search(unbounded_pattern, query):
            hints.append(OptimizationHint(
                hint_type="unbounded_traversal",
                description="Unbounded traversal detected. Consider adding upper limit",
                suggested_query=re.sub(unbounded_pattern, '[*1..5]', query),
                estimated_improvement=0.5
            ))
        
        # Check for missing direction
        if "-[" in query and not any(x in query for x in ["->", "<-"]):
            hints.append(OptimizationHint(
                hint_type="missing_direction",
                description="Specify relationship direction for better performance",
                estimated_improvement=0.2
            ))
        
        return optimized, hints
    
    def _optimize_aggregation(
        self,
        query: str,
        parameters: Dict[str, Any]
    ) -> Tuple[str, List[OptimizationHint]]:
        """Optimize aggregation queries"""
        hints = []
        optimized = query
        
        # Check for missing indexes on aggregation keys
        if "group by" in query.lower() or "order by" in query.lower():
            hints.append(OptimizationHint(
                hint_type="index_suggestion",
                description="Consider adding indexes on grouping/ordering properties",
                estimated_improvement=0.4
            ))
        
        # Check for collect without limit
        if "collect(" in query.lower() and "collect(distinct" not in query.lower():
            if not re.search(r'collect\([^)]+\)\[[:\d]+\]', query):
                hints.append(OptimizationHint(
                    hint_type="unlimited_collect",
                    description="Consider limiting collected elements to prevent memory issues",
                    estimated_improvement=0.3
                ))
        
        return optimized, hints
    
    def _apply_general_optimizations(
        self,
        query: str
    ) -> Tuple[str, List[OptimizationHint]]:
        """Apply general query optimizations"""
        hints = []
        optimized = query
        
        # Remove unnecessary OPTIONAL MATCH if no results are used
        lines = query.split('\n')
        for i, line in enumerate(lines):
            if "optional match" in line.lower():
                # Check if the matched variable is used later
                # This is simplified - real implementation would parse properly
                match_var = re.search(r'\((\w+):', line)
                if match_var:
                    var_name = match_var.group(1)
                    rest_of_query = '\n'.join(lines[i+1:])
                    if var_name not in rest_of_query:
                        hints.append(OptimizationHint(
                            hint_type="unused_optional_match",
                            description=f"OPTIONAL MATCH result '{var_name}' is not used",
                            estimated_improvement=0.1
                        ))
        
        # Check for redundant DISTINCT
        if query.lower().count("distinct") > 1:
            hints.append(OptimizationHint(
                hint_type="redundant_distinct",
                description="Multiple DISTINCT clauses detected, consider consolidation",
                estimated_improvement=0.1
            ))
        
        return optimized, hints
    
    def _load_optimization_rules(self) -> Dict[str, Any]:
        """Load optimization rules"""
        return {
            "filter_early": "Apply filters as early as possible in the query",
            "use_indexes": "Ensure queries use available indexes",
            "limit_traversal": "Limit traversal depth for better performance",
            "batch_operations": "Use UNWIND for batch operations"
        }
    
    def _compile_query_patterns(self) -> Dict[str, re.Pattern]:
        """Compile common query patterns"""
        return {
            "vector_search": re.compile(r'db\.index\.vector\.queryNodes'),
            "shortest_path": re.compile(r'shortestPath\s*\('),
            "variable_length": re.compile(r'\[\*(\d*\.\.)?(\d*)\]'),
            "aggregation": re.compile(r'(count|sum|avg|collect)\s*\('),
            "optional_match": re.compile(r'optional\s+match', re.IGNORECASE)
        }


class Neo4jQueryCache:
    """
    Query result cache for Neo4j operations.
    
    Features:
    - Multiple caching strategies
    - TTL support
    - Size-based eviction
    - Cache warming
    - Statistics tracking
    """
    
    def __init__(
        self,
        strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        max_size_mb: int = 100,
        default_ttl_seconds: int = 3600
    ):
        """
        Initialize query cache.
        
        Args:
            strategy: Caching strategy to use
            max_size_mb: Maximum cache size in MB
            default_ttl_seconds: Default TTL for entries
        """
        self.strategy = strategy
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl_seconds
        
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_size_bytes = 0
        self.stats: Dict[str, QueryStats] = defaultdict(QueryStats)
        
        self._lock = asyncio.Lock()
        
    async def get(
        self,
        query: str,
        parameters: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Get cached query result.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            
        Returns:
            Cached result or None
        """
        cache_key = self._generate_cache_key(query, parameters)
        
        async with self._lock:
            entry = self.cache.get(cache_key)
            
            if entry is None:
                self._record_miss(query)
                return None
            
            # Check expiration
            if entry.is_expired():
                self._evict_entry(cache_key)
                self._record_miss(query)
                return None
            
            # Update access info
            entry.touch()
            
            # Move to end for LRU
            if self.strategy in [CacheStrategy.LRU, CacheStrategy.ADAPTIVE]:
                self.cache.move_to_end(cache_key)
            
            self._record_hit(query)
            return entry.result
    
    async def put(
        self,
        query: str,
        parameters: Dict[str, Any],
        result: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Cache query result.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            result: Query result
            ttl_seconds: Optional TTL override
        """
        cache_key = self._generate_cache_key(query, parameters)
        result_size = self._estimate_size(result)
        
        async with self._lock:
            # Check if we need to evict entries
            while self.current_size_bytes + result_size > self.max_size_bytes:
                if not self._evict_one():
                    # Can't evict anything, don't cache
                    return
            
            # Create new entry
            entry = CacheEntry(
                key=cache_key,
                query=query,
                parameters=parameters,
                result=result,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                size_bytes=result_size,
                ttl_seconds=ttl_seconds or self.default_ttl
            )
            
            # Add to cache
            self.cache[cache_key] = entry
            self.current_size_bytes += result_size
    
    async def invalidate(
        self,
        pattern: Optional[str] = None
    ) -> int:
        """
        Invalidate cache entries.
        
        Args:
            pattern: Optional pattern to match queries
            
        Returns:
            Number of entries invalidated
        """
        async with self._lock:
            if pattern is None:
                # Clear all
                count = len(self.cache)
                self.cache.clear()
                self.current_size_bytes = 0
                return count
            
            # Invalidate matching entries
            to_remove = []
            for key, entry in self.cache.items():
                if pattern in entry.query:
                    to_remove.append(key)
            
            for key in to_remove:
                self._evict_entry(key)
            
            return len(to_remove)
    
    async def warm_cache(
        self,
        queries: List[Tuple[str, Dict[str, Any]]],
        connection: Neo4jConnectionManager
    ) -> int:
        """
        Warm cache with predefined queries.
        
        Args:
            queries: List of (query, parameters) tuples
            connection: Neo4j connection for executing queries
            
        Returns:
            Number of queries cached
        """
        cached_count = 0
        
        for query, parameters in queries:
            try:
                # Check if already cached
                if await self.get(query, parameters) is not None:
                    continue
                
                # Execute query
                result = await connection.execute_query(query, parameters)
                
                # Cache result
                await self.put(query, parameters, result)
                cached_count += 1
                
            except Exception as e:
                logger.error(f"Failed to warm cache for query: {e}")
                continue
        
        logger.info(f"Warmed cache with {cached_count} queries")
        return cached_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = sum(s.cache_hits for s in self.stats.values())
        total_misses = sum(s.cache_misses for s in self.stats.values())
        hit_rate = total_hits / (total_hits + total_misses) if total_hits + total_misses > 0 else 0
        
        return {
            "cache_size": len(self.cache),
            "size_bytes": self.current_size_bytes,
            "size_mb": self.current_size_bytes / (1024 * 1024),
            "hit_rate": hit_rate,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "query_patterns": len(self.stats),
            "strategy": self.strategy.value
        }
    
    def _generate_cache_key(
        self,
        query: str,
        parameters: Dict[str, Any]
    ) -> str:
        """Generate cache key from query and parameters"""
        # Normalize query (remove extra whitespace)
        normalized_query = ' '.join(query.split())
        
        # Create stable parameter string
        param_str = json.dumps(parameters, sort_keys=True)
        
        # Generate hash
        content = f"{normalized_query}:{param_str}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate size of object in bytes"""
        if isinstance(obj, (str, bytes)):
            return len(obj)
        elif isinstance(obj, (list, tuple)):
            return sum(self._estimate_size(item) for item in obj)
        elif isinstance(obj, dict):
            return sum(
                self._estimate_size(k) + self._estimate_size(v)
                for k, v in obj.items()
            )
        else:
            # Rough estimate for other types
            return 64
    
    def _evict_one(self) -> bool:
        """Evict one entry based on strategy"""
        if not self.cache:
            return False
        
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used (first item)
            key = next(iter(self.cache))
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].access_count
            )
        elif self.strategy == CacheStrategy.TTL:
            # Remove oldest
            key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].created_at
            )
        else:  # ADAPTIVE
            # Combine factors
            now = datetime.utcnow()
            key = min(
                self.cache.keys(),
                key=lambda k: self._calculate_eviction_score(self.cache[k], now)
            )
        
        self._evict_entry(key)
        return True
    
    def _evict_entry(self, key: str) -> None:
        """Evict a specific entry"""
        if key in self.cache:
            entry = self.cache[key]
            self.current_size_bytes -= entry.size_bytes
            del self.cache[key]
    
    def _calculate_eviction_score(
        self,
        entry: CacheEntry,
        now: datetime
    ) -> float:
        """Calculate eviction score for adaptive strategy (lower = evict first)"""
        # Factor in recency
        age_seconds = (now - entry.last_accessed).total_seconds()
        recency_score = 1.0 / (1.0 + age_seconds / 3600)  # Decay over hours
        
        # Factor in frequency
        frequency_score = min(1.0, entry.access_count / 10.0)
        
        # Factor in size (prefer evicting larger entries)
        size_score = 1.0 - (entry.size_bytes / self.max_size_bytes)
        
        # Combine factors
        return recency_score * 0.4 + frequency_score * 0.4 + size_score * 0.2
    
    def _record_hit(self, query: str) -> None:
        """Record cache hit"""
        pattern = self._extract_query_pattern(query)
        self.stats[pattern].record_execution(0.0, cache_hit=True)
    
    def _record_miss(self, query: str) -> None:
        """Record cache miss"""
        pattern = self._extract_query_pattern(query)
        self.stats[pattern].record_execution(0.0, cache_hit=False)
    
    def _extract_query_pattern(self, query: str) -> str:
        """Extract query pattern for statistics"""
        # Simple pattern extraction - could be more sophisticated
        # Remove parameters and literals
        pattern = re.sub(r'\$\w+', '$param', query)
        pattern = re.sub(r"'[^']*'", "'literal'", pattern)
        pattern = re.sub(r'\d+', 'N', pattern)
        pattern = ' '.join(pattern.split())  # Normalize whitespace
        return pattern


class Neo4jQueryOptimizer:
    """
    Combined query optimizer and cache manager.
    
    Integrates optimization and caching for optimal performance.
    """
    
    def __init__(
        self,
        connection_manager: Neo4jConnectionManager,
        cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        cache_size_mb: int = 100,
        enable_optimization: bool = True
    ):
        """
        Initialize query optimizer with cache.
        
        Args:
            connection_manager: Neo4j connection manager
            cache_strategy: Caching strategy
            cache_size_mb: Maximum cache size
            enable_optimization: Whether to enable query optimization
        """
        self.connection = connection_manager
        self.optimizer = QueryOptimizer() if enable_optimization else None
        self.cache = Neo4jQueryCache(
            strategy=cache_strategy,
            max_size_mb=cache_size_mb
        )
        self.enable_optimization = enable_optimization
        
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        ttl_seconds: Optional[int] = None
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Execute query with optimization and caching.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            use_cache: Whether to use cache
            ttl_seconds: Optional TTL for cache
            
        Returns:
            Query result and execution metadata
        """
        parameters = parameters or {}
        metadata = {
            "optimized": False,
            "cache_hit": False,
            "execution_time": 0.0,
            "optimization_hints": []
        }
        
        start_time = time.time()
        
        # Try cache first
        if use_cache:
            cached_result = await self.cache.get(query, parameters)
            if cached_result is not None:
                metadata["cache_hit"] = True
                metadata["execution_time"] = time.time() - start_time
                return cached_result, metadata
        
        # Optimize query
        optimized_query = query
        if self.enable_optimization:
            optimized_query, hints = self.optimizer.optimize_query(query, parameters)
            metadata["optimized"] = optimized_query != query
            metadata["optimization_hints"] = [
                {"type": h.hint_type, "description": h.description}
                for h in hints
            ]
        
        # Execute query
        try:
            result = await self.connection.execute_query(optimized_query, parameters)
            
            # Cache result
            if use_cache:
                await self.cache.put(query, parameters, result, ttl_seconds)
            
            metadata["execution_time"] = time.time() - start_time
            return result, metadata
            
        except Exception as e:
            metadata["error"] = str(e)
            metadata["execution_time"] = time.time() - start_time
            raise
    
    async def analyze_query_performance(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze query performance without caching.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            
        Returns:
            Performance analysis
        """
        parameters = parameters or {}
        
        # Get query plan
        explain_query = f"EXPLAIN {query}"
        plan_result = await self.connection.execute_query(explain_query, parameters)
        
        # Get optimization hints
        if self.enable_optimization:
            _, hints = self.optimizer.optimize_query(query, parameters)
        else:
            hints = []
        
        # Execute with timing
        start_time = time.time()
        result = await self.connection.execute_query(query, parameters)
        execution_time = time.time() - start_time
        
        return {
            "execution_time": execution_time,
            "result_count": len(result) if isinstance(result, list) else 1,
            "optimization_hints": [
                {
                    "type": h.hint_type,
                    "description": h.description,
                    "estimated_improvement": h.estimated_improvement
                }
                for h in hints
            ],
            "query_type": self.optimizer._detect_query_type(query).value if self.optimizer else "unknown"
        }
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        cache_stats = self.cache.get_stats()
        
        # Get top query patterns by execution count
        top_patterns = sorted(
            self.cache.stats.items(),
            key=lambda x: x[1].execution_count,
            reverse=True
        )[:10]
        
        return {
            "cache": cache_stats,
            "top_query_patterns": [
                {
                    "pattern": pattern,
                    "executions": stats.execution_count,
                    "cache_hit_rate": stats.cache_hits / stats.execution_count if stats.execution_count > 0 else 0,
                    "avg_execution_time": stats.avg_execution_time
                }
                for pattern, stats in top_patterns
            ],
            "optimization_enabled": self.enable_optimization
        }