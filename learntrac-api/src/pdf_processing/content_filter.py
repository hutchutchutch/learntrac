"""
ContentFilter for Prefatory and Appendix Removal

Implements intelligent content filtering to remove non-essential content like
table of contents, copyright pages, and appendix material while preserving
core educational content.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum

from .structure_detector import StructureDetector, StructureElement, StructureType


class ContentType(Enum):
    """Types of content sections"""
    CORE_CONTENT = "core_content"
    PREFATORY = "prefatory"
    APPENDIX = "appendix"
    TABLE_OF_CONTENTS = "table_of_contents"
    COPYRIGHT = "copyright"
    ACKNOWLEDGMENTS = "acknowledgments"
    BIBLIOGRAPHY = "bibliography"
    INDEX = "index"
    GLOSSARY = "glossary"
    UNKNOWN = "unknown"


@dataclass
class ContentSection:
    """Represents a section of content with classification"""
    start_position: int
    end_position: int
    content_type: ContentType
    confidence: float
    title: Optional[str]
    text_length: int
    should_retain: bool


@dataclass
class FilteringStats:
    """Statistics from content filtering process"""
    original_length: int
    filtered_length: int
    sections_identified: int
    prefatory_removed: int
    appendix_removed: int
    core_content_retained: int
    retention_ratio: float
    content_types_found: Dict[ContentType, int]


@dataclass
class FilteringResult:
    """Result from content filtering operation"""
    filtered_text: str
    stats: FilteringStats
    sections: List[ContentSection]
    quality_score: float
    warnings: List[str]


class ContentFilter:
    """
    Advanced content filtering system for educational documents.
    
    Features:
    - Intelligent prefatory content detection and removal
    - Appendix and bibliography detection
    - Copyright and acknowledgment removal
    - Table of contents filtering
    - Core educational content preservation
    - Configurable retention policies
    - Quality validation and scoring
    """
    
    def __init__(self, 
                 min_retention_ratio: float = 0.5,
                 preserve_learning_objectives: bool = True,
                 aggressive_filtering: bool = False):
        """
        Initialize ContentFilter with configuration options.
        
        Args:
            min_retention_ratio: Minimum ratio of content to retain (0.5 = 50%)
            preserve_learning_objectives: Keep learning objectives in prefatory content
            aggressive_filtering: More aggressive removal of questionable content
        """
        self.min_retention_ratio = min_retention_ratio
        self.preserve_learning_objectives = preserve_learning_objectives
        self.aggressive_filtering = aggressive_filtering
        self.logger = logging.getLogger(__name__)
        
        # Initialize structure detector for chapter boundaries
        self.structure_detector = StructureDetector()
        
        # Compile regex patterns
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for content detection"""
        
        # Prefatory content patterns
        self.prefatory_patterns = {
            'copyright': re.compile(
                r'(?:copyright|©|\(c\))\s*(?:\d{4}|\d{4}\s*[-–—]\s*\d{4})',
                re.IGNORECASE | re.MULTILINE
            ),
            'table_of_contents': re.compile(
                r'(?:^|\n)\s*(?:table\s+of\s+contents|contents)\s*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'preface': re.compile(
                r'(?:^|\n)\s*(?:preface|foreword|introduction)\s*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'acknowledgments': re.compile(
                r'(?:^|\n)\s*(?:acknowledgment?s?|thanks?)\s*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'about_author': re.compile(
                r'(?:^|\n)\s*(?:about\s+the\s+author|author\s+biography)\s*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'publisher_info': re.compile(
                r'(?:published\s+by|publisher|printing|edition|isbn)',
                re.IGNORECASE | re.MULTILINE
            )
        }
        
        # Appendix content patterns
        self.appendix_patterns = {
            'appendix': re.compile(
                r'(?:^|\n)\s*(?:appendix\s*[a-z]?|appendices)\s*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'bibliography': re.compile(
                r'(?:^|\n)\s*(?:bibliography|references|works?\s+cited)\s*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'index': re.compile(
                r'(?:^|\n)\s*(?:index|subject\s+index)\s*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'glossary': re.compile(
                r'(?:^|\n)\s*(?:glossary|terms|definitions)\s*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            'answer_key': re.compile(
                r'(?:^|\n)\s*(?:answer\s+key|solutions|answers)\s*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            )
        }
        
        # Essential content patterns (should be preserved even in prefatory sections)
        self.essential_patterns = {
            'learning_objectives': re.compile(
                r'(?:learning\s+objectives?|objectives?|goals?|outcomes?)',
                re.IGNORECASE | re.MULTILINE
            ),
            'overview': re.compile(
                r'(?:overview|summary|key\s+concepts?)',
                re.IGNORECASE | re.MULTILINE
            ),
            'prerequisites': re.compile(
                r'(?:prerequisites?|requirements?|background)',
                re.IGNORECASE | re.MULTILINE
            )
        }
        
        # Table of contents line patterns
        self.toc_line_patterns = [
            re.compile(r'^\s*(?:chapter\s+)?\d+\.?\s+.+?\.{3,}\s*\d+\s*$', re.IGNORECASE),
            re.compile(r'^\s*.+?\.{3,}\s*\d+\s*$'),
            re.compile(r'^\s*\d+\.\d+\s+.+?\.{3,}\s*\d+\s*$'),
        ]
    
    def filter_content(self, text: str, structure_elements: Optional[List[StructureElement]] = None) -> FilteringResult:
        """
        Filter document content to remove prefatory and appendix material.
        
        Args:
            text: Full document text
            structure_elements: Optional pre-detected structure elements
            
        Returns:
            FilteringResult with filtered text and statistics
        """
        if not text or not text.strip():
            return FilteringResult(
                filtered_text="",
                stats=FilteringStats(0, 0, 0, 0, 0, 0, 0.0, {}),
                sections=[],
                quality_score=0.0,
                warnings=["Empty text provided"]
            )
        
        original_length = len(text)
        self.logger.info(f"Starting content filtering on {original_length} characters")
        
        # Detect structure if not provided
        if structure_elements is None:
            detection_result = self.structure_detector.detect_structure(text)
            structure_elements = detection_result.hierarchy.elements
        
        # Identify content sections
        sections = self._identify_content_sections(text, structure_elements)
        
        # Determine content boundaries
        core_boundaries = self._determine_core_boundaries(sections, structure_elements)
        
        # Apply filtering logic
        filtered_sections = self._apply_filtering_logic(sections, core_boundaries)
        
        # Extract filtered text
        filtered_text = self._extract_filtered_text(text, filtered_sections)
        
        # Validate retention ratio
        filtered_text, warnings = self._validate_retention(text, filtered_text)
        
        # Calculate statistics
        stats = self._calculate_stats(original_length, len(filtered_text), sections)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(stats, warnings)
        
        self.logger.info(f"Content filtering completed. Retained {len(filtered_text)}/{original_length} characters ({stats.retention_ratio:.1%})")
        
        return FilteringResult(
            filtered_text=filtered_text,
            stats=stats,
            sections=filtered_sections,
            quality_score=quality_score,
            warnings=warnings
        )
    
    def _identify_content_sections(self, text: str, structure_elements: List[StructureElement]) -> List[ContentSection]:
        """Identify and classify different content sections"""
        sections = []
        text_length = len(text)
        
        # Create sections based on structure elements
        for i, element in enumerate(structure_elements):
            start_pos = element.start_position
            end_pos = element.end_position or text_length
            
            # Extract section text for analysis
            section_text = text[start_pos:end_pos]
            
            # Classify content type
            content_type, confidence = self._classify_content_type(element, section_text)
            
            section = ContentSection(
                start_position=start_pos,
                end_position=end_pos,
                content_type=content_type,
                confidence=confidence,
                title=element.title,
                text_length=len(section_text),
                should_retain=content_type == ContentType.CORE_CONTENT
            )
            
            sections.append(section)
        
        # Fill gaps between structure elements
        sections = self._fill_content_gaps(text, sections)
        
        # Sort by position
        sections.sort(key=lambda s: s.start_position)
        
        return sections
    
    def _classify_content_type(self, element: StructureElement, text: str) -> Tuple[ContentType, float]:
        """Classify the type of content section"""
        title = element.title.lower() if element.title else ""
        text_lower = text.lower()
        
        # Check for specific content types
        
        # Copyright content
        if self.prefatory_patterns['copyright'].search(text):
            return ContentType.COPYRIGHT, 0.9
        
        # Table of contents
        if (self.prefatory_patterns['table_of_contents'].search(title) or
            self._is_table_of_contents(text)):
            return ContentType.TABLE_OF_CONTENTS, 0.85
        
        # Acknowledgments
        if self.prefatory_patterns['acknowledgments'].search(title):
            return ContentType.ACKNOWLEDGMENTS, 0.8
        
        # Bibliography/References
        if self.appendix_patterns['bibliography'].search(title):
            return ContentType.BIBLIOGRAPHY, 0.9
        
        # Index
        if self.appendix_patterns['index'].search(title):
            return ContentType.INDEX, 0.85
        
        # Glossary
        if self.appendix_patterns['glossary'].search(title):
            return ContentType.GLOSSARY, 0.8
        
        # Appendix
        if self.appendix_patterns['appendix'].search(title):
            return ContentType.APPENDIX, 0.85
        
        # Preface/Foreword
        if self.prefatory_patterns['preface'].search(title):
            # Check if it contains essential content
            if self.preserve_learning_objectives and self._contains_essential_content(text):
                return ContentType.CORE_CONTENT, 0.7
            return ContentType.PREFATORY, 0.8
        
        # Default to core content for chapters and sections
        if element.type in [StructureType.CHAPTER, StructureType.SECTION]:
            return ContentType.CORE_CONTENT, 0.9
        
        # General classification based on content
        prefatory_score = self._calculate_prefatory_score(text)
        appendix_score = self._calculate_appendix_score(text)
        
        if prefatory_score > 0.6:
            return ContentType.PREFATORY, prefatory_score
        elif appendix_score > 0.6:
            return ContentType.APPENDIX, appendix_score
        else:
            return ContentType.CORE_CONTENT, 0.5
    
    def _is_table_of_contents(self, text: str) -> bool:
        """Check if text appears to be a table of contents"""
        lines = text.split('\n')
        toc_lines = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check against TOC patterns
            if any(pattern.match(line) for pattern in self.toc_line_patterns):
                toc_lines += 1
        
        # If more than 30% of lines look like TOC entries
        total_lines = len([line for line in lines if line.strip()])
        return total_lines > 0 and (toc_lines / total_lines) > 0.3
    
    def _contains_essential_content(self, text: str) -> bool:
        """Check if text contains essential educational content"""
        return any(pattern.search(text) for pattern in self.essential_patterns.values())
    
    def _calculate_prefatory_score(self, text: str) -> float:
        """Calculate likelihood that content is prefatory"""
        score = 0.0
        text_lower = text.lower()
        
        # Check for prefatory indicators
        for pattern in self.prefatory_patterns.values():
            if pattern.search(text):
                score += 0.2
        
        # Check for publisher/copyright content
        if 'isbn' in text_lower or 'publisher' in text_lower:
            score += 0.3
        
        # Check for author information
        if 'author' in text_lower and 'biography' in text_lower:
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_appendix_score(self, text: str) -> float:
        """Calculate likelihood that content is appendix material"""
        score = 0.0
        
        # Check for appendix indicators
        for pattern in self.appendix_patterns.values():
            if pattern.search(text):
                score += 0.25
        
        # Check for reference-like content
        if re.search(r'\[\d+\]|\(\d{4}\)|et\s+al\.', text):
            score += 0.2
        
        return min(1.0, score)
    
    def _fill_content_gaps(self, text: str, sections: List[ContentSection]) -> List[ContentSection]:
        """Fill gaps between identified sections"""
        if not sections:
            # No structure detected, classify entire text
            content_type, confidence = self._classify_unstructured_content(text)
            return [ContentSection(
                start_position=0,
                end_position=len(text),
                content_type=content_type,
                confidence=confidence,
                title=None,
                text_length=len(text),
                should_retain=content_type == ContentType.CORE_CONTENT
            )]
        
        filled_sections = []
        
        # Add gap before first section
        if sections[0].start_position > 0:
            gap_text = text[0:sections[0].start_position]
            content_type, confidence = self._classify_unstructured_content(gap_text)
            filled_sections.append(ContentSection(
                start_position=0,
                end_position=sections[0].start_position,
                content_type=content_type,
                confidence=confidence,
                title=None,
                text_length=len(gap_text),
                should_retain=content_type == ContentType.CORE_CONTENT
            ))
        
        # Add existing sections and gaps between them
        for i, section in enumerate(sections):
            filled_sections.append(section)
            
            # Add gap after this section
            if i < len(sections) - 1:
                gap_start = section.end_position
                gap_end = sections[i + 1].start_position
                
                if gap_end > gap_start:
                    gap_text = text[gap_start:gap_end]
                    content_type, confidence = self._classify_unstructured_content(gap_text)
                    filled_sections.append(ContentSection(
                        start_position=gap_start,
                        end_position=gap_end,
                        content_type=content_type,
                        confidence=confidence,
                        title=None,
                        text_length=len(gap_text),
                        should_retain=content_type == ContentType.CORE_CONTENT
                    ))
        
        # Add gap after last section
        last_section = sections[-1]
        if last_section.end_position < len(text):
            gap_text = text[last_section.end_position:len(text)]
            content_type, confidence = self._classify_unstructured_content(gap_text)
            filled_sections.append(ContentSection(
                start_position=last_section.end_position,
                end_position=len(text),
                content_type=content_type,
                confidence=confidence,
                title=None,
                text_length=len(gap_text),
                should_retain=content_type == ContentType.CORE_CONTENT
            ))
        
        return filled_sections
    
    def _classify_unstructured_content(self, text: str) -> Tuple[ContentType, float]:
        """Classify content that doesn't have clear structure"""
        if not text.strip():
            return ContentType.UNKNOWN, 0.0
        
        # Check for specific patterns
        if self.prefatory_patterns['copyright'].search(text):
            return ContentType.COPYRIGHT, 0.8
        
        if self._is_table_of_contents(text):
            return ContentType.TABLE_OF_CONTENTS, 0.7
        
        # Use scoring system
        prefatory_score = self._calculate_prefatory_score(text)
        appendix_score = self._calculate_appendix_score(text)
        
        if prefatory_score > appendix_score and prefatory_score > 0.5:
            return ContentType.PREFATORY, prefatory_score
        elif appendix_score > 0.5:
            return ContentType.APPENDIX, appendix_score
        else:
            return ContentType.CORE_CONTENT, 0.6
    
    def _determine_core_boundaries(self, sections: List[ContentSection], structure_elements: List[StructureElement]) -> Tuple[int, int]:
        """Determine the boundaries of core educational content"""
        chapters = [e for e in structure_elements if e.type == StructureType.CHAPTER]
        
        if not chapters:
            # No clear chapters, use heuristics
            core_sections = [s for s in sections if s.content_type == ContentType.CORE_CONTENT]
            if core_sections:
                return core_sections[0].start_position, core_sections[-1].end_position
            else:
                # Keep middle 80% as fallback
                text_length = sections[-1].end_position if sections else 0
                return int(text_length * 0.1), int(text_length * 0.9)
        
        # Use first and last chapter boundaries
        first_chapter = min(chapters, key=lambda c: c.start_position)
        last_chapter = max(chapters, key=lambda c: c.start_position)
        
        return first_chapter.start_position, last_chapter.end_position or len(' '.join([s.title or '' for s in sections]))
    
    def _apply_filtering_logic(self, sections: List[ContentSection], core_boundaries: Tuple[int, int]) -> List[ContentSection]:
        """Apply filtering logic to determine which sections to retain"""
        core_start, core_end = core_boundaries
        filtered_sections = []
        
        for section in sections:
            should_retain = section.should_retain
            
            # Override retention logic based on position and type
            if section.start_position < core_start:
                # Before core content
                if (section.content_type in [ContentType.CORE_CONTENT] or
                    (self.preserve_learning_objectives and self._contains_essential_content_in_section(section))):
                    should_retain = True
                else:
                    should_retain = False
            elif section.start_position > core_end:
                # After core content
                if section.content_type == ContentType.CORE_CONTENT:
                    should_retain = True
                else:
                    should_retain = False
            else:
                # Within core boundaries - generally retain
                should_retain = section.content_type != ContentType.COPYRIGHT
            
            # Apply aggressive filtering if enabled
            if self.aggressive_filtering:
                if section.content_type in [ContentType.PREFATORY, ContentType.TABLE_OF_CONTENTS]:
                    should_retain = False
            
            section.should_retain = should_retain
            filtered_sections.append(section)
        
        return filtered_sections
    
    def _contains_essential_content_in_section(self, section: ContentSection) -> bool:
        """Check if a section contains essential content that should be preserved"""
        # This is a simplified check - in a real implementation you'd analyze the actual text
        return (section.title and 
                any(keyword in section.title.lower() 
                    for keyword in ['objective', 'goal', 'overview', 'prerequisite']))
    
    def _extract_filtered_text(self, original_text: str, sections: List[ContentSection]) -> str:
        """Extract text from sections marked for retention"""
        retained_parts = []
        
        for section in sections:
            if section.should_retain:
                section_text = original_text[section.start_position:section.end_position]
                retained_parts.append(section_text.strip())
        
        return '\n\n'.join(part for part in retained_parts if part)
    
    def _validate_retention(self, original_text: str, filtered_text: str) -> Tuple[str, List[str]]:
        """Validate that sufficient content has been retained"""
        warnings = []
        
        if not filtered_text.strip():
            warnings.append("All content was filtered out - returning original text")
            return original_text, warnings
        
        retention_ratio = len(filtered_text) / len(original_text)
        
        if retention_ratio < self.min_retention_ratio:
            warnings.append(f"Low retention ratio: {retention_ratio:.1%} < {self.min_retention_ratio:.1%}")
            
            # If too much was removed, be more conservative
            if retention_ratio < 0.3:
                warnings.append("Retention too low - returning original text")
                return original_text, warnings
        
        return filtered_text, warnings
    
    def _calculate_stats(self, original_length: int, filtered_length: int, sections: List[ContentSection]) -> FilteringStats:
        """Calculate filtering statistics"""
        content_types_found = {}
        prefatory_removed = 0
        appendix_removed = 0
        core_content_retained = 0
        
        for section in sections:
            content_type = section.content_type
            content_types_found[content_type] = content_types_found.get(content_type, 0) + 1
            
            if not section.should_retain:
                if content_type in [ContentType.PREFATORY, ContentType.COPYRIGHT, 
                                   ContentType.ACKNOWLEDGMENTS, ContentType.TABLE_OF_CONTENTS]:
                    prefatory_removed += 1
                elif content_type in [ContentType.APPENDIX, ContentType.BIBLIOGRAPHY, 
                                     ContentType.INDEX, ContentType.GLOSSARY]:
                    appendix_removed += 1
            else:
                if content_type == ContentType.CORE_CONTENT:
                    core_content_retained += 1
        
        retention_ratio = filtered_length / original_length if original_length > 0 else 0.0
        
        return FilteringStats(
            original_length=original_length,
            filtered_length=filtered_length,
            sections_identified=len(sections),
            prefatory_removed=prefatory_removed,
            appendix_removed=appendix_removed,
            core_content_retained=core_content_retained,
            retention_ratio=retention_ratio,
            content_types_found=content_types_found
        )
    
    def _calculate_quality_score(self, stats: FilteringStats, warnings: List[str]) -> float:
        """Calculate quality score for filtering results"""
        base_score = 0.8
        
        # Adjust based on retention ratio
        if 0.5 <= stats.retention_ratio <= 0.9:
            base_score += 0.1  # Good retention ratio
        elif stats.retention_ratio < 0.3:
            base_score -= 0.3  # Too much removed
        elif stats.retention_ratio > 0.95:
            base_score -= 0.1  # Too little removed
        
        # Bonus for successful content identification
        if stats.prefatory_removed > 0 or stats.appendix_removed > 0:
            base_score += 0.1
        
        # Penalty for warnings
        base_score -= len(warnings) * 0.1
        
        # Bonus for core content retention
        if stats.core_content_retained > 0:
            base_score += 0.1
        
        return max(0.0, min(1.0, base_score))