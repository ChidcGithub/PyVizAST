"""
Ollama Manager - Auto-install, download, and manage Ollama and models

@author: Chidc
@link: github.com/chidcGithub
"""
import asyncio
import json
import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, AsyncIterator

import httpx

from .models import DownloadProgress, OllamaInstallStatus

logger = logging.getLogger(__name__)


class OllamaManager:
    """
    Manages Ollama installation, server, and model downloads.
    Supports auto-installation on Windows, macOS, and Linux.
    """
    
    # Ollama download URLs
    OLLAMA_VERSION = "0.1.33"
    OLLAMA_DOWNLOADS = {
        "windows": {
            "url": f"https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-windows-amd64.zip",
            "filename": "ollama-windows-amd64.zip",
            "install_dir": "ollama",
            "executable": "ollama.exe",
            "size_approx_gb": 0.6
        },
        "darwin": {
            "url": f"https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/Ollama-darwin.zip",
            "filename": "Ollama-darwin.zip",
            "install_dir": "ollama",
            "executable": "ollama",
            "size_approx_gb": 0.6
        },
        "linux": {
            "url": f"https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-linux-amd64.tgz",
            "filename": "ollama-linux-amd64.tgz",
            "install_dir": "ollama",
            "executable": "bin/ollama",
            "size_approx_gb": 0.5
        }
    }
    
    def __init__(self, install_dir: Optional[Path] = None):
        self.platform = platform.system().lower()
        self.install_dir = install_dir or self._get_default_install_dir()
        self._ollama_process: Optional[subprocess.Popen] = None
        self._download_progress: Dict[str, DownloadProgress] = {}
        
    def _get_default_install_dir(self) -> Path:
        """Get default installation directory"""
        if self.platform == "windows":
            return Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "PyVizAST" / "ollama"
        elif self.platform == "darwin":
            return Path.home() / ".pyvizast" / "ollama"
        else:
            return Path.home() / ".pyvizast" / "ollama"
    
    def get_ollama_executable(self) -> Optional[Path]:
        """Find Ollama executable"""
        # First check our install directory
        our_install = self.install_dir / self.OLLAMA_DOWNLOADS[self.platform]["executable"]
        if our_install.exists():
            return our_install
        
        # Then check system PATH
        ollama_path = shutil.which("ollama")
        if ollama_path:
            return Path(ollama_path)
        
        return None
    
    def is_ollama_installed(self) -> bool:
        """Check if Ollama is installed"""
        return self.get_ollama_executable() is not None
    
    async def is_ollama_running(self, base_url: str = "http://localhost:11434") -> bool:
        """Check if Ollama server is running"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    async def get_ollama_version(self) -> Optional[str]:
        """Get installed Ollama version"""
        executable = self.get_ollama_executable()
        if not executable:
            return None
        
        try:
            proc = await asyncio.create_subprocess_exec(
                str(executable), "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            if stdout:
                # Parse version from output like "ollama version is 0.1.33"
                output = stdout.decode().strip()
                for part in output.split():
                    if part.replace(".", "").isdigit():
                        return part
            return "unknown"
        except Exception as e:
            logger.error(f"Failed to get Ollama version: {e}")
            return None
    
    async def get_install_status(self) -> OllamaInstallStatus:
        """Get comprehensive install status"""
        installed = self.is_ollama_installed()
        running = await self.is_ollama_running() if installed else False
        version = await self.get_ollama_version() if installed else None
        
        return OllamaInstallStatus(
            installed=installed,
            running=running,
            version=version,
            platform=self.platform,
            install_dir=str(self.install_dir) if installed else None,
            executable=str(self.get_ollama_executable()) if installed else None,
            can_auto_install=self._can_auto_install()
        )
    
    def _can_auto_install(self) -> bool:
        """Check if we can auto-install on this platform"""
        # We can auto-install on all major platforms
        return self.platform in self.OLLAMA_DOWNLOADS
    
    async def install_ollama(
        self,
        on_progress: Optional[Callable[[DownloadProgress], None]] = None,
        use_aria2: bool = True
    ) -> bool:
        """
        Download and install Ollama automatically.
        
        Args:
            on_progress: Callback for download progress
            use_aria2: Whether to use aria2 for faster downloads
            
        Returns:
            True if installation successful
        """
        if self.platform not in self.OLLAMA_DOWNLOADS:
            logger.error(f"Unsupported platform: {self.platform}")
            return False
        
        info = self.OLLAMA_DOWNLOADS[self.platform]
        url = info["url"]
        filename = info["filename"]
        
        # Create progress tracker
        progress = DownloadProgress(
            model_name="ollama",
            status="downloading",
            progress=0.0,
            total_bytes=int(info["size_approx_gb"] * 1024 * 1024 * 1024)
        )
        
        try:
            # Download
            download_path = self.install_dir / "downloads" / filename
            download_path.parent.mkdir(parents=True, exist_ok=True)
            
            if use_aria2 and shutil.which("aria2c"):
                success = await self._download_with_aria2(url, download_path, progress, on_progress)
            else:
                success = await self._download_with_http(url, download_path, progress, on_progress)
            
            if not success:
                return False
            
            # Extract and install
            progress.status = "installing"
            progress.progress = 90
            if on_progress:
                on_progress(progress)
            
            success = await self._extract_and_install(download_path, info)
            
            if success:
                progress.status = "completed"
                progress.progress = 100
                if on_progress:
                    on_progress(progress)
                
                # Clean up download
                try:
                    download_path.unlink(missing_ok=True)
                except Exception:
                    pass
                
                return True
            else:
                progress.status = "error"
                progress.error = "Installation failed"
                if on_progress:
                    on_progress(progress)
                return False
                
        except Exception as e:
            logger.error(f"Ollama installation failed: {e}")
            progress.status = "error"
            progress.error = str(e)
            if on_progress:
                on_progress(progress)
            return False
    
    async def _download_with_aria2(
        self,
        url: str,
        output_path: Path,
        progress: DownloadProgress,
        on_progress: Optional[Callable[[DownloadProgress], None]]
    ) -> bool:
        """Download using aria2 for faster downloads"""
        try:
            cmd = [
                "aria2c",
                "-x", "16",
                "-s", "16",
                "-k", "1M",
                "-d", str(output_path.parent),
                "-o", output_path.name,
                "--summary-interval=1",
                url
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                
                line = line.decode().strip()
                
                if "%" in line:
                    try:
                        # Parse progress
                        parts = line.split("(")
                        if len(parts) > 1:
                            percent_str = parts[1].split("%")[0]
                            progress.progress = float(percent_str)
                            
                            if "DL:" in line:
                                speed_parts = line.split("DL:")
                                if len(speed_parts) > 1:
                                    progress.speed = speed_parts[1].split()[0]
                            
                            if on_progress:
                                on_progress(progress)
                    except (ValueError, IndexError):
                        pass
            
            await proc.wait()
            return proc.returncode == 0 and output_path.exists()
            
        except Exception as e:
            logger.error(f"aria2 download failed: {e}")
            return False
    
    async def _download_with_http(
        self,
        url: str,
        output_path: Path,
        progress: DownloadProgress,
        on_progress: Optional[Callable[[DownloadProgress], None]]
    ) -> bool:
        """Download using httpx"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3600.0, connect=30.0)) as client:
                async with client.stream("GET", url, follow_redirects=True) as response:
                    response.raise_for_status()
                    
                    total = int(response.headers.get("content-length", 0))
                    progress.total_bytes = total
                    
                    downloaded = 0
                    chunk_size = 1024 * 1024  # 1MB chunks
                    
                    with open(output_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size):
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress.downloaded_bytes = downloaded
                            
                            if total > 0:
                                progress.progress = (downloaded / total) * 85  # Reserve 15% for extraction
                            
                            if on_progress:
                                on_progress(progress)
                    
                    return True
                    
        except Exception as e:
            logger.error(f"HTTP download failed: {e}")
            return False
    
    async def _extract_and_install(self, archive_path: Path, info: Dict[str, Any]) -> bool:
        """Extract archive and install Ollama"""
        try:
            import zipfile
            import tarfile
            
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            if archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(self.install_dir)
            elif archive_path.suffix in [".tgz", ".tar.gz"]:
                with tarfile.open(archive_path, 'r:gz') as tf:
                    tf.extractall(self.install_dir)
            else:
                # Assume it's already an executable (Linux)
                shutil.copy(archive_path, self.install_dir / info["executable"])
            
            # Make executable on Unix
            if self.platform != "windows":
                executable_path = self.install_dir / info["executable"]
                if executable_path.exists():
                    os.chmod(executable_path, 0o755)
            
            return True
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return False
    
    async def start_ollama_server(self, port: int = 11434) -> bool:
        """Start Ollama server"""
        executable = self.get_ollama_executable()
        if not executable:
            logger.error("Ollama not installed")
            return False
        
        # Check if already running
        if await self.is_ollama_running(f"http://localhost:{port}"):
            logger.info("Ollama server already running")
            return True
        
        try:
            # Set environment
            env = os.environ.copy()
            env["OLLAMA_HOST"] = f"127.0.0.1:{port}"
            
            # Start server
            if self.platform == "windows":
                # On Windows, use serve command
                self._ollama_process = subprocess.Popen(
                    [str(executable), "serve"],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self._ollama_process = subprocess.Popen(
                    [str(executable), "serve"],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # Wait for server to start
            for _ in range(30):  # 30 second timeout
                await asyncio.sleep(1)
                if await self.is_ollama_running(f"http://localhost:{port}"):
                    logger.info("Ollama server started successfully")
                    return True
            
            logger.error("Ollama server failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start Ollama server: {e}")
            return False
    
    def stop_ollama_server(self) -> bool:
        """Stop Ollama server (if we started it)"""
        if self._ollama_process:
            try:
                self._ollama_process.terminate()
                self._ollama_process.wait(timeout=10)
                self._ollama_process = None
                return True
            except Exception as e:
                logger.error(f"Failed to stop Ollama server: {e}")
                return False
        return True
    
    async def pull_model(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Pull a model from Ollama registry.
        
        Args:
            model_name: Name of model to pull (e.g., "codellama:7b")
            base_url: Ollama server URL
            on_progress: Callback for progress updates
            
        Yields:
            Progress data dictionaries
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(7200.0)) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/api/pull",
                    json={"name": model_name, "stream": True}
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                
                                # Add calculated progress percentage
                                if "completed" in data and "total" in data:
                                    completed = data["completed"]
                                    total = data["total"]
                                    if total > 0:
                                        data["progress_percent"] = round((completed / total) * 100, 1)
                                
                                if on_progress:
                                    on_progress(data)
                                
                                yield data
                                        
                            except json.JSONDecodeError:
                                continue
                    
                    # Yield final completion
                    yield {"status": "success", "model": model_name}
                    
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            yield {"status": "error", "error": str(e)}
    
    async def list_models(self, base_url: str = "http://localhost:11434") -> List[Dict[str, Any]]:
        """List installed models"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def delete_model(self, model_name: str, base_url: str = "http://localhost:11434") -> bool:
        """Delete a model"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{base_url}/api/delete",
                    json={"name": model_name}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            return False
    
    def get_download_info(self) -> Dict[str, Any]:
        """Get download information for current platform"""
        if self.platform not in self.OLLAMA_DOWNLOADS:
            return {
                "platform": self.platform,
                "supported": False,
                "message": "Platform not supported for auto-install"
            }
        
        info = self.OLLAMA_DOWNLOADS[self.platform]
        return {
            "platform": self.platform,
            "supported": True,
            "version": self.OLLAMA_VERSION,
            "download_url": info["url"],
            "size_approx": f"{info['size_approx_gb']:.1f} GB",
            "install_dir": str(self.install_dir)
        }
    
    def get_install_instructions(self) -> Dict[str, Any]:
        """Get manual install instructions if auto-install not possible"""
        instructions = {
            "windows": {
                "method": "Download Installer",
                "commands": [
                    "Download from https://ollama.ai/download",
                    "Run the installer",
                    "Ollama will start automatically"
                ],
                "download_url": "https://ollama.ai/download/windows"
            },
            "darwin": {
                "method": "Download Installer",
                "commands": [
                    "Download from https://ollama.ai/download",
                    "Open the DMG and drag Ollama to Applications",
                    "Run Ollama from Applications"
                ],
                "download_url": "https://ollama.ai/download/mac"
            },
            "linux": {
                "method": "curl script",
                "commands": [
                    "curl -fsSL https://ollama.ai/install.sh | sh",
                    "ollama serve"
                ],
                "download_url": "https://ollama.ai/download/linux"
            }
        }
        
        return instructions.get(self.platform, instructions["linux"])


class Aria2Downloader:
    """
    Downloader using aria2 for fast, parallel downloads.
    Falls back to HTTP download if aria2 is not available.
    """
    
    def __init__(self, aria2_path: Optional[str] = None):
        self.aria2_path = aria2_path or self._find_aria2c()
        self._active_downloads: Dict[str, asyncio.subprocess.Process] = {}
    
    def _find_aria2c(self) -> Optional[str]:
        """Find aria2c executable"""
        return shutil.which("aria2c")
    
    def is_available(self) -> bool:
        """Check if aria2 is available"""
        return self.aria2_path is not None
    
    async def get_version(self) -> Optional[str]:
        """Get aria2 version"""
        if not self.aria2_path:
            return None
        try:
            proc = await asyncio.create_subprocess_exec(
                self.aria2_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            first_line = stdout.decode().strip().split("\n")[0] if stdout else ""
            return first_line
        except Exception:
            return None
    
    async def download_file(
        self,
        url: str,
        output_path: Path,
        on_progress: Optional[Callable[[DownloadProgress], None]] = None
    ) -> bool:
        """Download a file using aria2 or fallback to HTTP"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        progress = DownloadProgress(
            model_name=output_path.name,
            status="downloading",
            progress=0.0
        )
        
        if self.is_available():
            return await self._download_with_aria2(url, output_path, progress, on_progress)
        else:
            return await self._download_with_http(url, output_path, progress, on_progress)
    
    async def _download_with_aria2(self, url: str, output_path: Path, 
                                    progress: DownloadProgress,
                                    on_progress: Optional[Callable[[DownloadProgress], None]]) -> bool:
        """Download using aria2"""
        try:
            cmd = [
                self.aria2_path,
                "-x", "16",
                "-s", "16",
                "-k", "1M",
                "-d", str(output_path.parent),
                "-o", output_path.name,
                "--summary-interval=1",
                url
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self._active_downloads[url] = proc
            
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                
                line = line.decode().strip()
                
                if "NOTICE" in line and "Download completed" in line:
                    progress.status = "completed"
                    progress.progress = 100.0
                    if on_progress:
                        on_progress(progress)
                    return True
                
                elif "%" in line:
                    try:
                        parts = line.split("(")
                        if len(parts) > 1:
                            percent_str = parts[1].split("%")[0]
                            progress.progress = float(percent_str)
                            if on_progress:
                                on_progress(progress)
                    except (ValueError, IndexError):
                        pass
            
            await proc.wait()
            return proc.returncode == 0
            
        except Exception as e:
            logger.error(f"aria2 download error: {e}")
            return False
        finally:
            if url in self._active_downloads:
                del self._active_downloads[url]
    
    async def _download_with_http(self, url: str, output_path: Path,
                                   progress: DownloadProgress,
                                   on_progress: Optional[Callable[[DownloadProgress], None]]) -> bool:
        """Download using HTTP"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3600.0)) as client:
                async with client.stream("GET", url, follow_redirects=True) as response:
                    response.raise_for_status()
                    
                    total = int(response.headers.get("content-length", 0))
                    progress.total_bytes = total
                    
                    downloaded = 0
                    
                    with open(output_path, "wb") as f:
                        async for chunk in response.aiter_bytes(1024 * 1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress.downloaded_bytes = downloaded
                            
                            if total > 0:
                                progress.progress = (downloaded / total) * 100
                            
                            if on_progress:
                                on_progress(progress)
                    
                    progress.status = "completed"
                    progress.progress = 100
                    if on_progress:
                        on_progress(progress)
                    return True
                    
        except Exception as e:
            logger.error(f"HTTP download error: {e}")
            progress.status = "error"
            progress.error = str(e)
            if on_progress:
                on_progress(progress)
            return False
    
    async def cancel_download(self, url: str) -> bool:
        """Cancel an active download"""
        if url in self._active_downloads:
            proc = self._active_downloads[url]
            try:
                proc.terminate()
                await proc.wait()
                return True
            except Exception:
                return False
        return False
    
    async def get_install_instructions(self, platform: str) -> Dict[str, Any]:
        """Get installation instructions for aria2"""
        instructions = {
            "windows": {
                "method": "winget or chocolatey",
                "commands": [
                    "winget install aria2",
                    "# or",
                    "choco install aria2"
                ],
                "download_url": "https://github.com/aria2/aria2/releases"
            },
            "darwin": {
                "method": "Homebrew",
                "commands": ["brew install aria2"],
                "download_url": "https://github.com/aria2/aria2/releases"
            },
            "linux": {
                "method": "Package manager",
                "commands": [
                    "# Ubuntu/Debian",
                    "sudo apt install aria2",
                    "# Fedora",
                    "sudo dnf install aria2",
                    "# Arch",
                    "sudo pacman -S aria2"
                ],
                "download_url": "https://github.com/aria2/aria2/releases"
            }
        }
        
        return instructions.get(platform, instructions["linux"])