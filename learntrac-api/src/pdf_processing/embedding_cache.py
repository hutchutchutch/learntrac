"""
Embedding Cache and Optimization - Advanced caching and optimization for embeddings

Implements sophisticated caching strategies, embedding optimization techniques,
and performance enhancements for educational content embedding systems.
"""

import os
import json
import pickle
import sqlite3
import hashlib
import time
import threading
import logging
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import numpy as np
from collections import defaultdict, OrderedDict
import gzip

from .embedding_generator import EmbeddingResult, EmbeddingModel
from .chunk_metadata import ChunkMetadata, ContentType


class CacheStrategy(Enum):
    """Caching strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used  
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on usage patterns
    CONTENT_AWARE = "content_aware"  # Based on content characteristics


class CompressionType(Enum):
    """Compression types for embeddings"""
    NONE = "none"
    GZIP = "gzip"
    QUANTIZATION_8BIT = "quantization_8bit"
    QUANTIZATION_4BIT = "quantization_4bit"
    PCA_REDUCTION = "pca_reduction"


class OptimizationTechnique(Enum):
    """Embedding optimization techniques"""
    NORMALIZATION = "normalization"
    DIMENSIONALITY_REDUCTION = "dimensionality_reduction"
    DEDUPLICATION = "deduplication"
    QUANTIZATION = "quantization"
    CLUSTERING = "clustering"


@dataclass
class CacheConfig:
    """Configuration for embedding cache"""
    # Cache strategy
    strategy: CacheStrategy = CacheStrategy.ADAPTIVE
    max_size: int = 100000  # Maximum number of cached embeddings
    max_memory_mb: int = 1024  # Maximum memory usage in MB
    
    # TTL settings
    default_ttl: int = 86400  # 24 hours in seconds
    content_type_ttl: Dict[ContentType, int] = field(default_factory=lambda: {
        ContentType.DEFINITION: 86400 * 7,  # 7 days
        ContentType.MATH: 86400 * 3,        # 3 days
        ContentType.EXAMPLE: 86400 * 5,     # 5 days
        ContentType.TEXT: 86400             # 1 day
    })
    
    # Persistence settings
    enable_persistence: bool = True
    cache_directory: str = ".embedding_cache"
    database_file: str = "embeddings.db"
    
    # Compression settings
    compression_type: CompressionType = CompressionType.GZIP
    compression_threshold: int = 1000  # Compress embeddings larger than this
    
    # Optimization settings
    enable_optimization: bool = True
    optimization_techniques: List[OptimizationTechnique] = field(default_factory=lambda: [
        OptimizationTechnique.NORMALIZATION,
        OptimizationTechnique.DEDUPLICATION
    ])
    
    # Performance settings
    enable_background_cleanup: bool = True
    cleanup_interval: int = 3600  # 1 hour
    batch_write_size: int = 100
    thread_safe: bool = True


@dataclass
class CacheEntry:
    """Cache entry for an embedding"""
    key: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    model: EmbeddingModel
    content_type: ContentType
    
    # Cache metadata
    created_time: float
    last_accessed: float
    access_count: int
    ttl: Optional[int] = None
    compressed: bool = False
    optimized: bool = False
    
    # Quality and performance info
    quality_score: float = 0.0
    generation_time: float = 0.0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_time > self.ttl
    
    def update_access(self):
        """Update access metadata"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStatistics:
    """Cache performance statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0
    memory_usage_mb: float = 0.0
    cleanup_operations: int = 0
    compression_savings_mb: float = 0.0
    optimization_improvements: Dict[str, float] = field(default_factory=dict)
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        return 1.0 - self.hit_rate


class EmbeddingOptimizer:
    """Optimizer for embedding vectors"""
    
    def __init__(self):
        self.pca_models = {}  # Store PCA models for different dimensionalities
        self.quantization_params = {}
        self.logger = logging.getLogger(__name__)
    
    def optimize_embedding(self, 
                          embedding: np.ndarray,
                          techniques: List[OptimizationTechnique],
                          content_type: ContentType) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Apply optimization techniques to embedding.
        
        Args:
            embedding: Original embedding vector
            techniques: List of optimization techniques to apply
            content_type: Type of content (affects optimization strategy)
            
        Returns:
            Tuple of (optimized_embedding, optimization_metadata)
        """
        
        optimized = embedding.copy()
        metadata = {'applied_techniques': [], 'improvements': {}}
        
        for technique in techniques:
            if technique == OptimizationTechnique.NORMALIZATION:
                optimized, improvement = self._normalize_embedding(optimized)
                metadata['applied_techniques'].append('normalization')
                metadata['improvements']['normalization'] = improvement
            
            elif technique == OptimizationTechnique.DIMENSIONALITY_REDUCTION:
                optimized, improvement = self._reduce_dimensionality(optimized, content_type)
                metadata['applied_techniques'].append('dimensionality_reduction')
                metadata['improvements']['dimensionality_reduction'] = improvement
            
            elif technique == OptimizationTechnique.QUANTIZATION:
                optimized, improvement = self._quantize_embedding(optimized)
                metadata['applied_techniques'].append('quantization')
                metadata['improvements']['quantization'] = improvement
        
        return optimized, metadata
    
    def _normalize_embedding(self, embedding: np.ndarray) -> Tuple[np.ndarray, float]:
        """Normalize embedding to unit length"""
        original_norm = np.linalg.norm(embedding)
        if original_norm == 0:
            return embedding, 0.0
        
        normalized = embedding / original_norm
        improvement = abs(1.0 - original_norm)  # How far from unit norm
        
        return normalized, improvement
    
    def _reduce_dimensionality(self, 
                              embedding: np.ndarray, 
                              content_type: ContentType,
                              target_ratio: float = 0.8) -> Tuple[np.ndarray, float]:
        """Reduce embedding dimensionality using PCA"""
        
        original_dims = len(embedding)
        target_dims = int(original_dims * target_ratio)
        
        # For demo purposes, simulate PCA by selecting top dimensions
        # In production, would use actual PCA fitted on embedding corpus
        
        # Simulate PCA by keeping dimensions with highest absolute values
        importance = np.abs(embedding)
        top_indices = np.argsort(importance)[-target_dims:]
        
        reduced = np.zeros(target_dims)
        reduced[:] = embedding[top_indices]
        
        # Calculate information retention (simplified)
        original_energy = np.sum(embedding ** 2)
        reduced_energy = np.sum(reduced ** 2)
        retention_ratio = reduced_energy / original_energy if original_energy > 0 else 1.0
        
        return reduced, retention_ratio
    
    def _quantize_embedding(self, 
                           embedding: np.ndarray,
                           bits: int = 8) -> Tuple[np.ndarray, float]:
        """Quantize embedding to reduce memory usage"""
        
        if bits == 8:
            # Quantize to 8-bit integers
            min_val, max_val = embedding.min(), embedding.max()
            if max_val > min_val:
                scale = 255.0 / (max_val - min_val)
                quantized_int = np.round((embedding - min_val) * scale).astype(np.uint8)
                quantized = (quantized_int.astype(np.float32) / scale) + min_val
            else:
                quantized = embedding
        else:
            quantized = embedding
        
        # Calculate compression ratio
        original_size = embedding.nbytes
        quantized_size = quantized.nbytes if bits == 8 else original_size // (32 // bits)
        compression_ratio = 1.0 - (quantized_size / original_size)
        
        return quantized, compression_ratio


