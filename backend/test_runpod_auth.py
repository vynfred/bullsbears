#!/usr/bin/env python3
"""
Test RunPod API Authentication
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_runpod_auth():
    """Test RunPod API key authentication"""
    
    api_key = os.getenv('RUNPOD_API_KEY')
    
    print("🔐 RunPod Authentication Test")
    print("=" * 40)
    print(f"API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'None'}")
    
    if not api_key:
        print("❌ No API key found!")
        return False
    
    # Test 1: GraphQL API (user info)
    print("\n🔍 Testing GraphQL API...")

    graphql_url = "https://api.runpod.io/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Simple query to get user info
    query = {
        "query": """
        query {
            myself {
                id
                email
            }
        }
        """
    }
    
    try:
        response = requests.post(graphql_url, headers=headers, json=query, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'data' in result and result['data']['myself']:
                user = result['data']['myself']
                print(f"✅ Authentication successful!")
                print(f"   User ID: {user.get('id', 'N/A')}")
                print(f"   Email: {user.get('email', 'N/A')}")
                return True
            else:
                print(f"❌ Authentication failed: {result}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_list_endpoints():
    """List user's serverless endpoints"""
    
    api_key = os.getenv('RUNPOD_API_KEY')
    if not api_key:
        return False
    
    print("\n📋 Listing Serverless Endpoints...")

    graphql_url = "https://api.runpod.io/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    query = {
        "query": """
        query {
            myself {
                endpoints {
                    id
                    name
                }
            }
        }
        """
    }
    
    try:
        response = requests.post(graphql_url, headers=headers, json=query, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            endpoints = result.get('data', {}).get('myself', {}).get('endpoints', [])

            if endpoints:
                print(f"✅ Found {len(endpoints)} endpoints:")
                for endpoint in endpoints:
                    print(f"   📍 {endpoint.get('id')}: {endpoint.get('name')}")
                return True
            else:
                print("⚠️ No serverless endpoints found")
                print("💡 You may need to create an endpoint first")
                return False
        else:
            print(f"❌ Failed to list endpoints: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error listing endpoints: {e}")
        return False

def main():
    """Main test function"""
    
    print("🎯 RunPod API Authentication Test")
    print("=" * 50)
    
    # Test authentication
    auth_ok = test_runpod_auth()
    
    if auth_ok:
        # List endpoints
        endpoints_ok = test_list_endpoints()
        
        print("\n" + "=" * 50)
        print("📊 SUMMARY:")
        print(f"Authentication: {'✅ PASS' if auth_ok else '❌ FAIL'}")
        print(f"Endpoints Found: {'✅ YES' if endpoints_ok else '⚠️ NONE'}")
        
        if auth_ok and not endpoints_ok:
            print("\n💡 NEXT STEPS:")
            print("1. Go to https://console.runpod.io/serverless")
            print("2. Create a new serverless endpoint")
            print("3. Use a template with Python support")
            print("4. Note the endpoint ID for your .env file")
    else:
        print("\n❌ Authentication failed!")
        print("💡 Check your RUNPOD_API_KEY in .env file")
        print("🔗 Get your API key from: https://console.runpod.io/user/settings")

if __name__ == "__main__":
    main()
