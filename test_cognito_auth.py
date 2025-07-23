#!/usr/bin/env python
import requests
import json
import sys
import boto3
from datetime import datetime

class CognitoAuthTester:
    def __init__(self, base_url, client_id, region, user_pool_id):
        self.base_url = base_url
        self.client_id = client_id
        self.region = region
        self.user_pool_id = user_pool_id
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        self.session = requests.Session()
    
    def test_login_flow(self, username, password):
        """Test the complete login flow"""
        print(f"\n1. Testing login for user: {username}")
        
        try:
            # Authenticate with Cognito
            response = self.cognito_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            tokens = response['AuthenticationResult']
            print("✓ Successfully authenticated with Cognito")
            print(f"  - Access Token: {tokens['AccessToken'][:50]}...")
            print(f"  - ID Token: {tokens['IdToken'][:50]}...")
            print(f"  - Expires In: {tokens['ExpiresIn']} seconds")
            
            return tokens
            
        except Exception as e:
            print(f"✗ Login failed: {str(e)}")
            return None
    
    def test_api_with_token(self, token):
        """Test API access with Bearer token"""
        print("\n2. Testing API access with Bearer token")
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test various endpoints
        endpoints = [
            '/api/tickets',
            '/api/wiki',
            '/api/milestones'
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print(f"✓ {endpoint}: Success (200)")
                else:
                    print(f"✗ {endpoint}: Failed ({response.status_code})")
                    print(f"  Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"✗ {endpoint}: Error - {str(e)}")
    
    def test_token_refresh(self, refresh_token):
        """Test token refresh endpoint"""
        print("\n3. Testing token refresh")
        
        try:
            response = self.session.post(
                f"{self.base_url}/auth/refresh",
                json={'refresh_token': refresh_token}
            )
            
            if response.status_code == 200:
                new_tokens = response.json()
                print("✓ Token refresh successful")
                print(f"  - New Access Token: {new_tokens['access_token'][:50]}...")
                return new_tokens
            else:
                print(f"✗ Token refresh failed ({response.status_code})")
                print(f"  Response: {response.text}")
                
        except Exception as e:
            print(f"✗ Token refresh error: {str(e)}")
        
        return None
    
    def test_invalid_token(self):
        """Test API response to invalid token"""
        print("\n4. Testing invalid token handling")
        
        headers = {'Authorization': 'Bearer invalid.token.here'}
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/tickets",
                headers=headers
            )
            
            if response.status_code == 401:
                print("✓ Invalid token correctly rejected (401)")
                auth_header = response.headers.get('WWW-Authenticate')
                if auth_header and 'Bearer' in auth_header:
                    print("✓ WWW-Authenticate header present")
            else:
                print(f"✗ Unexpected status code: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    def test_permission_mapping(self, token, expected_group):
        """Test that Cognito groups map to Trac permissions"""
        print(f"\n5. Testing permission mapping for group: {expected_group}")
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test operations based on group
        if expected_group == 'admins':
            # Admins should be able to delete
            response = self.session.delete(
                f"{self.base_url}/api/tickets/99999",
                headers=headers
            )
            if response.status_code in [200, 404]:  # 404 is ok, means auth worked
                print("✓ Admin permission check passed")
            else:
                print(f"✗ Admin permission check failed ({response.status_code})")
                
        elif expected_group == 'students':
            # Students should NOT be able to delete
            response = self.session.delete(
                f"{self.base_url}/api/tickets/99999",
                headers=headers
            )
            if response.status_code == 403:
                print("✓ Student permission restriction working")
            else:
                print(f"✗ Student permission check failed ({response.status_code})")
    
    def run_all_tests(self, username, password, expected_group='students'):
        """Run all authentication tests"""
        print("=" * 60)
        print("COGNITO AUTHENTICATION TEST SUITE")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print(f"User Pool ID: {self.user_pool_id}")
        print(f"Client ID: {self.client_id}")
        print(f"Testing as: {username} (group: {expected_group})")
        
        # Test 1: Login
        tokens = self.test_login_flow(username, password)
        if not tokens:
            print("\n❌ Cannot proceed without valid tokens")
            return False
        
        # Test 2: API Access
        self.test_api_with_token(tokens['AccessToken'])
        
        # Test 3: Token Refresh
        if 'RefreshToken' in tokens:
            new_tokens = self.test_token_refresh(tokens['RefreshToken'])
        
        # Test 4: Invalid Token
        self.test_invalid_token()
        
        # Test 5: Permissions
        self.test_permission_mapping(tokens['AccessToken'], expected_group)
        
        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETE")
        print("=" * 60)
        
        return True

# Usage
if __name__ == "__main__":
    tester = CognitoAuthTester(
        base_url='http://localhost:8000',
        client_id='5adkv019v4rcu6o87ffg46ep02',
        region='us-east-2',
        user_pool_id='us-east-2_IvxzMrWwg'
    )
    
    # Test with different users
    tester.run_all_tests('student@example.com', 'StudentPass123!', 'students')
    tester.run_all_tests('admin@example.com', 'AdminPass123!', 'admins')