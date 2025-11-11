#!/usr/bin/env python3
"""
Simple RunPod Database Connection Test
Just tests if we can connect to Google Cloud SQL from RunPod
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def create_simple_db_test():
    """Create a simple database connection test payload"""
    
    return {
        "input": {
            "task": "test_database_connection",
            "database_url": os.getenv('DATABASE_URL'),
            "test_query": "SELECT version();"
        }
    }

def submit_test_job():
    """Submit simple test job to RunPod"""
    
    api_key = os.getenv('RUNPOD_API_KEY')
    endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID')
    
    if not api_key or not endpoint_id:
        print("❌ Missing RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID in .env")
        return None
    
    print("🔌 TESTING DATABASE CONNECTION VIA RUNPOD")
    print("=" * 50)
    print(f"Endpoint: {endpoint_id}")
    print(f"Database: {os.getenv('DATABASE_URL', 'Not configured')[:50]}...")
    
    payload = create_simple_db_test()
    
    url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        print("\n🚀 Submitting test job...")
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ Response received!")
            print(f"Status: {result.get('status', 'Unknown')}")
            
            if result.get('status') == 'COMPLETED':
                output = result.get('output', {})
                print("\n📊 Test Results:")
                for key, value in output.items():
                    print(f"   {key}: {value}")
                return True
            else:
                print(f"❌ Job failed or incomplete")
                print(f"Error: {result.get('error', 'Unknown')}")
                return False
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = submit_test_job()
    
    if success:
        print("\n🎉 DATABASE CONNECTION WORKING FROM RUNPOD!")
        print("✅ Ready to proceed with full bootstrap")
    else:
        print("\n🔧 Database connection needs troubleshooting")
        print("Check RunPod logs for more details")
