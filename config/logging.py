import os
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Generate log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"netWORKS_{timestamp}.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set to DEBUG for maximum verbosity
    
    # Create console handler with a specific format for better visibility
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Set console to DEBUG level
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # Create file handler with format matching what log-viewer expects
    # Format must be: timestamp - source - level - message
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers to the root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set up specific loggers
    setup_library_loggers()
    
    # Log startup message
    root_logger.info(f"Logging initialized. Log file: {log_file}")
    
    return root_logger

def setup_library_loggers():
    """Configure logging levels for third-party libraries."""
    # Silence overly verbose libraries
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    
    # Make certain libraries more verbose if needed
    logging.getLogger("PySide6").setLevel(logging.INFO)
    logging.getLogger("scapy").setLevel(logging.WARNING)

    # Create specific loggers for key components
    loggers = [
        "NetSCAN.UI",
        "NetSCAN.Plugin",
        "NetSCAN.Menu",
        "NetSCAN.Window"
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG) 