"""
PyVizAST API Routers

@author: Chidc
@link: github.com/chidcGithub
"""
from .base import router as base_router
from .progress import router as progress_router
from .analysis import router as analysis_router
from .ast_routes import router as ast_router
from .learning import router as learning_router
from .challenges import router as challenges_router
from .projects import router as projects_router
from .logs import router as logs_router
from .llm import router as llm_router

__all__ = [
    'base_router',
    'progress_router',
    'analysis_router',
    'ast_router',
    'learning_router',
    'challenges_router',
    'projects_router',
    'logs_router',
    'llm_router',
]
