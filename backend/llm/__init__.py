"""
LLM Integration Module for PyVizAST

This module provides optional LLM (Large Language Model) integration
for enhanced code analysis, learning explanations, and challenge generation.

Uses Ollama for local LLM inference with aria2 for fast model downloads.

@author: Chidc
@link: github.com/chidcGithub
"""

from .service import LLMService, get_llm_service
from .ollama_client import OllamaClient
from .models import (
    LLMConfig,
    LLMStatus,
    ModelInfo,
    DownloadProgress,
    GeneratedExplanation,
    GeneratedChallenge,
)
from .downloader import Aria2Downloader

__all__ = [
    "LLMService",
    "get_llm_service",
    "OllamaClient",
    "LLMConfig",
    "LLMStatus",
    "ModelInfo",
    "DownloadProgress",
    "GeneratedExplanation",
    "GeneratedChallenge",
    "Aria2Downloader",
]
