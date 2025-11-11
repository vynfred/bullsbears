#!/usr/bin/env python3
"""
Deploy BullsBears AI Agents to RunPod Container
Creates a complete deployment package and uploads to RunPod
"""

import os
import json
import zipfile
import shutil
from pathlib import Path
import requests

class RunPodContainerDeployer:
    def __init__(self):
        self.runpod_api_key = os.getenv('RUNPOD_API_KEY')
        if not self.runpod_api_key:
            raise ValueError("RUNPOD_API_KEY environment variable is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.runpod_api_key}",
            "Content-Type": "application/json"
        }
    
    def create_dockerfile(self, deploy_dir: Path):
        """Create Dockerfile for RunPod deployment"""
        dockerfile_content = '''# BullsBears AI - RunPod Deployment
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    wget \\
    git \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Copy application files
COPY . /workspace/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies
RUN pip install runpod asyncpg python-dotenv

# Download required models (this will take time on first run)
RUN ollama serve & \\
    sleep 10 && \\
    ollama pull deepseek-r1:8b && \\
    ollama pull qwen2.5:32b && \\
    ollama pull llama3.2-vision:11b && \\
    pkill ollama

# Set environment variables
ENV PYTHONPATH=/workspace
ENV OLLAMA_HOST=0.0.0.0:11434

# Expose port
EXPOSE 8000

# Start script
CMD ["python", "runpod_handler.py"]
'''
        
        with open(deploy_dir / "Dockerfile", "w") as f:
            f.write(dockerfile_content)
        print("   ✅ Created Dockerfile")
    
    def create_deployment_package(self) -> Path:
        """Create complete deployment package"""
        print("📦 Creating RunPod deployment package...")
        
        deploy_dir = Path("runpod_container_deploy")
        if deploy_dir.exists():
            shutil.rmtree(deploy_dir)
        deploy_dir.mkdir()
        
        # Core agent files
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
            print("   ✅ Copied all prompt files")
        
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
requests==2.31.0
"""
        
        with open(deploy_dir / "requirements.txt", "w") as f:
            f.write(requirements)
        print("   ✅ Created requirements.txt")
        
        # Create environment template (no actual keys)
        env_template = """# BullsBears AI - Environment Variables
# Set these in RunPod environment settings:
DATABASE_URL=postgresql://user:pass@host:port/db
FMP_API_KEY=your_fmp_api_key_here
GROK_API_KEY=your_grok_api_key_here
OLLAMA_HOST=0.0.0.0:11434
PYTHONPATH=/workspace
DEBUG=false
LOG_LEVEL=INFO
"""
        
        with open(deploy_dir / ".env.template", "w") as f:
            f.write(env_template)
        print("   ✅ Created .env.template")
        
        # Create RunPod handler
        self.create_runpod_handler(deploy_dir)
        
        # Create Dockerfile
        self.create_dockerfile(deploy_dir)
        
        # Create deployment instructions
        instructions = """# BullsBears AI - RunPod Deployment Instructions

## 1. Upload this package to RunPod

## 2. Set Environment Variables in RunPod:
- DATABASE_URL: Your PostgreSQL connection string
- FMP_API_KEY: Your Financial Modeling Prep API key
- GROK_API_KEY: Your Grok API key (optional)

## 3. Build and Deploy:
The Dockerfile will automatically:
- Install Ollama
- Download required models (deepseek-r1:8b, qwen2.5:32b, llama3.2-vision:11b)
- Set up the agent system

