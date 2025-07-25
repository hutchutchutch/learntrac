"""
Text Cleaning and Normalization Pipeline

Implements comprehensive text cleaning functionality to correct missing spaces,
normalize whitespace, and handle special characters while preserving mathematical content.
"""

import re
import logging
import unicodedata
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class TextIssueType(Enum):
    """Types of text issues that can be detected and corrected"""
    MISSING_SPACES = "missing_spaces"
    EXCESS_WHITESPACE = "excess_whitespace"
    BROKEN_SENTENCES = "broken_sentences"
    MALFORMED_PARAGRAPHS = "malformed_paragraphs"
    SPECIAL_CHARACTERS = "special_characters"
    HEADER_FOOTER_ARTIFACTS = "header_footer_artifacts"


@dataclass
class CleaningStats:
    """Statistics from text cleaning process"""
    original_length: int
    cleaned_length: int
    spaces_added: int
    whitespace_normalized: int
    sentences_fixed: int
    paragraphs_restructured: int
    math_content_preserved: int
    artifacts_removed: int
    issues_detected: Dict[TextIssueType, int]


@dataclass
class CleaningResult:
    """Result from text cleaning operation"""
    cleaned_text: str
    stats: CleaningStats
    quality_score: float
    warnings: List[str]


class TextCleaner:
    """
    Advanced text cleaning and normalization system for PDF-extracted text.
    
    Features:
    - Intelligent space correction between concatenated words
    - Whitespace normalization while preserving paragraph structure
    - Mathematical content preservation
    - Special character and Unicode handling
    - Header/footer artifact removal
    - Sentence boundary correction
    - Quality scoring and validation
    """
    
    def __init__(self, preserve_mathematical: bool = True):
        """
        Initialize TextCleaner with configuration options.
        
        Args:
            preserve_mathematical: Whether to preserve mathematical expressions
        """
        self.preserve_mathematical = preserve_mathematical
        self.logger = logging.getLogger(__name__)
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile frequently used regex patterns for better performance"""
        
        # Mathematical content patterns
        self.math_patterns = [
            re.compile(r'\$[^$]+\$'),  # LaTeX inline math
            re.compile(r'\$\$[^$]+\$\$'),  # LaTeX display math
            re.compile(r'\\[a-zA-Z]+\{[^}]*\}'),  # LaTeX commands
            re.compile(r'[∫∑∏√≤≥≠±∓∞πα-ωΑ-Ω]'),  # Mathematical symbols
            re.compile(r'\b\d+\s*[+\-*/=±]\s*\d+\b'),  # Simple equations
            re.compile(r'\b(?:sin|cos|tan|log|ln|exp|lim|int|sum|prod|sqrt)\s*\([^)]+\)'),  # Math functions
        ]
        
        # Space correction patterns
        self.space_patterns = [
            # Between lowercase and uppercase (likely word boundaries)
            (re.compile(r'([a-z])([A-Z])'), r'\1 \2'),
            
            # Between letters and numbers
            (re.compile(r'([a-zA-Z])(\d)'), r'\1 \2'),
            (re.compile(r'(\d)([a-zA-Z])'), r'\1 \2'),
            
            # After punctuation without space
            (re.compile(r'([.!?])([A-Z])'), r'\1 \2'),
            (re.compile(r'\.([a-z])'), r'. \1'),
            (re.compile(r'([,;:])([A-Za-z])'), r'\1 \2'),
            
            # Around mathematical operators (but preserve in equations)
            (re.compile(r'([a-zA-Z])([+\-*/=])([a-zA-Z])'), r'\1 \2 \3'),
            
            # Between concatenated words (common pattern: wordWord)
            (re.compile(r'([a-z])([A-Z][a-z])'), r'\1 \2'),
            
            # After common abbreviations
            (re.compile(r'\b(Dr|Mr|Mrs|Ms|Prof|etc)\.([A-Z])'), r'\1. \2'),
        ]
        
        # Header/footer patterns
        self.artifact_patterns = [
            re.compile(r'^\s*Page\s+\d+\s*(of\s+\d+)?\s*$', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^\s*\d+\s*$', re.MULTILINE),  # Standalone page numbers
            re.compile(r'^\s*Chapter\s+\d+\s*$', re.MULTILINE),  # Isolated chapter headers
            re.compile(r'^\s*\d+\.\d+\s*$', re.MULTILINE),  # Section numbers only
            re.compile(r'Copyright\s+©?\s*\d{4}.*$', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^\s*\.{3,}\s*\d+\s*$', re.MULTILINE),  # Table of contents dots
        ]
        
        # Special character normalization
        self.char_replacements = {
            '"': '"',  # Smart quotes to regular
            '"': '"',
            ''': "'",
            ''': "'",
            '–': '-',  # En dash to hyphen
            '—': '-',  # Em dash to hyphen
            '…': '...',  # Ellipsis
            ' ': ' ',  # Non-breaking space
            '\u00A0': ' ',  # Another non-breaking space variant
        }
    
    def clean_text(self, text: str) -> CleaningResult:
        """
        Perform comprehensive text cleaning and normalization.
        
        Args:
            text: Raw text to clean
            
        Returns:
            CleaningResult with cleaned text and statistics
        """
        if not text or not text.strip():
            return CleaningResult(
                cleaned_text="",
                stats=CleaningStats(0, 0, 0, 0, 0, 0, 0, 0, {}),
                quality_score=0.0,
                warnings=["Input text is empty"]
            )
        
        original_length = len(text)
        warnings = []
        issues_detected = {issue: 0 for issue in TextIssueType}
        
        # Step 1: Preserve mathematical content
        math_placeholders, text_with_placeholders = self._preserve_mathematical_content(text)
        if math_placeholders:
            issues_detected[TextIssueType.SPECIAL_CHARACTERS] = len(math_placeholders)
        
        # Step 2: Normalize Unicode and special characters
        normalized_text = self._normalize_unicode(text_with_placeholders)
        
        # Step 3: Remove header/footer artifacts
        artifact_cleaned, artifacts_removed = self._remove_artifacts(normalized_text)
        issues_detected[TextIssueType.HEADER_FOOTER_ARTIFACTS] = artifacts_removed
        
        # Step 4: Correct missing spaces
        space_corrected, spaces_added = self._correct_missing_spaces(artifact_cleaned)
        issues_detected[TextIssueType.MISSING_SPACES] = spaces_added
        
        # Step 5: Normalize whitespace
        whitespace_normalized, whitespace_changes = self._normalize_whitespace(space_corrected)
        issues_detected[TextIssueType.EXCESS_WHITESPACE] = whitespace_changes
        
        # Step 6: Fix sentence boundaries
        sentence_fixed, sentences_fixed = self._fix_sentence_boundaries(whitespace_normalized)
        issues_detected[TextIssueType.BROKEN_SENTENCES] = sentences_fixed
        
        # Step 7: Restructure paragraphs
        paragraph_fixed, paragraphs_restructured = self._restructure_paragraphs(sentence_fixed)
        issues_detected[TextIssueType.MALFORMED_PARAGRAPHS] = paragraphs_restructured
        
        # Step 8: Restore mathematical content
        final_text = self._restore_mathematical_content(paragraph_fixed, math_placeholders)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(text, final_text, issues_detected)
        
        # Generate warnings for potential issues
        if quality_score < 0.5:
            warnings.append(f"Low quality score: {quality_score:.2f}")
        if len(final_text) < original_length * 0.5:
            warnings.append(f"Significant text reduction: {len(final_text)}/{original_length}")
        
        stats = CleaningStats(
            original_length=original_length,
            cleaned_length=len(final_text),
            spaces_added=spaces_added,
            whitespace_normalized=whitespace_changes,
            sentences_fixed=sentences_fixed,
            paragraphs_restructured=paragraphs_restructured,
            math_content_preserved=len(math_placeholders),
            artifacts_removed=artifacts_removed,
            issues_detected=issues_detected
        )
        
        self.logger.info(f"Text cleaning completed. Original: {original_length}, Cleaned: {len(final_text)}, Quality: {quality_score:.2f}")
        
        return CleaningResult(
            cleaned_text=final_text.strip(),
            stats=stats,
            quality_score=quality_score,
            warnings=warnings
        )
    
    def _preserve_mathematical_content(self, text: str) -> Tuple[Dict[str, str], str]:
        """Extract and preserve mathematical content with placeholders"""
        if not self.preserve_mathematical:
            return {}, text
        
        math_placeholders = {}
        modified_text = text
        placeholder_counter = 0
        
        for pattern in self.math_patterns:
            matches = pattern.findall(modified_text)
            for match in matches:
                placeholder = f"MATH_PLACEHOLDER_{placeholder_counter}"
                math_placeholders[placeholder] = match
                modified_text = modified_text.replace(match, placeholder, 1)
                placeholder_counter += 1
        
        return math_placeholders, modified_text
    
    def _restore_mathematical_content(self, text: str, placeholders: Dict[str, str]) -> str:
        """Restore mathematical content from placeholders"""
        restored_text = text
        for placeholder, original in placeholders.items():
            restored_text = restored_text.replace(placeholder, original)
        return restored_text
    
    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode characters and replace special characters"""
        # Normalize Unicode (NFKC normalization)
        normalized = unicodedata.normalize('NFKC', text)
        
        # Replace special characters
        for old_char, new_char in self.char_replacements.items():
            normalized = normalized.replace(old_char, new_char)
        
        return normalized
    
    def _remove_artifacts(self, text: str) -> Tuple[str, int]:
        """Remove common PDF artifacts like headers, footers, page numbers"""
        cleaned_text = text
        artifacts_removed = 0
        
        for pattern in self.artifact_patterns:
            matches = pattern.findall(cleaned_text)
            artifacts_removed += len(matches)
            cleaned_text = pattern.sub('', cleaned_text)
        
        return cleaned_text, artifacts_removed
    
    def _correct_missing_spaces(self, text: str) -> Tuple[str, int]:
        """Correct missing spaces between words using regex patterns"""
        corrected_text = text
        spaces_added = 0
        
        for pattern, replacement in self.space_patterns:
            original_len = len(corrected_text)
            corrected_text = pattern.sub(replacement, corrected_text)
            # Approximate count of spaces added
            new_len = len(corrected_text)
            if new_len > original_len:
                spaces_added += corrected_text.count(' ') - text.count(' ')
        
        # Additional heuristic: detect words that are likely concatenated
        # Look for patterns like "wordAnother" where case change indicates word boundary
        words = corrected_text.split()
        processed_words = []
        
        for word in words:
            # Skip if word contains mathematical placeholders
            if 'MATH_PLACEHOLDER' in word:
                processed_words.append(word)
                continue
            
            # Check for internal capitalization that suggests concatenation
            if len(word) > 3 and any(c.isupper() for c in word[1:]):
                # Split on capital letters that follow lowercase letters
                split_word = re.sub(r'([a-z])([A-Z])', r'\1 \2', word)
                if split_word != word:
                    spaces_added += split_word.count(' ') - word.count(' ')
                    processed_words.append(split_word)
                else:
                    processed_words.append(word)
            else:
                processed_words.append(word)
        
        return ' '.join(processed_words), max(0, spaces_added)
    
    def _normalize_whitespace(self, text: str) -> Tuple[str, int]:
        """Normalize whitespace while preserving paragraph structure"""
        original_whitespace_count = len(re.findall(r'\s+', text))
        
        # Replace multiple spaces/tabs with single space
        normalized = re.sub(r'[ \t]+', ' ', text)
        
        # Preserve paragraph breaks (double newlines)
        normalized = re.sub(r'\n\s*\n', '\n\n', normalized)
        
        # Remove excessive line breaks (more than 2)
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        
        # Clean up space around newlines
        normalized = re.sub(r' *\n *', '\n', normalized)
        
        # Trim each line but preserve structure
        lines = normalized.split('\n')
        trimmed_lines = [line.strip() for line in lines]
        
        # Remove empty lines except where they separate paragraphs
        cleaned_lines = []
        prev_empty = False
        for line in trimmed_lines:
            if line:
                cleaned_lines.append(line)
                prev_empty = False
            elif not prev_empty:  # Only keep one empty line
                cleaned_lines.append('')
                prev_empty = True
        
        final_text = '\n'.join(cleaned_lines)
        new_whitespace_count = len(re.findall(r'\s+', final_text))
        
        return final_text, max(0, original_whitespace_count - new_whitespace_count)
    
    def _fix_sentence_boundaries(self, text: str) -> Tuple[str, int]:
        """Fix broken sentence boundaries"""
        sentences_fixed = 0
        
        # Fix sentences that are split across lines
        lines = text.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            if not line.strip():
                fixed_lines.append(line)
                continue
            
            # If line doesn't end with sentence-ending punctuation and next line
            # starts with lowercase, they might be part of the same sentence
            if (i < len(lines) - 1 and 
                line.strip() and 
                not line.strip()[-1] in '.!?' and 
                lines[i + 1].strip() and 
                lines[i + 1].strip()[0].islower()):
                
                # Join with next line
                if i + 1 < len(lines):
                    combined = line.strip() + ' ' + lines[i + 1].strip()
                    fixed_lines.append(combined)
                    lines[i + 1] = ''  # Mark as processed
                    sentences_fixed += 1
                else:
                    fixed_lines.append(line)
            elif lines[i]:  # Only add non-empty lines that weren't processed
                fixed_lines.append(line)
        
        return '\n'.join(line for line in fixed_lines if line is not None), sentences_fixed
    
    def _restructure_paragraphs(self, text: str) -> Tuple[str, int]:
        """Restructure malformed paragraphs"""
        paragraphs_restructured = 0
        
        # Split into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        restructured_paragraphs = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Check if paragraph is too short (likely a fragment)
            lines = [line.strip() for line in paragraph.split('\n') if line.strip()]
            
            if len(lines) == 1 and len(lines[0]) < 50:
                # Very short single line - might be a heading or fragment
                restructured_paragraphs.append(paragraph.strip())
            elif len(lines) > 1:
                # Multiple lines - join them properly
                joined = ' '.join(lines)
                if joined != paragraph.strip():
                    paragraphs_restructured += 1
                restructured_paragraphs.append(joined)
            else:
                restructured_paragraphs.append(paragraph.strip())
        
        return '\n\n'.join(restructured_paragraphs), paragraphs_restructured
    
    def _calculate_quality_score(self, original: str, cleaned: str, issues: Dict[TextIssueType, int]) -> float:
        """Calculate quality score for cleaned text"""
        if not cleaned.strip():
            return 0.0
        
        base_score = 1.0
        
        # Penalize excessive changes
        length_ratio = len(cleaned) / len(original) if original else 0
        if length_ratio < 0.5:
            base_score -= 0.3  # Significant text loss
        elif length_ratio < 0.8:
            base_score -= 0.1  # Some text loss
        
        # Bonus for fixing issues
        total_issues = sum(issues.values())
        if total_issues > 0:
            base_score += min(0.2, total_issues * 0.01)  # Small bonus for fixes
        
        # Check for sentence structure
        sentences = len(re.findall(r'[.!?]+', cleaned))
        words = len(cleaned.split())
        if words > 0:
            sentence_ratio = sentences / words * 100
            if 5 <= sentence_ratio <= 20:  # Reasonable sentence to word ratio
                base_score += 0.1
        
        # Check for paragraph structure
        paragraphs = len(re.split(r'\n\s*\n', cleaned.strip()))
        if paragraphs > 1:
            base_score += 0.05
        
        return max(0.0, min(1.0, base_score))