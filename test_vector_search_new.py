#!/usr/bin/env python3
"""
Test vector search functionality
"""

import requests
import json

def test_vector_search():
    """Test the vector search functionality"""
    print("Testing vector search functionality...")
    
    # Test queries
    queries = [
        "What is an algorithm?",
        "computer programming basics",
        "data structures and arrays",
        "object-oriented programming"
    ]
    
    for query in queries:
        print(f"\nTesting query: '{query}'")
        
        try:
            # Test the search endpoint
            response = requests.post(
                "http://localhost:8001/api/trac/search",
                json={
                    "query": query,
                    "limit": 5
                },
                headers={"Authorization": "Bearer dummy-token"},  # Add dummy auth for now
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"  Found {len(results)} results")
                for i, result in enumerate(results[:3]):  # Show first 3 results
                    print(f"  {i+1}. Score: {result.get('score', 0):.3f}")
                    print(f"     Text: {result.get('text', '')[:100]}...")
                    print(f"     Chapter: {result.get('textbook_title', 'N/A')}")
            else:
                print(f"  Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"  Exception: {e}")

def test_graph_vector_search():
    """Test direct graph vector search using Cypher-like queries"""
    print("\nTesting direct graph queries for embeddings...")
    
    try:
        # Test for chunks with embeddings
        response = requests.get(
            "http://localhost:8001/api/trac/debug/graph-status",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total chunks in database: {data.get('node_counts', {}).get('Chunk', 0)}")
            print(f"Textbooks: {len(data.get('textbooks', []))}")
            
            # Look for our latest textbook
            textbooks = data.get('textbooks', [])
            latest_textbook = textbooks[-1] if textbooks else None
            if latest_textbook:
                print(f"Latest textbook: {latest_textbook['title']} (ID: {latest_textbook['id']})")
        else:
            print(f"Error getting graph status: {response.status_code}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_graph_vector_search()
    test_vector_search()