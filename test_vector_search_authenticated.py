#!/usr/bin/env python3
"""
Test enhanced vector search API with proper authentication for user 'hutch'
"""

import requests
import json
import os
from datetime import datetime
import base64
import hmac
import hashlib
import time

# API configuration
API_BASE_URL = "http://localhost:8001/api/learntrac"
TRAC_BASE_URL = "http://localhost:8000"
VECTOR_SEARCH_ENHANCED_URL = f"{API_BASE_URL}/vector/search/enhanced"

# Authentication methods
def get_trac_session_cookie(username="hutch", password="hutch"):
    """
    Get session cookie from Trac login
    """
    try:
        # Try to login to Trac to get session cookie
        login_url = f"{TRAC_BASE_URL}/login"
        session = requests.Session()
        
        # First, get the login page to get any CSRF tokens
        response = session.get(login_url)
        
        # Try basic auth
        response = session.post(
            login_url,
            auth=(username, password),
            allow_redirects=True
        )
        
        # Check for trac_auth cookie
        if 'trac_auth' in session.cookies:
            return session.cookies['trac_auth']
        
        return None
    except Exception as e:
        print(f"Failed to get Trac session: {e}")
        return None

def create_dev_session_token(username="hutch"):
    """
    Create a development session token (for testing only)
    This simulates what Trac would generate
    """
    # Development only - create a mock session token
    payload = {
        "user_id": username,
        "session_id": f"dev_session_{int(time.time())}",
        "expires_at": int(time.time()) + 3600,  # 1 hour from now
        "permissions": ["LEARNING_PARTICIPATE", "TICKET_VIEW", "WIKI_VIEW"],
        "groups": ["students"],
        "created_at": int(time.time())
    }
    
    # Encode payload
    payload_json = json.dumps(payload)
    payload_b64 = base64.b64encode(payload_json.encode('utf-8')).decode('ascii')
    
    # Create signature (in dev mode, we'll use a simple signature)
    # In production, this would use the shared secret
    secret = "dev_secret"  # This would need to match the API's trac_auth_secret
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{signature}"

def test_enhanced_search_with_auth(auth_method="bearer"):
    """
    Test the enhanced vector search endpoint with authentication
    
    auth_method: 'bearer', 'cookie', 'basic', or 'dev'
    """
    print("🔍 Testing Enhanced Vector Search API with Authentication")
    print("="*60)
    print(f"URL: {VECTOR_SEARCH_ENHANCED_URL}")
    print(f"Auth Method: {auth_method}")
    print(f"User: hutch")
    print("-"*60)
    
    # Prepare test query
    test_query = {
        "query": "What are binary search trees and how do they work?",
        "generate_sentences": 5,
        "min_score": 0.7,
        "limit": 10,
        "include_prerequisites": True,
        "include_generated_context": True
    }
    
    # Prepare headers based on auth method
    headers = {"Content-Type": "application/json"}
    cookies = {}
    
    if auth_method == "bearer":
        # Use Bearer token in Authorization header
        token = create_dev_session_token("hutch")
        headers["Authorization"] = f"Bearer {token}"
        print(f"Using Bearer token: {token[:50]}...")
        
    elif auth_method == "cookie":
        # Try to get real Trac session cookie
        trac_cookie = get_trac_session_cookie()
        if trac_cookie:
            cookies["trac_auth"] = trac_cookie
            print(f"Using Trac session cookie: {trac_cookie[:20]}...")
        else:
            # Fall back to dev token in cookie
            token = create_dev_session_token("hutch")
            cookies["trac_auth_token"] = token
            print(f"Using dev token in cookie: {token[:50]}...")
            
    elif auth_method == "basic":
        # Use Basic auth (dev mode only)
        auth_string = base64.b64encode(b"hutch:hutch").decode('ascii')
        headers["Authorization"] = f"Basic {auth_string}"
        print(f"Using Basic auth for user: hutch")
        
    elif auth_method == "dev":
        # Use X-API-Key header (if configured)
        headers["X-API-Key"] = "dev_api_key"
        print("Using development API key")
    
    try:
        # Make the request
        response = requests.post(
            VECTOR_SEARCH_ENHANCED_URL,
            json=test_query,
            headers=headers,
            cookies=cookies,
            timeout=60
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
                print(f"\nCombined Text Length: {context.get('total_length', 0)} characters")
            
            # Show results
            results = data.get('results', [])
            if results:
                print(f"\n📊 Search Results (showing top {min(5, len(results))}):")
                for i, result in enumerate(results[:5], 1):
                    print(f"\n  Result {i}:")
                    print(f"    ID: {result.get('id')}")
                    print(f"    Score: {result.get('score', 0):.4f}")
                    print(f"    Content Preview: {result.get('content', '')[:150]}...")
                    
                    # Show prerequisites if available
                    prereqs = result.get('prerequisites', [])
                    if prereqs:
                        print(f"    Prerequisites ({len(prereqs)} found):")
                        for j, p in enumerate(prereqs[:3], 1):
                            print(f"      {j}. {p.get('id')}: {p.get('content', '')[:50]}...")
                        if len(prereqs) > 3:
                            print(f"      ... and {len(prereqs) - 3} more prerequisites")
            else:
                print("\n⚠️  No results found")
            
            # Save full response
            filename = f"vector_search_auth_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full response saved to: {filename}")
            
        elif response.status_code == 401:
            print("❌ Authentication failed (401 Unauthorized)")
            print(f"Response: {response.text}")
            print("\nTrying to check auth status...")
            
            # Try to check auth endpoint
            auth_check = requests.get(
                f"{API_BASE_URL.replace('/learntrac', '')}/auth/status",
                headers=headers,
                cookies=cookies
            )
            if auth_check.status_code == 200:
                print("Auth system status:", json.dumps(auth_check.json(), indent=2))
                
        elif response.status_code == 403:
            print("❌ Access denied (403 Forbidden)")
            print(f"Response: {response.text}")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (60s)")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server at", API_BASE_URL)
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

def test_auth_debug():
    """Test the auth debug endpoint to understand what's expected"""
    print("\n🔍 Testing Auth Debug Endpoint")
    print("="*40)
    
    debug_url = f"{API_BASE_URL.replace('/learntrac', '')}/auth/debug"
    
    try:
        response = requests.get(debug_url)
        if response.status_code == 200:
            print("Auth Debug Info:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Debug endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"Failed to access debug endpoint: {e}")

if __name__ == "__main__":
    # First, try to understand the auth system
    test_auth_debug()
    
    print("\n" + "="*60 + "\n")
    
    # Test with different auth methods
    # Try bearer token first (most likely to work in dev mode)
    test_enhanced_search_with_auth("bearer")
    
    # Uncomment to try other methods:
    # print("\n" + "="*60 + "\n")
    # test_enhanced_search_with_auth("cookie")
    
    # print("\n" + "="*60 + "\n")
    # test_enhanced_search_with_auth("basic")
    
    # print("\n" + "="*60 + "\n")
    # test_enhanced_search_with_auth("dev")