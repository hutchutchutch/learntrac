#!/usr/bin/env python3
"""Test authentication and LearnTrac access"""

import requests
import sys

def test_auth():
    base_url = "http://localhost:8000/projects"
    
    # Test 1: Access wiki without authentication
    print("1. Testing access without authentication...")
    response = requests.get(f"{base_url}/wiki/LearnTrac")
    print(f"   Status: {response.status_code}")
    if "login" in response.text.lower() or "please" in response.text.lower():
        print("   ✓ Authentication check working - login required")
    else:
        print("   ✗ No authentication check found")
    
    # Test 2: Try to login
    print("\n2. Testing login...")
    session = requests.Session()
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    # First get the login page
    login_response = session.get(f"{base_url}/login")
    print(f"   Login page status: {login_response.status_code}")
    
    # Post login credentials
    login_post = session.post(f"{base_url}/login", data=login_data)
    print(f"   Login POST status: {login_post.status_code}")
    
    # Test 3: Access LearnTrac with session
    print("\n3. Testing authenticated access...")
    wiki_response = session.get(f"{base_url}/wiki/LearnTrac")
    print(f"   Wiki page status: {wiki_response.status_code}")
    
    if "PDFUpload" in wiki_response.text or "LearnTrac" in wiki_response.text:
        print("   ✓ LearnTrac macro found in page")
    else:
        print("   ✗ LearnTrac macro not found")
    
    # Save response for debugging
    with open("auth_test_response.html", "w") as f:
        f.write(wiki_response.text)
        print("\n   Response saved to auth_test_response.html")

if __name__ == "__main__":
    test_auth()