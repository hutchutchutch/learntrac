"""
Unit tests for ContentAwareChunker class

Tests chunking with mathematical textbooks, verifies preservation of equations 
and definitions, and validates educational content coherence.
"""

import pytest
from .content_aware_chunker import (
    ContentAwareChunker,
    ChunkingResult,
    ChunkBoundary,
    MathematicalContentDetector,
    DefinitionDetector,
    ExampleDetector
)
from .chunk_metadata import ContentType
from .structure_detector import StructureElement, StructureType, NumberingStyle


class TestMathematicalContentDetector:
    """Test mathematical content detection"""
    
    def setup_method(self):
        self.detector = MathematicalContentDetector()
    
    def test_latex_detection(self):
        """Test LaTeX mathematical content detection"""
        text = "The formula $E = mc^2$ shows energy equivalence. Also $$\\int x dx = \\frac{x^2}{2}$$"
        
        regions = self.detector.find_mathematical_content(text)
        
        assert len(regions) >= 2
        # Should find inline math $E = mc^2$
        assert any('E = mc^2' in text[start:end] for start, end, _ in regions)
        # Should find display math
        assert any('int x dx' in text[start:end] for start, end, _ in regions)
    
    def test_mathematical_expressions(self):
        """Test mathematical expression detection"""
        text = "We have f(x) = x² + 2x - 1 and when x = 3, we get f(3) = 14."
        
        regions = self.detector.find_mathematical_content(text)
        
        assert len(regions) > 0
        # Should detect function notation
        assert any('f(x)' in text[start:end] for start, end, _ in regions)
    
    def test_greek_letters(self):
        """Test Greek letter detection"""
        text = "The angle θ = π/4 radians and α + β = γ."
        
        regions = self.detector.find_mathematical_content(text)
        
        assert len(regions) > 0
        # Should detect Greek letters
        found_text = ''.join(text[start:end] for start, end, _ in regions)
        assert 'θ' in found_text or 'π' in found_text
    
    def test_merge_overlapping_regions(self):
        """Test merging of overlapping mathematical regions"""
        # Simulate overlapping regions
        regions = [(10, 20, 'math'), (15, 25, 'equation'), (30, 40, 'formula')]
        
        merged = self.detector._merge_overlapping_regions(regions)
        
        assert len(merged) == 2  # First two should merge, third separate
        assert merged[0] == (10, 25, 'math+equation')
        assert merged[1] == (30, 40, 'formula')


class TestDefinitionDetector:
    """Test definition detection"""
    
    def setup_method(self):
        self.detector = DefinitionDetector()
    
    def test_explicit_definition(self):
        """Test detection of explicit definitions"""
        text = "Definition 1.1: A function is a relation where each input has exactly one output."
        
        definitions = self.detector.find_definitions(text)
        
        assert len(definitions) > 0
        assert any('function is a relation' in text[start:end] for start, end, _ in definitions)
    
    def test_implicit_definition(self):
        """Test detection of implicit definitions"""
        text = "A variable is a container for storing data values."
        
        definitions = self.detector.find_definitions(text)
        
        assert len(definitions) > 0
        assert any('variable' in text[start:end] for start, end, _ in definitions)
    
    def test_definition_with_explanation(self):
        """Test that definitions include their explanations"""
        text = ("Definition: An algorithm is a step-by-step procedure. "
               "It must be finite and produce a result. Each step must be clearly defined.")
        
        definitions = self.detector.find_definitions(text)
        
        assert len(definitions) > 0
        # Should include explanation
        def_text = text[definitions[0][0]:definitions[0][1]]
        assert 'step-by-step' in def_text
        assert 'finite' in def_text or 'clearly defined' in def_text


class TestExampleDetector:
    """Test example and exercise detection"""
    
    def setup_method(self):
        self.detector = ExampleDetector()
    
    def test_example_detection(self):
        """Test detection of examples"""
        text = "Example 1: Find the derivative of f(x) = x². Solution: f'(x) = 2x."
        
        examples = self.detector.find_examples(text)
        
        assert len(examples) > 0
        example_text = text[examples[0][0]:examples[0][1]]
        assert 'Example 1' in example_text
        assert 'Solution' in example_text
    
    def test_exercise_detection(self):
        """Test detection of exercises"""
        text = "Exercise 2.1: Solve the equation 2x + 3 = 7. Answer: x = 2."
        
        examples = self.detector.find_examples(text)
        
        assert len(examples) > 0
        exercise_text = text[examples[0][0]:examples[0][1]]
        assert 'Exercise' in exercise_text
        assert 'Answer' in exercise_text
    
    def test_example_without_solution(self):
        """Test example detection without explicit solution"""
        text = "For example, consider the case where x = 5. This gives us a specific instance."
        
        examples = self.detector.find_examples(text)
        
        assert len(examples) > 0
        example_text = text[examples[0][0]:examples[0][1]]
        assert 'For example' in example_text


