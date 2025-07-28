#!/usr/bin/env python3
"""
Test PDF upload through the API using curl commands
"""

import subprocess
import os
import json
import time

PDF_FILE = "/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/textbooks/Introduction_To_Computer_Science.pdf"
API_BASE = "http://localhost:8001"

def test_upload():
    """Test PDF upload through API"""
    
    print("Testing PDF Upload through API")
    print("=" * 60)
    
    # Check file exists
    if not os.path.exists(PDF_FILE):
        print(f"Error: PDF file not found at {PDF_FILE}")
        return
        
    file_size = os.path.getsize(PDF_FILE) / (1024 * 1024)
    print(f"PDF: {os.path.basename(PDF_FILE)}")
    print(f"Size: {file_size:.2f} MB")
    
    # First check API health
    print("\n1. Checking API health...")
    health_cmd = f"curl -s {API_BASE}/health"
    result = subprocess.run(health_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        health_data = json.loads(result.stdout)
        print(f"✓ API Status: {health_data.get('status', 'unknown')}")
    else:
        print("✗ API health check failed")
        return
    
    # Try the development endpoint (no auth required)
    print("\n2. Uploading PDF to development endpoint...")
    
    upload_cmd = f'''curl -X POST "{API_BASE}/api/trac/textbooks/upload-dev" \
        -H "accept: application/json" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@{PDF_FILE}"'''
    
    print("Command:", upload_cmd.replace(PDF_FILE, "...Introduction_To_Computer_Science.pdf"))
    
    start_time = time.time()
    result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start_time
    
    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            print(f"\n✓ Upload successful! (took {elapsed:.2f} seconds)")
            print("\nResponse:")
            print(json.dumps(response, indent=2))
            
            textbook_id = response.get('textbook_id')
            if textbook_id:
                print(f"\nTextbook ID: {textbook_id}")
                
                # Wait a moment for processing
                print("\n3. Checking textbook in database...")
                time.sleep(2)
                
                # Check if textbook exists in Neo4j
                check_neo4j(textbook_id)
                
        except json.JSONDecodeError:
            print(f"\n✗ Invalid JSON response: {result.stdout}")
    else:
        print(f"\n✗ Upload failed with return code: {result.returncode}")
        print(f"Error: {result.stderr}")
        print(f"Response: {result.stdout}")

def check_neo4j(textbook_id):
    """Check if textbook exists in Neo4j"""
    
    # Query Neo4j through the API
    neo4j_cmd = f'curl -s {API_BASE}/api/learntrac/vector/health'
    result = subprocess.run(neo4j_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            print(f"Neo4j Status: {data.get('status', 'unknown')}")
            
            if data.get('status') == 'healthy':
                print("✓ Neo4j connection is healthy")
                print("\nNote: The dev endpoint is a placeholder and doesn't actually process the PDF.")
                print("To fully process the PDF, we need to use the authenticated endpoint or run the processing directly.")
        except:
            print("Could not parse Neo4j status")

def test_authenticated_upload():
    """Test with the full authenticated endpoint"""
    
    print("\n" + "=" * 60)
    print("Testing Full PDF Processing Pipeline")
    print("=" * 60)
    
    # Since the endpoint is in development mode with auth commented out,
    # we can try calling it directly
    print("\n1. Attempting to upload to full processing endpoint...")
    
    upload_cmd = f'''curl -X POST "{API_BASE}/api/trac/textbooks/upload" \
        -H "accept: application/json" \
        -F "file=@{PDF_FILE}" \
        -F "title=Introduction to Computer Science" \
        -F "subject=Computer Science"'''
    
    print("Uploading with full processing pipeline...")
    start_time = time.time()
    result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start_time
    
    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            print(f"\n✓ Processing completed! (took {elapsed:.2f} seconds)")
            print("\nResponse:")
            print(json.dumps(response, indent=2))
            
            # Check statistics
            if 'statistics' in response:
                stats = response['statistics']
                print("\nProcessing Statistics:")
                print(f"  - Chapters: {stats.get('chapters', 0)}")
                print(f"  - Sections: {stats.get('sections', 0)}")
                print(f"  - Chunks: {stats.get('chunks', 0)}")
                print(f"  - Concepts: {stats.get('concepts', 0)}")
                
        except json.JSONDecodeError:
            print(f"\n✗ Invalid JSON response: {result.stdout}")
    else:
        print(f"\n✗ Processing failed")
        print(f"Status code: {result.returncode}")
        print(f"Response: {result.stdout}")
        
        # Check if it's an auth issue
        if "401" in result.stdout or "403" in result.stdout:
            print("\nThe endpoint requires authentication. The auth check might be enabled.")

if __name__ == "__main__":
    # Test development endpoint first
    test_upload()
    
    # Then try the full processing endpoint
    test_authenticated_upload()