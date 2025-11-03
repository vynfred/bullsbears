#!/usr/bin/env python3
"""
Full ML Training Pipeline
Runs the complete pipeline: Data Collection → Move Detection → Feature Extraction → ML Training
"""

import asyncio
import logging
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def run_script(script_name: str, description: str) -> bool:
    """Run a Python script and return success status."""
    logger.info(f"🚀 Starting: {description}")
    logger.info(f"📜 Running: {script_name}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run([
            sys.executable, script_name
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            logger.info(f"✅ {description} completed successfully in {duration:.1f}s")
            if result.stdout:
                logger.info("📄 Output:")
                for line in result.stdout.strip().split('\n')[-10:]:  # Last 10 lines
                    logger.info(f"   {line}")
            return True
        else:
            logger.error(f"❌ {description} failed after {duration:.1f}s")
            logger.error(f"Return code: {result.returncode}")
            if result.stderr:
                logger.error("Error output:")
                for line in result.stderr.strip().split('\n'):
                    logger.error(f"   {line}")
            return False
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"💥 {description} crashed after {duration:.1f}s: {e}")
        return False


def check_prerequisites() -> bool:
    """Check if all prerequisites are met."""
    logger.info("🔍 Checking prerequisites...")
    
    # Check environment variables
    import os
    if not os.getenv('DATABENTO_API_KEY'):
        logger.error("❌ DATABENTO_API_KEY environment variable not found!")
        return False
    
    # Check data directory
    data_dir = Path("data/backtest")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Check NASDAQ CSV file
    nasdaq_file = Path("../Data/nasdaq_screener_1762100638908.csv")
    if not nasdaq_file.exists():
        logger.error(f"❌ NASDAQ CSV file not found: {nasdaq_file}")
        return False
    
    logger.info("✅ All prerequisites met!")
    return True


def estimate_pipeline_duration() -> str:
    """Estimate total pipeline duration."""
    # Rough estimates based on API limits and processing time
    data_collection = 120  # 2 hours for 6,961 stocks
    move_detection = 30    # 30 minutes for analysis
    feature_extraction = 45  # 45 minutes for features
    ml_training = 15       # 15 minutes for training
    
    total_minutes = data_collection + move_detection + feature_extraction + ml_training
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    return f"{hours}h {minutes}m"


async def main():
    """Run the complete ML training pipeline."""
    logger.info("🎯 BullsBears.xyz - Full ML Training Pipeline")
    logger.info("=" * 70)
    
    pipeline_start = datetime.now()
    
    # Check prerequisites
    if not check_prerequisites():
        logger.error("💥 Prerequisites not met. Exiting.")
        return False
    
    # Estimate duration
    estimated_duration = estimate_pipeline_duration()
    logger.info(f"⏰ Estimated total duration: {estimated_duration}")
    logger.info(f"🚀 Pipeline started at: {pipeline_start}")
    logger.info("=" * 70)
    
    # Pipeline steps
    steps = [
        ("run_full_data_collection.py", "Full NASDAQ Data Collection (6 months, 6,961 stocks)"),
        ("run_full_move_detection.py", "Move Detection (+20%/-20% events identification)"),
        ("run_feature_extraction.py", "Feature Extraction (Technical indicators, sentiment)"),
        ("run_ml_training.py", "ML Model Training (RandomForest with cross-validation)")
    ]
    
    successful_steps = 0
    
    for i, (script, description) in enumerate(steps, 1):
        logger.info(f"📋 STEP {i}/{len(steps)}: {description}")
        logger.info("-" * 50)
        
        step_start = time.time()
        success = run_script(script, description)
        step_duration = time.time() - step_start
        
        if success:
            successful_steps += 1
            logger.info(f"✅ Step {i} completed in {step_duration/60:.1f} minutes")
        else:
            logger.error(f"❌ Step {i} failed after {step_duration/60:.1f} minutes")
            logger.error(f"💥 Pipeline stopped at step {i}")
            break
        
        logger.info("-" * 50)
        
        # Brief pause between steps
        if i < len(steps):
            logger.info("⏸️  Brief pause before next step...")
            await asyncio.sleep(5)
    
    pipeline_end = datetime.now()
    total_duration = pipeline_end - pipeline_start
    
    # Final summary
    logger.info("=" * 70)
    if successful_steps == len(steps):
        logger.info("🎉 FULL PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("🚀 BullsBears.xyz is ready for production deployment!")
    else:
        logger.info(f"⚠️  PIPELINE PARTIALLY COMPLETED ({successful_steps}/{len(steps)} steps)")
        logger.info("🔧 Check logs above for failed steps and retry.")
    
    logger.info("=" * 70)
    logger.info(f"⏱️  Total pipeline duration: {total_duration}")
    logger.info(f"📊 Successful steps: {successful_steps}/{len(steps)}")
    logger.info(f"🏁 Pipeline ended at: {pipeline_end}")
    
    # Next steps guidance
    if successful_steps == len(steps):
        logger.info("🎯 NEXT STEPS:")
        logger.info("   1. Review ML model performance metrics")
        logger.info("   2. Test daily scanning service")
        logger.info("   3. Deploy to production environment")
        logger.info("   4. Set up monitoring and alerting")
    
    return successful_steps == len(steps)


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logger.info("🚀 Full pipeline completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Pipeline failed. Check individual step logs.")
        sys.exit(1)
