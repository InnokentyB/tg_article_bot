"""
Test script for authentication system
"""
import requests
import json
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5002"
API_KEY = os.getenv("API_KEY", "your-api-key-for-external-services")

def test_health_check():
    """Test health check endpoint (no auth required)"""
    print("🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_login():
    """Test login endpoint"""
    print("🔐 Testing login...")
    response = requests.post(f"{BASE_URL}/api/auth/login?username=admin&password=fakehashedpassword")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        token_data = response.json()
        print(f"Token: {token_data['access_token'][:50]}...")
        return token_data['access_token']
    else:
        print(f"Error: {response.text}")
        return None

def test_protected_endpoint(token):
    """Test protected endpoint with JWT token"""
    print("🔒 Testing protected endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        user_data = response.json()
        print(f"User: {user_data}")
    else:
        print(f"Error: {response.text}")
    print()

def test_api_key_auth():
    """Test API key authentication"""
    print("🔑 Testing API key authentication...")
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(f"{BASE_URL}/api/public/articles?limit=5", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        articles = response.json()
        print(f"Found {len(articles)} articles")
    else:
        print(f"Error: {response.text}")
    print()

def test_rate_limiting():
    """Test rate limiting"""
    print("⏱️ Testing rate limiting...")
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    # Make multiple requests quickly
    for i in range(5):
        response = requests.get(f"{BASE_URL}/api/public/articles?limit=1", headers=headers)
        print(f"Request {i+1}: {response.status_code}")
        if response.status_code == 429:
            print("Rate limit hit!")
            break
    
    print()

def test_unauthorized_access():
    """Test unauthorized access"""
    print("🚫 Testing unauthorized access...")
    
    # Try to access protected endpoint without token
    response = requests.get(f"{BASE_URL}/api/articles")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

def main():
    """Run all tests"""
    print("🧪 Starting authentication tests...")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 50)
    
    # Test 1: Health check
    test_health_check()
    
    # Test 2: Unauthorized access
    test_unauthorized_access()
    
    # Test 3: Login
    token = test_login()
    
    if token:
        # Test 4: Protected endpoint
        test_protected_endpoint(token)
    
    # Test 5: API key authentication
    test_api_key_auth()
    
    # Test 6: Rate limiting
    test_rate_limiting()
    
    print("✅ Authentication tests completed!")

if __name__ == "__main__":
    main()
