#!/usr/bin/env python3
"""
Test script to upload Introduction to Computer Science PDF to the LearnTrac API
"""

import requests
import os
import sys
from pathlib import Path

# Configuration
API_URL = "http://localhost:8001/api/trac/textbooks/upload"
PDF_FILE = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/textbooks/Introduction_To_Computer_Science.pdf"

def upload_pdf():
    """Upload PDF to the API"""
    
    # Check if file exists
    if not os.path.exists(PDF_FILE):
        print(f"Error: PDF file not found at {PDF_FILE}")
        sys.exit(1)
    
    # Get file size
    file_size = os.path.getsize(PDF_FILE) / (1024 * 1024)  # MB
    print(f"Uploading PDF: {Path(PDF_FILE).name}")
    print(f"File size: {file_size:.2f} MB")
    
    # Prepare the multipart form data
    with open(PDF_FILE, 'rb') as f:
        files = {
            'file': (Path(PDF_FILE).name, f, 'application/pdf')
        }
        
        # Additional form data
        data = {
            'title': 'Introduction to Computer Science',
            'subject': 'Computer Science'
        }
        
        # Make the request
        print("\nSending request to API...")
        try:
            response = requests.post(API_URL, files=files, data=data)
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                print("\nUpload successful!")
                print(f"Response: {result}")
                
                # Extract key information
                if 'textbook_id' in result:
                    print(f"\nTextbook ID: {result['textbook_id']}")
                if 'nodes_created' in result:
                    print(f"Nodes created: {result['nodes_created']}")
                if 'processing_time' in result:
                    print(f"Processing time: {result['processing_time']:.2f} seconds")
                    
            else:
                print(f"\nUpload failed with status code: {response.status_code}")
                print(f"Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("\nError: Could not connect to API. Make sure the API is running on http://localhost:8001")
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")

if __name__ == "__main__":
    print("PDF Upload Test Script")
    print("=" * 50)
    upload_pdf()