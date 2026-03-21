"""
Frontend log receiving API routes

@author: Chidc
@link: github.com/chidcGithub
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["logs"])


class FrontendLogEntry(BaseModel):
    """Frontend log entry model"""
    timestamp: str
    level: str
    message: str
    userAgent: Optional[str] = None
    url: Optional[str] = None
    reason: Optional[str] = None
    stack: Optional[str] = None
    componentStack: Optional[str] = None
    filename: Optional[str] = None
    lineno: Optional[int] = None
    colno: Optional[int] = None


class FrontendLogsRequest(BaseModel):
    """Frontend logs request model"""
    logs: List[FrontendLogEntry]


# Ensure log directory exists
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"


def ensure_logs_dir():
    """Ensure log directory exists"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_log_content(content: str, max_length: int = 500) -> str:
    """Sanitize log content to prevent log injection attacks
    
    Removes/escapes potentially dangerous characters:
    - Newlines (prevent log entry spoofing)
    - Control characters
    """
    if not content:
        return ""
    
    # Truncate to max length
    content = content[:max_length]
    
    # Remove control characters and newlines
    sanitized = ""
    for char in content:
        if char == '\n':
            sanitized += '\\n'
        elif char == '\r':
            sanitized += '\\r'
        elif char == '\t':
            sanitized += '\\t'
        elif ord(char) < 32:
            # Skip other control characters
            continue
        else:
            sanitized += char
    
    return sanitized


@router.post("/frontend")
async def receive_frontend_logs(request: FrontendLogsRequest):
    """Receive frontend logs and save to file"""
    ensure_logs_dir()
    
    # Generate log filename (by date)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"frontend-{today}.log"
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            for log_entry in request.logs:
                # Format log entry with sanitized content
                log_line = (
                    f"[{sanitize_log_content(log_entry.timestamp, 30)}] "
                    f"[{sanitize_log_content(log_entry.level, 10).upper()}] "
                    f"{sanitize_log_content(log_entry.message, 1000)}"
                )
                
                # Add extra info with sanitized content
                extras = []
                if log_entry.url:
                    extras.append(f"url={sanitize_log_content(log_entry.url, 200)}")
                if log_entry.filename:
                    extras.append(f"file={sanitize_log_content(log_entry.filename, 200)}:{log_entry.lineno}:{log_entry.colno}")
                if log_entry.stack:
                    extras.append(f"stack={sanitize_log_content(log_entry.stack, 500)}")
                if log_entry.componentStack:
                    extras.append(f"componentStack={sanitize_log_content(log_entry.componentStack, 500)}")
                
                if extras:
                    log_line += f" | {' | '.join(extras)}"
                
                f.write(log_line + "\n")
        
        logger.debug(f"Saved {len(request.logs)} frontend log entries")
        return {"status": "ok", "count": len(request.logs)}
    
    except Exception as e:
        logger.error(f"Failed to save frontend logs: {e}")
        return {"status": "error", "message": str(e)}
