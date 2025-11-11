#!/usr/bin/env python3
"""
RunPod Database Bootstrap
Connects Google Cloud SQL to RunPod and runs database migration + bootstrap
"""

import os
import json
import requests
import time
from dotenv import load_dotenv

load_dotenv()

class RunPodDatabaseBootstrap:
    def __init__(self):
        self.api_key = os.getenv('RUNPOD_API_KEY')
        self.endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID', 'cf18ff49-3664-4628-bd95-aa120bb6a148')
        
        if not self.api_key:
            raise ValueError("RUNPOD_API_KEY must be set in .env")
    
    def create_bootstrap_job(self):
        """Create RunPod job for database bootstrap"""
        
        # Database connection details
        database_config = {
            "database_url": os.getenv('DATABASE_URL'),
            "host": os.getenv('DATABASE_HOST', '104.198.40.56'),
            "port": int(os.getenv('DATABASE_PORT', 5432)),
            "database": os.getenv('DATABASE_NAME', 'postgres'),
            "user": os.getenv('DATABASE_USER', 'postgres'),
            "password": os.getenv('DATABASE_PASSWORD'),
            "connection_name": os.getenv('GOOGLE_CLOUD_SQL_CONNECTION_NAME', 'bullsbears:us-central1:bullsbears-prod-db')
        }
        
        # FMP API configuration
        fmp_config = {
            "api_key": os.getenv('FMP_API_KEY'),
            "base_url": "https://financialmodelingprep.com/api/v3",
            "rate_limit": 300  # calls per minute
        }
        
        # Bootstrap job payload
        payload = {
            "input": {
                "job_type": "database_bootstrap",
                "database": database_config,
                "fmp": fmp_config,
                "operations": [
                    "test_database_connection",
                    "run_migrations", 
                    "bootstrap_90_day_data",
                    "verify_data_integrity"
                ],
                "bootstrap_config": {
                    "days": 90,
                    "symbols_limit": 1700,  # ACTIVE tier
                    "batch_size": 100
                }
            }
        }
        
        return payload
    
    def submit_job(self):
        """Submit bootstrap job to RunPod"""
        
        print("🚀 SUBMITTING DATABASE BOOTSTRAP TO RUNPOD")
        print("=" * 60)
        
        payload = self.create_bootstrap_job()
        
        print("📦 Job Configuration:")
        print(f"   - Endpoint: {self.endpoint_id}")
        print(f"   - Database: {payload['input']['database']['host']}:{payload['input']['database']['port']}")
        print(f"   - Operations: {len(payload['input']['operations'])}")
        print(f"   - Bootstrap Days: {payload['input']['bootstrap_config']['days']}")
        
        # RunPod API endpoint
        url = f"https://api.runpod.ai/v2/{self.endpoint_id}/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            print(f"\n🔌 Submitting to RunPod...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('id')
                
                print(f"✅ Job submitted successfully!")
                print(f"📋 Job ID: {job_id}")
                print(f"🔍 Status: {result.get('status', 'Unknown')}")
                
                return job_id
                
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Job submission failed: {e}")
            return None
    
    def check_job_status(self, job_id):
        """Check the status of a RunPod job"""
        
        url = f"https://api.runpod.ai/v2/{self.endpoint_id}/status/{job_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return None
    
    def monitor_job(self, job_id, max_wait_minutes=30):
        """Monitor job progress"""
        
        print(f"\n🔍 MONITORING JOB: {job_id}")
        print("=" * 60)
        
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        while time.time() - start_time < max_wait_seconds:
            status = self.check_job_status(job_id)
            
            if status:
                job_status = status.get('status', 'UNKNOWN')
                print(f"⏱️  Status: {job_status}")
                
                if job_status == 'COMPLETED':
                    output = status.get('output', {})
                    print("\n✅ BOOTSTRAP COMPLETED!")
                    print("📊 Results:")
                    
                    for key, value in output.items():
                        print(f"   - {key}: {value}")
                    
                    return True
                    
                elif job_status == 'FAILED':
                    error = status.get('error', 'Unknown error')
                    print(f"\n❌ BOOTSTRAP FAILED!")
                    print(f"Error: {error}")
                    return False
                    
                elif job_status in ['IN_QUEUE', 'IN_PROGRESS']:
                    print("   Job is running...")
                    time.sleep(30)  # Check every 30 seconds
                    
                else:
                    print(f"   Unknown status: {job_status}")
                    time.sleep(10)
            else:
                print("   Status check failed, retrying...")
                time.sleep(10)
        
        print(f"\n⏰ Job monitoring timed out after {max_wait_minutes} minutes")
        print("The job may still be running. Check RunPod console for updates.")
        return False

def main():
    """Main bootstrap function"""
    
    print("🔧 BULLSBEARS DATABASE BOOTSTRAP VIA RUNPOD")
    print("=" * 60)
    
    try:
        bootstrap = RunPodDatabaseBootstrap()
        
        # Submit the job
        job_id = bootstrap.submit_job()
        
        if job_id:
            print(f"\n🎯 Job submitted: {job_id}")
            print("🔍 Monitoring progress...")
            
            # Monitor the job
            success = bootstrap.monitor_job(job_id, max_wait_minutes=30)
            
            if success:
                print("\n🎉 DATABASE BOOTSTRAP SUCCESSFUL!")
                print("\n🚀 NEXT STEPS:")
                print("1. Verify data in admin dashboard")
                print("2. Enable pipeline in admin controls")
                print("3. Test agent processing")
            else:
                print("\n🔧 Check RunPod console for detailed logs")
                print(f"Job ID: {job_id}")
        else:
            print("\n❌ Failed to submit bootstrap job")
            
    except Exception as e:
        print(f"❌ Bootstrap setup failed: {e}")

if __name__ == "__main__":
    main()
