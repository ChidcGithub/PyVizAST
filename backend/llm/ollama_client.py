"""
Ollama API Client

Communicates with local Ollama server for LLM inference.

@author: Chidc
@link: github.com/chidcGithub
"""
import logging
import httpx
from typing import List, Optional, Dict, Any, AsyncIterator
import atexit

from .models import ModelInfo, LLMConfig

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Ollama API error"""
    pass


class OllamaClient:
    """Client for Ollama API with connection pooling"""
    
    # Shared client instance for connection pooling
    _shared_client: Optional[httpx.AsyncClient] = None
    
    @classmethod
    def _get_shared_client(cls, timeout: httpx.Timeout) -> httpx.AsyncClient:
        """Get or create shared HTTP client for connection pooling"""
        if cls._shared_client is None or cls._shared_client.is_closed:
            cls._shared_client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                    keepalive_expiry=30.0
                )
            )
        return cls._shared_client
    
    @classmethod
    def close_shared_client(cls):
        """Close shared client (call on shutdown)
        
        This method is registered with atexit but may not work reliably
        for async clients. Prefer using shutdown_async() in FastAPI lifespan.
        """
        if cls._shared_client and not cls._shared_client.is_closed:
            import asyncio
            client = cls._shared_client
            cls._shared_client = None  # Clear reference first to prevent double close
            
            try:
                # Try to get running loop
                loop = asyncio.get_running_loop()
                # If we have a running loop, schedule the close
                loop.call_soon_threadsafe(lambda: loop.create_task(client.aclose()))
            except RuntimeError:
                # No running loop available
                try:
                    # Try to create a new loop and run the close
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(client.aclose())
                    finally:
                        loop.close()
                except Exception as e:
                    # Last resort: just set to None and let GC handle it
                    logger.debug(f"Could not close HTTP client gracefully: {e}")
    
    @classmethod
    async def shutdown_async(cls):
        """Async shutdown for use in FastAPI lifespan context"""
        if cls._shared_client and not cls._shared_client.is_closed:
            client = cls._shared_client
            cls._shared_client = None
            try:
                await client.aclose()
                logger.debug("HTTP client closed successfully")
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.timeout = httpx.Timeout(config.timeout)
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get shared HTTP client"""
        return self._get_shared_client(self.timeout)
    
    async def is_available(self) -> bool:
        """Check if Ollama server is running"""
        try:
            # Use a quick timeout for availability check
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.debug(f"Ollama not available: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.warning(f"Ollama returned error status: {e}")
            return False
    
    async def list_models(self) -> List[ModelInfo]:
        """List all pulled models"""
        try:
            # Use a shorter timeout for listing models
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                
                models = []
                for model in data.get("models", []):
                    models.append(ModelInfo(
                        name=model.get("name", ""),
                        size=model.get("size", 0),  # Size in bytes
                        digest=model.get("digest", ""),
                        modified_at=model.get("modified_at", ""),
                        details=model.get("details")
                    ))
                return models
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.debug(f"Failed to list models (network error): {e}")
            raise OllamaError(f"Failed to connect to Ollama: {e}")
        except httpx.HTTPError as e:
            logger.error(f"Failed to list models: {e}")
            raise OllamaError(f"Failed to list models: {e}")
    
    async def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/show",
                json={"name": model_name}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return None
    
    async def pull_model(self, model_name: str) -> AsyncIterator[Dict[str, Any]]:
        """Pull a model from Ollama registry (streaming progress)"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3600.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model_name, "stream": True}
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            try:
                                yield json.loads(line)
                            except json.JSONDecodeError:
                                continue
        except httpx.HTTPError as e:
            logger.error(f"Failed to pull model: {e}")
            raise OllamaError(f"Failed to pull model {model_name}: {e}")
    
    async def delete_model(self, model_name: str) -> bool:
        """Delete a model"""
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            return False
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text using the model"""
        model = model or self.config.model
        temperature = temperature if temperature is not None else self.config.temperature
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or self.config.max_tokens
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.HTTPError as e:
            logger.error(f"Generation failed: {e}")
            raise OllamaError(f"Generation failed: {e}")
    
    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> AsyncIterator[str]:
        """Generate text with streaming"""
        model = model or self.config.model
        temperature = temperature if temperature is not None else self.config.temperature
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": self.config.max_tokens
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                continue
        except httpx.HTTPError as e:
            logger.error(f"Streaming generation failed: {e}")
            raise OllamaError(f"Streaming generation failed: {e}")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Chat completion with message history"""
        model = model or self.config.model
        temperature = temperature if temperature is not None else self.config.temperature
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": self.config.max_tokens
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            logger.error(f"Chat failed: {e}")
            raise OllamaError(f"Chat failed: {e}")


# Register cleanup on exit
atexit.register(OllamaClient.close_shared_client)
