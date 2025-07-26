"""
Unit tests for ContentChunker (Hybrid Controller) class

Tests the main hybrid chunking controller that orchestrates strategy selection,
batch processing, and comprehensive chunking operations.
"""

import pytest
import time
from unittest.mock import Mock, patch
from .content_chunker import (
    ContentChunker,
    HybridChunkingResult,
    BatchChunkingResult,
    ChunkingRequest,
    ChunkingMode
)
from .chunk_metadata import ContentType
from .structure_detector import StructureElement, StructureType, NumberingStyle, DetectionResult, StructureHierarchy
from .structure_quality_assessor import QualityAssessment, ChunkingStrategy


class TestContentChunker:
    """Test the main hybrid ContentChunker controller"""
    
    def setup_method(self):
        self.chunker = ContentChunker(
            structure_quality_threshold=0.3,
            content_aware_target_size=500,  # Smaller for testing
            content_aware_min_size=100,
            content_aware_max_size=800,
            fallback_target_size=400,
            fallback_min_size=100,
            fallback_max_size=700,
            thread_safe=True,
            max_workers=2
        )
        
        # Sample educational content for testing
        self.structured_text = """
        Chapter 1: Introduction to Programming
        
        Programming is the process of creating instructions for computers.
        Definition: A program is a sequence of instructions that tells a computer what to do.
        
        1.1 What is Programming?
        
        Programming involves writing code in a programming language.
        For example, consider this Python code: print("Hello, World!").
        This program outputs text to the screen.
        
        The mathematical foundation involves algorithms with complexity O(n).
        We can express this as f(x) = x + 1 where x represents input size.
        
        1.2 Programming Languages
        
        There are many programming languages available today.
        Python is known for simplicity. Java is used for enterprise applications.
        """
        
        self.unstructured_text = """
        This is poorly structured text without clear organization.
        It flows continuously without obvious chapter or section markers.
        
        Sometimes there are mathematical concepts like f(x) = x² discussed.
        Definition: A variable is a named storage location for data.
        
        Example: Consider x = 5. This gives us a specific value to work with.
        Solution: We can use this value in calculations.
        
        The content continues with more educational material but lacks
        clear structural boundaries that would help with organization.
        """
        
        # Create structure elements for testing
        self.structure_elements = [
            StructureElement(
                type=StructureType.CHAPTER,
                title="Introduction to Programming",
                number="1",
                level=0,
                start_position=0,
                end_position=400,
                page_number=1,
                confidence=0.9,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="Chapter 1: Introduction to Programming"
            ),
            StructureElement(
                type=StructureType.SECTION,
                title="What is Programming?",
                number="1.1",
                level=1,
                start_position=150,
                end_position=300,
                page_number=1,
                confidence=0.8,
                numbering_style=NumberingStyle.DECIMAL,
                raw_text="1.1 What is Programming?"
            ),
            StructureElement(
                type=StructureType.SECTION,
                title="Programming Languages",
                number="1.2",
                level=1,
                start_position=300,
                end_position=len(self.structured_text),
                page_number=1,
                confidence=0.8,
                numbering_style=NumberingStyle.DECIMAL,
                raw_text="1.2 Programming Languages"
            )
        ]
    
    def test_content_aware_strategy_selection(self):
        """Test that high-quality structure selects content-aware strategy"""
        result = self.chunker.chunk_content(
            text=self.structured_text,
            book_id="structured_book",
            structure_elements=self.structure_elements,
            metadata_base={"title": "Programming Guide", "subject": "Computer Science"}
        )
        
        assert isinstance(result, HybridChunkingResult)
        assert result.strategy_used == ChunkingStrategy.CONTENT_AWARE
        assert len(result.chunks) > 0
        assert len(result.metadata_list) == len(result.chunks)
        
        # Check quality assessment
        assert result.quality_assessment is not None
        assert result.quality_assessment.overall_quality_score > 0.3
        
        # Check metadata
        for metadata in result.metadata_list:
            assert metadata.book_id == "structured_book"
            assert metadata.title == "Programming Guide"
            assert metadata.subject == "Computer Science"
            assert metadata.chunking_strategy == "content_aware"
    
    def test_fallback_strategy_selection(self):
        """Test that poor structure selects fallback strategy"""
        result = self.chunker.chunk_content(
            text=self.unstructured_text,
            book_id="unstructured_book",
            structure_elements=[],  # No structure
            metadata_base={"title": "Unstructured Content"}
        )
        
        assert isinstance(result, HybridChunkingResult)
        assert result.strategy_used == ChunkingStrategy.FALLBACK
        assert len(result.chunks) > 0
        assert len(result.metadata_list) == len(result.chunks)
        
        # Check quality assessment
        assert result.quality_assessment is not None
        assert result.quality_assessment.overall_quality_score <= 0.3
        
        # Check metadata
        for metadata in result.metadata_list:
            assert metadata.book_id == "unstructured_book"
            assert metadata.title == "Unstructured Content"
            assert metadata.chunking_strategy == "fallback"
    
    def test_forced_strategy_override(self):
        """Test forcing a specific strategy"""
        # Force fallback strategy on structured text
        result = self.chunker.chunk_content(
            text=self.structured_text,
            book_id="forced_book",
            structure_elements=self.structure_elements,
            force_strategy=ChunkingStrategy.FALLBACK
        )
        
        assert result.strategy_used == ChunkingStrategy.FALLBACK
        assert result.quality_assessment is None  # Should be None when forced
    
    def test_hybrid_strategy_execution(self):
        """Test hybrid strategy that tries content-aware then falls back"""
        # Create a chunker that will prefer hybrid strategy
        hybrid_chunker = ContentChunker(structure_quality_threshold=0.5)
        
        # Use borderline quality structure
        borderline_elements = self.structure_elements[:1]  # Only one chapter
        
        result = hybrid_chunker.chunk_content(
            text=self.structured_text,
            book_id="hybrid_book",
            structure_elements=borderline_elements,
            force_strategy=ChunkingStrategy.HYBRID
        )
        
        assert result.strategy_used == ChunkingStrategy.HYBRID
        assert len(result.chunks) > 0
    
    def test_empty_text_handling(self):
        """Test handling of empty text"""
        result = self.chunker.chunk_content(
            text="",
            book_id="empty_book"
        )
        
        assert len(result.chunks) == 0
        assert len(result.metadata_list) == 0
        assert len(result.warnings) > 0
        assert "Empty text" in result.warnings[0]
    
    def test_performance_metrics(self):
        """Test performance metrics calculation"""
        start_time = time.time()
        
        result = self.chunker.chunk_content(
            text=self.structured_text,
            book_id="perf_book",
            structure_elements=self.structure_elements
        )
        
        # Check performance metrics
        assert result.processing_time > 0
        assert result.chunks_per_second >= 0
        assert result.processing_time < 5.0  # Should be fast for small text
        
        if len(result.chunks) > 0:
            expected_rate = len(result.chunks) / result.processing_time
            assert abs(result.chunks_per_second - expected_rate) < 0.1
    
    def test_chunking_statistics(self):
        """Test comprehensive statistics calculation"""
        result = self.chunker.chunk_content(
            text=self.structured_text,
            book_id="stats_book",
            structure_elements=self.structure_elements
        )
        
        stats = result.chunking_statistics
        
        # Required statistics
        required_keys = [
            'total_chunks', 'avg_chunk_size', 'min_chunk_size', 'max_chunk_size',
            'total_characters', 'content_type_distribution', 'avg_confidence',
            'chunking_strategy', 'structure_quality_score'
        ]
        
        for key in required_keys:
            assert key in stats, f"Missing statistic: {key}"
        
        # Value validation
        assert stats['total_chunks'] == len(result.chunks)
        assert stats['total_characters'] == sum(len(chunk) for chunk in result.chunks)
        assert 0.0 <= stats['avg_confidence'] <= 1.0
        assert isinstance(stats['content_type_distribution'], dict)
        assert stats['chunking_strategy'] in ['content_aware', 'fallback', 'hybrid']
    
    def test_warning_generation(self):
        """Test warning generation for various issues"""
        # Test with very small chunks
        small_chunker = ContentChunker(
            content_aware_min_size=200,
            fallback_min_size=200
        )
        
        short_text = "This is very short text that might generate warnings."
        
        result = small_chunker.chunk_content(
            text=short_text,
            book_id="warning_book"
        )
        
        # Should generate warnings about chunk sizes or quality
        # (Exact warnings depend on implementation)
        if result.warnings:
            assert all(isinstance(warning, str) for warning in result.warnings)
    
    def test_recommendation_generation(self):
        """Test recommendation generation"""
        result = self.chunker.chunk_content(
            text=self.structured_text,
            book_id="rec_book",
            structure_elements=self.structure_elements
        )
        
        # Should have recommendations
        assert isinstance(result.recommendations, list)
        if result.recommendations:
            assert all(isinstance(rec, str) for rec in result.recommendations)
    
    def test_preprocessing_and_postprocessing(self):
        """Test text preprocessing and chunk postprocessing"""
        # Text with artifacts that should be cleaned
        dirty_text = """
        Page 1
        
        Chapter  1:   Introduction
        
        This   has   excessive   whitespace.
        
        
        
        Too many newlines here.
        
        ___________________________
        
        Page 2 - Header
        
        More content here.
        """
        
        result = self.chunker.chunk_content(
            text=dirty_text,
            book_id="clean_book"
        )
        
        # Text should be cleaned (preprocessing)
        combined_text = ' '.join(result.chunks)
        
        # Should not have excessive whitespace
        assert '   ' not in combined_text
        
        # Should not have page headers
        assert 'Page 1' not in combined_text
        assert 'Page 2' not in combined_text
        
        # Chunks should pass quality validation (postprocessing)
        for chunk in result.chunks:
            assert len(chunk.strip()) >= 50  # Minimum quality threshold
    
    def test_thread_safety(self):
        """Test thread-safe operations"""
        import threading
        
        results = []
        errors = []
        
        def chunk_text(text_id):
            try:
                result = self.chunker.chunk_content(
                    text=self.structured_text,
                    book_id=f"thread_book_{text_id}",
                    structure_elements=self.structure_elements
                )
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=chunk_text, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 5
        
        # All results should be valid
        for result in results:
            assert isinstance(result, HybridChunkingResult)
            assert len(result.chunks) > 0


