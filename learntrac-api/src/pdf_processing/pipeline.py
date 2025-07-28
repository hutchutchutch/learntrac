"""
PDF Processing Pipeline - Main Integration Component

Orchestrates the complete PDF processing pipeline combining extraction, cleaning,
structure detection, and content filtering with comprehensive quality scoring.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .pdf_processor import PDFProcessor, ExtractionResult
from .text_cleaner import TextCleaner, CleaningResult
from .structure_detector import StructureDetector, DetectionResult, StructureElement
from .content_filter import ContentFilter, FilteringResult


class ProcessingStage(Enum):
    """Processing pipeline stages"""
    INITIALIZATION = "initialization"
    PDF_EXTRACTION = "pdf_extraction"
    TEXT_CLEANING = "text_cleaning"
    STRUCTURE_DETECTION = "structure_detection"
    CONTENT_FILTERING = "content_filtering"
    QUALITY_ASSESSMENT = "quality_assessment"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStatus(Enum):
    """Overall processing status"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class QualityMetrics:
    """Comprehensive quality metrics for processed content"""
    extraction_confidence: float
    text_cleaning_score: float
    structure_detection_score: float
    content_filtering_score: float
    overall_quality_score: float
    textbook_validity_score: float
    
    # Detailed metrics
    character_retention_ratio: float
    structure_completeness: float
    content_coherence: float
    educational_value_score: float
    
    # Validation flags
    meets_minimum_chapters: bool
    meets_retention_threshold: bool
    has_coherent_structure: bool
    passes_quality_gate: bool


@dataclass
class ProcessingMetadata:
    """Metadata about the processing operation"""
    file_path: str
    file_size_bytes: int
    processing_start_time: float
    processing_end_time: Optional[float]
    total_processing_time: Optional[float]
    
    # Stage timings
    stage_timings: Dict[ProcessingStage, float]
    
    # Component versions/settings
    pdf_processor_method: str
    text_cleaner_settings: Dict[str, Any]
    structure_detector_settings: Dict[str, Any]
    content_filter_settings: Dict[str, Any]
    
    # Processing statistics
    original_text_length: int
    cleaned_text_length: int
    filtered_text_length: int
    chapters_detected: int
    sections_detected: int


@dataclass
class ProcessingResult:
    """Complete result from PDF processing pipeline"""
    status: ProcessingStatus
    final_text: str
    structure_elements: List[StructureElement]
    quality_metrics: QualityMetrics
    metadata: ProcessingMetadata
    
    # Intermediate results (for debugging/analysis)
    extraction_result: Optional[ExtractionResult]
    cleaning_result: Optional[CleaningResult]
    detection_result: Optional[DetectionResult]
    filtering_result: Optional[FilteringResult]
    
    # Issues and recommendations
    warnings: List[str]
    errors: List[str]
    recommendations: List[str]
    
    # Summary for users
    processing_summary: str


