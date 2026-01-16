"""
Loop Utilities Module
=====================
Helper functions for the Ralph Wiggum Loop.
"""

import logging
import os
import sys

def setup_logging(log_file: str) -> logging.Logger:
    """
    Configure structured logging for the application.
    
    Args:
        log_file: Path to the log file.
        
    Returns:
        Configured logger instance.
    """
    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = logging.getLogger("ralphs_loop")
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # File Handler (Detailed errors and infos)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console Handler (User friendly output)
    # We keep console output clean (print-like) for INFO, but detailed for ERROR
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s') # Minimal format for console
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