class TestBatchChunking:
    """Test batch chunking functionality"""
    
    def setup_method(self):
        self.chunker = ContentChunker(max_workers=2)
        
        # Create multiple chunking requests
        self.requests = [
            ChunkingRequest(
                text="Chapter 1: First topic. This is structured content with clear organization.",
                book_id="batch_book_1",
                metadata_base={"title": "Book 1", "subject": "Topic A"}
            ),
            ChunkingRequest(
                text="Unstructured content that flows without clear boundaries or organization.",
                book_id="batch_book_2",
                metadata_base={"title": "Book 2", "subject": "Topic B"}
            ),
            ChunkingRequest(
                text="Chapter 2: Mathematics. The equation f(x) = x² + 1 represents a parabola.",
                book_id="batch_book_3",
                metadata_base={"title": "Book 3", "subject": "Mathematics"}
            )
        ]
    
    def test_parallel_batch_processing(self):
        """Test parallel batch processing"""
        start_time = time.time()
        
        result = self.chunker.chunk_batch(self.requests, max_workers=2)
        
        end_time = time.time()
        
        assert isinstance(result, BatchChunkingResult)
        assert result.total_documents == 3
        assert result.successful_documents == 3
        assert result.failed_documents == 0
        assert len(result.results) == 3
        assert len(result.errors) == 0
        
        # Check timing
        assert result.total_processing_time > 0
        assert result.total_processing_time <= end_time - start_time + 0.1  # Small tolerance
        
        # Check that all requests were processed
        book_ids = {r.metadata_list[0].book_id if r.metadata_list else None for r in result.results}
        expected_ids = {"batch_book_1", "batch_book_2", "batch_book_3"}
        assert book_ids == expected_ids
    
    def test_sequential_batch_processing(self):
        """Test sequential batch processing (max_workers=1)"""
        result = self.chunker.chunk_batch(self.requests, max_workers=1)
        
        assert isinstance(result, BatchChunkingResult)
        assert result.total_documents == 3
        assert result.successful_documents == 3
        assert result.failed_documents == 0
        assert len(result.results) == 3
    
    def test_batch_error_handling(self):
        """Test error handling in batch processing"""
        # Add a request that should fail
        error_requests = self.requests + [
            ChunkingRequest(
                text="",  # Empty text might cause issues
                book_id="error_book",
                metadata_base={}
            )
        ]
        
        result = self.chunker.chunk_batch(error_requests)
        
        # Should handle the error gracefully
        assert result.total_documents == 4
        assert result.successful_documents >= 3  # At least the good ones
        
        # Empty text should either succeed (with empty result) or fail gracefully
        if result.failed_documents > 0:
            assert len(result.errors) > 0
    
    def test_batch_statistics(self):
        """Test batch processing statistics"""
        result = self.chunker.chunk_batch(self.requests)
        
        stats = result.batch_statistics
        
        # Required batch statistics
        required_keys = [
            'strategy_distribution', 'total_chunks_created', 'total_characters_processed',
            'avg_processing_time_per_doc', 'avg_chunks_per_doc', 'throughput_docs_per_second'
        ]
        
        for key in required_keys:
            assert key in stats, f"Missing batch statistic: {key}"
        
        # Value validation
        assert stats['total_chunks_created'] > 0
        assert stats['total_characters_processed'] > 0
        assert stats['avg_processing_time_per_doc'] > 0
        assert stats['avg_chunks_per_doc'] > 0
        assert stats['throughput_docs_per_second'] > 0


