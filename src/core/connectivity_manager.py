#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Connectivity manager for NetWORKS
Monitors internet connectivity and provides status to the application
"""

import urllib.request
import urllib.error
from loguru import logger
from PySide6.QtCore import QObject, Signal, QTimer
import functools

class ConnectivityManager(QObject):
    """Manager for monitoring internet connectivity status"""
    
    # Signals
    connectivity_changed = Signal(bool)  # online status changed
    
    def __init__(self, config=None, app=None):
        """Initialize the connectivity manager
        
        Args:
            config: Config instance for accessing settings
            app: Application instance for getting version
        """
        super().__init__()
        self.config = config
        self.app = app
        self._is_online = False
        self._last_check_result = None
        
        # Timer for periodic connectivity checks
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._periodic_check)
        
        # Default check interval (30 seconds)
        self.check_interval = 30000  # milliseconds
        
        # Configure connectivity checking
        self._setup_connectivity_checking()
        
        # Perform initial check
        self._check_connectivity_internal()
        
    def _setup_connectivity_checking(self):
        """Setup connectivity checking based on configuration"""
        if self.config:
            # Get check interval from config (default 30 seconds)
            self.check_interval = self.config.get("connectivity.check_interval", 30) * 1000
            
            # Start periodic checking if enabled
            if self.config.get("connectivity.auto_check", True):
                self.start_monitoring()
    
    def start_monitoring(self):
        """Start automatic connectivity monitoring"""
        if not self.check_timer.isActive():
            self.check_timer.start(self.check_interval)
            logger.debug(f"Started connectivity monitoring (interval: {self.check_interval/1000}s)")
    
    def stop_monitoring(self):
        """Stop automatic connectivity monitoring"""
        if self.check_timer.isActive():
            self.check_timer.stop()
            logger.debug("Stopped connectivity monitoring")
    
    def check_connectivity(self):
        """Check internet connectivity immediately
        
        Returns:
            bool: True if online, False if offline
        """
        return self._check_connectivity_internal()
    
    def is_online(self):
        """Get current connectivity status
        
        Returns:
            bool: True if online, False if offline
        """
        return self._is_online
    
    def _periodic_check(self):
        """Periodic connectivity check (called by timer)"""
        self._check_connectivity_internal()
    
    def _check_connectivity_internal(self):
        """Internal method to check connectivity
        
        Returns:
            bool: True if online, False if offline
        """
        try:
            # Try multiple reliable endpoints
            test_urls = [
                "https://api.github.com",
                "https://www.google.com",
                "https://1.1.1.1"  # Cloudflare DNS
            ]
            
            for url in test_urls:
                try:
                    req = urllib.request.Request(
                        url,
                        headers={
                            'User-Agent': f'NetWORKS/{self.app.get_version() if self.app else "1.0.0"}',
                            'Cache-Control': 'no-cache'
                        }
                    )
                    
                    with urllib.request.urlopen(req, timeout=3) as response:
                        if response.getcode() in [200, 204, 301, 302]:
                            # We got a valid response
                            was_online = self._is_online
                            self._is_online = True
                            self._last_check_result = True
                            
                            # Emit signal if status changed
                            if was_online != self._is_online:
                                logger.info("Internet connectivity restored")
                                self.connectivity_changed.emit(True)
                            
                            return True
                            
                except (urllib.error.URLError, urllib.error.HTTPError, OSError):
                    # Try next URL
                    continue
            
            # All URLs failed
            was_online = self._is_online
            self._is_online = False
            self._last_check_result = False
            
            # Emit signal if status changed
            if was_online != self._is_online:
                logger.warning("Internet connectivity lost")
                self.connectivity_changed.emit(False)
            
            return False
            
        except Exception as e:
            logger.debug(f"Connectivity check error: {e}")
            was_online = self._is_online
            self._is_online = False
            self._last_check_result = False
            
            # Emit signal if status changed
            if was_online != self._is_online:
                logger.warning("Internet connectivity lost due to error")
                self.connectivity_changed.emit(False)
            
            return False
    
    def get_status_text(self):
        """Get human-readable connectivity status
        
        Returns:
            str: Status text for display
        """
        if self._is_online:
            return "Online"
        else:
            return "Offline"
    
    def get_detailed_status(self):
        """Get detailed connectivity status information
        
        Returns:
            dict: Detailed status information
        """
        return {
            "online": self._is_online,
            "last_check": self._last_check_result,
            "monitoring": self.check_timer.isActive(),
            "check_interval": self.check_interval / 1000  # convert to seconds
        }

def require_connectivity(show_warning=True):
    """Decorator to check connectivity before executing a function
    
    Args:
        show_warning: Whether to log a warning if offline
        
    Returns:
        The decorated function or None if offline
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get connectivity manager from the first argument (usually self)
            connectivity_manager = None
            if args and hasattr(args[0], 'connectivity_manager'):
                connectivity_manager = args[0].connectivity_manager
            elif args and hasattr(args[0], 'app') and hasattr(args[0].app, 'connectivity_manager'):
                connectivity_manager = args[0].app.connectivity_manager
            
            # Check connectivity
            if connectivity_manager and not connectivity_manager.is_online():
                if show_warning:
                    logger.warning(f"Cannot execute {func.__name__}: No internet connectivity")
                return None
            
            # Execute the function
            return func(*args, **kwargs)
        return wrapper
    return decorator


def check_connectivity_before_request(connectivity_manager=None):
    """Check connectivity before making a network request
    
    Args:
        connectivity_manager: ConnectivityManager instance, or None to skip check
        
    Returns:
        bool: True if online or no manager provided, False if offline
    """
    if connectivity_manager and not connectivity_manager.is_online():
        logger.warning("Network request blocked: No internet connectivity")
        return False
    return True 