"""
Unit tests for ChunkMetadata class

Tests data validation, serialization/deserialization, and edge cases
with missing or invalid metadata fields.
"""

import pytest
import json
from datetime import datetime
from .chunk_metadata import (
    ChunkMetadata,
    ContentType,
    DifficultyLevel
)


class TestChunkMetadata:
    """Test suite for ChunkMetadata class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.basic_metadata = ChunkMetadata(
            book_id="test_book_001",
            chunk_id="chunk_001",
            title="Introduction to Python",
            subject="Computer Science",
            chapter="1",
            section="1.1"
        )
        
        self.complete_metadata = ChunkMetadata(
            book_id="advanced_book_002",
            chunk_id="chunk_advanced_001",
            title="Advanced Data Structures",
            subject="Computer Science",
            chapter="5",
            section="5.2",
            content_type=ContentType.DEFINITION,
            difficulty=0.8,
            keywords=["binary tree", "algorithm", "complexity"],
            topics=["data structures", "trees", "algorithms"],
            learning_objectives=["Understand binary trees", "Implement tree traversal"],
            page_numbers=[45, 46, 47],
            start_position=1000,
            end_position=1500,
            confidence_score=0.9,
            structure_quality=0.85,
            content_coherence=0.75,
            char_count=500,
            word_count=85,
            sentence_count=12,
            chunking_strategy="content_aware",
            custom_metadata={"author": "Jane Doe", "edition": "3rd"}
        )
    
    def test_basic_initialization(self):
        """Test basic metadata initialization"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        assert metadata.book_id == "book1"
        assert metadata.chunk_id == "chunk1"
        assert metadata.title == ""
        assert metadata.subject == ""
        assert metadata.content_type == ContentType.TEXT
        assert metadata.difficulty == 0.5
        assert metadata.confidence_score == 0.0
        assert isinstance(metadata.keywords, list)
        assert len(metadata.keywords) == 0
        assert isinstance(metadata.created_at, str)
    
    def test_required_field_validation(self):
        """Test validation of required fields"""
        # Missing book_id
        with pytest.raises(ValueError, match="book_id is required"):
            ChunkMetadata(book_id="", chunk_id="chunk1")
        
        # Missing chunk_id
        with pytest.raises(ValueError, match="chunk_id is required"):
            ChunkMetadata(book_id="book1", chunk_id="")
    
    def test_range_validation(self):
        """Test validation of numeric ranges"""
        # Test difficulty range
        with pytest.raises(ValueError, match="difficulty must be between 0.0 and 1.0"):
            ChunkMetadata(book_id="book1", chunk_id="chunk1", difficulty=1.5)
        
        with pytest.raises(ValueError, match="difficulty must be between 0.0 and 1.0"):
            ChunkMetadata(book_id="book1", chunk_id="chunk1", difficulty=-0.1)
        
        # Test confidence score range
        with pytest.raises(ValueError, match="confidence_score must be between 0.0 and 1.0"):
            ChunkMetadata(book_id="book1", chunk_id="chunk1", confidence_score=1.1)
        
        # Test position validation
        with pytest.raises(ValueError, match="end_position must be >= start_position"):
            ChunkMetadata(book_id="book1", chunk_id="chunk1", start_position=100, end_position=50)
        
        # Test negative counts
        with pytest.raises(ValueError, match="char_count must be non-negative"):
            ChunkMetadata(book_id="book1", chunk_id="chunk1", char_count=-1)
    
    def test_content_type_validation(self):
        """Test content type validation and conversion"""
        # Valid enum
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1", content_type=ContentType.MATH)
        assert metadata.content_type == ContentType.MATH
        
        # Valid string conversion
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1", content_type="definition")
        assert metadata.content_type == ContentType.DEFINITION
        
        # Invalid string
        with pytest.raises(ValueError, match="Invalid content_type"):
            ChunkMetadata(book_id="book1", chunk_id="chunk1", content_type="invalid_type")
    
    def test_difficulty_level_methods(self):
        """Test difficulty level categorical methods"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        # Test setting by level
        metadata.set_difficulty_level(DifficultyLevel.ADVANCED)
        assert metadata.get_difficulty_level() == DifficultyLevel.ADVANCED
        assert 0.5 <= metadata.difficulty < 0.75
        
        # Test level boundaries
        metadata.difficulty = 0.1
        assert metadata.get_difficulty_level() == DifficultyLevel.BEGINNER
        
        metadata.difficulty = 0.3
        assert metadata.get_difficulty_level() == DifficultyLevel.INTERMEDIATE
        
        metadata.difficulty = 0.9
        assert metadata.get_difficulty_level() == DifficultyLevel.EXPERT
    
    def test_keyword_management(self):
        """Test keyword addition and management"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        # Add keywords
        metadata.add_keyword("algorithm")
        metadata.add_keyword("data structure")
        assert "algorithm" in metadata.keywords
        assert "data structure" in metadata.keywords
        assert len(metadata.keywords) == 2
        
        # Don't add duplicates
        metadata.add_keyword("algorithm")
        assert len(metadata.keywords) == 2
        
        # Don't add empty strings
        metadata.add_keyword("")
        assert len(metadata.keywords) == 2
    
    def test_topic_management(self):
        """Test topic addition and management"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        metadata.add_topic("Computer Science")
        metadata.add_topic("Mathematics")
        assert len(metadata.topics) == 2
        
        # No duplicates
        metadata.add_topic("Computer Science")
        assert len(metadata.topics) == 2
    
    def test_learning_objective_management(self):
        """Test learning objective management"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        metadata.add_learning_objective("Understand algorithms")
        metadata.add_learning_objective("Implement data structures")
        assert len(metadata.learning_objectives) == 2
        
        # No duplicates
        metadata.add_learning_objective("Understand algorithms")
        assert len(metadata.learning_objectives) == 2
    
    def test_page_number_management(self):
        """Test page number management"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        # Add page numbers
        metadata.add_page_number(5)
        metadata.add_page_number(3)
        metadata.add_page_number(7)
        
        # Should be sorted
        assert metadata.page_numbers == [3, 5, 7]
        
        # No duplicates
        metadata.add_page_number(5)
        assert metadata.page_numbers == [3, 5, 7]
        
        # Don't add invalid page numbers
        metadata.add_page_number(0)
        metadata.add_page_number(-1)
        assert metadata.page_numbers == [3, 5, 7]
    
    def test_page_range_formatting(self):
        """Test page range string formatting"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        # No pages
        assert metadata.get_page_range() == "N/A"
        
        # Single page
        metadata.add_page_number(5)
        assert metadata.get_page_range() == "5"
        
        # Multiple pages
        metadata.add_page_number(7)
        metadata.add_page_number(6)
        assert metadata.get_page_range() == "5-7"
    
    def test_content_type_queries(self):
        """Test content type query methods"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        # Mathematical content
        metadata.content_type = ContentType.MATH
        assert metadata.is_mathematical_content() is True
        assert metadata.is_exercise_content() is False
        
        metadata.content_type = ContentType.FORMULA
        assert metadata.is_mathematical_content() is True
        
        # Exercise content
        metadata.content_type = ContentType.EXERCISE
        assert metadata.is_exercise_content() is True
        assert metadata.is_mathematical_content() is False
        
        metadata.content_type = ContentType.EXAMPLE
        assert metadata.is_exercise_content() is True
        
        # Regular text
        metadata.content_type = ContentType.TEXT
        assert metadata.is_mathematical_content() is False
        assert metadata.is_exercise_content() is False
    
    def test_hierarchical_path(self):
        """Test hierarchical path generation"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        # No chapter or section
        assert metadata.get_hierarchical_path() == "Root"
        
        # Chapter only
        metadata.chapter = "3"
        assert metadata.get_hierarchical_path() == "Ch.3"
        
        # Chapter and section
        metadata.section = "2"
        assert metadata.get_hierarchical_path() == "Ch.3 > Sec.2"
    
    def test_complexity_score_calculation(self):
        """Test complexity score calculation"""
        metadata = self.complete_metadata
        
        complexity = metadata.calculate_complexity_score()
        assert 0.0 <= complexity <= 1.0
        
        # High difficulty should increase complexity
        high_diff_metadata = ChunkMetadata(
            book_id="book1", chunk_id="chunk1",
            difficulty=0.9, confidence_score=0.1
        )
        high_complexity = high_diff_metadata.calculate_complexity_score()
        
        low_diff_metadata = ChunkMetadata(
            book_id="book1", chunk_id="chunk1",
            difficulty=0.1, confidence_score=0.9
        )
        low_complexity = low_diff_metadata.calculate_complexity_score()
        
        assert high_complexity > low_complexity
    
    def test_metrics_update(self):
        """Test metrics update method"""
        metadata = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        
        metadata.update_metrics(char_count=500, word_count=100, sentence_count=10)
        
        assert metadata.char_count == 500
        assert metadata.word_count == 100
        assert metadata.sentence_count == 10
        
        # Partial update
        metadata.update_metrics(word_count=120)
        assert metadata.char_count == 500  # Unchanged
        assert metadata.word_count == 120  # Updated
    
    def test_serialization_to_dict(self):
        """Test serialization to dictionary"""
        metadata = self.complete_metadata
        data_dict = metadata.to_dict()
        
        assert isinstance(data_dict, dict)
        assert data_dict['book_id'] == "advanced_book_002"
        assert data_dict['content_type'] == "definition"  # Should be string
        assert data_dict['keywords'] == ["binary tree", "algorithm", "complexity"]
        assert data_dict['custom_metadata']['author'] == "Jane Doe"
    
    def test_serialization_to_json(self):
        """Test JSON serialization"""
        metadata = self.complete_metadata
        json_str = metadata.to_json()
        
        assert isinstance(json_str, str)
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed['book_id'] == "advanced_book_002"
        assert parsed['content_type'] == "definition"
        
        # Test with indentation
        pretty_json = metadata.to_json(indent=2)
        assert "\\n" in pretty_json or "\n" in pretty_json
    
    def test_deserialization_from_dict(self):
        """Test deserialization from dictionary"""
        original = self.complete_metadata
        data_dict = original.to_dict()
        
        # Recreate from dict
        recreated = ChunkMetadata.from_dict(data_dict)
        
        assert recreated.book_id == original.book_id
        assert recreated.chunk_id == original.chunk_id
        assert recreated.content_type == original.content_type
        assert recreated.keywords == original.keywords
        assert recreated.custom_metadata == original.custom_metadata
    
    def test_deserialization_from_json(self):
        """Test deserialization from JSON"""
        original = self.complete_metadata
        json_str = original.to_json()
        
        # Recreate from JSON
        recreated = ChunkMetadata.from_json(json_str)
        
        assert recreated.book_id == original.book_id
        assert recreated.content_type == original.content_type
        assert recreated.difficulty == original.difficulty
        assert recreated.page_numbers == original.page_numbers
    
    def test_roundtrip_serialization(self):
        """Test complete roundtrip serialization"""
        original = self.complete_metadata
        
        # Dict roundtrip
        dict_recreated = ChunkMetadata.from_dict(original.to_dict())
        assert dict_recreated.to_dict() == original.to_dict()
        
        # JSON roundtrip
        json_recreated = ChunkMetadata.from_json(original.to_json())
        assert json_recreated.to_dict() == original.to_dict()
    
    def test_merge_functionality(self):
        """Test metadata merging"""
        metadata1 = ChunkMetadata(
            book_id="book1", chunk_id="chunk1",
            chapter="1", difficulty=0.3,
            keywords=["python", "basics"],
            page_numbers=[1, 2],
            char_count=100, word_count=20,
            confidence_score=0.8,
            structure_quality=0.7
        )
        
        metadata2 = ChunkMetadata(
            book_id="book1", chunk_id="chunk2",
            chapter="1", difficulty=0.7,
            keywords=["advanced", "python"],
            page_numbers=[2, 3],
            char_count=150, word_count=30,
            confidence_score=0.6,
            structure_quality=0.9
        )
        
        merged = metadata1.merge_with(metadata2)
        
        assert merged.book_id == "book1"
        assert merged.chunk_id == "chunk1+chunk2"
        assert merged.difficulty == 0.7  # Max of both
        assert set(merged.keywords) == {"python", "basics", "advanced"}  # Union
        assert merged.page_numbers == [1, 2, 3]  # Sorted union
        assert merged.char_count == 250  # Sum
        assert merged.confidence_score == 0.6  # Min (more conservative)
        assert merged.structure_quality == 0.8  # Average
    
    def test_merge_different_books_error(self):
        """Test error when merging chunks from different books"""
        metadata1 = ChunkMetadata(book_id="book1", chunk_id="chunk1")
        metadata2 = ChunkMetadata(book_id="book2", chunk_id="chunk2")
        
        with pytest.raises(ValueError, match="Cannot merge chunks from different books"):
            metadata1.merge_with(metadata2)
    
    def test_content_type_merge_priority(self):
        """Test content type merging priority"""
        text_metadata = ChunkMetadata(
            book_id="book1", chunk_id="chunk1",
            content_type=ContentType.TEXT
        )
        
        math_metadata = ChunkMetadata(
            book_id="book1", chunk_id="chunk2",
            content_type=ContentType.MATH
        )
        
        # Math should have priority over text
        merged = text_metadata.merge_with(math_metadata)
        assert merged.content_type == ContentType.MATH
        
        # Definition should have priority over text but not over math
        def_metadata = ChunkMetadata(
            book_id="book1", chunk_id="chunk3",
            content_type=ContentType.DEFINITION
        )
        
        merged_def_text = text_metadata.merge_with(def_metadata)
        assert merged_def_text.content_type == ContentType.DEFINITION
        
        merged_math_def = math_metadata.merge_with(def_metadata)
        assert merged_math_def.content_type == ContentType.MATH
    
    def test_consistency_validation(self):
        """Test internal consistency validation"""
        metadata = ChunkMetadata(
            book_id="book1", chunk_id="chunk1",
            start_position=0, end_position=100,
            char_count=100,  # Matches position range
            word_count=20,
            sentence_count=5
        )
        
        issues = metadata.validate_consistency()
        assert len(issues) == 0  # Should be consistent
        
        # Add inconsistency
        metadata.char_count = 200  # Doesn't match position range
        issues = metadata.validate_consistency()
        assert len(issues) > 0
        assert any("Character count" in issue for issue in issues)
        
        # Test unusual word-to-sentence ratio
        metadata.char_count = 100
        metadata.sentence_count = 50  # Too many sentences for word count
        issues = metadata.validate_consistency()
        assert any("word-to-sentence ratio" in issue for issue in issues)
    
    def test_edge_cases(self):
        """Test various edge cases"""
        # Minimal valid metadata
        minimal = ChunkMetadata(book_id="b", chunk_id="c")
        assert minimal.book_id == "b"
        assert minimal.chunk_id == "c"
        
        # Empty lists should work
        metadata = ChunkMetadata(
            book_id="book1", chunk_id="chunk1",
            keywords=[], topics=[], page_numbers=[]
        )
        assert len(metadata.keywords) == 0
        assert metadata.get_page_range() == "N/A"
        
        # Large values should work within ranges
        large_metadata = ChunkMetadata(
            book_id="book1", chunk_id="chunk1",
            difficulty=1.0, confidence_score=1.0,
            char_count=1000000, word_count=200000,
            sentence_count=50000
        )
        assert large_metadata.difficulty == 1.0
        assert large_metadata.char_count == 1000000
    
    def test_string_representations(self):
        """Test string representation methods"""
        metadata = self.complete_metadata
        
        # Test __str__
        str_repr = str(metadata)
        assert "chunk_advanced_001" in str_repr
        assert "definition" in str_repr
        assert "45-47" in str_repr  # Page range
        
        # Test __repr__
        repr_str = repr(metadata)
        assert "ChunkMetadata" in repr_str
        assert "advanced_book_002" in repr_str
        assert "chunk_advanced_001" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])