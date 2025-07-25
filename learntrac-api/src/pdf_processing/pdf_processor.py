"""
PDFProcessor Class with Multi-Library Support

Implements the core PDF processing functionality with PyMuPDF (fitz) as primary library
and pdfplumber and pypdf as fallback options for robust text extraction.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Primary PDF library
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

# Fallback PDF libraries
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class ExtractionMethod(Enum):
    """PDF text extraction methods in order of preference"""
    FITZ = "PyMuPDF (fitz)"
    PDFPLUMBER = "pdfplumber"
    PYPDF = "pypdf"


@dataclass
class ExtractionResult:
    """Results from PDF text extraction"""
    text: str
    page_count: int
    method_used: ExtractionMethod
    confidence_score: float
    metadata: Dict[str, Any]
    error_message: Optional[str] = None


@dataclass
class PageMetadata:
    """Metadata for individual PDF pages"""
    page_number: int
    text_length: int
    extraction_confidence: float
    has_images: bool
    has_tables: bool


class PDFProcessor:
    """
    Core PDF processor with multi-library support and fallback mechanisms.
    
    Features:
    - Primary extraction using PyMuPDF (fitz) for high quality
    - Automatic fallback to pdfplumber for complex layouts
    - Final fallback to pypdf for simple extraction
    - Comprehensive error handling and logging
    - Page-level metadata extraction
    - Confidence scoring for extraction quality
    """
    
    def __init__(self, max_file_size_mb: int = 100):
        """
        Initialize PDFProcessor with configuration options.
        
        Args:
            max_file_size_mb: Maximum allowed PDF file size in megabytes
        """
        self.max_file_size_mb = max_file_size_mb
        self.logger = logging.getLogger(__name__)
        
        # Log available libraries
        self._log_available_libraries()
    
    def _log_available_libraries(self) -> None:
        """Log which PDF processing libraries are available"""
        available = []
        if HAS_FITZ:
            available.append("PyMuPDF (fitz)")
        if HAS_PDFPLUMBER:
            available.append("pdfplumber")
        if HAS_PYPDF:
            available.append("pypdf")
        
        if not available:
            self.logger.error("No PDF processing libraries available!")
            raise ImportError("No PDF processing libraries installed. Please install PyMuPDF, pdfplumber, or pypdf.")
        
        self.logger.info(f"Available PDF libraries: {', '.join(available)}")
    
    def extract_text(self, pdf_path: str) -> ExtractionResult:
        """
        Extract text from PDF using multi-library approach with fallbacks.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            ExtractionResult containing extracted text and metadata
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If file is too large or invalid format
            RuntimeError: If all extraction methods fail
        """
        pdf_file = Path(pdf_path)
        
        # Validate file
        self._validate_pdf_file(pdf_file)
        
        # Try extraction methods in order of preference
        extraction_methods = [
            (ExtractionMethod.FITZ, self._extract_with_fitz),
            (ExtractionMethod.PDFPLUMBER, self._extract_with_pdfplumber),
            (ExtractionMethod.PYPDF, self._extract_with_pypdf)
        ]
        
        last_error = None
        for method, extractor in extraction_methods:
            try:
                self.logger.info(f"Attempting extraction with {method.value}")
                result = extractor(pdf_file)
                
                if result.text.strip():  # Ensure we got meaningful text
                    self.logger.info(f"Successfully extracted {len(result.text)} characters using {method.value}")
                    return result
                else:
                    self.logger.warning(f"{method.value} returned empty text")
                    
            except Exception as e:
                last_error = e
                self.logger.warning(f"{method.value} failed: {str(e)}")
                continue
        
        # All methods failed
        error_msg = f"All extraction methods failed. Last error: {str(last_error)}"
        self.logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def _validate_pdf_file(self, pdf_file: Path) -> None:
        """Validate PDF file existence, size, and format"""
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_file}")
        
        # Check file size
        file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise ValueError(f"PDF file too large: {file_size_mb:.1f}MB > {self.max_file_size_mb}MB")
        
        # Basic format validation
        if not pdf_file.suffix.lower() == '.pdf':
            raise ValueError(f"File is not a PDF: {pdf_file}")
    
    def _extract_with_fitz(self, pdf_file: Path) -> ExtractionResult:
        """Extract text using PyMuPDF (fitz) - primary method"""
        if not HAS_FITZ:
            raise ImportError("PyMuPDF (fitz) not available")
        
        doc = fitz.open(str(pdf_file))
        
        try:
            text_parts = []
            page_metadata = []
            total_confidence = 0.0
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_text = page.get_text()
                
                # Calculate confidence based on text quality indicators
                confidence = self._calculate_fitz_confidence(page, page_text)
                total_confidence += confidence
                
                # Collect page metadata
                page_meta = PageMetadata(
                    page_number=page_num + 1,
                    text_length=len(page_text),
                    extraction_confidence=confidence,
                    has_images=len(page.get_images()) > 0,
                    has_tables=len(page.find_tables()) > 0
                )
                page_metadata.append(page_meta)
                
                text_parts.append(page_text)
            
            # Extract document metadata
            doc_metadata = self._extract_fitz_metadata(doc)
            doc_metadata['pages'] = page_metadata
            
            avg_confidence = total_confidence / doc.page_count if doc.page_count > 0 else 0.0
            
            return ExtractionResult(
                text='\n'.join(text_parts),
                page_count=doc.page_count,
                method_used=ExtractionMethod.FITZ,
                confidence_score=avg_confidence,
                metadata=doc_metadata
            )
            
        finally:
            doc.close()
    
    def _extract_with_pdfplumber(self, pdf_file: Path) -> ExtractionResult:
        """Extract text using pdfplumber - good for complex layouts"""
        if not HAS_PDFPLUMBER:
            raise ImportError("pdfplumber not available")
        
        with pdfplumber.open(str(pdf_file)) as pdf:
            text_parts = []
            page_metadata = []
            total_confidence = 0.0
            
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                
                # Calculate confidence based on extraction quality
                confidence = self._calculate_pdfplumber_confidence(page, page_text)
                total_confidence += confidence
                
                # Collect page metadata
                page_meta = PageMetadata(
                    page_number=page_num + 1,
                    text_length=len(page_text),
                    extraction_confidence=confidence,
                    has_images=len(page.images) > 0,
                    has_tables=len(page.extract_tables()) > 0
                )
                page_metadata.append(page_meta)
                
                text_parts.append(page_text)
            
            # Extract document metadata
            doc_metadata = self._extract_pdfplumber_metadata(pdf)
            doc_metadata['pages'] = page_metadata
            
            avg_confidence = total_confidence / len(pdf.pages) if pdf.pages else 0.0
            
            return ExtractionResult(
                text='\n'.join(text_parts),
                page_count=len(pdf.pages),
                method_used=ExtractionMethod.PDFPLUMBER,
                confidence_score=avg_confidence,
                metadata=doc_metadata
            )
    
    def _extract_with_pypdf(self, pdf_file: Path) -> ExtractionResult:
        """Extract text using pypdf - final fallback method"""
        if not HAS_PYPDF:
            raise ImportError("pypdf not available")
        
        with open(pdf_file, 'rb') as file:
            reader = pypdf.PdfReader(file)
            
            text_parts = []
            page_metadata = []
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                
                # pypdf has limited confidence calculation options
                confidence = 0.7 if page_text.strip() else 0.1
                
                page_meta = PageMetadata(
                    page_number=page_num + 1,
                    text_length=len(page_text),
                    extraction_confidence=confidence,
                    has_images=False,  # pypdf doesn't easily provide image info
                    has_tables=False   # pypdf doesn't easily provide table info
                )
                page_metadata.append(page_meta)
                
                text_parts.append(page_text)
            
            # Extract basic metadata
            doc_metadata = self._extract_pypdf_metadata(reader)
            doc_metadata['pages'] = page_metadata
            
            avg_confidence = sum(p.extraction_confidence for p in page_metadata) / len(page_metadata) if page_metadata else 0.0
            
            return ExtractionResult(
                text='\n'.join(text_parts),
                page_count=len(reader.pages),
                method_used=ExtractionMethod.PYPDF,
                confidence_score=avg_confidence,
                metadata=doc_metadata
            )
    
    def _calculate_fitz_confidence(self, page, text: str) -> float:
        """Calculate extraction confidence for PyMuPDF results"""
        if not text.strip():
            return 0.0
        
        confidence = 0.8  # Base confidence for fitz
        
        # Adjust based on text characteristics
        if len(text) < 50:
            confidence -= 0.2
        
        # Check for garbled text (many consecutive non-printable chars)
        garbled_ratio = sum(1 for c in text if not c.isprintable() and c not in '\n\t') / len(text)
        confidence -= garbled_ratio * 0.3
        
        # Bonus for having proper sentence structure
        if '. ' in text and text.count('.') > 1:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_pdfplumber_confidence(self, page, text: str) -> float:
        """Calculate extraction confidence for pdfplumber results"""
        if not text.strip():
            return 0.0
        
        confidence = 0.7  # Base confidence for pdfplumber
        
        # pdfplumber is good with tables and structured content
        if page.extract_tables():
            confidence += 0.1
        
        # Adjust based on text quality
        if len(text) > 100 and '. ' in text:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _extract_fitz_metadata(self, doc) -> Dict[str, Any]:
        """Extract metadata using PyMuPDF"""
        metadata = doc.metadata or {}
        return {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', ''),
            'file_size': doc.page_count * 1000  # Rough estimate
        }
    
    def _extract_pdfplumber_metadata(self, pdf) -> Dict[str, Any]:
        """Extract metadata using pdfplumber"""
        metadata = pdf.metadata or {}
        return {
            'title': metadata.get('/Title', ''),
            'author': metadata.get('/Author', ''),
            'subject': metadata.get('/Subject', ''),
            'creator': metadata.get('/Creator', ''),
            'producer': metadata.get('/Producer', ''),
            'creation_date': metadata.get('/CreationDate', ''),
            'modification_date': metadata.get('/ModDate', ''),
            'file_size': 0  # pdfplumber doesn't provide file size easily
        }
    
    def _extract_pypdf_metadata(self, reader) -> Dict[str, Any]:
        """Extract metadata using pypdf"""
        metadata = reader.metadata or {}
        return {
            'title': metadata.get('/Title', ''),
            'author': metadata.get('/Author', ''),
            'subject': metadata.get('/Subject', ''),
            'creator': metadata.get('/Creator', ''),
            'producer': metadata.get('/Producer', ''),
            'creation_date': metadata.get('/CreationDate', ''),
            'modification_date': metadata.get('/ModDate', ''),
            'file_size': 0  # pypdf doesn't provide file size easily
        }