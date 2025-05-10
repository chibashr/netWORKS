#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging manager for NetWORKS
"""

import os
import sys
import time
import platform
from datetime import datetime
from pathlib import Path
from loguru import logger

class LoggingManager:
    """Manage application logging with enhanced capabilities"""
    
    def __init__(self, app_version=None):
        """Initialize the logging manager
        
        Args:
            app_version (str, optional): The application version for logging. Defaults to None.
        """
        self.app_version = app_version
        self.logs_dir = Path("logs")
        self.recent_log_path = self.logs_dir / "recent_logs.log"
        self.init_time = datetime.now()
        self.session_id = int(time.time())
        
        # Create logs directory if it doesn't exist
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Remove all existing loguru sinks
        logger.remove()
        
        # Initialize logging
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging handlers with proper configuration"""
        # Define log format
        base_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        detailed_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "session:{extra[session_id]} | "
            "v{extra[app_version]} | "
            "{extra[system_info]} | "
            "<level>{message}</level>"
        )
        
        # Add stderr handler for console output
        logger.configure(
            extra={
                "session_id": self.session_id,
                "app_version": self.app_version or "?.?.?",
                "system_info": f"{platform.system()} {platform.release()}"
            }
        )
        
        # Console handler
        logger.add(
            sys.stderr,
            format=base_format,
            level="INFO",
            colorize=True,
            backtrace=True,
            diagnose=True
        )
        
        # Recent logs file handler (always keeps the recent logs)
        logger.add(
            self.recent_log_path,
            format=detailed_format,
            level="DEBUG",
            rotation="5 MB",
            retention=3,
            compression="zip",
            backtrace=True,
            diagnose=True
        )
        
        # Session-specific log file
        session_log_file = self.logs_dir / f"networks_{self.init_time.strftime('%Y%m%d_%H%M%S')}_{self.session_id}.log"
        logger.add(
            session_log_file,
            format=detailed_format,
            level="DEBUG",
            rotation="10 MB",
            retention="1 week",
            compression="zip",
            backtrace=True,
            diagnose=True
        )
        
        # Log startup information
        logger.info(f"Logging initialized for session {self.session_id}")
        logger.debug(f"Application Version: {self.app_version or 'Unknown'}")
        logger.debug(f"System: {platform.system()} {platform.release()} {platform.version()}")
        logger.debug(f"Python: {platform.python_version()}")
        logger.debug(f"Machine: {platform.machine()}")
        logger.debug(f"Log files directory: {self.logs_dir.absolute()}")
        logger.debug(f"Session log file: {session_log_file.name}")
        
    def get_logger(self):
        """Get the configured logger instance
        
        Returns:
            logger: The configured loguru logger
        """
        return logger
        
    def set_level(self, level):
        """Set the logging level
        
        Args:
            level (str): The logging level to set (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # Implementation would depend on how we want to change log levels at runtime
        # This is a placeholder for future functionality
        pass 