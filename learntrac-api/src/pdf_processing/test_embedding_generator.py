#!/usr/bin/env python3
"""
Comprehensive Tests for EmbeddingGenerator - Multi-model embedding generation testing

Tests all functionality of the EmbeddingGenerator including:
- Multi-model embedding generation 
- Caching mechanisms
- Batch processing
- Error handling and retries
- Performance statistics
- Quality assessment integration
"""

import unittest
import numpy as np
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from embedding_generator import (
    EmbeddingGenerator, EmbeddingConfig, EmbeddingResult, BatchEmbeddingResult,
    EmbeddingModel, EmbeddingCache, MockEmbeddingProvider,
    create_educational_config, create_mathematical_config,
    calculate_embedding_similarity
)


class TestEmbeddingModel(unittest.TestCase):
    """Test EmbeddingModel enum and configurations"""
    
    def test_model_enum_values(self):
        """Test all embedding models are defined"""
        expected_models = [
            "text-embedding-ada-002",
            "text-embedding-3-small", 
            "text-embedding-3-large",
            "sentence-transformers/all-MiniLM-L6-v2",
            "sentence-transformers/all-mpnet-base-v2",
            "embed-english-v3.0",
            "embed-multilingual-v3.0",
            "hkunlp/instructor-large"
        ]
        
        actual_models = [model.value for model in EmbeddingModel]
        
        for expected in expected_models:
            self.assertIn(expected, actual_models)
    
    def test_model_dimensions_mapping(self):
        """Test that all models have proper dimension mappings"""
        provider = MockEmbeddingProvider(EmbeddingModel.OPENAI_3_LARGE)
        self.assertEqual(provider.dimensions, 3072)
        
        provider = MockEmbeddingProvider(EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM)
        self.assertEqual(provider.dimensions, 384)
        
        provider = MockEmbeddingProvider(EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET)
        self.assertEqual(provider.dimensions, 768)


class TestEmbeddingConfig(unittest.TestCase):
    """Test EmbeddingConfig data structure"""
    
    def test_config_creation(self):
        """Test creating embedding configuration"""
        config = EmbeddingConfig(
            model=EmbeddingModel.OPENAI_3_SMALL,
            dimensions=1536,
            max_tokens=512,
            batch_size=10,
            normalize=True,
            cache_embeddings=True
        )
        
        self.assertEqual(config.model, EmbeddingModel.OPENAI_3_SMALL)
        self.assertEqual(config.dimensions, 1536)
        self.assertEqual(config.max_tokens, 512)
        self.assertEqual(config.batch_size, 10)
        self.assertTrue(config.normalize)
        self.assertTrue(config.cache_embeddings)
    
    def test_config_defaults(self):
        """Test configuration defaults"""
        config = EmbeddingConfig(
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM,
            dimensions=384,
            max_tokens=512
        )
        
        self.assertEqual(config.batch_size, 10)  # Default batch size
        self.assertTrue(config.normalize)  # Default normalize
        self.assertTrue(config.cache_embeddings)  # Default caching


