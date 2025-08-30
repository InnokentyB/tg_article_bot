#!/usr/bin/env python3
"""
Test script for HTTPS authentication system
"""
import requests
import json
import os
import urllib3
from datetime import datetime

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
BASE_URL = "https://localhost:5000"
API_KEY = os.getenv("API_KEY", "your-api-key-for-external-services")

def test_health_check():
    """Test health check endpoint (no auth required)"""
    print("🔍 Testing health check (HTTPS)...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", verify=False)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except requests.exceptions.SSLError as e:
        print(f"SSL Error: {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")
    print()

def test_login():
    """Test login endpoint"""
    print("🔐 Testing login (HTTPS)...")
    login_data = {
        "username": "admin",
        "password": "fakehashedpassword"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            print(f"Token: {token_data['access_token'][:50]}...")
            return token_data['access_token']
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    return None

def test_protected_endpoint(token):
    """Test protected endpoint with JWT token"""
    print("🔒 Testing protected endpoint (HTTPS)...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            user_data = response.json()
            print(f"User: {user_data}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    print()

def test_api_key_auth():
    """Test API key authentication"""
    print("🔑 Testing API key authentication (HTTPS)...")
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        response = requests.get(f"{BASE_URL}/api/public/articles?limit=5", headers=headers, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            articles = response.json()
            print(f"Found {len(articles)} articles")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    print()

def test_rate_limiting():
    """Test rate limiting"""
    print("⏱️ Testing rate limiting (HTTPS)...")
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    # Make multiple requests quickly
    for i in range(5):
        try:
            response = requests.get(f"{BASE_URL}/api/public/articles?limit=1", headers=headers, verify=False)
            print(f"Request {i+1}: {response.status_code}")
            if response.status_code == 429:
                print("Rate limit hit!")
                break
        except Exception as e:
            print(f"Request {i+1}: Error - {e}")
    
    print()

def test_unauthorized_access():
    """Test unauthorized access"""
    print("🚫 Testing unauthorized access (HTTPS)...")
    
    # Try to access protected endpoint without token
    try:
        response = requests.get(f"{BASE_URL}/api/articles", verify=False)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    print()

def test_ssl_certificate():
    """Test SSL certificate"""
    print("🔒 Testing SSL certificate...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", verify=True)
        print("✅ SSL certificate is valid")
    except requests.exceptions.SSLError as e:
        print(f"⚠️ SSL certificate warning (expected for self-signed): {e}")
    except Exception as e:
        print(f"❌ SSL error: {e}")
    print()

def main():
    """Run all tests"""
    print("🧪 Starting HTTPS authentication tests...")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 50)
    
    # Test 1: SSL certificate
    test_ssl_certificate()
    
    # Test 2: Health check
    test_health_check()
    
    # Test 3: Unauthorized access
    test_unauthorized_access()
    
    # Test 4: Login
    token = test_login()
    
    if token:
        # Test 5: Protected endpoint
        test_protected_endpoint(token)
    
    # Test 6: API key authentication
    test_api_key_auth()
    
    # Test 7: Rate limiting
    test_rate_limiting()
    
    print("✅ HTTPS authentication tests completed!")

if __name__ == "__main__":
    main()
