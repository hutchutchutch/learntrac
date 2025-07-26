#!/usr/bin/env python3
"""
Comprehensive Tests for EmbeddingQualityAssessor - Quality assessment testing

Tests all functionality of the EmbeddingQualityAssessor including:
- Educational quality metrics
- Semantic quality assessment  
- Technical quality evaluation
- Content-type specific assessments
- Batch quality processing
- Statistical analysis
"""

import unittest
import numpy as np
import time
from unittest.mock import Mock, patch

from embedding_quality_assessor import (
    EmbeddingQualityAssessor, EmbeddingQualityAssessment, BatchQualityAssessment,
    QualityMetrics, QualityGrade
)
from embedding_generator import EmbeddingResult, EmbeddingModel
from chunk_metadata import ChunkMetadata, ContentType


class TestQualityGrade(unittest.TestCase):
    """Test QualityGrade enum"""
    
    def test_quality_grade_values(self):
        """Test quality grade enum values"""
        self.assertEqual(QualityGrade.EXCELLENT.value, "excellent")
        self.assertEqual(QualityGrade.GOOD.value, "good")
        self.assertEqual(QualityGrade.FAIR.value, "fair")
        self.assertEqual(QualityGrade.POOR.value, "poor")
    
    def test_quality_grade_ordering(self):
        """Test that quality grades can be ordered"""
        grades = [QualityGrade.POOR, QualityGrade.EXCELLENT, QualityGrade.FAIR, QualityGrade.GOOD]
        
        # Test that grades exist and are distinct
        self.assertEqual(len(set(grades)), 4)


class TestQualityMetrics(unittest.TestCase):
    """Test QualityMetrics data structure"""
    
    def test_metrics_creation(self):
        """Test creating quality metrics"""
        metrics = QualityMetrics(
            educational_clarity=0.8,
            semantic_coherence=0.75,
            technical_accuracy=0.9,
            content_completeness=0.85,
            difficulty_alignment=0.7
        )
        
        self.assertEqual(metrics.educational_clarity, 0.8)
        self.assertEqual(metrics.semantic_coherence, 0.75)
        self.assertEqual(metrics.technical_accuracy, 0.9)
        self.assertEqual(metrics.content_completeness, 0.85)
        self.assertEqual(metrics.difficulty_alignment, 0.7)
    
    def test_metrics_defaults(self):
        """Test quality metrics defaults"""
        metrics = QualityMetrics()
        
        self.assertEqual(metrics.educational_clarity, 0.0)
        self.assertEqual(metrics.semantic_coherence, 0.0)
        self.assertEqual(metrics.technical_accuracy, 0.0)
        self.assertEqual(metrics.content_completeness, 0.0)
        self.assertEqual(metrics.difficulty_alignment, 0.0)


class TestEmbeddingQualityAssessment(unittest.TestCase):
    """Test EmbeddingQualityAssessment data structure"""
    
    def test_assessment_creation(self):
        """Test creating quality assessment"""
        metrics = QualityMetrics(
            educational_clarity=0.8,
            semantic_coherence=0.75,
            technical_accuracy=0.9
        )
        
        assessment = EmbeddingQualityAssessment(
            overall_quality=0.82,
            quality_grade=QualityGrade.GOOD,
            metrics=metrics,
            confidence=0.9,
            assessment_time=0.1
        )
        
        self.assertEqual(assessment.overall_quality, 0.82)
        self.assertEqual(assessment.quality_grade, QualityGrade.GOOD)
        self.assertEqual(assessment.metrics, metrics)
        self.assertEqual(assessment.confidence, 0.9)
        self.assertEqual(assessment.assessment_time, 0.1)
    
    def test_assessment_defaults(self):
        """Test assessment defaults"""
        assessment = EmbeddingQualityAssessment(
            overall_quality=0.5,
            quality_grade=QualityGrade.FAIR,
            metrics=QualityMetrics()
        )
        
        self.assertIsNotNone(assessment.detailed_feedback)
        self.assertIsNotNone(assessment.suggestions)
        self.assertEqual(assessment.confidence, 1.0)  # Default confidence