class TestEmbeddingCache(unittest.TestCase):
    """Test embedding caching functionality"""
    
    def setUp(self):
        """Set up test cache"""
        self.cache = EmbeddingCache(max_size=3)
        self.model = EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM
    
    def test_cache_put_and_get(self):
        """Test basic cache operations"""
        # Create test result
        embedding = np.random.rand(384).astype(np.float32)
        result = EmbeddingResult(
            text="test text",
            embedding=embedding,
            model=self.model,
            dimensions=384,
            generation_time=0.1,
            token_count=2
        )
        
        # Store in cache
        self.cache.put("test text", self.model, result)
        
        # Retrieve from cache
        cached_result = self.cache.get("test text", self.model)
        
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.text, "test text")
        self.assertEqual(cached_result.model, self.model)
        np.testing.assert_array_equal(cached_result.embedding, embedding)
    
    def test_cache_miss(self):
        """Test cache miss behavior"""
        result = self.cache.get("nonexistent text", self.model)
        self.assertIsNone(result)
    
    def test_cache_eviction(self):
        """Test LRU cache eviction"""
        # Fill cache to capacity
        for i in range(3):
            embedding = np.random.rand(384).astype(np.float32)
            result = EmbeddingResult(
                text=f"text {i}",
                embedding=embedding,
                model=self.model,
                dimensions=384,
                generation_time=0.1,
                token_count=2
            )
            self.cache.put(f"text {i}", self.model, result)
        
        # Verify all are cached
        for i in range(3):
            self.assertIsNotNone(self.cache.get(f"text {i}", self.model))
        
        # Add one more to trigger eviction
        embedding = np.random.rand(384).astype(np.float32)
        result = EmbeddingResult(
            text="text 3",
            embedding=embedding,
            model=self.model,
            dimensions=384,
            generation_time=0.1,
            token_count=2
        )
        self.cache.put("text 3", self.model, result)
        
        # First item should be evicted
        self.assertIsNone(self.cache.get("text 0", self.model))
        self.assertIsNotNone(self.cache.get("text 3", self.model))
    
    def test_cache_size_tracking(self):
        """Test cache size tracking"""
        self.assertEqual(self.cache.size(), 0)
        
        embedding = np.random.rand(384).astype(np.float32)
        result = EmbeddingResult(
            text="test",
            embedding=embedding,
            model=self.model,
            dimensions=384,
            generation_time=0.1,
            token_count=2
        )
        
        self.cache.put("test", self.model, result)
        self.assertEqual(self.cache.size(), 1)
        
        self.cache.clear()
        self.assertEqual(self.cache.size(), 0)


class TestMockEmbeddingProvider(unittest.TestCase):
    """Test mock embedding provider"""
    
    def test_provider_initialization(self):
        """Test provider initialization with different models"""
        provider = MockEmbeddingProvider(EmbeddingModel.OPENAI_3_LARGE)
        self.assertEqual(provider.model, EmbeddingModel.OPENAI_3_LARGE)
        self.assertEqual(provider.dimensions, 3072)
        
        provider = MockEmbeddingProvider(EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM)
        self.assertEqual(provider.dimensions, 384)
    
    def test_deterministic_embeddings(self):
        """Test that embeddings are deterministic for same text"""
        provider = MockEmbeddingProvider(EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM)
        
        text = "This is a test sentence."
        
        # Generate embedding twice
        emb1, tokens1 = provider.generate_embedding(text)
        emb2, tokens2 = provider.generate_embedding(text)
        
        # Should be identical
        np.testing.assert_array_equal(emb1, emb2)
        self.assertEqual(tokens1, tokens2)
    
    def test_different_embeddings_for_different_text(self):
        """Test that different texts produce different embeddings"""
        provider = MockEmbeddingProvider(EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM)
        
        emb1, _ = provider.generate_embedding("First text")
        emb2, _ = provider.generate_embedding("Second text")
        
        # Should be different
        self.assertFalse(np.array_equal(emb1, emb2))
    
    def test_content_type_signals(self):
        """Test that content type affects embedding generation"""
        provider = MockEmbeddingProvider(EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM)
        
        # Test definition signal
        def_emb, _ = provider.generate_embedding("Definition: A triangle is a polygon")
        regular_emb, _ = provider.generate_embedding("A triangle is a polygon")
        
        # Definition should have higher values in first 10 dimensions
        self.assertGreater(np.mean(def_emb[0:10]), np.mean(regular_emb[0:10]))
        
        # Test mathematical content signal
        math_emb, _ = provider.generate_embedding("∫ x² dx = x³/3 + C")
        text_emb, _ = provider.generate_embedding("This is regular text")
        
        # Math should have higher values in dimensions 20-30
        self.assertGreater(np.mean(math_emb[20:30]), np.mean(text_emb[20:30]))
    
    def test_normalized_embeddings(self):
        """Test that embeddings are normalized"""
        provider = MockEmbeddingProvider(EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM)
        
        embedding, _ = provider.generate_embedding("Test text")
        norm = np.linalg.norm(embedding)
        
        # Should be approximately unit length
        self.assertAlmostEqual(norm, 1.0, places=5)


