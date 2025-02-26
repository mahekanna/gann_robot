# core/utils/logger.py

import logging
import os
from datetime import datetime

def setup_logger(name: str, log_level: str = 'INFO', log_dir: str = 'logs'):
    """
    Create a logger with file and console handlers
    
    Args:
        name (str): Name of the logger
        log_level (str, optional): Logging level. Defaults to 'INFO'.
        log_dir (str, optional): Directory to store log files. Defaults to 'logs'.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Set logging level
    log_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create file handler
    log_file = os.path.join(log_dir, f'{name}_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Remove existing handlers to prevent duplicate logs
    logger.handlers.clear()
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Example usage
def get_logger(name: str):
    """Convenience function to get a logger"""
    return setup_logger(name)