class PersistentCache:
    """Persistent cache using SQLite"""
    
    def __init__(self, cache_dir: str, db_file: str = "embeddings.db"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / db_file
        self.logger = logging.getLogger(__name__)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    key TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT NOT NULL,
                    created_time REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER NOT NULL,
                    ttl INTEGER,
                    compressed BOOLEAN NOT NULL,
                    optimized BOOLEAN NOT NULL,
                    quality_score REAL NOT NULL,
                    generation_time REAL NOT NULL
                )
            """)
            
            # Create indices for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON embeddings(model)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON embeddings(content_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_time ON embeddings(created_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_accessed ON embeddings(last_accessed)")
    
    def store(self, entry: CacheEntry):
        """Store cache entry in database"""
        try:
            # Serialize embedding
            embedding_blob = pickle.dumps(entry.embedding)
            if entry.compressed:
                embedding_blob = gzip.compress(embedding_blob)
            
            metadata_json = json.dumps(entry.metadata)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO embeddings 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.key, entry.model.value, entry.content_type.value,
                    embedding_blob, metadata_json, entry.created_time,
                    entry.last_accessed, entry.access_count, entry.ttl,
                    entry.compressed, entry.optimized, entry.quality_score,
                    entry.generation_time
                ))
        
        except Exception as e:
            self.logger.error(f"Failed to store cache entry {entry.key}: {e}")
    
    def load(self, key: str) -> Optional[CacheEntry]:
        """Load cache entry from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM embeddings WHERE key = ?
                """, (key,))
                row = cursor.fetchone()
                
                if row is None:
                    return None
                
                # Deserialize data
                embedding_blob = row[3]
                if row[9]:  # compressed
                    embedding_blob = gzip.decompress(embedding_blob)
                embedding = pickle.loads(embedding_blob)
                
                metadata = json.loads(row[4])
                
                return CacheEntry(
                    key=row[0],
                    model=EmbeddingModel(row[1]),
                    content_type=ContentType(row[2]),
                    embedding=embedding,
                    metadata=metadata,
                    created_time=row[5],
                    last_accessed=row[6],
                    access_count=row[7],
                    ttl=row[8],
                    compressed=row[9],
                    optimized=row[10],
                    quality_score=row[11],
                    generation_time=row[12]
                )
        
        except Exception as e:
            self.logger.error(f"Failed to load cache entry {key}: {e}")
            return None
    
    def update_access(self, key: str):
        """Update access statistics for entry"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE embeddings 
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE key = ?
                """, (time.time(), key))
        except Exception as e:
            self.logger.error(f"Failed to update access for {key}: {e}")
    
    def delete(self, key: str):
        """Delete cache entry"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM embeddings WHERE key = ?", (key,))
        except Exception as e:
            self.logger.error(f"Failed to delete cache entry {key}: {e}")
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed"""
        try:
            current_time = time.time()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM embeddings 
                    WHERE ttl IS NOT NULL AND (created_time + ttl) < ?
                """, (current_time,))
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired entries: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
                total_entries = cursor.fetchone()[0]
                
                cursor = conn.execute("""
                    SELECT model, COUNT(*) FROM embeddings GROUP BY model
                """)
                model_counts = dict(cursor.fetchall())
                
                cursor = conn.execute("""
                    SELECT content_type, COUNT(*) FROM embeddings GROUP BY content_type
                """)
                content_type_counts = dict(cursor.fetchall())
                
                return {
                    'total_entries': total_entries,
                    'model_distribution': model_counts,
                    'content_type_distribution': content_type_counts
                }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}