class TestEmbeddingGenerator(unittest.TestCase):
    """Test main EmbeddingGenerator functionality"""
    
    def setUp(self):
        """Set up test generator"""
        config = EmbeddingConfig(
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM,
            dimensions=384,
            max_tokens=512,
            batch_size=5
        )
        self.generator = EmbeddingGenerator(
            default_config=config,
            enable_cache=True,
            cache_size=100,
            max_workers=2
        )
    
    def test_generator_initialization(self):
        """Test generator initialization"""
        self.assertIsNotNone(self.generator.default_config)
        self.assertIsNotNone(self.generator.cache)
        self.assertEqual(self.generator.max_workers, 2)
        self.assertIsNotNone(self.generator.providers)
        
        # Check all models have providers
        for model in EmbeddingModel:
            self.assertIn(model, self.generator.providers)
    
    def test_single_embedding_generation(self):
        """Test generating single embedding"""
        text = "This is a test sentence for embedding generation."
        
        result = self.generator.generate_embedding(text)
        
        self.assertIsInstance(result, EmbeddingResult)
        self.assertEqual(result.text, text)
        self.assertEqual(result.model, self.generator.default_config.model)
        self.assertEqual(result.dimensions, 384)
        self.assertGreater(result.generation_time, 0)
        self.assertGreater(result.token_count, 0)
        self.assertIsInstance(result.embedding, np.ndarray)
        self.assertEqual(len(result.embedding), 384)
    
    def test_empty_text_handling(self):
        """Test handling of empty text"""
        with self.assertRaises(ValueError):
            self.generator.generate_embedding("")
        
        with self.assertRaises(ValueError):
            self.generator.generate_embedding("   ")
    
    def test_custom_config_override(self):
        """Test using custom config override"""
        custom_config = EmbeddingConfig(
            model=EmbeddingModel.OPENAI_3_LARGE,
            dimensions=3072,
            max_tokens=1000,
            normalize=False
        )
        
        text = "Test with custom config"
        result = self.generator.generate_embedding(text, custom_config)
        
        self.assertEqual(result.model, EmbeddingModel.OPENAI_3_LARGE)
        self.assertEqual(result.dimensions, 3072)
    
    def test_caching_behavior(self):
        """Test embedding caching"""
        text = "This text will be cached"
        
        # Generate first time
        start_time = time.time()
        result1 = self.generator.generate_embedding(text)
        first_time = time.time() - start_time
        
        # Generate second time (should be cached)
        start_time = time.time()
        result2 = self.generator.generate_embedding(text)
        second_time = time.time() - start_time
        
        # Results should be identical
        self.assertEqual(result1.text, result2.text)
        np.testing.assert_array_equal(result1.embedding, result2.embedding)
        
        # Second call should be faster (cached)
        self.assertLess(second_time, first_time)
        
        # Check cache hit statistics
        stats = self.generator.get_statistics()
        self.assertGreater(stats['cache_hits'], 0)
    
    def test_text_preprocessing(self):
        """Test text preprocessing functionality"""
        # Test with excessive whitespace
        text_with_spaces = "This    has   excessive    whitespace"
        result = self.generator.generate_embedding(text_with_spaces)
        
        self.assertIsNotNone(result)
        self.assertIn('processed_text_length', result.metadata)
        
        # Test with very long text (should be truncated)
        long_text = " ".join(["word"] * 1000)  # Very long text
        result = self.generator.generate_embedding(long_text)
        
        self.assertIsNotNone(result)
        # Processed text should be shorter than original
        self.assertLess(result.metadata['processed_text_length'], len(long_text))
    
    def test_batch_embedding_generation(self):
        """Test batch embedding generation"""
        texts = [
            "First test sentence",
            "Second test sentence", 
            "Third test sentence",
            "Fourth test sentence"
        ]
        
        batch_result = self.generator.generate_batch_embeddings(texts)
        
        self.assertIsInstance(batch_result, BatchEmbeddingResult)
        self.assertEqual(batch_result.total_texts, 4)
        self.assertEqual(batch_result.successful_embeddings, 4)
        self.assertEqual(batch_result.failed_embeddings, 0)
        self.assertEqual(len(batch_result.results), 4)
        self.assertGreater(batch_result.total_time, 0)
        self.assertGreater(batch_result.total_tokens, 0)
        
        # Check individual results
        for i, result in enumerate(batch_result.results):
            self.assertEqual(result.text, texts[i])
            self.assertIsInstance(result.embedding, np.ndarray)
    
    def test_batch_with_empty_list(self):
        """Test batch processing with empty list"""
        with self.assertRaises(ValueError):
            self.generator.generate_batch_embeddings([])
    
    def test_parallel_vs_sequential_batch(self):
        """Test parallel vs sequential batch processing"""
        texts = ["Text " + str(i) for i in range(5)]
        
        # Sequential processing
        start_time = time.time()
        sequential_result = self.generator.generate_batch_embeddings(texts, max_workers=1)
        sequential_time = time.time() - start_time
        
        # Clear cache to ensure fair comparison
        self.generator.clear_cache()
        
        # Parallel processing
        start_time = time.time() 
        parallel_result = self.generator.generate_batch_embeddings(texts, max_workers=3)
        parallel_time = time.time() - start_time
        
        # Both should succeed
        self.assertEqual(sequential_result.successful_embeddings, 5)
        self.assertEqual(parallel_result.successful_embeddings, 5)
        
        # Parallel should be faster (or at least not significantly slower)
        self.assertLessEqual(parallel_time, sequential_time * 1.5)
    
    def test_statistics_tracking(self):
        """Test statistics tracking"""
        initial_stats = self.generator.get_statistics()
        
        # Generate some embeddings
        texts = ["Text 1", "Text 2", "Text 3"]
        self.generator.generate_batch_embeddings(texts)
        
        updated_stats = self.generator.get_statistics()
        
        # Statistics should be updated
        self.assertGreater(updated_stats['total_embeddings'], initial_stats['total_embeddings'])
        self.assertGreater(updated_stats['total_tokens'], initial_stats['total_tokens'])
        self.assertGreater(updated_stats['total_time'], initial_stats['total_time'])
        
        # Check derived statistics
        self.assertIn('avg_tokens_per_embedding', updated_stats)
        self.assertIn('avg_time_per_embedding', updated_stats)
        self.assertIn('tokens_per_second', updated_stats)
    
    def test_statistics_reset(self):
        """Test statistics reset"""
        # Generate some embeddings
        self.generator.generate_embedding("Test text")
        
        stats_before = self.generator.get_statistics()
        self.assertGreater(stats_before['total_embeddings'], 0)
        
        # Reset statistics
        self.generator.reset_statistics()
        
        stats_after = self.generator.get_statistics()
        self.assertEqual(stats_after['total_embeddings'], 0)
        self.assertEqual(stats_after['total_tokens'], 0)
        self.assertEqual(stats_after['total_time'], 0.0)
    
    def test_model_information_retrieval(self):
        """Test getting model information"""
        supported_models = self.generator.get_supported_models()
        self.assertIsInstance(supported_models, list)
        self.assertGreater(len(supported_models), 0)
        
        # Test getting info for specific model
        model_info = self.generator.get_model_info(EmbeddingModel.OPENAI_3_LARGE)
        self.assertIn('model', model_info)
        self.assertIn('dimensions', model_info) 
        self.assertIn('description', model_info)
        self.assertEqual(model_info['dimensions'], 3072)