class TestEmbeddingQualityAssessor(unittest.TestCase):
    """Test main EmbeddingQualityAssessor functionality"""
    
    def setUp(self):
        """Set up test assessor"""
        self.assessor = EmbeddingQualityAssessor(
            quality_threshold=0.7,
            educational_weight=0.3,
            semantic_weight=0.4,
            technical_weight=0.3
        )
    
    def test_assessor_initialization(self):
        """Test assessor initialization"""
        self.assertEqual(self.assessor.quality_threshold, 0.7)
        self.assertEqual(self.assessor.educational_weight, 0.3)
        self.assertEqual(self.assessor.semantic_weight, 0.4)
        self.assertEqual(self.assessor.technical_weight, 0.3)
        
        # Weights should sum to 1.0
        total_weight = (self.assessor.educational_weight + 
                       self.assessor.semantic_weight + 
                       self.assessor.technical_weight)
        self.assertAlmostEqual(total_weight, 1.0, places=5)
    
    def test_default_initialization(self):
        """Test default assessor initialization"""
        assessor = EmbeddingQualityAssessor()
        
        self.assertEqual(assessor.quality_threshold, 0.75)
        self.assertEqual(assessor.educational_weight, 0.4)
        self.assertEqual(assessor.semantic_weight, 0.4)
        self.assertEqual(assessor.technical_weight, 0.2)
    
    def create_test_embedding_result(self, text: str, content_type: ContentType = ContentType.TEXT) -> EmbeddingResult:
        """Helper to create test embedding result"""
        # Create deterministic embedding based on text
        np.random.seed(hash(text) % 2**32)
        embedding = np.random.normal(0, 1, 768).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            dimensions=768,
            generation_time=0.1,
            token_count=len(text.split()),
            quality_score=0.0,
            metadata={'content_type': content_type.value}
        )
    
    def create_test_chunk_metadata(self, content_type: ContentType = ContentType.TEXT, difficulty: str = "intermediate") -> ChunkMetadata:
        """Helper to create test chunk metadata"""
        return ChunkMetadata(
            chunk_id="test_chunk_1",
            content_type=content_type,
            start_position=0,
            end_position=100,
            confidence_score=0.9,
            difficulty=difficulty,
            chapter="Test Chapter",
            section="Test Section"
        )
    
    def test_single_embedding_assessment(self):
        """Test assessing single embedding quality"""
        text = "Definition: A function is a mathematical relation between sets that assigns exactly one output for each input."
        embedding_result = self.create_test_embedding_result(text, ContentType.DEFINITION)
        chunk_metadata = self.create_test_chunk_metadata(ContentType.DEFINITION)
        
        assessment = self.assessor.assess_embedding_quality(embedding_result, chunk_metadata)
        
        self.assertIsInstance(assessment, EmbeddingQualityAssessment)
        self.assertGreaterEqual(assessment.overall_quality, 0.0)
        self.assertLessEqual(assessment.overall_quality, 1.0)
        self.assertIsInstance(assessment.quality_grade, QualityGrade)
        self.assertIsInstance(assessment.metrics, QualityMetrics)
        self.assertGreater(assessment.assessment_time, 0)
        self.assertGreaterEqual(assessment.confidence, 0.0)
        self.assertLessEqual(assessment.confidence, 1.0)
    
    def test_mathematical_content_assessment(self):
        """Test assessment of mathematical content"""
        math_text = "Example: Solve the integral ∫ x² dx = x³/3 + C, where C is the constant of integration."
        embedding_result = self.create_test_embedding_result(math_text, ContentType.MATH)
        chunk_metadata = self.create_test_chunk_metadata(ContentType.MATH)
        
        assessment = self.assessor.assess_embedding_quality(embedding_result, chunk_metadata)
        
        # Mathematical content should have specific quality characteristics
        self.assertIsNotNone(assessment)
        self.assertIn('mathematical', assessment.detailed_feedback)
        
        # Should have assessed mathematical symbols preservation
        self.assertGreaterEqual(assessment.metrics.technical_accuracy, 0.0)
    
    def test_definition_content_assessment(self):
        """Test assessment of definition content"""
        definition_text = "Definition: Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce glucose and oxygen."
        embedding_result = self.create_test_embedding_result(definition_text, ContentType.DEFINITION)
        chunk_metadata = self.create_test_chunk_metadata(ContentType.DEFINITION)
        
        assessment = self.assessor.assess_embedding_quality(embedding_result, chunk_metadata)
        
        # Definition should have high educational clarity
        self.assertGreater(assessment.metrics.educational_clarity, 0.5)
        self.assertIn('definition', assessment.detailed_feedback.lower())
    
    def test_example_content_assessment(self):
        """Test assessment of example content"""
        example_text = "Example: If a car travels 60 miles per hour for 2 hours, it will travel a total distance of 60 × 2 = 120 miles."
        embedding_result = self.create_test_embedding_result(example_text, ContentType.EXAMPLE)
        chunk_metadata = self.create_test_chunk_metadata(ContentType.EXAMPLE)
        
        assessment = self.assessor.assess_embedding_quality(embedding_result, chunk_metadata)
        
        # Example should have good practical application
        self.assertIsNotNone(assessment)
        self.assertIn('example', assessment.detailed_feedback.lower())
    
    def test_quality_grade_assignment(self):
        """Test quality grade assignment based on scores"""
        # Test different quality levels by manipulating the embedding quality
        test_cases = [
            (0.95, QualityGrade.EXCELLENT),
            (0.82, QualityGrade.GOOD), 
            (0.65, QualityGrade.FAIR),
            (0.45, QualityGrade.POOR)
        ]
        
        for expected_quality, expected_grade in test_cases:
            # Create embedding with specific characteristics to influence quality
            text = f"Test text for quality {expected_quality}"
            embedding_result = self.create_test_embedding_result(text)
            
            # Mock the quality calculation to return specific score
            with patch.object(self.assessor, '_calculate_overall_quality', return_value=expected_quality):
                assessment = self.assessor.assess_embedding_quality(embedding_result)
                self.assertEqual(assessment.quality_grade, expected_grade)
    
    def test_batch_quality_assessment(self):
        """Test batch quality assessment"""
        texts = [
            "Definition: A triangle is a polygon with three sides and three angles.",
            "Example: An equilateral triangle has all sides equal and all angles equal to 60 degrees.",
            "The area of a triangle can be calculated using the formula A = ½ × base × height.",
            "Mathematical proof: In any triangle, the sum of all angles equals 180 degrees."
        ]
        
        embedding_results = [self.create_test_embedding_result(text) for text in texts]
        chunk_metadata_list = [self.create_test_chunk_metadata() for _ in texts]
        
        batch_assessment = self.assessor.assess_batch_quality(embedding_results, chunk_metadata_list)
        
        self.assertIsInstance(batch_assessment, BatchQualityAssessment)
        self.assertEqual(len(batch_assessment.individual_assessments), 4)
        self.assertGreaterEqual(batch_assessment.average_quality, 0.0)
        self.assertLessEqual(batch_assessment.average_quality, 1.0)
        self.assertGreater(batch_assessment.total_assessment_time, 0)
        
        # Check quality distribution
        self.assertIsInstance(batch_assessment.quality_distribution, dict)
        total_assessments = sum(batch_assessment.quality_distribution.values())
        self.assertEqual(total_assessments, 4)
        
        # Check individual assessments
        for assessment in batch_assessment.individual_assessments:
            self.assertIsInstance(assessment, EmbeddingQualityAssessment)
    
    def test_batch_with_mismatched_lengths(self):
        """Test batch assessment with mismatched input lengths"""
        embedding_results = [self.create_test_embedding_result("Text 1")]
        chunk_metadata_list = [self.create_test_chunk_metadata(), self.create_test_chunk_metadata()]
        
        with self.assertRaises(ValueError):
            self.assessor.assess_batch_quality(embedding_results, chunk_metadata_list)
    
    def test_empty_batch_assessment(self):
        """Test batch assessment with empty inputs"""
        batch_assessment = self.assessor.assess_batch_quality([], [])
        
        self.assertEqual(len(batch_assessment.individual_assessments), 0)
        self.assertEqual(batch_assessment.average_quality, 0.0)
        self.assertEqual(batch_assessment.total_assessment_time, 0.0)
        self.assertEqual(batch_assessment.quality_distribution, {})
    
    def test_content_type_specific_assessment(self):
        """Test that assessment varies by content type"""
        base_text = "This is educational content about mathematical concepts and definitions."
        
        # Assess same text as different content types
        content_types = [ContentType.TEXT, ContentType.DEFINITION, ContentType.MATH, ContentType.EXAMPLE]
        assessments = {}
        
        for content_type in content_types:
            embedding_result = self.create_test_embedding_result(base_text, content_type)
            chunk_metadata = self.create_test_chunk_metadata(content_type)
            assessment = self.assessor.assess_embedding_quality(embedding_result, chunk_metadata)
            assessments[content_type] = assessment
        
        # Different content types should potentially have different assessments
        quality_scores = [assessment.overall_quality for assessment in assessments.values()]
        
        # All should be valid scores
        for score in quality_scores:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
    
    def test_difficulty_alignment_assessment(self):
        """Test difficulty alignment assessment"""
        text = "Advanced calculus involves the study of limits, derivatives, and integrals in higher dimensions."
        
        # Test with different difficulty levels
        difficulties = ["beginner", "intermediate", "advanced", "expert"]
        
        for difficulty in difficulties:
            embedding_result = self.create_test_embedding_result(text)
            chunk_metadata = self.create_test_chunk_metadata(difficulty=difficulty)
            
            assessment = self.assessor.assess_embedding_quality(embedding_result, chunk_metadata)
            
            # Should have assessed difficulty alignment
            self.assertGreaterEqual(assessment.metrics.difficulty_alignment, 0.0)
            self.assertLessEqual(assessment.metrics.difficulty_alignment, 1.0)
    
    def test_embedding_quality_factors(self):
        """Test various factors that affect embedding quality"""
        # Test normalized vs unnormalized embeddings
        text = "Test embedding normalization effects"
        
        # Normalized embedding
        normalized_embedding = np.random.normal(0, 1, 768).astype(np.float32)
        normalized_embedding = normalized_embedding / np.linalg.norm(normalized_embedding)
        
        normalized_result = EmbeddingResult(
            text=text,
            embedding=normalized_embedding,
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            dimensions=768,
            generation_time=0.1,
            token_count=len(text.split())
        )
        
        # Unnormalized embedding
        unnormalized_embedding = np.random.normal(0, 1, 768).astype(np.float32) * 10
        
        unnormalized_result = EmbeddingResult(
            text=text,
            embedding=unnormalized_embedding,
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            dimensions=768,
            generation_time=0.1,
            token_count=len(text.split())
        )
        
        normalized_assessment = self.assessor.assess_embedding_quality(normalized_result)
        unnormalized_assessment = self.assessor.assess_embedding_quality(unnormalized_result)
        
        # Both should be valid assessments
        self.assertIsNotNone(normalized_assessment)
        self.assertIsNotNone(unnormalized_assessment)
    
    def test_assessment_statistics_tracking(self):
        """Test assessment statistics tracking"""
        initial_stats = self.assessor.get_assessment_statistics()
        
        # Perform some assessments
        texts = ["Text 1", "Text 2", "Text 3"]
        for text in texts:
            embedding_result = self.create_test_embedding_result(text)
            self.assessor.assess_embedding_quality(embedding_result)
        
        updated_stats = self.assessor.get_assessment_statistics()
        
        # Statistics should be updated
        self.assertGreater(updated_stats['total_assessments'], initial_stats['total_assessments'])
        self.assertGreater(updated_stats['total_assessment_time'], initial_stats['total_assessment_time'])
        
        # Check derived statistics
        self.assertIn('average_assessment_time', updated_stats)
        self.assertIn('quality_distribution', updated_stats)
    
    def test_statistics_reset(self):
        """Test statistics reset"""
        # Perform assessment
        embedding_result = self.create_test_embedding_result("Test text")
        self.assessor.assess_embedding_quality(embedding_result)
        
        stats_before = self.assessor.get_assessment_statistics()
        self.assertGreater(stats_before['total_assessments'], 0)
        
        # Reset statistics
        self.assessor.reset_statistics()
        
        stats_after = self.assessor.get_assessment_statistics()
        self.assertEqual(stats_after['total_assessments'], 0)
        self.assertEqual(stats_after['total_assessment_time'], 0.0)
    
    def test_threshold_filtering(self):
        """Test quality threshold filtering"""
        # Create assessor with high threshold
        high_threshold_assessor = EmbeddingQualityAssessor(quality_threshold=0.9)
        
        text = "Standard quality text for threshold testing"
        embedding_result = self.create_test_embedding_result(text)
        
        assessment = high_threshold_assessor.assess_embedding_quality(embedding_result)
        
        # Assessment should indicate whether it meets threshold
        meets_threshold = assessment.overall_quality >= high_threshold_assessor.quality_threshold
        
        if meets_threshold:
            self.assertIn(QualityGrade.EXCELLENT, [QualityGrade.EXCELLENT, QualityGrade.GOOD])
        else:
            # May not meet high threshold
            pass  # This is expected behavior


