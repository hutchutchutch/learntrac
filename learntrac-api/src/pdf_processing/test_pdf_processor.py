"""
Unit tests for PDFProcessor class

Tests the multi-library PDF processing functionality with various scenarios.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from .pdf_processor import PDFProcessor, ExtractionMethod, ExtractionResult


class TestPDFProcessor:
    """Test suite for PDFProcessor class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = PDFProcessor(max_file_size_mb=10)
    
    def test_init_logging(self):
        """Test PDFProcessor initialization and library logging"""
        # Should initialize without errors
        processor = PDFProcessor()
        assert processor.max_file_size_mb == 100
    
    def test_validate_pdf_file_not_found(self):
        """Test validation with non-existent file"""
        with pytest.raises(FileNotFoundError):
            self.processor._validate_pdf_file(Path("/nonexistent/file.pdf"))
    
    def test_validate_pdf_file_wrong_extension(self):
        """Test validation with non-PDF file"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            
        try:
            with pytest.raises(ValueError, match="File is not a PDF"):
                self.processor._validate_pdf_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_validate_pdf_file_too_large(self):
        """Test validation with oversized file"""
        # Create a temporary large file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            # Write enough data to exceed size limit (10MB + some extra)
            temp_file.write(b"x" * (11 * 1024 * 1024))
            temp_path = Path(temp_file.name)
        
        try:
            with pytest.raises(ValueError, match="PDF file too large"):
                self.processor._validate_pdf_file(temp_path)
        finally:
            temp_path.unlink()
    
    @patch('pdf_processing.pdf_processor.HAS_FITZ', True)
    @patch('pdf_processing.pdf_processor.fitz')
    def test_extract_with_fitz_success(self, mock_fitz):
        """Test successful extraction with PyMuPDF"""
        # Setup mock
        mock_doc = Mock()
        mock_doc.page_count = 2
        mock_doc.metadata = {'title': 'Test PDF', 'author': 'Test Author'}
        
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "Page 1 content with proper sentences."
        mock_page1.get_images.return_value = []
        mock_page1.find_tables.return_value = []
        
        mock_page2 = Mock()
        mock_page2.get_text.return_value = "Page 2 content continues here."
        mock_page2.get_images.return_value = []
        mock_page2.find_tables.return_value = []
        
        mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]
        mock_fitz.open.return_value = mock_doc
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            result = self.processor._extract_with_fitz(temp_path)
            
            assert result.method_used == ExtractionMethod.FITZ
            assert result.page_count == 2
            assert "Page 1 content" in result.text
            assert "Page 2 content" in result.text
            assert result.confidence_score > 0
            assert result.metadata['title'] == 'Test PDF'
            
            mock_doc.close.assert_called_once()
            
        finally:
            temp_path.unlink()
    
    @patch('pdf_processing.pdf_processor.HAS_FITZ', False)
    def test_extract_with_fitz_not_available(self):
        """Test fitz extraction when library not available"""
        with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_file:
            temp_path = Path(temp_file.name)
            
            with pytest.raises(ImportError, match="PyMuPDF.*not available"):
                self.processor._extract_with_fitz(temp_path)
    
    def test_calculate_fitz_confidence_empty_text(self):
        """Test confidence calculation with empty text"""
        confidence = self.processor._calculate_fitz_confidence(Mock(), "")
        assert confidence == 0.0
    
    def test_calculate_fitz_confidence_good_text(self):
        """Test confidence calculation with quality text"""
        text = "This is a proper sentence. It has multiple sentences with periods."
        confidence = self.processor._calculate_fitz_confidence(Mock(), text)
        assert confidence > 0.8  # Should be high confidence
    
    def test_calculate_fitz_confidence_short_text(self):
        """Test confidence calculation with short text"""
        text = "Short"
        confidence = self.processor._calculate_fitz_confidence(Mock(), text)
        assert confidence < 0.8  # Should be lower confidence
    
    @patch('pdf_processing.pdf_processor.HAS_FITZ', False)
    @patch('pdf_processing.pdf_processor.HAS_PDFPLUMBER', False)
    @patch('pdf_processing.pdf_processor.HAS_PYPDF', False)
    def test_no_libraries_available(self):
        """Test initialization when no PDF libraries are available"""
        with pytest.raises(ImportError, match="No PDF processing libraries"):
            PDFProcessor()
    
    @patch('pdf_processing.pdf_processor.HAS_FITZ', True)
    @patch('pdf_processing.pdf_processor.fitz')
    def test_extract_text_success(self, mock_fitz):
        """Test full extract_text method with successful extraction"""
        # Setup mock for successful fitz extraction
        mock_doc = Mock()
        mock_doc.page_count = 1
        mock_doc.metadata = {}
        
        mock_page = Mock()
        mock_page.get_text.return_value = "Test content from PDF."
        mock_page.get_images.return_value = []
        mock_page.find_tables.return_value = []
        
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_doc
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"fake pdf content")
            temp_path = temp_file.name
        
        try:
            result = self.processor.extract_text(temp_path)
            
            assert isinstance(result, ExtractionResult)
            assert result.method_used == ExtractionMethod.FITZ
            assert "Test content" in result.text
            assert result.page_count == 1
            
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])