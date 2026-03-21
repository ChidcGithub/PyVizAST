"""
LLM Service - Core service for LLM operations

@author: Chidc
@link: github.com/chidcGithub
"""
import json
import logging
import asyncio
import threading
import re
import time
from typing import List, Optional, Dict, Any, Tuple

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


# ============== Response Parsing Utilities ==============

def _extract_json_from_response(response: str) -> Optional[dict]:
    """
    Extract JSON from LLM response with multiple fallback strategies.
    
    Strategies (in order):
    1. Direct JSON parse
    2. Remove markdown code blocks
    3. Find JSON object boundaries
    4. Extract key-value pairs heuristically
    """
    if not response:
        return None
    
    response = response.strip()
    
    # Strategy 1: Direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Remove markdown code blocks
    cleaned = response
    for prefix in ['```json', '```JSON', '```']:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Find JSON object boundaries
    start_idx = response.find('{')
    end_idx = response.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = response[start_idx:end_idx + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Heuristic extraction for explanation format
    # Try to extract fields manually
    result = {}
    
    # Extract explanation
    exp_match = re.search(r'"explanation"\s*:\s*"([^"]+)"', response, re.DOTALL)
    if exp_match:
        result['explanation'] = exp_match.group(1)
    
    # Extract python_doc
    doc_match = re.search(r'"python_doc"\s*:\s*"([^"]+)"', response, re.DOTALL)
    if doc_match:
        result['python_doc'] = doc_match.group(1)
    
    # Extract examples array
    examples_match = re.search(r'"examples"\s*:\s*\[(.*?)\]', response, re.DOTALL)
    if examples_match:
        examples_str = examples_match.group(1)
        examples = re.findall(r'"([^"]+)"', examples_str)
        if examples:
            result['examples'] = examples
    
    # Extract related_concepts array
    concepts_match = re.search(r'"related_concepts"\s*:\s*\[(.*?)\]', response, re.DOTALL)
    if concepts_match:
        concepts_str = concepts_match.group(1)
        concepts = re.findall(r'"([^"]+)"', concepts_str)
        if concepts:
            result['related_concepts'] = concepts
    
    if result:
        return result
    
    return None


def _create_fallback_explanation(node_type: str, raw_response: str = "") -> GeneratedExplanation:
    """Create a basic explanation when LLM response parsing fails"""
    
    # Try to extract any meaningful text from the response
    text_content = raw_response[:500] if raw_response else ""
    
    # Clean up the text if it looks like prose
    if text_content and not text_content.startswith('{'):
        # Remove common LLM preamble
        for prefix in ['Here is', 'Here\'s', 'The explanation', 'Sure,', 'Certainly,']:
            if text_content.startswith(prefix):
                # Find end of first sentence
                end = text_content.find('.')
                if end > 0:
                    text_content = text_content[end + 1:].strip()
                break
    
    return GeneratedExplanation(
        node_type=node_type,
        explanation=text_content if text_content else f"This is a {node_type} node in Python's Abstract Syntax Tree.",
        python_doc=f"The {node_type} represents a specific construct in Python code. Consult Python documentation for details.",
        examples=[f"# Example of {node_type}\n# (LLM parsing failed)"],
        related_concepts=[node_type, "AST", "Python"]
    )


# ============== Simple Cache ==============

class SimpleCache:
    """Thread-safe simple cache with TTL"""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    return value
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            # Evict old entries if at capacity
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (value, time.time())
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


# ============== LLM Service ==============

class LLMService:
    """Service for LLM-powered features"""
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    RETRY_BACKOFF = 2.0  # multiplier
    
    # Cache for explanations (5 minute TTL)
    _explanation_cache = SimpleCache(ttl_seconds=300, max_size=50)
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client: Optional[OllamaClient] = None
        self._status = LLMStatus.UNAVAILABLE
        self._cached_models: List[ModelInfo] = []
    
    async def _generate_with_retry(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text with exponential backoff retry"""
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return await self.client.generate(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except OllamaError as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY * (self.RETRY_BACKOFF ** attempt)
                    logger.warning(f"LLM attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM failed after {self.MAX_RETRIES} attempts: {e}")
                    raise
        
        raise last_error or OllamaError("Unknown error during generation")
    
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
        self._explanation_cache.clear()  # Clear cache on config change
    
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
        except Exception as e:
            logger.warning(f"Failed to check Ollama availability: {e}")
            self._status = LLMStatus.UNAVAILABLE
            return {
                "status": LLMStatus.UNAVAILABLE.value,
                "enabled": True,
                "message": f"Cannot connect to Ollama: {str(e)}"
            }
        
        try:
            models = await self.client.list_models()
            self._cached_models = models
        except OllamaError as e:
            logger.warning(f"Failed to list models: {e}")
            self._status = LLMStatus.ERROR
            return {
                "status": LLMStatus.ERROR.value,
                "enabled": True,
                "message": f"Failed to list models: {str(e)}"
            }
        
        # Check if configured model is available (case-insensitive matching)
        model_names = [m.name for m in models]
        config_model = self.config.model.strip()
        config_model_lower = config_model.lower()
        config_base = config_model_lower.split(":")[0]  # e.g., "codellama" from "codellama:7b"
        config_tag = config_model_lower.split(":")[1] if ":" in config_model_lower else None
        
        logger.info(f"Checking model: config='{config_model}', available={model_names}")
        
        # Matching logic with priority:
        # 1. Exact match (case-insensitive)
        # 2. Tag match if config has tag
        # 3. Base name match (any tag)
        has_model = False
        matched_model = None
        
        for name in model_names:
            name_lower = name.lower()
            
            # Exact match (case-insensitive)
            if name_lower == config_model_lower:
                has_model = True
                matched_model = name
                logger.debug(f"Exact match: {name}")
                break
            
            # Parse installed model name
            name_parts = name_lower.split(":")
            name_base = name_parts[0]
            name_tag = name_parts[1] if len(name_parts) > 1 else "latest"
            
            # If config has tag, must match both base and tag
            if config_tag is not None:
                if name_base == config_base and name_tag == config_tag:
                    has_model = True
                    matched_model = name
                    logger.debug(f"Tag match: base={name_base}, tag={name_tag}")
                    break
            else:
                # Config only has base name, match any version
                if name_base == config_base:
                    has_model = True
                    matched_model = name
                    logger.debug(f"Base match: {name_base}")
                    break
        
        logger.info(f"Model match result: has_model={has_model}, matched={matched_model}")
        
        if has_model:
            self._status = LLMStatus.READY
            return {
                "status": LLMStatus.READY.value,
                "enabled": True,
                "model": self.config.model,
                "matched_model": matched_model,
                "models": [{"name": m.name, "size": m.size} for m in models],
                "message": "LLM service is ready"
            }
        else:
            self._status = LLMStatus.UNAVAILABLE
            available_models = ", ".join(model_names[:5])
            if len(model_names) > 5:
                available_models += f" (+{len(model_names) - 5} more)"
            return {
                "status": LLMStatus.UNAVAILABLE.value,
                "enabled": True,
                "model": self.config.model,
                "models": [{"name": m.name, "size": m.size} for m in models],
                "message": f"Model '{config_model}' not found. Available: {available_models}"
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
        code_context: Optional[str] = None,
        full_code: Optional[str] = None
    ) -> GeneratedExplanation:
        """
        Generate explanation for an AST node using LLM.
        
        Features:
        - Caching for repeated requests
        - Multi-strategy JSON parsing
        - Graceful fallback on errors
        """
        if not self.config.enabled or self._status != LLMStatus.READY:
            raise RuntimeError("LLM service is not available")
        
        # Create cache key
        cache_key = f"{node_type}:{node_name}:{hash(code_context or '')}"
        
        # Check cache
        cached = self._explanation_cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for {node_type}")
            return cached
        
        # Build prompt
        prompt = get_node_explanation_prompt(
            node_type=node_type,
            node_name=node_name,
            node_info=node_info or {},
            code_context=code_context,
            full_code=full_code
        )
        
        try:
            # Generate with retry
            response = await self._generate_with_retry(
                prompt=prompt,
                system=SYSTEM_PROMPT_EXPLANATION,
                temperature=0.7
            )
            
            # Parse response with multi-strategy extraction
            data = _extract_json_from_response(response)
            
            if data:
                explanation = GeneratedExplanation(
                    node_type=node_type,
                    explanation=data.get("explanation", ""),
                    python_doc=data.get("python_doc", ""),
                    examples=data.get("examples", []),
                    related_concepts=data.get("related_concepts", [])
                )
            else:
                # Fallback with raw response
                logger.warning(f"Could not parse JSON for {node_type}, using fallback")
                explanation = _create_fallback_explanation(node_type, response)
            
            # Cache successful result
            self._explanation_cache.set(cache_key, explanation)
            return explanation
            
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
            response = await self._generate_with_retry(
                prompt=prompt,
                system=SYSTEM_PROMPT_CHALLENGE,
                temperature=0.8
            )
            
            # Parse with multi-strategy extraction
            data = _extract_json_from_response(response)
            
            if not data:
                raise ValueError("Could not parse challenge response as JSON")
            
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
        except ValueError as e:
            logger.error(f"Challenge parsing failed: {e}")
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
            response = await self._generate_with_retry(
                prompt=prompt,
                temperature=0.7,
                max_tokens=100
            )
            
            data = _extract_json_from_response(response)
            return data.get("hint", "") if data else ""
            
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
            response = await self._generate_with_retry(
                prompt=prompt,
                system=SYSTEM_PROMPT_EXPLANATION,
                temperature=0.7
            )
            
            data = _extract_json_from_response(response)
            return data if data else {"improved_code": "", "changes": [], "explanation": ""}
            
        except (json.JSONDecodeError, OllamaError) as e:
            logger.error(f"Improvement generation failed: {e}")
            return {"improved_code": "", "changes": [], "explanation": ""}


# ============== Global Service Instance ==============

_llm_service: Optional[LLMService] = None
_service_lock = threading.Lock()


def get_llm_service() -> LLMService:
    """Get or create global LLM service instance (thread-safe)"""
    global _llm_service
    if _llm_service is None:
        with _service_lock:
            if _llm_service is None:
                _llm_service = LLMService()
    return _llm_service


def init_llm_service(config: LLMConfig) -> LLMService:
    """Initialize LLM service with configuration (thread-safe)"""
    global _llm_service
    with _service_lock:
        _llm_service = LLMService(config)
    return _llm_service