class PDFProcessingPipeline:
    """
    Complete PDF processing pipeline orchestrator.
    
    Integrates all components:
    - PDFProcessor for text extraction
    - TextCleaner for normalization
    - StructureDetector for hierarchy detection
    - ContentFilter for content curation
    
    Features:
    - Comprehensive quality scoring
    - Validation and error handling
    - Performance monitoring
    - Detailed reporting and recommendations
    """
    
    def __init__(self,
                 min_chapters: int = 3,
                 min_retention_ratio: float = 0.5,
                 quality_threshold: float = 0.7,
                 preserve_mathematical: bool = True,
                 aggressive_filtering: bool = False):
        """
        Initialize PDF processing pipeline.
        
        Args:
            min_chapters: Minimum chapters required for textbook validation
            min_retention_ratio: Minimum content retention ratio
            quality_threshold: Minimum quality score for acceptance
            preserve_mathematical: Preserve mathematical expressions
            aggressive_filtering: Use aggressive content filtering
        """
        self.min_chapters = min_chapters
        self.min_retention_ratio = min_retention_ratio
        self.quality_threshold = quality_threshold
        self.preserve_mathematical = preserve_mathematical
        self.aggressive_filtering = aggressive_filtering
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize all processing components"""
        self.pdf_processor = PDFProcessor()
        self.text_cleaner = TextCleaner(preserve_mathematical=self.preserve_mathematical)
        self.structure_detector = StructureDetector(
            min_chapters=self.min_chapters,
            confidence_threshold=0.3
        )
        self.content_filter = ContentFilter(
            min_retention_ratio=self.min_retention_ratio,
            aggressive_filtering=self.aggressive_filtering
        )
    
    def process_pdf(self, pdf_path: str) -> ProcessingResult:
        """
        Process a PDF file through the complete pipeline.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            ProcessingResult with processed content and quality metrics
        """
        start_time = time.time()
        file_path = Path(pdf_path)
        
        if not file_path.exists():
            return self._create_error_result(
                pdf_path, 
                f"File not found: {pdf_path}",
                start_time
            )
        
        self.logger.info(f"Starting PDF processing pipeline for: {pdf_path}")
        
        # Initialize metadata
        metadata = ProcessingMetadata(
            file_path=str(file_path),
            file_size_bytes=file_path.stat().st_size,
            processing_start_time=start_time,
            processing_end_time=None,
            total_processing_time=None,
            stage_timings={},
            pdf_processor_method="",
            text_cleaner_settings={},
            structure_detector_settings={},
            content_filter_settings={},
            original_text_length=0,
            cleaned_text_length=0,
            filtered_text_length=0,
            chapters_detected=0,
            sections_detected=0
        )
        
        warnings = []
        errors = []
        recommendations = []
        
        try:
            # Stage 1: PDF Text Extraction
            stage_start = time.time()
            self.logger.info("Stage 1: PDF text extraction")
            
            extraction_result = self.pdf_processor.extract_text(pdf_path)
            metadata.stage_timings[ProcessingStage.PDF_EXTRACTION] = time.time() - stage_start
            metadata.pdf_processor_method = extraction_result.method_used.value
            metadata.original_text_length = len(extraction_result.text)
            
            if not extraction_result.text.strip():
                return self._create_error_result(
                    pdf_path,
                    "No text could be extracted from PDF",
                    start_time,
                    metadata
                )
            
            # Stage 2: Text Cleaning
            stage_start = time.time()
            self.logger.info("Stage 2: Text cleaning and normalization")
            
            cleaning_result = self.text_cleaner.clean_text(extraction_result.text)
            metadata.stage_timings[ProcessingStage.TEXT_CLEANING] = time.time() - stage_start
            metadata.cleaned_text_length = len(cleaning_result.cleaned_text)
            
            warnings.extend(cleaning_result.warnings)
            
            # Stage 3: Structure Detection
            stage_start = time.time()
            self.logger.info("Stage 3: Document structure detection")
            
            detection_result = self.structure_detector.detect_structure(cleaning_result.cleaned_text)
            metadata.stage_timings[ProcessingStage.STRUCTURE_DETECTION] = time.time() - stage_start
            metadata.chapters_detected = detection_result.hierarchy.total_chapters
            metadata.sections_detected = detection_result.hierarchy.total_sections
            
            warnings.extend(detection_result.warnings)
            
            # Stage 4: Content Filtering
            stage_start = time.time()
            self.logger.info("Stage 4: Content filtering")
            
            filtering_result = self.content_filter.filter_content(
                cleaning_result.cleaned_text,
                detection_result.hierarchy.elements
            )
            metadata.stage_timings[ProcessingStage.CONTENT_FILTERING] = time.time() - stage_start
            metadata.filtered_text_length = len(filtering_result.filtered_text)
            
            warnings.extend(filtering_result.warnings)
            
            # Stage 5: Quality Assessment
            stage_start = time.time()
            self.logger.info("Stage 5: Quality assessment")
            
            quality_metrics = self._calculate_quality_metrics(
                extraction_result,
                cleaning_result,
                detection_result,
                filtering_result
            )
            metadata.stage_timings[ProcessingStage.QUALITY_ASSESSMENT] = time.time() - stage_start
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                quality_metrics,
                detection_result,
                filtering_result
            )
            
            # Determine final status
            status = self._determine_processing_status(quality_metrics, warnings, errors)
            
            # Finalize metadata
            end_time = time.time()
            metadata.processing_end_time = end_time
            metadata.total_processing_time = end_time - start_time
            
            # Generate processing summary
            summary = self._generate_processing_summary(
                status,
                quality_metrics,
                metadata,
                warnings,
                recommendations
            )
            
            self.logger.info(f"PDF processing completed in {metadata.total_processing_time:.2f}s with status: {status.value}")
            
            return ProcessingResult(
                status=status,
                final_text=filtering_result.filtered_text,
                structure_elements=detection_result.hierarchy.elements,
                quality_metrics=quality_metrics,
                metadata=metadata,
                extraction_result=extraction_result,
                cleaning_result=cleaning_result,
                detection_result=detection_result,
                filtering_result=filtering_result,
                warnings=warnings,
                errors=errors,
                recommendations=recommendations,
                processing_summary=summary
            )
            
        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return self._create_error_result(pdf_path, error_msg, start_time, metadata)
    
    def _calculate_quality_metrics(self,
                                 extraction_result: ExtractionResult,
                                 cleaning_result: CleaningResult,
                                 detection_result: DetectionResult,
                                 filtering_result: FilteringResult) -> QualityMetrics:
        """Calculate comprehensive quality metrics"""
        
        # Individual component scores
        extraction_confidence = extraction_result.confidence_score
        text_cleaning_score = cleaning_result.quality_score
        structure_detection_score = detection_result.hierarchy.quality_score
        content_filtering_score = filtering_result.quality_score
        
        # Overall quality score (weighted average)
        overall_quality_score = (
            extraction_confidence * 0.25 +
            text_cleaning_score * 0.20 +
            structure_detection_score * 0.30 +
            content_filtering_score * 0.25
        )
        
        # Textbook validity score
        textbook_validity_score = self._calculate_textbook_validity(detection_result)
        
        # Detailed metrics
        original_length = len(extraction_result.text)
        final_length = len(filtering_result.filtered_text)
        character_retention_ratio = final_length / original_length if original_length > 0 else 0.0
        
        structure_completeness = self._calculate_structure_completeness(detection_result)
        content_coherence = self._calculate_content_coherence(cleaning_result, detection_result)
        educational_value_score = self._calculate_educational_value(detection_result, filtering_result)
        
        # Validation flags
        meets_minimum_chapters = detection_result.hierarchy.total_chapters >= self.min_chapters
        meets_retention_threshold = character_retention_ratio >= self.min_retention_ratio
        has_coherent_structure = structure_detection_score >= 0.5
        passes_quality_gate = overall_quality_score >= self.quality_threshold
        
        return QualityMetrics(
            extraction_confidence=extraction_confidence,
            text_cleaning_score=text_cleaning_score,
            structure_detection_score=structure_detection_score,
            content_filtering_score=content_filtering_score,
            overall_quality_score=overall_quality_score,
            textbook_validity_score=textbook_validity_score,
            character_retention_ratio=character_retention_ratio,
            structure_completeness=structure_completeness,
            content_coherence=content_coherence,
            educational_value_score=educational_value_score,
            meets_minimum_chapters=meets_minimum_chapters,
            meets_retention_threshold=meets_retention_threshold,
            has_coherent_structure=has_coherent_structure,
            passes_quality_gate=passes_quality_gate
        )
    
    def _calculate_textbook_validity(self, detection_result: DetectionResult) -> float:
        """Calculate how likely this is a valid textbook"""
        base_score = 0.5
        
        # Chapter count
        chapter_count = detection_result.hierarchy.total_chapters
        if chapter_count >= self.min_chapters:
            base_score += 0.2
        elif chapter_count > 0:
            base_score += 0.1
        
        # Section structure
        if detection_result.hierarchy.total_sections > 0:
            base_score += 0.1
        
        # Hierarchical depth
        if detection_result.hierarchy.max_depth > 0:
            base_score += 0.1
        
        # Structure consistency
        base_score += detection_result.hierarchy.numbering_consistency * 0.1
        
        return min(1.0, base_score)
    
    def _calculate_structure_completeness(self, detection_result: DetectionResult) -> float:
        """Calculate how complete the detected structure is"""
        if not detection_result.hierarchy.elements:
            return 0.0
        
        # Base on ratio of structured vs unstructured content
        structured_elements = len(detection_result.hierarchy.elements)
        
        # Ideal ratio: 1 chapter per 10-20 pages, sections within chapters
        # This is a simplified heuristic
        completeness = min(1.0, structured_elements / 10)
        
        # Bonus for hierarchical structure
        if detection_result.hierarchy.max_depth > 1:
            completeness += 0.1
        
        return min(1.0, completeness)
    
    def _calculate_content_coherence(self, cleaning_result: CleaningResult, detection_result: DetectionResult) -> float:
        """Calculate how coherent the content is"""
        base_score = 0.5
        
        # Text cleaning quality contributes to coherence
        base_score += cleaning_result.quality_score * 0.3
        
        # Structure detection confidence contributes
        base_score += detection_result.hierarchy.overall_confidence * 0.2
        
        # Penalty for excessive warnings
        warning_penalty = min(0.2, len(cleaning_result.warnings) * 0.05)
        base_score -= warning_penalty
        
        return max(0.0, min(1.0, base_score))
    
    def _calculate_educational_value(self, detection_result: DetectionResult, filtering_result: FilteringResult) -> float:
        """Estimate educational value of the content"""
        base_score = 0.6
        
        # Bonus for good chapter structure
        if detection_result.hierarchy.total_chapters >= 3:
            base_score += 0.2
        
        # Bonus for sections within chapters
        if detection_result.hierarchy.total_sections > 0:
            avg_sections_per_chapter = detection_result.hierarchy.total_sections / max(1, detection_result.hierarchy.total_chapters)
            if 1 <= avg_sections_per_chapter <= 10:
                base_score += 0.1
        
        # Bonus for appropriate content filtering
        if filtering_result.stats.retention_ratio > 0.6:
            base_score += 0.1
        
        return min(1.0, base_score)
    
    def _determine_processing_status(self, quality_metrics: QualityMetrics, warnings: List[str], errors: List[str]) -> ProcessingStatus:
        """Determine the overall processing status"""
        if errors:
            return ProcessingStatus.FAILED
        
        if not quality_metrics.passes_quality_gate:
            return ProcessingStatus.VALIDATION_FAILED
        
        if warnings or not quality_metrics.meets_minimum_chapters:
            return ProcessingStatus.PARTIAL_SUCCESS
        
        return ProcessingStatus.SUCCESS
    
    def _generate_recommendations(self,
                                quality_metrics: QualityMetrics,
                                detection_result: DetectionResult,
                                filtering_result: FilteringResult) -> List[str]:
        """Generate recommendations for improving processing results"""
        recommendations = []
        
        if quality_metrics.extraction_confidence < 0.7:
            recommendations.append("Consider using a different PDF extraction method or checking PDF quality")
        
        if quality_metrics.structure_detection_score < 0.5:
            recommendations.append("Document structure may need manual review - consider custom chapter patterns")
        
        if quality_metrics.character_retention_ratio < 0.6:
            recommendations.append("High content removal detected - review filtering settings")
        
        if not quality_metrics.meets_minimum_chapters:
            recommendations.append(f"Document has fewer than {self.min_chapters} chapters - may not be suitable as textbook")
        
        if detection_result.hierarchy.numbering_consistency < 0.7:
            recommendations.append("Inconsistent numbering detected - manual structure review recommended")
        
        if quality_metrics.overall_quality_score < self.quality_threshold:
            recommendations.append("Overall quality below threshold - consider manual review or different processing settings")
        
        return recommendations
    
    def _generate_processing_summary(self,
                                   status: ProcessingStatus,
                                   quality_metrics: QualityMetrics,
                                   metadata: ProcessingMetadata,
                                   warnings: List[str],
                                   recommendations: List[str]) -> str:
        """Generate a human-readable processing summary"""
        
        summary_parts = [
            f"Processing Status: {status.value.replace('_', ' ').title()}",
            f"Overall Quality Score: {quality_metrics.overall_quality_score:.2f}/1.00",
            "",
            "Content Statistics:",
            f"  • Original text: {metadata.original_text_length:,} characters",
            f"  • Final text: {metadata.filtered_text_length:,} characters",
            f"  • Retention ratio: {quality_metrics.character_retention_ratio:.1%}",
            f"  • Chapters detected: {metadata.chapters_detected}",
            f"  • Sections detected: {metadata.sections_detected}",
            "",
            "Quality Metrics:",
            f"  • Text extraction: {quality_metrics.extraction_confidence:.2f}",
            f"  • Text cleaning: {quality_metrics.text_cleaning_score:.2f}",
            f"  • Structure detection: {quality_metrics.structure_detection_score:.2f}",
            f"  • Content filtering: {quality_metrics.content_filtering_score:.2f}",
            f"  • Textbook validity: {quality_metrics.textbook_validity_score:.2f}",
            "",
            f"Processing time: {metadata.total_processing_time:.2f} seconds"
        ]
        
        if warnings:
            summary_parts.extend([
                "",
                f"Warnings ({len(warnings)}):",
                *[f"  • {warning}" for warning in warnings[:3]],
                *["  • ..." if len(warnings) > 3 else []]
            ])
        
        if recommendations:
            summary_parts.extend([
                "",
                f"Recommendations ({len(recommendations)}):",
                *[f"  • {rec}" for rec in recommendations[:3]],
                *(["  • ..."] if len(recommendations) > 3 else [])
            ])
        
        return "\n".join(summary_parts)
    
    def _create_error_result(self,
                           pdf_path: str,
                           error_message: str,
                           start_time: float,
                           metadata: Optional[ProcessingMetadata] = None) -> ProcessingResult:
        """Create a ProcessingResult for error cases"""
        
        if metadata is None:
            metadata = ProcessingMetadata(
                file_path=pdf_path,
                file_size_bytes=0,
                processing_start_time=start_time,
                processing_end_time=time.time(),
                total_processing_time=time.time() - start_time,
                stage_timings={},
                pdf_processor_method="",
                text_cleaner_settings={},
                structure_detector_settings={},
                content_filter_settings={},
                original_text_length=0,
                cleaned_text_length=0,
                filtered_text_length=0,
                chapters_detected=0,
                sections_detected=0
            )
        
        quality_metrics = QualityMetrics(
            extraction_confidence=0.0,
            text_cleaning_score=0.0,
            structure_detection_score=0.0,
            content_filtering_score=0.0,
            overall_quality_score=0.0,
            textbook_validity_score=0.0,
            character_retention_ratio=0.0,
            structure_completeness=0.0,
            content_coherence=0.0,
            educational_value_score=0.0,
            meets_minimum_chapters=False,
            meets_retention_threshold=False,
            has_coherent_structure=False,
            passes_quality_gate=False
        )
        
        return ProcessingResult(
            status=ProcessingStatus.FAILED,
            final_text="",
            structure_elements=[],
            quality_metrics=quality_metrics,
            metadata=metadata,
            extraction_result=None,
            cleaning_result=None,
            detection_result=None,
            filtering_result=None,
            warnings=[],
            errors=[error_message],
            recommendations=["Fix the error and retry processing"],
            processing_summary=f"Processing failed: {error_message}"
        )