class TestGlobalStatistics:
    """Test global processing statistics"""
    
    def setup_method(self):
        self.chunker = ContentChunker()
    
    def test_statistics_tracking(self):
        """Test that global statistics are tracked correctly"""
        # Reset statistics
        self.chunker.reset_statistics()
        
        initial_stats = self.chunker.get_processing_statistics()
        assert initial_stats['total_documents'] == 0
        assert initial_stats['total_chunks_created'] == 0
        
        # Process some documents
        self.chunker.chunk_content(
            text="Chapter 1: Test content with structure.",
            book_id="stats_test_1",
            structure_elements=[
                StructureElement(
                    type=StructureType.CHAPTER,
                    title="Test",
                    number="1",
                    level=0,
                    start_position=0,
                    end_position=50,
                    page_number=1,
                    confidence=0.9,
                    numbering_style=NumberingStyle.ARABIC,
                    raw_text="Chapter 1: Test"
                )
            ]
        )
        
        self.chunker.chunk_content(
            text="Unstructured content without clear organization.",
            book_id="stats_test_2",
            structure_elements=[]
        )
        
        # Check updated statistics
        final_stats = self.chunker.get_processing_statistics()
        
        assert final_stats['total_documents'] == 2
        assert final_stats['total_chunks_created'] > 0
        assert final_stats['content_aware_used'] >= 1
        assert final_stats['fallback_used'] >= 1
        assert final_stats['total_processing_time'] > 0
        
        # Should have averages
        if 'avg_chunks_per_doc' in final_stats:
            expected_avg = final_stats['total_chunks_created'] / final_stats['total_documents']
            assert abs(final_stats['avg_chunks_per_doc'] - expected_avg) < 0.1
    
    def test_statistics_reset(self):
        """Test statistics reset functionality"""
        # Process a document
        self.chunker.chunk_content(
            text="Test content for statistics.",
            book_id="reset_test"
        )
        
        # Check statistics exist
        stats_before = self.chunker.get_processing_statistics()
        assert stats_before['total_documents'] > 0
        
        # Reset statistics
        self.chunker.reset_statistics()
        
        # Check statistics are reset
        stats_after = self.chunker.get_processing_statistics()
        assert stats_after['total_documents'] == 0
        assert stats_after['total_chunks_created'] == 0
        assert stats_after['total_processing_time'] == 0.0


