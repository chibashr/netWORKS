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
        
    def update_configuration(self, level="INFO", diagnose=True, backtrace=True):
        """Update logging configuration at runtime
        
        Args:
            level (str): The logging level to set (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            diagnose (bool): Whether to enable diagnostic mode for better error tracing
            backtrace (bool): Whether to enable backtraces for error logs
        """
        # Convert string level to uppercase to ensure consistent format
        level = level.upper() if isinstance(level, str) else level
        
        # Validate level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level not in valid_levels:
            logger.warning(f"Invalid log level {level}, defaulting to INFO")
            level = "INFO"
            
        logger.info(f"Updating logging configuration: level={level}, diagnose={diagnose}, backtrace={backtrace}")
        
        # Remove existing handlers and recreate them with new settings
        # Note: We can't easily update existing handlers with loguru, so we recreate them
        
        # Keep track of existing handlers
        existing_handlers = logger._core.handlers.copy()
        console_handler = None
        file_handlers = []
        
        # Find console and file handlers
        for handler_id, handler in existing_handlers.items():
            if hasattr(handler, '_sink') and handler._sink == sys.stderr:
                console_handler = handler_id
            elif hasattr(handler, '_sink') and hasattr(handler._sink, 'name'):
                file_handlers.append(handler_id)
        
        # Update console handler if it exists
        if console_handler is not None:
            logger.remove(console_handler)
            logger.add(
                sys.stderr,
                format=existing_handlers[console_handler]._format,
                level=level,
                colorize=True,
                backtrace=backtrace,
                diagnose=diagnose
            )
        
        # Update file handlers if they exist
        for handler_id in file_handlers:
            handler = existing_handlers[handler_id]
            if hasattr(handler._sink, 'name'):
                file_path = handler._sink.name
                logger.remove(handler_id)
                logger.add(
                    file_path,
                    format=handler._format,
                    level=level,
                    rotation=handler._rotation,
                    retention=handler._retention,
                    compression=handler._compression,
                    backtrace=backtrace,
                    diagnose=diagnose
                )
        
        logger.info(f"Logging configuration updated: level={level}, diagnose={diagnose}, backtrace={backtrace}")
        
    def set_level(self, level):
        """Set the logging level
        
        Args:
            level (str): The logging level to set (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.update_configuration(level=level) 