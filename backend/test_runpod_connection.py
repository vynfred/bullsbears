#!/usr/bin/env python3
"""
Simple RunPod Connection Test
Test basic connectivity to RunPod endpoint
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_runpod_connection():
    """Test basic RunPod connection"""
    
    # Get credentials
    api_key = os.getenv('RUNPOD_API_KEY')
    endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID', '0bv1yn1beqszt7')
    
    print("🔍 RunPod Connection Test")
    print("=" * 40)
    print(f"API Key: {'✅ Found' if api_key else '❌ Missing'}")
    print(f"Endpoint ID: {endpoint_id}")
    
    if not api_key:
        print("❌ RUNPOD_API_KEY not found in environment")
        print("💡 Add RUNPOD_API_KEY=your_key to your .env file")
        return False
    
    # Test different endpoint URLs
    endpoints_to_test = [
        f"https://api.runpod.ai/v2/{endpoint_id}/run",
        f"https://api.runpod.ai/v2/{endpoint_id}/runsync", 
        f"https://api.runpod.ai/v2/{endpoint_id}/status"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Simple test payload
    test_payload = {
        "input": {
            "test": "health_check"
        }
    }
    
    print("\n🚀 Testing endpoints...")
    
    for endpoint_url in endpoints_to_test:
        print(f"\nTesting: {endpoint_url}")
        
        try:
            response = requests.post(
                endpoint_url,
                headers=headers,
                json=test_payload,
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ Success: {json.dumps(result, indent=2)}")
                    return True
                except:
                    print(f"✅ Success (non-JSON): {response.text[:200]}")
                    return True
            else:
                print(f"❌ Failed: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print("⏰ Timeout")
        except requests.exceptions.ConnectionError:
            print("🔌 Connection Error")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n❌ All endpoint tests failed")
    return False

def test_runpod_graphql():
    """Test RunPod GraphQL API for endpoint info"""
    
    api_key = os.getenv('RUNPOD_API_KEY')
    if not api_key:
        return False
    
    print("\n🔍 Testing RunPod GraphQL API...")
    
    graphql_url = "https://api.runpod.ai/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Query to get user's endpoints
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
            }
        }
        """
    }
    
    try:
        response = requests.post(
            graphql_url,
            headers=headers,
            json=query,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ GraphQL API working")
            
            endpoints = result.get('data', {}).get('serverlessEndpoints', [])
            if endpoints:
                print(f"📋 Found {len(endpoints)} endpoints:")
                for endpoint in endpoints:
                    print(f"   {endpoint.get('id')}: {endpoint.get('name')} ({endpoint.get('status')})")
            else:
                print("⚠️ No serverless endpoints found")
            
            return True
        else:
            print(f"❌ GraphQL failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ GraphQL error: {e}")
        return False

def main():
    """Main test function"""
    print("🎯 BullsBears RunPod Connection Test")
    print("=" * 50)
    
    # Test 1: Basic connection
    connection_ok = test_runpod_connection()
    
    # Test 2: GraphQL API
    graphql_ok = test_runpod_graphql()
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY:")
    print(f"Connection Test: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    print(f"GraphQL Test: {'✅ PASS' if graphql_ok else '❌ FAIL'}")
    
    if connection_ok:
        print("\n🎉 RunPod connection is working!")
        print("✅ Ready to deploy models")
    else:
        print("\n❌ RunPod connection failed!")
        print("🔧 Check your API key and endpoint ID")
        print("💡 Possible issues:")
        print("   - Invalid RUNPOD_API_KEY")
        print("   - Wrong RUNPOD_ENDPOINT_ID")
        print("   - Endpoint not deployed/running")
        print("   - Network connectivity issues")

if __name__ == "__main__":
    main()