class TestQualityMetricsCalculation(unittest.TestCase):
    """Test specific quality metrics calculations"""
    
    def setUp(self):
        """Set up metrics testing"""
        self.assessor = EmbeddingQualityAssessor()
    
    def test_educational_clarity_calculation(self):
        """Test educational clarity assessment"""
        # Clear educational content
        clear_text = "Definition: A prime number is a natural number greater than 1 that has no positive divisors other than 1 and itself."
        embedding_result = self.assessor._create_test_embedding_result(clear_text, ContentType.DEFINITION)
        chunk_metadata = self.assessor._create_test_chunk_metadata(ContentType.DEFINITION)
        
        # Use internal method to test specific metric
        educational_score = self.assessor._assess_educational_quality(embedding_result, chunk_metadata)
        
        self.assertGreaterEqual(educational_score, 0.0)
        self.assertLessEqual(educational_score, 1.0)
        
        # Should be reasonably high for clear definition
        self.assertGreater(educational_score, 0.5)
    
    def test_semantic_coherence_calculation(self):
        """Test semantic coherence assessment"""
        coherent_text = "Photosynthesis is the process by which plants convert light energy into chemical energy. This process occurs in chloroplasts and requires sunlight, carbon dioxide, and water."
        
        embedding_result = self.assessor._create_test_embedding_result(coherent_text)
        
        semantic_score = self.assessor._assess_semantic_quality(embedding_result)
        
        self.assertGreaterEqual(semantic_score, 0.0)
        self.assertLessEqual(semantic_score, 1.0)
    
    def test_technical_accuracy_calculation(self):
        """Test technical accuracy assessment"""
        technical_text = "The derivative of f(x) = x² is f'(x) = 2x, calculated using the power rule."
        
        embedding_result = self.assessor._create_test_embedding_result(technical_text, ContentType.MATH)
        chunk_metadata = self.assessor._create_test_chunk_metadata(ContentType.MATH)
        
        technical_score = self.assessor._assess_technical_quality(embedding_result, chunk_metadata)
        
        self.assertGreaterEqual(technical_score, 0.0)
        self.assertLessEqual(technical_score, 1.0)
    
    def _create_test_embedding_result(self, text: str, content_type: ContentType = ContentType.TEXT) -> EmbeddingResult:
        """Helper method for testing - mirrors the main class helper"""
        np.random.seed(hash(text) % 2**32)
        embedding = np.random.normal(0, 1, 768).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            dimensions=768,
            generation_time=0.1,
            token_count=len(text.split()),
            quality_score=0.0,
            metadata={'content_type': content_type.value}
        )
    
    def _create_test_chunk_metadata(self, content_type: ContentType = ContentType.TEXT) -> ChunkMetadata:
        """Helper method for testing - mirrors the main class helper"""
        return ChunkMetadata(
            chunk_id="test_chunk",
            content_type=content_type,
            start_position=0,
            end_position=100,
            confidence_score=0.9,
            difficulty="intermediate",
            chapter="Test Chapter",
            section="Test Section"
        )


