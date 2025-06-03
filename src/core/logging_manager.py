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

# Windows-specific imports for file locking handling
if platform.system().lower() == "windows":
    import threading
    import atexit

class LoggingManager:
    """Manage application logging with enhanced capabilities"""
    
    def __init__(self, app_version=None):
        """Initialize the logging manager
        
        Args:
            app_version (str, optional): The application version for logging. Defaults to None.
        """
        self.app_version = app_version
        
        # Determine the correct base directory for the application
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable
            base_dir = Path(sys.executable).parent
        else:
            # Running as Python script
            base_dir = Path(__file__).parent.parent.parent
        
        self.logs_dir = base_dir / "logs"
        self.recent_log_path = self.logs_dir / "recent_logs.log"
        self.init_time = datetime.now()
        self.session_id = int(time.time())
        
        # Windows-specific file rotation management
        self._is_windows = platform.system().lower() == "windows"
        self._file_locks = set()  # Track file locks for cleanup
        self._cleanup_registered = False
        
        # Create logs directory if it doesn't exist
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # If we can't create the logs directory, fall back to a temp directory
            import tempfile
            self.logs_dir = Path(tempfile.gettempdir()) / "NetWORKS_logs"
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            self.recent_log_path = self.logs_dir / "recent_logs.log"
            print(f"Warning: Could not create logs directory, using temp directory: {self.logs_dir}")
        
        # Remove all existing loguru sinks
        logger.remove()
        
        # Initialize logging
        self._setup_logging()
        
        # Register cleanup on Windows
        if self._is_windows and not self._cleanup_registered:
            atexit.register(self._cleanup_file_locks)
            self._cleanup_registered = True

    def _cleanup_file_locks(self):
        """Clean up file locks on Windows when application exits"""
        if self._is_windows and self._file_locks:
            try:
                # Small delay to allow loguru to finish any pending operations
                time.sleep(0.1)
                # Remove all loguru handlers to release file locks
                logger.remove()
                time.sleep(0.1)  # Additional delay for Windows file system
            except Exception:
                pass  # Ignore cleanup errors on exit

    def _windows_safe_rotation_handler(self, message, file_path):
        """
        Windows-safe rotation handler that prevents file locking issues
        
        Args:
            message: The log message to write
            file_path: Path to the log file
        """
        try:
            # For Windows, we'll use time-based rotation instead of size-based
            # This reduces the likelihood of file locking conflicts
            file_path = Path(file_path)
            if file_path.exists():
                # Check if file is older than 1 hour and larger than 512KB
                file_stat = file_path.stat()
                file_age = time.time() - file_stat.st_mtime
                file_size = file_stat.st_size
                
                if file_age > 3600 and file_size > 524288:  # 1 hour and 512KB
                    # Create a new timestamped file instead of rotating
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    session_suffix = f"_{self.session_id}"
                    new_name = file_path.stem + f"_{timestamp}{session_suffix}" + file_path.suffix
                    new_path = file_path.parent / new_name
                    
                    # Use session-specific naming to avoid conflicts
                    counter = 1
                    while new_path.exists():
                        new_name = file_path.stem + f"_{timestamp}{session_suffix}_{counter}" + file_path.suffix
                        new_path = file_path.parent / new_name
                        counter += 1
                    
                    # Instead of renaming, just start using the new file
                    # Let the old file be cleaned up later by retention policy
                    return str(new_path)
            
            return str(file_path)
        except Exception:
            # If anything fails, just use the original path
            return str(file_path)

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
        try:
            logger.add(
                sys.stderr,
                format=base_format,
                level="INFO",
                colorize=True,
                backtrace=True,
                diagnose=True,
                enqueue=True  # Fix for Windows threading issues
            )
        except Exception as e:
            print(f"Warning: Could not add console logger: {e}")
        
        # Recent logs file handler (Windows-safe approach)
        try:
            if self.recent_log_path and self.recent_log_path.parent.exists():
                if self._is_windows:
                    # On Windows, use session-specific naming to avoid file locking
                    # This prevents rotation conflicts entirely
                    timestamp = self.init_time.strftime('%Y%m%d_%H%M%S')
                    recent_log_name = f"recent_logs_{timestamp}_{self.session_id}.log"
                    recent_log_path = self.logs_dir / recent_log_name
                    
                    logger.add(
                        str(recent_log_path),
                        format=detailed_format,
                        level="DEBUG",
                        # No rotation on Windows to prevent file locking issues
                        backtrace=True,
                        diagnose=True,
                        enqueue=True,
                        catch=True
                    )
                    
                    # Track this file for cleanup
                    self._file_locks.add(str(recent_log_path))
                    
                    logger.debug(f"Windows: Using session-specific log file: {recent_log_name}")
                else:
                    # On non-Windows systems, use normal rotation
                    logger.add(
                        str(self.recent_log_path),
                        format=detailed_format,
                        level="DEBUG",
                        rotation="5 MB",
                        retention=3,
                        compression="zip",
                        backtrace=True,
                        diagnose=True,
                        enqueue=True,
                        catch=True
                    )
        except Exception as e:
            print(f"Warning: Could not add recent logs file handler: {e}")
            # Try fallback without any special features
            try:
                fallback_log = self.logs_dir / f"fallback_logs_{self.session_id}.log"
                logger.add(
                    str(fallback_log),
                    format=detailed_format,
                    level="DEBUG",
                    enqueue=True,
                    catch=True
                )
                print(f"Using fallback log file: {fallback_log}")
                if self._is_windows:
                    self._file_locks.add(str(fallback_log))
            except Exception as fallback_error:
                print(f"Warning: Fallback logging also failed: {fallback_error}")
        
        # Session-specific log file
        try:
            session_log_file = self.logs_dir / f"networks_{self.init_time.strftime('%Y%m%d_%H%M%S')}_{self.session_id}.log"
            if session_log_file and session_log_file.parent.exists():
                if self._is_windows:
                    # On Windows, use conservative settings to avoid file locking
                    logger.add(
                        str(session_log_file),
                        format=detailed_format,
                        level="DEBUG",
                        # Use time-based rotation instead of size-based to reduce conflicts
                        rotation="1 day",
                        retention="1 week",
                        # No compression on Windows to reduce file operations
                        backtrace=True,
                        diagnose=True,
                        enqueue=True,
                        catch=True
                    )
                    self._file_locks.add(str(session_log_file))
                else:
                    # On non-Windows systems, use more aggressive settings
                    logger.add(
                        str(session_log_file),
                        format=detailed_format,
                        level="DEBUG",
                        rotation="10 MB",
                        retention="1 week",
                        compression="zip",
                        backtrace=True,
                        diagnose=True,
                        enqueue=True,
                        catch=True
                    )
        except Exception as e:
            print(f"Warning: Could not add session log file handler: {e}")
        
        # Log startup information
        try:
            logger.info(f"Logging initialized for session {self.session_id}")
            logger.debug(f"Application Version: {self.app_version or 'Unknown'}")
            logger.debug(f"System: {platform.system()} {platform.release()} {platform.version()}")
            logger.debug(f"Python: {platform.python_version()}")
            logger.debug(f"Machine: {platform.machine()}")
            logger.debug(f"Log files directory: {self.logs_dir.absolute()}")
            if self._is_windows:
                logger.debug("Windows-specific logging configuration applied - using session-based file naming to prevent rotation conflicts")
            if 'session_log_file' in locals():
                logger.debug(f"Session log file: {session_log_file.name}")
        except Exception as e:
            print(f"Warning: Could not log startup information: {e}")
        
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
        
    def shutdown(self):
        """Properly shutdown logging and release file handles"""
        try:
            logger.info("Shutting down logging system")
            # Remove all handlers to release file locks
            logger.remove()
            # Clear file lock tracking
            self._file_locks.clear()
            
            if self._is_windows:
                # Add a small delay for Windows file system
                time.sleep(0.1)
                
            logger.info("Logging system shutdown completed")
        except Exception as e:
            print(f"Warning: Error during logging shutdown: {e}")
            
    def get_log_files_info(self):
        """Get information about current log files
        
        Returns:
            dict: Information about log files and their status
        """
        info = {
            "logs_directory": str(self.logs_dir.absolute()),
            "session_id": self.session_id,
            "is_windows": self._is_windows,
            "tracked_files": list(self._file_locks),
            "log_files": []
        }
        
        try:
            # List all log files in the logs directory
            if self.logs_dir.exists():
                for log_file in self.logs_dir.glob("*.log"):
                    try:
                        stat = log_file.stat()
                        info["log_files"].append({
                            "name": log_file.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "tracked": str(log_file) in self._file_locks
                        })
                    except Exception:
                        info["log_files"].append({
                            "name": log_file.name,
                            "size": "unknown",
                            "modified": "unknown",
                            "tracked": str(log_file) in self._file_locks
                        })
        except Exception as e:
            info["error"] = str(e)
            
        return info 