"""
Content-Aware Chunker - Intelligent chunking that respects educational structure

Creates semantically coherent chunks while preserving educational content boundaries,
mathematical expressions, and pedagogical relationships.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field

from .chunk_metadata import ChunkMetadata, ContentType
from .structure_detector import StructureElement, StructureType


@dataclass
class ChunkingResult:
    """Result from content-aware chunking operation"""
    chunks: List[str]
    metadata_list: List[ChunkMetadata]
    chunking_statistics: Dict[str, any]
    warnings: List[str] = field(default_factory=list)


@dataclass
class ChunkBoundary:
    """Represents a potential chunk boundary with quality score"""
    position: int
    boundary_type: str  # 'section', 'paragraph', 'sentence', 'forced'
    quality_score: float  # 0.0 to 1.0, higher is better boundary
    context: str = ""  # Text context around boundary


class MathematicalContentDetector:
    """Detects and preserves mathematical content as complete units"""
    
    def __init__(self):
        # LaTeX patterns
        self.latex_patterns = [
            r'\$[^$]+\$',  # Inline math: $E = mc^2$
            r'\$\$[^$]+\$\$',  # Display math: $$\int x dx$$  
            r'\\begin\{equation\}.*?\\end\{equation\}',  # Equation environment
            r'\\begin\{align\}.*?\\end\{align\}',  # Align environment
            r'\\begin\{eqnarray\}.*?\\end\{eqnarray\}',  # Eqnarray environment
        ]
        
        # Mathematical expressions and symbols
        self.math_patterns = [
            r'[∑∏∫∮∂∇][\w\s\(\)]+',  # Mathematical operators with context
            r'[α-ωΑ-Ω][\w\s]*',  # Greek letters
            r'\b\d+\s*[+\-*/=]\s*\d+.*?=.*?\d+',  # Simple equations
            r'[fx]\([^)]+\)\s*=\s*[^,.\n]+',  # Function definitions
            r'\\frac\{[^}]+\}\{[^}]+\}',  # Fractions
            r'[xy][\d²³⁴]+\s*[+\-]\s*[xy]?[\d²³⁴]*',  # Polynomials
        ]
        
        # Mathematical operators and symbols
        self.math_symbols = {
            '≈', '≠', '≤', '≥', '±', '∞', '√', '∑', '∏', '∫', '∮', '∂', '∇',
            'π', 'θ', 'φ', 'λ', 'μ', 'σ', 'ρ', 'Δ', 'Ω', 'α', 'β', 'γ'
        }
        
        self.compiled_patterns = [re.compile(pattern, re.DOTALL | re.IGNORECASE) 
                                 for pattern in self.latex_patterns + self.math_patterns]
    
    def find_mathematical_content(self, text: str) -> List[Tuple[int, int, str]]:
        """Find all mathematical content regions in text"""
        math_regions = []
        
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                start, end = match.span()
                content_type = self._classify_math_content(match.group())
                math_regions.append((start, end, content_type))
        
        # Merge overlapping regions
        return self._merge_overlapping_regions(math_regions)
    
    def _classify_math_content(self, content: str) -> str:
        """Classify type of mathematical content"""
        if content.startswith('$$') or '\\begin{' in content:
            return 'display_math'
        elif content.startswith('$'):
            return 'inline_math'
        elif '=' in content and any(op in content for op in ['+', '-', '*', '/']):
            return 'equation'
        elif 'f(' in content or 'g(' in content:
            return 'function'
        else:
            return 'mathematical_expression'
    
    def _merge_overlapping_regions(self, regions: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
        """Merge overlapping mathematical content regions"""
        if not regions:
            return []
        
        # Sort by start position
        sorted_regions = sorted(regions, key=lambda x: x[0])
        merged = [sorted_regions[0]]
        
        for current in sorted_regions[1:]:
            last = merged[-1]
            
            # If regions overlap or are very close (within 10 chars)
            if current[0] <= last[1] + 10:
                # Merge regions
                merged[-1] = (last[0], max(last[1], current[1]), f"{last[2]}+{current[2]}")
            else:
                merged.append(current)
        
        return merged


class DefinitionDetector:
    """Detects definitions and keeps them with their explanations"""
    
    def __init__(self):
        # Definition indicators
        self.definition_patterns = [
            r'(?:Definition|Define|Definition \d+\.?\d*)[:\.]?\s*([^.!?]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+(?:defined as|a|an)\s+([^.!?]+)',
            r'(?:Let|Suppose)\s+([^.!?]+)\s+(?:be|denote|represent)\s+([^.!?]+)',
            r'(?:We define|By definition)\s+([^.!?]+)',
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) 
                                 for pattern in self.definition_patterns]
    
    def find_definitions(self, text: str) -> List[Tuple[int, int, str]]:
        """Find definition regions in text"""
        definitions = []
        
        # Split into sentences to find definition boundaries
        sentences = re.split(r'[.!?]+\s+', text)
        position = 0
        
        for sentence in sentences:
            sentence_start = position
            sentence_end = position + len(sentence)
            
            for pattern in self.compiled_patterns:
                if pattern.search(sentence):
                    # Extend to include explanation (next 1-2 sentences)
                    extended_end = self._find_definition_end(text, sentence_end)
                    definitions.append((sentence_start, extended_end, 'definition'))
                    break
            
            position = sentence_end + 1
        
        return definitions
    
    def _find_definition_end(self, text: str, start_pos: int) -> int:
        """Find the end of a definition including its explanation"""
        # Look for end markers or extend by 1-2 sentences max
        remaining_text = text[start_pos:]
        
        # Find next 2 sentence boundaries
        sentence_ends = []
        for match in re.finditer(r'[.!?]\s+', remaining_text):
            sentence_ends.append(start_pos + match.end())
            if len(sentence_ends) >= 2:
                break
        
        if sentence_ends:
            # Use first sentence end if definition is complete, otherwise second
            if len(sentence_ends) >= 2 and len(remaining_text[:sentence_ends[0] - start_pos]) < 100:
                return sentence_ends[1]
            else:
                return sentence_ends[0]
        else:
            # No sentence boundaries found, use reasonable default
            return min(start_pos + 200, len(text))


class ExampleDetector:
    """Detects examples and exercises, keeping them with solutions"""
    
    def __init__(self):
        self.example_patterns = [
            r'(?:Example|Ex\.?)\s*\d*[:\.]?\s*([^.!?]+)',
            r'(?:Exercise|Problem)\s*\d*[:\.]?\s*([^.!?]+)',
            r'(?:Consider|Suppose)\s+the\s+(?:following|case|example)',
            r'(?:For\s+instance|For\s+example)[,:]?\s*([^.!?]+)',
        ]
        
        self.solution_patterns = [
            r'(?:Solution|Answer|Proof)[:\.]?\s*',
            r'(?:We\s+(?:have|get|obtain|find)|Therefore|Thus|Hence)[,:]?\s*',
        ]
        
        self.compiled_example_patterns = [re.compile(pattern, re.IGNORECASE) 
                                         for pattern in self.example_patterns]
        self.compiled_solution_patterns = [re.compile(pattern, re.IGNORECASE)
                                          for pattern in self.solution_patterns]
    
    def find_examples(self, text: str) -> List[Tuple[int, int, str]]:
        """Find example regions including their solutions"""
        examples = []
        
        for pattern in self.compiled_example_patterns:
            for match in pattern.finditer(text):
                start = match.start()
                
                # Find the end of the example (including solution if present)
                end = self._find_example_end(text, start)
                examples.append((start, end, 'example'))
        
        return self._merge_overlapping_regions(examples)
    
    def _find_example_end(self, text: str, start_pos: int) -> int:
        """Find the end of an example including its solution"""
        remaining_text = text[start_pos:]
        
        # Look for solution markers
        solution_start = None
        for pattern in self.compiled_solution_patterns:
            match = pattern.search(remaining_text)
            if match and match.start() < 500:  # Solution should be reasonably close
                solution_start = start_pos + match.start()
                break
        
        if solution_start:
            # Find end of solution (next example, exercise, or paragraph break)
            solution_text = text[solution_start:]
            
            # Look for next example/exercise
            for pattern in self.compiled_example_patterns:
                match = pattern.search(solution_text)
                if match and match.start() > 50:  # Not too close
                    return solution_start + match.start()
            
            # Look for paragraph break or reasonable length
            paragraph_break = re.search(r'\n\s*\n', solution_text)
            if paragraph_break and paragraph_break.start() > 50:
                return solution_start + paragraph_break.start()
            else:
                return min(solution_start + 300, len(text))
        else:
            # No solution found, end at paragraph break or reasonable length
            paragraph_break = re.search(r'\n\s*\n', remaining_text)
            if paragraph_break:
                return start_pos + paragraph_break.start()
            else:
                return min(start_pos + 200, len(text))
    
    def _merge_overlapping_regions(self, regions: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
        """Merge overlapping example regions"""
        if not regions:
            return []
        
        sorted_regions = sorted(regions, key=lambda x: x[0])
        merged = [sorted_regions[0]]
        
        for current in sorted_regions[1:]:
            last = merged[-1]
            
            if current[0] <= last[1]:
                merged[-1] = (last[0], max(last[1], current[1]), last[2])
            else:
                merged.append(current)
        
        return merged


class ContentAwareChunker:
    """
    Intelligent chunker that respects educational content structure.
    
    Creates chunks by respecting chapter/section boundaries while preserving
    mathematical content, definitions, and examples as complete units.
    """
    
    def __init__(self,
                 target_chunk_size: int = 1250,  # 1000-1500 range
                 min_chunk_size: int = 300,
                 max_chunk_size: int = 1500,
                 overlap_size: int = 150,
                 preserve_math: bool = True,
                 preserve_definitions: bool = True,
                 preserve_examples: bool = True):
        """
        Initialize content-aware chunker.
        
        Args:
            target_chunk_size: Target size for chunks (characters)
            min_chunk_size: Minimum acceptable chunk size
            max_chunk_size: Maximum acceptable chunk size  
            overlap_size: Overlap between chunks within sections
            preserve_math: Preserve mathematical content as complete units
            preserve_definitions: Keep definitions with explanations
            preserve_examples: Keep examples with solutions
        """
        self.target_chunk_size = target_chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.preserve_math = preserve_math
        self.preserve_definitions = preserve_definitions
        self.preserve_examples = preserve_examples
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize content detectors
        self.math_detector = MathematicalContentDetector()
        self.definition_detector = DefinitionDetector()
        self.example_detector = ExampleDetector()
    
    def chunk_content(self,
                     text: str,
                     structure_elements: List[StructureElement],
                     book_id: str,
                     metadata_base: Dict[str, any] = None) -> ChunkingResult:
        """
        Chunk content while respecting educational structure.
        
        Args:
            text: Text content to chunk
            structure_elements: Detected structure elements
            book_id: Identifier for the book
            metadata_base: Base metadata to include in all chunks
            
        Returns:
            ChunkingResult with chunks and metadata
        """
        self.logger.info(f"Starting content-aware chunking for {len(text)} characters")
        
        if not text.strip():
            return ChunkingResult(chunks=[], metadata_list=[], chunking_statistics={})
        
        metadata_base = metadata_base or {}
        
        # Find protected content regions
        protected_regions = self._find_protected_regions(text)
        
        # Organize structure elements by hierarchy
        structured_sections = self._organize_by_structure(structure_elements, text)
        
        # Chunk each section separately
        all_chunks = []
        all_metadata = []
        warnings = []
        
        for section_info in structured_sections:
            section_chunks, section_metadata, section_warnings = self._chunk_section(
                text, section_info, protected_regions, book_id, metadata_base
            )
            
            all_chunks.extend(section_chunks)
            all_metadata.extend(section_metadata)
            warnings.extend(section_warnings)
        
        # Calculate statistics
        statistics = self._calculate_chunking_statistics(all_chunks, all_metadata)
        
        self.logger.info(f"Content-aware chunking complete: {len(all_chunks)} chunks created")
        
        return ChunkingResult(
            chunks=all_chunks,
            metadata_list=all_metadata,
            chunking_statistics=statistics,
            warnings=warnings
        )
    
    def _find_protected_regions(self, text: str) -> List[Tuple[int, int, str]]:
        """Find regions that should not be split (math, definitions, examples)"""
        protected_regions = []
        
        if self.preserve_math:
            math_regions = self.math_detector.find_mathematical_content(text)
            protected_regions.extend(math_regions)
        
        if self.preserve_definitions:
            def_regions = self.definition_detector.find_definitions(text)
            protected_regions.extend(def_regions)
        
        if self.preserve_examples:
            example_regions = self.example_detector.find_examples(text)
            protected_regions.extend(example_regions)
        
        # Sort and merge overlapping regions
        return self._merge_all_protected_regions(protected_regions)
    
    def _merge_all_protected_regions(self, regions: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
        """Merge all overlapping protected regions"""
        if not regions:
            return []
        
        # Sort by start position
        sorted_regions = sorted(regions, key=lambda x: x[0])
        merged = [sorted_regions[0]]
        
        for current in sorted_regions[1:]:
            last = merged[-1]
            
            # If regions overlap or are very close
            if current[0] <= last[1] + 20:
                # Merge regions, combining types
                new_type = f"{last[2]}+{current[2]}" if last[2] != current[2] else last[2]
                merged[-1] = (last[0], max(last[1], current[1]), new_type)
            else:
                merged.append(current)
        
        return merged
    
    def _organize_by_structure(self, 
                              elements: List[StructureElement], 
                              text: str) -> List[Dict[str, any]]:
        """Organize text into structured sections for chunking"""
        if not elements:
            # No structure detected, treat entire text as one section
            return [{
                'type': 'unstructured',
                'title': 'Content',
                'start': 0,
                'end': len(text),
                'level': 0,
                'chapter': '',
                'section': ''
            }]
        
        # Sort elements by position
        sorted_elements = sorted(elements, key=lambda x: x.start_position)
        sections = []
        
        for i, element in enumerate(sorted_elements):
            # Determine section boundaries
            start_pos = element.start_position
            
            # Find end position (start of next element of same or higher level)
            end_pos = len(text)
            for j in range(i + 1, len(sorted_elements)):
                next_element = sorted_elements[j]
                if next_element.level <= element.level:
                    end_pos = next_element.start_position
                    break
            
            # Determine chapter and section context
            chapter, section = self._determine_context(element, sorted_elements[:i])
            
            sections.append({
                'type': element.type.value,
                'title': element.title,
                'start': start_pos,
                'end': end_pos,
                'level': element.level,
                'chapter': chapter,
                'section': section,
                'element': element
            })
        
        return sections
    
    def _determine_context(self, 
                          element: StructureElement, 
                          previous_elements: List[StructureElement]) -> Tuple[str, str]:
        """Determine chapter and section context for an element"""
        chapter = ""
        section = ""
        
        # Look backwards for chapter context
        for prev in reversed(previous_elements):
            if prev.type == StructureType.CHAPTER and not chapter:
                chapter = prev.number or prev.title
            elif prev.type == StructureType.SECTION and not section and prev.level < element.level:
                section = prev.number or prev.title
        
        # Current element context
        if element.type == StructureType.CHAPTER:
            chapter = element.number or element.title
        elif element.type == StructureType.SECTION:
            section = element.number or element.title
        
        return chapter, section
    
    def _chunk_section(self,
                      text: str,
                      section_info: Dict[str, any],
                      protected_regions: List[Tuple[int, int, str]],
                      book_id: str,
                      metadata_base: Dict[str, any]) -> Tuple[List[str], List[ChunkMetadata], List[str]]:
        """Chunk a single structured section"""
        section_text = text[section_info['start']:section_info['end']]
        section_start = section_info['start']
        
        if len(section_text.strip()) < self.min_chunk_size:
            # Section too small, return as single chunk
            chunk_metadata = self._create_chunk_metadata(
                text=section_text,
                chunk_id=f"{book_id}_chunk_{section_start}",
                book_id=book_id,
                section_info=section_info,
                start_pos=section_start,
                end_pos=section_info['end'],
                metadata_base=metadata_base
            )
            
            return [section_text], [chunk_metadata], []
        
        # Find relevant protected regions for this section
        section_protected = []
        for start, end, ptype in protected_regions:
            if start >= section_start and end <= section_info['end']:
                # Adjust positions relative to section
                section_protected.append((start - section_start, end - section_start, ptype))
        
        # Find optimal chunk boundaries
        boundaries = self._find_chunk_boundaries(section_text, section_protected)
        
        # Create chunks based on boundaries
        chunks = []
        metadata_list = []
        warnings = []
        
        current_pos = 0
        for i, boundary in enumerate(boundaries):
            chunk_end = boundary.position
            
            # Apply overlap for non-boundary chunks
            if i > 0 and boundary.boundary_type not in ['section', 'chapter']:
                overlap_start = max(0, current_pos - self.overlap_size)
            else:
                overlap_start = current_pos
            
            chunk_text = section_text[overlap_start:chunk_end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunk_metadata = self._create_chunk_metadata(
                    text=chunk_text,
                    chunk_id=f"{book_id}_chunk_{section_start + overlap_start}",
                    book_id=book_id,
                    section_info=section_info,
                    start_pos=section_start + overlap_start,
                    end_pos=section_start + chunk_end,
                    metadata_base=metadata_base,
                    protected_regions=section_protected
                )
                
                chunks.append(chunk_text)
                metadata_list.append(chunk_metadata)
            else:
                warnings.append(f"Chunk too small ({len(chunk_text)} chars), merging with next")
            
            current_pos = chunk_end
        
        # Handle remaining text
        if current_pos < len(section_text):
            remaining_text = section_text[current_pos:].strip()
            if len(remaining_text) >= self.min_chunk_size:
                chunk_metadata = self._create_chunk_metadata(
                    text=remaining_text,
                    chunk_id=f"{book_id}_chunk_{section_start + current_pos}",
                    book_id=book_id,
                    section_info=section_info,
                    start_pos=section_start + current_pos,
                    end_pos=section_info['end'],
                    metadata_base=metadata_base,
                    protected_regions=section_protected
                )
                
                chunks.append(remaining_text)
                metadata_list.append(chunk_metadata)
            elif chunks:
                # Merge with last chunk
                chunks[-1] += " " + remaining_text
                metadata_list[-1].end_position = section_info['end']
                metadata_list[-1].char_count = len(chunks[-1])
                metadata_list[-1].word_count = len(chunks[-1].split())
                metadata_list[-1].sentence_count = len(re.findall(r'[.!?]+', chunks[-1]))
        
        return chunks, metadata_list, warnings
    
    def _find_chunk_boundaries(self, 
                              text: str, 
                              protected_regions: List[Tuple[int, int, str]]) -> List[ChunkBoundary]:
        """Find optimal chunk boundaries within text"""
        boundaries = []
        current_pos = 0
        
        while current_pos < len(text):
            # Find next boundary position
            target_pos = current_pos + self.target_chunk_size
            
            if target_pos >= len(text):
                # Last chunk
                boundaries.append(ChunkBoundary(
                    position=len(text),
                    boundary_type='end',
                    quality_score=1.0
                ))
                break
            
            # Find best boundary near target position
            best_boundary = self._find_best_boundary(
                text, current_pos, target_pos, protected_regions
            )
            
            boundaries.append(best_boundary)
            current_pos = best_boundary.position
        
        return boundaries
    
    def _find_best_boundary(self,
                           text: str,
                           start_pos: int,
                           target_pos: int,
                           protected_regions: List[Tuple[int, int, str]]) -> ChunkBoundary:
        """Find the best boundary position near target"""
        # Search window around target position
        search_start = max(start_pos + self.min_chunk_size, target_pos - 200)
        search_end = min(len(text), target_pos + 200)
        
        # Check if target position is within a protected region
        for pstart, pend, ptype in protected_regions:
            if pstart <= target_pos <= pend:
                # Move boundary to after protected region
                if pend < search_end:
                    return ChunkBoundary(
                        position=pend,
                        boundary_type='protected_region',
                        quality_score=0.9,
                        context=f"After {ptype}"
                    )
                # Or before protected region
                elif pstart > search_start:
                    return ChunkBoundary(
                        position=pstart,
                        boundary_type='protected_region',
                        quality_score=0.8,
                        context=f"Before {ptype}"
                    )
        
        # Look for natural boundaries in search window
        candidates = []
        
        # Paragraph breaks (highest quality)
        for match in re.finditer(r'\n\s*\n', text[search_start:search_end]):
            pos = search_start + match.end()
            candidates.append(ChunkBoundary(
                position=pos,
                boundary_type='paragraph',
                quality_score=0.9
            ))
        
        # Sentence boundaries (good quality)
        for match in re.finditer(r'[.!?]\s+', text[search_start:search_end]):
            pos = search_start + match.end()
            candidates.append(ChunkBoundary(
                position=pos,
                boundary_type='sentence',
                quality_score=0.7
            ))
        
        # Word boundaries (acceptable quality)
        for match in re.finditer(r'\s+', text[search_start:search_end]):
            pos = search_start + match.end()
            candidates.append(ChunkBoundary(
                position=pos,
                boundary_type='word',
                quality_score=0.5
            ))
        
        if not candidates:
            # Forced boundary at target position
            return ChunkBoundary(
                position=target_pos,
                boundary_type='forced',
                quality_score=0.2
            )
        
        # Choose best candidate based on quality and distance to target
        best_candidate = max(candidates, key=lambda c: self._score_boundary_candidate(c, target_pos))
        return best_candidate
    
    def _score_boundary_candidate(self, candidate: ChunkBoundary, target_pos: int) -> float:
        """Score a boundary candidate based on quality and distance"""
        distance = abs(candidate.position - target_pos)
        distance_score = max(0, 1.0 - distance / 200)  # Penalty for distance from target
        
        return candidate.quality_score * 0.7 + distance_score * 0.3
    
    def _create_chunk_metadata(self,
                              text: str,
                              chunk_id: str,
                              book_id: str,
                              section_info: Dict[str, any],
                              start_pos: int,
                              end_pos: int,
                              metadata_base: Dict[str, any],
                              protected_regions: List[Tuple[int, int, str]] = None) -> ChunkMetadata:
        """Create metadata for a chunk"""
        
        # Determine content type based on protected regions
        content_type = ContentType.TEXT
        if protected_regions:
            for pstart, pend, ptype in protected_regions:
                if pstart < len(text) and pend > 0:  # Region overlaps with chunk
                    if 'math' in ptype or 'equation' in ptype:
                        content_type = ContentType.MATH
                        break
                    elif 'definition' in ptype:
                        content_type = ContentType.DEFINITION
                        break
                    elif 'example' in ptype:
                        content_type = ContentType.EXAMPLE
                        break
        
        # Calculate basic metrics
        word_count = len(text.split())
        sentence_count = len(re.findall(r'[.!?]+', text))
        
        # Extract keywords (simple approach - most frequent meaningful words)
        keywords = self._extract_keywords(text)
        
        # Estimate difficulty based on content characteristics
        difficulty = self._estimate_difficulty(text, content_type, keywords)
        
        # Calculate confidence based on chunk quality
        confidence = self._calculate_chunk_confidence(text, content_type, word_count, sentence_count)
        
        metadata = ChunkMetadata(
            book_id=book_id,
            chunk_id=chunk_id,
            title=metadata_base.get('title', ''),
            subject=metadata_base.get('subject', ''),
            chapter=section_info.get('chapter', ''),
            section=section_info.get('section', ''),
            content_type=content_type,
            difficulty=difficulty,
            keywords=keywords,
            start_position=start_pos,
            end_position=end_pos,
            confidence_score=confidence,
            structure_quality=0.8,  # High for content-aware chunking
            content_coherence=0.7,  # Reasonable default
            char_count=len(text),
            word_count=word_count,
            sentence_count=sentence_count,
            chunking_strategy="content_aware"
        )
        
        # Add custom metadata
        for key, value in metadata_base.items():
            if key not in ['title', 'subject']:
                metadata.custom_metadata[key] = value
        
        return metadata
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract keywords from text (simple frequency-based approach)"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'this', 'that', 'these', 'those'
        }
        
        # Extract words and count frequency
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_freq = {}
        
        for word in words:
            if word not in stop_words and len(word) >= 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return most frequent words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
    
    def _estimate_difficulty(self, text: str, content_type: ContentType, keywords: List[str]) -> float:
        """Estimate difficulty of content"""
        base_difficulty = 0.5
        
        # Adjust based on content type
        type_adjustments = {
            ContentType.MATH: 0.2,
            ContentType.DEFINITION: 0.15,
            ContentType.EXAMPLE: -0.1,
            ContentType.TEXT: 0.0
        }
        base_difficulty += type_adjustments.get(content_type, 0.0)
        
        # Adjust based on text characteristics
        avg_word_length = sum(len(word) for word in text.split()) / max(1, len(text.split()))
        if avg_word_length > 6:
            base_difficulty += 0.1
        
        # Adjust based on sentence complexity
        sentences = re.split(r'[.!?]+', text)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
        if avg_sentence_length > 20:
            base_difficulty += 0.1
        
        # Mathematical symbols increase difficulty
        math_symbols = set(text) & self.math_detector.math_symbols
        if math_symbols:
            base_difficulty += len(math_symbols) * 0.02
        
        return max(0.0, min(1.0, base_difficulty))
    
    def _calculate_chunk_confidence(self, 
                                   text: str, 
                                   content_type: ContentType, 
                                   word_count: int, 
                                   sentence_count: int) -> float:
        """Calculate confidence in chunk quality"""
        confidence = 0.8  # Base confidence for content-aware chunking
        
        # Adjust based on chunk size appropriateness
        char_count = len(text)
        if self.min_chunk_size <= char_count <= self.max_chunk_size:
            confidence += 0.1
        elif char_count < self.min_chunk_size:
            confidence -= 0.2
        
        # Adjust based on content completeness
        if content_type in [ContentType.MATH, ContentType.DEFINITION, ContentType.EXAMPLE]:
            confidence += 0.1  # These should be complete units
        
        # Adjust based on sentence completeness
        if sentence_count > 0 and not text.strip().endswith(('.', '!', '?')):
            confidence -= 0.1  # Incomplete sentence
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_chunking_statistics(self, 
                                     chunks: List[str], 
                                     metadata_list: List[ChunkMetadata]) -> Dict[str, any]:
        """Calculate statistics for the chunking operation"""
        if not chunks:
            return {}
        
        chunk_sizes = [len(chunk) for chunk in chunks]
        
        # Content type distribution
        content_types = {}
        for metadata in metadata_list:
            content_types[metadata.content_type.value] = content_types.get(metadata.content_type.value, 0) + 1
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes),
            'min_chunk_size': min(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'size_std_dev': (sum((size - sum(chunk_sizes) / len(chunk_sizes)) ** 2 for size in chunk_sizes) / len(chunk_sizes)) ** 0.5,
            'total_characters': sum(chunk_sizes),
            'content_type_distribution': content_types,
            'avg_confidence': sum(m.confidence_score for m in metadata_list) / len(metadata_list),
            'chunking_strategy': 'content_aware'
        }