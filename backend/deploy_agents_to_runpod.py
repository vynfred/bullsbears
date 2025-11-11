#!/usr/bin/env python3
"""
BullsBears AI - Deploy 18-Agent System to RunPod
Comprehensive deployment script for the complete agent pipeline
"""

import os
import sys
import shutil
import requests
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv  # Add this import

# Load environment variables from .env file
load_dotenv()  # Add this line at the top

class RunPodAgentDeployer:
    def __init__(self):
        # Load .env file explicitly
        load_dotenv()
        
        self.runpod_api_key = os.getenv('RUNPOD_API_KEY')
        self.endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID')
        self.database_url = os.getenv('DATABASE_URL')
        self.fmp_api_key = os.getenv('FMP_API_KEY')

        # Debug: Print what we found
        print(f"🔍 Debug - API Key found: {'Yes' if self.runpod_api_key else 'No'}")
        print(f"🔍 Debug - Endpoint ID: {self.endpoint_id}")

        # Validate required environment variables
        if not self.runpod_api_key:
            print("❌ RUNPOD_API_KEY not found in environment")
            print("💡 Check your .env file contains: RUNPOD_API_KEY=your_key")
            raise ValueError("RUNPOD_API_KEY environment variable is required")
        if not self.endpoint_id:
            raise ValueError("RUNPOD_ENDPOINT_ID environment variable is required")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        if not self.fmp_api_key:
            raise ValueError("FMP_API_KEY environment variable is required")
        
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.runpod_api_key}"
        }
        
    def test_endpoint_health(self) -> bool:
        """Test if RunPod endpoint is responding"""
        try:
            print("🔍 Testing RunPod endpoint health...")
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json={"input": {"test": "health_check"}},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Endpoint responding: {result.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Endpoint error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Endpoint connection failed: {e}")
            return False
    
    def create_deployment_package(self) -> Path:
        """Create deployment package with all agent files"""
        print("📦 Creating deployment package...")
        
        deploy_dir = Path("runpod_deployment")
        deploy_dir.mkdir(exist_ok=True)
        
        # Agent files to include (relative to backend directory)
        agent_files = [
            "app/services/agents/__init__.py",
            "app/services/agents/base_agent.py",
            "app/services/agents/predictor_agents.py",
            "app/services/agents/enhanced_agents.py",
            "app/services/agents/specialized_agents.py",
            "app/services/agents/learner_agent.py",
            "app/services/agents/brain_agent.py",
            "app/services/agents/enhanced_arbitrator_agent.py",
            "app/services/agents/social_agents.py",

            "app/services/agents/ollama_news_filter.py",
            "app/services/agent_manager.py",
            "app/services/ollama_client.py",

            "app/services/candidate_tracking_service.py",
            "app/core/database.py",
            "app/core/config.py",
            "app/models/pick_candidates.py"
        ]
        
        # Copy agent files
        for file_path in agent_files:
            if Path(file_path).exists():
                dest_path = deploy_dir / file_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                print(f"   ✅ {file_path}")
            else:
                print(f"   ⚠️  Missing: {file_path}")
        
        # Copy prompt files
        prompt_dir = Path("app/services/agents/prompts")
        if prompt_dir.exists():
            dest_prompt_dir = deploy_dir / "app/services/agents/prompts"
            shutil.copytree(prompt_dir, dest_prompt_dir, dirs_exist_ok=True)
            print(f"   ✅ Copied all prompt files")
        
        # Create environment file
        env_content = f"""# BullsBears AI - RunPod Environment
DATABASE_URL={self.database_url}
FMP_API_KEY={self.fmp_api_key}
RUNPOD_API_KEY={self.runpod_api_key}
OLLAMA_HOST=0.0.0.0:11434
PYTHONPATH=/workspace
DEBUG=false
LOG_LEVEL=INFO
"""
        
        with open(deploy_dir / ".env", "w") as f:
            f.write(env_content)
        print("   ✅ Created .env file")
        
        # Create requirements.txt
        requirements = """fastapi==0.104.1
uvicorn==0.24.0
asyncio
aiohttp==3.9.1
asyncpg==0.29.0
python-dotenv==1.0.0
yfinance==0.2.28
pandas==2.1.4
numpy==1.24.4
sqlalchemy==2.0.23
pydantic==2.5.2
runpod==1.6.2
"""
        
        with open(deploy_dir / "requirements.txt", "w") as f:
            f.write(requirements)
        print("   ✅ Created requirements.txt")
        
        return deploy_dir
    
    def create_runpod_handler(self, deploy_dir: Path):
        """Create RunPod serverless handler"""
        handler_content = '''#!/usr/bin/env python3
"""
BullsBears RunPod Serverless Handler
Handles requests to the 18-agent system
"""

import runpod
import asyncio
import json
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append('/workspace/backend')

async def run_agent_analysis(job_input):
    """Run the complete agent analysis pipeline"""
    try:
        from app.services.agent_manager import AgentManager
        from app.services.candidate_tracking_service import get_candidate_tracking_service
        
        # Initialize agent manager
        print("🔧 Initializing Agent Manager...")
        agent_manager = AgentManager()
        await agent_manager.initialize()
        
        print(f"✅ Agent Manager initialized with {len(agent_manager.agents)} agents")
        
        # Get input data
        tickers = job_input.get('tickers', [])
        analysis_type = job_input.get('analysis_type', 'full')
        
        if not tickers:
            return {"error": "No tickers provided"}
        
        print(f"🔍 Running analysis for {len(tickers)} tickers...")
        
        # Run analysis
        results = await agent_manager.run_full_analysis({
            'tickers': tickers,
            'analysis_type': analysis_type
        })
        
        # Store candidates if tracking enabled
        candidates_stored = 0
        if job_input.get('store_candidates', True):
            try:
                async with await get_candidate_tracking_service() as tracking_service:
                    for result in results.get('candidates', []):
                        await tracking_service.store_candidate(result, 'runpod_analysis')
                        candidates_stored += 1
            except Exception as e:
                print(f"⚠️ Candidate tracking error: {e}")
        
        return {
            "success": True,
            "results": results,
            "agent_count": len(agent_manager.agents),
            "candidates_stored": candidates_stored,
            "tickers_processed": len(tickers)
        }
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def handler(job):
    """RunPod serverless handler"""
    job_input = job["input"]
    
    # Handle health check
    if job_input.get("test") == "health_check":
        return {
            "success": True,
            "message": "BullsBears AI Agents - Healthy",
            "timestamp": str(asyncio.get_event_loop().time())
        }
    
    # Run async analysis
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(run_agent_analysis(job_input))
        return result
    finally:
        loop.close()

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
'''
        
        with open(deploy_dir / "runpod_handler.py", "w") as f:
            f.write(handler_content)
        print("   ✅ Created runpod_handler.py")
    
    def deploy_to_runpod(self) -> bool:
        """Deploy the agent system to RunPod"""
        try:
            print("🚀 Starting RunPod deployment...")
            
            # Test endpoint first
            if not self.test_endpoint_health():
                print("❌ Endpoint not responding, cannot deploy")
                return False
            
            # Create deployment package
            deploy_dir = self.create_deployment_package()
            self.create_runpod_handler(deploy_dir)
            
            # Test with a simple agent initialization
            print("🧪 Testing agent initialization...")
            test_payload = {
                "input": {
                    "tickers": ["AAPL"],
                    "analysis_type": "test",
                    "store_candidates": False
                }
            }
            
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json=test_payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Test deployment successful: {result}")
                return True
            else:
                print(f"❌ Test deployment failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            return False

async def main():
    """Main deployment function"""
    print("🎯 BullsBears AI - RunPod Agent Deployment")
    print("=" * 50)
    
    deployer = RunPodAgentDeployer()
    
    # Deploy agents
    if deployer.deploy_to_runpod():
        print("\n🎉 Deployment successful!")
        print("📊 Next steps:")
        print("   1. Test with surveillance data")
        print("   2. Run full pipeline test")
        print("   3. Generate production picks")
    else:
        print("\n❌ Deployment failed!")
        print("🔧 Check logs and retry")

if __name__ == "__main__":
    asyncio.run(main())
