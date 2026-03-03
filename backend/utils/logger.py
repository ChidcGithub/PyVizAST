"""
日志配置模块
提供统一的日志配置，将日志保存到 logs 文件夹
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


# 日志目录
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
    获取配置好的日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_to_file: 是否记录到文件
        log_to_console: 是否输出到控制台
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的日志文件数量
    
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 详细的错误日志格式（包含文件名和行号）
    error_formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    if log_to_file:
        # 普通日志文件
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
        
        # 错误日志文件（单独记录 ERROR 及以上级别）
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
    记录异常的详细信息
    
    Args:
        logger: 日志记录器
        exc: 异常对象
        context: 上下文信息
    """
    import traceback
    
    context_str = f" [{context}]" if context else ""
    logger.error(
        f"异常发生{context_str}: {type(exc).__name__}: {str(exc)}\n"
        f"堆栈跟踪:\n{traceback.format_exc()}"
    )


def get_request_logger() -> logging.Logger:
    """获取请求日志记录器"""
    return get_logger("pyvizast.request")


def get_error_logger() -> logging.Logger:
    """获取错误日志记录器"""
    return get_logger("pyvizast.error", level=logging.ERROR)


def get_access_logger() -> logging.Logger:
    """获取访问日志记录器"""
    return get_logger("pyvizast.access")


class ContextFilter(logging.Filter):
    """
    日志上下文过滤器
    可以为日志添加额外的上下文信息
    """
    
    def __init__(self, context: str = ""):
        super().__init__()
        self.context = context
    
    def filter(self, record):
        record.context = self.context
        return True


def init_logging(level: int = logging.INFO):
    """
    初始化全局日志配置
    
    Args:
        level: 日志级别
    """
    # 创建主日志记录器
    main_logger = get_logger("pyvizast", level=level)
    
    # 创建日志索引文件
    index_file = LOG_DIR / "index.txt"
    if not index_file.exists():
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(f"PyVizAST 日志文件\n")
            f.write(f"创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"app.log - 应用日志\n")
            f.write(f"error.log - 错误日志\n")
    
    main_logger.info("日志系统初始化完成")
    return main_logger


# 模块级别的便捷方法
logger = get_logger("pyvizast")
