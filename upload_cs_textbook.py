#!/usr/bin/env python3
"""
Upload Introduction to Computer Science PDF to Neo4j Aura
This script will process, chunk, embed, and store the PDF with all relationships
"""

import requests
import json
import time
import os
import sys
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8001"
PDF_FILE = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/textbooks/Introduction_To_Computer_Science.pdf"

def upload_textbook():
    """Upload and process the Computer Science textbook"""
    
    print("Processing Introduction to Computer Science Textbook")
    print("=" * 60)
    
    # Check if file exists
    if not os.path.exists(PDF_FILE):
        print(f"Error: PDF file not found at {PDF_FILE}")
        sys.exit(1)
    
    file_size = os.path.getsize(PDF_FILE) / (1024 * 1024)  # MB
    print(f"PDF File: {Path(PDF_FILE).name}")
    print(f"File Size: {file_size:.2f} MB")
    
    # Check API health first
    print("\n1. Checking API health...")
    try:
        health_response = requests.get(f"{API_BASE_URL}/health")
        if health_response.status_code == 200:
            print("✓ API is healthy")
        else:
            print("✗ API health check failed")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Cannot connect to API: {e}")
        sys.exit(1)
    
    # Upload the PDF to the processing endpoint
    upload_url = f"{API_BASE_URL}/api/trac/textbooks/upload"
    
    print("\n2. Uploading PDF for processing...")
    print(f"Endpoint: {upload_url}")
    
    # Prepare the multipart form data
    with open(PDF_FILE, 'rb') as f:
        files = {
            'file': ('Introduction_To_Computer_Science.pdf', f, 'application/pdf')
        }
        
        # Additional metadata
        data = {
            'title': 'Introduction to Computer Science',
            'subject': 'Computer Science'
        }
        
        print("\nMetadata:")
        print(f"  Title: {data['title']}")
        print(f"  Subject: {data['subject']}")
        
        # Make the request
        print("\nSending request (this may take a few minutes)...")
        start_time = time.time()
        
        try:
            response = requests.post(
                upload_url, 
                files=files, 
                data=data,
                timeout=600  # 10 minute timeout for large PDFs
            )
            
            elapsed_time = time.time() - start_time
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                print(f"\n✓ Upload and processing successful! (took {elapsed_time:.2f} seconds)")
                print("\n" + "=" * 60)
                print("Processing Results:")
                print("=" * 60)
                
                # Display results
                if 'success' in result:
                    print(f"\nSuccess: {result['success']}")
                
                if 'textbook_id' in result:
                    print(f"Textbook ID: {result['textbook_id']}")
                
                if 'statistics' in result:
                    stats = result['statistics']
                    print("\nStatistics:")
                    print(f"  - Chapters created: {stats.get('chapters', 0)}")
                    print(f"  - Sections created: {stats.get('sections', 0)}")
                    print(f"  - Chunks created: {stats.get('chunks', 0)}")
                    print(f"  - Concepts extracted: {stats.get('concepts', 0)}")
                    print(f"  - Processing time: {stats.get('processing_time', 0):.2f} seconds")
                
                if 'summary' in result:
                    print(f"\nSummary:\n{result['summary']}")
                
                # Save the textbook ID for later use
                if 'textbook_id' in result:
                    with open('last_upload.json', 'w') as f:
                        json.dump({
                            'textbook_id': result['textbook_id'],
                            'title': data['title'],
                            'upload_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'statistics': result.get('statistics', {})
                        }, f, indent=2)
                    print("\n✓ Upload details saved to last_upload.json")
                
                return result.get('textbook_id')
                
            else:
                print(f"\n✗ Upload failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                
                # Try to parse error details
                try:
                    error_data = response.json()
                    if 'detail' in error_data:
                        print(f"\nError details: {error_data['detail']}")
                except:
                    pass
                
        except requests.exceptions.Timeout:
            print(f"\n✗ Request timed out after {elapsed_time:.2f} seconds")
            print("The PDF may be too large or processing is taking longer than expected")
        except requests.exceptions.ConnectionError:
            print(f"\n✗ Error: Could not connect to API at {API_BASE_URL}")
            print("Make sure the API is running")
        except Exception as e:
            print(f"\n✗ Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return None

def verify_upload(textbook_id):
    """Verify the textbook was uploaded and processed correctly"""
    
    print(f"\n3. Verifying upload for textbook ID: {textbook_id}")
    
    # Query textbooks endpoint
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/trac/textbooks",
            params={'limit': 100}
        )
        
        if response.status_code == 200:
            data = response.json()
            textbooks = data.get('textbooks', [])
            
            for book in textbooks:
                if book.get('textbook_id') == textbook_id:
                    print("\n✓ Textbook found in database:")
                    print(f"  - Title: {book.get('title')}")
                    print(f"  - Subject: {book.get('subject')}")
                    print(f"  - Chapters: {book.get('chapters')}")
                    print(f"  - Quality Score: {book.get('quality_score')}")
                    print(f"  - Processing Date: {book.get('processing_date')}")
                    return True
            
            print("✗ Textbook not found in database listing")
        else:
            print(f"✗ Failed to query textbooks: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error verifying upload: {e}")
    
    return False

def test_vector_search(textbook_id=None):
    """Test vector search on the uploaded content"""
    
    print("\n4. Testing vector search on uploaded content...")
    
    test_queries = [
        "What is computer science?",
        "Programming fundamentals",
        "Data structures and algorithms",
        "Computer architecture",
        "Software engineering principles"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        
        search_payload = {
            "query": query,
            "min_score": 0.7,
            "limit": 3,
            "include_prerequisites": True,
            "include_dependents": False
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/learntrac/vector/search",
                json=search_payload
            )
            
            if response.status_code == 200:
                results = response.json()
                
                if results.get('count', 0) > 0:
                    print(f"  Found {results['count']} results:")
                    
                    for i, result in enumerate(results.get('results', [])[:3], 1):
                        print(f"\n  {i}. Score: {result.get('score', 0):.4f}")
                        print(f"     Chunk ID: {result.get('id', 'N/A')}")
                        text_preview = result.get('text', '')[:150]
                        print(f"     Text: {text_preview}...")
                        
                        # Show prerequisites if available
                        if 'prerequisites' in result and result['prerequisites']:
                            print(f"     Prerequisites: {len(result['prerequisites'])} found")
                else:
                    print("  No results found")
                    
            else:
                print(f"  Search failed: {response.status_code}")
                
        except Exception as e:
            print(f"  Search error: {e}")

def main():
    print("LearnTrac PDF Upload Script")
    print("Upload and process Introduction to Computer Science textbook")
    print("=" * 60)
    
    # Upload the textbook
    textbook_id = upload_textbook()
    
    if textbook_id:
        # Verify the upload
        if verify_upload(textbook_id):
            # Test vector search
            test_vector_search(textbook_id)
            
            print("\n" + "=" * 60)
            print("✓ PDF processing completed successfully!")
            print(f"✓ Textbook ID: {textbook_id}")
            print("✓ Content is now searchable through vector similarity")
            print("\nThe textbook has been:")
            print("  - Parsed into chapters and sections")
            print("  - Chunked into manageable pieces")
            print("  - Embedded using OpenAI embeddings")
            print("  - Stored in Neo4j with proper relationships")
            print("  - Indexed for vector similarity search")
        else:
            print("\n⚠️ Upload succeeded but verification failed")
            print("The textbook may still be processing")
    else:
        print("\n✗ Upload failed")
        print("Please check the error messages above")

if __name__ == "__main__":
    main()