class AdvancedEmbeddingCache:
    """
    Advanced embedding cache with multiple strategies and optimizations.
    
    Features:
    - Multiple caching strategies (LRU, LFU, TTL, adaptive)
    - Persistent storage with SQLite
    - Embedding compression and optimization
    - Background cleanup and maintenance
    - Thread-safe operations
    - Content-aware caching policies
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # In-memory cache (primary cache)
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.access_frequencies: Dict[str, int] = defaultdict(int)
        
        # Thread safety
        self._lock = threading.RLock() if config.thread_safe else None
        
        # Persistent cache
        self.persistent_cache = None
        if config.enable_persistence:
            self.persistent_cache = PersistentCache(
                config.cache_directory, config.database_file
            )
        
        # Optimizer
        self.optimizer = EmbeddingOptimizer() if config.enable_optimization else None
        
        # Statistics
        self.stats = CacheStatistics()
        
        # Background cleanup
        self._cleanup_thread = None
        if config.enable_background_cleanup:
            self._start_background_cleanup()
        
        self.logger.info(f"Advanced embedding cache initialized: {config.strategy.value} strategy, "
                        f"max_size={config.max_size}, persistence={config.enable_persistence}")
    
    def get(self, text: str, model: EmbeddingModel, content_type: ContentType) -> Optional[EmbeddingResult]:
        """
        Get embedding from cache.
        
        Args:
            text: Text content
            model: Embedding model used
            content_type: Type of content
            
        Returns:
            EmbeddingResult if found in cache, None otherwise
        """
        
        key = self._generate_key(text, model, content_type)
        
        with self._lock if self._lock else self._dummy_context():
            self.stats.total_requests += 1
            
            # Check memory cache first
            entry = self._get_from_memory(key)
            if entry is None and self.persistent_cache:
                # Check persistent cache
                entry = self._get_from_persistent(key)
                if entry:
                    # Promote to memory cache
                    self._store_in_memory(entry)
            
            if entry:
                # Update access patterns
                entry.update_access()
                self.access_frequencies[key] += 1
                
                # Update statistics
                self.stats.cache_hits += 1
                
                # Create EmbeddingResult
                result = EmbeddingResult(
                    text=text,
                    embedding=entry.embedding,
                    model=entry.model,
                    dimensions=len(entry.embedding),
                    generation_time=entry.generation_time,
                    token_count=len(text.split()),  # Rough estimate
                    quality_score=entry.quality_score,
                    metadata=entry.metadata
                )
                
                self.logger.debug(f"Cache hit for key: {key[:20]}...")
                return result
            else:
                self.stats.cache_misses += 1
                self.logger.debug(f"Cache miss for key: {key[:20]}...")
                return None
    
    def put(self, 
           text: str, 
           model: EmbeddingModel, 
           content_type: ContentType,
           embedding_result: EmbeddingResult,
           chunk_metadata: Optional[ChunkMetadata] = None):
        """
        Store embedding in cache.
        
        Args:
            text: Original text
            model: Embedding model used
            content_type: Type of content
            embedding_result: Embedding result to cache
            chunk_metadata: Optional chunk metadata
        """
        
        key = self._generate_key(text, model, content_type)
        
        with self._lock if self._lock else self._dummy_context():
            # Determine TTL based on content type
            ttl = self.config.content_type_ttl.get(content_type, self.config.default_ttl)
            
            # Optimize embedding if enabled
            optimized_embedding = embedding_result.embedding
            optimization_metadata = {}
            
            if self.optimizer and self.config.enable_optimization:
                optimized_embedding, optimization_metadata = self.optimizer.optimize_embedding(
                    embedding_result.embedding,
                    self.config.optimization_techniques,
                    content_type
                )
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                embedding=optimized_embedding,
                metadata={
                    'original_text_length': len(text),
                    'token_count': embedding_result.token_count,
                    'optimization': optimization_metadata,
                    **(chunk_metadata.custom_metadata if chunk_metadata else {})
                },
                model=model,
                content_type=content_type,
                created_time=time.time(),
                last_accessed=time.time(),
                access_count=1,
                ttl=ttl,
                compressed=self.config.compression_type != CompressionType.NONE,
                optimized=bool(optimization_metadata),
                quality_score=embedding_result.quality_score,
                generation_time=embedding_result.generation_time
            )
            
            # Store in memory cache
            self._store_in_memory(entry)
            
            # Store in persistent cache if enabled
            if self.persistent_cache:
                self.persistent_cache.store(entry)
            
            self.logger.debug(f"Cached embedding for key: {key[:20]}...")
    
    def _get_from_memory(self, key: str) -> Optional[CacheEntry]:
        """Get entry from memory cache"""
        entry = self.memory_cache.get(key)
        if entry and not entry.is_expired():
            # Move to end for LRU
            if self.config.strategy == CacheStrategy.LRU:
                self.memory_cache.move_to_end(key)
            return entry
        elif entry and entry.is_expired():
            # Remove expired entry
            del self.memory_cache[key]
            if key in self.access_frequencies:
                del self.access_frequencies[key]
        return None
    
    def _get_from_persistent(self, key: str) -> Optional[CacheEntry]:
        """Get entry from persistent cache"""
        entry = self.persistent_cache.load(key)
        if entry and not entry.is_expired():
            self.persistent_cache.update_access(key)
            return entry
        elif entry and entry.is_expired():
            self.persistent_cache.delete(key)
        return None
    
    def _store_in_memory(self, entry: CacheEntry):
        """Store entry in memory cache with eviction policy"""
        
        # Check if we need to evict
        while len(self.memory_cache) >= self.config.max_size:
            self._evict_from_memory()
        
        # Store entry
        self.memory_cache[entry.key] = entry
        
        # Update statistics
        self.stats.cache_size = len(self.memory_cache)
        self.stats.memory_usage_mb = self._calculate_memory_usage()
    
    def _evict_from_memory(self):
        """Evict entry from memory cache based on strategy"""
        
        if not self.memory_cache:
            return
        
        if self.config.strategy == CacheStrategy.LRU:
            # Remove least recently used (first item in OrderedDict)
            key, entry = self.memory_cache.popitem(last=False)
        
        elif self.config.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            if self.access_frequencies:
                key = min(self.access_frequencies.keys(), 
                         key=lambda k: self.access_frequencies[k])
                entry = self.memory_cache.pop(key)
                del self.access_frequencies[key]
            else:
                key, entry = self.memory_cache.popitem(last=False)
        
        elif self.config.strategy == CacheStrategy.TTL:
            # Remove expired entries first, then oldest
            current_time = time.time()
            expired_keys = [
                k for k, v in self.memory_cache.items() 
                if v.is_expired()
            ]
            
            if expired_keys:
                key = expired_keys[0]
                entry = self.memory_cache.pop(key)
            else:
                key, entry = self.memory_cache.popitem(last=False)
        
        elif self.config.strategy == CacheStrategy.ADAPTIVE:
            # Adaptive strategy based on access patterns and content type
            key = self._select_adaptive_eviction_candidate()
            entry = self.memory_cache.pop(key)
        
        else:  # Default to LRU
            key, entry = self.memory_cache.popitem(last=False)
        
        self.logger.debug(f"Evicted cache entry: {key[:20]}...")
    
    def _select_adaptive_eviction_candidate(self) -> str:
        """Select eviction candidate using adaptive strategy"""
        
        # Score entries based on multiple factors
        scores = {}
        current_time = time.time()
        
        for key, entry in self.memory_cache.items():
            score = 0.0
            
            # Age factor (older = higher score = more likely to evict)
            age = current_time - entry.created_time
            score += age / 86400  # Normalize by day
            
            # Access frequency factor (less frequent = higher score)
            frequency = self.access_frequencies.get(key, 1)
            score += 1.0 / frequency
            
            # Recency factor (less recent = higher score)
            recency = current_time - entry.last_accessed
            score += recency / 3600  # Normalize by hour
            
            # Content type factor (some content types are more valuable)
            if entry.content_type == ContentType.DEFINITION:
                score -= 0.5  # Keep definitions longer
            elif entry.content_type == ContentType.MATH:
                score -= 0.3  # Keep math content longer
            
            # Quality factor (lower quality = higher score)
            score += (1.0 - entry.quality_score)
            
            scores[key] = score
        
        # Return key with highest score (most suitable for eviction)
        return max(scores.keys(), key=lambda k: scores[k])
    
    def _generate_key(self, text: str, model: EmbeddingModel, content_type: ContentType) -> str:
        """Generate cache key for text, model, and content type"""
        content = f"{text}||{model.value}||{content_type.value}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _calculate_memory_usage(self) -> float:
        """Calculate approximate memory usage in MB"""
        total_bytes = 0
        
        for entry in self.memory_cache.values():
            # Embedding size
            total_bytes += entry.embedding.nbytes
            
            # Metadata size (rough estimate)
            total_bytes += len(str(entry.metadata)) * 4  # Assume 4 bytes per character
        
        return total_bytes / (1024 * 1024)  # Convert to MB
    
    def _start_background_cleanup(self):
        """Start background cleanup thread"""
        
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.config.cleanup_interval)
                    self.cleanup()
                except Exception as e:
                    self.logger.error(f"Error in background cleanup: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        
        self.logger.info("Background cleanup thread started")
    
    def cleanup(self):
        """Perform cache cleanup operations"""
        
        with self._lock if self._lock else self._dummy_context():
            initial_size = len(self.memory_cache)
            
            # Remove expired entries from memory cache
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.memory_cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
                if key in self.access_frequencies:
                    del self.access_frequencies[key]
            
            # Cleanup persistent cache if enabled
            persistent_cleaned = 0
            if self.persistent_cache:
                persistent_cleaned = self.persistent_cache.cleanup_expired()
            
            memory_cleaned = len(expired_keys)
            total_cleaned = memory_cleaned + persistent_cleaned
            
            if total_cleaned > 0:
                self.stats.cleanup_operations += 1
                self.logger.info(f"Cleanup completed: removed {memory_cleaned} from memory, "
                               f"{persistent_cleaned} from persistent cache")
            
            # Update statistics
            self.stats.cache_size = len(self.memory_cache)
            self.stats.memory_usage_mb = self._calculate_memory_usage()
    
    def clear(self):
        """Clear all cache entries"""
        
        with self._lock if self._lock else self._dummy_context():
            self.memory_cache.clear()
            self.access_frequencies.clear()
            
            if self.persistent_cache:
                # Clear persistent cache (would need to implement in PersistentCache)
                pass
            
            self.stats.cache_size = 0
            self.stats.memory_usage_mb = 0.0
            
            self.logger.info("Cache cleared")
    
    def get_statistics(self) -> CacheStatistics:
        """Get comprehensive cache statistics"""
        
        # Update current statistics
        self.stats.cache_size = len(self.memory_cache)
        self.stats.memory_usage_mb = self._calculate_memory_usage()
        
        # Add persistent cache statistics if available
        if self.persistent_cache:
            persistent_stats = self.persistent_cache.get_statistics()
            # Would merge with self.stats
        
        return self.stats
    
    def export_cache_info(self) -> Dict[str, Any]:
        """Export comprehensive cache information"""
        
        info = {
            'config': asdict(self.config),
            'statistics': asdict(self.get_statistics()),
            'memory_cache_size': len(self.memory_cache),
            'access_frequencies': dict(self.access_frequencies),
            'content_type_distribution': self._get_content_type_distribution(),
            'model_distribution': self._get_model_distribution(),
            'quality_distribution': self._get_quality_distribution()
        }
        
        return info
    
    def _get_content_type_distribution(self) -> Dict[str, int]:
        """Get distribution of content types in cache"""
        distribution = defaultdict(int)
        for entry in self.memory_cache.values():
            distribution[entry.content_type.value] += 1
        return dict(distribution)
    
    def _get_model_distribution(self) -> Dict[str, int]:
        """Get distribution of models in cache"""
        distribution = defaultdict(int)
        for entry in self.memory_cache.values():
            distribution[entry.model.value] += 1
        return dict(distribution)
    
    def _get_quality_distribution(self) -> Dict[str, int]:
        """Get distribution of quality scores in cache"""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        for entry in self.memory_cache.values():
            if entry.quality_score >= 0.8:
                distribution['high'] += 1
            elif entry.quality_score >= 0.6:
                distribution['medium'] += 1
            else:
                distribution['low'] += 1
        return distribution
    
    def _dummy_context(self):
        """Dummy context manager for when thread safety is disabled"""
        class DummyContext:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        return DummyContext()


# Utility functions

def create_educational_cache_config() -> CacheConfig:
    """Create cache configuration optimized for educational content"""
    
    return CacheConfig(
        strategy=CacheStrategy.CONTENT_AWARE,
        max_size=50000,
        max_memory_mb=512,
        content_type_ttl={
            ContentType.DEFINITION: 86400 * 14,  # 2 weeks for definitions
            ContentType.MATH: 86400 * 7,         # 1 week for math
            ContentType.EXAMPLE: 86400 * 10,     # 10 days for examples
            ContentType.TEXT: 86400 * 3          # 3 days for general text
        },
        enable_persistence=True,
        compression_type=CompressionType.GZIP,
        enable_optimization=True,
        optimization_techniques=[
            OptimizationTechnique.NORMALIZATION,
            OptimizationTechnique.DEDUPLICATION,
            OptimizationTechnique.QUANTIZATION
        ],
        enable_background_cleanup=True,
        cleanup_interval=1800,  # 30 minutes
        thread_safe=True
    )


def create_high_performance_cache_config() -> CacheConfig:
    """Create cache configuration optimized for high performance"""
    
    return CacheConfig(
        strategy=CacheStrategy.LRU,
        max_size=100000,
        max_memory_mb=1024,
        enable_persistence=False,  # Disable for maximum speed  
        compression_type=CompressionType.NONE,
        enable_optimization=False,
        enable_background_cleanup=False,
        thread_safe=True
    )


def create_memory_efficient_cache_config() -> CacheConfig:
    """Create cache configuration optimized for memory efficiency"""
    
    return CacheConfig(
        strategy=CacheStrategy.ADAPTIVE,
        max_size=20000,
        max_memory_mb=256,
        enable_persistence=True,
        compression_type=CompressionType.QUANTIZATION_8BIT,
        enable_optimization=True,
        optimization_techniques=[
            OptimizationTechnique.DIMENSIONALITY_REDUCTION,
            OptimizationTechnique.QUANTIZATION,
            OptimizationTechnique.NORMALIZATION
        ],
        enable_background_cleanup=True,
        cleanup_interval=900,  # 15 minutes
        thread_safe=True
    )