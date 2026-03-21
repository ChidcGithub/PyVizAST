"""
LLM API Routes - Optimized for clarity and reliability

@author: Chidc
@link: github.com/chidcGithub
"""
import json
import logging
import platform
import threading
from typing import List, Optional, AsyncIterator

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..llm import (
    get_llm_service,
    LLMConfig,
)
from ..llm.downloader import OllamaManager, Aria2Downloader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


# ============== Global Instances (Thread-Safe) ==============

_ollama_manager: Optional[OllamaManager] = None
_aria2_downloader: Optional[Aria2Downloader] = None
_instances_lock = threading.Lock()


def get_ollama_manager() -> OllamaManager:
    """Get or create OllamaManager instance"""
    global _ollama_manager
    if _ollama_manager is None:
        with _instances_lock:
            if _ollama_manager is None:
                _ollama_manager = OllamaManager()
    return _ollama_manager


def get_aria2_downloader() -> Aria2Downloader:
    """Get or create Aria2Downloader instance"""
    global _aria2_downloader
    if _aria2_downloader is None:
        with _instances_lock:
            if _aria2_downloader is None:
                _aria2_downloader = Aria2Downloader()
    return _aria2_downloader


# ============== Request/Response Models ==============

class LLMConfigRequest(BaseModel):
    """LLM configuration update request"""
    enabled: bool = True
    model: str = "codellama:7b"
    base_url: str = "http://localhost:11434"
    timeout: int = Field(default=60, ge=10, le=600)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=256, le=8192)
    use_for_explanations: bool = True
    use_for_challenges: bool = True
    use_for_hints: bool = True


class ModelPullRequest(BaseModel):
    """Request to pull a model"""
    model_name: str = Field(..., min_length=1)


class GenerateExplanationRequest(BaseModel):
    """Request to generate node explanation"""
    node_type: str = Field(..., min_length=1)
    node_name: Optional[str] = None
    node_info: Optional[dict] = None
    code_context: Optional[str] = None
    full_code: Optional[str] = None


class GenerateChallengeRequest(BaseModel):
    """Request to generate a challenge"""
    category: str = Field(default="code_smell")
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    topic: Optional[str] = None
    focus_issues: Optional[List[str]] = None


class GenerateHintRequest(BaseModel):
    """Request to generate a hint"""
    code: str
    issues: List[str] = Field(default_factory=list)
    user_progress: str = ""


class OllamaStartRequest(BaseModel):
    """Request to start Ollama server"""
    port: int = Field(default=11434, ge=1024, le=65535)


# ============== Error Response Helper ==============

def error_response(status_code: int, message: str, detail: Optional[str] = None):
    """Create standardized error response"""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": message,
            "detail": detail,
            "status_code": status_code
        }
    )


# ============== Ollama Management Endpoints ==============

@router.get("/ollama/status")
async def get_ollama_install_status():
    """Get Ollama installation and running status"""
    manager = get_ollama_manager()
    status = await manager.get_install_status()
    
    logger.debug(f"Ollama status: installed={status.installed}, running={status.running}")
    
    # Get models count if running
    if status.running:
        try:
            models = await manager.list_models()
            status.models_count = len(models)
        except Exception:
            status.models_count = 0
    
    return status


@router.get("/ollama/download-info")
async def get_ollama_download_info():
    """Get Ollama download information for current platform"""
    manager = get_ollama_manager()
    return {
        "download_info": manager.get_download_info(),
        "manual_instructions": manager.get_install_instructions(),
        "official_url": "https://ollama.ai/download"
    }


@router.post("/ollama/install")
async def install_ollama(background_tasks: BackgroundTasks):
    """Install Ollama automatically (returns progress stream)"""
    manager = get_ollama_manager()
    
    status = await manager.get_install_status()
    if status.installed:
        return {"status": "already_installed", "message": "Ollama is already installed"}
    
    if not status.can_auto_install:
        raise error_response(400, "Auto-install not supported", "Please install manually from ollama.ai")
    
    return StreamingResponse(
        _stream_install_progress(manager),
        media_type="text/event-stream"
    )


