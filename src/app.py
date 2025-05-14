#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main application class for NetWORKS
"""

import sys
import os
import json
from loguru import logger
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

from .config import Config
from .ui.splash_screen import SplashScreen
from .ui.main_window import MainWindow
from .core.plugin_manager import PluginManager
from .core.device_manager import DeviceManager
from .core import LoggingManager
from .core.crash_reporter import setup_global_exception_handler, show_crash_dialog


class Application(QApplication):
    """Main application class for NetWORKS"""

    def __init__(self, argv):
        """Initialize the application"""
        super().__init__(argv)
        
        # Load manifest
        self.manifest = self._load_manifest()
        
        # Initialize logging manager
        version = self.manifest.get("version", "0.1.0")
        self.logging_manager = LoggingManager(version)
        # Get the configured logger
        self.logger = self.logging_manager.get_logger()
        
        # Set up global exception handler
        setup_global_exception_handler()
        
        # Set application properties
        self.setApplicationName("NetWORKS")
        self.setApplicationVersion(self.manifest.get("version", "0.1.0"))
        self.setOrganizationName("NetWORKS")
        self.setOrganizationDomain("networks.app")
        
        # Force light mode by setting the style to Fusion
        self.setStyle("Fusion")
        
        # Apply light mode stylesheet
        light_stylesheet = """
        QMainWindow, QDialog, QDockWidget, QWidget {
            background-color: #f5f5f5;
            color: #333333;
        }
        QMenuBar, QMenu, QToolBar {
            background-color: #f5f5f5;
            color: #333333;
        }
        QMenu::item {
            padding: 5px 20px 5px 20px;
            border-radius: 3px;
            margin: 2px;
        }
        QMenu::item:selected {
            background-color: #4a90e2;
            color: white;
        }
        QMenu::item:disabled {
            color: #aaaaaa;
        }
        QMenu::icon {
            padding-left: 10px;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
            border-radius: 3px;
            margin: 1px;
        }
        QMenuBar::item:selected {
            background-color: #e0e0e0;
            color: #333333;
        }
        QMenuBar::item:pressed {
            background-color: #4a90e2;
            color: white;
        }
        QComboBox {
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 3px 18px 3px 3px;
            background-color: white;
            color: #333333;
            min-width: 6em;
        }
        QComboBox:hover {
            border-color: #4a90e2;
        }
        QComboBox:focus {
            border-color: #4a90e2;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 15px;
            border-left: 1px solid #cccccc;
        }
        QComboBox::down-arrow {
            width: 8px;
            height: 8px;
            image: url(down_arrow.png);
        }
        QComboBox QAbstractItemView {
            border: 1px solid #cccccc;
            background-color: white;
            selection-background-color: #4a90e2;
            selection-color: white;
        }
        QComboBox QAbstractItemView::item {
            min-height: 20px;
            padding: 3px;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #e7f0fd;
        }
        QStatusBar {
            background-color: #f0f0f0;
            color: #333333;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
            background-color: #f5f5f5;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #333333;
            padding: 5px 10px;
            border: 1px solid #cccccc;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #f5f5f5;
            border-bottom: 1px solid #f5f5f5;
        }
        QTabBar::tab:hover:!selected {
            background-color: #d0d0d0;
        }
        QTreeView, QTableView {
            background-color: white;
            alternate-background-color: #f7f7f7;
            color: #333333;
            border: 1px solid #cccccc;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            color: #333333;
            padding: 5px;
            border: 1px solid #cccccc;
        }
        QDockWidget {
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(undock.png);
        }
        QDockWidget::title {
            background-color: #e0e0e0;
            color: #333333;
            padding: 6px;
            font-weight: bold;
        }
        QDockWidget > QWidget {
            border-top: 1px solid #cccccc;
        }
        QDockWidget::close-button, QDockWidget::float-button {
            background-color: transparent;
            border: none;
            padding: 2px;
        }
        QDockWidget::close-button:hover, QDockWidget::float-button:hover {
            background-color: rgba(0, 0, 0, 0.1);
            border-radius: 3px;
        }
        QGroupBox {
            background-color: #f8f8f8;
            border: 1px solid #dddddd;
            border-radius: 4px;
            margin-top: 15px;
            padding-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
            background-color: #f8f8f8;
        }
        QLabel {
            color: #333333;
        }
        QScrollBar:vertical {
            background-color: #f0f0f0;
            width: 12px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #cccccc;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar:horizontal {
            background-color: #f0f0f0;
            height: 12px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background-color: #cccccc;
            min-width: 20px;
            border-radius: 6px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        QPushButton {
            background-color: #e0e0e0;
            border: 1px solid #cccccc;
            padding: 5px 10px;
            border-radius: 3px;
            color: #333333;
            min-width: 90px;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        QToolButton {
            background-color: #e0e0e0;
            border: 1px solid #cccccc;
            border-radius: 3px;
            color: #333333;
            min-width: 28px;
            min-height: 28px;
            padding: 3px;
        }
        QToolButton:hover {
            background-color: #d0d0d0;
        }
        QToolButton:pressed {
            background-color: #c0c0c0;
        }
        QToolButton[popupMode="1"] {
            padding-right: 18px;
        }
        QToolButton::menu-button {
            border: none;
            width: 16px;
        }
        QLineEdit {
            background-color: white;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 3px;
            border-radius: 2px;
        }
        """
        self.setStyleSheet(light_stylesheet)
        
        self.logger.info(f"Initializing NetWORKS application v{self.manifest.get('version', '0.1.0')}")
        
        # Log system information 
        self.logger.debug(f"Qt Version: {sys.modules['PySide6'].__version__}")
        
        # Load configuration
        self.config = Config(self)
        
        # Create device manager
        self.device_manager = DeviceManager(self)
        
        # Create plugin manager
        self.plugin_manager = PluginManager(self)
        
        # Initialize splash screen
        self.splash = SplashScreen()
        self.splash.show()
        
        # Use a timer to give the splash screen time to display
        QTimer.singleShot(100, self.init_application)

    def _load_manifest(self):
        """Load the application manifest"""
        manifest_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "manifest.json"
        )
        
        try:
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    data = json.load(f)
                    # Handle both new and old format
                    version = data.get("version_string", data.get("version", "0.1.0"))
                    return {
                        "name": data.get("name", "NetWORKS"),
                        "version": version,
                        "description": data.get("description", "An extensible device management application"),
                        "author": data.get("author", "NetWORKS Team"),
                        "changelog": data.get("version_history", data.get("changelog", []))
                    }
            else:
                self.logger.warning(f"Manifest file not found at {manifest_path}, using default values")
                return {
                    "name": "NetWORKS",
                    "version": "0.1.0",
                    "description": "An extensible device management application",
                    "author": "NetWORKS Team"
                }
        except Exception as e:
            self.logger.error(f"Error loading manifest: {e}")
            return {
                "name": "NetWORKS", 
                "version": "0.1.0"
            }

    def init_application(self):
        """Initialize the application components"""
        try:
            # Load configuration
            self.splash.update_progress(20, "Loading configuration...")
            self.config.load()
            
            # Initialize device manager
            self.splash.update_progress(40, "Initializing device manager...")
            self.device_manager.initialize()
            
            # Discover plugins
            self.splash.update_progress(60, "Discovering plugins...")
            self.plugin_manager.discover_plugins()

            # Extra validation step: ensure all disabled plugins are truly marked as disabled
            # and all LOADED plugins are reset to just ENABLED state (they'll be loaded explicitly later)
            for plugin_id, plugin_info in list(self.plugin_manager.plugins.items()):
                if plugin_info.state == plugin_info.state.DISABLED:
                    self.logger.debug(f"Ensuring plugin {plugin_id} is properly marked as disabled at startup")
                    # Double-check that it's not loaded
                    if plugin_info.instance is not None:
                        self.logger.warning(f"Plugin {plugin_id} is disabled but has an instance - clearing it")
                        plugin_info.instance = None
                elif plugin_info.state == plugin_info.state.LOADED:
                    # Reset to ENABLED state since nothing is actually loaded yet
                    self.logger.debug(f"Resetting plugin {plugin_id} from LOADED to ENABLED state at startup")
                    plugin_info.state = plugin_info.state.ENABLED
                    plugin_info.instance = None
            
            # Create main window but don't show it yet
            self.splash.update_progress(80, "Initializing main window...")
            self.main_window = MainWindow(self)
            
            # Now load ONLY enabled plugins since the main window is accessible
            self.splash.update_progress(90, "Loading plugins...")
            self.plugin_manager.load_all_plugins()
            
            # Final verification: ensure that any disabled plugins are truly not loaded
            for plugin_id, plugin_info in list(self.plugin_manager.plugins.items()):
                if not plugin_info.state.is_enabled and plugin_info.instance is not None:
                    self.logger.warning(f"Plugin {plugin_id} is disabled but has an instance - forcing unload during startup")
                    # Force unload and clear the instance
                    if plugin_info.state.is_loaded:
                        self.plugin_manager.unload_plugin(plugin_id)
                    else:
                        plugin_info.instance = None
            
            # Now show the main window
            self.splash.update_progress(100, "Starting application...")
            self.main_window.show()
            
            # Close splash screen
            self.splash.finish(self.main_window)
            
            # Optional: show first-run dialog
            if self.config.is_first_run():
                self.on_first_run()
                
            self.logger.info("Application initialized successfully")
        except Exception as e:
            self.logger.exception("Error during application initialization")
            self.splash.hide()  # Hide splash screen before showing error
            show_crash_dialog("Application Initialization Error", e, {"stage": "init_application"})
            sys.exit(1)

    def run(self):
        """Run the application"""
        try:
            return self.exec()
        except Exception as e:
            self.logger.exception(f"Uncaught exception in main event loop: {e}")
            return 1

    def get_version(self):
        """Get the application version"""
        return self.manifest.get("version", "0.1.0")
        
    def get_changelog(self):
        """Get the application changelog"""
        # First try the new format
        changelog = self.manifest.get("changelog", [])
        if changelog:
            return changelog
        
        # If empty, try the old format (version_history)
        version_history = self.manifest.get("version_history", [])
        return version_history 

    def handle_exception(self, title, e, context=None):
        """
        Handle exceptions in a consistent way
        
        Args:
            title: Title for the error dialog
            e: The exception
            context: Additional context for the crash report
        """
        self.logger.exception(f"{title}: {str(e)}")
        show_crash_dialog(title, e, context)
        
    def on_first_run(self):
        """Handle first run setup and welcome"""
        try:
            self.logger.info("First run detected - performing initial setup")
            
            # Show welcome message
            welcome = QMessageBox()
            welcome.setWindowTitle("Welcome to NetWORKS")
            welcome.setText("Welcome to NetWORKS!")
            welcome.setInformativeText(
                "Thank you for installing NetWORKS. This is your first time running the application. "
                "Would you like to see a quick tour of the features?"
            )
            welcome.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            welcome.setDefaultButton(QMessageBox.Yes)
            
            # Show the dialog
            result = welcome.exec()
            
            # If user wants a tour, show it
            if result == QMessageBox.Yes:
                # TODO: Implement tour - for now just show a simple message
                QMessageBox.information(
                    None, 
                    "Tour", 
                    "The tour feature will be available in a future update. "
                    "For now, please explore the application at your own pace."
                )
            
            # Mark as not first run
            self.config.mark_as_run()
            
        except Exception as e:
            self.logger.error(f"Error during first run setup: {e}")
            # Don't crash if first run setup fails 