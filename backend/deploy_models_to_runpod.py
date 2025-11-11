#!/usr/bin/env python3
"""
BullsBears RunPod Model Deployment Script
Deploy FinMA-7b and DeepSeek-r1:8b models to RunPod endpoint
"""

import os
import sys
import json
import time
import requests
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RunPodModelDeployer:
    """Deploy and manage AI models on RunPod for BullsBears"""
    
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
        
        # Model configurations
        self.models = {
            "finma-7b": {
                "name": "finma-7b",
                "size": "4.2GB",
                "vram_required": "5GB",
                "purpose": "Prescreen Agent - ACTIVE to SHORT_LIST (75 candidates)",
                "ollama_model": "finma-7b"
            },
            "deepseek-r1:8b": {
                "name": "deepseek-r1:8b", 
                "size": "5.2GB",
                "vram_required": "6GB",
                "purpose": "Bull/Bear Predictors + Learning Agents",
                "ollama_model": "deepseek-r1:8b"
            }
        }
    
    def test_endpoint_health(self) -> bool:
        """Test if RunPod endpoint is responding"""
        print("🔍 Testing RunPod endpoint health...")

        try:
            health_payload = {
                "input": {
                    "test": "health_check",
                    "message": "BullsBears model deployment test"
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
                print("✅ RunPod endpoint is healthy")
                print(f"   Response: {result.get('message', 'OK')}")
                return True
            else:
                print(f"⚠️ Endpoint returned status {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Endpoint health check failed: {e}")
            return False
    
    def deploy_model(self, model_key: str) -> bool:
        """Deploy a specific model to RunPod"""
        model_config = self.models.get(model_key)
        if not model_config:
            print(f"❌ Unknown model: {model_key}")
            return False
        
        print(f"🚀 Deploying {model_config['name']}...")
        print(f"   Size: {model_config['size']}")
        print(f"   VRAM: {model_config['vram_required']}")
        print(f"   Purpose: {model_config['purpose']}")
        
        try:
            # Create deployment payload
            deploy_payload = {
                "input": {
                    "action": "deploy_model",
                    "model_name": model_config["ollama_model"],
                    "model_config": model_config
                }
            }
            
            # Send deployment request
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json=deploy_payload,
                timeout=300  # 5 minutes for model download
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "IN_PROGRESS":
                    # Poll for completion
                    job_id = result.get("id")
                    return self._wait_for_deployment(job_id, model_config["name"])
                else:
                    print(f"✅ {model_config['name']} deployed successfully")
                    return True
            else:
                print(f"❌ Deployment failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Deployment error for {model_config['name']}: {e}")
            return False
    
    def _wait_for_deployment(self, job_id: str, model_name: str) -> bool:
        """Wait for model deployment to complete"""
        print(f"⏳ Waiting for {model_name} deployment to complete...")
        
        max_wait = 600  # 10 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Check job status
                status_response = requests.get(
                    f"{self.base_url}/status/{job_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status")
                    
                    if status == "COMPLETED":
                        print(f"✅ {model_name} deployment completed")
                        return True
                    elif status == "FAILED":
                        print(f"❌ {model_name} deployment failed")
                        print(f"Error: {status_data.get('error', 'Unknown error')}")
                        return False
                    else:
                        print(f"   Status: {status}...")
                        time.sleep(10)
                else:
                    print(f"⚠️ Status check failed: {status_response.status_code}")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"⚠️ Status check error: {e}")
                time.sleep(10)
        
        print(f"⏰ Deployment timeout for {model_name}")
        return False
    
    def test_model_inference(self, model_key: str) -> bool:
        """Test model inference after deployment"""
        model_config = self.models.get(model_key)
        if not model_config:
            return False
        
        print(f"🧪 Testing {model_config['name']} inference...")
        
        try:
            # Create test payload based on model purpose
            if "finma" in model_key.lower():
                test_payload = {
                    "input": {
                        "action": "test_inference",
                        "model": model_config["ollama_model"],
                        "prompt": "Analyze AAPL for explosive move potential. Consider volume, price action, and technical setup.",
                        "max_tokens": 100
                    }
                }
            else:  # DeepSeek
                test_payload = {
                    "input": {
                        "action": "test_inference", 
                        "model": model_config["ollama_model"],
                        "prompt": "Is TSLA bullish or bearish? Provide confidence score.",
                        "max_tokens": 50
                    }
                }
            
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json=test_payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"✅ {model_config['name']} inference test passed")
                    print(f"   Response: {result.get('output', '')[:100]}...")
                    return True
                else:
                    print(f"❌ Inference test failed: {result.get('error')}")
                    return False
            else:
                print(f"❌ Inference test failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Inference test error: {e}")
            return False
    
    def get_model_status(self) -> dict:
        """Get status of all deployed models"""
        print("📊 Checking model deployment status...")
        
        try:
            status_payload = {
                "input": {
                    "action": "list_models"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json=status_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("models", {})
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return {}
    
    def deploy_all_models(self) -> bool:
        """Deploy all required models"""
        print("🚀 STARTING BULLSBEARS MODEL DEPLOYMENT")
        print("=" * 60)
        
        # Test endpoint first
        if not self.test_endpoint_health():
            print("❌ Endpoint not healthy, cannot deploy models")
            return False
        
        success_count = 0
        total_models = len(self.models)
        
        # Deploy each model
        for model_key in self.models.keys():
            print(f"\n📦 Deploying model {success_count + 1}/{total_models}: {model_key}")
            
            if self.deploy_model(model_key):
                # Test inference
                if self.test_model_inference(model_key):
                    success_count += 1
                    print(f"✅ {model_key} fully deployed and tested")
                else:
                    print(f"⚠️ {model_key} deployed but inference test failed")
            else:
                print(f"❌ {model_key} deployment failed")
        
        # Final status
        print("\n" + "=" * 60)
        print(f"📊 DEPLOYMENT SUMMARY: {success_count}/{total_models} models successful")
        
        if success_count == total_models:
            print("🎉 ALL MODELS DEPLOYED SUCCESSFULLY!")
            
            # Show final status
            model_status = self.get_model_status()
            if model_status:
                print("\n📋 Final Model Status:")
                for model, status in model_status.items():
                    print(f"   {model}: {status}")
            
            return True
        else:
            print("⚠️ Some models failed to deploy")
            return False


def main():
    """Main deployment function"""
    print("🎯 BullsBears AI - RunPod Model Deployment")
    print("=" * 50)
    
    try:
        deployer = RunPodModelDeployer()
        
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "test":
                deployer.test_endpoint_health()
            elif command == "status":
                status = deployer.get_model_status()
                print(f"Model Status: {json.dumps(status, indent=2)}")
            elif command in deployer.models:
                # Deploy specific model
                success = deployer.deploy_model(command)
                if success:
                    deployer.test_model_inference(command)
            else:
                print(f"Unknown command: {command}")
                print("Available commands: test, status, finma-7b, deepseek-r1:8b")
        else:
            # Deploy all models
            success = deployer.deploy_all_models()
            if success:
                print("\n🎉 Deployment completed successfully!")
                print("📊 Next steps:")
                print("   1. Test with real stock data")
                print("   2. Run full pipeline test")
                print("   3. Monitor model performance")
            else:
                print("\n❌ Deployment failed!")
                print("🔧 Check logs and retry individual models")
    
    except Exception as e:
        print(f"❌ Deployment script error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
