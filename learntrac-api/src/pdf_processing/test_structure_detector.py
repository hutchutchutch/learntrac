"""
Unit tests for StructureDetector class

Tests comprehensive document structure detection including chapter/section recognition,
confidence scoring, and hierarchy building.
"""

import pytest
from .structure_detector import (
    StructureDetector, 
    StructureType, 
    NumberingStyle,
    StructureElement,
    DetectionResult
)


class TestStructureDetector:
    """Test suite for StructureDetector class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.detector = StructureDetector(min_chapters=3, confidence_threshold=0.3)
    
    def test_init_default(self):
        """Test StructureDetector initialization with defaults"""
        detector = StructureDetector()
        assert detector.min_chapters == 3
        assert detector.confidence_threshold == 0.3
    
    def test_init_custom(self):
        """Test StructureDetector initialization with custom settings"""
        detector = StructureDetector(min_chapters=5, confidence_threshold=0.5)
        assert detector.min_chapters == 5
        assert detector.confidence_threshold == 0.5
    
    def test_detect_empty_text(self):
        """Test structure detection with empty text"""
        result = self.detector.detect_structure("")
        assert not result.is_valid_textbook
        assert result.hierarchy.total_chapters == 0
        assert "Empty text" in result.warnings[0]
    
    def test_detect_basic_chapters(self):
        """Test detection of basic chapter patterns"""
        text = """
        Chapter 1: Introduction to Programming
        
        This chapter covers the basics.
        
        Chapter 2: Variables and Data Types
        
        Learn about different data types.
        
        Chapter 3: Control Structures
        
        Conditional statements and loops.
        """
        
        result = self.detector.detect_structure(text)
        
        assert result.hierarchy.total_chapters == 3
        assert result.is_valid_textbook  # Meets minimum chapter requirement
        
        chapters = [e for e in result.hierarchy.elements if e.type == StructureType.CHAPTER]
        assert len(chapters) == 3
        assert chapters[0].title == "Introduction to Programming"
        assert chapters[0].number == "1"
        assert chapters[0].numbering_style == NumberingStyle.ARABIC
    
    def test_detect_various_chapter_formats(self):
        """Test detection of different chapter formats"""
        text = """
        CHAPTER 1 - Getting Started
        
        Chapter 2: Basic Concepts
        
        Ch. 3 Advanced Topics
        
        Unit 4: Applications
        
        Module 5 - Final Project
        """
        
        result = self.detector.detect_structure(text)
        
        chapters = [e for e in result.hierarchy.elements if e.type == StructureType.CHAPTER]
        assert len(chapters) == 5
        
        # Check various formats detected
        titles = [ch.title for ch in chapters]
        assert "Getting Started" in titles
        assert "Basic Concepts" in titles
        assert "Advanced Topics" in titles
        assert "Applications" in titles
        assert "Final Project" in titles
    
    def test_detect_sections(self):
        """Test detection of section patterns"""
        text = """
        Chapter 1: Introduction
        
        1.1 Overview
        Some content here.
        
        1.2 Objectives
        Learning objectives.
        
        1.3 Prerequisites
        What you need to know.
        
        Chapter 2: Getting Started
        
        2.1 Installation
        How to install.
        
        2.2 Configuration
        Setup steps.
        """
        
        result = self.detector.detect_structure(text)
        
        sections = [e for e in result.hierarchy.elements if e.type == StructureType.SECTION]
        assert len(sections) == 5
        
        # Check section numbers and hierarchy
        section_numbers = [s.number for s in sections]
        assert "1.1" in section_numbers
        assert "1.2" in section_numbers
        assert "2.1" in section_numbers
        
        # Check levels
        for section in sections:
            assert section.level == 1  # Sections should be level 1
    
    def test_detect_subsections(self):
        """Test detection of subsection hierarchies"""
        text = """
        Chapter 1: Data Structures
        
        1.1 Arrays
        Introduction to arrays.
        
        1.1.1 Declaration
        How to declare arrays.
        
        1.1.2 Initialization
        Initializing array values.
        
        1.2 Lists
        Working with lists.
        
        1.2.1 Creating Lists
        List creation methods.
        """
        
        result = self.detector.detect_structure(text)
        
        subsections = [e for e in result.hierarchy.elements if e.type == StructureType.SUBSECTION]
        assert len(subsections) == 4
        
        # Check subsection levels
        for subsection in subsections:
            assert subsection.level == 2  # Subsections should be level 2
        
        # Check hierarchy
        assert result.hierarchy.max_depth == 2
    
    def test_confidence_scoring(self):
        """Test confidence scoring for different patterns"""
        text = """
        Chapter 1: Clear Chapter Title
        
        1.1 Clear Section Title
        
        SomeVagueHeading
        
        A
        """
        
        result = self.detector.detect_structure(text)
        
        elements = result.hierarchy.elements
        
        # Chapter should have high confidence
        chapter = next(e for e in elements if e.type == StructureType.CHAPTER)
        assert chapter.confidence > 0.8
        
        # Section should have good confidence
        section = next(e for e in elements if e.type == StructureType.SECTION)
        assert section.confidence > 0.7
        
        # Overall confidence should be reasonable
        assert result.hierarchy.overall_confidence > 0.5
    
    def test_numbering_consistency(self):
        """Test numbering consistency calculation"""
        # Consistent numbering
        consistent_text = """
        Chapter 1: First
        Chapter 2: Second
        Chapter 3: Third
        1.1 Section One
        1.2 Section Two
        2.1 Section Three
        """
        
        result = self.detector.detect_structure(consistent_text)
        assert result.hierarchy.numbering_consistency > 0.7
        
        # Inconsistent numbering
        inconsistent_text = """
        Chapter 1: First
        CHAPTER II: Second
        Ch. C: Third
        1.1 Section
        A.2 Another
        """
        
        result2 = self.detector.detect_structure(inconsistent_text)
        # Should detect the inconsistency
        assert result2.hierarchy.numbering_consistency < result.hierarchy.numbering_consistency
    
    def test_quality_scoring(self):
        """Test overall quality scoring"""
        # High quality structure
        good_text = """
        Chapter 1: Introduction to Programming
        
        1.1 What is Programming
        1.2 Programming Languages
        1.3 Getting Started
        
        Chapter 2: Variables and Data Types
        
        2.1 Variables
        2.2 Integer Types
        2.3 String Types
        
        Chapter 3: Control Structures
        
        3.1 Conditional Statements
        3.2 Loops
        3.3 Functions
        """
        
        good_result = self.detector.detect_structure(good_text)
        
        # Poor quality structure
        poor_text = """
        Page 1
        Some random text
        42
        Another line
        More content
        """
        
        poor_result = self.detector.detect_structure(poor_text)
        
        # Good structure should have higher quality
        assert good_result.hierarchy.quality_score > poor_result.hierarchy.quality_score
        assert good_result.hierarchy.quality_score > 0.6
    
    def test_textbook_validation(self):
        """Test textbook structure validation"""
        # Valid textbook structure
        valid_text = """
        Chapter 1: Introduction
        Chapter 2: Basic Concepts  
        Chapter 3: Advanced Topics
        Chapter 4: Applications
        """
        
        valid_result = self.detector.detect_structure(valid_text)
        assert valid_result.is_valid_textbook
        assert len(valid_result.warnings) == 0
        
        # Invalid textbook (too few chapters)
        invalid_text = """
        Chapter 1: Only Chapter
        Some content here.
        """
        
        invalid_result = self.detector.detect_structure(invalid_text)
        assert not invalid_result.is_valid_textbook
        assert any("Insufficient chapters" in warning for warning in invalid_result.warnings)
    
    def test_roman_numeral_detection(self):
        """Test detection of Roman numeral patterns"""
        text = """
        Chapter I: Introduction
        Chapter II: Methodology
        Chapter III: Results
        
        I. First Section
        II. Second Section
        """
        
        result = self.detector.detect_structure(text)
        
        chapters = [e for e in result.hierarchy.elements if e.type == StructureType.CHAPTER]
        assert len(chapters) == 3
        
        # Check Roman numeral numbering style
        roman_chapters = [ch for ch in chapters if ch.numbering_style == NumberingStyle.ROMAN_UPPER]
        assert len(roman_chapters) == 3
    
    def test_mixed_numbering_styles(self):
        """Test handling of mixed numbering styles"""
        text = """
        Chapter 1: Numeric
        Chapter II: Roman
        Chapter C: Letter
        
        1.1 Decimal section
        A. Letter section
        i. Roman section
        """
        
        result = self.detector.detect_structure(text)
        
        # Should detect all elements despite mixed styles
        assert result.hierarchy.total_chapters == 3
        assert len([e for e in result.hierarchy.elements if e.type == StructureType.SECTION]) == 3
        
        # Numbering consistency should be lower
        assert result.hierarchy.numbering_consistency < 0.8
    
    def test_position_tracking(self):
        """Test that positions are tracked correctly"""
        text = """Chapter 1: First
        
        Some content in chapter 1.
        
        Chapter 2: Second
        
        Some content in chapter 2."""
        
        result = self.detector.detect_structure(text)
        
        chapters = [e for e in result.hierarchy.elements if e.type == StructureType.CHAPTER]
        assert len(chapters) == 2
        
        # First chapter should start at beginning
        assert chapters[0].start_position < chapters[1].start_position
        
        # End positions should be set
        assert chapters[0].end_position is not None
        assert chapters[0].end_position > chapters[0].start_position
    
    def test_statistics_generation(self):
        """Test statistics generation"""
        text = """
        Chapter 1: Introduction
        
        1.1 Overview
        1.2 Objectives
        
        Chapter 2: Methods
        
        2.1 Approach
        2.2 Implementation
        
        Chapter 3: Results
        """
        
        result = self.detector.detect_structure(text)
        stats = result.statistics
        
        # Check basic statistics
        assert stats['total_elements'] > 0
        assert 'chapter' in stats['element_types']
        assert 'section' in stats['element_types']
        assert stats['element_types']['chapter'] == 3
        
        # Check confidence distribution
        assert 'high' in stats['confidence_distribution']
        assert 'medium' in stats['confidence_distribution']
        assert 'low' in stats['confidence_distribution']
        
        # Check coverage
        assert 0 <= stats['text_coverage'] <= 1.0
    
    def test_edge_cases(self):
        """Test various edge cases"""
        # Very short text
        short_result = self.detector.detect_structure("Chapter 1")
        assert short_result.hierarchy.total_chapters == 1
        
        # Text with no structure
        no_structure_result = self.detector.detect_structure("Just some random text with no structure at all.")
        assert no_structure_result.hierarchy.total_chapters == 0
        
        # Text with only sections (no chapters)
        sections_only = self.detector.detect_structure("1.1 First\n1.2 Second\n1.3 Third")
        assert sections_only.hierarchy.total_chapters == 0
        assert sections_only.hierarchy.total_sections > 0
    
    def test_case_insensitive_detection(self):
        """Test case-insensitive pattern matching"""
        text = """
        CHAPTER 1: UPPERCASE
        chapter 2: lowercase
        Chapter 3: Mixed Case
        """
        
        result = self.detector.detect_structure(text)
        assert result.hierarchy.total_chapters == 3
        
        chapters = [e for e in result.hierarchy.elements if e.type == StructureType.CHAPTER]
        titles = [ch.title for ch in chapters]
        assert "UPPERCASE" in titles
        assert "lowercase" in titles
        assert "Mixed Case" in titles


if __name__ == "__main__":
    pytest.main([__file__, "-v"])