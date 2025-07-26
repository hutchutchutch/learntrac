#!/usr/bin/env python3
"""
Comprehensive Tests for AdvancedEmbeddingCache - Advanced caching and optimization testing

Tests all functionality of the AdvancedEmbeddingCache including:
- Multiple caching strategies (LRU, LFU, TTL, adaptive, content-aware)
- Persistent storage with SQLite
- Embedding optimization techniques
- Background cleanup and maintenance
- Thread-safe operations
- Performance metrics and statistics
"""

import unittest
import numpy as np
import time
import tempfile
import threading
import os
import shutil
from unittest.mock import Mock, patch, MagicMock

from embedding_cache import (
    AdvancedEmbeddingCache, CacheConfig, CacheEntry, CacheStatistics,
    CacheStrategy, CompressionType, OptimizationTechnique,
    EmbeddingOptimizer, PersistentCache,
    create_educational_cache_config, create_high_performance_cache_config,
    create_memory_efficient_cache_config
)
from embedding_generator import EmbeddingResult, EmbeddingModel
from chunk_metadata import ChunkMetadata, ContentType


class TestCacheStrategy(unittest.TestCase):
    """Test CacheStrategy enum"""
    
    def test_cache_strategy_values(self):
        """Test cache strategy enum values"""
        self.assertEqual(CacheStrategy.LRU.value, "lru")
        self.assertEqual(CacheStrategy.LFU.value, "lfu")
        self.assertEqual(CacheStrategy.TTL.value, "ttl")
        self.assertEqual(CacheStrategy.ADAPTIVE.value, "adaptive")
        self.assertEqual(CacheStrategy.CONTENT_AWARE.value, "content_aware")


class TestCompressionType(unittest.TestCase):
    """Test CompressionType enum"""
    
    def test_compression_type_values(self):
        """Test compression type enum values"""
        self.assertEqual(CompressionType.NONE.value, "none")
        self.assertEqual(CompressionType.GZIP.value, "gzip")
        self.assertEqual(CompressionType.QUANTIZATION_8BIT.value, "quantization_8bit")
        self.assertEqual(CompressionType.QUANTIZATION_4BIT.value, "quantization_4bit")
        self.assertEqual(CompressionType.PCA_REDUCTION.value, "pca_reduction")


class TestOptimizationTechnique(unittest.TestCase):
    """Test OptimizationTechnique enum"""
    
    def test_optimization_technique_values(self):
        """Test optimization technique enum values"""
        self.assertEqual(OptimizationTechnique.NORMALIZATION.value, "normalization")
        self.assertEqual(OptimizationTechnique.DIMENSIONALITY_REDUCTION.value, "dimensionality_reduction")
        self.assertEqual(OptimizationTechnique.DEDUPLICATION.value, "deduplication")
        self.assertEqual(OptimizationTechnique.QUANTIZATION.value, "quantization")
        self.assertEqual(OptimizationTechnique.CLUSTERING.value, "clustering")


class TestCacheConfig(unittest.TestCase):
    """Test CacheConfig data structure"""
    
    def test_config_creation(self):
        """Test creating cache configuration"""
        config = CacheConfig(
            strategy=CacheStrategy.LRU,
            max_size=50000,
            max_memory_mb=512,
            default_ttl=3600,
            enable_persistence=True,
            compression_type=CompressionType.GZIP,
            enable_optimization=True
        )
        
        self.assertEqual(config.strategy, CacheStrategy.LRU)
        self.assertEqual(config.max_size, 50000)
        self.assertEqual(config.max_memory_mb, 512)
        self.assertEqual(config.default_ttl, 3600)
        self.assertTrue(config.enable_persistence)
        self.assertEqual(config.compression_type, CompressionType.GZIP)
        self.assertTrue(config.enable_optimization)
    
    def test_config_defaults(self):
        """Test configuration defaults"""
        config = CacheConfig()
        
        self.assertEqual(config.strategy, CacheStrategy.ADAPTIVE)
        self.assertEqual(config.max_size, 100000)
        self.assertEqual(config.max_memory_mb, 1024)
        self.assertEqual(config.default_ttl, 86400)  # 24 hours
        self.assertTrue(config.enable_persistence)
        self.assertEqual(config.compression_type, CompressionType.GZIP)
        self.assertTrue(config.enable_optimization)
        
        # Check default content type TTLs
        self.assertIn(ContentType.DEFINITION, config.content_type_ttl)
        self.assertIn(ContentType.MATH, config.content_type_ttl)
        self.assertIn(ContentType.EXAMPLE, config.content_type_ttl)
        self.assertIn(ContentType.TEXT, config.content_type_ttl)


