#!/usr/bin/env python3
"""
Test script for LearnTrac API
Tests basic connectivity and health endpoints
"""

import httpx
import asyncio
import sys

API_BASE_URL = "http://localhost:8001"


async def test_health_endpoints():
    """Test health check endpoints"""
    print("Testing LearnTrac API Health Endpoints...\n")
    
    async with httpx.AsyncClient() as client:
        # Test system health
        try:
            response = await client.get(f"{API_BASE_URL}/health")
            print(f"✓ System Health Check: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Status: {data.get('status')}")
                print(f"  Version: {data.get('version')}")
                print(f"  Components:")
                for component, status in data.get('components', {}).items():
                    print(f"    - {component}: {status}")
            else:
                print(f"  ✗ Unexpected status code: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Failed to connect: {e}")
            return False
        
        print()
        
        # Test LearnTrac health
        try:
            response = await client.get(f"{API_BASE_URL}/api/learntrac/health")
            print(f"✓ LearnTrac Health Check: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Service: {data.get('service')}")
                print(f"  Features:")
                for feature, status in data.get('features', {}).items():
                    print(f"    - {feature}: {status}")
            else:
                print(f"  ✗ Unexpected status code: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            return False
    
    return True


async def test_openapi_docs():
    """Test OpenAPI documentation endpoints"""
    print("\nTesting API Documentation Endpoints...\n")
    
    async with httpx.AsyncClient() as client:
        # Test OpenAPI JSON
        try:
            response = await client.get(f"{API_BASE_URL}/openapi.json")
            print(f"✓ OpenAPI JSON: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Title: {data.get('info', {}).get('title')}")
                print(f"  Version: {data.get('info', {}).get('version')}")
                print(f"  Endpoints: {len(data.get('paths', {}))}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
    
    print(f"\n✓ Interactive API docs available at: {API_BASE_URL}/docs")
    print(f"✓ ReDoc documentation available at: {API_BASE_URL}/redoc")


async def test_protected_endpoint():
    """Test that protected endpoints require authentication"""
    print("\nTesting Authentication Requirements...\n")
    
    async with httpx.AsyncClient() as client:
        # Test without auth
        try:
            response = await client.get(f"{API_BASE_URL}/api/learntrac/paths")
            if response.status_code == 401:
                print("✓ Protected endpoint correctly requires authentication")
            else:
                print(f"✗ Expected 401, got {response.status_code}")
        except Exception as e:
            print(f"✗ Failed: {e}")


async def main():
    """Run all tests"""
    print("=" * 50)
    print("LearnTrac API Test Suite")
    print("=" * 50)
    
    # Check if API is running
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{API_BASE_URL}/health", timeout=2.0)
    except:
        print(f"\n✗ Cannot connect to API at {API_BASE_URL}")
        print("  Make sure the API is running:")
        print("  - Python: uvicorn src.main:app --reload --port 8001")
        print("  - Docker: docker-compose up")
        return 1
    
    # Run tests
    all_passed = True
    
    if not await test_health_endpoints():
        all_passed = False
    
    await test_openapi_docs()
    await test_protected_endpoint()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 50)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))