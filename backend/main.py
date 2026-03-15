"""
PyVizAST - FastAPI Backend
AST-based Python Code Visualizer and Optimization Analyzer

@author: Chidc
@link: github.com/chidcGithub
"""
import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .utils.logger import log_exception, init_logging
from .config import VERSION
from .exceptions import (
    AnalysisError,
    CodeParsingError,
    CodeTooLargeError,
    ResourceNotFoundError,
)
from .routers import (
    base_router,
    progress_router,
    analysis_router,
    ast_router,
    learning_router,
    challenges_router,
    projects_router,
    logs_router,
)


# Initialize logging system
logger = init_logging(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("PyVizAST API starting up...")
    logger.info(f"Python version: {__import__('sys').version.split()[0]}")
    logger.info(f"FastAPI version: {__import__('fastapi').__version__}")
    
    yield
    
    # Shutdown
    logger.info("PyVizAST API shutting down...")


# Create FastAPI application with lifespan
app = FastAPI(
    title="PyVizAST API",
    description="Python AST Visualization and Static Analysis API",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Cache-Control"],
)


# Request timing middleware for performance monitoring
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses for monitoring."""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    
    # Log slow requests (> 1 second)
    if process_time > 1.0:
        logger.warning(f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s")
    
    return response


# ============== Global Exception Handlers ==============

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    log_exception(logger, exc, f"Request path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"Input validation failed: {exc}"}
    )


@app.exception_handler(CodeParsingError)
async def code_parsing_exception_handler(request: Request, exc: CodeParsingError):
    """Handle code parsing errors"""
    logger.warning(f"Code parsing error: {exc} | Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(CodeTooLargeError)
async def code_too_large_exception_handler(request: Request, exc: CodeTooLargeError):
    """Handle code too large errors"""
    logger.warning(f"Code too large: {exc} | Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={"detail": str(exc)}
    )


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_exception_handler(request: Request, exc: ResourceNotFoundError):
    """Handle resource not found errors"""
    logger.warning(f"Resource not found: {exc} | Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)}
    )


@app.exception_handler(AnalysisError)
async def analysis_exception_handler(request: Request, exc: AnalysisError):
    """Handle errors during analysis"""
    log_exception(logger, exc, f"Request path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Error during analysis: {str(exc)}"}
    )


@app.exception_handler(OSError)
async def os_exception_handler(request: Request, exc: OSError):
    """Handle OS errors (e.g., file operations)"""
    log_exception(logger, exc, f"Request path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error, please try again later"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    log_exception(logger, exc, f"Request path: {request.url.path}")
    
    # Provide user-friendly messages without exposing internal details
    if isinstance(exc, TypeError):
        detail = "An internal type error occurred. The code structure may be unexpected."
    elif isinstance(exc, AttributeError):
        detail = "An internal attribute error occurred. The code structure may be unexpected."
    elif isinstance(exc, ValueError):
        detail = "An invalid value was encountered during analysis."
    elif isinstance(exc, KeyError):
        detail = "Some expected data is missing in the analysis."
    elif isinstance(exc, RecursionError):
        detail = "Code structure is too deeply nested to analyze. Consider simplifying the code."
    elif isinstance(exc, MemoryError):
        detail = "Not enough memory to analyze this code. Try with a smaller file."
    else:
        detail = "An unexpected error occurred during analysis. Please try again."
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail}
    )


# ============== Register Routers ==============

app.include_router(base_router)
app.include_router(progress_router)
app.include_router(analysis_router)
app.include_router(ast_router)
app.include_router(learning_router)
app.include_router(challenges_router)
app.include_router(projects_router)
app.include_router(logs_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
