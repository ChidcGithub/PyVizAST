"""
LLM Data Models

@author: Chidc
@link: github.com/chidcGithub
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    OPENAI = "openai"  # Future support


class LLMStatus(str, Enum):
    """LLM service status"""
    UNAVAILABLE = "unavailable"
    READY = "ready"
    DOWNLOADING = "downloading"
    ERROR = "error"


class ModelInfo(BaseModel):
    """Information about an LLM model"""
    name: str
    size: int  # Size in bytes (Ollama returns integer)
    digest: str
    modified_at: str
    details: Optional[Dict[str, Any]] = None
    
    # Recommended models for PyVizAST
    @classmethod
    def get_recommended_models(cls) -> List[Dict[str, Any]]:
        """Get list of recommended models for code analysis"""
        return [
            {
                "name": "codellama:7b",
                "display_name": "CodeLlama 7B",
                "description": "Optimized for code, good balance of speed and quality",
                "size_gb": 3.8,
                "ram_required": "8GB",
                "recommended_for": ["code_analysis", "explanations", "challenges"],
                "download_command": "ollama pull codellama:7b"
            },
            {
                "name": "codellama:13b",
                "display_name": "CodeLlama 13B",
                "description": "Better quality for complex code, slower inference",
                "size_gb": 7.4,
                "ram_required": "16GB",
                "recommended_for": ["code_analysis", "explanations", "challenges"],
                "download_command": "ollama pull codellama:13b"
            },
            {
                "name": "llama3.2:3b",
                "display_name": "Llama 3.2 3B",
                "description": "Fast and efficient, good for quick explanations",
                "size_gb": 2.0,
                "ram_required": "6GB",
                "recommended_for": ["explanations", "quick_analysis"],
                "download_command": "ollama pull llama3.2:3b"
            },
            {
                "name": "mistral:7b",
                "display_name": "Mistral 7B",
                "description": "Excellent general-purpose model, good code understanding",
                "size_gb": 4.1,
                "ram_required": "8GB",
                "recommended_for": ["explanations", "challenges", "general"],
                "download_command": "ollama pull mistral:7b"
            },
            {
                "name": "deepseek-coder:6.7b",
                "display_name": "DeepSeek Coder 6.7B",
                "description": "Specialized for code, excellent for Python analysis",
                "size_gb": 3.8,
                "ram_required": "8GB",
                "recommended_for": ["code_analysis", "challenges", "python"],
                "download_command": "ollama pull deepseek-coder:6.7b"
            },
            {
                "name": "qwen2.5-coder:7b",
                "display_name": "Qwen 2.5 Coder 7B",
                "description": "Strong multilingual code model, supports Chinese",
                "size_gb": 4.7,
                "ram_required": "8GB",
                "recommended_for": ["code_analysis", "challenges", "multilingual"],
                "download_command": "ollama pull qwen2.5-coder:7b"
            }
        ]


class LLMConfig(BaseModel):
    """LLM configuration settings"""
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "codellama:7b"
    base_url: str = "http://localhost:11434"
    timeout: int = 60
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    enabled: bool = False
    
    # Feature toggles
    use_for_explanations: bool = True
    use_for_challenges: bool = True
    use_for_hints: bool = True


class DownloadProgress(BaseModel):
    """Model download progress"""
    model_name: str
    status: str  # "downloading", "completed", "error", "cancelled", "installing"
    progress: float = 0.0  # 0-100
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: str = "0 B/s"
    eta: str = "calculating..."
    error: Optional[str] = None


class OllamaInstallStatus(BaseModel):
    """Ollama installation status"""
    installed: bool = False
    running: bool = False
    version: Optional[str] = None
    platform: str = "unknown"
    install_dir: Optional[str] = None
    executable: Optional[str] = None
    can_auto_install: bool = False
    models_count: int = 0


class OllamaInstallProgress(BaseModel):
    """Progress for Ollama installation"""
    status: str  # "downloading", "extracting", "installing", "completed", "error"
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: str = ""
    error: Optional[str] = None


class GeneratedExplanation(BaseModel):
    """LLM-generated node explanation"""
    node_type: str
    explanation: str
    python_doc: str
    examples: List[str] = []
    related_concepts: List[str] = []
    best_practices: List[str] = []
    common_pitfalls: List[str] = []


class ChallengeDifficulty(str, Enum):
    """Challenge difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GeneratedChallenge(BaseModel):
    """LLM-generated challenge"""
    title: str
    description: str
    category: str
    code: str
    issues: List[str]
    difficulty: ChallengeDifficulty
    learning_objectives: List[str] = []
    hints: List[str] = []
    solution_hint: str = ""
    estimated_time_minutes: int = 5
    points: int = 100


class ChallengeCategory(BaseModel):
    """Challenge category"""
    id: str
    name: str
    description: str
    icon: str = "star"
    challenge_count: int = 0
    total_points: int = 0
