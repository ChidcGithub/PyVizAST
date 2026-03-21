"""
Base API routes (root, health check)

@author: Chidc
@link: github.com/chidcGithub
"""
from fastapi import APIRouter

from ..config import VERSION

router = APIRouter(tags=["base"])


@router.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "PyVizAST API",
        "version": VERSION,
        "description": "Python AST Visualizer and Static Analyzer",
        "status": "running",
        "endpoints": {
            "analyze": "/api/analyze",
            "ast": "/api/ast",
            "complexity": "/api/complexity",
            "performance": "/api/performance",
            "security": "/api/security",
            "suggestions": "/api/suggestions",
            "docs": "/docs"
        }
    }


@router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "PyVizAST API"}