class TestBatchProcessingPerformance(unittest.TestCase):
    """Test batch processing performance and statistics"""
    
    def setUp(self):
        """Set up performance test generator"""
        self.generator = EmbeddingGenerator(max_workers=4)
    
    def test_batch_statistics_calculation(self):
        """Test batch statistics calculation"""
        texts = [
            "Mathematical content with equations: x² + y² = z²",
            "Definition: A function is a relation between sets",
            "Example: Let f(x) = 2x + 1",
            "Regular text without special content"
        ]
        
        batch_result = self.generator.generate_batch_embeddings(texts)
        
        # Check batch statistics
        self.assertIn('embedding_dimensions', batch_result.batch_statistics)
        self.assertIn('avg_generation_time', batch_result.batch_statistics)
        self.assertIn('tokens_per_second', batch_result.batch_statistics)
        self.assertIn('embeddings_per_second', batch_result.batch_statistics)
        self.assertIn('avg_cosine_similarity', batch_result.batch_statistics)
        self.assertIn('embedding_norm_stats', batch_result.batch_statistics)
        
        # Verify statistics are reasonable
        self.assertGreater(batch_result.batch_statistics['tokens_per_second'], 0)
        self.assertGreater(batch_result.batch_statistics['embeddings_per_second'], 0)
        self.assertGreaterEqual(batch_result.batch_statistics['avg_cosine_similarity'], -1)
        self.assertLessEqual(batch_result.batch_statistics['avg_cosine_similarity'], 1)
    
    def test_large_batch_processing(self):
        """Test processing large batches"""
        # Generate a larger batch
        texts = [f"Test sentence number {i} with unique content" for i in range(20)]
        
        start_time = time.time()
        batch_result = self.generator.generate_batch_embeddings(texts, max_workers=4)
        total_time = time.time() - start_time
        
        self.assertEqual(batch_result.successful_embeddings, 20)
        self.assertEqual(batch_result.failed_embeddings, 0)
        
        # Should process multiple embeddings per second
        embeddings_per_second = len(texts) / total_time
        self.assertGreater(embeddings_per_second, 10)  # At least 10 per second
    
    def test_error_handling_in_batch(self):
        """Test error handling in batch processing"""
        # Mix valid and problematic texts
        texts = [
            "Valid text 1",
            "",  # Empty text should cause error
            "Valid text 2",
            "   ",  # Whitespace-only should cause error
            "Valid text 3"
        ]
        
        batch_result = self.generator.generate_batch_embeddings(texts)
        
        # Should have some successes and some failures
        self.assertGreater(batch_result.successful_embeddings, 0)
        self.assertGreater(batch_result.failed_embeddings, 0)
        self.assertGreater(len(batch_result.errors), 0)
        
        # Total should match
        self.assertEqual(
            batch_result.successful_embeddings + batch_result.failed_embeddings,
            len(texts)
        )


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_educational_config_creation(self):
        """Test creating educational-optimized config"""
        config = create_educational_config()
        
        self.assertEqual(config.model, EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET)
        self.assertEqual(config.dimensions, 768)
        self.assertEqual(config.max_tokens, 512)
        self.assertEqual(config.batch_size, 16)
        self.assertTrue(config.normalize)
        self.assertTrue(config.cache_embeddings)
        self.assertIn("educational", config.custom_instructions)
        
        # Test with different model
        config2 = create_educational_config(EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM)
        self.assertEqual(config2.model, EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM)
        self.assertEqual(config2.dimensions, 384)
    
    def test_mathematical_config_creation(self):
        """Test creating math-optimized config"""
        config = create_mathematical_config()
        
        self.assertEqual(config.model, EmbeddingModel.OPENAI_3_LARGE)
        self.assertEqual(config.dimensions, 3072)
        self.assertEqual(config.max_tokens, 1000)
        self.assertEqual(config.batch_size, 8)
        self.assertIn("mathematical", config.custom_instructions)
    
    def test_embedding_similarity_calculation(self):
        """Test embedding similarity calculation"""
        # Test identical embeddings
        emb1 = np.array([1, 0, 0], dtype=np.float32)
        emb2 = np.array([1, 0, 0], dtype=np.float32)
        similarity = calculate_embedding_similarity(emb1, emb2)
        self.assertAlmostEqual(similarity, 1.0, places=5)
        
        # Test orthogonal embeddings
        emb1 = np.array([1, 0, 0], dtype=np.float32)
        emb2 = np.array([0, 1, 0], dtype=np.float32)
        similarity = calculate_embedding_similarity(emb1, emb2)
        self.assertAlmostEqual(similarity, 0.0, places=5)
        
        # Test opposite embeddings
        emb1 = np.array([1, 0, 0], dtype=np.float32)
        emb2 = np.array([-1, 0, 0], dtype=np.float32)
        similarity = calculate_embedding_similarity(emb1, emb2)
        self.assertAlmostEqual(similarity, -1.0, places=5)
        
        # Test different dimensions
        emb1 = np.array([1, 0], dtype=np.float32)
        emb2 = np.array([1, 0, 0], dtype=np.float32)
        with self.assertRaises(ValueError):
            calculate_embedding_similarity(emb1, emb2)
        
        # Test zero embeddings
        emb1 = np.array([0, 0, 0], dtype=np.float32)
        emb2 = np.array([1, 0, 0], dtype=np.float32)
        similarity = calculate_embedding_similarity(emb1, emb2)
        self.assertEqual(similarity, 0.0)


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of embedding generation"""
    
    def test_concurrent_embedding_generation(self):
        """Test concurrent embedding generation from multiple threads"""
        generator = EmbeddingGenerator(max_workers=2)
        texts = [f"Concurrent test {i}" for i in range(10)]
        results = []
        errors = []
        
        def generate_embedding(text):
            try:
                result = generator.generate_embedding(text)
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for text in texts:
            thread = threading.Thread(target=generate_embedding, args=(text,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors in concurrent generation: {errors}")
        self.assertEqual(len(results), len(texts))
        
        # Verify all results are valid
        for result in results:
            self.assertIsInstance(result, EmbeddingResult)
            self.assertIsInstance(result.embedding, np.ndarray)
            self.assertGreater(result.dimensions, 0)
    
    def test_concurrent_cache_access(self):
        """Test concurrent cache access"""
        generator = EmbeddingGenerator(enable_cache=True, cache_size=50)
        same_text = "This text will be accessed concurrently"
        results = []
        errors = []
        
        def generate_and_cache(iteration):
            try:
                result = generator.generate_embedding(f"{same_text} {iteration}")
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads accessing cache
        threads = []
        for i in range(20):
            thread = threading.Thread(target=generate_and_cache, args=(i,))
            threads.append(thread)
        
        # Start and wait for all threads
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        self.assertEqual(len(errors), 0, f"Cache concurrency errors: {errors}")
        self.assertEqual(len(results), 20)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        """Set up edge case testing"""
        self.generator = EmbeddingGenerator()
    
    def test_unicode_text_handling(self):
        """Test handling of unicode text"""
        unicode_texts = [
            "Text with émojis: 🚀 🎯 📊",
            "Mathematical symbols: ∫∑∂√π",
            "Foreign characters: 你好世界 こんにちは",
            "Mixed content: Hello 世界 with √π"
        ]
        
        for text in unicode_texts:
            result = self.generator.generate_embedding(text)
            self.assertIsNotNone(result)
            self.assertEqual(result.text, text)
            self.assertIsInstance(result.embedding, np.ndarray)
    
    def test_very_long_text(self):
        """Test handling of very long text"""
        long_text = "word " * 10000  # Very long text
        
        result = self.generator.generate_embedding(long_text)
        
        self.assertIsNotNone(result)
        # Should be truncated based on max_tokens
        self.assertLess(result.metadata['processed_text_length'], len(long_text))
    
    def test_special_characters(self):
        """Test handling of special characters"""
        special_texts = [
            "Text with\nnewlines\nand\ttabs",
            "Quotes: \"Hello\" and 'World'",
            "Symbols: @#$%^&*(){}[]|\\",
            "HTML-like: <tag>content</tag>",
            "JSON-like: {\"key\": \"value\"}"
        ]
        
        for text in special_texts:
            result = self.generator.generate_embedding(text)
            self.assertIsNotNone(result)
            self.assertIsInstance(result.embedding, np.ndarray)
    
    def test_disabled_caching(self):
        """Test generator with caching disabled"""
        generator = EmbeddingGenerator(enable_cache=False)
        
        text = "Test without caching"
        
        # Generate twice
        result1 = generator.generate_embedding(text)
        result2 = generator.generate_embedding(text) 
        
        # Should get same results but no cache benefits
        np.testing.assert_array_equal(result1.embedding, result2.embedding)
        
        stats = generator.get_statistics()
        self.assertEqual(stats['cache_hits'], 0)  # No cache enabled
    
    def test_model_provider_failure_simulation(self):
        """Test handling of model provider failures"""
        generator = EmbeddingGenerator()
        
        # Mock a provider to raise an exception
        original_provider = generator.providers[EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM]
        mock_provider = Mock()
        mock_provider.generate_embedding.side_effect = Exception("Simulated provider failure")
        generator.providers[EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM] = mock_provider
        
        # Should raise the exception
        with self.assertRaises(Exception):
            generator.generate_embedding("Test text")
        
        # Restore original provider
        generator.providers[EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM] = original_provider


if __name__ == '__main__':
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestEmbeddingModel,
        TestEmbeddingConfig,
        TestEmbeddingCache,
        TestMockEmbeddingProvider,
        TestEmbeddingGenerator,
        TestBatchProcessingPerformance,
        TestUtilityFunctions,
        TestThreadSafety,
        TestEdgeCases
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"EmbeddingGenerator Test Summary")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError: ')[-1].split('\n')[0]}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('\n')[-2]}")
    
    print(f"\n🎯 EmbeddingGenerator testing completed!")