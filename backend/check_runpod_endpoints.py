#!/usr/bin/env python3
"""
Check available RunPod endpoints
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def list_runpod_endpoints():
    """List available RunPod endpoints"""
    
    api_key = os.getenv('RUNPOD_API_KEY')
    if not api_key:
        print("❌ RUNPOD_API_KEY not found")
        return
    
    print("🔍 CHECKING RUNPOD ENDPOINTS")
    print("=" * 40)
    
    # Try GraphQL API to list endpoints
    url = "https://api.runpod.ai/graphql"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    query = {
        "query": """
        query {
            myself {
                serverlessDiscount {
                    discountFactor
                    type
                }
            }
            serverlessEndpoints {
                id
                name
                status
                version
                locations {
                    id
                    name
                }
            }
        }
        """
    }
    
    try:
        response = requests.post(url, json=query, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'data' in result and 'serverlessEndpoints' in result['data']:
                endpoints = result['data']['serverlessEndpoints']
                
                print(f"✅ Found {len(endpoints)} endpoints:")
                
                for endpoint in endpoints:
                    print(f"\n📋 Endpoint: {endpoint.get('name', 'Unnamed')}")
                    print(f"   ID: {endpoint.get('id')}")
                    print(f"   Status: {endpoint.get('status')}")
                    print(f"   Version: {endpoint.get('version')}")
                    
                    locations = endpoint.get('locations', [])
                    if locations:
                        print(f"   Locations: {', '.join([loc.get('name', 'Unknown') for loc in locations])}")
                
                return endpoints
            else:
                print("❌ No endpoints found or API response format changed")
                print(f"Response: {result}")
                return []
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Failed to check endpoints: {e}")
        return []

def test_endpoint_direct(endpoint_id):
    """Test a specific endpoint directly"""
    
    api_key = os.getenv('RUNPOD_API_KEY')
    
    print(f"\n🔌 TESTING ENDPOINT: {endpoint_id}")
    print("=" * 40)
    
    # Try a simple health check
    url = f"https://api.runpod.ai/v2/{endpoint_id}/health"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ Endpoint is healthy")
            return True
        elif response.status_code == 404:
            print("❌ Endpoint not found (404)")
            return False
        else:
            print(f"⚠️ Endpoint status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def main():
    """Main function"""
    
    # List all endpoints
    endpoints = list_runpod_endpoints()
    
    # Test the configured endpoint
    configured_endpoint = os.getenv('RUNPOD_ENDPOINT_ID')
    if configured_endpoint:
        test_endpoint_direct(configured_endpoint)
    
    print("\n🎯 RECOMMENDATIONS:")
    if endpoints:
        active_endpoints = [ep for ep in endpoints if ep.get('status') == 'ACTIVE']
        if active_endpoints:
            print("✅ Use one of these active endpoints:")
            for ep in active_endpoints:
                print(f"   - {ep.get('id')} ({ep.get('name', 'Unnamed')})")
        else:
            print("⚠️ No active endpoints found")
            print("   Create a new serverless endpoint in RunPod console")
    else:
        print("🔧 Check RunPod console to create/configure endpoints")

if __name__ == "__main__":
    main()
