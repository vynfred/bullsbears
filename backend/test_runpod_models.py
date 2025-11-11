#!/usr/bin/env python3
"""
Test BullsBears RunPod Model Deployment
Verify that models are deployed and working correctly
"""

import os
import json
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RunPodModelTester:
    """Test deployed models on RunPod"""
    
    def __init__(self):
        self.runpod_api_key = os.getenv('RUNPOD_API_KEY')
        self.endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID', '0bv1yn1beqszt7')
        
        if not self.runpod_api_key:
            raise ValueError("RUNPOD_API_KEY environment variable is required")
        
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.runpod_api_key}"
        }
    
    def test_endpoint_health(self) -> bool:
        """Test basic endpoint health"""
        print("🔍 Testing RunPod endpoint health...")
        
        try:
            health_payload = {
                "input": {
                    "test": "health_check"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json=health_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Endpoint is healthy")
                print(f"   Deployed models: {result.get('deployed_models', [])}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def list_deployed_models(self) -> dict:
        """List all deployed models"""
        print("📋 Listing deployed models...")
        
        try:
            list_payload = {
                "input": {
                    "action": "list_models"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json=list_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    models = result.get("models", {})
                    print(f"✅ Found {len(models)} models:")
                    for model_name, model_info in models.items():
                        status = model_info.get("status", "unknown")
                        size = model_info.get("size", 0)
                        print(f"   {model_name}: {status} ({size} bytes)")
                    return models
                else:
                    print(f"❌ Failed to list models: {result.get('error')}")
                    return {}
            else:
                print(f"❌ List models failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ List models error: {e}")
            return {}
    
    def test_model_inference(self, model_name: str, test_prompt: str) -> bool:
        """Test inference for a specific model"""
        print(f"🧪 Testing {model_name} inference...")
        
        try:
            inference_payload = {
                "input": {
                    "action": "test_inference",
                    "model": model_name,
                    "prompt": test_prompt,
                    "max_tokens": 100
                }
            }
            
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json=inference_payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    output = result.get("output", "")
                    print(f"✅ {model_name} inference successful")
                    print(f"   Prompt: {test_prompt}")
                    print(f"   Response: {output[:200]}...")
                    return True
                else:
                    print(f"❌ {model_name} inference failed: {result.get('error')}")
                    return False
            else:
                print(f"❌ {model_name} inference failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ {model_name} inference error: {e}")
            return False
    
    def run_comprehensive_test(self) -> bool:
        """Run comprehensive test of all models"""
        print("🎯 RUNNING COMPREHENSIVE RUNPOD MODEL TEST")
        print("=" * 60)
        
        # Test 1: Endpoint health
        if not self.test_endpoint_health():
            print("❌ Endpoint health check failed, aborting tests")
            return False
        
        print()
        
        # Test 2: List models
        models = self.list_deployed_models()
        if not models:
            print("❌ No models found, aborting tests")
            return False
        
        print()
        
        # Test 3: Test each model
        test_prompts = {
            "finma-7b": "Analyze AAPL stock for explosive move potential. Consider volume, price action, and technical indicators.",
            "deepseek-r1:8b": "Is TSLA currently bullish or bearish? Provide a confidence score from 0-100."
        }
        
        successful_tests = 0
        total_tests = 0
        
        for model_name in models.keys():
            if model_name in test_prompts:
                total_tests += 1
                test_prompt = test_prompts[model_name]
                
                if self.test_model_inference(model_name, test_prompt):
                    successful_tests += 1
                
                print()  # Add spacing between tests
        
        # Test 4: Summary
        print("=" * 60)
        print(f"📊 TEST SUMMARY: {successful_tests}/{total_tests} models passed")
        
        if successful_tests == total_tests and total_tests > 0:
            print("🎉 ALL MODEL TESTS PASSED!")
            print("✅ RunPod deployment is ready for production")
            return True
        else:
            print("⚠️ Some model tests failed")
            print("🔧 Check model deployment and retry")
            return False


def main():
    """Main test function"""
    print("🎯 BullsBears RunPod Model Testing")
    print("=" * 50)
    
    try:
        tester = RunPodModelTester()
        
        # Run comprehensive test
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 All tests passed! RunPod models are ready.")
            print("📊 Next steps:")
            print("   1. Run bootstrap to prime database")
            print("   2. Test full pipeline with real data")
            print("   3. Monitor model performance")
        else:
            print("\n❌ Some tests failed!")
            print("🔧 Check model deployment and retry")
    
    except Exception as e:
        print(f"❌ Test script error: {e}")


if __name__ == "__main__":
    main()
