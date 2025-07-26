"""
Unit tests for FallbackChunker class

Tests with unstructured documents, PDFs with poor formatting,
validates sentence boundary detection and word boundary preservation.
"""

import pytest
from .fallback_chunker import (
    FallbackChunker,
    FallbackChunkingResult,
    SentenceTokenizer,
    SentenceBoundary
)
from .chunk_metadata import ContentType


class TestSentenceTokenizer:
    """Test sentence boundary detection"""
    
    def setup_method(self):
        self.tokenizer = SentenceTokenizer()
    
    def test_basic_sentence_detection(self):
        """Test basic sentence boundary detection"""
        text = "This is the first sentence. This is the second sentence! Is this a question?"
        
        boundaries = self.tokenizer.tokenize_sentences(text)
        
        assert len(boundaries) >= 2
        # Should detect sentence endings
        positions = [b.position for b in boundaries]
        assert any(pos > 20 and pos < 35 for pos in positions)  # After "first sentence."
        assert any(pos > 50 and pos < 70 for pos in positions)  # After "second sentence!"
    
    def test_abbreviation_handling(self):
        """Test that abbreviations don't break sentences incorrectly"""
        text = "Dr. Smith and Prof. Johnson published their research. The study was comprehensive."
        
        boundaries = self.tokenizer.tokenize_sentences(text)
        
        # Should not break after "Dr." or "Prof."
        for boundary in boundaries:
            context_before = boundary.context_before.lower()
            assert 'dr.' not in context_before[-3:] or boundary.confidence < 0.5
            assert 'prof.' not in context_before[-5:] or boundary.confidence < 0.5
    
    def test_mathematical_content_protection(self):
        """Test that mathematical content is not broken"""
        text = "The equation $E = mc^2$ is famous. It relates energy to mass."
        
        boundaries = self.tokenizer.tokenize_sentences(text)
        
        # Should not break within mathematical expressions
        for boundary in boundaries:
            pos = boundary.position
            # Check that boundary is not within $...$
            before_dollar = text[:pos].count('$')
            if before_dollar % 2 == 1:  # Odd number means we're inside math
                assert boundary.confidence < 0.5
    
    def test_academic_abbreviations(self):
        """Test handling of academic abbreviations"""
        text = "The authors (et al. 2023) found significant results. The data supports this conclusion."
        
        boundaries = self.tokenizer.tokenize_sentences(text)
        
        # Should not break after "et al."
        valid_boundaries = [b for b in boundaries if b.confidence > 0.5]
        
        # Should have at least one good boundary after the full citation
        assert len(valid_boundaries) >= 1
    
    def test_numbered_lists(self):
        """Test handling of numbered lists"""
        text = "Here are the steps: 1. First step. 2. Second step. 3. Final step."
        
        boundaries = self.tokenizer.tokenize_sentences(text)
        
        # Should not break after numbered items
        low_confidence = [b for b in boundaries if b.confidence < 0.5]
        
        # Some boundaries after numbers should have low confidence
        assert len(low_confidence) > 0


