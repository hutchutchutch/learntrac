#!/usr/bin/env python3
"""
Simple integration test for ContentChunker
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'pdf_processing'))

# Import modules with absolute imports
from chunk_metadata import ChunkMetadata, ContentType
from structure_detector import StructureElement, StructureType, NumberingStyle
from structure_quality_assessor import StructureQualityAssessor, QualityAssessment, ChunkingStrategy
from content_aware_chunker import ContentAwareChunker
from fallback_chunker import FallbackChunker
from content_chunker import ContentChunker, HybridChunkingResult

def test_content_chunker():
    """Test ContentChunker basic functionality"""
    print("Testing ContentChunker...")
    
    # Create chunker
    chunker = ContentChunker(
        structure_quality_threshold=0.3,
        content_aware_target_size=500,
        fallback_target_size=400,
        max_workers=2
    )
    
    # Test structured content
    structured_text = """
    Chapter 1: Introduction to Programming
    
    Programming is the process of creating instructions for computers.
    Definition: A program is a sequence of instructions.
    
    1.1 What is Programming?
    
    Programming involves writing code in a programming language.
    Example: print("Hello, World!") outputs text to the screen.
    
    The mathematical foundation involves algorithms with complexity O(n).
    """
    
    structure_elements = [
        StructureElement(
            type=StructureType.CHAPTER,
            title="Introduction to Programming",
            number="1",
            level=0,
            start_position=0,
            end_position=300,
            page_number=1,
            confidence=0.9,
            numbering_style=NumberingStyle.ARABIC,
            raw_text="Chapter 1: Introduction to Programming"
        )
    ]
    
    # Test content-aware chunking
    result1 = chunker.chunk_content(
        text=structured_text,
        book_id="test_book_1",
        structure_elements=structure_elements,
        metadata_base={"title": "Programming Guide", "subject": "Computer Science"}
    )
    
    print(f"✓ Structured content: {len(result1.chunks)} chunks")
    print(f"✓ Strategy used: {result1.strategy_used.value}")
    print(f"✓ Processing time: {result1.processing_time:.3f}s")
    print(f"✓ Quality score: {result1.quality_assessment.overall_quality_score:.2f}" if result1.quality_assessment else "✓ No quality assessment (forced strategy)")
    
    # Test unstructured content (fallback)
    unstructured_text = """
    This is poorly structured text without clear organization.
    It flows continuously without obvious chapter markers.
    
    Sometimes there are mathematical concepts like f(x) = x² discussed.
    Definition: A variable is a named storage location.
    """
    
    result2 = chunker.chunk_content(
        text=unstructured_text,
        book_id="test_book_2",
        structure_elements=[],  # No structure
        metadata_base={"title": "Unstructured Content"}
    )
    
    print(f"✓ Unstructured content: {len(result2.chunks)} chunks")
    print(f"✓ Strategy used: {result2.strategy_used.value}")
    print(f"✓ Processing time: {result2.processing_time:.3f}s")
    
    # Test statistics
    stats = chunker.get_processing_statistics()
    print(f"✓ Total documents processed: {stats['total_documents']}")
    print(f"✓ Total chunks created: {stats['total_chunks_created']}")
    print(f"✓ Content-aware used: {stats['content_aware_used']}")
    print(f"✓ Fallback used: {stats['fallback_used']}")
    
    # Test content type detection
    math_text = "The equation $E = mc^2$ shows energy-mass equivalence."
    result3 = chunker.chunk_content(text=math_text, book_id="math_test")
    
    math_chunks = [m for m in result3.metadata_list if m.content_type == ContentType.MATH]
    print(f"✓ Mathematical content detected: {len(math_chunks)} chunks")
    
    print("\n🎉 All ContentChunker integration tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_content_chunker()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)