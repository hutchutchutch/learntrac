"""
StructureDetector for Chapter and Section Recognition

Implements intelligent document structure detection using regex patterns to identify
chapters, sections, and hierarchical content organization with confidence scoring.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class StructureType(Enum):
    """Types of document structure elements"""
    CHAPTER = "chapter"
    SECTION = "section" 
    SUBSECTION = "subsection"
    SUBSUBSECTION = "subsubsection"
    HEADING = "heading"
    UNKNOWN = "unknown"


class NumberingStyle(Enum):
    """Different numbering styles found in documents"""
    ARABIC = "1, 2, 3"  # 1, 2, 3
    ROMAN_UPPER = "I, II, III"  # I, II, III
    ROMAN_LOWER = "i, ii, iii"  # i, ii, iii
    LETTER_UPPER = "A, B, C"  # A, B, C
    LETTER_LOWER = "a, b, c"  # a, b, c
    DECIMAL = "1.1, 1.2"  # 1.1, 1.2, 1.3
    NONE = "no numbering"


@dataclass
class StructureElement:
    """Represents a detected structure element"""
    type: StructureType
    title: str
    number: Optional[str]
    level: int  # 0=chapter, 1=section, 2=subsection, etc.
    start_position: int
    end_position: Optional[int]
    page_number: Optional[int]
    confidence: float
    numbering_style: NumberingStyle
    raw_text: str


@dataclass
class StructureHierarchy:
    """Complete document structure hierarchy"""
    elements: List[StructureElement]
    total_chapters: int
    total_sections: int  
    max_depth: int
    numbering_consistency: float
    overall_confidence: float
    quality_score: float


@dataclass
class DetectionResult:
    """Result from structure detection"""
    hierarchy: StructureHierarchy
    is_valid_textbook: bool
    warnings: List[str]
    statistics: Dict[str, Any]


class StructureDetector:
    """
    Advanced document structure detection system.
    
    Features:
    - Multi-format chapter detection (Chapter, CHAPTER, Ch., Unit, etc.)
    - Hierarchical section detection (1.1, 1.1.1, etc.)
    - Multiple numbering style support (Arabic, Roman, letters)
    - Confidence scoring based on pattern consistency
    - Quality assessment for textbook validation
    - Position and page tracking
    """
    
    def __init__(self, min_chapters: int = 3, confidence_threshold: float = 0.3):
        """
        Initialize StructureDetector.
        
        Args:
            min_chapters: Minimum chapters required for valid textbook
            confidence_threshold: Minimum confidence for valid structure
        """
        self.min_chapters = min_chapters
        self.confidence_threshold = confidence_threshold
        self.logger = logging.getLogger(__name__)
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile all regex patterns for structure detection"""
        
        # Chapter patterns with various formats
        self.chapter_patterns = {
            'standard': re.compile(
                r'^(?:Chapter|CHAPTER|Ch\.?)\s*(\d+)(?:\s*[:.\-]\s*(.+?))?$',
                re.MULTILINE | re.IGNORECASE
            ),
            'unit': re.compile(
                r'^(?:Unit|UNIT)\s+(\d+)(?:\s*[:.\-]\s*(.+?))?$',
                re.MULTILINE | re.IGNORECASE
            ),
            'part': re.compile(
                r'^(?:Part|PART)\s+([IVXLCDM]+|\d+)(?:\s*[:.\-]\s*(.+?))?$',
                re.MULTILINE | re.IGNORECASE
            ),
            'numbered_simple': re.compile(
                r'^(\d+)\s*[:.\-]\s*(.+?)$',
                re.MULTILINE
            ),
            'roman_numbered': re.compile(
                r'^([IVXLCDM]+)\.\s*(.+?)$',
                re.MULTILINE
            ),
            'lesson': re.compile(
                r'^(?:Lesson|LESSON)\s+(\d+)(?:\s*[:.\-]\s*(.+?))?$',
                re.MULTILINE | re.IGNORECASE
            ),
            'module': re.compile(
                r'^(?:Module|MODULE)\s+(\d+)(?:\s*[:.\-]\s*(.+?))?$',
                re.MULTILINE | re.IGNORECASE
            )
        }
        
        # Section patterns for hierarchical detection
        self.section_patterns = {
            'decimal': re.compile(
                r'^(\d+\.\d+)(?:\.\d+)*\s+(.+?)$',
                re.MULTILINE
            ),
            'letter_section': re.compile(
                r'^([A-Z])\.\s*(.+?)$',
                re.MULTILINE
            ),
            'numbered_section': re.compile(
                r'^(\d+\.\d+)\s+(.+?)$',
                re.MULTILINE
            ),
            'subsection': re.compile(
                r'^(\d+\.\d+\.\d+)\s+(.+?)$',
                re.MULTILINE
            ),
            'roman_section': re.compile(
                r'^([ivxlcdm]+)\.\s*(.+?)$',
                re.MULTILINE
            )
        }
        
        # General heading patterns
        self.heading_patterns = {
            'title_case': re.compile(
                r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*$',
                re.MULTILINE
            ),
            'all_caps': re.compile(
                r'^([A-Z\s]{4,})\s*$',
                re.MULTILINE
            ),
            'bold_indicators': re.compile(
                r'\*\*(.+?)\*\*|\*(.+?)\*',
                re.MULTILINE
            )
        }
    
    def detect_structure(self, text: str) -> DetectionResult:
        """
        Detect document structure from text.
        
        Args:
            text: Full document text
            
        Returns:
            DetectionResult with detected hierarchy and quality metrics
        """
        if not text or not text.strip():
            return DetectionResult(
                hierarchy=StructureHierarchy([], 0, 0, 0, 0.0, 0.0, 0.0),
                is_valid_textbook=False,
                warnings=["Empty text provided"],
                statistics={}
            )
        
        self.logger.info("Starting document structure detection")
        
        # Detect all structure elements
        elements = self._detect_all_elements(text)
        
        # Sort by position and assign hierarchy
        elements.sort(key=lambda x: x.start_position)
        
        # Calculate levels and relationships
        self._assign_hierarchy_levels(elements)
        
        # Calculate confidence and quality metrics
        hierarchy = self._build_hierarchy(elements, text)
        
        # Validate textbook structure
        is_valid, warnings = self._validate_textbook_structure(hierarchy)
        
        # Generate statistics
        statistics = self._generate_statistics(elements, text)
        
        self.logger.info(f"Structure detection completed. Found {hierarchy.total_chapters} chapters, {hierarchy.total_sections} sections")
        
        return DetectionResult(
            hierarchy=hierarchy,
            is_valid_textbook=is_valid,
            warnings=warnings,
            statistics=statistics
        )
    
    def _detect_all_elements(self, text: str) -> List[StructureElement]:
        """Detect all structure elements from text"""
        elements = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 2:
                continue
            
            position = sum(len(lines[i]) + 1 for i in range(line_num))
            
            # Try to detect chapters first (highest priority)
            chapter_element = self._detect_chapter(line, position, line_num)
            if chapter_element:
                elements.append(chapter_element)
                continue
            
            # Try to detect sections
            section_element = self._detect_section(line, position, line_num)
            if section_element:
                elements.append(section_element)
                continue
            
            # Try to detect general headings
            heading_element = self._detect_heading(line, position, line_num)
            if heading_element:
                elements.append(heading_element)
        
        return elements
    
    def _detect_chapter(self, line: str, position: int, line_num: int) -> Optional[StructureElement]:
        """Detect chapter-level elements"""
        for pattern_name, pattern in self.chapter_patterns.items():
            match = pattern.match(line)
            if match:
                number = match.group(1) if match.groups() else None
                title = match.group(2) if len(match.groups()) > 1 and match.group(2) else line
                
                # Calculate confidence based on pattern type and context
                confidence = self._calculate_chapter_confidence(pattern_name, line, number)
                
                # Determine numbering style
                numbering_style = self._determine_numbering_style(number)
                
                return StructureElement(
                    type=StructureType.CHAPTER,
                    title=title.strip() if title else line,
                    number=number,
                    level=0,
                    start_position=position,
                    end_position=None,
                    page_number=None,  # Would need page mapping
                    confidence=confidence,
                    numbering_style=numbering_style,
                    raw_text=line
                )
        
        return None
    
    def _detect_section(self, line: str, position: int, line_num: int) -> Optional[StructureElement]:
        """Detect section-level elements"""
        for pattern_name, pattern in self.section_patterns.items():
            match = pattern.match(line)
            if match:
                number = match.group(1)
                title = match.group(2) if len(match.groups()) > 1 else line
                
                # Determine section level based on numbering
                level = self._calculate_section_level(number, pattern_name)
                
                # Calculate confidence
                confidence = self._calculate_section_confidence(pattern_name, line, number)
                
                # Determine structure type based on level
                if level == 1:
                    struct_type = StructureType.SECTION
                elif level == 2:
                    struct_type = StructureType.SUBSECTION
                elif level == 3:
                    struct_type = StructureType.SUBSUBSECTION
                else:
                    struct_type = StructureType.SECTION
                
                numbering_style = self._determine_numbering_style(number)
                
                return StructureElement(
                    type=struct_type,
                    title=title.strip(),
                    number=number,
                    level=level,
                    start_position=position,
                    end_position=None,
                    page_number=None,
                    confidence=confidence,
                    numbering_style=numbering_style,
                    raw_text=line
                )
        
        return None
    
    def _detect_heading(self, line: str, position: int, line_num: int) -> Optional[StructureElement]:
        """Detect general heading elements"""
        # Skip very short or very long lines
        if len(line) < 3 or len(line) > 200:
            return None
        
        # Check various heading patterns
        for pattern_name, pattern in self.heading_patterns.items():
            match = pattern.match(line)
            if match:
                confidence = self._calculate_heading_confidence(pattern_name, line)
                
                # Only accept headings with reasonable confidence
                if confidence < 0.3:
                    continue
                
                return StructureElement(
                    type=StructureType.HEADING,
                    title=line.strip(),
                    number=None,
                    level=2,  # Default level for general headings
                    start_position=position,
                    end_position=None,
                    page_number=None,
                    confidence=confidence,
                    numbering_style=NumberingStyle.NONE,
                    raw_text=line
                )
        
        return None
    
    def _assign_hierarchy_levels(self, elements: List[StructureElement]) -> None:
        """Assign proper hierarchy levels to elements"""
        current_chapter_level = 0
        
        for element in elements:
            if element.type == StructureType.CHAPTER:
                current_chapter_level = element.level = 0
            elif element.type in [StructureType.SECTION, StructureType.SUBSECTION, StructureType.SUBSUBSECTION]:
                # Keep existing calculated level, but ensure it's relative to chapters
                if element.level <= current_chapter_level:
                    element.level = current_chapter_level + 1
            elif element.type == StructureType.HEADING:
                # Place headings at appropriate level
                if current_chapter_level >= 0:
                    element.level = max(1, current_chapter_level + 1)
    
    def _calculate_chapter_confidence(self, pattern_name: str, line: str, number: str) -> float:
        """Calculate confidence score for chapter detection"""
        base_confidence = {
            'standard': 0.9,
            'unit': 0.85,
            'part': 0.8,
            'numbered_simple': 0.6,
            'roman_numbered': 0.7,
            'lesson': 0.75,
            'module': 0.75
        }.get(pattern_name, 0.5)
        
        # Adjust based on context
        if number and number.isdigit():
            base_confidence += 0.05
        
        # Penalize very short or very long titles
        title_length = len(line)
        if title_length < 5:
            base_confidence -= 0.2
        elif title_length > 100:
            base_confidence -= 0.1
        
        # Bonus for common chapter indicators
        if any(word in line.lower() for word in ['introduction', 'overview', 'conclusion', 'summary']):
            base_confidence += 0.05
        
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_section_confidence(self, pattern_name: str, line: str, number: str) -> float:
        """Calculate confidence score for section detection"""
        base_confidence = {
            'decimal': 0.85,
            'numbered_section': 0.8,
            'subsection': 0.9,
            'letter_section': 0.7,
            'roman_section': 0.65
        }.get(pattern_name, 0.5)
        
        # Bonus for proper decimal numbering
        if '.' in number and all(part.isdigit() for part in number.split('.')):
            base_confidence += 0.05
        
        # Penalty for very short titles
        if len(line.split()) < 2:
            base_confidence -= 0.15
        
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_heading_confidence(self, pattern_name: str, line: str) -> float:
        """Calculate confidence score for heading detection"""
        base_confidence = {
            'title_case': 0.6,
            'all_caps': 0.5,
            'bold_indicators': 0.7
        }.get(pattern_name, 0.3)
        
        # Adjust based on length and content
        word_count = len(line.split())
        if 2 <= word_count <= 10:
            base_confidence += 0.1
        elif word_count > 20:
            base_confidence -= 0.2
        
        # Bonus for title-like words
        title_words = ['introduction', 'overview', 'definition', 'example', 'exercise', 'summary', 'conclusion']
        if any(word in line.lower() for word in title_words):
            base_confidence += 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_section_level(self, number: str, pattern_name: str) -> int:
        """Calculate hierarchical level for sections"""
        if pattern_name == 'decimal':
            # Count dots to determine depth (1.1 = level 1, 1.1.1 = level 2)
            return number.count('.')
        elif pattern_name == 'subsection':
            return 2  # Explicitly subsection
        elif pattern_name in ['numbered_section', 'letter_section']:
            return 1
        else:
            return 1  # Default section level
    
    def _determine_numbering_style(self, number: Optional[str]) -> NumberingStyle:
        """Determine the numbering style used"""
        if not number:
            return NumberingStyle.NONE
        
        if re.match(r'^\d+$', number):
            return NumberingStyle.ARABIC
        elif re.match(r'^[IVXLCDM]+$', number):
            return NumberingStyle.ROMAN_UPPER
        elif re.match(r'^[ivxlcdm]+$', number):
            return NumberingStyle.ROMAN_LOWER
        elif re.match(r'^[A-Z]$', number):
            return NumberingStyle.LETTER_UPPER
        elif re.match(r'^[a-z]$', number):
            return NumberingStyle.LETTER_LOWER
        elif '.' in number:
            return NumberingStyle.DECIMAL
        else:
            return NumberingStyle.ARABIC  # Default assumption
    
    def _build_hierarchy(self, elements: List[StructureElement], text: str) -> StructureHierarchy:
        """Build complete hierarchy structure with metrics"""
        chapters = [e for e in elements if e.type == StructureType.CHAPTER]
        sections = [e for e in elements if e.type in [StructureType.SECTION, StructureType.SUBSECTION, StructureType.SUBSUBSECTION]]
        
        # Calculate end positions
        for i, element in enumerate(elements):
            if i < len(elements) - 1:
                element.end_position = elements[i + 1].start_position
            else:
                element.end_position = len(text)
        
        # Calculate metrics
        max_depth = max((e.level for e in elements), default=0)
        numbering_consistency = self._calculate_numbering_consistency(elements)
        overall_confidence = sum(e.confidence for e in elements) / len(elements) if elements else 0.0
        quality_score = self._calculate_structure_quality(elements, numbering_consistency)
        
        return StructureHierarchy(
            elements=elements,
            total_chapters=len(chapters),
            total_sections=len(sections),
            max_depth=max_depth,
            numbering_consistency=numbering_consistency,
            overall_confidence=overall_confidence,
            quality_score=quality_score
        )
    
    def _calculate_numbering_consistency(self, elements: List[StructureElement]) -> float:
        """Calculate how consistent the numbering scheme is"""
        if not elements:
            return 0.0
        
        # Group by type and level
        level_groups = {}
        for element in elements:
            key = (element.type, element.level)
            if key not in level_groups:
                level_groups[key] = []
            level_groups[key].append(element)
        
        consistency_scores = []
        
        for group in level_groups.values():
            if len(group) < 2:
                continue
            
            # Check numbering style consistency
            styles = [e.numbering_style for e in group if e.number]
            if styles:
                most_common_style = max(set(styles), key=styles.count)
                style_consistency = styles.count(most_common_style) / len(styles)
                consistency_scores.append(style_consistency)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.5
    
    def _calculate_structure_quality(self, elements: List[StructureElement], numbering_consistency: float) -> float:
        """Calculate overall structure quality score"""
        if not elements:
            return 0.0
        
        # Base score from average confidence
        avg_confidence = sum(e.confidence for e in elements) / len(elements)
        quality = avg_confidence * 0.6
        
        # Bonus for numbering consistency
        quality += numbering_consistency * 0.2
        
        # Bonus for having good hierarchy
        chapters = sum(1 for e in elements if e.type == StructureType.CHAPTER)
        sections = sum(1 for e in elements if e.type != StructureType.CHAPTER)
        
        if chapters >= self.min_chapters:
            quality += 0.1
        
        if sections > 0 and chapters > 0:
            section_to_chapter_ratio = sections / chapters
            if 1 <= section_to_chapter_ratio <= 10:  # Reasonable ratio
                quality += 0.1
        
        return max(0.0, min(1.0, quality))
    
    def _validate_textbook_structure(self, hierarchy: StructureHierarchy) -> Tuple[bool, List[str]]:
        """Validate if structure represents a valid textbook"""
        warnings = []
        is_valid = True
        
        # Check minimum chapters
        if hierarchy.total_chapters < self.min_chapters:
            warnings.append(f"Insufficient chapters: {hierarchy.total_chapters} < {self.min_chapters}")
            is_valid = False
        
        # Check overall quality
        if hierarchy.quality_score < self.confidence_threshold:
            warnings.append(f"Low structure quality: {hierarchy.quality_score:.2f} < {self.confidence_threshold}")
            is_valid = False
        
        # Check for reasonable section distribution
        if hierarchy.total_chapters > 0:
            avg_sections_per_chapter = hierarchy.total_sections / hierarchy.total_chapters
            if avg_sections_per_chapter < 0.5:
                warnings.append("Very few sections per chapter - may indicate poor structure detection")
            elif avg_sections_per_chapter > 20:
                warnings.append("Too many sections per chapter - may indicate over-detection")
        
        # Check numbering consistency
        if hierarchy.numbering_consistency < 0.5:
            warnings.append("Inconsistent numbering scheme detected")
        
        return is_valid, warnings
    
    def _generate_statistics(self, elements: List[StructureElement], text: str) -> Dict[str, Any]:
        """Generate detailed statistics about structure detection"""
        stats = {
            'total_elements': len(elements),
            'element_types': {},
            'numbering_styles': {},
            'confidence_distribution': {
                'high': 0,  # > 0.8
                'medium': 0,  # 0.5 - 0.8
                'low': 0  # < 0.5
            },
            'text_coverage': 0.0,
            'average_element_length': 0
        }
        
        # Count element types
        for element in elements:
            type_name = element.type.value
            stats['element_types'][type_name] = stats['element_types'].get(type_name, 0) + 1
            
            # Count numbering styles
            style_name = element.numbering_style.value
            stats['numbering_styles'][style_name] = stats['numbering_styles'].get(style_name, 0) + 1
            
            # Confidence distribution
            if element.confidence > 0.8:
                stats['confidence_distribution']['high'] += 1
            elif element.confidence > 0.5:
                stats['confidence_distribution']['medium'] += 1
            else:
                stats['confidence_distribution']['low'] += 1
        
        # Calculate text coverage
        if elements and text:
            covered_chars = sum(
                (element.end_position or len(text)) - element.start_position 
                for element in elements
            )
            stats['text_coverage'] = min(1.0, covered_chars / len(text))
            
            # Average element length
            element_lengths = [
                (element.end_position or len(text)) - element.start_position 
                for element in elements
            ]
            stats['average_element_length'] = sum(element_lengths) / len(element_lengths) if element_lengths else 0
        
        return stats