#!/usr/bin/env python3
"""
Log Viewer Plugin for netWORKS
"""

import os
import sys
import glob
import logging
import datetime
import traceback
from typing import List, Dict, Optional, Union, Any

from PySide6.QtCore import QTimer, QObject, Signal, Qt, QThread
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMessageBox, QToolButton, QFrame

# Add the plugin directory to the Python path to allow imports from the ui directory
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(PLUGIN_DIR, "ui")

# Ensure the import uses the absolute path to avoid naming conflicts
sys.path.insert(0, os.path.dirname(PLUGIN_DIR))  # Add parent of plugin dir to sys.path

# Rename the directory in sys.modules to handle hyphenated directory name
if not 'plugins.log_viewer' in sys.modules:
    sys.modules['plugins.log_viewer'] = __import__('plugins').__dict__.setdefault('log_viewer', type('module', (), {}))
if not 'plugins.log_viewer.ui' in sys.modules:
    sys.modules['plugins.log_viewer.ui'] = __import__('plugins.log_viewer').__dict__.setdefault('ui', type('module', (), {}))

# Set up logging for this module
logger = logging.getLogger(__name__)

def init_logging():
    """Initialize logging if not already set up."""
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        # Add a console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        logger.debug("Log viewer plugin logging initialized")

# Initialize logging
init_logging()