class TestCacheEntry(unittest.TestCase):
    """Test CacheEntry data structure"""
    
    def setUp(self):
        """Set up test cache entry"""
        self.embedding = np.random.rand(768).astype(np.float32)
        self.entry = CacheEntry(
            key="test_key",
            embedding=self.embedding,
            metadata={"test": "metadata"},
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            content_type=ContentType.TEXT,
            created_time=time.time(),
            last_accessed=time.time(),
            access_count=1,
            ttl=3600,
            quality_score=0.8,
            generation_time=0.1
        )
    
    def test_cache_entry_creation(self):
        """Test creating cache entry"""
        self.assertEqual(self.entry.key, "test_key")
        self.assertEqual(self.entry.model, EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET)
        self.assertEqual(self.entry.content_type, ContentType.TEXT)
        self.assertEqual(self.entry.ttl, 3600)
        self.assertEqual(self.entry.quality_score, 0.8)
        np.testing.assert_array_equal(self.entry.embedding, self.embedding)
    
    def test_expiration_check(self):
        """Test TTL expiration checking"""
        # Entry with short TTL that should expire
        expired_entry = CacheEntry(
            key="expired_key",
            embedding=self.embedding,
            metadata={},
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            content_type=ContentType.TEXT,
            created_time=time.time() - 7200,  # 2 hours ago
            last_accessed=time.time(),
            access_count=1,
            ttl=3600  # 1 hour TTL
        )
        
        self.assertTrue(expired_entry.is_expired())
        
        # Entry with no TTL should never expire
        no_ttl_entry = CacheEntry(
            key="no_ttl_key",
            embedding=self.embedding,
            metadata={},
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            content_type=ContentType.TEXT,
            created_time=time.time() - 86400,  # 1 day ago
            last_accessed=time.time(),
            access_count=1,
            ttl=None
        )
        
        self.assertFalse(no_ttl_entry.is_expired())
    
    def test_access_update(self):
        """Test access metadata update"""
        initial_time = self.entry.last_accessed
        initial_count = self.entry.access_count
        
        time.sleep(0.01)  # Small delay
        self.entry.update_access()
        
        self.assertGreater(self.entry.last_accessed, initial_time)
        self.assertEqual(self.entry.access_count, initial_count + 1)


