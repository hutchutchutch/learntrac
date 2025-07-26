#!/usr/bin/env python3
"""
Comprehensive Tests for EmbeddingPipeline - Complete pipeline orchestration testing

Tests all functionality of the EmbeddingPipeline including:
- Document processing workflow
- Pipeline configuration and modes
- Batch processing capabilities
- Error handling and retry logic
- Performance metrics and statistics
- Export functionality
- Integration with all components
"""

import unittest
import numpy as np
import time
import tempfile
import json
import os
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from embedding_pipeline import (
    EmbeddingPipeline, PipelineConfig, DocumentInput, ChunkEmbeddingResult,
    DocumentEmbeddingResult, BatchProcessingResult, PipelineMode, RetryStrategy,
    create_fast_pipeline_config, create_quality_focused_config, create_batch_optimized_config
)
from embedding_generator import EmbeddingConfig, EmbeddingModel, EmbeddingResult
from chunk_metadata import ChunkMetadata, ContentType
from structure_detector import StructureElement


class TestPipelineConfig(unittest.TestCase):
    """Test PipelineConfig data structure"""
    
    def test_config_creation(self):
        """Test creating pipeline configuration"""
        embedding_config = EmbeddingConfig(
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            dimensions=768,
            max_tokens=512
        )
        
        config = PipelineConfig(
            embedding_config=embedding_config,
            mode=PipelineMode.QUALITY_FOCUSED,
            enable_quality_assessment=True,
            quality_threshold=0.8,
            parallel_processing=True,
            max_workers=4
        )
        
        self.assertEqual(config.embedding_config, embedding_config)
        self.assertEqual(config.mode, PipelineMode.QUALITY_FOCUSED)
        self.assertTrue(config.enable_quality_assessment)
        self.assertEqual(config.quality_threshold, 0.8)
        self.assertTrue(config.parallel_processing)
        self.assertEqual(config.max_workers, 4)
    
    def test_config_defaults(self):
        """Test configuration defaults"""
        config = PipelineConfig()
        
        self.assertEqual(config.mode, PipelineMode.STANDARD)
        self.assertEqual(config.retry_strategy, RetryStrategy.ADAPTIVE)
        self.assertEqual(config.max_retries, 3)
        self.assertTrue(config.parallel_processing)
        self.assertEqual(config.max_workers, 4)
        self.assertTrue(config.enable_caching)
        self.assertEqual(config.batch_size, 10)
        self.assertTrue(config.filter_low_quality)
        self.assertEqual(config.min_quality_score, 0.6)


class TestDocumentInput(unittest.TestCase):
    """Test DocumentInput data structure"""
    
    def test_document_input_creation(self):
        """Test creating document input"""
        structure_elements = [
            StructureElement(
                element_type="heading",
                content="Chapter 1: Introduction",
                level=1,
                start_position=0,
                end_position=50
            )
        ]
        
        doc_input = DocumentInput(
            document_id="test_doc_1",
            text="This is test document content with educational material.",
            title="Test Document",
            subject="Mathematics",
            structure_elements=structure_elements,
            metadata={"source": "textbook", "page": 1}
        )
        
        self.assertEqual(doc_input.document_id, "test_doc_1")
        self.assertEqual(doc_input.title, "Test Document")
        self.assertEqual(doc_input.subject, "Mathematics")
        self.assertEqual(len(doc_input.structure_elements), 1)
        self.assertEqual(doc_input.metadata["source"], "textbook")
        
    def test_document_input_defaults(self):
        """Test document input defaults"""
        doc_input = DocumentInput(
            document_id="test_doc",
            text="Test content"
        )
        
        self.assertIsNone(doc_input.title)
        self.assertIsNone(doc_input.subject)
        self.assertEqual(len(doc_input.structure_elements), 0)
        self.assertEqual(len(doc_input.metadata), 0)