## 4. Test:
Send POST request to your endpoint with:
{
  "input": {
    "tickers": ["AAPL", "TSLA"],
    "analysis_type": "full",
    "store_candidates": true
  }
}
"""
        
        with open(deploy_dir / "DEPLOYMENT_INSTRUCTIONS.md", "w") as f:
            f.write(instructions)
        print("   ✅ Created deployment instructions")
        
        return deploy_dir
    
    def create_runpod_handler(self, deploy_dir: Path):
        """Create optimized RunPod handler"""
        handler_content = '''#!/usr/bin/env python3
"""
BullsBears RunPod Handler - Optimized for Container Deployment
"""

import runpod
import asyncio
import json
import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add to Python path
sys.path.append('/workspace')

async def run_agent_analysis(job_input):
    """Run the complete agent analysis pipeline"""
    try:
        logger.info("🔧 Initializing Agent Manager...")
        
        # Import here to avoid startup issues
        from app.services.agent_manager import AgentManager
        from app.services.candidate_tracking_service import get_candidate_tracking_service
        
        # Initialize agent manager
        agent_manager = AgentManager()
        await agent_manager.initialize()
        
        logger.info(f"✅ Agent Manager initialized with {len(agent_manager.agents)} agents")
        
        # Get input data
        tickers = job_input.get('tickers', [])
        analysis_type = job_input.get('analysis_type', 'full')
        store_candidates = job_input.get('store_candidates', True)
        
        if not tickers:
            return {"error": "No tickers provided", "success": False}
        
        logger.info(f"🔍 Running {analysis_type} analysis for {len(tickers)} tickers...")
        
        # Run analysis
        results = await agent_manager.run_full_analysis({
            'tickers': tickers,
            'analysis_type': analysis_type
        })
        
        # Store candidates if requested
        candidates_stored = 0
        if store_candidates and results.get('candidates'):
            try:
                async with await get_candidate_tracking_service() as tracking_service:
                    for result in results.get('candidates', []):
                        await tracking_service.store_candidate(result, 'runpod_analysis')
                        candidates_stored += 1
                logger.info(f"📊 Stored {candidates_stored} candidates")
            except Exception as e:
                logger.warning(f"⚠️ Candidate tracking error: {e}")
        
        return {
            "success": True,
            "results": results,
            "agent_count": len(agent_manager.agents),
            "candidates_stored": candidates_stored,
            "tickers_processed": len(tickers)
        }
        
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
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
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_agent_analysis(job_input))
        return result
    except Exception as e:
        logger.error(f"❌ Handler error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        loop.close()

if __name__ == "__main__":
    logger.info("🚀 Starting BullsBears AI RunPod Handler...")
    runpod.serverless.start({"handler": handler})
'''
        
        with open(deploy_dir / "runpod_handler.py", "w") as f:
            f.write(handler_content)
        print("   ✅ Created optimized RunPod handler")
    
    def create_zip_package(self, deploy_dir: Path) -> Path:
        """Create ZIP package for upload"""
        zip_path = Path("bullsbears_runpod_deployment.zip")
        
        print(f"📦 Creating ZIP package: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in deploy_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(deploy_dir)
                    zipf.write(file_path, arcname)
                    
        print(f"✅ ZIP package created: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
        return zip_path

def main():
    """Main deployment function"""
    print("🎯 BullsBears AI - RunPod Container Deployment")
    print("=" * 60)
    
    try:
        deployer = RunPodContainerDeployer()
        
        # Create deployment package
        deploy_dir = deployer.create_deployment_package()
        
        # Create ZIP for upload
        zip_path = deployer.create_zip_package(deploy_dir)
        
        print(f"\n🎉 Deployment package ready!")
        print(f"📁 Package location: {zip_path.absolute()}")
        print(f"\n📋 Next steps:")
        print(f"   1. Upload {zip_path} to RunPod")
        print(f"   2. Set environment variables in RunPod dashboard")
        print(f"   3. Build and deploy the container")
        print(f"   4. Test with surveillance data")
        
        print(f"\n🔑 Required Environment Variables:")
        print(f"   - DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
        print(f"   - FMP_API_KEY: {'Set' if os.getenv('FMP_API_KEY') else 'Not set'}")
        print(f"   - GROK_API_KEY: {'Set' if os.getenv('GROK_API_KEY') else 'Not set'}")
        
    except Exception as e:
        print(f"❌ Deployment preparation failed: {e}")

if __name__ == "__main__":
    main()