async def _stream_install_progress(manager: OllamaManager) -> AsyncIterator[str]:
    """Stream Ollama installation progress"""
    import httpx
    
    info = manager.OLLAMA_DOWNLOADS.get(manager.platform)
    if not info:
        yield f"data: {json.dumps({'status': 'error', 'error': 'Platform not supported'})}\n\n"
        return
    
    url = info["url"]
    download_path = manager.install_dir / "downloads" / info["filename"]
    download_path.parent.mkdir(parents=True, exist_ok=True)
    
    total_size = int(info.get("size_approx_gb", 0.5) * 1024 * 1024 * 1024)
    
    yield f"data: {json.dumps({'status': 'starting', 'progress': 0})}\n\n"
    
    try:
        downloaded = 0
        async with httpx.AsyncClient(timeout=httpx.Timeout(3600.0)) as client:
            async with client.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                
                content_length = int(response.headers.get("content-length", total_size))
                
                with open(download_path, "wb") as f:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if content_length > 0:
                            percent = (downloaded / content_length) * 85
                            yield f"data: {json.dumps({'status': 'downloading', 'progress': round(percent, 1)})}\n\n"
        
        yield f"data: {json.dumps({'status': 'extracting', 'progress': 90})}\n\n"
        
        success = await manager._extract_and_install(download_path, info)
        
        if success:
            try:
                download_path.unlink(missing_ok=True)
            except Exception:
                pass
            yield f"data: {json.dumps({'status': 'completed', 'progress': 100})}\n\n"
        else:
            yield f"data: {json.dumps({'status': 'error', 'error': 'Extraction failed'})}\n\n"
            
    except Exception as e:
        logger.error(f"Ollama installation failed: {e}")
        yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"


@router.post("/ollama/start")
async def start_ollama_server(request: OllamaStartRequest):
    """Start Ollama server"""
    manager = get_ollama_manager()
    
    if not manager.is_ollama_installed():
        raise error_response(400, "Ollama not installed", "Please install Ollama first")
    
    base_url = f"http://localhost:{request.port}"
    if await manager.is_ollama_running(base_url):
        return {"status": "already_running", "message": "Ollama server is already running"}
    
    success = await manager.start_ollama_server(request.port)
    
    if success:
        return {"status": "started", "message": "Ollama server started successfully"}
    raise error_response(500, "Failed to start", "Could not start Ollama server")


@router.post("/ollama/stop")
async def stop_ollama_server():
    """Stop Ollama server (if started by PyVizAST)"""
    manager = get_ollama_manager()
    success = manager.stop_ollama_server()
    
    return {
        "status": "stopped" if success else "not_stopped",
        "message": "Ollama server stopped" if success else "Could not stop (not started by PyVizAST)"
    }


# ============== Status and Configuration Endpoints ==============

@router.get("/status")
async def get_llm_status():
    """Get LLM service status"""
    service = get_llm_service()
    manager = get_ollama_manager()
    ollama_status = await manager.get_install_status()
    
    return {
        **await service.check_status(),
        "ollama_installed": ollama_status.installed,
        "ollama_running": ollama_status.running,
        "ollama_version": ollama_status.version
    }


@router.get("/config")
async def get_llm_config():
    """Get current LLM configuration"""
    service = get_llm_service()
    config = service.config
    return {
        "enabled": config.enabled,
        "model": config.model,
        "base_url": config.base_url,
        "timeout": config.timeout,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "use_for_explanations": config.use_for_explanations,
        "use_for_challenges": config.use_for_challenges,
        "use_for_hints": config.use_for_hints,
    }


@router.post("/config")
async def update_llm_config(config: LLMConfigRequest):
    """Update LLM configuration"""
    service = get_llm_service()
    
    logger.info(f"Updating LLM config: enabled={config.enabled}, model={config.model}, base_url={config.base_url}")
    
    new_config = LLMConfig(
        enabled=config.enabled,
        model=config.model,
        base_url=config.base_url,
        timeout=config.timeout,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        use_for_explanations=config.use_for_explanations,
        use_for_challenges=config.use_for_challenges,
        use_for_hints=config.use_for_hints,
    )
    
    service.update_config(new_config)
    status = await service.check_status()
    
    logger.info(f"LLM config updated, status check result: {status}")
    
    return {
        "status": "ok",
        "config": {"enabled": new_config.enabled, "model": new_config.model},
        "llm_status": status
    }


# ============== Model Management Endpoints ==============

@router.get("/models")
async def list_models():
    """List all pulled models"""
    manager = get_ollama_manager()
    
    if not await manager.is_ollama_running():
        return []
    
    return await manager.list_models()


@router.get("/models/recommended")
async def get_recommended_models():
    """Get list of recommended models"""
    service = get_llm_service()
    return service.get_recommended_models()