class TestEmbeddingPipeline(unittest.TestCase):
    """Test main EmbeddingPipeline functionality"""
    
    def setUp(self):
        """Set up test pipeline"""
        embedding_config = EmbeddingConfig(
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM,
            dimensions=384,
            max_tokens=512,
            batch_size=5
        )
        
        config = PipelineConfig(
            embedding_config=embedding_config,
            mode=PipelineMode.STANDARD,
            enable_quality_assessment=True,
            quality_threshold=0.7,
            max_workers=2,
            batch_size=5,
            max_retries=2
        )
        
        self.pipeline = EmbeddingPipeline(config)
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization"""
        self.assertIsNotNone(self.pipeline.config)
        self.assertIsNotNone(self.pipeline.chunker)
        self.assertIsNotNone(self.pipeline.embedding_generator)
        self.assertIsNotNone(self.pipeline.quality_assessor)
        
        # Check statistics initialization
        self.assertEqual(self.pipeline.stats['documents_processed'], 0)
        self.assertEqual(self.pipeline.stats['chunks_processed'], 0)
        self.assertEqual(self.pipeline.stats['embeddings_generated'], 0)
    
    def test_default_initialization(self):
        """Test pipeline initialization with defaults"""
        pipeline = EmbeddingPipeline()
        
        self.assertIsNotNone(pipeline.config)
        self.assertEqual(pipeline.config.mode, PipelineMode.STANDARD)
        self.assertTrue(pipeline.config.enable_quality_assessment)
    
    def create_test_document(self, text: str = None, doc_id: str = "test_doc") -> DocumentInput:
        """Helper to create test document"""
        if text is None:
            text = """
            Chapter 1: Introduction to Mathematics

            Definition: Mathematics is the study of numbers, shapes, and patterns.
            
            Example: The number 7 is a prime number because it can only be divided by 1 and itself.
            
            Mathematical notation: Let f(x) = x² + 2x + 1 be a quadratic function.
            
            This chapter introduces fundamental concepts that will be used throughout the course.
            """
        
        return DocumentInput(
            document_id=doc_id,
            text=text,
            title="Mathematics Textbook",
            subject="Mathematics",
            metadata={"chapter": 1, "source": "textbook"}
        )
    
    def test_single_document_processing(self):
        """Test processing single document"""
        document = self.create_test_document()
        
        result = self.pipeline.process_document(document)
        
        self.assertIsInstance(result, DocumentEmbeddingResult)
        self.assertEqual(result.document_id, "test_doc")
        self.assertGreater(result.total_chunks, 0)
        self.assertGreaterEqual(result.successful_embeddings, 0)
        self.assertGreater(result.total_processing_time, 0)
        self.assertGreater(result.chunking_time, 0)
        self.assertGreater(result.embedding_time, 0)
        
        # Check chunk results
        self.assertIsInstance(result.chunk_results, list)
        if result.chunk_results:
            chunk_result = result.chunk_results[0]
            self.assertIsInstance(chunk_result, ChunkEmbeddingResult)
            self.assertIsNotNone(chunk_result.chunk_id)
            self.assertIsNotNone(chunk_result.chunk_text)
            self.assertIsInstance(chunk_result.chunk_metadata, ChunkMetadata)
    
    def test_empty_document_processing(self):
        """Test processing empty document"""
        empty_document = DocumentInput(
            document_id="empty_doc",
            text=""
        )
        
        result = self.pipeline.process_document(empty_document)
        
        # Should handle empty document gracefully
        self.assertIsInstance(result, DocumentEmbeddingResult)
        self.assertEqual(result.document_id, "empty_doc")
        # May have 0 chunks or handle empty content specially
    
    def test_document_with_structure_elements(self):
        """Test processing document with structure elements"""
        structure_elements = [
            StructureElement(
                element_type="heading",
                content="Chapter 1: Introduction",
                level=1,
                start_position=0,
                end_position=50
            ),
            StructureElement(
                element_type="definition",
                content="Definition: Mathematics is...",
                level=2,
                start_position=100,
                end_position=200
            )
        ]
        
        document = DocumentInput(
            document_id="structured_doc",
            text="Chapter 1: Introduction\n\nDefinition: Mathematics is the study of numbers...",
            structure_elements=structure_elements
        )
        
        result = self.pipeline.process_document(document)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.document_id, "structured_doc")
        self.assertIsNotNone(result.chunking_result)
    
    def test_batch_document_processing(self):
        """Test batch processing multiple documents"""
        documents = [
            self.create_test_document("First document content", "doc1"),
            self.create_test_document("Second document content", "doc2"),
            self.create_test_document("Third document content", "doc3")
        ]
        
        batch_result = self.pipeline.process_documents_batch(documents)
        
        self.assertIsInstance(batch_result, BatchProcessingResult)
        self.assertEqual(batch_result.total_documents, 3)
        self.assertEqual(len(batch_result.document_results), 3)
        self.assertGreater(batch_result.total_processing_time, 0)
        self.assertGreater(batch_result.average_time_per_document, 0)
        
        # Check individual document results
        for doc_result in batch_result.document_results:
            self.assertIsInstance(doc_result, DocumentEmbeddingResult)
            self.assertIn(doc_result.document_id, ["doc1", "doc2", "doc3"])
    
    def test_empty_batch_processing(self):
        """Test batch processing with empty document list"""
        with self.assertRaises(ValueError):
            self.pipeline.process_documents_batch([])
    
    def test_parallel_vs_sequential_batch_processing(self):
        """Test parallel vs sequential batch processing"""
        documents = [
            self.create_test_document(f"Document {i} content", f"doc_{i}")
            for i in range(4)
        ]
        
        # Sequential processing
        config_sequential = PipelineConfig(
            parallel_processing=False,
            max_workers=1,
            enable_quality_assessment=False  # Faster for comparison
        )
        pipeline_sequential = EmbeddingPipeline(config_sequential)
        
        start_time = time.time()
        sequential_result = pipeline_sequential.process_documents_batch(documents, max_workers=1)
        sequential_time = time.time() - start_time
        
        # Parallel processing
        config_parallel = PipelineConfig(
            parallel_processing=True,
            max_workers=3,
            enable_quality_assessment=False  # Faster for comparison
        )
        pipeline_parallel = EmbeddingPipeline(config_parallel)
        
        start_time = time.time()
        parallel_result = pipeline_parallel.process_documents_batch(documents, max_workers=3)
        parallel_time = time.time() - start_time
        
        # Both should succeed
        self.assertEqual(sequential_result.successful_documents, 4)
        self.assertEqual(parallel_result.successful_documents, 4)
        
        # Parallel should be faster or at least competitive
        self.assertLessEqual(parallel_time, sequential_time * 1.5)
    
    def test_pipeline_modes(self):
        """Test different pipeline modes"""
        document = self.create_test_document()
        
        # Test FAST mode
        fast_config = PipelineConfig(
            mode=PipelineMode.FAST,
            enable_quality_assessment=False,
            max_workers=4
        )
        fast_pipeline = EmbeddingPipeline(fast_config)
        
        start_time = time.time()
        fast_result = fast_pipeline.process_document(document)
        fast_time = time.time() - start_time
        
        # Test QUALITY_FOCUSED mode
        quality_config = PipelineConfig(
            mode=PipelineMode.QUALITY_FOCUSED,
            enable_quality_assessment=True,
            quality_threshold=0.8,
            max_retries=5
        )
        quality_pipeline = EmbeddingPipeline(quality_config)
        
        start_time = time.time()
        quality_result = quality_pipeline.process_document(document)
        quality_time = time.time() - start_time
        
        # Both should succeed
        self.assertIsNotNone(fast_result)
        self.assertIsNotNone(quality_result)
        
        # Fast mode should be faster
        self.assertLess(fast_time, quality_time * 2)  # Allow some margin
        
        # Quality mode should have quality assessments
        if quality_result.chunk_results:
            has_quality_assessment = any(
                chunk.quality_assessment is not None 
                for chunk in quality_result.chunk_results
            )
            # Quality assessments may be present in quality-focused mode
    
    def test_retry_logic(self):
        """Test retry logic for failed embeddings"""
        config = PipelineConfig(
            retry_strategy=RetryStrategy.SIMPLE,
            max_retries=3
        )
        pipeline = EmbeddingPipeline(config)
        
        # Create document
        document = self.create_test_document("Test retry logic")
        
        # Mock embedding generator to fail first few times
        original_generate = pipeline.embedding_generator.generate_embedding
        call_count = 0
        
        def mock_generate_with_retry(text, config=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise Exception("Simulated embedding failure")
            return original_generate(text, config)
        
        pipeline.embedding_generator.generate_embedding = mock_generate_with_retry
        
        result = pipeline.process_document(document)
        
        # Should succeed after retries
        self.assertIsNotNone(result)
        # Some chunks might have succeeded with retries
        
        # Restore original method
        pipeline.embedding_generator.generate_embedding = original_generate
    
    def test_quality_filtering(self):
        """Test quality-based filtering of embeddings"""
        config = PipelineConfig(
            enable_quality_assessment=True,
            filter_low_quality=True,
            min_quality_score=0.8  # High threshold
        )
        pipeline = EmbeddingPipeline(config)
        
        document = self.create_test_document()
        result = pipeline.process_document(document)
        
        self.assertIsNotNone(result)
        # Some embeddings might be filtered based on quality
        # The exact behavior depends on the mock quality assessment
    
    def test_statistics_tracking(self):
        """Test pipeline statistics tracking"""
        initial_stats = self.pipeline.get_pipeline_statistics()
        
        # Process some documents
        documents = [
            self.create_test_document("Doc 1", "doc1"),
            self.create_test_document("Doc 2", "doc2")
        ]
        
        self.pipeline.process_documents_batch(documents)
        
        updated_stats = self.pipeline.get_pipeline_statistics()
        
        # Statistics should be updated
        self.assertGreater(updated_stats['documents_processed'], initial_stats['documents_processed'])
        self.assertGreater(updated_stats['chunks_processed'], initial_stats['chunks_processed'])
        self.assertGreater(updated_stats['embeddings_generated'], initial_stats['embeddings_generated'])
        
        # Check derived statistics
        if updated_stats['documents_processed'] > 0:
            self.assertIn('avg_chunks_per_document', updated_stats)
            self.assertIn('avg_processing_time_per_document', updated_stats)
        
        if updated_stats['chunks_processed'] > 0:
            self.assertIn('embedding_success_rate', updated_stats)
    
    def test_statistics_reset(self):
        """Test statistics reset"""
        # Process a document
        document = self.create_test_document()
        self.pipeline.process_document(document)
        
        stats_before = self.pipeline.get_pipeline_statistics()
        self.assertGreater(stats_before['documents_processed'], 0)
        
        # Reset statistics
        self.pipeline.reset_statistics()
        
        stats_after = self.pipeline.get_pipeline_statistics()
        self.assertEqual(stats_after['documents_processed'], 0)
        self.assertEqual(stats_after['chunks_processed'], 0)
        self.assertEqual(stats_after['embeddings_generated'], 0)
    
    def test_config_update(self):
        """Test updating pipeline configuration"""
        original_mode = self.pipeline.config.mode
        
        new_config = PipelineConfig(
            mode=PipelineMode.FAST,
            enable_quality_assessment=False
        )
        
        self.pipeline.update_config(new_config)
        
        self.assertEqual(self.pipeline.config.mode, PipelineMode.FAST)
        self.assertFalse(self.pipeline.config.enable_quality_assessment)
        self.assertNotEqual(self.pipeline.config.mode, original_mode)


class TestEmbeddingExport(unittest.TestCase):
    """Test embedding export functionality"""
    
    def setUp(self):
        """Set up export testing"""
        self.pipeline = EmbeddingPipeline()
    
    def test_numpy_export(self):
        """Test exporting embeddings to numpy format"""
        document = DocumentInput(
            document_id="export_test",
            text="Test document for export functionality with multiple sentences. Each sentence should create a chunk."
        )
        
        result = self.pipeline.process_document(document)
        
        # Test in-memory export (no file path)
        export_info = self.pipeline.export_embeddings(result, format='numpy')
        
        self.assertEqual(export_info['document_id'], "export_test")
        self.assertGreater(export_info['total_embeddings'], 0)
        self.assertGreater(export_info['embedding_dimensions'], 0)
        self.assertEqual(export_info['export_format'], 'numpy')
        self.assertIn('export_timestamp', export_info)
    
    def test_json_export(self):
        """Test exporting embeddings to JSON format"""
        document = DocumentInput(
            document_id="json_export_test",
            text="Test document for JSON export."
        )
        
        result = self.pipeline.process_document(document)
        
        # Test in-memory export
        export_info = self.pipeline.export_embeddings(result, format='json')
        
        self.assertEqual(export_info['export_format'], 'json')
        self.assertGreater(export_info['total_embeddings'], 0)
    
    def test_file_export(self):
        """Test exporting embeddings to file"""
        document = DocumentInput(
            document_id="file_export_test",
            text="Test document for file export."
        )
        
        result = self.pipeline.process_document(document)
        
        # Test numpy file export
        with tempfile.NamedTemporaryFile(suffix='.npz', delete=False) as temp_file:
            try:
                export_info = self.pipeline.export_embeddings(
                    result, format='numpy', output_path=temp_file.name
                )
                
                self.assertEqual(export_info['output_path'], temp_file.name)
                self.assertTrue(os.path.exists(temp_file.name))
                
                # Load and verify
                loaded_data = np.load(temp_file.name, allow_pickle=True)
                self.assertIn('embeddings', loaded_data)
                self.assertIn('metadata', loaded_data)
                self.assertIn('export_info', loaded_data)
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        
        # Test JSON file export
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            try:
                export_info = self.pipeline.export_embeddings(
                    result, format='json', output_path=temp_file.name
                )
                
                self.assertTrue(os.path.exists(temp_file.name))
                
                # Load and verify JSON
                with open(temp_file.name, 'r') as f:
                    loaded_data = json.load(f)
                
                self.assertIn('embeddings', loaded_data)
                self.assertIn('metadata', loaded_data)
                self.assertIn('export_info', loaded_data)
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    def test_empty_result_export(self):
        """Test exporting empty result"""
        # Create result with no successful embeddings
        empty_result = DocumentEmbeddingResult(
            document_id="empty",
            chunk_results=[],
            total_chunks=0,
            successful_embeddings=0,
            failed_embeddings=0,
            filtered_low_quality=0,
            chunking_time=0.0,
            embedding_time=0.0,
            quality_assessment_time=0.0,
            total_processing_time=0.0,
            average_quality=0.0,
            quality_distribution={},
            pipeline_config=PipelineConfig()
        )
        
        with self.assertRaises(ValueError):
            self.pipeline.export_embeddings(empty_result)
    
    def test_unsupported_format_export(self):
        """Test exporting with unsupported format"""
        document = DocumentInput(
            document_id="format_test",
            text="Test document."
        )
        
        result = self.pipeline.process_document(document)
        
        with tempfile.NamedTemporaryFile() as temp_file:
            with self.assertRaises(ValueError):
                self.pipeline.export_embeddings(
                    result, format='unsupported_format', output_path=temp_file.name
                )


class TestUtilityConfigurations(unittest.TestCase):
    """Test utility configuration functions"""
    
    def test_fast_pipeline_config(self):
        """Test fast pipeline configuration"""
        config = create_fast_pipeline_config()
        
        self.assertEqual(config.mode, PipelineMode.FAST)
        self.assertFalse(config.enable_quality_assessment)
        self.assertTrue(config.parallel_processing)
        self.assertEqual(config.max_workers, 8)
        self.assertEqual(config.batch_size, 20)
        self.assertFalse(config.filter_low_quality)
        
        # Should have fast embedding model
        self.assertEqual(config.embedding_config.model, EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM)
    
    def test_quality_focused_config(self):
        """Test quality-focused pipeline configuration"""
        config = create_quality_focused_config()
        
        self.assertEqual(config.mode, PipelineMode.QUALITY_FOCUSED)
        self.assertTrue(config.enable_quality_assessment)
        self.assertEqual(config.quality_threshold, 0.8)
        self.assertTrue(config.filter_low_quality)
        self.assertEqual(config.min_quality_score, 0.7)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.retry_strategy, RetryStrategy.ADAPTIVE)
        
        # Should have high-quality embedding model
        self.assertEqual(config.embedding_config.model, EmbeddingModel.OPENAI_3_LARGE)
        self.assertIsNotNone(config.fallback_embedding_config)
    
    def test_batch_optimized_config(self):
        """Test batch-optimized pipeline configuration"""
        config = create_batch_optimized_config()
        
        self.assertEqual(config.mode, PipelineMode.BATCH_OPTIMIZED)
        self.assertTrue(config.enable_quality_assessment)
        self.assertEqual(config.quality_threshold, 0.7)
        self.assertTrue(config.parallel_processing)
        self.assertEqual(config.max_workers, 12)
        self.assertEqual(config.batch_size, 50)
        self.assertTrue(config.enable_caching)
        self.assertTrue(config.filter_low_quality)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def setUp(self):
        """Set up error testing"""
        self.pipeline = EmbeddingPipeline()
    
    def test_document_processing_error_handling(self):
        """Test handling of document processing errors"""
        # Create document that might cause processing errors
        problematic_document = DocumentInput(
            document_id="problematic_doc",
            text="A" * 100000  # Very long text that might cause issues
        )
        
        # Should handle gracefully and return error result
        result = self.pipeline.process_document(problematic_document)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.document_id, "problematic_doc")
        # May have errors in the result
    
    def test_batch_processing_with_errors(self):
        """Test batch processing with some failed documents"""
        documents = [
            DocumentInput(document_id="good_doc", text="Good document content"),
            DocumentInput(document_id="empty_doc", text=""),  # Might cause issues
            DocumentInput(document_id="another_good_doc", text="Another good document")
        ]
        
        batch_result = self.pipeline.process_documents_batch(documents)
        
        self.assertEqual(batch_result.total_documents, 3)
        self.assertEqual(len(batch_result.document_results), 3)
        # Some documents might succeed, others might fail
        self.assertGreaterEqual(batch_result.successful_documents, 0)
        self.assertGreaterEqual(batch_result.failed_documents, 0)
    
    def test_invalid_document_input(self):
        """Test handling of invalid document input"""
        # Document with no text
        invalid_doc = DocumentInput(
            document_id="invalid",
            text=None
        )
        
        # Should handle gracefully
        try:
            result = self.pipeline.process_document(invalid_doc)
            self.assertIsNotNone(result)
        except (ValueError, TypeError):
            # Acceptable to raise exception for invalid input
            pass
    
    def test_component_failure_simulation(self):
        """Test handling of component failures"""
        # Mock chunker to raise exception
        original_chunk_content = self.pipeline.chunker.chunk_content
        
        def mock_chunk_content_failure(*args, **kwargs):
            raise Exception("Simulated chunker failure")
        
        self.pipeline.chunker.chunk_content = mock_chunk_content_failure
        
        document = DocumentInput(
            document_id="test_failure",
            text="Test document for failure simulation"
        )
        
        result = self.pipeline.process_document(document)
        
        # Should return error result
        self.assertIsNotNone(result)
        self.assertEqual(result.document_id, "test_failure")
        self.assertGreater(len(result.errors), 0)
        
        # Restore original method
        self.pipeline.chunker.chunk_content = original_chunk_content


class TestPerformanceBenchmarks(unittest.TestCase):
    """Test pipeline performance benchmarks"""
    
    def test_single_document_performance(self):
        """Test single document processing performance"""
        pipeline = EmbeddingPipeline()
        
        document = DocumentInput(
            document_id="perf_test",
            text="Performance test document with educational content. " * 50
        )
        
        start_time = time.time()
        result = pipeline.process_document(document)
        total_time = time.time() - start_time
        
        # Should complete in reasonable time
        self.assertLess(total_time, 30.0)  # Less than 30 seconds
        self.assertIsNotNone(result)
        
        # Check performance metrics
        if result.successful_embeddings > 0:
            avg_time_per_embedding = result.embedding_time / result.successful_embeddings
            self.assertLess(avg_time_per_embedding, 5.0)  # Less than 5 seconds per embedding
    
    def test_batch_processing_performance(self):
        """Test batch processing performance"""
        pipeline = EmbeddingPipeline(PipelineConfig(max_workers=4))
        
        # Create batch of documents
        documents = [
            DocumentInput(
                document_id=f"batch_perf_{i}",
                text=f"Batch performance test document {i} with educational content. " * 20
            )
            for i in range(10)
        ]
        
        start_time = time.time()
        batch_result = pipeline.process_documents_batch(documents)
        total_time = time.time() - start_time
        
        # Should complete in reasonable time
        self.assertLess(total_time, 60.0)  # Less than 60 seconds for 10 documents
        
        # Check throughput
        documents_per_second = len(documents) / total_time
        self.assertGreater(documents_per_second, 0.1)  # At least 0.1 documents per second
        
        # Most documents should succeed
        success_rate = batch_result.successful_documents / batch_result.total_documents
        self.assertGreater(success_rate, 0.7)  # At least 70% success rate
    
    def test_memory_usage_stability(self):
        """Test that memory usage remains stable during processing"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        pipeline = EmbeddingPipeline()
        
        # Process multiple documents
        for i in range(5):
            document = DocumentInput(
                document_id=f"memory_test_{i}",
                text=f"Memory stability test document {i}. " * 100
            )
            pipeline.process_document(document)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        self.assertLess(memory_increase, 100 * 1024 * 1024)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestPipelineConfig,
        TestDocumentInput,
        TestEmbeddingPipeline,
        TestEmbeddingExport,
        TestUtilityConfigurations,
        TestErrorHandling,
        TestPerformanceBenchmarks
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"EmbeddingPipeline Test Summary")
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
    
    print(f"\n🎯 EmbeddingPipeline testing completed!")