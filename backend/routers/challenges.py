"""
Challenge API routes

@author: Chidc
@link: github.com/chidcGithub
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..models.schemas import ChallengeResult
from ..exceptions import ResourceNotFoundError
from ..llm import get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


class ChallengeSubmission(BaseModel):
    challenge_id: str
    found_issues: List[str]


class GenerateChallengeRequest(BaseModel):
    category: str
    difficulty: str = "medium"
    topic: Optional[str] = None
    focus_issues: Optional[List[str]] = None


def load_challenges() -> List[Dict[str, Any]]:
    """Load challenge data from JSON file"""
    challenges_path = Path(__file__).parent.parent / "data" / "challenges.json"
    try:
        import json
        with open(challenges_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("challenges", [])
    except FileNotFoundError:
        logger.warning(f"Challenge data file not found: {challenges_path}")
        return []
    except Exception as e:
        logger.error(f"Challenge data parse error: {e}")
        return []


def get_challenges_cache() -> List[Dict[str, Any]]:
    """Get challenge data (with cache, auto-reload on file change)"""
    challenges_path = Path(__file__).parent.parent / "data" / "challenges.json"
    
    # Check if cache needs to be refreshed
    if not hasattr(get_challenges_cache, '_cache'):
        get_challenges_cache._cache = load_challenges()
        get_challenges_cache._mtime = challenges_path.stat().st_mtime if challenges_path.exists() else 0
    elif challenges_path.exists():
        current_mtime = challenges_path.stat().st_mtime
        if current_mtime != get_challenges_cache._mtime:
            get_challenges_cache._cache = load_challenges()
            get_challenges_cache._mtime = current_mtime
            logger.debug("Challenge data reloaded due to file change")
    
    return get_challenges_cache._cache


def clear_challenges_cache():
    """Clear challenge cache to force reload"""
    if hasattr(get_challenges_cache, '_cache'):
        delattr(get_challenges_cache, '_cache')
    if hasattr(get_challenges_cache, '_mtime'):
        delattr(get_challenges_cache, '_mtime')
    logger.debug("Challenge cache cleared")


def load_challenge_categories() -> List[Dict[str, Any]]:
    """Load challenge categories from JSON file"""
    challenges_path = Path(__file__).parent.parent / "data" / "challenges.json"
    try:
        import json
        with open(challenges_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("categories", [])
    except FileNotFoundError:
        logger.warning(f"Challenge categories file not found: {challenges_path}")
        return []
    except Exception as e:
        logger.error(f"Challenge categories parse error: {e}")
        return []


def _generate_challenge_feedback(correct, missed, wrong, solution_hint=None, passed=False):
    """Generate comprehensive challenge feedback"""
    feedback = []
    
    if passed:
        feedback.append("Congratulations! You passed this challenge!")
    else:
        feedback.append("Keep practicing! You're getting there.")
    
    if correct:
        feedback.append(f"Correctly identified: {', '.join(sorted(correct))}")
    
    if missed:
        feedback.append(f"Missed issues: {', '.join(sorted(missed))}")
    
    if wrong:
        feedback.append(f"Incorrectly identified: {', '.join(sorted(wrong))}")
    
    if solution_hint and not passed:
        feedback.append(f"Hint: {solution_hint}")
    
    return "\n\n".join(feedback) if feedback else "Keep trying!"


@router.post("/reload")
async def reload_challenges():
    """Force reload challenge data from file"""
    clear_challenges_cache()
    challenges = get_challenges_cache()
    return {"status": "ok", "count": len(challenges), "message": "Challenges reloaded"}


@router.get("/categories")
async def get_challenge_categories():
    """Get challenge categories"""
    logger.debug("Getting challenge categories")
    categories = load_challenge_categories()
    challenges = get_challenges_cache()
    
    # Enrich categories with challenge details
    for category in categories:
        category_challenges = [c for c in challenges if c["id"] in category.get("challenges", [])]
        category["challenge_count"] = len(category_challenges)
        category["total_points"] = sum(c.get("points", 0) for c in category_challenges)
    
    return categories


@router.get("")
async def get_challenges():
    """Get challenge list"""
    logger.debug("Getting challenge list")
    challenges = get_challenges_cache()
    return [
        {
            "id": c["id"], 
            "title": c["title"], 
            "difficulty": c["difficulty"],
            "category": c.get("category"),
            "estimated_time_minutes": c.get("estimated_time_minutes"),
            "points": c.get("points", 0)
        } 
        for c in challenges
    ]


@router.get("/{challenge_id}")
async def get_challenge(challenge_id: str):
    """Get challenge details"""
    logger.debug(f"Getting challenge details: {challenge_id}")
    challenges = get_challenges_cache()
    for challenge in challenges:
        if challenge["id"] == challenge_id:
            return {
                "id": challenge["id"],
                "title": challenge["title"],
                "description": challenge["description"],
                "code": challenge["code"],
                "category": challenge.get("category"),
                "difficulty": challenge["difficulty"],
                "hints": challenge.get("hints", []),
                "learning_objectives": challenge.get("learning_objectives", []),
                "solution_hint": challenge.get("solution_hint"),
                "points": challenge.get("points", 0),
                "estimated_time_minutes": challenge.get("estimated_time_minutes", 5)
            }
    raise ResourceNotFoundError(f"Challenge not found: {challenge_id}")


@router.post("/submit")
async def submit_challenge(submission: ChallengeSubmission):
    """Submit challenge answer"""
    logger.debug(f"Submitting challenge answer: {submission.challenge_id}")
    challenges = get_challenges_cache()
    for challenge in challenges:
        if challenge["id"] == submission.challenge_id:
            expected = set(challenge["issues"])
            found = set(submission.found_issues)
            
            correct = found & expected
            missed = expected - found
            wrong = found - expected
            
            # Calculate score based on points
            base_points = challenge.get("points", 100)
            correct_ratio = len(correct) / len(expected) if expected else 0
            penalty = len(wrong) * 0.1  # 10% penalty per wrong answer
            score = max(0, int(base_points * correct_ratio * (1 - penalty)))
            
            # Determine if passed (at least 60% of issues found)
            passed = correct_ratio >= 0.6
            
            return ChallengeResult(
                challenge_id=submission.challenge_id,
                score=score,
                max_score=base_points,
                found_issues=list(correct),
                missed_issues=list(missed),
                feedback=_generate_challenge_feedback(correct, missed, wrong, challenge.get("solution_hint"), passed),
                passed=passed
            )
    
    raise ResourceNotFoundError(f"Challenge not found: {submission.challenge_id}")


# ============== LLM-Powered Challenge Generation ==============

@router.post("/generate")
async def generate_challenge_llm(request: GenerateChallengeRequest):
    """Generate a new challenge using LLM"""
    llm_service = get_llm_service()
    
    if not llm_service.is_enabled:
        raise ResourceNotFoundError("LLM service is not enabled. Enable it in settings.")
    
    try:
        challenge = await llm_service.generate_challenge(
            category=request.category,
            difficulty=request.difficulty,
            topic=request.topic,
            focus_issues=request.focus_issues
        )
        
        return {
            "id": f"llm_generated_{request.category}_{hash(challenge.title) % 10000}",
            "title": challenge.title,
            "description": challenge.description,
            "code": challenge.code,
            "category": challenge.category,
            "difficulty": challenge.difficulty.value,
            "hints": challenge.hints,
            "learning_objectives": challenge.learning_objectives,
            "solution_hint": challenge.solution_hint,
            "points": challenge.points,
            "estimated_time_minutes": challenge.estimated_time_minutes,
            "issues": challenge.issues,
            "llm_generated": True
        }
    except RuntimeError as e:
        raise ResourceNotFoundError(str(e))
    except Exception as e:
        logger.error(f"Challenge generation failed: {e}")
        raise ResourceNotFoundError(f"Failed to generate challenge: {str(e)}")


@router.post("/hint")
async def get_llm_hint(request: GenerateChallengeRequest):
    """Get an LLM-generated hint for a challenge"""
    llm_service = get_llm_service()
    
    if not llm_service.is_enabled:
        return {"hint": "", "available": False}
    
    # This endpoint is for getting hints during challenge solving
    # The actual hint generation needs the challenge code and issues
    return {"hint": "", "available": True, "message": "Use the challenge hint endpoint with code context"}