@router.post("/models/pull")
async def pull_model(request: ModelPullRequest):
    """Pull a model from Ollama registry (returns progress stream)"""
    manager = get_ollama_manager()
    
    if not await manager.is_ollama_running():
        raise error_response(503, "Ollama not running", "Please start Ollama server first")
    
    async def progress_stream():
        try:
            async for progress_data in manager.pull_model(request.model_name, on_progress=lambda _: None):
                yield f"data: {json.dumps(progress_data)}\n\n"
            yield f"data: {json.dumps({'status': 'completed', 'model': request.model_name})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(progress_stream(), media_type="text/event-stream")


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Delete a model"""
    manager = get_ollama_manager()
    
    if not await manager.is_ollama_running():
        raise error_response(503, "Ollama not running", "Please start Ollama server first")
    
    success = await manager.delete_model(model_name)
    
    if success:
        logger.info(f"Model deleted: {model_name}")
        return {"status": "ok", "message": f"Model {model_name} deleted"}
    raise error_response(500, "Delete failed", f"Could not delete model {model_name}")


# ============== Generation Endpoints ==============

@router.post("/generate/explanation")
async def generate_explanation(request: GenerateExplanationRequest):
    """Generate explanation for an AST node using LLM"""
    service = get_llm_service()
    
    if not service.is_enabled:
        raise error_response(503, "LLM disabled", "Enable LLM features in settings")
    
    try:
        explanation = await service.generate_explanation(
            node_type=request.node_type,
            node_name=request.node_name,
            node_info=request.node_info,
            code_context=request.code_context,
            full_code=request.full_code
        )
        logger.debug(f"Generated explanation for {request.node_type}")
        return explanation
    except RuntimeError as e:
        raise error_response(503, "Service unavailable", str(e))
    except Exception as e:
        logger.error(f"Explanation generation failed: {e}")
        raise error_response(500, "Generation failed", str(e))


@router.post("/generate/challenge")
async def generate_challenge(request: GenerateChallengeRequest):
    """Generate a new challenge using LLM"""
    service = get_llm_service()
    
    if not service.is_enabled:
        raise error_response(503, "LLM disabled", "Enable LLM features in settings")
    
    try:
        challenge = await service.generate_challenge(
            category=request.category,
            difficulty=request.difficulty,
            topic=request.topic,
            focus_issues=request.focus_issues
        )
        logger.debug(f"Generated challenge: {challenge.title}")
        return challenge
    except RuntimeError as e:
        raise error_response(503, "Service unavailable", str(e))
    except ValueError as e:
        raise error_response(422, "Invalid response", str(e))
    except Exception as e:
        logger.error(f"Challenge generation failed: {e}")
        raise error_response(500, "Generation failed", str(e))


@router.post("/generate/hint")
async def generate_hint(request: GenerateHintRequest):
    """Generate a contextual hint for a challenge"""
    service = get_llm_service()
    
    if not service.is_enabled:
        return {"hint": ""}
    
    try:
        hint = await service.generate_hint(
            code=request.code,
            issues=request.issues,
            user_progress=request.user_progress
        )
        return {"hint": hint}
    except Exception as e:
        logger.warning(f"Hint generation failed: {e}")
        return {"hint": ""}


# ============== Download Management (aria2) ==============

@router.get("/downloads/aria2/status")
async def get_aria2_status():
    """Check aria2 availability"""
    downloader = get_aria2_downloader()
    available = downloader.is_available()
    version = await downloader.get_version() if available else None
    
    return {
        "available": available,
        "version": version,
        "platform": platform.system().lower()
    }


@router.get("/downloads/aria2/install")
async def get_aria2_install_instructions():
    """Get aria2 installation instructions"""
    downloader = get_aria2_downloader()
    current_platform = platform.system().lower()
    instructions = await downloader.get_install_instructions(current_platform)
    
    return {"platform": current_platform, "instructions": instructions}


# ============== Legacy Endpoint ==============

@router.get("/downloads/ollama")
async def get_ollama_download_info_legacy():
    """Get Ollama download information (legacy endpoint)"""
    manager = get_ollama_manager()
    return {
        "platform": manager.get_download_info().get("platform", "unknown"),
        "download_info": manager.get_download_info(),
        "install_url": "https://ollama.ai/download",
        "instructions": [
            "1. Download and install Ollama from https://ollama.ai",
            "2. Run 'ollama serve' to start the server",
            "3. Run 'ollama pull codellama:7b' to download a model",
            "4. Refresh this page to check status"
        ],
        "manual_instructions": manager.get_install_instructions()
    }
