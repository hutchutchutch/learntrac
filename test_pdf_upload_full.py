#!/usr/bin/env python3
"""
Test script to upload Introduction to Computer Science PDF to the LearnTrac API
Using the full processing pipeline through the authenticated endpoint
"""

import requests
import os
import sys
import time
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8001"
PDF_FILE = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/textbooks/Introduction_To_Computer_Science.pdf"

def test_full_pipeline():
    """Test the complete PDF processing pipeline"""
    
    # Check if file exists
    if not os.path.exists(PDF_FILE):
        print(f"Error: PDF file not found at {PDF_FILE}")
        sys.exit(1)
    
    # Get file size
    file_size = os.path.getsize(PDF_FILE) / (1024 * 1024)  # MB
    print(f"Uploading PDF: {Path(PDF_FILE).name}")
    print(f"File size: {file_size:.2f} MB")
    
    # First, let's check if the API is healthy
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
    
    # Try the upload endpoint directly without auth (since it's development mode)
    upload_url = f"{API_BASE_URL}/api/trac/textbooks/upload"
    
    # Prepare the multipart form data
    with open(PDF_FILE, 'rb') as f:
        files = {
            'file': (Path(PDF_FILE).name, f, 'application/pdf')
        }
        
        # Additional form data as query parameters (based on the API signature)
        params = {
            'title': 'Introduction to Computer Science',
            'subject': 'Computer Science'
        }
        
        # Make the request
        print("\nSending request to API...")
        print(f"URL: {upload_url}")
        
        start_time = time.time()
        
        try:
            response = requests.post(upload_url, files=files, params=params)
            
            elapsed_time = time.time() - start_time
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                print(f"\n✓ Upload successful! (took {elapsed_time:.2f} seconds)")
                print("\nResponse Details:")
                print("-" * 50)
                
                # Display the response in a structured way
                if isinstance(result, dict):
                    for key, value in result.items():
                        if key == 'statistics' and isinstance(value, dict):
                            print(f"\n{key}:")
                            for k, v in value.items():
                                print(f"  - {k}: {v}")
                        elif key == 'summary':
                            print(f"\n{key}:")
                            print(f"  {value}")
                        else:
                            print(f"{key}: {value}")
                else:
                    print(result)
                    
            else:
                print(f"\n✗ Upload failed with status code: {response.status_code}")
                print(f"Error: {response.text}")
                
                # If we get a 401/403, suggest using the dev endpoint
                if response.status_code in [401, 403]:
                    print("\nTip: The endpoint requires authentication. You might want to:")
                    print("1. Use the /api/trac/textbooks/upload-dev endpoint (no auth required)")
                    print("2. Or authenticate first using /api/trac/auth/login")
                
        except requests.exceptions.ConnectionError:
            print(f"\n✗ Error: Could not connect to API at {API_BASE_URL}")
            print("Make sure the API is running with: docker-compose up learntrac-api")
        except Exception as e:
            print(f"\n✗ Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()

def check_upload_status(textbook_id):
    """Check the status of an uploaded textbook"""
    print(f"\nChecking status of textbook: {textbook_id}")
    
    # Query the textbooks endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/api/trac/textbooks")
        if response.status_code == 200:
            textbooks = response.json().get('textbooks', [])
            for book in textbooks:
                if book.get('textbook_id') == textbook_id:
                    print(f"✓ Found textbook in database:")
                    print(f"  - Title: {book.get('title')}")
                    print(f"  - Chapters: {book.get('chapters')}")
                    print(f"  - Quality Score: {book.get('quality_score')}")
                    return True
        print("✗ Textbook not found in database")
        return False
    except Exception as e:
        print(f"✗ Error checking status: {e}")
        return False

if __name__ == "__main__":
    print("PDF Upload Full Pipeline Test")
    print("=" * 60)
    test_full_pipeline()
    
    # If successful, you can check the status
    # Example: check_upload_status("book_introduction_to_computer_science")