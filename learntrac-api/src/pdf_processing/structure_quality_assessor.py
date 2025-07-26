"""
Structure Quality Assessor - Evaluates document structure quality for chunking strategy selection

Analyzes structure detector results to determine optimal chunking approach based on
document organization quality and educational content structure.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .structure_detector import DetectionResult, StructureElement, StructureType, NumberingStyle


class ChunkingStrategy(Enum):
    """Available chunking strategies"""
    CONTENT_AWARE = "content_aware"
    FALLBACK = "fallback"
    HYBRID = "hybrid"


@dataclass
class QualityAssessment:
    """Result of structure quality assessment"""
    overall_quality_score: float  # 0.0 to 1.0
    recommended_strategy: ChunkingStrategy
    confidence: float  # Confidence in the recommendation
    
    # Individual quality components
    heading_consistency_score: float
    chapter_boundary_score: float
    section_organization_score: float
    hierarchy_logic_score: float
    
    # Detailed analysis
    total_structural_elements: int
    chapter_count: int
    section_count: int
    subsection_count: int
    max_hierarchy_depth: int
    numbering_consistency: float
    
    # Quality indicators
    has_clear_chapters: bool
    has_logical_hierarchy: bool
    has_consistent_numbering: bool
    supports_educational_chunking: bool
    
    # Warnings and recommendations
    warnings: List[str]
    improvement_suggestions: List[str]
    
    def __str__(self) -> str:
        return (f"QualityAssessment(score={self.overall_quality_score:.2f}, "
                f"strategy={self.recommended_strategy.value}, "
                f"confidence={self.confidence:.2f})")


class StructureQualityAssessor:
    """
    Evaluates document structure quality to determine optimal chunking strategy.
    
    Analyzes detected structure from StructureDetector and calculates quality scores
    based on educational document standards and structure consistency.
    """
    
    def __init__(self,
                 strategy_threshold: float = 0.3,
                 min_chapters_for_structure: int = 2,
                 max_sections_per_chapter: int = 20):
        """
        Initialize structure quality assessor.
        
        Args:
            strategy_threshold: Minimum quality score for content-aware chunking
            min_chapters_for_structure: Minimum chapters for structured approach
            max_sections_per_chapter: Maximum reasonable sections per chapter
        """
        self.strategy_threshold = strategy_threshold
        self.min_chapters_for_structure = min_chapters_for_structure
        self.max_sections_per_chapter = max_sections_per_chapter
        
        self.logger = logging.getLogger(__name__)
        
        # Quality component weights (must sum to 1.0)
        self.weights = {
            'heading_consistency': 0.4,
            'chapter_boundaries': 0.3,
            'section_organization': 0.2,
            'hierarchy_logic': 0.1
        }
    
    def assess_structure_quality(self, detection_result: DetectionResult) -> QualityAssessment:
        """
        Assess the quality of detected document structure.
        
        Args:
            detection_result: Result from StructureDetector
            
        Returns:
            QualityAssessment with detailed analysis and recommendations
        """
        self.logger.info("Assessing document structure quality for chunking strategy selection")
        
        if not detection_result or not detection_result.hierarchy:
            return self._create_poor_quality_assessment("No structure detected")
        
        hierarchy = detection_result.hierarchy
        elements = hierarchy.elements
        
        if not elements:
            return self._create_poor_quality_assessment("No structural elements found")
        
        # Calculate individual quality components
        heading_consistency = self._assess_heading_consistency(elements)
        chapter_boundary = self._assess_chapter_boundaries(elements, hierarchy)
        section_organization = self._assess_section_organization(elements, hierarchy)
        hierarchy_logic = self._assess_hierarchy_logic(elements, hierarchy)
        
        # Calculate overall quality score
        overall_quality = (
            heading_consistency * self.weights['heading_consistency'] +
            chapter_boundary * self.weights['chapter_boundaries'] +
            section_organization * self.weights['section_organization'] +
            hierarchy_logic * self.weights['hierarchy_logic']
        )
        
        # Determine recommended strategy
        strategy, confidence = self._determine_strategy(overall_quality, hierarchy)
        
        # Analyze structure characteristics
        structure_analysis = self._analyze_structure_characteristics(elements, hierarchy)
        
        # Generate warnings and suggestions
        warnings = self._generate_warnings(hierarchy, structure_analysis)
        suggestions = self._generate_improvement_suggestions(
            overall_quality, structure_analysis, hierarchy
        )
        
        self.logger.info(f"Structure quality assessment complete: {overall_quality:.2f} -> {strategy.value}")
        
        return QualityAssessment(
            overall_quality_score=overall_quality,
            recommended_strategy=strategy,
            confidence=confidence,
            heading_consistency_score=heading_consistency,
            chapter_boundary_score=chapter_boundary,
            section_organization_score=section_organization,
            hierarchy_logic_score=hierarchy_logic,
            total_structural_elements=len(elements),
            chapter_count=structure_analysis['chapter_count'],
            section_count=structure_analysis['section_count'],
            subsection_count=structure_analysis['subsection_count'],
            max_hierarchy_depth=hierarchy.max_depth,
            numbering_consistency=hierarchy.numbering_consistency,
            has_clear_chapters=structure_analysis['has_clear_chapters'],
            has_logical_hierarchy=structure_analysis['has_logical_hierarchy'],
            has_consistent_numbering=hierarchy.numbering_consistency > 0.7,
            supports_educational_chunking=overall_quality >= self.strategy_threshold,
            warnings=warnings,
            improvement_suggestions=suggestions
        )
    
    def _assess_heading_consistency(self, elements: List[StructureElement]) -> float:
        """Assess consistency of heading patterns (40% weight)"""
        if not elements:
            return 0.0
        
        # Group elements by type and level
        type_level_patterns = {}
        numbering_styles = {}
        title_patterns = {}
        
        for element in elements:
            key = (element.type, element.level)
            type_level_patterns.setdefault(key, []).append(element)
            
            # Track numbering styles
            if element.numbering_style:
                numbering_styles.setdefault(element.type, set()).add(element.numbering_style)
            
            # Track title patterns
            if element.title:
                title_patterns.setdefault(element.type, []).append(element.title)
        
        consistency_scores = []
        
        # 1. Numbering style consistency within types
        for struct_type, styles in numbering_styles.items():
            if len(styles) == 1:
                consistency_scores.append(1.0)  # Perfect consistency
            else:
                # Penalty for mixed numbering styles
                consistency_scores.append(1.0 / len(styles))
        
        # 2. Level consistency (chapters at level 0, sections at level 1, etc.)
        level_consistency = self._check_level_consistency(type_level_patterns)
        consistency_scores.append(level_consistency)
        
        # 3. Title format consistency
        title_consistency = self._check_title_format_consistency(title_patterns)
        consistency_scores.append(title_consistency)
        
        # 4. Sequential numbering consistency
        sequential_consistency = self._check_sequential_numbering(elements)
        consistency_scores.append(sequential_consistency)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
    
    def _assess_chapter_boundaries(self, elements: List[StructureElement], hierarchy) -> float:
        """Assess presence and clarity of chapter boundaries (30% weight)"""
        chapters = [e for e in elements if e.type == StructureType.CHAPTER]
        
        if not chapters:
            return 0.0
        
        boundary_scores = []
        
        # 1. Minimum chapter count
        chapter_count_score = min(1.0, len(chapters) / self.min_chapters_for_structure)
        boundary_scores.append(chapter_count_score)
        
        # 2. Chapter spacing and separation
        if len(chapters) > 1:
            spacing_score = self._assess_chapter_spacing(chapters)
            boundary_scores.append(spacing_score)
        
        # 3. Chapter title quality
        title_quality = self._assess_chapter_title_quality(chapters)
        boundary_scores.append(title_quality)
        
        # 4. Chapter length consistency
        length_consistency = self._assess_chapter_length_consistency(chapters)
        boundary_scores.append(length_consistency)
        
        return sum(boundary_scores) / len(boundary_scores)
    
    def _assess_section_organization(self, elements: List[StructureElement], hierarchy) -> float:
        """Assess section organization depth and logic (20% weight)"""
        sections = [e for e in elements if e.type == StructureType.SECTION]
        subsections = [e for e in elements if e.type == StructureType.SUBSECTION]
        chapters = [e for e in elements if e.type == StructureType.CHAPTER]
        
        if not sections and not chapters:
            return 0.3  # Base score for minimal structure
        
        organization_scores = []
        
        # 1. Section distribution across chapters
        if chapters:
            section_distribution = self._assess_section_distribution(chapters, sections)
            organization_scores.append(section_distribution)
        
        # 2. Hierarchical depth appropriateness
        depth_score = self._assess_hierarchical_depth(hierarchy.max_depth)
        organization_scores.append(depth_score)
        
        # 3. Section-to-subsection ratio
        if sections:
            subsection_ratio = self._assess_subsection_ratio(sections, subsections)
            organization_scores.append(subsection_ratio)
        
        # 4. Section length and balance
        section_balance = self._assess_section_balance(sections)
        organization_scores.append(section_balance)
        
        return sum(organization_scores) / len(organization_scores) if organization_scores else 0.3
    
    def _assess_hierarchy_logic(self, elements: List[StructureElement], hierarchy) -> float:
        """Assess content hierarchy logic (10% weight)"""
        if not elements:
            return 0.0
        
        logic_scores = []
        
        # 1. Proper nesting (chapters contain sections, sections contain subsections)
        nesting_score = self._check_proper_nesting(elements)
        logic_scores.append(nesting_score)
        
        # 2. No orphaned elements (sections without chapters, etc.)
        orphan_score = self._check_orphaned_elements(elements)
        logic_scores.append(orphan_score)
        
        # 3. Logical progression (increasing numbers/letters)
        progression_score = self._check_logical_progression(elements)
        logic_scores.append(progression_score)
        
        # 4. Consistent hierarchy levels
        level_logic = self._check_hierarchy_level_logic(elements)
        logic_scores.append(level_logic)
        
        return sum(logic_scores) / len(logic_scores)
    
    def _check_level_consistency(self, type_level_patterns: Dict) -> float:
        """Check if element types consistently use appropriate levels"""
        expected_levels = {
            StructureType.CHAPTER: 0,
            StructureType.SECTION: 1,
            StructureType.SUBSECTION: 2
        }
        
        violations = 0
        total_checks = 0
        
        for (struct_type, level), elements in type_level_patterns.items():
            if struct_type in expected_levels:
                expected_level = expected_levels[struct_type]
                total_checks += 1
                if level != expected_level:
                    violations += 1
        
        return 1.0 - (violations / total_checks) if total_checks > 0 else 1.0
    
    def _check_title_format_consistency(self, title_patterns: Dict) -> float:
        """Check consistency of title formatting patterns"""
        consistency_scores = []
        
        for struct_type, titles in title_patterns.items():
            if len(titles) < 2:
                consistency_scores.append(1.0)
                continue
            
            # Check for common patterns in titles
            patterns = {
                'starts_with_number': sum(1 for t in titles if re.match(r'^\d', t)),
                'contains_colon': sum(1 for t in titles if ':' in t),
                'all_caps': sum(1 for t in titles if t.isupper()),
                'title_case': sum(1 for t in titles if t.istitle())
            }
            
            # Calculate consistency as the maximum pattern adherence
            max_pattern_score = max(patterns.values()) / len(titles)
            consistency_scores.append(max_pattern_score)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.5
    
    def _check_sequential_numbering(self, elements: List[StructureElement]) -> float:
        """Check if numbering follows sequential patterns"""
        # Group by type and level
        grouped = {}
        for element in elements:
            key = (element.type, element.level)
            grouped.setdefault(key, []).append(element)
        
        sequential_scores = []
        
        for (struct_type, level), group in grouped.items():
            if len(group) < 2:
                sequential_scores.append(1.0)
                continue
            
            # Sort by position and check for sequential numbering
            sorted_group = sorted(group, key=lambda x: x.start_position)
            numbers = []
            
            for element in sorted_group:
                if element.number:
                    # Extract numeric part
                    numeric_match = re.search(r'(\d+)', element.number)
                    if numeric_match:
                        numbers.append(int(numeric_match.group(1)))
            
            if len(numbers) < 2:
                sequential_scores.append(0.5)
                continue
            
            # Check if sequence is mostly sequential
            sequential_count = 0
            for i in range(len(numbers) - 1):
                if numbers[i + 1] == numbers[i] + 1:
                    sequential_count += 1
            
            sequence_score = sequential_count / (len(numbers) - 1) if len(numbers) > 1 else 1.0
            sequential_scores.append(sequence_score)
        
        return sum(sequential_scores) / len(sequential_scores) if sequential_scores else 0.5
    
    def _assess_chapter_spacing(self, chapters: List[StructureElement]) -> float:
        """Assess spacing and separation between chapters"""
        if len(chapters) < 2:
            return 1.0
        
        sorted_chapters = sorted(chapters, key=lambda x: x.start_position)
        spacings = []
        
        for i in range(len(sorted_chapters) - 1):
            current_end = sorted_chapters[i].end_position or sorted_chapters[i].start_position
            next_start = sorted_chapters[i + 1].start_position
            spacing = next_start - current_end
            spacings.append(spacing)
        
        if not spacings:
            return 0.5
        
        # Good spacing is relatively consistent and substantial
        avg_spacing = sum(spacings) / len(spacings)
        spacing_variance = sum((s - avg_spacing) ** 2 for s in spacings) / len(spacings)
        
        # Score based on consistency and adequacy of spacing
        consistency_score = 1.0 / (1.0 + spacing_variance / max(1, avg_spacing))
        adequacy_score = min(1.0, avg_spacing / 100)  # Assume 100 chars is good spacing
        
        return (consistency_score + adequacy_score) / 2
    
    def _assess_chapter_title_quality(self, chapters: List[StructureElement]) -> float:
        """Assess quality of chapter titles"""
        if not chapters:
            return 0.0
        
        quality_scores = []
        
        for chapter in chapters:
            if not chapter.title:
                quality_scores.append(0.0)
                continue
            
            title = chapter.title.strip()
            score = 0.5  # Base score
            
            # Bonus for descriptive length
            if 5 <= len(title.split()) <= 10:
                score += 0.2
            
            # Bonus for proper capitalization
            if title.istitle() or title.isupper():
                score += 0.15
            
            # Bonus for containing educational keywords
            educational_keywords = ['introduction', 'overview', 'fundamentals', 'advanced', 
                                   'principles', 'concepts', 'theory', 'practice', 'applications']
            if any(keyword in title.lower() for keyword in educational_keywords):
                score += 0.15
            
            quality_scores.append(min(1.0, score))
        
        return sum(quality_scores) / len(quality_scores)
    
    def _assess_chapter_length_consistency(self, chapters: List[StructureElement]) -> float:
        """Assess consistency of chapter lengths"""
        if len(chapters) < 2:
            return 1.0
        
        lengths = []
        for chapter in chapters:
            if chapter.end_position:
                length = chapter.end_position - chapter.start_position
                lengths.append(length)
        
        if len(lengths) < 2:
            return 0.5
        
        # Calculate coefficient of variation
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        std_dev = variance ** 0.5
        
        cv = std_dev / avg_length if avg_length > 0 else 0
        
        # Score inversely related to coefficient of variation
        # CV < 0.3 is good, CV > 1.0 is poor
        return max(0.0, 1.0 - cv / 0.7)
    
    def _assess_section_distribution(self, chapters: List[StructureElement], 
                                   sections: List[StructureElement]) -> float:
        """Assess how well sections are distributed across chapters"""
        if not chapters or not sections:
            return 0.5
        
        # Count sections per chapter
        chapter_sections = {ch.start_position: 0 for ch in chapters}
        sorted_chapters = sorted(chapters, key=lambda x: x.start_position)
        
        for section in sections:
            # Find which chapter this section belongs to
            for i, chapter in enumerate(sorted_chapters):
                chapter_end = (sorted_chapters[i + 1].start_position 
                              if i + 1 < len(sorted_chapters) 
                              else float('inf'))
                
                if chapter.start_position <= section.start_position < chapter_end:
                    chapter_sections[chapter.start_position] += 1
                    break
        
        section_counts = list(chapter_sections.values())
        
        if not section_counts or max(section_counts) == 0:
            return 0.2
        
        # Good distribution: most chapters have 1-5 sections
        good_range_count = sum(1 for count in section_counts if 1 <= count <= 5)
        distribution_score = good_range_count / len(section_counts)
        
        # Penalty for chapters with too many sections
        excessive_sections = sum(1 for count in section_counts if count > self.max_sections_per_chapter)
        penalty = excessive_sections / len(section_counts) * 0.5
        
        return max(0.0, distribution_score - penalty)
    
    def _assess_hierarchical_depth(self, max_depth: int) -> float:
        """Assess appropriateness of hierarchical depth"""
        # Ideal depth for educational content is 2-3 levels
        if max_depth == 0:
            return 0.2
        elif max_depth == 1:
            return 0.6
        elif 2 <= max_depth <= 3:
            return 1.0
        elif max_depth == 4:
            return 0.8
        else:
            return 0.5  # Too deep can be confusing
    
    def _assess_subsection_ratio(self, sections: List[StructureElement], 
                                subsections: List[StructureElement]) -> float:
        """Assess ratio of subsections to sections"""
        if not sections:
            return 0.5
        
        ratio = len(subsections) / len(sections)
        
        # Ideal ratio is 0.5 to 3.0 (some sections have subsections, but not excessive)
        if 0.5 <= ratio <= 3.0:
            return 1.0
        elif ratio < 0.5:
            return 0.7  # Few subsections is okay
        else:
            return max(0.0, 1.0 - (ratio - 3.0) / 5.0)  # Too many subsections
    
    def _assess_section_balance(self, sections: List[StructureElement]) -> float:
        """Assess balance in section lengths"""
        if len(sections) < 2:
            return 1.0
        
        lengths = []
        for section in sections:
            if section.end_position:
                length = section.end_position - section.start_position
                if length > 0:
                    lengths.append(length)
        
        if len(lengths) < 2:
            return 0.5
        
        # Calculate balance using coefficient of variation
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        std_dev = variance ** 0.5
        
        cv = std_dev / avg_length if avg_length > 0 else 0
        
        # Reasonable variation is expected, penalize excessive variation
        return max(0.0, 1.0 - max(0, cv - 0.5) / 0.8)
    
    def _check_proper_nesting(self, elements: List[StructureElement]) -> float:
        """Check if elements are properly nested hierarchically"""
        # Sort elements by position
        sorted_elements = sorted(elements, key=lambda x: x.start_position)
        
        nesting_violations = 0
        total_checks = 0
        
        for i, element in enumerate(sorted_elements):
            if element.type == StructureType.SECTION:
                # Check if there's a chapter before this section
                found_chapter = False
                for j in range(i - 1, -1, -1):
                    if sorted_elements[j].type == StructureType.CHAPTER:
                        found_chapter = True
                        break
                    elif sorted_elements[j].type == StructureType.SECTION:
                        break  # Another section, stop looking
                
                total_checks += 1
                if not found_chapter:
                    nesting_violations += 1
            
            elif element.type == StructureType.SUBSECTION:
                # Check if there's a section before this subsection
                found_section = False
                for j in range(i - 1, -1, -1):
                    if sorted_elements[j].type == StructureType.SECTION:
                        found_section = True
                        break
                    elif sorted_elements[j].type == StructureType.SUBSECTION:
                        break  # Another subsection, stop looking
                
                total_checks += 1
                if not found_section:
                    nesting_violations += 1
        
        return 1.0 - (nesting_violations / total_checks) if total_checks > 0 else 1.0
    
    def _check_orphaned_elements(self, elements: List[StructureElement]) -> float:
        """Check for orphaned structural elements"""
        chapters = [e for e in elements if e.type == StructureType.CHAPTER]
        sections = [e for e in elements if e.type == StructureType.SECTION]
        subsections = [e for e in elements if e.type == StructureType.SUBSECTION]
        
        orphan_penalty = 0.0
        
        # Sections without chapters
        if sections and not chapters:
            orphan_penalty += 0.3
        
        # Subsections without sections
        if subsections and not sections:
            orphan_penalty += 0.4
        
        return max(0.0, 1.0 - orphan_penalty)
    
    def _check_logical_progression(self, elements: List[StructureElement]) -> float:
        """Check for logical progression in numbering"""
        # Group by type
        by_type = {}
        for element in elements:
            by_type.setdefault(element.type, []).append(element)
        
        progression_scores = []
        
        for struct_type, type_elements in by_type.items():
            if len(type_elements) < 2:
                progression_scores.append(1.0)
                continue
            
            # Sort by position
            sorted_elements = sorted(type_elements, key=lambda x: x.start_position)
            
            # Extract numbers and check progression
            numbers = []
            for element in sorted_elements:
                if element.number:
                    numeric_match = re.search(r'(\d+)', element.number)
                    if numeric_match:
                        numbers.append(int(numeric_match.group(1)))
            
            if len(numbers) < 2:
                progression_scores.append(0.5)
                continue
            
            # Check for mostly increasing sequence
            increasing_count = 0
            for i in range(len(numbers) - 1):
                if numbers[i + 1] > numbers[i]:
                    increasing_count += 1
            
            progression_score = increasing_count / (len(numbers) - 1) if len(numbers) > 1 else 1.0
            progression_scores.append(progression_score)
        
        return sum(progression_scores) / len(progression_scores) if progression_scores else 0.5
    
    def _check_hierarchy_level_logic(self, elements: List[StructureElement]) -> float:
        """Check if hierarchy levels make logical sense"""
        level_violations = 0
        total_transitions = 0
        
        sorted_elements = sorted(elements, key=lambda x: x.start_position)
        
        for i in range(len(sorted_elements) - 1):
            current = sorted_elements[i]
            next_elem = sorted_elements[i + 1]
            
            total_transitions += 1
            
            # Level should not increase by more than 1
            if next_elem.level > current.level + 1:
                level_violations += 1
        
        return 1.0 - (level_violations / total_transitions) if total_transitions > 0 else 1.0
    
    def _determine_strategy(self, quality_score: float, hierarchy) -> Tuple[ChunkingStrategy, float]:
        """Determine recommended chunking strategy and confidence"""
        
        # Primary decision based on quality threshold
        if quality_score >= self.strategy_threshold:
            strategy = ChunkingStrategy.CONTENT_AWARE
            # Confidence increases with quality above threshold
            confidence = min(1.0, 0.7 + (quality_score - self.strategy_threshold) * 0.3 / (1.0 - self.strategy_threshold))
        else:
            strategy = ChunkingStrategy.FALLBACK
            # Confidence decreases as quality gets worse
            confidence = min(1.0, 0.8 - (self.strategy_threshold - quality_score) * 0.5 / self.strategy_threshold)
        
        # Adjust confidence based on additional factors
        if hierarchy.total_chapters < self.min_chapters_for_structure:
            confidence *= 0.8
        
        if hierarchy.numbering_consistency < 0.5:
            confidence *= 0.9
        
        # Consider hybrid approach for borderline cases
        if abs(quality_score - self.strategy_threshold) < 0.1:
            strategy = ChunkingStrategy.HYBRID
            confidence = min(confidence, 0.7)  # Lower confidence for hybrid
        
        return strategy, max(0.1, confidence)  # Minimum confidence of 0.1
    
    def _analyze_structure_characteristics(self, elements: List[StructureElement], hierarchy) -> Dict[str, Any]:
        """Analyze structural characteristics for detailed assessment"""
        chapters = [e for e in elements if e.type == StructureType.CHAPTER]
        sections = [e for e in elements if e.type == StructureType.SECTION]
        subsections = [e for e in elements if e.type == StructureType.SUBSECTION]
        
        return {
            'chapter_count': len(chapters),
            'section_count': len(sections),
            'subsection_count': len(subsections),
            'has_clear_chapters': len(chapters) >= self.min_chapters_for_structure,
            'has_logical_hierarchy': hierarchy.max_depth >= 1 and len(chapters) > 0,
            'average_sections_per_chapter': len(sections) / max(1, len(chapters)),
            'hierarchy_depth_appropriate': 1 <= hierarchy.max_depth <= 3,
            'numbering_consistent': hierarchy.numbering_consistency > 0.7
        }
    
    def _generate_warnings(self, hierarchy, structure_analysis: Dict) -> List[str]:
        """Generate warnings about structure quality issues"""
        warnings = []
        
        if structure_analysis['chapter_count'] < self.min_chapters_for_structure:
            warnings.append(f"Document has only {structure_analysis['chapter_count']} chapters, "
                           f"minimum {self.min_chapters_for_structure} recommended for structured chunking")
        
        if hierarchy.numbering_consistency < 0.5:
            warnings.append(f"Inconsistent numbering detected (consistency: {hierarchy.numbering_consistency:.2f})")
        
        if structure_analysis['average_sections_per_chapter'] > self.max_sections_per_chapter:
            warnings.append(f"High section density detected "
                           f"({structure_analysis['average_sections_per_chapter']:.1f} sections per chapter)")
        
        if hierarchy.max_depth > 4:
            warnings.append(f"Deep hierarchy detected ({hierarchy.max_depth} levels), "
                           "may complicate chunking")
        
        if hierarchy.max_depth == 0:
            warnings.append("Flat structure detected - no hierarchical organization found")
        
        return warnings
    
    def _generate_improvement_suggestions(self, quality_score: float, 
                                        structure_analysis: Dict, hierarchy) -> List[str]:
        """Generate suggestions for improving structure quality"""
        suggestions = []
        
        if quality_score < self.strategy_threshold:
            suggestions.append("Consider manual structure review to improve chunking quality")
        
        if structure_analysis['chapter_count'] == 0:
            suggestions.append("Add chapter markers to enable structure-aware chunking")
        
        if hierarchy.numbering_consistency < 0.7:
            suggestions.append("Standardize numbering format across sections and chapters")
        
        if structure_analysis['average_sections_per_chapter'] < 1:
            suggestions.append("Consider adding section divisions within chapters")
        
        if not structure_analysis['has_logical_hierarchy']:
            suggestions.append("Establish clear hierarchical organization (chapters > sections > subsections)")
        
        if quality_score < 0.5:
            suggestions.append("Document may benefit from restructuring before processing")
        
        return suggestions
    
    def _create_poor_quality_assessment(self, reason: str) -> QualityAssessment:
        """Create assessment result for poor quality structures"""
        return QualityAssessment(
            overall_quality_score=0.0,
            recommended_strategy=ChunkingStrategy.FALLBACK,
            confidence=0.9,  # High confidence in fallback recommendation
            heading_consistency_score=0.0,
            chapter_boundary_score=0.0,
            section_organization_score=0.0,
            hierarchy_logic_score=0.0,
            total_structural_elements=0,
            chapter_count=0,
            section_count=0,
            subsection_count=0,
            max_hierarchy_depth=0,
            numbering_consistency=0.0,
            has_clear_chapters=False,
            has_logical_hierarchy=False,
            has_consistent_numbering=False,
            supports_educational_chunking=False,
            warnings=[reason],
            improvement_suggestions=["Improve document structure before processing"]
        )