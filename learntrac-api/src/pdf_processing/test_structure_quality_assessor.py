"""
Unit tests for StructureQualityAssessor class

Tests structure quality assessment with various textbook structures including
well-organized academic texts and poorly structured documents.
"""

import pytest
from unittest.mock import Mock
from .structure_quality_assessor import (
    StructureQualityAssessor,
    QualityAssessment,
    ChunkingStrategy
)
from .structure_detector import (
    DetectionResult,
    StructureHierarchy,
    StructureElement,
    StructureType,
    NumberingStyle
)


class TestStructureQualityAssessor:
    """Test suite for StructureQualityAssessor class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.assessor = StructureQualityAssessor(
            strategy_threshold=0.3,
            min_chapters_for_structure=2,
            max_sections_per_chapter=10
        )
        
        # Create well-structured textbook example
        self.good_elements = [
            StructureElement(
                type=StructureType.CHAPTER,
                title="Introduction to Programming",
                number="1",
                level=0,
                start_position=0,
                end_position=1000,
                confidence=0.9,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="Chapter 1: Introduction to Programming"
            ),
            StructureElement(
                type=StructureType.SECTION,
                title="What is Programming?",
                number="1.1",
                level=1,
                start_position=100,
                end_position=400,
                confidence=0.8,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="1.1 What is Programming?"
            ),
            StructureElement(
                type=StructureType.SECTION,
                title="Programming Languages",
                number="1.2",
                level=1,
                start_position=400,
                end_position=700,
                confidence=0.8,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="1.2 Programming Languages"
            ),
            StructureElement(
                type=StructureType.CHAPTER,
                title="Variables and Data Types",
                number="2",
                level=0,
                start_position=1000,
                end_position=2000,
                confidence=0.9,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="Chapter 2: Variables and Data Types"
            ),
            StructureElement(
                type=StructureType.SECTION,
                title="Integer Variables",
                number="2.1",
                level=1,
                start_position=1100,
                end_position=1400,
                confidence=0.8,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="2.1 Integer Variables"
            ),
            StructureElement(
                type=StructureType.SECTION,
                title="String Variables",
                number="2.2",
                level=1,
                start_position=1400,
                end_position=1700,
                confidence=0.8,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="2.2 String Variables"
            ),
            StructureElement(
                type=StructureType.CHAPTER,
                title="Control Structures",
                number="3",
                level=0,
                start_position=2000,
                end_position=3000,
                confidence=0.9,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="Chapter 3: Control Structures"
            )
        ]
        
        self.good_hierarchy = StructureHierarchy(
            elements=self.good_elements,
            total_chapters=3,
            total_sections=4,
            max_depth=1,
            numbering_consistency=0.9,
            overall_confidence=0.85,
            quality_score=0.8
        )
        
        self.good_detection_result = DetectionResult(
            hierarchy=self.good_hierarchy,
            is_valid_textbook=True,
            warnings=[],
            statistics={}
        )
        
        # Create poorly structured example
        self.poor_elements = [
            StructureElement(
                type=StructureType.SECTION,  # Section without chapter
                title="some content",
                number="",
                level=0,
                start_position=0,
                end_position=500,
                confidence=0.3,
                numbering_style=None,
                raw_text="some content"
            )
        ]
        
        self.poor_hierarchy = StructureHierarchy(
            elements=self.poor_elements,
            total_chapters=0,
            total_sections=1,
            max_depth=0,
            numbering_consistency=0.1,
            overall_confidence=0.3,
            quality_score=0.2
        )
        
        self.poor_detection_result = DetectionResult(
            hierarchy=self.poor_hierarchy,
            is_valid_textbook=False,
            warnings=["Inconsistent structure"],
            statistics={}
        )
    
    def test_init_default(self):
        """Test StructureQualityAssessor initialization with defaults"""
        assessor = StructureQualityAssessor()
        assert assessor.strategy_threshold == 0.3
        assert assessor.min_chapters_for_structure == 2
        assert assessor.max_sections_per_chapter == 20
        assert sum(assessor.weights.values()) == 1.0
    
    def test_init_custom(self):
        """Test StructureQualityAssessor initialization with custom settings"""
        assessor = StructureQualityAssessor(
            strategy_threshold=0.5,
            min_chapters_for_structure=3,
            max_sections_per_chapter=15
        )
        assert assessor.strategy_threshold == 0.5
        assert assessor.min_chapters_for_structure == 3
        assert assessor.max_sections_per_chapter == 15
    
    def test_assess_good_structure_quality(self):
        """Test assessment of well-structured document"""
        assessment = self.assessor.assess_structure_quality(self.good_detection_result)
        
        # Should recommend content-aware chunking
        assert assessment.recommended_strategy == ChunkingStrategy.CONTENT_AWARE
        assert assessment.overall_quality_score >= self.assessor.strategy_threshold
        assert assessment.confidence > 0.7
        
        # Check individual components
        assert assessment.heading_consistency_score > 0.7
        assert assessment.chapter_boundary_score > 0.5
        assert assessment.section_organization_score > 0.5
        assert assessment.hierarchy_logic_score > 0.7
        
        # Check structure characteristics
        assert assessment.has_clear_chapters is True
        assert assessment.has_logical_hierarchy is True
        assert assessment.has_consistent_numbering is True
        assert assessment.supports_educational_chunking is True
        
        # Check counts
        assert assessment.chapter_count == 3
        assert assessment.section_count == 4
        assert assessment.max_hierarchy_depth == 1
    
    def test_assess_poor_structure_quality(self):
        """Test assessment of poorly structured document"""
        assessment = self.assessor.assess_structure_quality(self.poor_detection_result)
        
        # Should recommend fallback chunking
        assert assessment.recommended_strategy == ChunkingStrategy.FALLBACK
        assert assessment.overall_quality_score < self.assessor.strategy_threshold
        assert assessment.confidence > 0.5  # Should be confident in fallback recommendation
        
        # Check structure characteristics
        assert assessment.has_clear_chapters is False
        assert assessment.has_logical_hierarchy is False
        assert assessment.has_consistent_numbering is False
        assert assessment.supports_educational_chunking is False
        
        # Should have warnings
        assert len(assessment.warnings) > 0
        assert len(assessment.improvement_suggestions) > 0
    
    def test_assess_empty_structure(self):
        """Test assessment with no structure detected"""
        empty_detection = DetectionResult(
            hierarchy=None,
            is_valid_textbook=False,
            warnings=["No structure detected"],
            statistics={}
        )
        
        assessment = self.assessor.assess_structure_quality(empty_detection)
        
        assert assessment.recommended_strategy == ChunkingStrategy.FALLBACK
        assert assessment.overall_quality_score == 0.0
        assert assessment.confidence == 0.9  # High confidence in fallback
        assert "No structure detected" in assessment.warnings[0]
    
    def test_assess_no_elements(self):
        """Test assessment with empty elements list"""
        empty_hierarchy = StructureHierarchy(
            elements=[],
            total_chapters=0,
            total_sections=0,
            max_depth=0,
            numbering_consistency=0.0,
            overall_confidence=0.0,
            quality_score=0.0
        )
        
        empty_detection = DetectionResult(
            hierarchy=empty_hierarchy,
            is_valid_textbook=False,
            warnings=[],
            statistics={}
        )
        
        assessment = self.assessor.assess_structure_quality(empty_detection)
        
        assert assessment.recommended_strategy == ChunkingStrategy.FALLBACK
        assert assessment.overall_quality_score == 0.0
        assert "No structural elements found" in assessment.warnings[0]
    
    def test_heading_consistency_assessment(self):
        """Test heading consistency evaluation"""
        # Test with consistent numbering
        consistent_elements = [
            StructureElement(
                type=StructureType.CHAPTER, title="Chapter One", number="1",
                level=0, start_position=0, end_position=100,
                numbering_style=NumberingStyle.ARABIC, confidence=0.9,
                raw_text="Chapter 1: Chapter One"
            ),
            StructureElement(
                type=StructureType.CHAPTER, title="Chapter Two", number="2",
                level=0, start_position=100, end_position=200,
                numbering_style=NumberingStyle.ARABIC, confidence=0.9,
                raw_text="Chapter 2: Chapter Two"
            )
        ]
        
        consistency_score = self.assessor._assess_heading_consistency(consistent_elements)
        assert consistency_score > 0.8
        
        # Test with inconsistent numbering
        inconsistent_elements = [
            StructureElement(
                type=StructureType.CHAPTER, title="Chapter One", number="1",
                level=0, start_position=0, end_position=100,
                numbering_style=NumberingStyle.ARABIC, confidence=0.9,
                raw_text="Chapter 1: Chapter One"
            ),
            StructureElement(
                type=StructureType.CHAPTER, title="Chapter II", number="II",
                level=0, start_position=100, end_position=200,
                numbering_style=NumberingStyle.ROMAN_UPPER, confidence=0.9,
                raw_text="Chapter II: Chapter Two"
            )
        ]
        
        inconsistency_score = self.assessor._assess_heading_consistency(inconsistent_elements)
        assert inconsistency_score < consistency_score
    
    def test_chapter_boundary_assessment(self):
        """Test chapter boundary evaluation"""
        # Test with good chapter structure
        chapters = [e for e in self.good_elements if e.type == StructureType.CHAPTER]
        boundary_score = self.assessor._assess_chapter_boundaries(self.good_elements, self.good_hierarchy)
        assert boundary_score > 0.5
        
        # Test with insufficient chapters
        single_chapter = [chapters[0]]
        single_hierarchy = Mock()
        single_hierarchy.total_chapters = 1
        
        low_score = self.assessor._assess_chapter_boundaries(single_chapter, single_hierarchy)
        assert low_score < boundary_score
    
    def test_section_organization_assessment(self):
        """Test section organization evaluation"""
        org_score = self.assessor._assess_section_organization(self.good_elements, self.good_hierarchy)
        assert org_score > 0.5
        
        # Test with no sections
        chapters_only = [e for e in self.good_elements if e.type == StructureType.CHAPTER]
        no_sections_hierarchy = Mock()
        no_sections_hierarchy.max_depth = 0
        
        minimal_score = self.assessor._assess_section_organization(chapters_only, no_sections_hierarchy)
        assert minimal_score == 0.3  # Base score for minimal structure
    
    def test_hierarchy_logic_assessment(self):
        """Test hierarchy logic evaluation"""
        logic_score = self.assessor._assess_hierarchy_logic(self.good_elements, self.good_hierarchy)
        assert logic_score > 0.7
        
        # Test with orphaned sections
        orphaned_elements = [
            StructureElement(
                type=StructureType.SECTION, title="Orphaned", number="1",
                level=1, start_position=0, end_position=100,
                confidence=0.8, numbering_style=NumberingStyle.ARABIC,
                raw_text="1. Orphaned Section"
            )
        ]
        
        orphaned_score = self.assessor._assess_hierarchy_logic(orphaned_elements, Mock())
        assert orphaned_score < logic_score
    
    def test_strategy_determination(self):
        """Test chunking strategy determination"""
        # High quality should recommend content-aware
        strategy, confidence = self.assessor._determine_strategy(0.8, self.good_hierarchy)
        assert strategy == ChunkingStrategy.CONTENT_AWARE
        assert confidence > 0.7
        
        # Low quality should recommend fallback
        strategy, confidence = self.assessor._determine_strategy(0.1, self.poor_hierarchy)
        assert strategy == ChunkingStrategy.FALLBACK
        assert confidence > 0.5
        
        # Borderline quality should consider hybrid
        borderline_score = self.assessor.strategy_threshold + 0.05
        strategy, confidence = self.assessor._determine_strategy(borderline_score, self.good_hierarchy)
        # Could be either content-aware or hybrid depending on exact implementation
        assert strategy in [ChunkingStrategy.CONTENT_AWARE, ChunkingStrategy.HYBRID]
    
    def test_structure_characteristics_analysis(self):
        """Test structure characteristics analysis"""
        analysis = self.assessor._analyze_structure_characteristics(self.good_elements, self.good_hierarchy)
        
        assert analysis['chapter_count'] == 3
        assert analysis['section_count'] == 4
        assert analysis['subsection_count'] == 0
        assert analysis['has_clear_chapters'] is True
        assert analysis['has_logical_hierarchy'] is True
        assert analysis['average_sections_per_chapter'] == 4/3
        assert analysis['hierarchy_depth_appropriate'] is True
        assert analysis['numbering_consistent'] is True
    
    def test_warning_generation(self):
        """Test warning generation for structure issues"""
        # Test with insufficient chapters
        few_chapters_hierarchy = Mock()
        few_chapters_hierarchy.total_chapters = 1
        few_chapters_hierarchy.numbering_consistency = 0.9
        few_chapters_hierarchy.max_depth = 1
        
        analysis = {'chapter_count': 1, 'average_sections_per_chapter': 2}
        warnings = self.assessor._generate_warnings(few_chapters_hierarchy, analysis)
        
        assert len(warnings) > 0
        assert any("chapters" in warning.lower() for warning in warnings)
        
        # Test with inconsistent numbering
        inconsistent_hierarchy = Mock()
        inconsistent_hierarchy.total_chapters = 3
        inconsistent_hierarchy.numbering_consistency = 0.3
        inconsistent_hierarchy.max_depth = 1
        
        analysis = {'chapter_count': 3, 'average_sections_per_chapter': 2}
        warnings = self.assessor._generate_warnings(inconsistent_hierarchy, analysis)
        
        assert any("numbering" in warning.lower() for warning in warnings)
    
    def test_improvement_suggestions(self):
        """Test improvement suggestion generation"""
        suggestions = self.assessor._generate_improvement_suggestions(
            0.2,  # Low quality score
            {'chapter_count': 0, 'average_sections_per_chapter': 0, 'has_logical_hierarchy': False},
            self.poor_hierarchy
        )
        
        assert len(suggestions) > 0
        assert any("manual structure review" in suggestion.lower() for suggestion in suggestions)
        assert any("chapter" in suggestion.lower() for suggestion in suggestions)
    
    def test_level_consistency_check(self):
        """Test level consistency checking"""
        # Good level consistency
        type_level_patterns = {
            (StructureType.CHAPTER, 0): [Mock(), Mock()],
            (StructureType.SECTION, 1): [Mock(), Mock(), Mock()]
        }
        
        consistency = self.assessor._check_level_consistency(type_level_patterns)
        assert consistency == 1.0
        
        # Poor level consistency
        bad_patterns = {
            (StructureType.CHAPTER, 0): [Mock()],
            (StructureType.CHAPTER, 1): [Mock()],  # Chapters at wrong level
            (StructureType.SECTION, 1): [Mock()]
        }
        
        bad_consistency = self.assessor._check_level_consistency(bad_patterns)
        assert bad_consistency < 1.0
    
    def test_sequential_numbering_check(self):
        """Test sequential numbering validation"""
        # Sequential numbering
        sequential_elements = [
            Mock(type=StructureType.CHAPTER, level=0, number="1", start_position=0),
            Mock(type=StructureType.CHAPTER, level=0, number="2", start_position=100),
            Mock(type=StructureType.CHAPTER, level=0, number="3", start_position=200)
        ]
        
        sequential_score = self.assessor._check_sequential_numbering(sequential_elements)
        assert sequential_score == 1.0
        
        # Non-sequential numbering
        non_sequential_elements = [
            Mock(type=StructureType.CHAPTER, level=0, number="1", start_position=0),
            Mock(type=StructureType.CHAPTER, level=0, number="5", start_position=100),
            Mock(type=StructureType.CHAPTER, level=0, number="2", start_position=200)
        ]
        
        non_sequential_score = self.assessor._check_sequential_numbering(non_sequential_elements)
        assert non_sequential_score < sequential_score
    
    def test_chapter_spacing_assessment(self):
        """Test chapter spacing evaluation"""
        # Well-spaced chapters
        well_spaced = [
            Mock(start_position=0, end_position=100),
            Mock(start_position=200, end_position=300),
            Mock(start_position=400, end_position=500)
        ]
        
        spacing_score = self.assessor._assess_chapter_spacing(well_spaced)
        assert spacing_score > 0.5
        
        # Poorly spaced chapters
        poorly_spaced = [
            Mock(start_position=0, end_position=100),
            Mock(start_position=101, end_position=200),  # Too close
            Mock(start_position=1000, end_position=1100)  # Too far
        ]
        
        poor_spacing_score = self.assessor._assess_chapter_spacing(poorly_spaced)
        assert poor_spacing_score < spacing_score
    
    def test_chapter_title_quality(self):
        """Test chapter title quality assessment"""
        # Good titles
        good_chapters = [
            Mock(title="Introduction to Programming"),
            Mock(title="Advanced Data Structures"),
            Mock(title="Algorithm Design Principles")
        ]
        
        good_score = self.assessor._assess_chapter_title_quality(good_chapters)
        assert good_score > 0.6
        
        # Poor titles
        poor_chapters = [
            Mock(title=""),
            Mock(title="ch1"),
            Mock(title="stuff")
        ]
        
        poor_score = self.assessor._assess_chapter_title_quality(poor_chapters)
        assert poor_score < good_score
    
    def test_hierarchical_depth_assessment(self):
        """Test hierarchical depth appropriateness"""
        # Ideal depth
        ideal_score = self.assessor._assess_hierarchical_depth(2)
        assert ideal_score == 1.0
        
        # Too shallow
        shallow_score = self.assessor._assess_hierarchical_depth(0)
        assert shallow_score < ideal_score
        
        # Too deep
        deep_score = self.assessor._assess_hierarchical_depth(6)
        assert deep_score < ideal_score
    
    def test_proper_nesting_check(self):
        """Test proper nesting validation"""
        # Well-nested elements
        well_nested = [
            Mock(type=StructureType.CHAPTER, start_position=0),
            Mock(type=StructureType.SECTION, start_position=100),
            Mock(type=StructureType.SECTION, start_position=200),
            Mock(type=StructureType.CHAPTER, start_position=300),
            Mock(type=StructureType.SECTION, start_position=400)
        ]
        
        nesting_score = self.assessor._check_proper_nesting(well_nested)
        assert nesting_score == 1.0
        
        # Poorly nested (section without chapter)
        poorly_nested = [
            Mock(type=StructureType.SECTION, start_position=0),  # Orphaned section
            Mock(type=StructureType.CHAPTER, start_position=100),
            Mock(type=StructureType.SECTION, start_position=200)
        ]
        
        poor_nesting_score = self.assessor._check_proper_nesting(poorly_nested)
        assert poor_nesting_score < nesting_score
    
    def test_borderline_quality_hybrid_strategy(self):
        """Test hybrid strategy recommendation for borderline quality"""
        # Create borderline quality detection result
        borderline_hierarchy = StructureHierarchy(
            elements=self.good_elements[:2],  # Fewer elements
            total_chapters=1,  # Below minimum
            total_sections=1,
            max_depth=1,
            numbering_consistency=0.6,
            overall_confidence=0.4,
            quality_score=0.35  # Just above threshold
        )
        
        borderline_detection = DetectionResult(
            hierarchy=borderline_hierarchy,
            is_valid_textbook=False,
            warnings=["Borderline structure"],
            statistics={}
        )
        
        assessment = self.assessor.assess_structure_quality(borderline_detection)
        
        # Could recommend hybrid for borderline cases
        assert assessment.recommended_strategy in [ChunkingStrategy.CONTENT_AWARE, ChunkingStrategy.HYBRID]
        assert 0.1 <= assessment.confidence <= 1.0
    
    def test_edge_cases(self):
        """Test various edge cases"""
        # Single element
        single_element = [self.good_elements[0]]
        single_hierarchy = StructureHierarchy(
            elements=single_element,
            total_chapters=1,
            total_sections=0,
            max_depth=0,
            numbering_consistency=1.0,
            overall_confidence=0.9,
            quality_score=0.5
        )
        
        single_detection = DetectionResult(
            hierarchy=single_hierarchy,
            is_valid_textbook=False,
            warnings=[],
            statistics={}
        )
        
        assessment = self.assessor.assess_structure_quality(single_detection)
        assert assessment.recommended_strategy == ChunkingStrategy.FALLBACK
        
        # Very high quality
        perfect_hierarchy = StructureHierarchy(
            elements=self.good_elements,
            total_chapters=3,
            total_sections=4,
            max_depth=1,
            numbering_consistency=1.0,
            overall_confidence=1.0,
            quality_score=1.0
        )
        
        perfect_detection = DetectionResult(
            hierarchy=perfect_hierarchy,
            is_valid_textbook=True,
            warnings=[],
            statistics={}
        )
        
        perfect_assessment = self.assessor.assess_structure_quality(perfect_detection)
        assert perfect_assessment.recommended_strategy == ChunkingStrategy.CONTENT_AWARE
        assert perfect_assessment.confidence > 0.9
    
    def test_quality_assessment_string_representation(self):
        """Test string representation of QualityAssessment"""
        assessment = self.assessor.assess_structure_quality(self.good_detection_result)
        
        str_repr = str(assessment)
        assert "QualityAssessment" in str_repr
        assert f"score={assessment.overall_quality_score:.2f}" in str_repr
        assert assessment.recommended_strategy.value in str_repr
        assert f"confidence={assessment.confidence:.2f}" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])