class TestEmbeddingOptimizer(unittest.TestCase):
    """Test EmbeddingOptimizer functionality"""
    
    def setUp(self):
        """Set up test optimizer"""
        self.optimizer = EmbeddingOptimizer()
        self.test_embedding = np.random.rand(768).astype(np.float32) * 2 - 1  # Range [-1, 1]
    
    def test_normalization_optimization(self):
        """Test embedding normalization"""
        techniques = [OptimizationTechnique.NORMALIZATION]
        
        optimized, metadata = self.optimizer.optimize_embedding(
            self.test_embedding, techniques, ContentType.TEXT
        )
        
        # Should be normalized to unit length
        norm = np.linalg.norm(optimized)
        self.assertAlmostEqual(norm, 1.0, places=5)
        
        # Check metadata
        self.assertIn('normalization', metadata['applied_techniques'])
        self.assertIn('normalization', metadata['improvements'])
    
    def test_dimensionality_reduction_optimization(self):
        """Test dimensionality reduction"""
        techniques = [OptimizationTechnique.DIMENSIONALITY_REDUCTION]
        
        original_dims = len(self.test_embedding)
        optimized, metadata = self.optimizer.optimize_embedding(
            self.test_embedding, techniques, ContentType.TEXT
        )
        
        # Should have fewer dimensions
        self.assertLess(len(optimized), original_dims)
        
        # Check metadata
        self.assertIn('dimensionality_reduction', metadata['applied_techniques'])
        self.assertIn('dimensionality_reduction', metadata['improvements'])
        
        # Retention ratio should be reasonable
        retention = metadata['improvements']['dimensionality_reduction']
        self.assertGreaterEqual(retention, 0.0)
        self.assertLessEqual(retention, 1.0)
    
    def test_quantization_optimization(self):
        """Test embedding quantization"""
        techniques = [OptimizationTechnique.QUANTIZATION]
        
        optimized, metadata = self.optimizer.optimize_embedding(
            self.test_embedding, techniques, ContentType.TEXT
        )
        
        # Should have same dimensions
        self.assertEqual(len(optimized), len(self.test_embedding))
        
        # Check metadata
        self.assertIn('quantization', metadata['applied_techniques'])
        self.assertIn('quantization', metadata['improvements'])
        
        # Compression ratio should be reasonable
        compression = metadata['improvements']['quantization']
        self.assertGreaterEqual(compression, 0.0)
        self.assertLessEqual(compression, 1.0)
    
    def test_multiple_optimizations(self):
        """Test applying multiple optimization techniques"""
        techniques = [
            OptimizationTechnique.NORMALIZATION,
            OptimizationTechnique.QUANTIZATION
        ]
        
        optimized, metadata = self.optimizer.optimize_embedding(
            self.test_embedding, techniques, ContentType.MATH
        )
        
        # Should have applied both techniques
        self.assertEqual(len(metadata['applied_techniques']), 2)
        self.assertIn('normalization', metadata['applied_techniques'])
        self.assertIn('quantization', metadata['applied_techniques'])
        
        # Should have improvements for both
        self.assertIn('normalization', metadata['improvements'])
        self.assertIn('quantization', metadata['improvements'])
    
    def test_zero_embedding_handling(self):
        """Test handling of zero embedding"""
        zero_embedding = np.zeros(768, dtype=np.float32)
        techniques = [OptimizationTechnique.NORMALIZATION]
        
        optimized, metadata = self.optimizer.optimize_embedding(
            zero_embedding, techniques, ContentType.TEXT
        )
        
        # Should handle zero embedding gracefully
        self.assertEqual(len(optimized), len(zero_embedding))
        # May remain zero or be handled specially
        self.assertIn('normalization', metadata['applied_techniques'])


