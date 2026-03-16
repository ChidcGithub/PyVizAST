"""
LLM API Routes

@author: Chidc
@link: github.com/chidcGithub
"""
import asyncio
import json
import logging
import platform
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..llm import (
    LLMService,
    get_llm_service,
    LLMConfig,
    LLMStatus,
)
from ..llm.models import (
    ModelInfo,
    GeneratedExplanation,
    GeneratedChallenge,
    OllamaInstallStatus,
    OllamaInstallProgress,
)
from ..llm.downloader import OllamaManager, Aria2Downloader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


# ============== Global Instances ==============

_ollama_manager: Optional[OllamaManager] = None
_aria2_downloader: Optional[Aria2Downloader] = None


def get_ollama_manager() -> OllamaManager:
    """Get or create OllamaManager instance"""
    global _ollama_manager
    if _ollama_manager is None:
        _ollama_manager = OllamaManager()
    return _ollama_manager


def get_aria2_downloader() -> Aria2Downloader:
    """Get or create Aria2Downloader instance"""
    global _aria2_downloader
    if _aria2_downloader is None:
        _aria2_downloader = Aria2Downloader()
    return _aria2_downloader


# ============== Request/Response Models ==============

class LLMConfigRequest(BaseModel):
    """LLM configuration update request"""
    enabled: bool = True
    model: str = "codellama:7b"
    base_url: str = "http://localhost:11434"
    timeout: int = 60
    temperature: float = 0.7
    max_tokens: int = 2048
    use_for_explanations: bool = True
    use_for_challenges: bool = True
    use_for_hints: bool = True


class ModelPullRequest(BaseModel):
    """Request to pull a model"""
    model_name: str


class GenerateExplanationRequest(BaseModel):
    """Request to generate node explanation"""
    node_type: str
    node_name: Optional[str] = None
    node_info: Optional[dict] = None
    code_context: Optional[str] = None


class GenerateChallengeRequest(BaseModel):
    """Request to generate a challenge"""
    category: str
    difficulty: str = "medium"
    topic: Optional[str] = None
    focus_issues: Optional[List[str]] = None


class GenerateHintRequest(BaseModel):
    """Request to generate a hint"""
    code: str
    issues: List[str]
    user_progress: str = ""


class OllamaInstallRequest(BaseModel):
    """Request to install Ollama"""
    use_aria2: bool = True


class OllamaStartRequest(BaseModel):
    """Request to start Ollama server"""
    port: int = 11434


# ============== Ollama Management ==============

@router.get("/ollama/status")
async def get_ollama_install_status():
    """Get Ollama installation status"""
    manager = get_ollama_manager()
    status = await manager.get_install_status()
    
    # Debug log
    logger.info(f"Ollama status: installed={status.installed}, running={status.running}, can_auto_install={status.can_auto_install}, platform={status.platform}")
    
    # Also get models count if running
    if status.running:
        try:
            models = await manager.list_models()
            status.models_count = len(models)
        except Exception:
            pass
    
    return status


@router.get("/ollama/download-info")
async def get_ollama_download_info():
    """Get Ollama download information for current platform"""
    manager = get_ollama_manager()
    info = manager.get_download_info()
    instructions = manager.get_install_instructions()
    
    return {
        "download_info": info,
        "manual_instructions": instructions,
        "official_url": "https://ollama.ai/download"
    }


