#!/usr/bin/env python3
"""
Simple test for vector search without authentication
"""

import requests
import json

def test_basic_functionality():
    """Test basic functionality without complex auth"""
    print("Testing basic functionality...")
    
    try:
        # Test textbook listing
        response = requests.get(
            "http://localhost:8001/api/trac/textbooks",
            headers={"Authorization": "Bearer test-token"},
            timeout=10
        )
        
        if response.status_code == 200:
            textbooks = response.json()
            print(f"Found {len(textbooks.get('textbooks', []))} textbooks")
            
            for textbook in textbooks.get('textbooks', [])[:3]:
                print(f"  - {textbook.get('title', 'Unknown')} (ID: {textbook.get('textbook_id', 'N/A')})")
        else:
            print(f"Error listing textbooks: {response.status_code}")
            
    except Exception as e:
        print(f"Exception: {e}")

def test_chunk_content():
    """Test getting specific chunk content"""
    print("\nTesting chunk content retrieval...")
    
    # Try to get a specific chunk (we'll guess at an ID)
    chunk_ids = [
        "textbook_8ee79876_ch1_s1.1_c0",
        "textbook_8ee79876_ch1_s1.2_c1", 
        "textbook_8ee79876_ch2_s2.1_c2"
    ]
    
    for chunk_id in chunk_ids:
        try:
            response = requests.get(
                f"http://localhost:8001/api/trac/content/{chunk_id}",
                headers={"Authorization": "Bearer test-token"},
                timeout=10
            )
            
            if response.status_code == 200:
                content = response.json()
                print(f"  Found chunk {chunk_id}")
                print(f"    Text preview: {content.get('text', '')[:100]}...")
                print(f"    Concepts: {content.get('concepts', [])[:3]}")
                break  # Found one, that's enough
            elif response.status_code == 404:
                print(f"  Chunk {chunk_id} not found")
            else:
                print(f"  Error {response.status_code} for chunk {chunk_id}")
                
        except Exception as e:
            print(f"  Exception for chunk {chunk_id}: {e}")

if __name__ == "__main__":
    test_basic_functionality()
    test_chunk_content()