class TestFallbackChunker:
    """Test fallback chunking functionality"""
    
    def setup_method(self):
        self.chunker = FallbackChunker(
            target_chunk_size=400,  # Smaller for testing
            min_chunk_size=100,
            max_chunk_size=600,
            overlap_size=80
        )
        
        # Create sample unstructured content
        self.unstructured_text = """
        This is some poorly structured text that lacks clear chapter and section boundaries.
        The content flows continuously without obvious organizational markers.
        
        Sometimes there are paragraphs that discuss mathematical concepts like f(x) = x^2.
        These equations should be preserved as complete units during chunking.
        
        Definition: A variable is a named storage location. Variables can hold different types of data.
        This definition should ideally be kept together with its explanation.
        
        Here's another paragraph with more content. It discusses various programming concepts
        and techniques that students need to understand. The writing style is informal
        and educational.
        
        Example: Consider the case where x = 5. In this scenario, we would calculate
        the result as follows. Solution: The answer is 25 because 5 squared equals 25.
        
        The text continues with more educational content that needs to be chunked appropriately.
        Without clear structure markers, the fallback chunker must rely on sentence and
        paragraph boundaries to create meaningful chunks.
        
        Sometimes the content includes complex sentences with multiple clauses that could
        be challenging to parse correctly. The chunker should handle these gracefully.
        """
        
        # Create very long unstructured text for testing
        self.long_text = """
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor 
        incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis 
        nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
        
        Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore 
        eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt 
        in culpa qui officia deserunt mollit anim id est laborum.
        
        Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium 
        doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore 
        veritatis et quasi architecto beatae vitae dicta sunt explicabo.
        
        Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, 
        sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.
        
        Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, 
        adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et 
        dolore magnam aliquam quaerat voluptatem.
        """ * 5  # Repeat to make it longer
    
    def test_basic_fallback_chunking(self):
        """Test basic fallback chunking functionality"""
        result = self.chunker.chunk_content(
            text=self.unstructured_text,
            book_id="unstructured_book",
            metadata_base={"title": "Unstructured Content", "subject": "General"}
        )
        
        assert isinstance(result, FallbackChunkingResult)
        assert len(result.chunks) > 0
        assert len(result.metadata_list) == len(result.chunks)
        
        # Check that chunks respect minimum size
        for chunk in result.chunks:
            assert len(chunk) >= self.chunker.min_chunk_size
        
        # Check metadata
        for metadata in result.metadata_list:
            assert metadata.book_id == "unstructured_book"
            assert metadata.chunking_strategy == "fallback"
            assert metadata.title == "Unstructured Content"
            assert metadata.subject == "General"
            assert metadata.chapter == ""  # No structure available
            assert metadata.section == ""  # No structure available
    
    def test_empty_text_handling(self):
        """Test handling of empty text"""
        result = self.chunker.chunk_content(
            text="",
            book_id="empty_book"
        )
        
        assert len(result.chunks) == 0
        assert len(result.metadata_list) == 0
        assert len(result.warnings) > 0
        assert "Empty text" in result.warnings[0]
    
    def test_very_short_text(self):
        """Test handling of very short text"""
        short_text = "This is very short."
        
        result = self.chunker.chunk_content(
            text=short_text,
            book_id="short_book"
        )
        
        # Should either create no chunks (if below min) or one chunk
        if len(short_text) >= self.chunker.min_chunk_size:
            assert len(result.chunks) == 1
        else:
            assert len(result.chunks) == 0
    
    def test_sentence_boundary_chunking(self):
        """Test chunking that prefers sentence boundaries"""
        sentence_chunker = FallbackChunker(
            target_chunk_size=200,
            min_chunk_size=50,
            prefer_sentence_boundaries=True
        )
        
        text = ("This is the first sentence. " * 10 +
                "This is the second group of sentences. " * 10 +
                "This is the third group. " * 10)
        
        result = sentence_chunker.chunk_content(text, "sentence_book")
        
        # Should use sentence boundaries
        assert result.sentence_boundaries_used > 0
        
        # Chunks should end with sentence punctuation (mostly)
        sentence_endings = sum(1 for chunk in result.chunks 
                             if chunk.strip().endswith(('.', '!', '?')))
        assert sentence_endings >= len(result.chunks) * 0.7  # At least 70%
    
    def test_paragraph_preservation(self):
        """Test paragraph boundary preservation"""
        paragraph_text = """
        This is the first paragraph with several sentences. It discusses one main topic
        and should ideally be kept together as a coherent unit.
        
        This is the second paragraph that covers a different topic. It also has multiple
        sentences that form a cohesive unit of thought.
        
        The third paragraph continues the discussion. It provides additional information
        that builds on the previous paragraphs.
        """
        
        result = self.chunker.chunk_content(paragraph_text, "paragraph_book")
        
        # Should respect paragraph boundaries when possible
        if len(result.chunks) > 1:
            # Check that chunks don't break paragraphs unnaturally
            for chunk in result.chunks:
                # Chunks should generally start and end at paragraph-like boundaries
                assert not (chunk.startswith("and should") or chunk.startswith("that builds"))
    
    def test_mathematical_content_preservation(self):
        """Test preservation of mathematical content"""
        math_text = """
        Mathematical concepts are important. The equation f(x) = x^2 + 2x + 1 represents
        a quadratic function. When we solve this equation, we get specific results.
        
        Another equation is $E = mc^2$ which shows the relationship between energy and mass.
        These mathematical expressions should not be broken across chunk boundaries.
        """
        
        result = self.chunker.chunk_content(math_text, "math_book")
        
        # Mathematical content should be preserved
        combined_chunks = ' '.join(result.chunks)
        assert 'f(x) = x^2 + 2x + 1' in combined_chunks
        assert '$E = mc^2$' in combined_chunks
        
        # Check for math content type
        math_chunks = [m for m in result.metadata_list if m.content_type == ContentType.MATH]
        assert len(math_chunks) > 0
    
    def test_definition_detection(self):
        """Test detection of definitions in unstructured text"""
        def_text = """
        In programming, variables are important concepts to understand.
        Definition: A variable is a named location in memory that stores a value.
        Variables can be changed during program execution.
        
        Another important concept is functions. Functions are reusable blocks of code
        that perform specific tasks.
        """
        
        result = self.chunker.chunk_content(def_text, "definition_book")
        
        # Should detect definition content type
        def_chunks = [m for m in result.metadata_list if m.content_type == ContentType.DEFINITION]
        assert len(def_chunks) > 0
        
        # Definition should be preserved
        combined_chunks = ' '.join(result.chunks)
        assert 'Definition: A variable' in combined_chunks
    
    def test_example_detection(self):
        """Test detection of examples in unstructured text"""
        example_text = """
        Programming involves creating variables and using them in calculations.
        
        Example: To create a variable in Python, you write x = 5. This creates
        a variable named x with the value 5. You can then use this variable
        in calculations like y = x * 2.
        
        This shows how variables work in practice.
        """
        
        result = self.chunker.chunk_content(example_text, "example_book")
        
        # Should detect example content type
        example_chunks = [m for m in result.metadata_list if m.content_type == ContentType.EXAMPLE]
        assert len(example_chunks) > 0
    
    def test_chunk_overlap(self):
        """Test that chunks have appropriate overlap"""
        result = self.chunker.chunk_content(self.long_text, "overlap_book")
        
        if len(result.chunks) > 1:
            # Check for overlap between consecutive chunks
            overlaps_found = 0
            
            for i in range(len(result.chunks) - 1):
                chunk1 = result.chunks[i]
                chunk2 = result.chunks[i + 1]
                
                # Look for common words (indicating overlap)
                chunk1_words = set(chunk1.split()[-20:])  # Last 20 words
                chunk2_words = set(chunk2.split()[:20])   # First 20 words
                
                common_words = chunk1_words & chunk2_words
                if len(common_words) > 2:  # Reasonable overlap
                    overlaps_found += 1
            
            # Should have overlap in most consecutive chunks
            assert overlaps_found >= len(result.chunks) // 2
    
    def test_chunk_size_distribution(self):
        """Test chunk size distribution"""
        result = self.chunker.chunk_content(self.long_text, "size_book")
        
        chunk_sizes = [len(chunk) for chunk in result.chunks]
        
        # Most chunks should be within acceptable range
        in_range_count = sum(1 for size in chunk_sizes 
                           if self.chunker.min_chunk_size <= size <= self.chunker.max_chunk_size)
        
        assert in_range_count / len(chunk_sizes) >= 0.8  # At least 80% in range
        
        # Check statistics
        stats = result.chunking_statistics
        assert 'avg_chunk_size' in stats
        assert 'size_std_dev' in stats
        assert stats['total_chunks'] == len(result.chunks)
    
    def test_text_cleaning(self):
        """Test text cleaning functionality"""
        dirty_text = """
        Page 1
        
        This   is   text   with   excessive   whitespace.
        
        
        
        This has too many newlines.
        
        ___________________________
        
        This has formatting artifacts.
        
        Page 2 - Header
        
        More content here.
        """
        
        cleaned = self.chunker._clean_text(dirty_text)
        
        # Should remove excessive whitespace
        assert '   ' not in cleaned
        
        # Should reduce excessive newlines
        assert '\n\n\n' not in cleaned
        
        # Should remove page headers/footers
        assert 'Page 1' not in cleaned
        assert 'Page 2' not in cleaned
        
        # Should remove formatting artifacts
        assert '___' not in cleaned
    
    def test_word_boundary_preservation(self):
        """Test that word boundaries are preserved"""
        # Create text that would be split mid-word without proper boundaries
        boundary_text = "This is a supercalifragilisticexpialidocious word that should not be broken. " * 20
        
        result = self.chunker.chunk_content(boundary_text, "boundary_book")
        
        # Check that no chunk starts or ends mid-word
        for chunk in result.chunks:
            words = chunk.split()
            if words:
                # First and last words should be complete
                first_word = words[0]
                last_word = words[-1]
                
                # Simple check: words should not start/end with hyphens (incomplete)
                assert not first_word.startswith('-')
                assert not last_word.endswith('-')
    
    def test_confidence_scoring(self):
        """Test confidence scoring for fallback chunks"""
        result = self.chunker.chunk_content(self.unstructured_text, "confidence_book")
        
        # All confidence scores should be valid
        for metadata in result.metadata_list:
            assert 0.0 <= metadata.confidence_score <= 1.0
            # Fallback chunking should have moderate confidence
            assert 0.3 <= metadata.confidence_score <= 0.8
    
    def test_keyword_extraction(self):
        """Test keyword extraction from chunks"""
        keyword_text = """
        Programming is the process of creating software applications using various
        programming languages. Python is a popular programming language because
        of its simplicity and readability. Software development requires understanding
        of algorithms and data structures.
        """
        
        result = self.chunker.chunk_content(keyword_text, "keyword_book")
        
        # Check that keywords are extracted
        for metadata in result.metadata_list:
            assert isinstance(metadata.keywords, list)
            # Should extract relevant keywords
            if metadata.keywords:
                combined_keywords = ' '.join(metadata.keywords)
                # Should find programming-related terms
                assert any(term in combined_keywords 
                          for term in ['programming', 'python', 'software', 'development'])
    
    def test_difficulty_estimation(self):
        """Test difficulty estimation for different content"""
        # Simple text
        simple_text = "This is simple text with common words. It is easy to read."
        simple_result = self.chunker.chunk_content(simple_text, "simple")
        
        # Complex text
        complex_text = """
        The epistemological ramifications of quantum superposition necessitate
        a paradigmatic reconsideration of consciousness within the framework of
        phenomenological reductionism.
        """
        complex_result = self.chunker.chunk_content(complex_text, "complex")
        
        if simple_result.metadata_list and complex_result.metadata_list:
            simple_difficulty = simple_result.metadata_list[0].difficulty
            complex_difficulty = complex_result.metadata_list[0].difficulty
            
            # Complex text should have higher difficulty
            assert complex_difficulty >= simple_difficulty
    
    def test_chunking_statistics(self):
        """Test calculation of chunking statistics"""
        result = self.chunker.chunk_content(self.long_text, "stats_book")
        
        stats = result.chunking_statistics
        
        # Required statistics
        required_keys = [
            'total_chunks', 'avg_chunk_size', 'min_chunk_size', 'max_chunk_size',
            'total_characters', 'content_type_distribution', 'avg_confidence'
        ]
        
        for key in required_keys:
            assert key in stats
        
        # Values should make sense
        assert stats['total_chunks'] == len(result.chunks)
        assert stats['total_characters'] == sum(len(chunk) for chunk in result.chunks)
        assert 0.0 <= stats['avg_confidence'] <= 1.0
        assert stats['chunking_strategy'] == 'fallback'
    
    def test_warning_generation(self):
        """Test warning generation for quality issues"""
        # Test with very small chunks
        small_chunker = FallbackChunker(
            target_chunk_size=50,
            min_chunk_size=40,
            max_chunk_size=60
        )
        
        result = small_chunker.chunk_content(self.unstructured_text, "warning_book")
        
        # Should generate warnings about size issues
        warnings = result.warnings
        assert len(warnings) > 0
        
        # Check for specific warning types
        warning_text = ' '.join(warnings).lower()
        # Might warn about chunk sizes or confidence levels
        assert any(term in warning_text for term in ['size', 'confidence', 'variance', 'chunks'])
    
    def test_boundary_statistics(self):
        """Test tracking of boundary usage statistics"""
        result = self.chunker.chunk_content(self.unstructured_text, "boundary_stats")
        
        # Should track boundary usage
        assert hasattr(result, 'sentence_boundaries_used')
        assert hasattr(result, 'word_boundaries_used')
        
        # Should have used some boundaries
        total_boundaries = result.sentence_boundaries_used + result.word_boundaries_used
        assert total_boundaries > 0
    
    def test_large_document_handling(self):
        """Test handling of very large documents"""
        # Create a very large text
        large_text = self.long_text * 10  # Very long document
        
        result = self.chunker.chunk_content(large_text, "large_book")
        
        assert len(result.chunks) > 10  # Should create many chunks
        
        # All chunks should still respect size constraints
        for chunk in result.chunks:
            assert len(chunk) <= self.chunker.max_chunk_size * 1.1  # Allow small margin
    
    def test_edge_cases(self):
        """Test various edge cases"""
        # Text with only punctuation
        punct_text = "!!! ... ??? ... !!! ..."
        punct_result = self.chunker.chunk_content(punct_text, "punct")
        
        # Text with lots of numbers
        number_text = "123 456 789. 1.1 2.2 3.3. Version 1.0.1 and 2.0.3."
        number_result = self.chunker.chunk_content(number_text, "numbers")
        
        # Text with mixed languages/scripts (if any)
        mixed_text = "This is English. Ceci est français. Dies ist Deutsch."
        mixed_result = self.chunker.chunk_content(mixed_text, "mixed")
        
        # Should handle all cases without errors
        for result in [punct_result, number_result, mixed_result]:
            assert isinstance(result, FallbackChunkingResult)
            # May create chunks or not, but should not error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])