@router.post("/ollama/install")
async def install_ollama(request: OllamaInstallRequest, background_tasks: BackgroundTasks):
    """Install Ollama automatically (returns progress stream)"""
    manager = get_ollama_manager()
    
    # Check if already installed
    status = await manager.get_install_status()
    if status.installed:
        return {"status": "already_installed", "message": "Ollama is already installed"}
    
    # Check if can auto-install
    if not status.can_auto_install:
        raise HTTPException(
            status_code=400,
            detail="Auto-install not supported on this platform. Please install manually."
        )
    
    async def progress_stream():
        try:
            def on_progress(progress):
                # Progress is handled in the stream
                pass
            
            # Send initial status
            yield f"data: {json.dumps({'status': 'starting', 'progress': 0})}\n\n"
            
            # Install with progress callback
            async def install_with_progress():
                import httpx
                
                info = manager.OLLAMA_DOWNLOADS[manager.platform]
                url = info["url"]
                
                # Use aria2 if available and requested
                use_aria2 = request.use_aria2 and get_aria2_downloader().is_available()
                
                # Create download directory
                from pathlib import Path
                download_path = manager.install_dir / "downloads" / info["filename"]
                download_path.parent.mkdir(parents=True, exist_ok=True)
                
                total_size = int(info["size_approx_gb"] * 1024 * 1024 * 1024)
                downloaded = 0
                
                # Download
                yield f"data: {json.dumps({'status': 'downloading', 'progress': 0, 'total': total_size})}\n\n"
                
                try:
                    if use_aria2:
                        # Use aria2c
                        import subprocess
                        proc = subprocess.Popen(
                            ["aria2c", "-x", "16", "-s", "16", "-k", "1M",
                             "-d", str(download_path.parent), "-o", download_path.name,
                             "--summary-interval=1", url],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        
                        while True:
                            line = proc.stdout.readline()
                            if not line and proc.poll() is not None:
                                break
                            
                            if "%" in line:
                                try:
                                    parts = line.split("(")
                                    if len(parts) > 1:
                                        percent = float(parts[1].split("%")[0])
                                        yield f"data: {json.dumps({'status': 'downloading', 'progress': percent})}\n\n"
                                except:
                                    pass
                        
                        if proc.returncode != 0:
                            raise Exception("aria2 download failed")
                    
                    else:
                        # Use httpx
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
                                            yield f"data: {json.dumps({'status': 'downloading', 'progress': percent})}\n\n"
                    
                    # Extract
                    yield f"data: {json.dumps({'status': 'extracting', 'progress': 90})}\n\n"
                    
                    success = await manager._extract_and_install(download_path, info)
                    
                    if success:
                        # Clean up
                        try:
                            download_path.unlink(missing_ok=True)
                        except:
                            pass
                        
                        yield f"data: {json.dumps({'status': 'completed', 'progress': 100})}\n\n"
                    else:
                        yield f"data: {json.dumps({'status': 'error', 'error': 'Extraction failed'})}\n\n"
                        
                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
            
            async for progress_data in install_with_progress():
                yield progress_data
            
        except Exception as e:
            logger.error(f"Ollama installation failed: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        progress_stream(),
        media_type="text/event-stream"
    )


@router.post("/ollama/start")
async def start_ollama_server(request: OllamaStartRequest):
    """Start Ollama server"""
    manager = get_ollama_manager()
    
    # Check if installed
    if not manager.is_ollama_installed():
        raise HTTPException(
            status_code=400,
            detail="Ollama is not installed. Please install it first."
        )
    
    # Check if already running
    if await manager.is_ollama_running(f"http://localhost:{request.port}"):
        return {"status": "already_running", "message": "Ollama server is already running"}
    
    # Start server
    success = await manager.start_ollama_server(request.port)
    
    if success:
        return {"status": "started", "message": "Ollama server started successfully"}
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to start Ollama server"
        )


@router.post("/ollama/stop")
async def stop_ollama_server():
    """Stop Ollama server (if started by us)"""
    manager = get_ollama_manager()
    success = manager.stop_ollama_server()
    
    if success:
        return {"status": "stopped", "message": "Ollama server stopped"}
    else:
        return {"status": "not_stopped", "message": "Could not stop Ollama server (may not have been started by PyVizAST)"}


# ============== Status and Configuration ==============

