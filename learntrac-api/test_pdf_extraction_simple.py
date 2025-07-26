#!/usr/bin/env python3
"""
Test PDF extraction to understand data format for Neo4j schema design
"""

import sys
import json
import os
sys.path.append('src')

from pdf_processing.pipeline import PDFProcessingPipeline

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
        print("\nFirst 10 structure elements:")
        for i, element in enumerate(result.structure_elements[:10]):
            print(f"\n{i+1}. {element.element_type.upper()}")
            print(f"   Content: {element.content[:100]}...")
            print(f"   Level: {element.level}")
            print(f"   Position: {element.start_position}-{element.end_position}")
            if hasattr(element, 'metadata') and element.metadata:
                print(f"   Metadata: {element.metadata}")
    
    # Look at chapter structure specifically
    chapters = [elem for elem in result.structure_elements if elem.element_type == 'chapter']
    sections = [elem for elem in result.structure_elements if elem.element_type == 'section']
    
    print(f"\n\n=== Chapter/Section Analysis ===")
    print(f"Chapters found: {len(chapters)}")
    print(f"Sections found: {len(sections)}")
    
    if chapters:
        print("\nChapters:")
        for i, chapter in enumerate(chapters[:5]):
            print(f"  {i+1}. {chapter.content}")
    
    # Examine text content
    if result.final_text:
        print(f"\n\n=== Text Content Analysis ===")
        print(f"Total text length: {len(result.final_text)} characters")
        print(f"First 500 characters:")
        print(result.final_text[:500])
        print("...")
    
    # Save extracted data for analysis
    output_data = {
        'processing_result': {
            'status': result.status.value,
            'quality_score': result.quality_metrics.overall_quality_score,
            'chapters_detected': result.metadata.chapters_detected,
            'sections_detected': result.metadata.sections_detected,
            'text_length': len(result.final_text) if result.final_text else 0,
            'extraction_method': result.metadata.pdf_processor_method
        },
        'structure_elements': [
            {
                'type': elem.element_type,
                'content': elem.content,
                'level': elem.level,
                'start_position': elem.start_position,
                'end_position': elem.end_position,
                'metadata': elem.metadata if hasattr(elem, 'metadata') else None
            }
            for elem in result.structure_elements
        ] if result.structure_elements else [],
        'quality_metrics': {
            'extraction_confidence': result.quality_metrics.extraction_confidence,
            'text_cleaning_score': result.quality_metrics.text_cleaning_score,
            'structure_detection_score': result.quality_metrics.structure_detection_score,
            'content_filtering_score': result.quality_metrics.content_filtering_score,
            'overall_quality_score': result.quality_metrics.overall_quality_score,
            'textbook_validity_score': result.quality_metrics.textbook_validity_score
        },
        'metadata': {
            'file_path': result.metadata.file_path,
            'file_size_bytes': result.metadata.file_size_bytes,
            'chapters_detected': result.metadata.chapters_detected,
            'sections_detected': result.metadata.sections_detected,
            'original_text_length': result.metadata.original_text_length,
            'cleaned_text_length': result.metadata.cleaned_text_length,
            'filtered_text_length': result.metadata.filtered_text_length
        }
    }
    
    with open('pdf_extraction_output.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print("\n\nExtraction data saved to pdf_extraction_output.json")
    print("\nThis data structure will inform the Neo4j schema design.")

if __name__ == "__main__":
    test_pdf_extraction()