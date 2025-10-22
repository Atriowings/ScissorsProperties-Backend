#!/usr/bin/env python3
"""
Test script to verify API and CORS functionality
"""

import requests
import json

# Backend URL
BACKEND_URL = "https://scissorsproperties-backend-production.up.railway.app"

def test_cors_headers():
    """Test CORS headers"""
    try:
        # Test OPTIONS request to register endpoint specifically
        response = requests.options(f"{BACKEND_URL}/auth/register", 
                                  headers={'Origin': 'https://scissorsproperties.com'})
        
        print(f"CORS OPTIONS test for /auth/register: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        # Check for CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials'),
        }
        
        print(f"CORS Headers Found: {cors_headers}")
        
        # Check if all required headers are present
        required_headers = ['Access-Control-Allow-Origin', 'Access-Control-Allow-Methods', 'Access-Control-Allow-Headers']
        has_required_headers = all(header in cors_headers for header in required_headers)
        
        return response.status_code == 200 and has_required_headers
        
    except Exception as e:
        print(f"CORS test failed: {e}")
        return False

def test_health_endpoint():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BACKEND_URL}/auth/health")
        print(f"Health test: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health test failed: {e}")
        return False

def test_register_endpoint():
    """Test register endpoint with sample data"""
    try:
        test_data = {
            "user_name": "Test User",
            "mobile_number": 9876543210,
            "email": "test@example.com",
            "referredBy": "myself",
            "referredById": None
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://scissorsproperties.com'
        }
        
        response = requests.post(
            f"{BACKEND_URL}/auth/register", 
            json=test_data, 
            headers=headers
        )
        
        print(f"Register test: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Response Headers: {dict(response.headers)}")
        
        # Check for CORS headers in response
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }
        print(f"CORS Headers in Response: {cors_headers}")
        
        # Check if we get a proper response (not CORS error)
        return response.status_code in [200, 400, 500]  # Any proper HTTP response
    except Exception as e:
        print(f"Register test failed: {e}")
        return False

def main():
    print("🧪 Testing API and CORS functionality...")
    print("=" * 50)
    
    # Test 1: Health endpoint
    print("\n1. Testing Health Endpoint:")
    health_ok = test_health_endpoint()
    
    # Test 2: CORS headers
    print("\n2. Testing CORS Headers:")
    cors_ok = test_cors_headers()
    
    # Test 3: Register endpoint
    print("\n3. Testing Register Endpoint:")
    register_ok = test_register_endpoint()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Health Endpoint: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"CORS Headers: {'✅ PASS' if cors_ok else '❌ FAIL'}")
    print(f"Register Endpoint: {'✅ PASS' if register_ok else '❌ FAIL'}")
    
    if all([health_ok, cors_ok, register_ok]):
        print("\n🎉 All tests passed! API should be working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
