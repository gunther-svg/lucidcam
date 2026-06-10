"""
Logging configuration for LucidCam.
Provides structured logging to file and console with rotation support.
"""

import logging
import logging.handlers
from pathlib import Path
from config import config


def setup_logging():
    """Initialize logging with file and console handlers."""
    
    log_level = config.get('logging', 'level', 'INFO')
    log_file = config.get('logging', 'log_file', 'logs/lucidcam.log')
    max_file_size = config.get_int('logging', 'max_file_size', 10485760)  # 10MB default
    backup_count = config.get_int('logging', 'backup_count', 5)
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count
    )
    file_handler.setLevel(getattr(logging, log_level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Always show INFO+ on console
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Initialize logging
logger = setup_logging()
