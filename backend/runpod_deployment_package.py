#!/usr/bin/env python3
"""
RunPod Deployment Package
Prepares and validates the complete 18-agent system for RunPod deployment
"""

import asyncio
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RunPodDeploymentPackager:
    """Packages the validated 18-agent system for RunPod deployment"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.deployment_dir = self.base_dir / "runpod_deployment_ready"
        self.package_name = f"bullsbears_18agent_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    async def create_deployment_package(self):
        """Create complete deployment package"""
        logger.info("🚀 CREATING RUNPOD DEPLOYMENT PACKAGE")
        
        # Step 1: Prepare deployment directory
        await self._prepare_deployment_directory()
        
        # Step 2: Copy validated agent system
        await self._copy_agent_system()
        
        # Step 3: Create RunPod configuration
        await self._create_runpod_config()
        
        # Step 4: Create deployment scripts
        await self._create_deployment_scripts()
        
        # Step 5: Create validation checklist
        await self._create_validation_checklist()
        
        # Step 6: Package everything
        package_path = await self._create_deployment_zip()
        
        logger.info(f"✅ Deployment package created: {package_path}")
        return package_path
    
    async def _prepare_deployment_directory(self):
        """Prepare clean deployment directory"""
        if self.deployment_dir.exists():
            shutil.rmtree(self.deployment_dir)
        
        self.deployment_dir.mkdir(parents=True)
        logger.info(f"📁 Created deployment directory: {self.deployment_dir}")
    
    async def _copy_agent_system(self):
        """Copy validated agent system files"""
        logger.info("📋 Copying validated agent system...")
        
        # Core directories to copy
        core_dirs = [
            "app/services/agents",
            "app/services/enhanced_agent_manager.py",
            "app/core",
            "app/database",
            "database/migrations"
        ]
        
        for dir_path in core_dirs:
            src = self.base_dir / dir_path
            dst = self.deployment_dir / dir_path
            
            if src.exists():
                if src.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                else:
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                logger.info(f"✅ Copied: {dir_path}")
            else:
                logger.warning(f"⚠️ Not found: {dir_path}")
    
    async def _create_runpod_config(self):
        """Create RunPod-specific configuration"""
        logger.info("⚙️ Creating RunPod configuration...")
        
        runpod_config = {
            "system_requirements": {
                "gpu": "RTX 6000 Ada (48GB VRAM)",
                "memory": "64GB+ RAM recommended",
                "storage": "50GB+ SSD",
                "python": "3.11+",
                "cuda": "12.0+"
            },
            "model_requirements": {
                "deepseek-r1:8b": "5.2GB",
                "qwen2.5:32b": "19GB", 
                "qwen3-vl:8b-instruct": "6.1GB",
                "llama3.2-vision:11b": "7.8GB",
                "llama3.2:3b": "2.0GB"
            },
            "environment_variables": {
                "RUNPOD_ENDPOINT_ID": "0bv1yn1beqszt7",
                "OLLAMA_HOST": "0.0.0.0:11434",
                "REDIS_URL": "redis://localhost:6379",
                "DATABASE_URL": "postgresql://user:pass@localhost:5432/bullsbears",
                "FMP_API_KEY": "${FMP_API_KEY}",
                "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}"
            },
            "services": {
                "ollama": {
                    "port": 11434,
                    "models_to_pull": [z
                        "finma-7b",           # Phase 1: Prescreen
                        "deepseek-r1:8b",     # Phase 2: 4 predictors + Phase 4: 2 risk
                        "qwen3:8b",           # Phase 2: 4 predictors + Phase 5: 2 target
                        "qwen3-vl:11b",       # Phase 3: 2 vision agents
                        "llama3.2:3b"         # Phase 6: RSS news agent
                    ]
                },
                "redis": {
                    "port": 6379,
                    "persistence": True
                },
                "postgresql": {
                    "port": 5432,
                    "database": "bullsbears"
                }
            },
            "agent_architecture": {
                "total_agents": 18,
                "parallel_execution": True,
                "phases": [
                    "Kill-Switch (1 agent)",
                    "Pre-Filter (1 agent)", 
                    "Core Prediction (8 agents)",
                    "Vision Analysis (2 agents)",
                    "Risk & Target (4 agents)",
                    "News & Social (2 agents)",
                    "Final Arbitration (1 agent)"
                ],
                "learning_system": [
                    "LearnerAgent (pattern discovery)",
                    "BrainAgent (orchestration)"
                ]
            }
        }
        
        config_file = self.deployment_dir / "runpod_config.json"
        with open(config_file, 'w') as f:
            json.dump(runpod_config, f, indent=2)
        
        logger.info(f"✅ RunPod configuration saved: {config_file}")
    
    async def _create_deployment_scripts(self):
        """Create deployment and startup scripts"""
        logger.info("📜 Creating deployment scripts...")
        
        # Dockerfile
        dockerfile_content = """FROM nvidia/cuda:12.0-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    python3.11 \\
    python3.11-pip \\
    python3.11-venv \\
    curl \\
    wget \\
    git \\
    redis-server \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports
