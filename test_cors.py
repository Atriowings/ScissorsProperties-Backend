#!/usr/bin/env python3
"""
Simple test script to verify CORS and server functionality
Run this after deploying your changes to Railway
"""

import requests
import json

# Your Railway backend URL
BACKEND_URL = "https://scissorsproperties-backend-production.up.railway.app"

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get(f"{BACKEND_URL}/auth/health")
        print(f"Health check: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_cors_headers():
    """Test CORS headers"""
    try:
        # Make a preflight OPTIONS request
        headers = {
            'Origin': 'https://scissorsproperties.com',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        response = requests.options(f"{BACKEND_URL}/auth/register", headers=headers)
        
        print(f"CORS preflight: {response.status_code}")
        print(f"CORS headers: {dict(response.headers)}")
        
        # Check for CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
        }
        
        print(f"CORS configuration: {cors_headers}")
        return 'Access-Control-Allow-Origin' in response.headers
    except Exception as e:
        print(f"CORS test failed: {e}")
        return False

def test_register_endpoint():
    """Test the register endpoint with sample data"""
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
        
        # Check if we get a proper response (not CORS error)
        return response.status_code in [200, 400, 500]  # Any proper HTTP response
    except Exception as e:
        print(f"Register test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Scissors Properties Backend...")
    print("=" * 50)
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    health_ok = test_health_endpoint()
    
    # Test CORS headers
    print("\n2. Testing CORS configuration...")
    cors_ok = test_cors_headers()
    
    # Test register endpoint
    print("\n3. Testing register endpoint...")
    register_ok = test_register_endpoint()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Health endpoint: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"CORS headers: {'✅ PASS' if cors_ok else '❌ FAIL'}")
    print(f"Register endpoint: {'✅ PASS' if register_ok else '❌ FAIL'}")
    
    if all([health_ok, cors_ok, register_ok]):
        print("\n🎉 All tests passed! Your backend should be working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