class TestContentAwareChunker:
    """Test content-aware chunking functionality"""
    
    def setup_method(self):
        self.chunker = ContentAwareChunker(
            target_chunk_size=500,  # Smaller for testing
            min_chunk_size=100,
            max_chunk_size=800,
            overlap_size=50
        )
        
        # Create sample educational content
        self.sample_text = """
        Chapter 1: Introduction to Programming
        
        Programming is the process of creating instructions for computers to execute.
        Definition: A program is a sequence of instructions that tells a computer what to do.
        
        1.1 What is Programming?
        
        Programming involves writing code in a specific programming language.
        For example, consider this simple Python code: print("Hello, World!").
        This program outputs the text "Hello, World!" to the screen.
        
        The mathematical foundation involves algorithms with complexity O(n).
        We can express this as f(x) = x + 1 where x represents the input size.
        
        1.2 Programming Languages
        
        There are many programming languages available today.
        Each language has its own syntax and features.
        Python is known for its simplicity. Java is used for enterprise applications.
        C++ provides low-level control over hardware.
        
        Exercise 1.1: Write a program that prints your name.
        Solution: print("Your Name Here")
        
        Chapter 2: Variables and Data Types
        
        Variables are containers for storing data values.
        Definition: A variable is a named location in memory that stores a value.
        """
        
        # Create structure elements
        self.structure_elements = [
            StructureElement(
                type=StructureType.CHAPTER,
                title="Introduction to Programming",
                number="1",
                level=0,
                start_position=0,
                end_position=800,
                page_number=1,
                confidence=0.9,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="Chapter 1: Introduction to Programming"
            ),
            StructureElement(
                type=StructureType.SECTION,
                title="What is Programming?",
                number="1.1",
                level=1,
                start_position=200,
                end_position=600,
                page_number=1,
                confidence=0.8,
                numbering_style=NumberingStyle.DECIMAL,
                raw_text="1.1 What is Programming?"
            ),
            StructureElement(
                type=StructureType.SECTION,
                title="Programming Languages",
                number="1.2",
                level=1,
                start_position=600,
                end_position=1200,
                page_number=2,
                confidence=0.8,
                numbering_style=NumberingStyle.DECIMAL,
                raw_text="1.2 Programming Languages"
            ),
            StructureElement(
                type=StructureType.CHAPTER,
                title="Variables and Data Types",
                number="2",
                level=0,
                start_position=1200,
                end_position=len(self.sample_text),
                page_number=2,
                confidence=0.9,
                numbering_style=NumberingStyle.ARABIC,
                raw_text="Chapter 2: Variables and Data Types"
            )
        ]
    
    def test_basic_chunking(self):
        """Test basic content-aware chunking"""
        result = self.chunker.chunk_content(
            text=self.sample_text,
            structure_elements=self.structure_elements,
            book_id="test_book",
            metadata_base={"title": "Programming Basics", "subject": "Computer Science"}
        )
        
        assert isinstance(result, ChunkingResult)
        assert len(result.chunks) > 0
        assert len(result.metadata_list) == len(result.chunks)
        
        # Check that chunks respect minimum size
        for chunk in result.chunks:
            assert len(chunk) >= self.chunker.min_chunk_size
        
        # Check metadata
        for metadata in result.metadata_list:
            assert metadata.book_id == "test_book"
            assert metadata.chunking_strategy == "content_aware"
            assert metadata.title == "Programming Basics"
            assert metadata.subject == "Computer Science"
    
    def test_mathematical_content_preservation(self):
        """Test that mathematical content is preserved as complete units"""
        math_text = """
        The quadratic formula is $x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$.
        This formula solves equations of the form ax² + bx + c = 0.
        For example, when a=1, b=-3, c=2, we get x = 1 or x = 2.
        """
        
        result = self.chunker.chunk_content(
            text=math_text,
            structure_elements=[],
            book_id="math_book"
        )
        
        # Mathematical content should be preserved
        combined_chunks = ' '.join(result.chunks)
        assert '$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$' in combined_chunks
        assert 'ax² + bx + c = 0' in combined_chunks
        
        # Should have math content type
        math_chunks = [m for m in result.metadata_list if m.content_type == ContentType.MATH]
        assert len(math_chunks) > 0
    
    def test_definition_preservation(self):
        """Test that definitions are kept with their explanations"""
        def_text = """
        Definition 2.1: A function is a relation between sets.
        Each element in the domain maps to exactly one element in the codomain.
        This property distinguishes functions from general relations.
        
        Regular content continues here with other topics.
        """
        
        result = self.chunker.chunk_content(
            text=def_text,
            structure_elements=[],
            book_id="def_book"
        )
        
        # Find chunk containing definition
        def_chunks = [i for i, chunk in enumerate(result.chunks) 
                     if 'Definition 2.1' in chunk]
        assert len(def_chunks) > 0
        
        def_chunk_idx = def_chunks[0]
        def_chunk = result.chunks[def_chunk_idx]
        
        # Definition should include explanation
        assert 'relation between sets' in def_chunk
        assert 'domain maps to' in def_chunk or 'distinguishes functions' in def_chunk
        
        # Should have definition content type
        assert result.metadata_list[def_chunk_idx].content_type == ContentType.DEFINITION
    
    def test_example_preservation(self):
        """Test that examples are kept with their solutions"""
        example_text = """
        Example 3.1: Find the integral of f(x) = x².
        Solution: ∫x² dx = x³/3 + C, where C is the constant of integration.
        This follows from the power rule of integration.
        
        Next we consider a different function.
        """
        
        result = self.chunker.chunk_content(
            text=example_text,
            structure_elements=[],
            book_id="example_book"
        )
        
        # Find chunk containing example
        example_chunks = [i for i, chunk in enumerate(result.chunks) 
                         if 'Example 3.1' in chunk]
        assert len(example_chunks) > 0
        
        example_chunk_idx = example_chunks[0]
        example_chunk = result.chunks[example_chunk_idx]
        
        # Example should include solution
        assert 'Solution:' in example_chunk
        assert '∫x² dx' in example_chunk
        assert 'power rule' in example_chunk
        
        # Should have example content type
        assert result.metadata_list[example_chunk_idx].content_type == ContentType.EXAMPLE
    
    def test_structure_aware_chunking(self):
        """Test that chunking respects document structure"""
        result = self.chunker.chunk_content(
            text=self.sample_text,
            structure_elements=self.structure_elements,
            book_id="struct_book"
        )
        
        # Check that chapters and sections are reflected in metadata
        chapter_1_chunks = [m for m in result.metadata_list if m.chapter == "1"]
        chapter_2_chunks = [m for m in result.metadata_list if m.chapter == "2"]
        
        assert len(chapter_1_chunks) > 0
        assert len(chapter_2_chunks) > 0
        
        # Section information should be preserved
        section_chunks = [m for m in result.metadata_list if m.section in ["1.1", "1.2"]]
        assert len(section_chunks) > 0
    
    def test_chunk_overlap(self):
        """Test chunk overlap within sections"""
        long_text = "This is a long piece of text. " * 100  # Make it long enough for multiple chunks
        
        result = self.chunker.chunk_content(
            text=long_text,
            structure_elements=[],
            book_id="overlap_book"
        )
        
        if len(result.chunks) > 1:
            # Check for overlap between consecutive chunks
            for i in range(len(result.chunks) - 1):
                chunk1 = result.chunks[i]
                chunk2 = result.chunks[i + 1]
                
                # Look for common words at boundaries (indicating overlap)
                chunk1_words = chunk1.split()[-10:]  # Last 10 words
                chunk2_words = chunk2.split()[:10]   # First 10 words
                
                common_words = set(chunk1_words) & set(chunk2_words)
                # Should have some overlap for chunks in same section
                assert len(common_words) > 0 or len(chunk1) < self.chunker.target_chunk_size
    
    def test_chunk_size_distribution(self):
        """Test that chunk sizes fall within expected ranges"""
        result = self.chunker.chunk_content(
            text=self.sample_text,
            structure_elements=self.structure_elements,
            book_id="size_book"
        )
        
        chunk_sizes = [len(chunk) for chunk in result.chunks]
        
        # Most chunks should be within target range
        target_range_count = sum(1 for size in chunk_sizes 
                               if self.chunker.min_chunk_size <= size <= self.chunker.max_chunk_size)
        
        assert target_range_count / len(chunk_sizes) >= 0.8  # At least 80% in range
        
        # Check statistics
        stats = result.chunking_statistics
        assert 'avg_chunk_size' in stats
        assert 'total_chunks' in stats
        assert stats['total_chunks'] == len(result.chunks)
    
    def test_empty_text_handling(self):
        """Test handling of empty or very short text"""
        result = self.chunker.chunk_content(
            text="",
            structure_elements=[],
            book_id="empty_book"
        )
        
        assert len(result.chunks) == 0
        assert len(result.metadata_list) == 0
        
        # Very short text
        short_result = self.chunker.chunk_content(
            text="Short text.",
            structure_elements=[],
            book_id="short_book"
        )
        
        # Should still create a chunk if above minimum
        if len("Short text.") >= self.chunker.min_chunk_size:
            assert len(short_result.chunks) == 1
        else:
            assert len(short_result.chunks) == 0
    
    def test_no_structure_elements(self):
        """Test chunking without structure elements"""
        result = self.chunker.chunk_content(
            text=self.sample_text,
            structure_elements=[],
            book_id="no_struct_book"
        )
        
        assert len(result.chunks) > 0
        assert len(result.metadata_list) == len(result.chunks)
        
        # All chunks should have empty chapter/section
        for metadata in result.metadata_list:
            assert metadata.chapter == ""
            assert metadata.section == ""
    
    def test_protected_region_handling(self):
        """Test that protected regions are not split"""
        protected_text = """
        Here is some regular text that can be split normally.
        
        Definition: This is a definition that should not be split across chunks.
        It includes explanation that must stay together.
        
        More regular text that can be chunked.
        
        Example: Here is an example with solution.
        Solution: The answer is 42.
        
        Final regular text.
        """
        
        # Use very small target chunk size to force splitting
        small_chunker = ContentAwareChunker(
            target_chunk_size=100,
            min_chunk_size=50,
            max_chunk_size=200
        )
        
        result = small_chunker.chunk_content(
            text=protected_text,
            structure_elements=[],
            book_id="protected_book"
        )
        
        # Check that definition is not split
        def_chunks = [chunk for chunk in result.chunks if 'Definition:' in chunk]
        if def_chunks:
            def_chunk = def_chunks[0]
            assert 'should not be split' in def_chunk
            assert 'explanation' in def_chunk
        
        # Check that example with solution is not split
        example_chunks = [chunk for chunk in result.chunks if 'Example:' in chunk]
        if example_chunks:
            example_chunk = example_chunks[0]
            assert 'Solution:' in example_chunk
    
    def test_keyword_extraction(self):
        """Test keyword extraction from chunks"""
        result = self.chunker.chunk_content(
            text=self.sample_text,
            structure_elements=self.structure_elements,
            book_id="keyword_book"
        )
        
        # Check that keywords are extracted
        for metadata in result.metadata_list:
            assert isinstance(metadata.keywords, list)
            # Should have some keywords for non-empty chunks
            if len(result.chunks[result.metadata_list.index(metadata)]) > 100:
                assert len(metadata.keywords) > 0
    
    def test_difficulty_estimation(self):
        """Test difficulty estimation for different content types"""
        # Mathematical content should have higher difficulty
        math_text = "The integral ∫f(x)dx represents the area under the curve f(x)."
        math_result = self.chunker.chunk_content(
            text=math_text,
            structure_elements=[],
            book_id="math_book"
        )
        
        # Simple text should have lower difficulty
        simple_text = "This is simple text with common words and short sentences."
        simple_result = self.chunker.chunk_content(
            text=simple_text,
            structure_elements=[],
            book_id="simple_book"
        )
        
        if math_result.metadata_list and simple_result.metadata_list:
            math_difficulty = math_result.metadata_list[0].difficulty
            simple_difficulty = simple_result.metadata_list[0].difficulty
            
            # Math should generally be more difficult
            assert math_difficulty >= simple_difficulty - 0.1  # Allow some variance
    
    def test_confidence_scoring(self):
        """Test confidence scoring for chunks"""
        result = self.chunker.chunk_content(
            text=self.sample_text,
            structure_elements=self.structure_elements,
            book_id="confidence_book"
        )
        
        # All confidence scores should be valid
        for metadata in result.metadata_list:
            assert 0.0 <= metadata.confidence_score <= 1.0
            # Content-aware chunking should have reasonable confidence
            assert metadata.confidence_score >= 0.5
    
    def test_chunking_statistics(self):
        """Test calculation of chunking statistics"""
        result = self.chunker.chunk_content(
            text=self.sample_text,
            structure_elements=self.structure_elements,
            book_id="stats_book"
        )
        
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
        assert isinstance(stats['content_type_distribution'], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])