class LogViewerPlugin(QObject):
    """Plugin for viewing, filtering and downloading log files."""
    
    error_found = Signal(str, str)  # Signal for new errors (level, message)
    
    def __init__(self, plugin_api=None):
        """Initialize the log viewer plugin.
        
        Args:
            plugin_api: The plugin API instance
        """
        super().__init__()
        logger.debug("Initializing Log Viewer Plugin")
        
        self.api = plugin_api
        self.name = "Log Viewer"
        self.version = "1.0.0"
        self.description = "View, filter and download application logs"
        self.author = "netWORKS"
        self.ui = None
        self.log_viewer_dialog = None
        self.last_error_check = datetime.datetime.now()
        self.error_check_timer = None
        
        # Register a callback for when the main window is ready - important for UI setup
        if self.api and hasattr(self.api, 'on_main_window_ready'):
            self.api.on_main_window_ready(self.on_main_window_ready)
            logger.debug("Registered main_window_ready callback")
        
    def init_plugin(self):
        """Initialize the plugin."""
        try:
            logger.debug("Initializing plugin")
            
            # Create log file
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin_loaded.log"), "a") as f:
                f.write(f"{datetime.datetime.now()} - Plugin initialization called\n")
            
            logger.debug("About to import dialog module")
            
            # Use direct module loading instead of import
            import importlib.util
            
            # Get absolute path to the log_dialog.py file
            log_dialog_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "log_dialog.py")
            
            # Load the module from the file path
            spec = importlib.util.spec_from_file_location("log_dialog", log_dialog_path)
            log_dialog_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(log_dialog_module)
            
            # Get the LogViewerDialog class from the loaded module
            LogViewerDialog = log_dialog_module.LogViewerDialog
            self._log_dialog_class = LogViewerDialog
            
            logger.debug("Dialog module imported successfully")
            
            # Set up error checking timer
            logger.debug("Setting up error checking")
            self.setup_error_checking()
            logger.debug("Error checking setup complete")
            
            # Log initialization success
            logger.debug("Plugin initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize plugin: {str(e)}", exc_info=True, extra={'context': 'Plugin initialization failed'})
            
            # Write error to plugin log file
            try:
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin_error.log"), "a") as f:
                    f.write(f"{datetime.datetime.now()} - Plugin initialization failed: {str(e)}\n")
                    f.write(traceback.format_exc())
                    f.write("\n\n")
            except:
                pass
                
            return False
            
    def on_main_window_ready(self):
        """Called when the main window is ready."""
        try:
            logger.debug("Main window is now ready, initializing UI components")
            self.init_ui()
        except Exception as e:
            logger.error(f"Error in on_main_window_ready: {str(e)}", exc_info=True)
    
    def init_ui(self):
        """Initialize the UI components."""
        try:
            logger.debug("Initializing UI components")
            
            if not self.api or not hasattr(self.api, 'main_window'):
                logger.error("Plugin API or main window not available")
                return False
            
            # Get main window
            main_window = self.api.main_window
            logger.debug(f"Got main window: {main_window}")
            
            # Create action for the log viewer button
            log_action = QAction("View Logs", main_window)
            log_action.setIcon(QIcon.fromTheme("document-text"))  # Set an appropriate icon
            log_action.setToolTip("View application log files")
            
            # Use lambda to add extra debug output before calling our handler
            log_action.triggered.connect(lambda checked: self._debug_click_handler(checked))
            logger.debug(f"Created log_action and connected to trigger handler: {log_action}")
            
            # Focus on adding to Help tab as requested
            success = False
            
            # Try to add to Help tab in the diagnostics section
            if hasattr(main_window, 'add_toolbar_widget'):
                logger.debug("Using add_toolbar_widget method for diagnostics section")
                help_result = main_window.add_toolbar_widget(log_action, "Help", "Diagnostics")
                logger.debug(f"Added button to Help tab Diagnostics section via add_toolbar_widget, result: {help_result}")
                success = help_result
            
            # If add_toolbar_widget failed or doesn't exist, try direct access to help group
            if not success and hasattr(main_window, 'help_group'):
                logger.debug(f"Found help_group in main window: {main_window.help_group}")
                
                # Look for a diagnostics section in the help group
                diagnostics_section = None
                
                # Try to find a section with "Diagnostics" in its name or object name
                if hasattr(main_window.help_group, 'findChild'):
                    diagnostics_section = main_window.help_group.findChild(QFrame, "diagnostics_section")
                    if not diagnostics_section:
                        # Just use the help group itself
                        diagnostics_section = main_window.help_group
                else:
                    diagnostics_section = main_window.help_group
                
                logger.debug(f"Using diagnostics section: {diagnostics_section}")
                
                # Create button using this action
                help_button = QToolButton()
                help_button.setDefaultAction(log_action)
                help_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                help_button.setObjectName("log_viewer_help_button")  # Set object name for debugging
                logger.debug(f"Created help_button: {help_button}")
                
                # Add the button to the diagnostics section
                if hasattr(diagnostics_section, 'layout') and diagnostics_section.layout():
                    diagnostics_section.layout().addWidget(help_button)
                    logger.debug(f"Added button to diagnostics section layout: {diagnostics_section.layout()}")
                    success = True
                else:
                    logger.error(f"Diagnostics section has no layout: {diagnostics_section}")
            
            if not success:
                logger.debug("No suitable diagnostics section found, trying add_toolbar_widget with default settings")
                if hasattr(main_window, 'add_toolbar_widget'):
                    help_result = main_window.add_toolbar_widget(log_action, "Help", "Help & Support")
                    logger.debug(f"Added button to Help tab via add_toolbar_widget, result: {help_result}")
                    success = help_result
            
            # Add to menu if available as a fallback
            menu_added = False
            if hasattr(main_window, 'menuHelp'):
                logger.debug(f"Found menuHelp in main window: {main_window.menuHelp}")
                menu_action = QAction("View Logs", main_window)
                menu_action.triggered.connect(lambda checked: self._debug_click_handler(checked))
                main_window.menuHelp.addAction(menu_action)
                logger.debug("Added action to Help menu")
                menu_added = True
            elif hasattr(main_window, 'menus') and 'Help' in main_window.menus:
                logger.debug(f"Found Help in main window menus dictionary: {main_window.menus['Help']}")
                menu_action = QAction("View Logs", main_window)
                menu_action.triggered.connect(lambda checked: self._debug_click_handler(checked))
                main_window.menus['Help'].addAction(menu_action)
                logger.debug("Added action to Help menu via menus dictionary")
                menu_added = True
            else:
                logger.warning("Could not find Help menu to add action")
            
            # If no toolbar button was added but menu was, we'll count that as success
            success = success or menu_added
            
            if not success:
                logger.warning("Could not add button to any toolbar or menu")
            
            logger.debug("UI components initialized")
            return success
            
        except Exception as e:
            logger.error(f"Failed to initialize UI: {str(e)}", exc_info=True, extra={'context': 'UI initialization failed'})
            return False
            
    def _debug_click_handler(self, checked):
        """Debug wrapper for button click events."""
        logger.debug(f"BUTTON CLICKED! checked={checked}")
        logger.debug(f"Current thread: {QThread.currentThread()}")
        logger.debug(f"Main window available: {hasattr(self.api, 'main_window') and self.api.main_window is not None}")
        self.open_log_viewer()
        
    def open_log_viewer(self):
        """Open the log viewer dialog."""
        try:
            logger.debug("⭐ Opening log viewer - click handler executed ⭐")
            
            # Ensure we have a main window to parent the dialog
            if not self.api or not hasattr(self.api, 'main_window') or not self.api.main_window:
                logger.error("Cannot show dialog: Main window not available")
                QMessageBox.critical(
                    None,
                    "Error",
                    "Cannot open log viewer: Application main window not available."
                )
                return
                
            # Get absolute path to the log_dialog.py file if not already loaded
            if not hasattr(self, '_log_dialog_class'):
                logger.debug("Loading dialog class for the first time")
                import importlib.util
                log_dialog_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "log_dialog.py")
                logger.debug(f"Dialog path: {log_dialog_path}")
                
                spec = importlib.util.spec_from_file_location("log_dialog", log_dialog_path)
                log_dialog_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(log_dialog_module)
                self._log_dialog_class = log_dialog_module.LogViewerDialog
                logger.debug(f"Dialog class loaded: {self._log_dialog_class}")
            
            # Create dialog if it doesn't exist
            if not self.log_viewer_dialog:
                logger.debug("Creating new dialog instance")
                self.log_viewer_dialog = self._log_dialog_class(self)
            else:
                logger.debug("Reusing existing dialog instance")
            
            # Show dialog (make sure it's modal)
            logger.debug("Showing dialog...")
            # First make sure it's properly parented to the main window
            self.log_viewer_dialog.setParent(self.api.main_window, Qt.Dialog)
            
            # Try both exec and exec_ (for different PySide6 versions)
            try:
                logger.debug("Executing dialog with exec()")
                result = self.log_viewer_dialog.exec()
                logger.debug(f"Dialog execution result: {result}")
            except AttributeError:
                logger.debug("Executing dialog with exec_()")
                result = self.log_viewer_dialog.exec_()
                logger.debug(f"Dialog execution result: {result}")
                
        except Exception as e:
            logger.error(f"Failed to open log viewer: {str(e)}", exc_info=True, extra={'context': 'Opening log viewer failed'})
            QMessageBox.critical(
                self.api.main_window if self.api and hasattr(self.api, 'main_window') else None,
                "Error",
                f"Failed to open log viewer: {str(e)}"
            )
    
    def get_logs(self) -> List[Dict[str, str]]:
        """Get logs from the log directory.
        
        Returns:
            List of log entries as dictionaries
        """
        try:
            logger.debug("Retrieving logs")
            
            logs = []
            
            # Try multiple potential log directory locations
            log_dirs = [
                # Standard logs directory in the project root
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "logs"),
                
                # Legacy path (three levels up)
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs"),
                
                # Absolute paths that might be used in different environments
                "/logs",
                os.path.join(os.path.dirname(sys.executable), "logs"),
                
                # Current working directory logs
                os.path.join(os.getcwd(), "logs")
            ]
            
            # Select the first existing logs directory
            log_dir = None
            for potential_dir in log_dirs:
                if os.path.exists(potential_dir) and os.path.isdir(potential_dir):
                    log_dir = potential_dir
                    logger.debug(f"Found logs directory: {log_dir}")
                    break
            
            if not log_dir:
                logger.warning(f"No valid logs directory found. Tried: {', '.join(log_dirs)}")
                return logs
            
            # Get all log files
            log_files = glob.glob(os.path.join(log_dir, "*.log"))
            
            # Add most recent first
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            if not log_files:
                logger.warning(f"No log files found in directory: {log_dir}")
                return logs
                
            logger.debug(f"Found {len(log_files)} log files in {log_dir}")
            
            # Parse log files
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        for line in f:
                            try:
                                # Parse log line
                                parts = line.strip().split(' - ', 3)
                                
                                if len(parts) >= 4:
                                    timestamp, source, level, message = parts
                                    
                                    log_entry = {
                                        "timestamp": timestamp,
                                        "source": source,
                                        "level": level,
                                        "message": message,
                                        "file": os.path.basename(log_file)
                                    }
                                    
                                    # Check for multi-line entries (exceptions)
                                    if "Traceback" in message:
                                        exception_lines = []
                                        line = next(f, None)
                                        
                                        # Collect exception lines
                                        while line and not (' - INFO - ' in line or ' - WARNING - ' in line or 
                                                          ' - ERROR - ' in line or ' - DEBUG - ' in line or
                                                          ' - CRITICAL - ' in line):
                                            exception_lines.append(line.strip())
                                            line = next(f, None)
                                            if not line:
                                                break
                                        
                                        log_entry["exception"] = "\n".join(exception_lines)
                                    
                                    logs.append(log_entry)
                                    
                            except Exception as line_error:
                                logger.warning(f"Error parsing log line: {str(line_error)}")
                                continue
                                
                except Exception as file_error:
                    logger.warning(f"Error reading log file {log_file}: {str(file_error)}")
                    continue
            
            logger.debug(f"Retrieved {len(logs)} log entries")
            return logs
            
        except Exception as e:
            logger.error(f"Error retrieving logs: {str(e)}", exc_info=True, extra={'context': 'Retrieving logs failed'})
            return []
    
    def download_logs(self, logs: List[Dict[str, str]], file_path: str) -> bool:
        """Download logs to a file.
        
        Args:
            logs: List of log entries to download
            file_path: Path to save logs to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug(f"Downloading {len(logs)} logs to {file_path}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                for log in logs:
                    # Write log entry
                    f.write(f"{log.get('timestamp', '')} - {log.get('source', '')} - "
                            f"{log.get('level', '')} - {log.get('message', '')}\n")
                    
                    # Write exception if exists
                    if log.get("exception"):
                        f.write(f"{log.get('exception')}\n\n")
            
            logger.debug("Logs downloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading logs: {str(e)}", exc_info=True, extra={'context': 'Downloading logs failed'})
            return False
    
    def setup_error_checking(self):
        """Set up periodic error checking."""
        try:
            logger.debug("Setting up error checking")
            
            # Create timer to check for errors every 60 seconds
            self.error_check_timer = QTimer()
            self.error_check_timer.timeout.connect(self.check_for_errors)
            self.error_check_timer.start(60000)  # 60 seconds
            
            logger.debug("Error checking timer started")
            
        except Exception as e:
            logger.error(f"Error setting up error checking: {str(e)}", exc_info=True, extra={'context': 'Setting up error checking failed'})
    
    def check_for_errors(self):
        """Check for recent error logs."""
        try:
            logger.debug("Checking for recent errors")
            
            # Get current time
            now = datetime.datetime.now()
            
            # Get logs
            logs = self.get_logs()
            
            # Format for parsing timestamps
            time_formats = [
                "%Y-%m-%d %H:%M:%S",  # Standard format
                "%Y-%m-%d %H:%M:%S,%f",  # With milliseconds
                "%Y/%m/%d %H:%M:%S"  # Alternative format sometimes used
            ]
            
            # Check for errors since last check
            for log in logs:
                try:
                    # Try to parse timestamp with different formats
                    timestamp_str = log.get("timestamp", "").split(',')[0]
                    timestamp = None
                    
                    # Try each format until one works
                    for format_str in time_formats:
                        try:
                            timestamp = datetime.datetime.strptime(timestamp_str, format_str)
                            break
                        except ValueError:
                            continue
                    
                    # Skip if no valid timestamp
                    if not timestamp:
                        logger.warning(f"Could not parse timestamp: {log.get('timestamp', '')}")
                        continue
                    
                    # Check if error is newer than last check
                    if timestamp > self.last_error_check and log.get("level") in ["ERROR", "CRITICAL"]:
                        # Emit signal with error details
                        self.error_found.emit(log.get("level"), log.get("message"))
                        
                except Exception as e:
                    logger.warning(f"Error processing log entry: {str(e)}")
                    continue
            
            # Update last check time
            self.last_error_check = now
            
        except Exception as e:
            logger.error(f"Error checking for errors: {str(e)}", exc_info=True, extra={'context': 'Checking for recent errors failed'})

# Add the required init_plugin function for plugin framework compatibility
def init_plugin(plugin_api):
    """Required entry point for the plugin framework.
    
    Args:
        plugin_api: The plugin API instance
        
    Returns:
        The plugin instance
    """
    try:
        logger.debug("Plugin framework calling init_plugin")
        
        plugin = LogViewerPlugin(plugin_api)
        if plugin.init_plugin():
            return plugin
        else:
            logger.error("Failed to initialize plugin", exc_info=True, extra={'context': 'Plugin entry point failed'})
            return None
            
    except Exception as e:
        logger.error(f"Error in plugin entry point: {str(e)}", exc_info=True, extra={'context': 'Plugin entry point failed'})
        return None 