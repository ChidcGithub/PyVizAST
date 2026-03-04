"""
Logging Configuration Module
Provides unified logging configuration, saves logs to the logs folder
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


# Log directory
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Get a configured logger
    
    Args:
        name: Logger name
        level: Log level
        log_to_file: Whether to log to file
        log_to_console: Whether to output to console
        max_bytes: Maximum size of a single log file
        backup_count: Number of log files to keep
    
    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Log format
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Detailed error log format (includes filename and line number)
    error_formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    if log_to_file:
        # Regular log file
        log_file = LOG_DIR / "app.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Error log file (logs ERROR and above separately)
        error_log_file = LOG_DIR / "error.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(error_formatter)
        logger.addHandler(error_handler)
    
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def log_exception(logger: logging.Logger, exc: Exception, context: Optional[str] = None):
    """
    Log detailed exception information
    
    Args:
        logger: Logger instance
        exc: Exception object
        context: Context information
    """
    import traceback
    
    context_str = f" [{context}]" if context else ""
    logger.error(
        f"Exception occurred{context_str}: {type(exc).__name__}: {str(exc)}\n"
        f"Stack trace:\n{traceback.format_exc()}"
    )


def get_request_logger() -> logging.Logger:
    """Get request logger"""
    return get_logger("pyvizast.request")


def get_error_logger() -> logging.Logger:
    """Get error logger"""
    return get_logger("pyvizast.error", level=logging.ERROR)


def get_access_logger() -> logging.Logger:
    """Get access logger"""
    return get_logger("pyvizast.access")


class ContextFilter(logging.Filter):
    """
    Log context filter
    Can add additional context information to logs
    """
    
    def __init__(self, context: str = ""):
        super().__init__()
        self.context = context
    
    def filter(self, record):
        record.context = self.context
        return True


def init_logging(level: int = logging.INFO):
    """
    Initialize global logging configuration
    
    Args:
        level: Log level
    """
    # Create main logger
    main_logger = get_logger("pyvizast", level=level)
    
    # Create log index file
    index_file = LOG_DIR / "index.txt"
    if not index_file.exists():
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(f"PyVizAST Log Files\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"app.log - Application log\n")
            f.write(f"error.log - Error log\n")
    
    main_logger.info("Logging system initialized")
    return main_logger


# Module-level convenience method
logger = get_logger("pyvizast")