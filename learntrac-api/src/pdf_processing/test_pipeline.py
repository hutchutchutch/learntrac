"""
Unit tests for PDFProcessingPipeline - Integration Testing

Tests the complete PDF processing pipeline including all components
and their integration with quality scoring and validation.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from .pipeline import (
    PDFProcessingPipeline,
    ProcessingStatus,
    ProcessingStage,
    QualityMetrics,
    ProcessingResult
)
from .pdf_processor import ExtractionResult, ExtractionMethod
from .text_cleaner import CleaningResult, CleaningStats
from .structure_detector import DetectionResult, StructureHierarchy, StructureElement, StructureType
from .content_filter import FilteringResult, FilteringStats, ContentType


class TestPDFProcessingPipeline:
    """Test suite for PDFProcessingPipeline integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.pipeline = PDFProcessingPipeline(
            min_chapters=3,
            min_retention_ratio=0.5,
            quality_threshold=0.7
        )
    
    def test_init_default(self):
        """Test pipeline initialization with defaults"""
        pipeline = PDFProcessingPipeline()
        assert pipeline.min_chapters == 3
        assert pipeline.min_retention_ratio == 0.5
        assert pipeline.quality_threshold == 0.7
        assert pipeline.preserve_mathematical is True
        assert pipeline.aggressive_filtering is False
    
    def test_init_custom(self):
        """Test pipeline initialization with custom settings"""
        pipeline = PDFProcessingPipeline(
            min_chapters=5,
            min_retention_ratio=0.6,
            quality_threshold=0.8,
            preserve_mathematical=False,
            aggressive_filtering=True
        )
        assert pipeline.min_chapters == 5
        assert pipeline.min_retention_ratio == 0.6
        assert pipeline.quality_threshold == 0.8
        assert pipeline.preserve_mathematical is False
        assert pipeline.aggressive_filtering is True
    
    def test_process_nonexistent_file(self):
        """Test processing non-existent file"""
        result = self.pipeline.process_pdf("/nonexistent/file.pdf")
        
        assert result.status == ProcessingStatus.FAILED
        assert "File not found" in result.errors[0]
        assert result.final_text == ""
        assert result.quality_metrics.overall_quality_score == 0.0
    
    @patch('pdf_processing.pipeline.PDFProcessor')
    @patch('pdf_processing.pipeline.TextCleaner')
    @patch('pdf_processing.pipeline.StructureDetector')
    @patch('pdf_processing.pipeline.ContentFilter')
    def test_successful_pipeline_execution(self, mock_filter, mock_detector, mock_cleaner, mock_processor):
        """Test successful execution of complete pipeline"""
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"fake pdf content")
            temp_path = temp_file.name
        
        try:
            # Setup mocks for successful processing
            mock_extraction = ExtractionResult(
                text="Chapter 1: Introduction\nThis is educational content.\n\nChapter 2: Advanced Topics\nMore content here.",
                page_count=10,
                method_used=ExtractionMethod.FITZ,
                confidence_score=0.9,
                metadata={'title': 'Test Book'}
            )
            mock_processor.return_value.extract_text.return_value = mock_extraction
            
            mock_cleaning = CleaningResult(
                cleaned_text="Chapter 1: Introduction\nThis is educational content.\n\nChapter 2: Advanced Topics\nMore content here.",
                stats=CleaningStats(100, 95, 2, 1, 0, 0, 0, 1, {}),
                quality_score=0.85,
                warnings=[]
            )
            mock_cleaner.return_value.clean_text.return_value = mock_cleaning
            
            # Mock structure elements
            mock_elements = [
                Mock(type=StructureType.CHAPTER, title="Introduction", level=0, start_position=0, end_position=50),
                Mock(type=StructureType.CHAPTER, title="Advanced Topics", level=0, start_position=50, end_position=100)
            ]
            
            mock_detection = DetectionResult(
                hierarchy=StructureHierarchy(
                    elements=mock_elements,
                    total_chapters=2,
                    total_sections=0,
                    max_depth=0,
                    numbering_consistency=0.9,
                    overall_confidence=0.8,
                    quality_score=0.75
                ),
                is_valid_textbook=False,  # Only 2 chapters < min 3
                warnings=["Insufficient chapters"],
                statistics={}
            )
            mock_detector.return_value.detect_structure.return_value = mock_detection
            
            mock_filtering = FilteringResult(
                filtered_text="Chapter 1: Introduction\nThis is educational content.\n\nChapter 2: Advanced Topics\nMore content here.",
                stats=FilteringStats(95, 90, 2, 0, 0, 2, 0.95, {ContentType.CORE_CONTENT: 2}),
                sections=[],
                quality_score=0.8,
                warnings=[]
            )
            mock_filter.return_value.filter_content.return_value = mock_filtering
            
            # Process the PDF
            result = self.pipeline.process_pdf(temp_path)
            
            # Verify successful processing
            assert result.status in [ProcessingStatus.SUCCESS, ProcessingStatus.PARTIAL_SUCCESS]
            assert result.final_text != ""
            assert result.quality_metrics.overall_quality_score > 0
            assert result.metadata.total_processing_time is not None
            assert result.metadata.total_processing_time > 0
            
            # Verify all stages were executed
            assert ProcessingStage.PDF_EXTRACTION in result.metadata.stage_timings
            assert ProcessingStage.TEXT_CLEANING in result.metadata.stage_timings
            assert ProcessingStage.STRUCTURE_DETECTION in result.metadata.stage_timings
            assert ProcessingStage.CONTENT_FILTERING in result.metadata.stage_timings
            assert ProcessingStage.QUALITY_ASSESSMENT in result.metadata.stage_timings
            
            # Verify intermediate results are stored
            assert result.extraction_result is not None
            assert result.cleaning_result is not None
            assert result.detection_result is not None
            assert result.filtering_result is not None
            
        finally:
            os.unlink(temp_path)
    
    @patch('pdf_processing.pipeline.PDFProcessor')
    def test_extraction_failure(self, mock_processor):
        """Test handling of PDF extraction failure"""
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"fake pdf content")
            temp_path = temp_file.name
        
        try:
            # Mock extraction failure
            mock_processor.return_value.extract_text.side_effect = RuntimeError("Extraction failed")
            
            result = self.pipeline.process_pdf(temp_path)
            
            assert result.status == ProcessingStatus.FAILED
            assert "Pipeline failed" in result.errors[0]
            assert result.final_text == ""
            
        finally:
            os.unlink(temp_path)
    
    @patch('pdf_processing.pipeline.PDFProcessor')
    def test_empty_text_extraction(self, mock_processor):
        """Test handling when no text is extracted"""
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"fake pdf content")
            temp_path = temp_file.name
        
        try:
            # Mock empty extraction
            mock_extraction = ExtractionResult(
                text="",
                page_count=1,
                method_used=ExtractionMethod.FITZ,
                confidence_score=0.1,
                metadata={}
            )
            mock_processor.return_value.extract_text.return_value = mock_extraction
            
            result = self.pipeline.process_pdf(temp_path)
            
            assert result.status == ProcessingStatus.FAILED
            assert "No text could be extracted" in result.errors[0]
            
        finally:
            os.unlink(temp_path)
    
    def test_quality_metrics_calculation(self):
        """Test quality metrics calculation"""
        # Mock results for quality calculation
        extraction_result = Mock(confidence_score=0.9, text="original text")
        cleaning_result = Mock(quality_score=0.8, warnings=[])
        detection_result = Mock(
            hierarchy=Mock(
                quality_score=0.7,
                total_chapters=4,
                total_sections=8,
                max_depth=2,
                numbering_consistency=0.85,
                overall_confidence=0.75,
                elements=[]
            )
        )
        filtering_result = Mock(
            quality_score=0.75,
            filtered_text="filtered text",
            stats=Mock(retention_ratio=0.8)
        )
        
        quality_metrics = self.pipeline._calculate_quality_metrics(
            extraction_result,
            cleaning_result,
            detection_result,
            filtering_result
        )
        
        # Check individual scores
        assert quality_metrics.extraction_confidence == 0.9
        assert quality_metrics.text_cleaning_score == 0.8
        assert quality_metrics.structure_detection_score == 0.7
        assert quality_metrics.content_filtering_score == 0.75
        
        # Check overall score is weighted average
        expected_overall = (0.9 * 0.25 + 0.8 * 0.20 + 0.7 * 0.30 + 0.75 * 0.25)
        assert abs(quality_metrics.overall_quality_score - expected_overall) < 0.01
        
        # Check validation flags
        assert quality_metrics.meets_minimum_chapters == True  # 4 >= 3
        assert quality_metrics.meets_retention_threshold == True  # 0.8 >= 0.5
    
    def test_textbook_validity_calculation(self):
        """Test textbook validity scoring"""
        # High validity case
        good_detection = Mock(
            hierarchy=Mock(
                total_chapters=5,
                total_sections=15,
                max_depth=2,
                numbering_consistency=0.9
            )
        )
        
        high_validity = self.pipeline._calculate_textbook_validity(good_detection)
        assert high_validity > 0.8
        
        # Low validity case
        poor_detection = Mock(
            hierarchy=Mock(
                total_chapters=1,
                total_sections=0,
                max_depth=0,
                numbering_consistency=0.3
            )
        )
        
        low_validity = self.pipeline._calculate_textbook_validity(poor_detection)
        assert low_validity < 0.7
    
    def test_processing_status_determination(self):
        """Test processing status determination logic"""
        
        # Success case
        good_metrics = Mock(
            passes_quality_gate=True,
            meets_minimum_chapters=True
        )
        success_status = self.pipeline._determine_processing_status(good_metrics, [], [])
        assert success_status == ProcessingStatus.SUCCESS
        
        # Partial success case (warnings)
        partial_metrics = Mock(
            passes_quality_gate=True,
            meets_minimum_chapters=False
        )
        partial_status = self.pipeline._determine_processing_status(partial_metrics, ["warning"], [])
        assert partial_status == ProcessingStatus.PARTIAL_SUCCESS
        
        # Validation failed case
        failed_metrics = Mock(
            passes_quality_gate=False,
            meets_minimum_chapters=True
        )
        validation_failed_status = self.pipeline._determine_processing_status(failed_metrics, [], [])
        assert validation_failed_status == ProcessingStatus.VALIDATION_FAILED
        
        # Error case
        error_status = self.pipeline._determine_processing_status(good_metrics, [], ["error"])
        assert error_status == ProcessingStatus.FAILED
    
    def test_recommendations_generation(self):
        """Test recommendation generation"""
        # Low quality metrics to trigger recommendations
        low_quality_metrics = Mock(
            extraction_confidence=0.5,
            structure_detection_score=0.3,
            character_retention_ratio=0.4,
            meets_minimum_chapters=False,
            overall_quality_score=0.5
        )
        
        detection_result = Mock(
            hierarchy=Mock(numbering_consistency=0.4)
        )
        
        filtering_result = Mock()
        
        recommendations = self.pipeline._generate_recommendations(
            low_quality_metrics,
            detection_result,
            filtering_result
        )
        
        # Should generate multiple recommendations
        assert len(recommendations) > 3
        assert any("extraction method" in rec.lower() for rec in recommendations)
        assert any("structure" in rec.lower() for rec in recommendations)
        assert any("chapters" in rec.lower() for rec in recommendations)
    
    def test_processing_summary_generation(self):
        """Test processing summary generation"""
        status = ProcessingStatus.SUCCESS
        
        quality_metrics = Mock(
            overall_quality_score=0.85,
            extraction_confidence=0.9,
            text_cleaning_score=0.8,
            structure_detection_score=0.85,
            content_filtering_score=0.8,
            textbook_validity_score=0.9,
            character_retention_ratio=0.75
        )
        
        metadata = Mock(
            original_text_length=10000,
            filtered_text_length=7500,
            chapters_detected=5,
            sections_detected=15,
            total_processing_time=12.5
        )
        
        warnings = ["Minor formatting issue"]
        recommendations = ["Consider manual review"]
        
        summary = self.pipeline._generate_processing_summary(
            status,
            quality_metrics,
            metadata,
            warnings,
            recommendations
        )
        
        # Check summary contains key information
        assert "Success" in summary
        assert "0.85" in summary  # Quality score
        assert "10,000" in summary  # Original length
        assert "7,500" in summary  # Final length
        assert "75.0%" in summary  # Retention ratio
        assert "5" in summary  # Chapters
        assert "15" in summary  # Sections
        assert "12.5" in summary  # Processing time
        assert "Minor formatting issue" in summary
        assert "Consider manual review" in summary
    
    def test_error_result_creation(self):
        """Test creation of error results"""
        start_time = 1000.0
        error_result = self.pipeline._create_error_result(
            "/test/file.pdf",
            "Test error message",
            start_time
        )
        
        assert error_result.status == ProcessingStatus.FAILED
        assert error_result.final_text == ""
        assert error_result.errors == ["Test error message"]
        assert error_result.quality_metrics.overall_quality_score == 0.0
        assert error_result.metadata.file_path == "/test/file.pdf"
        assert "Test error message" in error_result.processing_summary
    
    def test_component_integration(self):
        """Test that all components are properly initialized"""
        pipeline = PDFProcessingPipeline()
        
        # Verify all components exist
        assert hasattr(pipeline, 'pdf_processor')
        assert hasattr(pipeline, 'text_cleaner')
        assert hasattr(pipeline, 'structure_detector')
        assert hasattr(pipeline, 'content_filter')
        
        # Verify they have expected methods
        assert hasattr(pipeline.pdf_processor, 'extract_text')
        assert hasattr(pipeline.text_cleaner, 'clean_text')
        assert hasattr(pipeline.structure_detector, 'detect_structure')
        assert hasattr(pipeline.content_filter, 'filter_content')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])