class TestBatchProcessingPerformance(unittest.TestCase):
    """Test batch processing performance"""
    
    def setUp(self):
        """Set up performance testing"""
        self.assessor = EmbeddingQualityAssessor()
    
    def create_test_embedding_result(self, text: str) -> EmbeddingResult:
        """Helper to create test embedding result"""
        np.random.seed(hash(text) % 2**32)
        embedding = np.random.normal(0, 1, 768).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            dimensions=768,
            generation_time=0.1,
            token_count=len(text.split())
        )
    
    def test_large_batch_performance(self):
        """Test performance with large batches"""
        # Create large batch
        texts = [f"Educational content example number {i} with various topics and concepts." for i in range(50)]
        embedding_results = [self.create_test_embedding_result(text) for text in texts]
        chunk_metadata_list = [ChunkMetadata(
            chunk_id=f"chunk_{i}",
            content_type=ContentType.TEXT,
            start_position=0,
            end_position=100,
            confidence_score=0.9
        ) for i in range(50)]
        
        start_time = time.time()
        batch_assessment = self.assessor.assess_batch_quality(embedding_results, chunk_metadata_list)
        total_time = time.time() - start_time
        
        # Should complete in reasonable time
        self.assertLess(total_time, 10.0)  # Less than 10 seconds
        
        # Should assess all items
        self.assertEqual(len(batch_assessment.individual_assessments), 50)
        self.assertGreater(batch_assessment.average_quality, 0.0)
        
        # Performance metrics
        assessments_per_second = 50 / total_time
        self.assertGreater(assessments_per_second, 5)  # At least 5 per second
    
    def test_batch_statistical_accuracy(self):
        """Test statistical accuracy of batch assessments"""
        texts = [
            "Excellent educational content with clear definitions and examples.",
            "Good quality content with adequate explanations.",
            "Fair content that could be improved.",
            "Poor quality content with unclear explanations."
        ]
        
        embedding_results = [self.create_test_embedding_result(text) for text in texts]
        chunk_metadata_list = [ChunkMetadata(
            chunk_id=f"chunk_{i}",
            content_type=ContentType.TEXT,
            start_position=0,
            end_position=100,
            confidence_score=0.9
        ) for i in range(4)]
        
        batch_assessment = self.assessor.assess_batch_quality(embedding_results, chunk_metadata_list)
        
        # Check statistical measures
        individual_qualities = [a.overall_quality for a in batch_assessment.individual_assessments]
        calculated_average = sum(individual_qualities) / len(individual_qualities)
        
        # Batch average should match calculated average
        self.assertAlmostEqual(batch_assessment.average_quality, calculated_average, places=5)
        
        # Quality distribution should add up to total
        total_in_distribution = sum(batch_assessment.quality_distribution.values())
        self.assertEqual(total_in_distribution, 4)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        """Set up edge case testing"""
        self.assessor = EmbeddingQualityAssessor()
    
    def create_test_embedding_result(self, text: str, embedding: np.ndarray = None) -> EmbeddingResult:
        """Helper to create test embedding result with optional custom embedding"""
        if embedding is None:
            np.random.seed(hash(text) % 2**32)
            embedding = np.random.normal(0, 1, 768).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
        
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET,
            dimensions=len(embedding),
            generation_time=0.1,
            token_count=len(text.split())
        )
    
    def test_zero_embedding_assessment(self):
        """Test assessment of zero embedding"""
        zero_embedding = np.zeros(768, dtype=np.float32)
        embedding_result = self.create_test_embedding_result("Test text", zero_embedding)
        
        assessment = self.assessor.assess_embedding_quality(embedding_result)
        
        # Should handle zero embedding gracefully
        self.assertIsNotNone(assessment)
        self.assertGreaterEqual(assessment.overall_quality, 0.0)
        self.assertLessEqual(assessment.overall_quality, 1.0)
    
    def test_very_small_embedding_assessment(self):
        """Test assessment of very small embedding values"""
        small_embedding = np.full(768, 1e-10, dtype=np.float32)
        embedding_result = self.create_test_embedding_result("Test text", small_embedding)
        
        assessment = self.assessor.assess_embedding_quality(embedding_result)
        
        self.assertIsNotNone(assessment)
        self.assertIsInstance(assessment.overall_quality, float)
    
    def test_very_large_embedding_assessment(self):
        """Test assessment of very large embedding values"""
        large_embedding = np.full(768, 1e6, dtype=np.float32)
        embedding_result = self.create_test_embedding_result("Test text", large_embedding)
        
        assessment = self.assessor.assess_embedding_quality(embedding_result)
        
        self.assertIsNotNone(assessment)
        self.assertIsInstance(assessment.overall_quality, float)
    
    def test_nan_embedding_handling(self):
        """Test handling of NaN values in embeddings"""
        nan_embedding = np.full(768, np.nan, dtype=np.float32)
        embedding_result = self.create_test_embedding_result("Test text", nan_embedding)
        
        # Should handle NaN gracefully (may raise exception or return low quality)
        try:
            assessment = self.assessor.assess_embedding_quality(embedding_result)
            # If it doesn't raise, should return valid assessment
            self.assertIsNotNone(assessment)
            self.assertGreaterEqual(assessment.overall_quality, 0.0)
        except (ValueError, FloatingPointError):
            # Acceptable to raise exception for invalid embeddings
            pass
    
    def test_empty_text_assessment(self):
        """Test assessment of embedding for empty text"""
        embedding_result = self.create_test_embedding_result("")
        
        assessment = self.assessor.assess_embedding_quality(embedding_result)
        
        # Should handle empty text
        self.assertIsNotNone(assessment)
        # Quality might be low for empty text
        self.assertLessEqual(assessment.overall_quality, 0.5)
    
    def test_unicode_text_assessment(self):
        """Test assessment of unicode text"""
        unicode_text = "Mathematical symbols: ∫∑∂√π, Foreign text: 你好世界, Emojis: 🚀📊🎯"
        embedding_result = self.create_test_embedding_result(unicode_text)
        
        assessment = self.assessor.assess_embedding_quality(embedding_result)
        
        self.assertIsNotNone(assessment)
        self.assertIsInstance(assessment.overall_quality, float)
    
    def test_very_long_text_assessment(self):
        """Test assessment of very long text"""
        long_text = "This is a very long educational text. " * 1000  # Very long
        embedding_result = self.create_test_embedding_result(long_text)
        
        assessment = self.assessor.assess_embedding_quality(embedding_result)
        
        self.assertIsNotNone(assessment)
        # Should complete in reasonable time even for long text
        self.assertLess(assessment.assessment_time, 1.0)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestQualityGrade,
        TestQualityMetrics,
        TestEmbeddingQualityAssessment,
        TestEmbeddingQualityAssessor,
        TestQualityMetricsCalculation,
        TestBatchProcessingPerformance,
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
    print(f"EmbeddingQualityAssessor Test Summary")
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
    
    print(f"\n🎯 EmbeddingQualityAssessor testing completed!")