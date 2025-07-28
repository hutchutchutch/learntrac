#!/usr/bin/env python3
"""
Simple test for enhanced vector search API with authentication
"""

import requests
import json
from datetime import datetime

# API configuration
API_BASE_URL = "http://localhost:8001/api/learntrac"
VECTOR_SEARCH_ENHANCED_URL = f"{API_BASE_URL}/vector/search/enhanced"

# Test query
TEST_QUERY = {
    "query": "What are binary search trees?",
    "generate_sentences": 5,
    "min_score": 0.7,
    "limit": 10,
    "include_prerequisites": True,
    "include_generated_context": True
}

def test_enhanced_search():
    """Test the enhanced vector search endpoint"""
    print("🔍 Testing Enhanced Vector Search API")
    print("="*60)
    print(f"URL: {VECTOR_SEARCH_ENHANCED_URL}")
    print(f"Query: {TEST_QUERY['query']}")
    print("-"*60)
    
    try:
        # Make the request
        response = requests.post(
            VECTOR_SEARCH_ENHANCED_URL,
            json=TEST_QUERY,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success!")
            
            # Print response details
            print(f"\nSearch Method: {data.get('search_method', 'unknown')}")
            print(f"Results Found: {data.get('result_count', 0)}")
            
            # Show generated context if available
            if 'generated_context' in data:
                context = data['generated_context']
                print(f"\n📝 Generated Academic Context ({context.get('sentence_count', 0)} sentences):")
                for i, sentence in enumerate(context.get('sentences', []), 1):
                    print(f"  {i}. {sentence}")
                print(f"\nTotal Length: {context.get('total_length', 0)} characters")
            
            # Show results
            results = data.get('results', [])
            if results:
                print(f"\n📊 Top Results (showing up to 5):")
                for i, result in enumerate(results[:5], 1):
                    print(f"\n  Result {i}:")
                    print(f"    ID: {result.get('id')}")
                    print(f"    Score: {result.get('score', 0):.4f}")
                    print(f"    Content: {result.get('content', '')[:200]}...")
                    
                    # Show prerequisites if available
                    prereqs = result.get('prerequisites', [])
                    if prereqs:
                        print(f"    Prerequisites: {len(prereqs)} found")
                        for p in prereqs[:3]:
                            print(f"      - {p.get('id')}: {p.get('content', '')[:50]}...")
            else:
                print("\n⚠️  No results found")
            
            # Save full response
            filename = f"vector_search_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full response saved to: {filename}")
            
        elif response.status_code == 401:
            print("❌ Authentication required")
            print("Response:", response.text)
        elif response.status_code == 403:
            print("❌ Forbidden - insufficient permissions")
            print("Response:", response.text)
        else:
            print(f"❌ Error: {response.status_code}")
            print("Response:", response.text)
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_enhanced_search()