EXPOSE 8000 11434 6379

# Start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
"""
        
        # Startup script
        startup_script = """#!/bin/bash
set -e

echo "🚀 Starting BullsBears 18-Agent System on RunPod"

# Start Redis
redis-server --daemonize yes --port 6379

# Start Ollama
ollama serve &
sleep 10

# Pull required models
echo "📥 Pulling AI models..."
ollama pull deepseek-r1:8b
ollama pull qwen2.5:32b  
ollama pull qwen3-vl:8b-instruct
ollama pull llama3.2-vision:11b
ollama pull llama3.2:3b

# Run database migrations
echo "🗄️ Running database migrations..."
python3.11 -m alembic upgrade head

# Start the application
echo "🎯 Starting 18-agent system..."
python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
        
        # Requirements file
        requirements_content = """fastapi==0.104.1
uvicorn==0.24.0
asyncio==3.4.3
aiohttp==3.9.1
redis==5.0.1
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
alembic==1.13.1
pydantic==2.5.0
python-multipart==0.0.6
ollama==0.1.7
openai==1.3.7
numpy==1.24.3
pandas==2.1.4
scikit-learn==1.3.2
"""
        
        # Save files
        files_to_create = {
            "Dockerfile": dockerfile_content,
            "start.sh": startup_script,
            "requirements.txt": requirements_content
        }
        
        for filename, content in files_to_create.items():
            file_path = self.deployment_dir / filename
            with open(file_path, 'w') as f:
                f.write(content)
            
            if filename.endswith('.sh'):
                os.chmod(file_path, 0o755)
            
            logger.info(f"✅ Created: {filename}")
    
    async def _create_validation_checklist(self):
        """Create deployment validation checklist"""
        logger.info("✅ Creating validation checklist...")
        
        checklist = """# BullsBears 18-Agent System - RunPod Deployment Checklist

## Pre-Deployment Validation ✅

### 1. Model Availability
- [ ] deepseek-r1:8b (5.2GB) - Reasoning agents
- [ ] qwen2.5:32b (19GB) - Complex analysis agents  
- [ ] qwen3-vl:8b-instruct (6.1GB) - Visual analysis agents
- [ ] llama3.2-vision:11b (7.8GB) - Secondary vision agent
- [ ] llama3.2:3b (2.0GB) - Fast pre-filter agent

### 2. Agent Role Clarity
- [ ] KillSwitchAgent: Market condition override
- [ ] PreFilterAgent: 2,000 → 200 candidate screening
- [ ] 8x Core Prediction Agents: Bull/Bear Technical/Fundamental/Sentiment
- [ ] 2x Vision Agents: Chart pattern analysis
- [ ] 4x Risk/Target Agents: Risk management and price targets
- [ ] 2x News/Social Agents: External data analysis
- [ ] ArbitratorAgent: Final selection with learned weights
- [ ] LearnerAgent: Pattern discovery from historical data
- [ ] BrainAgent: Learning orchestration and weight updates

### 3. Historical Data Access ⚠️ CRITICAL
- [ ] ArbitratorAgent has Redis access for learned weights
- [ ] LearnerAgent has database access for historical analysis
- [ ] BrainAgent has candidate tracking service integration
- [ ] All predictor candidates are stored for learning
- [ ] Weekly learning cycles update arbitrator weights

### 4. Data Flow Pipeline
- [ ] Phase 1: Kill-Switch → Pre-Filter
- [ ] Phase 2: 8x Predictors (parallel execution)
- [ ] Phase 3: 2x Vision Analysis (consensus)
- [ ] Phase 4: 4x Risk/Target Analysis
- [ ] Phase 5: 2x News/Social Analysis
- [ ] Phase 6: Final Arbitration with learned weights
- [ ] Phase 7: Candidate storage for learning

### 5. Learning System Integration
- [ ] Weekly learning cycles (7 days OR success_rate < 30%)
- [ ] Real-time candidate tracking
- [ ] Dynamic weight optimization
- [ ] Missed opportunity analysis
- [ ] Arbitrator prompt updates

## Deployment Steps

1. **Upload to RunPod**
   ```bash
   # Upload deployment package to RunPod endpoint 0bv1yn1beqszt7
   ```

2. **Environment Setup**
   ```bash
   # Set environment variables
   export FMP_API_KEY="your_fmp_key"
   export OPENROUTER_API_KEY="your_openrouter_key"
   ```

3. **Start Services**
   ```bash
   # Run startup script
   ./start.sh
   ```

4. **Validate System**
   ```bash
   # Test complete pipeline
   python3.11 test_runpod_system.py
   ```

## Performance Expectations

- **Model Loading**: ~5-10 minutes (first time)
- **Single Analysis Cycle**: ~5-10 seconds (all 18 agents)
- **Memory Usage**: ~35-40GB (all models loaded)
- **Cost**: ~$0.79/hour (RTX 6000 Ada)
- **Daily Cost**: ~$3-6 (assuming 10 analysis cycles)

## Critical Success Factors

1. **All models must load successfully**
2. **Redis must be accessible for learned weights**
3. **Database must be connected for historical data**
4. **Parallel execution must work (18 agents simultaneously)**
5. **Learning system must update weights weekly**

## Troubleshooting

- **Model loading fails**: Check VRAM availability (need 48GB+)
- **Redis connection fails**: Verify Redis service is running
- **Database connection fails**: Check PostgreSQL connection string
- **Slow performance**: Verify GPU utilization and memory usage
- **Learning system fails**: Check candidate tracking service integration
"""
        
        checklist_file = self.deployment_dir / "DEPLOYMENT_CHECKLIST.md"
        with open(checklist_file, 'w') as f:
            f.write(checklist)
        
        logger.info(f"✅ Validation checklist saved: {checklist_file}")
    
    async def _create_deployment_zip(self):
        """Create final deployment zip package"""
        logger.info("📦 Creating deployment zip package...")
        
        zip_path = self.base_dir / f"{self.package_name}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.deployment_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(self.deployment_dir)
                    zipf.write(file_path, arc_path)
        
        # Get zip size
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        logger.info(f"📦 Package size: {zip_size_mb:.1f} MB")
        
        return zip_path

async def main():
    """Create RunPod deployment package"""
    packager = RunPodDeploymentPackager()
    
    try:
        package_path = await packager.create_deployment_package()
        
        logger.info("=" * 80)
        logger.info("🎯 RUNPOD DEPLOYMENT PACKAGE READY")
        logger.info("=" * 80)
        logger.info(f"📦 Package: {package_path}")
        logger.info(f"🚀 Endpoint: 0bv1yn1beqszt7")
        logger.info(f"💰 Expected Cost: ~$3-6/day")
        logger.info(f"⚡ Performance: 5-10 seconds per analysis cycle")
        logger.info("=" * 80)
        logger.info("🔍 NEXT STEPS:")
        logger.info("1. Upload package to RunPod")
        logger.info("2. Set environment variables (FMP_API_KEY, OPENROUTER_API_KEY)")
        logger.info("3. Run ./start.sh to initialize system")
        logger.info("4. Validate with test_runpod_system.py")
        logger.info("5. Monitor learning system integration")
        logger.info("=" * 80)
        
        return package_path
        
    except Exception as e:
        logger.error(f"Package creation failed: {str(e)}")
        return None

if __name__ == "__main__":
    asyncio.run(main())
