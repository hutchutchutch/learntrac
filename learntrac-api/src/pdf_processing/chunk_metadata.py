"""
ChunkMetadata - Data structure for content chunk metadata

Provides comprehensive metadata for content chunks including educational context,
content classification, and quality metrics for the chunking system.
"""

import json
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime


class ContentType(Enum):
    """Types of educational content"""
    TEXT = "text"
    MATH = "math"
    DEFINITION = "definition"
    EXAMPLE = "example"
    EXERCISE = "exercise"
    SUMMARY = "summary"
    FIGURE_CAPTION = "figure_caption"
    TABLE = "table"
    CODE = "code"
    FORMULA = "formula"


class DifficultyLevel(Enum):
    """Educational difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class ChunkMetadata:
    """
    Comprehensive metadata for content chunks.
    
    Stores all relevant information about a content chunk including
    educational context, classification, and quality metrics.
    """
    
    # Required identification fields
    book_id: str
    chunk_id: str
    
    # Content identification
    title: str = ""
    subject: str = ""
    chapter: str = ""
    section: str = ""
    
    # Content classification
    content_type: ContentType = ContentType.TEXT
    difficulty: float = 0.5  # 0.0 (easiest) to 1.0 (hardest)
    
    # Semantic information
    keywords: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    
    # Physical location in document
    page_numbers: List[int] = field(default_factory=list)
    start_position: int = 0
    end_position: int = 0
    
    # Quality and confidence metrics
    confidence_score: float = 0.0  # 0.0 (low confidence) to 1.0 (high confidence)
    structure_quality: float = 0.0  # Quality of detected structure
    content_coherence: float = 0.0  # How coherent the chunk content is
    
    # Chunk characteristics
    char_count: int = 0
    word_count: int = 0
    sentence_count: int = 0
    
    # Relationships
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = field(default_factory=list)
    related_chunk_ids: List[str] = field(default_factory=list)
    
    # Processing metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    processing_version: str = "1.0"
    chunking_strategy: str = ""  # "content_aware" or "fallback"
    
    # Additional custom metadata
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate fields after initialization"""
        self._validate_required_fields()
        self._validate_ranges()
        self._validate_types()
    
    def _validate_required_fields(self) -> None:
        """Validate that required fields are provided"""
        if not self.book_id:
            raise ValueError("book_id is required")
        if not self.chunk_id:
            raise ValueError("chunk_id is required")
    
    def _validate_ranges(self) -> None:
        """Validate numeric ranges"""
        if not 0.0 <= self.difficulty <= 1.0:
            raise ValueError("difficulty must be between 0.0 and 1.0")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        if not 0.0 <= self.structure_quality <= 1.0:
            raise ValueError("structure_quality must be between 0.0 and 1.0")
        if not 0.0 <= self.content_coherence <= 1.0:
            raise ValueError("content_coherence must be between 0.0 and 1.0")
        if self.start_position < 0:
            raise ValueError("start_position must be non-negative")
        if self.end_position < self.start_position:
            raise ValueError("end_position must be >= start_position")
        if self.char_count < 0:
            raise ValueError("char_count must be non-negative")
        if self.word_count < 0:
            raise ValueError("word_count must be non-negative")
        if self.sentence_count < 0:
            raise ValueError("sentence_count must be non-negative")
    
    def _validate_types(self) -> None:
        """Validate field types"""
        if not isinstance(self.content_type, ContentType):
            if isinstance(self.content_type, str):
                try:
                    self.content_type = ContentType(self.content_type)
                except ValueError:
                    raise ValueError(f"Invalid content_type: {self.content_type}")
            else:
                raise ValueError("content_type must be ContentType enum or valid string")
        
        if not isinstance(self.keywords, list):
            raise ValueError("keywords must be a list")
        if not isinstance(self.topics, list):
            raise ValueError("topics must be a list")
        if not isinstance(self.page_numbers, list):
            raise ValueError("page_numbers must be a list")
    
    def get_difficulty_level(self) -> DifficultyLevel:
        """Get categorical difficulty level from numeric score"""
        if self.difficulty < 0.25:
            return DifficultyLevel.BEGINNER
        elif self.difficulty < 0.5:
            return DifficultyLevel.INTERMEDIATE
        elif self.difficulty < 0.75:
            return DifficultyLevel.ADVANCED
        else:
            return DifficultyLevel.EXPERT
    
    def set_difficulty_level(self, level: DifficultyLevel) -> None:
        """Set difficulty from categorical level"""
        level_map = {
            DifficultyLevel.BEGINNER: 0.125,
            DifficultyLevel.INTERMEDIATE: 0.375,
            DifficultyLevel.ADVANCED: 0.625,
            DifficultyLevel.EXPERT: 0.875
        }
        self.difficulty = level_map[level]
    
    def add_keyword(self, keyword: str) -> None:
        """Add a keyword if not already present"""
        if keyword and keyword not in self.keywords:
            self.keywords.append(keyword)
    
    def add_topic(self, topic: str) -> None:
        """Add a topic if not already present"""
        if topic and topic not in self.topics:
            self.topics.append(topic)
    
    def add_learning_objective(self, objective: str) -> None:
        """Add a learning objective if not already present"""
        if objective and objective not in self.learning_objectives:
            self.learning_objectives.append(objective)
    
    def add_page_number(self, page_num: int) -> None:
        """Add a page number if not already present"""
        if page_num > 0 and page_num not in self.page_numbers:
            self.page_numbers.append(page_num)
            self.page_numbers.sort()
    
    def get_page_range(self) -> str:
        """Get formatted page range string"""
        if not self.page_numbers:
            return "N/A"
        elif len(self.page_numbers) == 1:
            return str(self.page_numbers[0])
        else:
            return f"{min(self.page_numbers)}-{max(self.page_numbers)}"
    
    def is_mathematical_content(self) -> bool:
        """Check if chunk contains mathematical content"""
        return self.content_type in [ContentType.MATH, ContentType.FORMULA]
    
    def is_exercise_content(self) -> bool:
        """Check if chunk contains exercise content"""
        return self.content_type in [ContentType.EXERCISE, ContentType.EXAMPLE]
    
    def get_hierarchical_path(self) -> str:
        """Get hierarchical path as string"""
        parts = []
        if self.chapter:
            parts.append(f"Ch.{self.chapter}")
        if self.section:
            parts.append(f"Sec.{self.section}")
        return " > ".join(parts) if parts else "Root"
    
    def calculate_complexity_score(self) -> float:
        """Calculate overall complexity score from multiple factors"""
        factors = [
            self.difficulty,
            1.0 - self.confidence_score,  # Lower confidence = higher complexity
            self.structure_quality,  # Better structure may indicate more complex content
            min(1.0, len(self.keywords) / 10),  # More keywords may indicate complexity
            min(1.0, self.sentence_count / 20)  # More sentences may indicate complexity
        ]
        
        # Weighted average with emphasis on difficulty and confidence
        weights = [0.4, 0.3, 0.15, 0.1, 0.05]
        return sum(f * w for f, w in zip(factors, weights))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with enum values as strings"""
        data = asdict(self)
        data['content_type'] = self.content_type.value
        return data
    
    def to_json(self, indent: int = None) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChunkMetadata':
        """Create instance from dictionary"""
        # Handle enum conversion
        if 'content_type' in data and isinstance(data['content_type'], str):
            data['content_type'] = ContentType(data['content_type'])
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ChunkMetadata':
        """Create instance from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def update_metrics(self, 
                      char_count: int = None,
                      word_count: int = None,
                      sentence_count: int = None) -> None:
        """Update chunk metrics"""
        if char_count is not None:
            self.char_count = char_count
        if word_count is not None:
            self.word_count = word_count
        if sentence_count is not None:
            self.sentence_count = sentence_count
    
    def merge_with(self, other: 'ChunkMetadata') -> 'ChunkMetadata':
        """Create new metadata by merging with another chunk's metadata"""
        if self.book_id != other.book_id:
            raise ValueError("Cannot merge chunks from different books")
        
        # Create new merged metadata
        merged = ChunkMetadata(
            book_id=self.book_id,
            chunk_id=f"{self.chunk_id}+{other.chunk_id}",
            title=self.title or other.title,
            subject=self.subject or other.subject,
            chapter=self.chapter or other.chapter,
            section=self.section or other.section,
            content_type=self._merge_content_types(other.content_type),
            difficulty=max(self.difficulty, other.difficulty),
            keywords=list(set(self.keywords + other.keywords)),
            topics=list(set(self.topics + other.topics)),
            learning_objectives=list(set(self.learning_objectives + other.learning_objectives)),
            page_numbers=sorted(list(set(self.page_numbers + other.page_numbers))),
            start_position=min(self.start_position, other.start_position),
            end_position=max(self.end_position, other.end_position),
            confidence_score=min(self.confidence_score, other.confidence_score),
            structure_quality=(self.structure_quality + other.structure_quality) / 2,
            content_coherence=(self.content_coherence + other.content_coherence) / 2,
            char_count=self.char_count + other.char_count,
            word_count=self.word_count + other.word_count,
            sentence_count=self.sentence_count + other.sentence_count,
            chunking_strategy=f"{self.chunking_strategy}+{other.chunking_strategy}"
        )
        
        return merged
    
    def _merge_content_types(self, other_type: ContentType) -> ContentType:
        """Determine content type when merging chunks"""
        # Priority order for content types
        priority = {
            ContentType.MATH: 5,
            ContentType.FORMULA: 4,
            ContentType.DEFINITION: 3,
            ContentType.EXAMPLE: 3,
            ContentType.EXERCISE: 2,
            ContentType.TEXT: 1
        }
        
        self_priority = priority.get(self.content_type, 1)
        other_priority = priority.get(other_type, 1)
        
        return self.content_type if self_priority >= other_priority else other_type
    
    def validate_consistency(self) -> List[str]:
        """Validate internal consistency and return list of issues"""
        issues = []
        
        # Check position consistency
        expected_length = self.end_position - self.start_position
        if self.char_count > 0 and abs(expected_length - self.char_count) > self.char_count * 0.1:
            issues.append("Character count doesn't match position range")
        
        # Check word/sentence relationship
        if self.word_count > 0 and self.sentence_count > 0:
            words_per_sentence = self.word_count / self.sentence_count
            if words_per_sentence < 3 or words_per_sentence > 50:
                issues.append("Unusual word-to-sentence ratio")
        
        # Check page number consistency
        if self.page_numbers and self.start_position > 0:
            # This would need document-specific validation
            pass
        
        # Check difficulty vs content type consistency
        if self.content_type == ContentType.DEFINITION and self.difficulty < 0.3:
            issues.append("Definitions typically have higher difficulty")
        
        return issues
    
    def __str__(self) -> str:
        """String representation"""
        return (f"ChunkMetadata(id={self.chunk_id}, type={self.content_type.value}, "
                f"pages={self.get_page_range()}, difficulty={self.difficulty:.2f}, "
                f"confidence={self.confidence_score:.2f})")
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"ChunkMetadata(book_id='{self.book_id}', chunk_id='{self.chunk_id}', "
                f"chapter='{self.chapter}', section='{self.section}', "
                f"content_type={self.content_type}, difficulty={self.difficulty})")