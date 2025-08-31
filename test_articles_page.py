#!/usr/bin/env python3
"""
Test script for articles page functionality
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """Test login functionality"""
    print("🔐 Testing login...")
    
    # Test admin login
    login_data = {
        "username": "admin",
        "password": "fakehashedpassword"
    }
    
    response = requests.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    
    if response.status_code == 302:
        print("✅ Login successful")
        return response.cookies.get("access_token")
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return None

def test_articles_page(access_token, page=1, per_page=20):
    """Test articles page with pagination"""
    print(f"📰 Testing articles page (page={page}, per_page={per_page})...")
    
    headers = {}
    if access_token:
        headers["Cookie"] = f"access_token={access_token}"
    
    params = {
        "page": page,
        "per_page": per_page
    }
    
    response = requests.get(f"{BASE_URL}/articles", headers=headers, params=params)
    
    if response.status_code == 200:
        print("✅ Articles page loaded successfully")
        print(f"📄 Content length: {len(response.text)} characters")
        
        # Check if pagination info is present
        if "pagination" in response.text:
            print("✅ Pagination controls found")
        
        # Check if articles are present
        if "article-card" in response.text:
            print("✅ Article cards found")
        
        return True
    else:
        print(f"❌ Articles page failed: {response.status_code}")
        return False

def test_pagination_options():
    """Test different pagination options"""
    print("\n🔄 Testing pagination options...")
    
    access_token = test_login()
    if not access_token:
        print("❌ Cannot test pagination without login")
        return
    
    # Test 20 articles per page
    test_articles_page(access_token, page=1, per_page=20)
    
    # Test 50 articles per page
    test_articles_page(access_token, page=1, per_page=50)
    
    # Test second page
    test_articles_page(access_token, page=2, per_page=20)

def test_mock_articles():
    """Test mock articles generation"""
    print("\n🎭 Testing mock articles generation...")
    
    # Import the function from web_admin
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from web_admin import get_mock_articles
        
        # Test with 20 articles per page
        result = get_mock_articles(page=1, per_page=20)
        print(f"✅ Mock articles generated: {len(result['articles'])} articles")
        print(f"📊 Total: {result['total']}, Pages: {result['pages']}")
        
        # Test with 50 articles per page
        result = get_mock_articles(page=1, per_page=50)
        print(f"✅ Mock articles generated: {len(result['articles'])} articles")
        print(f"📊 Total: {result['total']}, Pages: {result['pages']}")
        
        # Test second page
        result = get_mock_articles(page=2, per_page=20)
        print(f"✅ Mock articles generated: {len(result['articles'])} articles")
        print(f"📊 Page: {result['page']}, Per page: {result['per_page']}")
        
    except ImportError as e:
        print(f"❌ Cannot import mock articles function: {e}")

if __name__ == "__main__":
    print("🚀 Starting articles page tests...\n")
    
    # Test mock articles generation
    test_mock_articles()
    
    # Test web interface
    test_pagination_options()
    
    print("\n✅ All tests completed!")
