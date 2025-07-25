"""
Unit tests for ContentFilter class

Tests comprehensive content filtering including prefatory removal,
appendix detection, and core content preservation.
"""

import pytest
from .content_filter import (
    ContentFilter, 
    ContentType, 
    ContentSection,
    FilteringResult
)
from .structure_detector import StructureDetector, StructureElement, StructureType


class TestContentFilter:
    """Test suite for ContentFilter class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.filter = ContentFilter(min_retention_ratio=0.5)
        self.aggressive_filter = ContentFilter(min_retention_ratio=0.5, aggressive_filtering=True)
    
    def test_init_default(self):
        """Test ContentFilter initialization with defaults"""
        filter_obj = ContentFilter()
        assert filter_obj.min_retention_ratio == 0.5
        assert filter_obj.preserve_learning_objectives is True
        assert filter_obj.aggressive_filtering is False
    
    def test_init_custom(self):
        """Test ContentFilter initialization with custom settings"""
        filter_obj = ContentFilter(
            min_retention_ratio=0.7,
            preserve_learning_objectives=False,
            aggressive_filtering=True
        )
        assert filter_obj.min_retention_ratio == 0.7
        assert filter_obj.preserve_learning_objectives is False
        assert filter_obj.aggressive_filtering is True
    
    def test_filter_empty_text(self):
        """Test filtering empty text"""
        result = self.filter.filter_content("")
        assert result.filtered_text == ""
        assert result.quality_score == 0.0
        assert "Empty text" in result.warnings[0]
    
    def test_basic_prefatory_removal(self):
        """Test removal of basic prefatory content"""
        text = """
        Copyright © 2023 Publisher Name
        All rights reserved.
        
        Table of Contents
        Chapter 1 ........................ 5
        Chapter 2 ........................ 15
        
        Preface
        This book is intended for students.
        
        Chapter 1: Introduction
        This is the actual content of the book.
        It contains the main educational material.
        
        Chapter 2: Basic Concepts
        More educational content here.
        """
        
        result = self.filter.filter_content(text)
        
        # Copyright should be removed
        assert "Copyright" not in result.filtered_text
        assert "All rights reserved" not in result.filtered_text
        
        # Table of contents should be removed
        assert "Table of Contents" not in result.filtered_text
        
        # Core content should be preserved
        assert "This is the actual content" in result.filtered_text
        assert "More educational content" in result.filtered_text
        
        # Should have reasonable retention ratio
        assert result.stats.retention_ratio > 0.4
        assert result.stats.prefatory_removed > 0
    
    def test_appendix_removal(self):
        """Test removal of appendix content"""
        text = """
        Chapter 1: Main Content
        This is the core educational material.
        
        Chapter 2: More Content  
        Additional learning material.
        
        Appendix A: Additional Resources
        Extra materials for reference.
        
        Bibliography
        [1] Author, A. (2023). Book Title.
        [2] Author, B. (2022). Another Book.
        
        Index
        A
        Array, 15, 23, 45
        B
        Boolean, 12, 34
        """
        
        result = self.filter.filter_content(text)
        
        # Core content should be preserved
        assert "core educational material" in result.filtered_text
        assert "Additional learning material" in result.filtered_text
        
        # Appendix content should be removed
        assert "Appendix A" not in result.filtered_text
        assert "Extra materials" not in result.filtered_text
        assert "Bibliography" not in result.filtered_text
        assert "Author, A. (2023)" not in result.filtered_text
        assert "Index" not in result.filtered_text
        assert "Array, 15, 23" not in result.filtered_text
        
        assert result.stats.appendix_removed > 0
    
    def test_learning_objectives_preservation(self):
        """Test preservation of learning objectives in prefatory content"""
        text = """
        Preface
        This book covers important topics.
        
        Learning Objectives
        After reading this book, you will:
        - Understand basic concepts
        - Apply advanced techniques
        
        Chapter 1: Introduction
        Main content starts here.
        """
        
        result = self.filter.filter_content(text)
        
        # Learning objectives should be preserved even though in preface
        assert "Learning Objectives" in result.filtered_text
        assert "Understand basic concepts" in result.filtered_text
        assert "Apply advanced techniques" in result.filtered_text
        
        # Main content should be preserved
        assert "Main content starts here" in result.filtered_text
    
    def test_learning_objectives_preservation_disabled(self):
        """Test when learning objectives preservation is disabled"""
        no_preserve_filter = ContentFilter(preserve_learning_objectives=False)
        
        text = """
        Preface
        Learning Objectives
        - Understand concepts
        - Apply techniques
        
        Chapter 1: Introduction
        Main content here.
        """
        
        result = no_preserve_filter.filter_content(text)
        
        # Learning objectives should be removed
        assert "Learning Objectives" not in result.filtered_text
        assert "Understand concepts" not in result.filtered_text
        
        # Main content should still be preserved
        assert "Main content here" in result.filtered_text
    
    def test_table_of_contents_detection(self):
        """Test detection and removal of table of contents"""
        toc_text = """
        Table of Contents
        
        Chapter 1: Introduction ............... 5
        Chapter 2: Basic Concepts ............ 15
        Chapter 3: Advanced Topics .......... 25
        
        Chapter 1: Introduction
        This is the actual chapter content.
        """
        
        result = self.filter.filter_content(toc_text)
        
        # TOC should be removed
        assert "Chapter 1: Introduction ..........." not in result.filtered_text
        assert "Chapter 2: Basic Concepts" not in result.filtered_text or "Chapter 2:" in result.filtered_text.split("actual chapter content")[0]
        
        # Actual content should be preserved
        assert "This is the actual chapter content" in result.filtered_text
    
    def test_aggressive_filtering(self):
        """Test aggressive filtering mode"""
        text = """
        Preface
        Some introductory material.
        
        Overview
        General overview of topics.
        
        Chapter 1: Main Content
        This is the core material.
        """
        
        # Normal filtering
        normal_result = self.filter.filter_content(text)
        
        # Aggressive filtering
        aggressive_result = self.aggressive_filter.filter_content(text)
        
        # Aggressive should remove more content
        assert len(aggressive_result.filtered_text) <= len(normal_result.filtered_text)
        
        # Core content should still be in both
        assert "This is the core material" in normal_result.filtered_text
        assert "This is the core material" in aggressive_result.filtered_text
    
    def test_retention_ratio_validation(self):
        """Test validation of minimum retention ratio"""
        # Text with mostly prefatory content
        mostly_prefatory = """
        Copyright © 2023
        Publisher information
        More copyright text
        Even more legal text
        
        Chapter 1: Tiny Content
        Small.
        """
        
        result = self.filter.filter_content(mostly_prefatory)
        
        # Should warn about low retention or return original
        assert (result.stats.retention_ratio >= self.filter.min_retention_ratio or
                len(result.warnings) > 0)
    
    def test_content_type_classification(self):
        """Test classification of different content types"""
        text = """
        Copyright © 2023 Test Publisher
        
        Acknowledgments
        Thanks to everyone who helped.
        
        Chapter 1: Introduction
        Main educational content.
        
        Appendix A: Resources
        Additional materials.
        
        Bibliography
        Reference materials.
        """
        
        result = self.filter.filter_content(text)
        
        # Check that different content types were identified
        content_types = result.stats.content_types_found
        assert ContentType.COPYRIGHT in content_types
        assert ContentType.ACKNOWLEDGMENTS in content_types
        assert ContentType.CORE_CONTENT in content_types
        assert ContentType.APPENDIX in content_types
        assert ContentType.BIBLIOGRAPHY in content_types
    
    def test_quality_scoring(self):
        """Test quality scoring for filtering results"""
        # Good structure with clear boundaries
        good_text = """
        Copyright notice here.
        
        Chapter 1: Introduction
        Educational content with good structure.
        Multiple sentences and paragraphs.
        
        Chapter 2: Advanced Topics
        More detailed educational material.
        
        Bibliography
        Reference materials.
        """
        
        good_result = self.filter.filter_content(good_text)
        
        # Poor structure (mostly artifacts)
        poor_text = """
        Copyright © 2023
        More copyright
        Publisher info
        Legal text
        """
        
        poor_result = self.filter.filter_content(poor_text)
        
        # Good structure should have higher quality
        assert good_result.quality_score > poor_result.quality_score
        assert good_result.quality_score > 0.5
    
    def test_structure_element_integration(self):
        """Test integration with pre-detected structure elements"""
        from .structure_detector import StructureElement, StructureType, NumberingStyle
        
        text = """
        Preface content here.
        
        Chapter 1: Introduction
        Main content.
        
        Appendix A: Extra
        Additional info.
        """
        
        # Create mock structure elements
        elements = [
            StructureElement(
                type=StructureType.CHAPTER,
                title="Introduction",
                number="1",
                level=0,
                start_position=text.find("Chapter 1"),
                end_position=text.find("Appendix A"),
                page_number=None,
                confidence=0.9,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="Chapter 1: Introduction"
            )
        ]
        
        result = self.filter.filter_content(text, structure_elements=elements)
        
        # Should use provided structure elements
        assert "Main content" in result.filtered_text
        assert result.stats.core_content_retained > 0
    
    def test_no_structure_fallback(self):
        """Test behavior when no clear structure is detected"""
        unstructured_text = """
        This is some text without clear chapter structure.
        It has multiple paragraphs but no obvious organization.
        
        There might be some educational content here.
        And some more content that should be preserved.
        
        This could be considered core material.
        """
        
        result = self.filter.filter_content(unstructured_text)
        
        # Should preserve most content when structure is unclear
        assert result.stats.retention_ratio > 0.7
        assert "educational content" in result.filtered_text
        assert "core material" in result.filtered_text
    
    def test_copyright_pattern_detection(self):
        """Test detection of various copyright patterns"""
        copyright_variations = [
            "Copyright © 2023 Publisher",
            "Copyright (c) 2023 Company", 
            "© 2023 Author Name",
            "(C) 2023 Organization",
            "Copyright 2020-2023 Publisher"
        ]
        
        for copyright_text in copyright_variations:
            text = f"""
            {copyright_text}
            All rights reserved.
            
            Chapter 1: Content
            Educational material here.
            """
            
            result = self.filter.filter_content(text)
            
            # Copyright should be removed
            assert copyright_text not in result.filtered_text
            # Educational content should remain
            assert "Educational material" in result.filtered_text
    
    def test_edge_cases(self):
        """Test various edge cases"""
        # Empty sections
        empty_result = self.filter.filter_content("")
        assert empty_result.filtered_text == ""
        
        # Very short text
        short_result = self.filter.filter_content("Chapter 1: Short")
        assert "Short" in short_result.filtered_text
        
        # No chapters, just content
        no_chapters_result = self.filter.filter_content("Some educational content without chapters.")
        assert "educational content" in no_chapters_result.filtered_text
    
    def test_statistics_accuracy(self):
        """Test accuracy of filtering statistics"""
        text = """
        Copyright © 2023
        
        Chapter 1: Content
        Educational material.
        
        Appendix A: Extra
        Additional resources.
        """
        
        result = self.filter.filter_content(text)
        stats = result.stats
        
        # Check statistics make sense
        assert stats.original_length == len(text)
        assert stats.filtered_length == len(result.filtered_text)
        assert 0 <= stats.retention_ratio <= 1.0
        assert stats.sections_identified > 0
        assert sum(stats.content_types_found.values()) == stats.sections_identified


if __name__ == "__main__":
    pytest.main([__file__, "-v"])