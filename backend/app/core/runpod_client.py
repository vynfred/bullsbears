#!/usr/bin/env python3
"""
RunPod Serverless Client – BullsBears v3.3 (November 14, 2025)
Handles all communication with RunPod serverless endpoint for Qwen2.5:32b
"""

import logging
import httpx
import asyncio
from typing import Dict, Any, Optional
from .config import settings

logger = logging.getLogger(__name__)

class RunPodClient:
    """
    Client for RunPod serverless endpoint
    Handles Qwen2.5:32b inference requests
    """
    
    def __init__(self):
        self.api_key = settings.runpod_api_key.strip() if settings.runpod_api_key else None
        self.endpoint_id = settings.runpod_endpoint_id
        self.base_url = f"{settings.runpod_base_url}/{self.endpoint_id}"
        self.client = httpx.AsyncClient(timeout=1200.0)  # 20 minute timeout for AI inference
        
    async def run_inference(
        self,
        prompt: str,
        model: str = "qwen2.5:32b",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: Optional[str] = "json"
    ) -> Dict[str, Any]:
        """
        Run inference on RunPod serverless endpoint
        
        Args:
            prompt: The prompt to send to the model
            model: Model name (default: qwen2.5:32b)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
            response_format: "json" or "text"
            
        Returns:
            Dict with response from model
        """
        if not self.api_key or not self.endpoint_id:
            raise RuntimeError("RunPod API key or endpoint ID not configured")
        
        payload = {
            "input": {
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": response_format
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Submit job to RunPod
            response = await self.client.post(
                f"{self.base_url}/run",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            # RunPod returns job ID, we need to poll for results
            job_id = result.get("id")
            if not job_id:
                raise RuntimeError(f"No job ID returned from RunPod: {result}")
            
            # Poll for results
            return await self._poll_for_results(job_id, headers)
            
        except httpx.HTTPError as e:
            logger.error(f"RunPod HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"RunPod inference error: {e}")
            raise
    
    async def _poll_for_results(self, job_id: str, headers: Dict[str, str], max_attempts: int = 600) -> Dict[str, Any]:
        """
        Poll RunPod for job results

        Args:
            job_id: The job ID to poll
            headers: HTTP headers with auth
            max_attempts: Maximum polling attempts (default: 600 = 20 minutes at 2s intervals)

        Returns:
            Dict with model response
        """
        for attempt in range(max_attempts):
            try:
                response = await self.client.get(
                    f"{self.base_url}/status/{job_id}",
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                status = result.get("status")
                
                if status == "COMPLETED":
                    output = result.get("output", {})
                    logger.info(f"RunPod job {job_id} completed")
                    return output
                
                elif status == "FAILED":
                    error = result.get("error", "Unknown error")
                    raise RuntimeError(f"RunPod job failed: {error}")
                
                elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                    # Still processing, wait and retry
                    await asyncio.sleep(2)
                    continue
                
                else:
                    logger.warning(f"Unknown RunPod status: {status}")
                    await asyncio.sleep(2)
                    continue
                    
            except httpx.HTTPError as e:
                logger.error(f"Error polling RunPod job {job_id}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2)
                    continue
                raise
        
        raise TimeoutError(f"RunPod job {job_id} did not complete within {max_attempts * 2} seconds")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global RunPod client instance
_runpod_client: Optional[RunPodClient] = None

async def get_runpod_client() -> RunPodClient:
    """Get or create the global RunPod client instance"""
    global _runpod_client
    if _runpod_client is None:
        _runpod_client = RunPodClient()
    return _runpod_client

