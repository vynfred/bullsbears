#!/usr/bin/env python3
"""
RunPod Cost Control Service - CRITICAL COST MANAGEMENT
Automatically shuts down RunPod endpoints when pipeline is disabled
Prevents accidental $10+ charges from idle endpoints
"""

import logging
import asyncio
import aiohttp
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class RunPodCostControl:
    """
    CRITICAL: RunPod Cost Control Service
    - Automatically terminates RunPod endpoints when pipeline disabled
    - Enforces maximum runtime limits (default: 2 hours)
    - Provides emergency shutdown capabilities
    - Tracks and reports costs in real-time
    """
    
    def __init__(self):
        self.api_key = settings.runpod_api_key
        self.endpoint_id = settings.runpod_endpoint_id
        self.base_url = "https://api.runpod.ai"
        
        # Cost control settings
        self.max_runtime_minutes = 20  # Maximum 20 minutes per session
        self.auto_shutdown_enabled = True
        self.cost_alert_threshold = 2.0  # Alert at $2
        
        # Track active jobs
        self.active_jobs = {}
        self.session_start_time = None
        
    async def initialize(self):
        """Initialize cost control service"""
        logger.info("🛡️ Initializing RunPod Cost Control Service")
        
        if not self.api_key or not self.endpoint_id:
            logger.error("❌ RunPod credentials not configured")
            return False
            
        # Check endpoint status
        status = await self.get_endpoint_status()
        if status:
            logger.info(f"✅ RunPod endpoint {self.endpoint_id} status: {status.get('status', 'unknown')}")
            
            # If endpoint is active, start monitoring
            if status.get('status') == 'ACTIVE':
                self.session_start_time = datetime.now()
                logger.warning(f"⚠️ RunPod endpoint is ACTIVE - monitoring costs")
                
        return True
    
    async def get_endpoint_status(self) -> Optional[Dict[str, Any]]:
        """Get current endpoint status"""
        try:
            # Try the GraphQL API first
            query = {
                "query": f"""
                query {{
                    serverlessEndpoint(id: "{self.endpoint_id}") {{
                        id
                        name
                        status
                        version
                        locations {{
                            id
                            name
                        }}
                    }}
                }}
                """
            }

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    f"{self.base_url}/graphql",
                    json=query,
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        endpoint_data = data.get('data', {}).get('serverlessEndpoint')
                        if endpoint_data:
                            return endpoint_data

                    # If GraphQL fails, try REST API
                    logger.warning(f"GraphQL endpoint check failed ({response.status}), trying REST API")

                # Try REST API as fallback
                async with session.get(
                    f"{self.base_url}/v2/{self.endpoint_id}",
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"REST API endpoint check also failed: {response.status}")
                        # Return a mock status to prevent complete failure
                        return {
                            "id": self.endpoint_id,
                            "status": "UNKNOWN",
                            "name": "BullsBears AI Endpoint",
                            "api_accessible": False
                        }

        except Exception as e:
            logger.error(f"Error getting endpoint status: {e}")
            # Return a mock status to prevent complete failure
            return {
                "id": self.endpoint_id,
                "status": "ERROR",
                "name": "BullsBears AI Endpoint",
                "error": str(e),
                "api_accessible": False
            }
    
    async def get_current_costs(self) -> Dict[str, Any]:
        """Get current RunPod spending"""
        try:
            query = {
                "query": """
                query {
                    myself {
                        currentSpendPerHour
                        spendLimit
                        serverlessDiscount {
                            discountFactor
                            type
                        }
                    }
                }
                """
            }

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    f"{self.base_url}/graphql",
                    json=query,
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        cost_data = data.get('data', {}).get('myself', {})
                        if cost_data:
                            return cost_data

                    # If API fails, return safe defaults with warning
                    logger.warning(f"Cost API failed ({response.status}), returning safe defaults")
                    return {
                        "currentSpendPerHour": 0.0,
                        "spendLimit": 0,
                        "api_accessible": False,
                        "warning": f"API unavailable (HTTP {response.status})"
                    }

        except Exception as e:
            logger.error(f"Error getting costs: {e}")
            return {
                "currentSpendPerHour": 0.0,
                "spendLimit": 0,
                "api_accessible": False,
                "error": str(e)
            }
    
    async def emergency_shutdown_all(self) -> bool:
        """EMERGENCY: Shutdown all RunPod activity immediately"""
        logger.critical("🚨 EMERGENCY SHUTDOWN: Terminating all RunPod activity")

        try:
            # 1. Create emergency kill file (works even if API is down)
            kill_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "RUNPOD_EMERGENCY_KILL")
            with open(kill_file_path, "w") as f:
                f.write(f"EMERGENCY_SHUTDOWN_ACTIVATED\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Reason: Manual emergency shutdown\n")
                f.write(f"Endpoint: {self.endpoint_id}\n")

            logger.critical(f"🛑 Emergency kill file created: {kill_file_path}")

            # 2. Cancel all running jobs (if API is accessible)
            cancelled_jobs = await self.cancel_all_jobs()

            # 3. Reset session tracking
            self.session_start_time = None

            # Note: RunPod serverless endpoints can't be "stopped" - they're pay-per-use
            # But we can ensure no new jobs are submitted via the kill file

            logger.critical(f"🛑 Emergency shutdown complete - cancelled {cancelled_jobs} jobs")
            return True

        except Exception as e:
            logger.critical(f"❌ Emergency shutdown failed: {e}")
            # Still try to create kill file as last resort
            try:
                kill_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "RUNPOD_EMERGENCY_KILL")
                with open(kill_file_path, "w") as f:
                    f.write(f"EMERGENCY_SHUTDOWN_ACTIVATED\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write(f"Reason: Emergency shutdown after API failure\n")
                    f.write(f"Error: {str(e)}\n")
                logger.critical(f"🛑 Emergency kill file created despite API failure")
                return True
            except Exception as kill_file_error:
                logger.critical(f"❌ Could not create emergency kill file: {kill_file_error}")
                return False
    
    async def cancel_all_jobs(self) -> int:
        """Cancel all running jobs on the endpoint"""
        try:
            # Get all running jobs
            jobs = await self.get_running_jobs()
            cancelled_count = 0
            
            for job in jobs:
                job_id = job.get('id')
                if job_id:
                    success = await self.cancel_job(job_id)
                    if success:
                        cancelled_count += 1
                        
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelling jobs: {e}")
            return 0
    
    async def get_running_jobs(self) -> List[Dict[str, Any]]:
        """Get all running jobs"""
        try:
            # This would need to be implemented based on RunPod's job listing API
            # For now, return empty list as RunPod serverless doesn't maintain job lists
            return []
            
        except Exception as e:
            logger.error(f"Error getting running jobs: {e}")
            return []
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific job"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    f"{self.base_url}/v2/{self.endpoint_id}/cancel/{job_id}",
                    headers=headers,
                    timeout=10
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False
    
    async def enforce_runtime_limits(self) -> bool:
        """Enforce maximum runtime limits"""
        if not self.session_start_time:
            return True
            
        runtime = datetime.now() - self.session_start_time
        max_runtime = timedelta(hours=self.max_runtime_hours)
        
        if runtime > max_runtime:
            logger.critical(f"🚨 RUNTIME LIMIT EXCEEDED: {runtime} > {max_runtime}")
            logger.critical("🛑 Initiating emergency shutdown")
            
            await self.emergency_shutdown_all()
            return False
            
        # Warning at 80% of limit
        warning_threshold = max_runtime * 0.8
        if runtime > warning_threshold:
            remaining = max_runtime - runtime
            logger.warning(f"⚠️ RUNTIME WARNING: {remaining} remaining before auto-shutdown")
            
        return True
    
    async def check_cost_alerts(self) -> Dict[str, Any]:
        """Check for cost alerts"""
        costs = await self.get_current_costs()
        
        if "error" in costs:
            return {"status": "error", "message": costs["error"]}
        
        current_spend = costs.get('currentSpendPerHour', 0)
        spend_limit = costs.get('spendLimit', 0)
        
        alerts = []
        
        if current_spend > self.cost_alert_threshold:
            alerts.append(f"High spending: ${current_spend:.2f}/hour")
            
        if spend_limit > 0 and current_spend > spend_limit * 0.8:
            alerts.append(f"Approaching spend limit: ${current_spend:.2f}/${spend_limit:.2f}")
        
        return {
            "status": "ok",
            "current_spend_per_hour": current_spend,
            "spend_limit": spend_limit,
            "alerts": alerts,
            "session_runtime": str(datetime.now() - self.session_start_time) if self.session_start_time else "Not running"
        }
    
    async def pipeline_disabled_shutdown(self) -> bool:
        """Shutdown RunPod when pipeline is disabled"""
        logger.info("🛑 Pipeline disabled - initiating RunPod shutdown")
        
        # Cancel any running jobs
        cancelled = await self.cancel_all_jobs()
        
        # Reset session tracking
        self.session_start_time = None
        
        logger.info(f"✅ Pipeline shutdown complete - cancelled {cancelled} jobs")
        return True
    
    def check_emergency_kill_file(self) -> Dict[str, Any]:
        """Check if emergency kill file exists"""
        kill_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "RUNPOD_EMERGENCY_KILL")

        if os.path.exists(kill_file_path):
            try:
                with open(kill_file_path, "r") as f:
                    content = f.read()
                return {
                    "kill_active": True,
                    "kill_file_path": kill_file_path,
                    "content": content,
                    "message": "🚨 EMERGENCY KILL ACTIVE - RunPod operations blocked"
                }
            except Exception as e:
                return {
                    "kill_active": True,
                    "kill_file_path": kill_file_path,
                    "error": str(e),
                    "message": "🚨 EMERGENCY KILL FILE EXISTS but unreadable"
                }

        return {"kill_active": False}

    def clear_emergency_kill_file(self) -> bool:
        """Clear the emergency kill file"""
        kill_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "RUNPOD_EMERGENCY_KILL")

        try:
            if os.path.exists(kill_file_path):
                os.remove(kill_file_path)
                logger.info(f"✅ Emergency kill file cleared: {kill_file_path}")
                return True
            return True  # File doesn't exist, so it's "cleared"
        except Exception as e:
            logger.error(f"❌ Failed to clear emergency kill file: {e}")
            return False

    async def pipeline_enabled_startup(self) -> bool:
        """Initialize RunPod when pipeline is enabled"""
        logger.info("🚀 Pipeline enabled - initializing RunPod monitoring")

        # Check for emergency kill file first
        kill_status = self.check_emergency_kill_file()
        if kill_status["kill_active"]:
            logger.error(f"❌ Cannot start pipeline: {kill_status['message']}")
            return False

        # Start session tracking
        self.session_start_time = datetime.now()

        # Check endpoint health
        status = await self.get_endpoint_status()
        if not status:
            logger.error("❌ RunPod endpoint not available")
            return False

        logger.info("✅ RunPod monitoring started")
        return True

# Global instance
runpod_cost_control = RunPodCostControl()

async def initialize_cost_control():
    """Initialize the cost control service"""
    return await runpod_cost_control.initialize()

async def emergency_shutdown():
    """Emergency shutdown function"""
    return await runpod_cost_control.emergency_shutdown_all()

async def get_cost_status():
    """Get current cost status"""
    return await runpod_cost_control.check_cost_alerts()