class TestContentTypeDetection:
    """Test content type detection across strategies"""
    
    def setup_method(self):
        self.chunker = ContentChunker()
    
    def test_mathematical_content_detection(self):
        """Test detection of mathematical content"""
        math_text = """
        Mathematical Analysis
        
        The integral ∫f(x)dx represents the area under curve f(x).
        Consider the equation $E = mc^2$ which shows energy-mass equivalence.
        For polynomial f(x) = x² + 2x + 1, we can find roots using the quadratic formula.
        """
        
        result = self.chunker.chunk_content(
            text=math_text,
            book_id="math_detection"
        )
        
        # Should detect mathematical content
        math_chunks = [m for m in result.metadata_list if m.content_type == ContentType.MATH]
        assert len(math_chunks) > 0
        
        # Mathematical content should be preserved
        combined_text = ' '.join(result.chunks)
        assert '$E = mc^2$' in combined_text
        assert 'f(x) = x² + 2x + 1' in combined_text
    
    def test_definition_detection(self):
        """Test detection of definitions"""
        def_text = """
        Basic Concepts
        
        Definition 1.1: A function is a relation between sets where each input
        maps to exactly one output. This property distinguishes functions from
        general relations.
        
        We define a variable as a named storage location that can hold different
        types of data during program execution.
        """
        
        result = self.chunker.chunk_content(
            text=def_text,
            book_id="def_detection"
        )
        
        # Should detect definitions
        def_chunks = [m for m in result.metadata_list if m.content_type == ContentType.DEFINITION]
        assert len(def_chunks) > 0
        
        # Definitions should be preserved with explanations
        combined_text = ' '.join(result.chunks)
        assert 'Definition 1.1' in combined_text
        assert 'each input maps to exactly one output' in combined_text
    
    def test_example_detection(self):
        """Test detection of examples"""
        example_text = """
        Practical Applications
        
        Example 1: Calculate the derivative of f(x) = x³.
        Solution: Using the power rule, f'(x) = 3x².
        
        Exercise 2.1: Solve the equation 2x + 3 = 7.
        Answer: Subtracting 3 from both sides gives 2x = 4, so x = 2.
        """
        
        result = self.chunker.chunk_content(
            text=example_text,
            book_id="example_detection"
        )
        
        # Should detect examples
        example_chunks = [m for m in result.metadata_list if m.content_type == ContentType.EXAMPLE]
        assert len(example_chunks) > 0
        
        # Examples should be preserved with solutions
        combined_text = ' '.join(result.chunks)
        assert 'Example 1' in combined_text
        assert 'Solution:' in combined_text
        assert 'Exercise 2.1' in combined_text
        assert 'Answer:' in combined_text


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def setup_method(self):
        self.chunker = ContentChunker()
    
    def test_very_long_text(self):
        """Test handling of very long text"""
        # Create a long text
        long_text = "This is a sentence that will be repeated many times. " * 1000
        
        result = self.chunker.chunk_content(
            text=long_text,
            book_id="long_text_test"
        )
        
        assert len(result.chunks) > 10  # Should create many chunks
        
        # All chunks should respect size constraints
        for chunk in result.chunks:
            assert len(chunk) <= self.chunker.max_workers * 1.1  # Small tolerance
    
    def test_mixed_content_types(self):
        """Test text with mixed content types"""
        mixed_text = """
        Chapter 1: Mixed Content
        
        This chapter contains various types of educational content.
        
        Definition: Integration is the reverse process of differentiation.
        It allows us to find areas under curves.
        
        The mathematical formula is ∫f(x)dx = F(x) + C where F'(x) = f(x).
        
        Example: Find ∫x²dx.
        Solution: Using the power rule, ∫x²dx = x³/3 + C.
        
        Regular explanatory text continues here with additional concepts
        that students need to understand for comprehensive learning.
        """
        
        result = self.chunker.chunk_content(
            text=mixed_text,
            book_id="mixed_content"
        )
        
        # Should detect multiple content types
        content_types = set(m.content_type for m in result.metadata_list)
        assert len(content_types) > 1
        
        # Should preserve different content types appropriately
        combined_text = ' '.join(result.chunks)
        assert 'Definition:' in combined_text
        assert '∫f(x)dx' in combined_text
        assert 'Example:' in combined_text
        assert 'Solution:' in combined_text
    
    def test_invalid_structure_elements(self):
        """Test handling of invalid structure elements"""
        # Structure elements with invalid positions
        invalid_elements = [
            StructureElement(
                type=StructureType.CHAPTER,
                title="Invalid Chapter",
                number="1",
                level=0,
                start_position=-10,  # Invalid
                end_position=1000000,  # Way beyond text
                page_number=1,
                confidence=0.9,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="Chapter 1: Invalid"
            )
        ]
        
        # Should handle gracefully without crashing
        result = self.chunker.chunk_content(
            text="Short valid text content.",
            book_id="invalid_structure",
            structure_elements=invalid_elements
        )
        
        assert isinstance(result, HybridChunkingResult)
        # Should either ignore invalid structure or handle it gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])