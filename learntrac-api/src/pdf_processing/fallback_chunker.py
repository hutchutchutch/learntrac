"""
Fallback Chunker - Robust chunking for documents with poor structure detection

Implements sentence-boundary splitting and fixed-size chunking with word boundaries
for documents that lack clear educational structure.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field

from .chunk_metadata import ChunkMetadata, ContentType


@dataclass
class SentenceBoundary:
    """Represents a sentence boundary with quality metrics"""
    position: int
    boundary_type: str  # 'period', 'exclamation', 'question', 'semicolon'
    confidence: float  # 0.0 to 1.0
    context_before: str = ""
    context_after: str = ""


@dataclass
class FallbackChunkingResult:
    """Result from fallback chunking operation"""
    chunks: List[str]
    metadata_list: List[ChunkMetadata]
    chunking_statistics: Dict[str, any]
    warnings: List[str] = field(default_factory=list)
    sentence_boundaries_used: int = 0
    word_boundaries_used: int = 0


class SentenceTokenizer:
    """
    Sentence boundary detection without external dependencies.
    
    Implements robust sentence segmentation for educational content
    including special handling for abbreviations, mathematical notation,
    and academic writing patterns.
    """
    
    def __init__(self):
        # Common abbreviations that shouldn't end sentences
        self.abbreviations = {
            'dr', 'mr', 'mrs', 'ms', 'prof', 'vs', 'etc', 'ie', 'eg', 'cf',
            'fig', 'eq', 'eqn', 'sec', 'ch', 'vol', 'no', 'pp', 'p',
            'st', 'nd', 'rd', 'th', 'inc', 'corp', 'ltd', 'co',
            # Academic abbreviations
            'et al', 'ibid', 'op cit', 'loc cit', 'circa', 'ca', 'approx',
            # Units and measurements
            'cm', 'mm', 'km', 'kg', 'mg', 'ml', 'hr', 'min', 'sec',
            # Mathematical and scientific
            'max', 'min', 'avg', 'std', 'var', 'def', 'thm', 'prop', 'cor'
        }
        
        # Sentence ending patterns
        self.sentence_endings = [
            r'[.!?]+\s+[A-Z]',  # Period/exclamation/question followed by capital
            r'[.!?]+\s*\n\s*[A-Z]',  # Sentence ending with newline
            r'[.!?]+\s*$',  # Sentence ending at end of text
        ]
        
        # Mathematical content patterns (to avoid breaking in middle)
        self.math_patterns = [
            r'\$[^$]+\$',  # Inline math
            r'\$\$[^$]+\$\$',  # Display math
            r'\\[a-zA-Z]+\{[^}]*\}',  # LaTeX commands
            r'[∑∏∫∮∂∇][^.!?]*',  # Math symbols with context
        ]
        
        self.compiled_math_patterns = [re.compile(pattern) for pattern in self.math_patterns]
    
    def tokenize_sentences(self, text: str) -> List[SentenceBoundary]:
        """
        Tokenize text into sentences, returning boundary positions.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of SentenceBoundary objects
        """
        if not text.strip():
            return []
        
        # Find mathematical content regions to protect
        math_regions = self._find_math_regions(text)
        
        # Find potential sentence boundaries
        potential_boundaries = self._find_potential_boundaries(text)
        
        # Filter boundaries that fall within mathematical content
        valid_boundaries = []
        for boundary in potential_boundaries:
            if not self._is_in_math_region(boundary.position, math_regions):
                if self._validate_sentence_boundary(text, boundary):
                    valid_boundaries.append(boundary)
        
        return valid_boundaries
    
    def _find_math_regions(self, text: str) -> List[Tuple[int, int]]:
        """Find regions containing mathematical content"""
        math_regions = []
        
        for pattern in self.compiled_math_patterns:
            for match in pattern.finditer(text):
                math_regions.append((match.start(), match.end()))
        
        # Merge overlapping regions
        if math_regions:
            math_regions.sort()
            merged = [math_regions[0]]
            
            for start, end in math_regions[1:]:
                if start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
            
            return merged
        
        return []
    
    def _find_potential_boundaries(self, text: str) -> List[SentenceBoundary]:
        """Find all potential sentence boundaries"""
        boundaries = []
        
        # Look for periods, exclamation marks, question marks
        for match in re.finditer(r'([.!?]+)(\s*)', text):
            pos = match.end()
            punctuation = match.group(1)
            
            # Determine boundary type
            if '.' in punctuation:
                boundary_type = 'period'
            elif '!' in punctuation:
                boundary_type = 'exclamation'
            elif '?' in punctuation:
                boundary_type = 'question'
            else:
                boundary_type = 'period'
            
            # Get context
            context_before = text[max(0, match.start() - 20):match.start()]
            context_after = text[pos:pos + 20]
            
            boundaries.append(SentenceBoundary(
                position=pos,
                boundary_type=boundary_type,
                confidence=0.8,  # Will be adjusted by validation
                context_before=context_before,
                context_after=context_after
            ))
        
        return boundaries
    
    def _is_in_math_region(self, position: int, math_regions: List[Tuple[int, int]]) -> bool:
        """Check if position falls within a mathematical region"""
        for start, end in math_regions:
            if start <= position <= end:
                return True
        return False
    
    def _validate_sentence_boundary(self, text: str, boundary: SentenceBoundary) -> bool:
        """Validate if a potential boundary is actually a sentence end"""
        pos = boundary.position
        
        # Check for abbreviations
        word_before = self._get_word_before(text, pos)
        if word_before and word_before.lower() in self.abbreviations:
            boundary.confidence *= 0.3  # Probably not a sentence boundary
            return False
        
        # Check if followed by lowercase (likely not sentence boundary)
        if pos < len(text) and text[pos:pos+1].strip() and text[pos].islower():
            boundary.confidence *= 0.2
            return False
        
        # Check for academic patterns like "et al."
        context_before = text[max(0, pos - 10):pos].lower()
        if any(abbrev in context_before for abbrev in ['et al', 'i.e', 'e.g']):
            boundary.confidence *= 0.4
            return False
        
        # Check for numbered lists or equations
        if re.search(r'\d+\.\s*$', text[max(0, pos - 10):pos]):
            boundary.confidence *= 0.5
            return False
        
        # Good indicators of sentence boundaries
        context_after = text[pos:pos + 5].strip()
        if context_after and context_after[0].isupper():
            boundary.confidence *= 1.2
        
        # Newline after punctuation is good indicator
        if '\n' in text[pos:pos + 3]:
            boundary.confidence *= 1.3
        
        boundary.confidence = min(1.0, boundary.confidence)
        return boundary.confidence > 0.5
    
    def _get_word_before(self, text: str, pos: int) -> Optional[str]:
        """Get the word immediately before the given position"""
        # Look backwards for word boundary
        i = pos - 1
        while i >= 0 and not text[i].isalpha():
            i -= 1
        
        if i < 0:
            return None
        
        # Find start of word
        word_end = i + 1
        while i >= 0 and (text[i].isalpha() or text[i] in '.-'):
            i -= 1
        
        word_start = i + 1
        return text[word_start:word_end]


class FallbackChunker:
    """
    Robust fallback chunker for documents with poor structure detection.
    
    Uses sentence-boundary splitting and fixed-size chunking with word boundaries
    when document structure is insufficient for content-aware chunking.
    """
    
    def __init__(self,
                 target_chunk_size: int = 1000,
                 min_chunk_size: int = 300,
                 max_chunk_size: int = 1500,
                 overlap_size: int = 200,
                 prefer_sentence_boundaries: bool = True,
                 preserve_paragraphs: bool = True):
        """
        Initialize fallback chunker.
        
        Args:
            target_chunk_size: Target size for chunks (characters)
            min_chunk_size: Minimum acceptable chunk size
            max_chunk_size: Maximum acceptable chunk size
            overlap_size: Overlap between consecutive chunks
            prefer_sentence_boundaries: Prefer sentence boundaries over fixed-size
            preserve_paragraphs: Try to preserve paragraph integrity
        """
        self.target_chunk_size = target_chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.prefer_sentence_boundaries = prefer_sentence_boundaries
        self.preserve_paragraphs = preserve_paragraphs
        
        self.logger = logging.getLogger(__name__)
        self.sentence_tokenizer = SentenceTokenizer()
    
    def chunk_content(self,
                     text: str,
                     book_id: str,
                     metadata_base: Dict[str, any] = None) -> FallbackChunkingResult:
        """
        Chunk content using fallback strategy.
        
        Args:
            text: Text content to chunk
            book_id: Identifier for the book
            metadata_base: Base metadata to include in all chunks
            
        Returns:
            FallbackChunkingResult with chunks and metadata
        """
        self.logger.info(f"Starting fallback chunking for {len(text)} characters")
        
        if not text.strip():
            return FallbackChunkingResult(
                chunks=[], 
                metadata_list=[], 
                chunking_statistics={},
                warnings=["Empty text provided"]
            )
        
        metadata_base = metadata_base or {}
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        # Find sentence boundaries
        sentence_boundaries = []
        if self.prefer_sentence_boundaries:
            sentence_boundaries = self.sentence_tokenizer.tokenize_sentences(cleaned_text)
            self.logger.info(f"Found {len(sentence_boundaries)} sentence boundaries")
        
        # Find paragraph boundaries
        paragraph_boundaries = []
        if self.preserve_paragraphs:
            paragraph_boundaries = self._find_paragraph_boundaries(cleaned_text)
            self.logger.info(f"Found {len(paragraph_boundaries)} paragraph boundaries")
        
        # Create chunks using available boundaries
        chunks, boundary_stats = self._create_chunks_with_boundaries(
            cleaned_text, sentence_boundaries, paragraph_boundaries
        )
        
        # Create metadata for each chunk
        metadata_list = []
        for i, chunk in enumerate(chunks):
            metadata = self._create_chunk_metadata(
                chunk, f"{book_id}_fallback_{i}", book_id, i, metadata_base
            )
            metadata_list.append(metadata)
        
        # Calculate statistics
        statistics = self._calculate_chunking_statistics(chunks, metadata_list)
        
        # Generate warnings
        warnings = self._generate_warnings(chunks, statistics)
        
        self.logger.info(f"Fallback chunking complete: {len(chunks)} chunks created")
        
        return FallbackChunkingResult(
            chunks=chunks,
            metadata_list=metadata_list,
            chunking_statistics=statistics,
            warnings=warnings,
            sentence_boundaries_used=boundary_stats['sentence_boundaries'],
            word_boundaries_used=boundary_stats['word_boundaries']
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for chunking"""
        # Remove excessive whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        cleaned = re.sub(r' +', ' ', cleaned)
        
        # Remove page headers/footers (simple patterns)
        cleaned = re.sub(r'^Page \d+.*?\n', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\n.*?Page \d+.*?$', '', cleaned, flags=re.MULTILINE)
        
        # Remove excessive dashes or underscores (likely formatting artifacts)
        cleaned = re.sub(r'^[-_]{3,}.*?$', '', cleaned, flags=re.MULTILINE)
        
        return cleaned.strip()
    
    def _find_paragraph_boundaries(self, text: str) -> List[int]:
        """Find paragraph boundaries in text"""
        boundaries = []
        
        # Look for double newlines (paragraph breaks)
        for match in re.finditer(r'\n\s*\n', text):
            boundaries.append(match.end())
        
        # Look for indented paragraphs
        for match in re.finditer(r'\n\s{4,}[A-Z]', text):
            boundaries.append(match.start() + 1)
        
        return sorted(set(boundaries))
    
    def _create_chunks_with_boundaries(self,
                                     text: str,
                                     sentence_boundaries: List[SentenceBoundary],
                                     paragraph_boundaries: List[int]) -> Tuple[List[str], Dict[str, int]]:
        """Create chunks using sentence and paragraph boundaries"""
        chunks = []
        current_pos = 0
        boundary_stats = {'sentence_boundaries': 0, 'word_boundaries': 0, 'paragraph_boundaries': 0}
        
        # Create sorted list of all boundaries with types
        all_boundaries = []
        
        # Add sentence boundaries
        for sb in sentence_boundaries:
            all_boundaries.append((sb.position, 'sentence', sb.confidence))
        
        # Add paragraph boundaries
        for pb in paragraph_boundaries:
            all_boundaries.append((pb, 'paragraph', 1.0))
        
        # Sort by position
        all_boundaries.sort(key=lambda x: x[0])
        
        while current_pos < len(text):
            chunk_end = self._find_chunk_end(
                text, current_pos, all_boundaries, boundary_stats
            )
            
            # Apply overlap (but not for first chunk)
            chunk_start = current_pos
            if chunks and current_pos > 0:
                overlap_start = max(0, current_pos - self.overlap_size)
                chunk_start = self._find_word_boundary_before(text, overlap_start)
            
            # Extract chunk
            chunk_text = text[chunk_start:chunk_end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
            elif chunks:
                # Merge with previous chunk if too small
                chunks[-1] = (chunks[-1] + " " + chunk_text).strip()
            
            current_pos = chunk_end
        
        return chunks, boundary_stats
    
    def _find_chunk_end(self,
                       text: str,
                       start_pos: int,
                       boundaries: List[Tuple[int, str, float]],
                       stats: Dict[str, int]) -> int:
        """Find the best end position for a chunk"""
        target_end = start_pos + self.target_chunk_size
        max_end = min(len(text), start_pos + self.max_chunk_size)
        
        # If target end is beyond text, return text end
        if target_end >= len(text):
            return len(text)
        
        # Look for best boundary within acceptable range
        best_boundary = None
        best_score = -1
        
        for pos, boundary_type, confidence in boundaries:
            if start_pos + self.min_chunk_size <= pos <= max_end:
                # Score boundary based on type, confidence, and distance to target
                score = self._score_boundary_for_chunking(
                    pos, boundary_type, confidence, target_end
                )
                
                if score > best_score:
                    best_score = score
                    best_boundary = (pos, boundary_type)
        
        if best_boundary:
            stats[f"{best_boundary[1]}_boundaries"] += 1
            return best_boundary[0]
        
        # No good boundary found, use word boundary near target
        word_boundary = self._find_word_boundary_near(text, target_end)
        stats['word_boundaries'] += 1
        return word_boundary
    
    def _score_boundary_for_chunking(self,
                                   pos: int,
                                   boundary_type: str,
                                   confidence: float,
                                   target_pos: int) -> float:
        """Score a boundary for chunking quality"""
        # Base scores by boundary type
        type_scores = {
            'paragraph': 1.0,
            'sentence': 0.8,
            'word': 0.3
        }
        
        base_score = type_scores.get(boundary_type, 0.1)
        
        # Adjust by confidence
        confidence_adjusted = base_score * confidence
        
        # Adjust by distance from target (closer is better)
        distance = abs(pos - target_pos)
        max_distance = self.target_chunk_size * 0.5
        distance_penalty = min(0.5, distance / max_distance)
        
        final_score = confidence_adjusted * (1.0 - distance_penalty)
        return final_score
    
    def _find_word_boundary_near(self, text: str, target_pos: int) -> int:
        """Find word boundary near target position"""
        # Look for whitespace around target position
        search_start = max(0, target_pos - 50)
        search_end = min(len(text), target_pos + 50)
        
        # Prefer boundaries after target position
        for i in range(target_pos, search_end):
            if text[i].isspace():
                return i
        
        # Fall back to boundaries before target position
        for i in range(target_pos - 1, search_start - 1, -1):
            if text[i].isspace():
                return i + 1
        
        # Last resort: use target position
        return min(target_pos, len(text))
    
    def _find_word_boundary_before(self, text: str, pos: int) -> int:
        """Find word boundary at or before given position"""
        if pos >= len(text):
            return len(text)
        
        # If already at word boundary, return it
        if text[pos].isspace():
            return pos
        
        # Look backwards for word boundary
        for i in range(pos, max(0, pos - 100), -1):
            if i < len(text) and text[i].isspace():
                return i + 1
        
        return pos
    
    def _create_chunk_metadata(self,
                              chunk_text: str,
                              chunk_id: str,
                              book_id: str,
                              chunk_index: int,
                              metadata_base: Dict[str, any]) -> ChunkMetadata:
        """Create metadata for a fallback chunk"""
        
        # Determine content type (simple heuristics for fallback)
        content_type = self._determine_content_type(chunk_text)
        
        # Calculate basic metrics
        word_count = len(chunk_text.split())
        sentence_count = len(re.findall(r'[.!?]+', chunk_text))
        
        # Extract keywords (simple frequency-based)
        keywords = self._extract_keywords(chunk_text)
        
        # Estimate difficulty
        difficulty = self._estimate_difficulty(chunk_text, content_type)
        
        # Calculate confidence (lower for fallback chunking)
        confidence = self._calculate_chunk_confidence(chunk_text, word_count, sentence_count)
        
        metadata = ChunkMetadata(
            book_id=book_id,
            chunk_id=chunk_id,
            title=metadata_base.get('title', ''),
            subject=metadata_base.get('subject', ''),
            chapter='',  # No structure available
            section='',  # No structure available
            content_type=content_type,
            difficulty=difficulty,
            keywords=keywords,
            start_position=0,  # Would need full text context to calculate
            end_position=len(chunk_text),
            confidence_score=confidence,
            structure_quality=0.2,  # Low for fallback
            content_coherence=0.6,  # Moderate
            char_count=len(chunk_text),
            word_count=word_count,
            sentence_count=sentence_count,
            chunking_strategy="fallback"
        )
        
        # Add custom metadata
        for key, value in metadata_base.items():
            if key not in ['title', 'subject']:
                metadata.custom_metadata[key] = value
        
        return metadata
    
    def _determine_content_type(self, text: str) -> ContentType:
        """Determine content type using simple heuristics"""
        text_lower = text.lower()
        
        # Check for mathematical content
        math_indicators = ['equation', 'formula', '$', '∫', '∑', '∏', '∂', '∇', '≈', '≠', '≤', '≥']
        if any(indicator in text for indicator in math_indicators):
            return ContentType.MATH
        
        # Check for definitions
        def_indicators = ['definition:', 'define', 'is defined as', 'we define', 'by definition']
        if any(indicator in text_lower for indicator in def_indicators):
            return ContentType.DEFINITION
        
        # Check for examples
        example_indicators = ['example', 'for instance', 'consider', 'suppose', 'exercise', 'problem']
        if any(indicator in text_lower for indicator in example_indicators):
            return ContentType.EXAMPLE
        
        return ContentType.TEXT
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract keywords using simple frequency analysis"""
        # Stop words to exclude
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'this', 'that', 'these', 'those',
            'we', 'you', 'they', 'it', 'he', 'she', 'him', 'her', 'them', 'us'
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
    
    def _estimate_difficulty(self, text: str, content_type: ContentType) -> float:
        """Estimate content difficulty"""
        base_difficulty = 0.4  # Lower base for fallback (less structured content)
        
        # Adjust based on content type
        type_adjustments = {
            ContentType.MATH: 0.3,
            ContentType.DEFINITION: 0.2,
            ContentType.EXAMPLE: -0.1,
            ContentType.TEXT: 0.0
        }
        base_difficulty += type_adjustments.get(content_type, 0.0)
        
        # Text complexity indicators
        words = text.split()
        if words:
            avg_word_length = sum(len(word) for word in words) / len(words)
            if avg_word_length > 6:
                base_difficulty += 0.1
        
        # Sentence complexity
        sentences = re.split(r'[.!?]+', text)
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_sentence_length > 20:
                base_difficulty += 0.1
        
        return max(0.0, min(1.0, base_difficulty))
    
    def _calculate_chunk_confidence(self, text: str, word_count: int, sentence_count: int) -> float:
        """Calculate confidence in chunk quality"""
        confidence = 0.6  # Base confidence for fallback chunking (lower than content-aware)
        
        # Adjust based on chunk size appropriateness
        char_count = len(text)
        if self.min_chunk_size <= char_count <= self.max_chunk_size:
            confidence += 0.1
        elif char_count < self.min_chunk_size:
            confidence -= 0.2
        
        # Adjust based on sentence completeness
        if sentence_count > 0:
            if text.strip().endswith(('.', '!', '?')):
                confidence += 0.1
            else:
                confidence -= 0.1
        
        # Adjust based on word-to-sentence ratio
        if sentence_count > 0:
            words_per_sentence = word_count / sentence_count
            if 5 <= words_per_sentence <= 25:  # Reasonable range
                confidence += 0.05
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_chunking_statistics(self, 
                                     chunks: List[str], 
                                     metadata_list: List[ChunkMetadata]) -> Dict[str, any]:
        """Calculate statistics for fallback chunking"""
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
            'chunking_strategy': 'fallback',
            'size_variance': max(chunk_sizes) - min(chunk_sizes)
        }
    
    def _generate_warnings(self, chunks: List[str], statistics: Dict[str, any]) -> List[str]:
        """Generate warnings about chunking quality"""
        warnings = []
        
        if not chunks:
            warnings.append("No chunks created from input text")
            return warnings
        
        # Check for size issues
        avg_size = statistics.get('avg_chunk_size', 0)
        if avg_size < self.min_chunk_size * 1.2:
            warnings.append(f"Average chunk size ({avg_size:.0f}) is close to minimum threshold")
        
        if avg_size > self.max_chunk_size * 0.8:
            warnings.append(f"Average chunk size ({avg_size:.0f}) is close to maximum threshold")
        
        # Check for high variance in chunk sizes
        size_variance = statistics.get('size_variance', 0)
        if size_variance > self.target_chunk_size:
            warnings.append("High variance in chunk sizes - document may have uneven content distribution")
        
        # Check confidence levels
        avg_confidence = statistics.get('avg_confidence', 0)
        if avg_confidence < 0.5:
            warnings.append(f"Low average confidence ({avg_confidence:.2f}) - consider manual review")
        
        # Check for potential quality issues
        if len(chunks) < 3:
            warnings.append("Very few chunks created - document may be too short or uniform")
        elif len(chunks) > 50:
            warnings.append("Many chunks created - consider increasing target chunk size")
        
        return warnings