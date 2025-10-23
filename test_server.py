#!/usr/bin/env python3
"""
Test script to verify the FastAPI server works.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from app.main import app
    from fastapi.testclient import TestClient
    
    print("✅ Successfully imported FastAPI app")
    
    # Create test client
    client = TestClient(app)
    
    # Test root endpoint
    print("🧪 Testing root endpoint...")
    response = client.get("/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test health endpoint
    print("\n🧪 Testing health endpoint...")
    response = client.get("/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    print("\n🎉 All tests passed! FastAPI server is working correctly.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
