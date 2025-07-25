"""
PDF Processing Module for LearnTrac

This module provides comprehensive PDF processing capabilities including:
- Multi-library text extraction (PyMuPDF, pdfplumber, pypdf)
- Text cleaning and normalization
- Document structure detection
- Content filtering and quality scoring
- Complete processing pipeline with quality metrics
"""

from .pdf_processor import PDFProcessor, ExtractionResult, ExtractionMethod
from .text_cleaner import TextCleaner, CleaningResult, TextIssueType
from .structure_detector import StructureDetector, DetectionResult, StructureType, StructureElement
from .content_filter import ContentFilter, FilteringResult, ContentType
from .pipeline import PDFProcessingPipeline, ProcessingResult, ProcessingStatus, QualityMetrics

__all__ = [
    # Core components
    'PDFProcessor',
    'TextCleaner', 
    'StructureDetector',
    'ContentFilter',
    
    # Main pipeline
    'PDFProcessingPipeline',
    
    # Result classes
    'ExtractionResult',
    'CleaningResult', 
    'DetectionResult',
    'FilteringResult',
    'ProcessingResult',
    
    # Data classes and enums
    'ExtractionMethod',
    'TextIssueType',
    'StructureType',
    'StructureElement',
    'ContentType',
    'ProcessingStatus',
    'QualityMetrics'
]