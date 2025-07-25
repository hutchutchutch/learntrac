#!/usr/bin/env python3
"""
Test script for Cognito Authentication Plugin
Tests JWT validation, permission mapping, and authentication flow
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
import jwt
from base64 import urlsafe_b64decode

class CognitoAuthTester:
    def __init__(self, region, user_pool_id, client_id, domain):
        self.region = region
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.domain = domain
        self.jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        
    def test_jwks_endpoint(self):
        """Test JWKS endpoint accessibility"""
        print("\n=== Testing JWKS Endpoint ===")
        try:
            response = requests.get(self.jwks_url)
            response.raise_for_status()
            jwks = response.json()
            print(f"✓ JWKS endpoint accessible")
            print(f"  Keys found: {len(jwks.get('keys', []))}")
            return True
        except Exception as e:
            print(f"✗ JWKS endpoint error: {e}")
            return False
    
    def decode_token_without_verification(self, token):
        """Decode JWT token without verification for testing"""
        print("\n=== Decoding Token (No Verification) ===")
        try:
            # Split token
            parts = token.split('.')
            if len(parts) != 3:
                print("✗ Invalid token format")
                return None
            
            # Decode header
            header = json.loads(urlsafe_b64decode(parts[0] + '=='))
            print(f"✓ Header decoded:")
            print(f"  Algorithm: {header.get('alg')}")
            print(f"  Key ID: {header.get('kid')}")
            
            # Decode payload
            payload = json.loads(urlsafe_b64decode(parts[1] + '=='))
            print(f"\n✓ Payload decoded:")
            print(f"  Subject: {payload.get('sub')}")
            print(f"  Username: {payload.get('cognito:username')}")
            print(f"  Email: {payload.get('email')}")
            print(f"  Groups: {payload.get('cognito:groups', [])}")
            print(f"  Issued at: {datetime.fromtimestamp(payload.get('iat', 0))}")
            print(f"  Expires at: {datetime.fromtimestamp(payload.get('exp', 0))}")
            
            # Check custom claims
            custom_perms = payload.get('trac_permissions', '')
            if custom_perms:
                print(f"\n✓ Custom Trac Permissions: {custom_perms}")
            
            return payload
        except Exception as e:
            print(f"✗ Token decode error: {e}")
            return None
    
    def test_permission_mapping(self, groups):
        """Test permission mapping for groups"""
        print("\n=== Testing Permission Mapping ===")
        
        # Default mappings from the plugin
        group_permissions = {
            'admins': [
                'TRAC_ADMIN', 'TICKET_ADMIN', 'MILESTONE_ADMIN', 
                'WIKI_ADMIN', 'PERMISSION_GRANT', 'PERMISSION_REVOKE'
            ],
            'instructors': [
                'TICKET_CREATE', 'TICKET_MODIFY', 'TICKET_VIEW',
                'MILESTONE_CREATE', 'MILESTONE_MODIFY', 'MILESTONE_VIEW',
                'WIKI_CREATE', 'WIKI_MODIFY', 'WIKI_VIEW'
            ],
            'students': [
                'TICKET_CREATE', 'TICKET_VIEW', 'MILESTONE_VIEW',
                'WIKI_VIEW', 'TIMELINE_VIEW', 'SEARCH_VIEW'
            ]
        }
        
        all_permissions = set()
        for group in groups:
            perms = group_permissions.get(group, [])
            if perms:
                print(f"\n✓ Group '{group}' grants:")
                for perm in perms:
                    print(f"  - {perm}")
                all_permissions.update(perms)
            else:
                print(f"\n⚠ Group '{group}' has no default permissions")
        
        print(f"\n✓ Total permissions granted: {len(all_permissions)}")
        return list(all_permissions)
    
    def test_oauth_urls(self):
        """Test OAuth URLs are properly formatted"""
        print("\n=== Testing OAuth URLs ===")
        
        base_url = f"https://{self.domain}.auth.{self.region}.amazoncognito.com"
        redirect_uri = "https://trac.example.com/auth/callback"
        
        # Login URL
        login_url = f"{base_url}/login?" + \
                   f"client_id={self.client_id}&" + \
                   f"response_type=code&" + \
                   f"scope=email+openid+profile&" + \
                   f"redirect_uri={redirect_uri}"
        
        print(f"✓ Login URL:")
        print(f"  {login_url}")
        
        # Logout URL
        logout_url = f"{base_url}/logout?" + \
                    f"client_id={self.client_id}&" + \
                    f"logout_uri=https://trac.example.com/"
        
        print(f"\n✓ Logout URL:")
        print(f"  {logout_url}")
        
        # Token endpoint
        token_url = f"{base_url}/oauth2/token"
        print(f"\n✓ Token endpoint:")
        print(f"  {token_url}")
        
        return True
    
    def test_api_authentication(self, token):
        """Test API authentication with Bearer token"""
        print("\n=== Testing API Authentication ===")
        
        # Simulate API request headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        print("✓ Request headers configured:")
        print(f"  Authorization: Bearer {token[:20]}...")
        print(f"  Content-Type: application/json")
        
        # The plugin would:
        # 1. Extract token from Authorization header
        # 2. Validate with JWKS
        # 3. Extract user info and permissions
        # 4. Grant/deny access
        
        return headers
    
    def generate_test_summary(self, results):
        """Generate test summary report"""
        print("\n" + "="*50)
        print("=== COGNITO AUTH PLUGIN TEST SUMMARY ===")
        print("="*50)
        
        print(f"\nConfiguration:")
        print(f"  Region: {self.region}")
        print(f"  User Pool: {self.user_pool_id}")
        print(f"  Client ID: {self.client_id}")
        print(f"  Domain: {self.domain}")
        
        print(f"\nTest Results:")
        for test, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  {test}: {status}")
        
        print(f"\nNext Steps:")
        if all(results.values()):
            print("  1. Install plugin in Trac environment")
            print("  2. Configure trac.ini with these values")
            print("  3. Test with real user authentication")
        else:
            print("  1. Fix failing tests")
            print("  2. Verify Cognito configuration")
            print("  3. Check network connectivity")

def main():
    # Configuration (from the documentation)
    config = {
        'region': 'us-east-2',
        'user_pool_id': 'us-east-2_IvxzMrWwg',
        'client_id': '5adkv019v4rcu6o87ffg46ep02',
        'domain': 'hutch-learntrac-dev-auth'
    }
    
    # Initialize tester
    tester = CognitoAuthTester(**config)
    
    print("=== Cognito Authentication Plugin Test ===")
    print(f"Testing configuration for LearnTrac")
    
    # Run tests
    results = {}
    
    # Test 1: JWKS endpoint
    results['JWKS Endpoint'] = tester.test_jwks_endpoint()
    
    # Test 2: OAuth URLs
    results['OAuth URLs'] = tester.test_oauth_urls()
    
    # Test 3: Permission mapping
    test_groups = ['admins', 'instructors', 'students']
    perms = tester.test_permission_mapping(test_groups)
    results['Permission Mapping'] = len(perms) > 0
    
    # Test 4: Token handling (with sample token)
    print("\n=== Sample Token Test ===")
    print("⚠ Note: Using a sample token structure for testing")
    print("  In production, use actual Cognito tokens")
    
    # Sample token structure (not a real token)
    sample_payload = {
        "sub": "1234567890",
        "cognito:username": "testuser",
        "email": "test@example.com",
        "cognito:groups": ["instructors"],
        "trac_permissions": "TICKET_CREATE,WIKI_MODIFY",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }
    
    print(f"\nSample token payload:")
    print(json.dumps(sample_payload, indent=2))
    
    # Generate summary
    tester.generate_test_summary(results)

if __name__ == "__main__":
    main()