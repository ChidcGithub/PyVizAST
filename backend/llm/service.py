"""
LLM Service - Core service for LLM operations

@author: Chidc
@link: github.com/chidcGithub
"""
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any, AsyncIterator
from pathlib import Path

from .models import (
    LLMConfig,
    LLMStatus,
    ModelInfo,
    GeneratedExplanation,
    GeneratedChallenge,
    ChallengeDifficulty,
)
from .ollama_client import OllamaClient, OllamaError
from .prompts import (
    get_node_explanation_prompt,
    get_challenge_generation_prompt,
    get_challenge_hint_prompt,
    get_code_improvement_prompt,
    SYSTEM_PROMPT_EXPLANATION,
    SYSTEM_PROMPT_CHALLENGE,
)

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-powered features"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client: Optional[OllamaClient] = None
        self._status = LLMStatus.UNAVAILABLE
        self._cached_models: List[ModelInfo] = []
    
    @property
    def client(self) -> OllamaClient:
        """Get or create Ollama client"""
        if self._client is None:
            self._client = OllamaClient(self.config)
        return self._client
    
    @property
    def status(self) -> LLMStatus:
        return self._status
    
    @property
    def is_enabled(self) -> bool:
        return self.config.enabled
    
    def update_config(self, config: LLMConfig) -> None:
        """Update LLM configuration"""
        self.config = config
        self._client = None  # Reset client to use new config
    
    async def check_status(self) -> Dict[str, Any]:
        """Check LLM service status and available models"""
        if not self.config.enabled:
            return {
                "status": LLMStatus.UNAVAILABLE.value,
                "enabled": False,
                "message": "LLM features are disabled"
            }
        
        try:
            available = await self.client.is_available()
            if not available:
                self._status = LLMStatus.UNAVAILABLE
                return {
                    "status": LLMStatus.UNAVAILABLE.value,
                    "enabled": True,
                    "message": "Ollama server is not running. Please start Ollama first."
                }
            
            models = await self.client.list_models()
            self._cached_models = models
            
            # Check if configured model is available
            model_names = [m.name for m in models]
            has_model = any(self.config.model in name or name.startswith(self.config.model.split(":")[0]) for name in model_names)
            
            if has_model:
                self._status = LLMStatus.READY
                return {
                    "status": LLMStatus.READY.value,
                    "enabled": True,
                    "model": self.config.model,
                    "models": [{"name": m.name, "size": m.size} for m in models],
                    "message": "LLM service is ready"
                }
            else:
                self._status = LLMStatus.UNAVAILABLE
                return {
                    "status": LLMStatus.UNAVAILABLE.value,
                    "enabled": True,
                    "model": self.config.model,
                    "models": [{"name": m.name, "size": m.size} for m in models],
                    "message": f"Model {self.config.model} not found. Please pull it first."
                }
        except Exception as e:
            self._status = LLMStatus.ERROR
            logger.error(f"Error checking LLM status: {e}")
            return {
                "status": LLMStatus.ERROR.value,
                "enabled": True,
                "message": f"Error: {str(e)}"
            }
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available (pulled) models"""
        try:
            models = await self.client.list_models()
            return [
                {
                    "name": m.name,
                    "size": m.size,
                    "modified_at": m.modified_at
                }
                for m in models
            ]
        except OllamaError:
            return []
    
    def get_recommended_models(self) -> List[Dict[str, Any]]:
        """Get list of recommended models"""
        return ModelInfo.get_recommended_models()
    
    async def generate_explanation(
        self,
        node_type: str,
        node_name: Optional[str] = None,
        node_info: Optional[dict] = None,
        code_context: Optional[str] = None
    ) -> GeneratedExplanation:
        """Generate explanation for an AST node using LLM"""
        if not self.config.enabled or self._status != LLMStatus.READY:
            raise RuntimeError("LLM service is not available")
        
        prompt = get_node_explanation_prompt(
            node_type=node_type,
            node_name=node_name,
            node_info=node_info or {},
            code_context=code_context
        )
        
        try:
            response = await self.client.generate(
                prompt=prompt,
                system=SYSTEM_PROMPT_EXPLANATION,
                temperature=0.7
            )
            
            # Parse JSON response
            # Handle potential markdown code blocks
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            
            return GeneratedExplanation(
                node_type=node_type,
                explanation=data.get("explanation", ""),
                python_doc=data.get("python_doc", ""),
                examples=data.get("examples", []),
                related_concepts=data.get("related_concepts", [])
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Return basic explanation on parse error
            return GeneratedExplanation(
                node_type=node_type,
                explanation=f"This is a {node_type} node in Python's AST.",
                python_doc="",
                examples=[],
                related_concepts=[]
            )
        except OllamaError as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    async def generate_challenge(
        self,
        category: str,
        difficulty: str = "medium",
        topic: Optional[str] = None,
        focus_issues: Optional[List[str]] = None
    ) -> GeneratedChallenge:
        """Generate a new challenge using LLM"""
        if not self.config.enabled or self._status != LLMStatus.READY:
            raise RuntimeError("LLM service is not available")
        
        prompt = get_challenge_generation_prompt(
            category=category,
            difficulty=difficulty,
            topic=topic,
            focus_issues=focus_issues
        )
        
        try:
            response = await self.client.generate(
                prompt=prompt,
                system=SYSTEM_PROMPT_CHALLENGE,
                temperature=0.8
            )
            
            # Parse JSON response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            
            return GeneratedChallenge(
                title=data.get("title", "Generated Challenge"),
                description=data.get("description", ""),
                category=data.get("category", category),
                code=data.get("code", ""),
                issues=data.get("issues", []),
                difficulty=ChallengeDifficulty(data.get("difficulty", difficulty).lower()),
                learning_objectives=data.get("learning_objectives", []),
                hints=data.get("hints", []),
                solution_hint=data.get("solution_hint", ""),
                estimated_time_minutes=data.get("estimated_time_minutes", 5),
                points=data.get("points", 100)
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse challenge response: {e}")
            raise ValueError("Failed to generate a valid challenge")
        except OllamaError as e:
            logger.error(f"Challenge generation failed: {e}")
            raise
    
    async def generate_hint(
        self,
        code: str,
        issues: List[str],
        user_progress: str
    ) -> str:
        """Generate contextual hint for a challenge"""
        if not self.config.enabled or self._status != LLMStatus.READY:
            return ""
        
        prompt = get_challenge_hint_prompt(
            code=code,
            issues=issues,
            user_progress=user_progress
        )
        
        try:
            response = await self.client.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=100
            )
            
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            return data.get("hint", "")
        except (json.JSONDecodeError, OllamaError) as e:
            logger.warning(f"Hint generation failed: {e}")
            return ""
    
    async def generate_improvement_suggestions(
        self,
        code: str,
        issues: List[str]
    ) -> Dict[str, Any]:
        """Generate code improvement suggestions"""
        if not self.config.enabled or self._status != LLMStatus.READY:
            return {"improved_code": "", "changes": [], "explanation": ""}
        
        prompt = get_code_improvement_prompt(code=code, issues=issues)
        
        try:
            response = await self.client.generate(
                prompt=prompt,
                system=SYSTEM_PROMPT_EXPLANATION,
                temperature=0.7
            )
            
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except (json.JSONDecodeError, OllamaError) as e:
            logger.error(f"Improvement generation failed: {e}")
            return {"improved_code": "", "changes": [], "explanation": ""}


# Global service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def init_llm_service(config: LLMConfig) -> LLMService:
    """Initialize LLM service with configuration"""
    global _llm_service
    _llm_service = LLMService(config)
    return _llm_service