class TestPersistentCache(unittest.TestCase):
    """Test PersistentCache functionality"""
    
    def setUp(self):
        """Set up test persistent cache"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = PersistentCache(self.temp_dir, "test_embeddings.db")
        
        # Create test entry
        self.test_embedding = np.random.rand(768).astype(np.float32)
        self.test_entry = CacheEntry(
            key="test_persistent",
            embedding=self.test_embedding,
            metadata={"test": "persistent"},
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            content_type=ContentType.TEXT,
            created_time=time.time(),
            last_accessed=time.time(),
            access_count=1,
            ttl=3600,
            quality_score=0.8,
            generation_time=0.1
        )
    
    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_initialization(self):
        """Test persistent cache initialization"""
        # Database file should be created
        db_path = os.path.join(self.temp_dir, "test_embeddings.db")
        self.assertTrue(os.path.exists(db_path))
    
    def test_store_and_load_entry(self):
        """Test storing and loading cache entry"""
        # Store entry
        self.cache.store(self.test_entry)
        
        # Load entry
        loaded_entry = self.cache.load("test_persistent")
        
        self.assertIsNotNone(loaded_entry)
        self.assertEqual(loaded_entry.key, "test_persistent")
        self.assertEqual(loaded_entry.model, EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET)
        self.assertEqual(loaded_entry.content_type, ContentType.TEXT)
        np.testing.assert_array_equal(loaded_entry.embedding, self.test_embedding)
    
    def test_load_nonexistent_entry(self):
        """Test loading nonexistent entry"""
        loaded_entry = self.cache.load("nonexistent_key")
        self.assertIsNone(loaded_entry)
    
    def test_update_access_statistics(self):
        """Test updating access statistics"""
        # Store entry
        self.cache.store(self.test_entry)
        
        original_count = self.test_entry.access_count
        
        # Update access
        self.cache.update_access("test_persistent")
        
        # Load and verify
        loaded_entry = self.cache.load("test_persistent")
        self.assertEqual(loaded_entry.access_count, original_count + 1)
        self.assertGreater(loaded_entry.last_accessed, self.test_entry.last_accessed)
    
    def test_delete_entry(self):
        """Test deleting cache entry"""
        # Store entry
        self.cache.store(self.test_entry)
        
        # Verify it exists
        loaded_entry = self.cache.load("test_persistent")
        self.assertIsNotNone(loaded_entry)
        
        # Delete entry
        self.cache.delete("test_persistent")
        
        # Verify it's gone
        loaded_entry = self.cache.load("test_persistent")
        self.assertIsNone(loaded_entry)
    
    def test_cleanup_expired_entries(self):
        """Test cleaning up expired entries"""
        # Create expired entry
        expired_entry = CacheEntry(
            key="expired_entry",
            embedding=self.test_embedding,
            metadata={},
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            content_type=ContentType.TEXT,
            created_time=time.time() - 7200,  # 2 hours ago
            last_accessed=time.time(),
            access_count=1,
            ttl=3600  # 1 hour TTL
        )
        
        # Store both entries
        self.cache.store(self.test_entry)  # Not expired
        self.cache.store(expired_entry)  # Expired
        
        # Cleanup expired entries
        removed_count = self.cache.cleanup_expired()
        
        # Should have removed one entry
        self.assertEqual(removed_count, 1)
        
        # Non-expired entry should still exist
        loaded_entry = self.cache.load("test_persistent")
        self.assertIsNotNone(loaded_entry)
        
        # Expired entry should be gone
        loaded_expired = self.cache.load("expired_entry")
        self.assertIsNone(loaded_expired)
    
    def test_statistics_retrieval(self):
        """Test retrieving cache statistics"""
        # Store some entries
        for i in range(3):
            entry = CacheEntry(
                key=f"stats_test_{i}",
                embedding=self.test_embedding,
                metadata={},
                model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
                content_type=ContentType.TEXT,
                created_time=time.time(),
                last_accessed=time.time(),
                access_count=1
            )
            self.cache.store(entry)
        
        stats = self.cache.get_statistics()
        
        self.assertIn('total_entries', stats)
        self.assertIn('model_distribution', stats)
        self.assertIn('content_type_distribution', stats)
        
        self.assertEqual(stats['total_entries'], 3)


class TestAdvancedEmbeddingCache(unittest.TestCase):
    """Test main AdvancedEmbeddingCache functionality"""
    
    def setUp(self):
        """Set up test cache"""
        self.temp_dir = tempfile.mkdtemp()
        
        config = CacheConfig(
            strategy=CacheStrategy.LRU,
            max_size=5,  # Small size for testing eviction
            cache_directory=self.temp_dir,
            enable_persistence=True,
            enable_optimization=True,
            thread_safe=True,
            enable_background_cleanup=False  # Disable for testing
        )
        
        self.cache = AdvancedEmbeddingCache(config)
        
        # Create test embedding result
        self.test_embedding = np.random.rand(768).astype(np.float32)
        self.embedding_result = EmbeddingResult(
            text="Test text for caching",
            embedding=self.test_embedding,
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            dimensions=768,
            generation_time=0.1,
            token_count=4,
            quality_score=0.8
        )
    
    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_initialization(self):
        """Test cache initialization"""
        self.assertIsNotNone(self.cache.config)
        self.assertIsNotNone(self.cache.memory_cache)
        self.assertIsNotNone(self.cache.persistent_cache)
        self.assertIsNotNone(self.cache.optimizer)
        self.assertIsNotNone(self.cache.stats)
    
    def test_put_and_get_operations(self):
        """Test basic put and get operations"""
        text = "Test caching functionality"
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        
        # Put embedding in cache
        self.cache.put(text, model, content_type, self.embedding_result)
        
        # Get embedding from cache
        cached_result = self.cache.get(text, model, content_type)
        
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.text, text)
        self.assertEqual(cached_result.model, model)
        np.testing.assert_array_equal(cached_result.embedding, self.embedding_result.embedding)
    
    def test_cache_miss(self):
        """Test cache miss behavior"""
        result = self.cache.get("nonexistent text", 
                                EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET, 
                                ContentType.TEXT)
        self.assertIsNone(result)
    
    def test_lru_eviction_strategy(self):
        """Test LRU eviction strategy"""
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        
        # Fill cache to capacity (max_size = 5)
        for i in range(5):
            text = f"Text {i}"
            embedding_result = EmbeddingResult(
                text=text,
                embedding=np.random.rand(768).astype(np.float32),
                model=model,
                dimensions=768,
                generation_time=0.1,
                token_count=2
            )
            self.cache.put(text, model, content_type, embedding_result)
        
        # All should be in cache
        for i in range(5):
            cached = self.cache.get(f"Text {i}", model, content_type)
            self.assertIsNotNone(cached)
        
        # Add one more to trigger eviction
        new_text = "Text 5"
        new_embedding = EmbeddingResult(
            text=new_text,
            embedding=np.random.rand(768).astype(np.float32),
            model=model,
            dimensions=768,
            generation_time=0.1,
            token_count=2
        )
        self.cache.put(new_text, model, content_type, new_embedding)
        
        # First entry should be evicted (LRU)
        evicted = self.cache.get("Text 0", model, content_type)
        self.assertIsNone(evicted)
        
        # New entry should be present
        new_cached = self.cache.get(new_text, model, content_type)
        self.assertIsNotNone(new_cached)
    
    def test_content_type_specific_ttl(self):
        """Test content-type specific TTL settings"""
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        
        # Cache with definition content type (longer TTL)
        definition_result = EmbeddingResult(
            text="Definition: A prime number...",
            embedding=self.test_embedding,
            model=model,
            dimensions=768,
            generation_time=0.1,
            token_count=5
        )
        
        self.cache.put("Definition: A prime number...", model, 
                      ContentType.DEFINITION, definition_result)
        
        # Cache with text content type (shorter TTL)
        text_result = EmbeddingResult(
            text="Regular text content",
            embedding=self.test_embedding,
            model=model,
            dimensions=768,
            generation_time=0.1,
            token_count=3
        )
        
        self.cache.put("Regular text content", model, 
                      ContentType.TEXT, text_result)
        
        # Both should be retrievable
        definition_cached = self.cache.get("Definition: A prime number...", 
                                         model, ContentType.DEFINITION)
        text_cached = self.cache.get("Regular text content", 
                                   model, ContentType.TEXT)
        
        self.assertIsNotNone(definition_cached)
        self.assertIsNotNone(text_cached)
    
    def test_optimization_integration(self):
        """Test embedding optimization integration"""
        config = CacheConfig(
            enable_optimization=True,
            optimization_techniques=[
                OptimizationTechnique.NORMALIZATION,
                OptimizationTechnique.QUANTIZATION
            ]
        )
        optimizing_cache = AdvancedEmbeddingCache(config)
        
        text = "Test optimization integration"
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        
        # Put embedding (should be optimized)
        optimizing_cache.put(text, model, content_type, self.embedding_result)
        
        # Get embedding back
        cached_result = optimizing_cache.get(text, model, content_type)
        
        self.assertIsNotNone(cached_result)
        # Embedding may be different due to optimization
        self.assertEqual(cached_result.text, text)
    
    def test_persistent_cache_integration(self):
        """Test integration with persistent cache"""
        text = "Test persistent integration"
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        
        # Put in cache
        self.cache.put(text, model, content_type, self.embedding_result)
        
        # Clear memory cache to force persistent lookup
        self.cache.memory_cache.clear()
        
        # Should still find in persistent cache
        cached_result = self.cache.get(text, model, content_type)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.text, text)
    
    def test_statistics_tracking(self):
        """Test cache statistics tracking"""
        initial_stats = self.cache.get_statistics()
        
        text = "Test statistics tracking"
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        
        # Generate cache miss
        self.cache.get("nonexistent", model, content_type)
        
        # Generate cache hit
        self.cache.put(text, model, content_type, self.embedding_result)
        self.cache.get(text, model, content_type)
        
        updated_stats = self.cache.get_statistics()
        
        # Statistics should be updated
        self.assertGreater(updated_stats.total_requests, initial_stats.total_requests)
        self.assertGreater(updated_stats.cache_hits, initial_stats.cache_hits)
        self.assertGreater(updated_stats.cache_misses, initial_stats.cache_misses)
    
    def test_cleanup_operations(self):
        """Test cache cleanup operations"""
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        
        # Add entries with short TTL
        config = CacheConfig(
            default_ttl=1,  # 1 second TTL
            enable_persistence=False  # Disable for simpler testing
        )
        short_ttl_cache = AdvancedEmbeddingCache(config)
        
        # Add entry
        short_ttl_cache.put("short lived", model, content_type, self.embedding_result)
        
        # Should be accessible immediately
        cached = short_ttl_cache.get("short lived", model, content_type)
        self.assertIsNotNone(cached)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Trigger cleanup
        short_ttl_cache.cleanup()
        
        # Should be gone after cleanup
        cached_after = short_ttl_cache.get("short lived", model, content_type)
        self.assertIsNone(cached_after)
    
    def test_cache_clear(self):
        """Test clearing all cache entries"""
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        
        # Add some entries
        self.cache.put("entry 1", model, content_type, self.embedding_result)
        self.cache.put("entry 2", model, content_type, self.embedding_result)
        
        # Verify they exist
        self.assertIsNotNone(self.cache.get("entry 1", model, content_type))
        self.assertIsNotNone(self.cache.get("entry 2", model, content_type))
        
        # Clear cache
        self.cache.clear()
        
        # Verify they're gone
        self.assertIsNone(self.cache.get("entry 1", model, content_type))
        self.assertIsNone(self.cache.get("entry 2", model, content_type))
        
        # Statistics should be reset
        stats = self.cache.get_statistics()
        self.assertEqual(stats.cache_size, 0)
        self.assertEqual(stats.memory_usage_mb, 0.0)
    
    def test_cache_export_info(self):
        """Test cache information export"""
        # Add some entries
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        self.cache.put("info test 1", model, ContentType.TEXT, self.embedding_result)
        self.cache.put("info test 2", model, ContentType.DEFINITION, self.embedding_result)
        
        # Export cache info
        cache_info = self.cache.export_cache_info()
        
        self.assertIn('config', cache_info)
        self.assertIn('statistics', cache_info)
        self.assertIn('memory_cache_size', cache_info)
        self.assertIn('content_type_distribution', cache_info)
        self.assertIn('model_distribution', cache_info)
        self.assertIn('quality_distribution', cache_info)
        
        # Check distributions
        self.assertGreater(cache_info['memory_cache_size'], 0)
        self.assertGreater(len(cache_info['content_type_distribution']), 0)
        self.assertGreater(len(cache_info['model_distribution']), 0)


class TestCacheStrategies(unittest.TestCase):
    """Test different caching strategies"""
    
    def setUp(self):
        """Set up strategy testing"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_cache_with_strategy(self, strategy: CacheStrategy) -> AdvancedEmbeddingCache:
        """Helper to create cache with specific strategy"""
        config = CacheConfig(
            strategy=strategy,
            max_size=3,  # Small for testing eviction
            cache_directory=self.temp_dir,
            enable_persistence=False,  # Disable for simpler testing
            enable_background_cleanup=False
        )
        return AdvancedEmbeddingCache(config)
    
    def test_lru_strategy(self):
        """Test LRU (Least Recently Used) strategy"""
        cache = self.create_cache_with_strategy(CacheStrategy.LRU)
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        
        # Add entries
        for i in range(3):
            embedding_result = EmbeddingResult(
                text=f"LRU test {i}",
                embedding=np.random.rand(768).astype(np.float32),
                model=model,
                dimensions=768,
                generation_time=0.1,
                token_count=3
            )
            cache.put(f"LRU test {i}", model, content_type, embedding_result)
        
        # Access first entry to make it recently used
        cache.get("LRU test 0", model, content_type)
        
        # Add new entry to trigger eviction
        new_embedding = EmbeddingResult(
            text="LRU test 3",
            embedding=np.random.rand(768).astype(np.float32),
            model=model,
            dimensions=768,
            generation_time=0.1,
            token_count=3
        )
        cache.put("LRU test 3", model, content_type, new_embedding)
        
        # Entry 1 should be evicted (least recently used)
        # Entry 0 should still exist (was accessed recently)
        self.assertIsNotNone(cache.get("LRU test 0", model, content_type))
        self.assertIsNone(cache.get("LRU test 1", model, content_type))
    
    def test_adaptive_strategy(self):
        """Test adaptive caching strategy"""
        cache = self.create_cache_with_strategy(CacheStrategy.ADAPTIVE)
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        
        # Add entries with different content types (affects adaptive scoring)
        definition_result = EmbeddingResult(
            text="Definition content",
            embedding=np.random.rand(768).astype(np.float32),
            model=model,
            dimensions=768,
            generation_time=0.1,
            token_count=2,
            quality_score=0.9  # High quality
        )
        
        text_result = EmbeddingResult(
            text="Regular text content",
            embedding=np.random.rand(768).astype(np.float32),
            model=model,
            dimensions=768,
            generation_time=0.1,
            token_count=3,
            quality_score=0.5  # Lower quality
        )
        
        cache.put("Definition content", model, ContentType.DEFINITION, definition_result)
        cache.put("Regular text content", model, ContentType.TEXT, text_result)
        
        # Both should be accessible
        self.assertIsNotNone(cache.get("Definition content", model, ContentType.DEFINITION))
        self.assertIsNotNone(cache.get("Regular text content", model, ContentType.TEXT))


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of cache operations"""
    
    def setUp(self):
        """Set up thread safety testing"""
        self.temp_dir = tempfile.mkdtemp()
        config = CacheConfig(
            cache_directory=self.temp_dir,
            thread_safe=True,
            enable_persistence=False  # Simpler for testing
        )
        self.cache = AdvancedEmbeddingCache(config)
    
    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_concurrent_put_operations(self):
        """Test concurrent put operations"""
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        num_threads = 5
        items_per_thread = 10
        
        def put_items(thread_id):
            for i in range(items_per_thread):
                text = f"thread_{thread_id}_item_{i}"
                embedding_result = EmbeddingResult(
                    text=text,
                    embedding=np.random.rand(768).astype(np.float32),
                    model=model,
                    dimensions=768,
                    generation_time=0.1,
                    token_count=len(text.split())
                )
                self.cache.put(text, model, content_type, embedding_result)
        
        # Create and start threads
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=put_items, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify some items were cached (exact count depends on eviction)
        stats = self.cache.get_statistics()
        self.assertGreater(stats.cache_size, 0)
        self.assertLessEqual(stats.cache_size, self.cache.config.max_size)
    
    def test_concurrent_get_operations(self):
        """Test concurrent get operations"""
        model = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET
        content_type = ContentType.TEXT
        
        # Pre-populate cache
        test_items = []
        for i in range(10):
            text = f"concurrent_get_test_{i}"
            embedding_result = EmbeddingResult(
                text=text,
                embedding=np.random.rand(768).astype(np.float32),
                model=model,
                dimensions=768,
                generation_time=0.1,
                token_count=3
            )
            self.cache.put(text, model, content_type, embedding_result)
            test_items.append(text)
        
        results = []
        
        def get_items():
            thread_results = []
            for text in test_items:
                result = self.cache.get(text, model, content_type)
                thread_results.append(result is not None)
            results.extend(thread_results)
        
        # Create and start threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_items)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Most get operations should succeed
        success_rate = sum(results) / len(results)
        self.assertGreater(success_rate, 0.5)  # At least 50% success


class TestUtilityConfigurations(unittest.TestCase):
    """Test utility configuration functions"""
    
    def test_educational_cache_config(self):
        """Test educational cache configuration"""
        config = create_educational_cache_config()
        
        self.assertEqual(config.strategy, CacheStrategy.CONTENT_AWARE)
        self.assertEqual(config.max_size, 50000)
        self.assertEqual(config.max_memory_mb, 512)
        self.assertTrue(config.enable_persistence)
        self.assertEqual(config.compression_type, CompressionType.GZIP)
        self.assertTrue(config.enable_optimization)
        
        # Check educational-specific TTLs
        self.assertEqual(config.content_type_ttl[ContentType.DEFINITION], 86400 * 14)  # 2 weeks
        self.assertEqual(config.content_type_ttl[ContentType.MATH], 86400 * 7)  # 1 week
        
        # Check optimization techniques
        self.assertIn(OptimizationTechnique.NORMALIZATION, config.optimization_techniques)
        self.assertIn(OptimizationTechnique.DEDUPLICATION, config.optimization_techniques)
        self.assertIn(OptimizationTechnique.QUANTIZATION, config.optimization_techniques)
    
    def test_high_performance_cache_config(self):
        """Test high-performance cache configuration"""
        config = create_high_performance_cache_config()
        
        self.assertEqual(config.strategy, CacheStrategy.LRU)
        self.assertEqual(config.max_size, 100000)
        self.assertEqual(config.max_memory_mb, 1024)
        self.assertFalse(config.enable_persistence)  # Disabled for speed
        self.assertEqual(config.compression_type, CompressionType.NONE)
        self.assertFalse(config.enable_optimization)
        self.assertFalse(config.enable_background_cleanup)
    
    def test_memory_efficient_cache_config(self):
        """Test memory-efficient cache configuration"""
        config = create_memory_efficient_cache_config()
        
        self.assertEqual(config.strategy, CacheStrategy.ADAPTIVE)
        self.assertEqual(config.max_size, 20000)  # Smaller cache
        self.assertEqual(config.max_memory_mb, 256)  # Less memory
        self.assertTrue(config.enable_persistence)
        self.assertEqual(config.compression_type, CompressionType.QUANTIZATION_8BIT)
        self.assertTrue(config.enable_optimization)
        
        # Check memory-focused optimizations
        self.assertIn(OptimizationTechnique.DIMENSIONALITY_REDUCTION, config.optimization_techniques)
        self.assertIn(OptimizationTechnique.QUANTIZATION, config.optimization_techniques)
        self.assertIn(OptimizationTechnique.NORMALIZATION, config.optimization_techniques)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestCacheStrategy,
        TestCompressionType,
        TestOptimizationTechnique,
        TestCacheConfig,
        TestCacheEntry,
        TestEmbeddingOptimizer,
        TestPersistentCache,
        TestAdvancedEmbeddingCache,
        TestCacheStrategies,
        TestThreadSafety,
        TestUtilityConfigurations
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"AdvancedEmbeddingCache Test Summary")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('\\n')[-2]}")
    
    print(f"\n🎯 AdvancedEmbeddingCache testing completed!")