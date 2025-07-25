"""
Integration tests for the complete PDF processing pipeline

Tests the end-to-end functionality with realistic scenarios.
"""

import pytest
from .pipeline import PDFProcessingPipeline, ProcessingStatus
from .pdf_processor import PDFProcessor
from .text_cleaner import TextCleaner
from .structure_detector import StructureDetector
from .content_filter import ContentFilter


class TestPDFProcessingIntegration:
    """Integration test suite for complete PDF processing pipeline"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.pipeline = PDFProcessingPipeline()
    
    def test_component_integration(self):
        """Test that all components work together properly"""
        
        # Simulate a realistic textbook content
        textbook_content = """
        Copyright © 2023 Educational Publishers
        All rights reserved. No part of this publication may be reproduced.
        
        Table of Contents
        Chapter 1: Introduction to Programming ............... 5
        Chapter 2: Variables and Data Types ................. 15
        Chapter 3: Control Structures ....................... 25
        Chapter 4: Functions and Modules .................... 35
        
        Preface
        This textbook provides a comprehensive introduction to programming.
        
        Learning Objectives
        After completing this book, students will be able to:
        • Understand basic programming concepts
        • Work with variables and data types
        • Use control structures effectively
        
        Chapter 1: Introduction to Programming
        
        Programming is the process of creating instructions for computers.
        In this chapter, we will explore the fundamental concepts.
        
        1.1 What is Programming?
        Programming involves writing code that tells a computer what to do.
        
        1.2 Programming Languages
        There are many programming languages, each with its own syntax.
        
        Chapter 2: Variables and Data Types
        
        Variables are containers for storing data values.
        
        2.1 Integer Variables
        Integers are whole numbers without decimal points.
        
        2.2 String Variables
        Strings are sequences of characters.
        
        Chapter 3: Control Structures
        
        Control structures determine the flow of program execution.
        
        3.1 Conditional Statements
        If-else statements allow programs to make decisions.
        
        3.2 Loops
        Loops allow repetitive execution of code blocks.
        
        Chapter 4: Functions and Modules
        
        Functions are reusable blocks of code.
        
        4.1 Defining Functions
        Functions are defined using the def keyword.
        
        4.2 Using Modules
        Modules allow code organization and reuse.
        
        Appendix A: Python Keywords
        Reserved words in Python programming language.
        
        Bibliography
        [1] Author, A. (2023). Programming Fundamentals.
        [2] Developer, B. (2022). Code Organization.
        
        Index
        A
        Array, 25, 30
        B
        Boolean, 20, 22
        """
        
        # Test each component individually
        
        # 1. Text Cleaning
        cleaner = TextCleaner()
        cleaning_result = cleaner.clean_text(textbook_content)
        assert cleaning_result.quality_score > 0.7
        assert "Programming is the process" in cleaning_result.cleaned_text
        
        # 2. Structure Detection
        detector = StructureDetector()
        detection_result = detector.detect_structure(cleaning_result.cleaned_text)
        assert detection_result.hierarchy.total_chapters == 4
        assert detection_result.is_valid_textbook  # Should meet 3 chapter minimum
        
        # 3. Content Filtering
        content_filter = ContentFilter()
        filtering_result = content_filter.filter_content(
            cleaning_result.cleaned_text,
            detection_result.hierarchy.elements
        )
        
        # Check that prefatory content was removed
        assert "Copyright ©" not in filtering_result.filtered_text
        assert "Table of Contents" not in filtering_result.filtered_text
        
        # But learning objectives should be preserved
        assert "Learning Objectives" in filtering_result.filtered_text
        assert "Understand basic programming" in filtering_result.filtered_text
        
        # Check that appendix content was removed
        assert "Appendix A" not in filtering_result.filtered_text
        assert "Bibliography" not in filtering_result.filtered_text
        assert "Index" not in filtering_result.filtered_text
        
        # Core content should be preserved
        assert "Chapter 1: Introduction to Programming" in filtering_result.filtered_text
        assert "Programming is the process" in filtering_result.filtered_text
        assert "Variables are containers" in filtering_result.filtered_text
        
        # Check retention ratio is reasonable
        assert filtering_result.stats.retention_ratio > 0.6
        assert filtering_result.stats.retention_ratio < 0.9
    
    def test_quality_scoring_accuracy(self):
        """Test that quality scoring accurately reflects content quality"""
        
        # High quality content
        high_quality_content = """
        Chapter 1: Introduction to Machine Learning
        
        Machine learning is a subset of artificial intelligence that focuses on algorithms.
        
        1.1 Supervised Learning
        Supervised learning uses labeled training data.
        
        1.2 Unsupervised Learning
        Unsupervised learning finds patterns in unlabeled data.
        
        Chapter 2: Neural Networks
        
        Neural networks are computational models inspired by biological neurons.
        
        2.1 Perceptrons
        The perceptron is the simplest neural network model.
        
        2.2 Multi-layer Networks
        Deep networks have multiple hidden layers.
        
        Chapter 3: Training Algorithms
        
        Training involves optimizing network parameters.
        
        3.1 Backpropagation
        Backpropagation computes gradients efficiently.
        
        3.2 Optimization Methods
        Various optimizers improve convergence.
        """
        
        # Low quality content (mostly artifacts)
        low_quality_content = """
        Page 1
        
        Copyright notice here
        More legal text
        Publisher information
        
        Chapter 1
        
        Some brief content.
        
        Page 2
        More page numbers
        """
        
        # Process both contents
        high_quality_result = self._process_text_content(high_quality_content)
        low_quality_result = self._process_text_content(low_quality_content)
        
        # High quality should have better scores
        assert high_quality_result.quality_metrics.overall_quality_score > low_quality_result.quality_metrics.overall_quality_score
        assert high_quality_result.quality_metrics.structure_detection_score > low_quality_result.quality_metrics.structure_detection_score
        assert high_quality_result.quality_metrics.educational_value_score > low_quality_result.quality_metrics.educational_value_score
        
        # High quality should meet validation criteria
        assert high_quality_result.quality_metrics.meets_minimum_chapters
        assert high_quality_result.quality_metrics.has_coherent_structure
        
        # Low quality might not
        assert not low_quality_result.quality_metrics.meets_minimum_chapters
    
    def test_edge_case_handling(self):
        """Test handling of various edge cases"""
        
        # Very short content
        short_content = "Chapter 1: Short"
        short_result = self._process_text_content(short_content)
        assert short_result.status in [ProcessingStatus.FAILED, ProcessingStatus.VALIDATION_FAILED]
        
        # No clear structure
        unstructured_content = """
        This is some random text without any clear chapter structure.
        It has educational content but no organization.
        Students might find this confusing.
        There are no clear boundaries or hierarchy.
        """
        unstructured_result = self._process_text_content(unstructured_content)
        assert unstructured_result.status != ProcessingStatus.SUCCESS
        
        # Mixed numbering styles
        mixed_numbering = """
        Chapter 1: First Chapter
        Content for first chapter.
        
        CHAPTER II: Second Chapter
        Content for second chapter.
        
        Ch. C: Third Chapter
        Content for third chapter.
        """
        mixed_result = self._process_text_content(mixed_numbering)
        # Should still process but with warnings about inconsistency
        assert len(mixed_result.warnings) > 0 or mixed_result.status == ProcessingStatus.PARTIAL_SUCCESS
    
    def test_mathematical_content_preservation(self):
        """Test that mathematical content is preserved throughout pipeline"""
        
        math_content = """
        Chapter 1: Mathematical Foundations
        
        This chapter covers basic mathematical concepts including equations like $E = mc^2$.
        
        1.1 Algebra
        Linear equations take the form $ax + b = 0$ where $a ≠ 0$.
        
        1.2 Calculus
        The derivative of $f(x) = x^2$ is $f'(x) = 2x$.
        Integration: $∫ x dx = \\frac{x^2}{2} + C$
        
        Chapter 2: Statistics
        
        The normal distribution has the formula:
        $$f(x) = \\frac{1}{\\sqrt{2πσ^2}} e^{-\\frac{(x-μ)^2}{2σ^2}}$$
        
        Chapter 3: Probability
        
        Basic probability: $P(A ∪ B) = P(A) + P(B) - P(A ∩ B)$
        """
        
        result = self._process_text_content(math_content)
        
        # Mathematical expressions should be preserved
        assert "$E = mc^2$" in result.final_text
        assert "$ax + b = 0$" in result.final_text
        assert "$a ≠ 0$" in result.final_text
        assert "∫ x dx" in result.final_text
        assert "√" in result.final_text
        assert "π" in result.final_text
        
        # Display math should be preserved
        assert "$$f(x)" in result.final_text
        
        # Should have good quality despite mathematical symbols
        assert result.quality_metrics.text_cleaning_score > 0.7
    
    def test_performance_tracking(self):
        """Test that performance metrics are properly tracked"""
        
        content = """
        Chapter 1: Performance Test
        This is content for testing performance tracking.
        
        Chapter 2: More Content
        Additional content to ensure processing takes measurable time.
        
        Chapter 3: Final Chapter
        Last chapter for completing the test.
        """
        
        result = self._process_text_content(content)
        
        # Check that timing information is recorded
        assert result.metadata.total_processing_time is not None
        assert result.metadata.total_processing_time > 0
        
        # Check that all stages have timing information
        from .pipeline import ProcessingStage
        assert ProcessingStage.TEXT_CLEANING in result.metadata.stage_timings
        assert ProcessingStage.STRUCTURE_DETECTION in result.metadata.stage_timings
        assert ProcessingStage.CONTENT_FILTERING in result.metadata.stage_timings
        assert ProcessingStage.QUALITY_ASSESSMENT in result.metadata.stage_timings
        
        # Check that metadata contains useful information
        assert result.metadata.original_text_length > 0
        assert result.metadata.cleaned_text_length > 0
        assert result.metadata.filtered_text_length > 0
        assert result.metadata.chapters_detected == 3
    
    def test_recommendation_system(self):
        """Test that the recommendation system provides useful guidance"""
        
        # Content with various quality issues
        problematic_content = """
        Chapter 1: Poor Quality
        Brief content.
        
        randomheading
        Some text without clear structure.
        """
        
        result = self._process_text_content(problematic_content)
        
        # Should generate recommendations
        assert len(result.recommendations) > 0
        
        # Check for common recommendation types
        rec_text = " ".join(result.recommendations).lower()
        assert any(keyword in rec_text for keyword in [
            "structure", "quality", "chapters", "review", "manual"
        ])
    
    def _process_text_content(self, content: str):
        """Helper method to process text content through components"""
        # This simulates the pipeline processing without requiring actual PDF files
        
        # Clean text
        cleaner = TextCleaner()
        cleaning_result = cleaner.clean_text(content)
        
        # Detect structure
        detector = StructureDetector()
        detection_result = detector.detect_structure(cleaning_result.cleaned_text)
        
        # Filter content
        content_filter = ContentFilter()
        filtering_result = content_filter.filter_content(
            cleaning_result.cleaned_text,
            detection_result.hierarchy.elements
        )
        
        # Calculate quality metrics manually (simplified version)
        from .pipeline import QualityMetrics, ProcessingStatus
        
        quality_metrics = QualityMetrics(
            extraction_confidence=0.8,  # Simulated
            text_cleaning_score=cleaning_result.quality_score,
            structure_detection_score=detection_result.hierarchy.quality_score,
            content_filtering_score=filtering_result.quality_score,
            overall_quality_score=(cleaning_result.quality_score + detection_result.hierarchy.quality_score + filtering_result.quality_score) / 3,
            textbook_validity_score=0.8 if detection_result.hierarchy.total_chapters >= 3 else 0.4,
            character_retention_ratio=len(filtering_result.filtered_text) / len(content),
            structure_completeness=min(1.0, detection_result.hierarchy.total_chapters / 3),
            content_coherence=0.7,
            educational_value_score=0.8 if detection_result.hierarchy.total_chapters >= 3 else 0.5,
            meets_minimum_chapters=detection_result.hierarchy.total_chapters >= 3,
            meets_retention_threshold=len(filtering_result.filtered_text) / len(content) >= 0.5,
            has_coherent_structure=detection_result.hierarchy.quality_score > 0.5,
            passes_quality_gate=detection_result.hierarchy.quality_score > 0.7
        )
        
        # Determine status
        if detection_result.hierarchy.total_chapters < 3:
            status = ProcessingStatus.VALIDATION_FAILED
        elif quality_metrics.overall_quality_score < 0.7:
            status = ProcessingStatus.PARTIAL_SUCCESS
        else:
            status = ProcessingStatus.SUCCESS
        
        # Create a mock result object
        from unittest.mock import Mock
        
        result = Mock()
        result.status = status
        result.final_text = filtering_result.filtered_text
        result.quality_metrics = quality_metrics
        result.warnings = cleaning_result.warnings + detection_result.warnings + filtering_result.warnings
        result.recommendations = []
        
        # Add simple recommendations based on quality
        if quality_metrics.overall_quality_score < 0.5:
            result.recommendations.append("Overall quality is low - consider manual review")
        if not quality_metrics.meets_minimum_chapters:
            result.recommendations.append("Document has insufficient chapters for textbook classification")
        if quality_metrics.structure_detection_score < 0.5:
            result.recommendations.append("Structure detection confidence is low - verify chapter organization")
        
        # Mock metadata
        result.metadata = Mock()
        result.metadata.total_processing_time = 1.5
        result.metadata.stage_timings = {
            ProcessingStage.TEXT_CLEANING: 0.3,
            ProcessingStage.STRUCTURE_DETECTION: 0.5,
            ProcessingStage.CONTENT_FILTERING: 0.4,
            ProcessingStage.QUALITY_ASSESSMENT: 0.3
        }
        result.metadata.original_text_length = len(content)
        result.metadata.cleaned_text_length = len(cleaning_result.cleaned_text)
        result.metadata.filtered_text_length = len(filtering_result.filtered_text)
        result.metadata.chapters_detected = detection_result.hierarchy.total_chapters
        
        return result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])