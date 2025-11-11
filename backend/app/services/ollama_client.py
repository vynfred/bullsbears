"""
BullsBears Ollama Client
Handles communication with local Ollama inference server
"""

import asyncio
import aiohttp
import json
import logging
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Configuration for Ollama client"""
    host: str = "localhost"
    port: int = 11434
    timeout: int = 120  # Increased for large models like qwen2.5:32b
    max_retries: int = 3
    retry_delay: float = 1.0


class OllamaClient:
    """Async client for Ollama API"""
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.base_url = f"http://{self.config.host}:{self.config.port}"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Override with environment variables if available
        if os.getenv('OLLAMA_HOST'):
            host_port = os.getenv('OLLAMA_HOST').split(':')
            self.config.host = host_port[0]
            if len(host_port) > 1:
                self.config.port = int(host_port[1])
            self.base_url = f"http://{self.config.host}:{self.config.port}"
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """Initialize HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def health_check(self) -> bool:
        """Check if Ollama server is healthy"""
        try:
            await self.connect()
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False
    
    async def list_models(self) -> Dict[str, Any]:
        """List available models"""
        try:
            await self.connect()
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to list models: {response.status}")
                    return {"models": []}
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            return {"models": []}
    
    async def generate(self, model: str, prompt: str, **options) -> Dict[str, Any]:
        """Generate response from model"""
        for attempt in range(self.config.max_retries):
            try:
                await self.connect()
                
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": options
                }
                
                async with self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"Generated response for model {model}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Generation failed: {response.status} - {error_text}")
                        
                        if attempt < self.config.max_retries - 1:
                            await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                            continue
                        else:
                            raise Exception(f"Generation failed after {self.config.max_retries} attempts")
            
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}, retrying...")
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Generation failed after {self.config.max_retries} attempts: {str(e)}")
                    raise

    async def generate_text(self, model: str, prompt: str, **options) -> str:
        """Generate text response from model (convenience method)"""
        result = await self.generate(model, prompt, **options)
        if result and 'response' in result:
            return result['response']
        return ""
    
    async def chat(self, model: str, messages: list, **options) -> Dict[str, Any]:
        """Chat with model using conversation format"""
        try:
            await self.connect()
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": options
            }
            
            async with self.session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.debug(f"Chat response for model {model}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Chat failed: {response.status} - {error_text}")
                    raise Exception(f"Chat failed: {response.status}")
        
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            raise
    
    async def pull_model(self, model: str) -> bool:
        """Pull/download a model"""
        try:
            await self.connect()
            
            payload = {"name": model}
            
            async with self.session.post(
                f"{self.base_url}/api/pull",
                json=payload
            ) as response:
                
                if response.status == 200:
                    # Stream the pull progress
                    async for line in response.content:
                        if line:
                            try:
                                progress = json.loads(line.decode())
                                if progress.get('status'):
                                    logger.info(f"Pulling {model}: {progress['status']}")
                            except json.JSONDecodeError:
                                continue
                    
                    logger.info(f"Successfully pulled model: {model}")
                    return True
                else:
                    logger.error(f"Failed to pull model {model}: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error pulling model {model}: {str(e)}")
            return False
    
    async def delete_model(self, model: str) -> bool:
        """Delete a model"""
        try:
            await self.connect()
            
            payload = {"name": model}
            
            async with self.session.delete(
                f"{self.base_url}/api/delete",
                json=payload
            ) as response:
                
                if response.status == 200:
                    logger.info(f"Successfully deleted model: {model}")
                    return True
                else:
                    logger.error(f"Failed to delete model {model}: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error deleting model {model}: {str(e)}")
            return False


# Global client instance
_ollama_client: Optional[OllamaClient] = None


async def get_ollama_client() -> OllamaClient:
    """Get global Ollama client instance"""
    global _ollama_client
    
    if _ollama_client is None:
        # Check if we're running on Fly.io
        if os.getenv('FLY_APP_NAME'):
            # Use internal Fly.io networking
            config = OllamaConfig(host="localhost", port=11434)
        else:
            # Local development
            config = OllamaConfig()
        
        _ollama_client = OllamaClient(config)
        await _ollama_client.connect()
    
    return _ollama_client


async def close_ollama_client():
    """Close global Ollama client"""
    global _ollama_client
    
    if _ollama_client:
        await _ollama_client.close()
        _ollama_client = None
