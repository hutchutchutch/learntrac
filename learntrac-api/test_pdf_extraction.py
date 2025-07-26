#!/usr/bin/env python3
"""
Test PDF extraction to understand data format for Neo4j schema design
"""

import sys
import json
import os
sys.path.append('src')

from pdf_processing.pipeline import PDFProcessingPipeline
from pdf_processing.content_chunker import ContentChunker
from pdf_processing.embedding_pipeline import EmbeddingPipeline, PipelineConfig, DocumentInput

def test_pdf_extraction():
    """Test PDF extraction and examine the data structure"""
    
    pdf_path = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/textbooks/Introduction_To_Computer_Science.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF not found at: {pdf_path}")
        return
    
    print("=== Testing PDF Processing Pipeline ===\n")
    
    # Initialize pipeline
    pipeline = PDFProcessingPipeline(
        min_chapters=3,
        min_retention_ratio=0.5,
        quality_threshold=0.6,
        preserve_mathematical=True,
        aggressive_filtering=False
    )
    
    # Process PDF
    print(f"Processing: {pdf_path}")
    result = pipeline.process_pdf(pdf_path)
    
    print(f"\nProcessing Status: {result.status.value}")
    print(f"Quality Score: {result.quality_metrics.overall_quality_score:.2f}")
    print(f"\n{result.processing_summary}")
    
    # Examine structure elements
    print("\n=== Document Structure ===")
    print(f"Total structure elements: {len(result.structure_elements)}")
    
    if result.structure_elements:
        print("\nFirst 5 structure elements:")
        for i, element in enumerate(result.structure_elements[:5]):
            print(f"\n{i+1}. {element.element_type.upper()}")
            print(f"   Content: {element.content[:100]}...")
            print(f"   Level: {element.level}")
            print(f"   Position: {element.start_position}-{element.end_position}")
            if hasattr(element, 'metadata') and element.metadata:
                print(f"   Metadata: {element.metadata}")
    
    # Test chunking
    print("\n\n=== Testing Content Chunking ===")
    chunker = ContentChunker()
    
    if result.final_text:
        chunking_result = chunker.chunk_content(
            result.final_text,
            result.structure_elements,
            document_metadata={
                'title': result.metadata.file_path.split('/')[-1].replace('.pdf', ''),
                'source': 'textbook',
                'processing_date': str(result.metadata.processing_start_time)
            }
        )
        
        print(f"\nTotal chunks created: {chunking_result.total_chunks}")
        print(f"Average chunk size: {chunking_result.avg_chunk_size:.0f} chars")
        
        if chunking_result.chunks:
            print("\nFirst 3 chunks:")
            for i, chunk in enumerate(chunking_result.chunks[:3]):
                print(f"\n{i+1}. Chunk ID: {chunk.metadata.chunk_id}")
                print(f"   Content Type: {chunk.metadata.content_type.value}")
                print(f"   Text: {chunk.text[:150]}...")
                print(f"   Chapter: {chunk.metadata.chapter}")
                print(f"   Section: {chunk.metadata.section}")
                if chunk.metadata.concepts:
                    print(f"   Concepts: {chunk.metadata.concepts}")
    
    # Test embedding pipeline (just structure, not actual embeddings)
    print("\n\n=== Testing Embedding Pipeline Structure ===")
    
    if result.final_text and chunking_result.chunks:
        # Create document input for embedding pipeline
        doc_input = DocumentInput(
            document_id="intro_cs_test",
            text=result.final_text,
            title="Introduction to Computer Science",
            subject="Computer Science",
            structure_elements=result.structure_elements,
            metadata={
                'source': 'textbook',
                'chapters': result.metadata.chapters_detected,
                'sections': result.metadata.sections_detected
            }
        )
        
        print(f"Document prepared for embedding:")
        print(f"  ID: {doc_input.document_id}")
        print(f"  Title: {doc_input.title}")
        print(f"  Subject: {doc_input.subject}")
        print(f"  Structure Elements: {len(doc_input.structure_elements)}")
    
    # Save extracted data for analysis
    output_data = {
        'processing_result': {
            'status': result.status.value,
            'quality_score': result.quality_metrics.overall_quality_score,
            'chapters_detected': result.metadata.chapters_detected,
            'sections_detected': result.metadata.sections_detected,
            'text_length': len(result.final_text) if result.final_text else 0
        },
        'structure_elements': [
            {
                'type': elem.element_type,
                'content': elem.content[:200],
                'level': elem.level,
                'position': f"{elem.start_position}-{elem.end_position}"
            }
            for elem in result.structure_elements[:10]
        ] if result.structure_elements else [],
        'chunks_sample': [
            {
                'chunk_id': chunk.metadata.chunk_id,
                'content_type': chunk.metadata.content_type.value,
                'text_preview': chunk.text[:200],
                'chapter': chunk.metadata.chapter,
                'section': chunk.metadata.section,
                'concepts': chunk.metadata.concepts
            }
            for chunk in (chunking_result.chunks[:5] if 'chunking_result' in locals() and chunking_result.chunks else [])
        ]
    }
    
    with open('pdf_extraction_output.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print("\n\nExtraction data saved to pdf_extraction_output.json")
    print("\nThis data structure will inform the Neo4j schema design.")

if __name__ == "__main__":
    test_pdf_extraction()