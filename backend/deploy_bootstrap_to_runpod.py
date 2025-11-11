#!/usr/bin/env python3
"""
Deploy BullsBears Database Bootstrap to RunPod
This will run the database migration and data bootstrap from RunPod infrastructure
"""

import os
import json
import requests
import time
from dotenv import load_dotenv

load_dotenv()

class RunPodBootstrapDeployer:
    def __init__(self):
        self.api_key = os.getenv('RUNPOD_API_KEY')
        self.endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID')
        
        if not self.api_key or not self.endpoint_id:
            raise ValueError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set in .env")
    
    def create_bootstrap_payload(self):
        """Create the payload for database bootstrap"""
        
        # Get database credentials from .env
        database_url = os.getenv('DATABASE_URL')
        fmp_api_key = os.getenv('FMP_API_KEY')
        
        return {
            "input": {
                "task": "database_bootstrap",
                "config": {
                    "database_url": database_url,
                    "fmp_api_key": fmp_api_key,
                    "bootstrap_days": 90,
                    "operations": [
                        "migrate_database",
                        "bootstrap_historical_data",
                        "verify_data_integrity"
                    ]
                }
            }
        }
    
    def deploy_bootstrap(self):
        """Deploy bootstrap task to RunPod"""
        
        print("🚀 DEPLOYING DATABASE BOOTSTRAP TO RUNPOD")
        print("=" * 60)
        
        # Create payload
        payload = self.create_bootstrap_payload()
        
        print("📦 Bootstrap Configuration:")
        print(f"   - Database: {payload['input']['config']['database_url'][:50]}...")
        print(f"   - Bootstrap Days: {payload['input']['config']['bootstrap_days']}")
        print(f"   - Operations: {len(payload['input']['config']['operations'])}")
        
        # Deploy to RunPod
        url = f"https://api.runpod.ai/v2/{self.endpoint_id}/runsync"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        print(f"\n🔌 Sending request to RunPod endpoint: {self.endpoint_id}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == 'COMPLETED':
                    print("✅ BOOTSTRAP COMPLETED SUCCESSFULLY!")
                    
                    output = result.get('output', {})
                    print(f"\n📊 Results:")
                    print(f"   - Migration Status: {output.get('migration_status', 'Unknown')}")
                    print(f"   - Records Inserted: {output.get('records_inserted', 'Unknown')}")
                    print(f"   - Symbols Processed: {output.get('symbols_processed', 'Unknown')}")
                    print(f"   - Execution Time: {output.get('execution_time', 'Unknown')}")
                    
                    return True
                    
                elif result.get('status') == 'FAILED':
                    print("❌ BOOTSTRAP FAILED!")
                    error = result.get('error', 'Unknown error')
                    print(f"Error: {error}")
                    return False
                    
                else:
                    print(f"⏳ Status: {result.get('status', 'Unknown')}")
                    print("This might be a long-running operation...")
                    return False
                    
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out (this is normal for long operations)")
            print("The bootstrap is likely still running on RunPod")
            return False
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return False
    
    def check_bootstrap_status(self):
        """Check the status of bootstrap operation"""
        print("🔍 Checking bootstrap status...")
        
        # This would typically query a status endpoint
        # For now, we'll provide manual verification steps
        print("\n📋 MANUAL VERIFICATION STEPS:")
        print("1. Check RunPod console for job status")
        print("2. Verify database tables were created")
        print("3. Check data was inserted successfully")
        
        return True

def main():
    """Main deployment function"""
    
    try:
        deployer = RunPodBootstrapDeployer()
        
        print("🔧 Pre-deployment checks...")
        
        # Verify environment variables
        required_vars = ['RUNPOD_API_KEY', 'RUNPOD_ENDPOINT_ID', 'DATABASE_URL', 'FMP_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ Missing environment variables: {missing_vars}")
            print("Please check your .env file")
            return False
        
        print("✅ Environment variables configured")
        
        # Deploy bootstrap
        success = deployer.deploy_bootstrap()
        
        if success:
            print("\n🎉 BOOTSTRAP DEPLOYMENT SUCCESSFUL!")
            print("\n🚀 NEXT STEPS:")
            print("1. Verify data in database")
            print("2. Start admin dashboard")
            print("3. Test pipeline operations")
        else:
            print("\n🔧 TROUBLESHOOTING:")
            print("1. Check RunPod console for detailed logs")
            print("2. Verify endpoint is active")
            print("3. Check database connectivity from RunPod")
        
        return success
        
    except Exception as e:
        print(f"❌ Deployment setup failed: {e}")
        return False

if __name__ == "__main__":
    main()