@router.get("/status")
async def get_llm_status():
    """Get LLM service status"""
    service = get_llm_service()
    
    # Also check Ollama status
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
    return {
        "enabled": service.config.enabled,
        "model": service.config.model,
        "base_url": service.config.base_url,
        "timeout": service.config.timeout,
        "temperature": service.config.temperature,
        "max_tokens": service.config.max_tokens,
        "use_for_explanations": service.config.use_for_explanations,
        "use_for_challenges": service.config.use_for_challenges,
        "use_for_hints": service.config.use_for_hints,
    }


@router.post("/config")
async def update_llm_config(config: LLMConfigRequest):
    """Update LLM configuration"""
    service = get_llm_service()
    
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
    
    # Check new status
    status = await service.check_status()
    
    return {
        "status": "ok",
        "config": {
            "enabled": new_config.enabled,
            "model": new_config.model,
        },
        "llm_status": status
    }


# ============== Model Management ==============

@router.get("/models")
async def list_models():
    """List all pulled models"""
    manager = get_ollama_manager()
    
    # Check if Ollama is running
    if not await manager.is_ollama_running():
        return []
    
    models = await manager.list_models()
    return models


@router.get("/models/recommended")
async def get_recommended_models():
    """Get list of recommended models"""
    service = get_llm_service()
    return service.get_recommended_models()


@router.post("/models/pull")
async def pull_model(request: ModelPullRequest):
    """Pull a model from Ollama registry (returns progress stream)"""
    manager = get_ollama_manager()
    
    # Check if Ollama is running
    if not await manager.is_ollama_running():
        raise HTTPException(
            status_code=503,
            detail="Ollama server is not running. Please start it first."
        )
    
    async def progress_stream():
        try:
            def on_progress(data):
                pass  # Stream handles progress
            
            async for progress_data in manager.pull_model(request.model_name, on_progress=on_progress):
                yield f"data: {json.dumps(progress_data)}\n\n"
            
            yield f"data: {json.dumps({'status': 'completed', 'model': request.model_name})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        progress_stream(),
        media_type="text/event-stream"
    )


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Delete a model"""
    manager = get_ollama_manager()
    
    if not await manager.is_ollama_running():
        raise HTTPException(status_code=503, detail="Ollama server is not running")
    
    success = await manager.delete_model(model_name)
    
    if success:
        return {"status": "ok", "message": f"Model {model_name} deleted"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to delete model {model_name}")


# ============== Generation Endpoints ==============

@router.post("/generate/explanation")
async def generate_explanation(request: GenerateExplanationRequest):
    """Generate explanation for an AST node using LLM"""
    service = get_llm_service()
    
    if not service.is_enabled:
        raise HTTPException(status_code=503, detail="LLM service is disabled")
    
    try:
        explanation = await service.generate_explanation(
            node_type=request.node_type,
            node_name=request.node_name,
            node_info=request.node_info,
            code_context=request.code_context
        )
        return explanation
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Explanation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/generate/challenge")
async def generate_challenge(request: GenerateChallengeRequest):
    """Generate a new challenge using LLM"""
    service = get_llm_service()
    
    if not service.is_enabled:
        raise HTTPException(status_code=503, detail="LLM service is disabled")
    
    try:
        challenge = await service.generate_challenge(
            category=request.category,
            difficulty=request.difficulty,
            topic=request.topic,
            focus_issues=request.focus_issues
        )
        return challenge
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Challenge generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


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
    
    return {
        "platform": current_platform,
        "instructions": instructions
    }


# ============== Legacy Endpoints (for backward compatibility) ==============

@router.get("/downloads/ollama")
async def get_ollama_download_info_legacy():
    """Get Ollama download information (legacy endpoint)"""
    manager = get_ollama_manager()
    info = manager.get_download_info()
    instructions = manager.get_install_instructions()
    
    return {
        "platform": info.get("platform", "unknown"),
        "download_info": info,
        "install_url": "https://ollama.ai/download",
        "instructions": [
            "1. Download and install Ollama from https://ollama.ai",
            "2. Run 'ollama serve' to start the server",
            "3. Run 'ollama pull codellama:7b' to download a model",
            "4. Refresh this page to check status"
        ],
        "manual_instructions": instructions
    }