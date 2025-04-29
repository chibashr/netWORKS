#!/usr/bin/env python3
# netWORKS - Network Scanner Application
# Main application entry point

import sys
import os
import logging
import traceback
import time
import importlib
import platform
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer

from core.ui.main_window import MainWindow
from core.plugins.plugin_manager import PluginManager
from core.ui.splash_screen import SplashScreen
from config.logging import setup_logging
from core.version import get_version_string, load_manifest

def setup_style():
    """Setup application style and theme."""
    style = """
        QMainWindow, QWidget {
            background-color: #ffffff;
            color: #333333;
        }
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            padding: 5px 15px;
            min-width: 80px;
            outline: none;
            color: #333333;
        }
        QPushButton:hover {
            background-color: #e6e6e6;
            border-color: #adadad;
        }
        QPushButton:pressed {
            background-color: #d4d4d4;
            border-color: #8c8c8c;
        }
        QPushButton:disabled {
            background-color: #f5f5f5;
            border-color: #d9d9d9;
            color: #999999;
        }
        QLineEdit {
            padding: 5px;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            background-color: white;
            color: #333333;
        }
        QComboBox {
            padding: 5px;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            background-color: white;
            color: #333333;
        }
        QComboBox QAbstractItemView {
            background-color: white;
            color: #333333;
            selection-background-color: #e6e6e6;
            selection-color: #333333;
        }
        QGroupBox {
            margin-top: 10px;
            font-weight: bold;
            color: #333333;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            padding: 15px;
            background-color: white;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            background-color: white;
        }
        QTableWidget {
            gridline-color: #e0e0e0;
            background-color: white;
            border: 1px solid #c0c0c0;
            color: #333333;
            selection-background-color: #f0f0f0;
            selection-color: #333333;
            alternate-background-color: #ffffff;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:selected {
            background-color: #f0f0f0;
        }
        QHeaderView::section {
            background-color: #f5f5f5;
            padding: 5px;
            border: 1px solid #c0c0c0;
            border-left: 0px;
            border-top: 0px;
            color: #333333;
            font-weight: bold;
        }
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #f0f0f0;
            border: 1px solid #c0c0c0;
            padding: 5px 10px;
            margin-right: 2px;
            color: #666666;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom-color: white;
            color: #333333;
        }
        QTabBar::tab:hover {
            background-color: #e6e6e6;
        }
        QTextEdit {
            background-color: white;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            color: #333333;
            selection-background-color: #e6e6e6;
            selection-color: #333333;
        }
        QLabel {
            color: #333333;
        }
        QMenuBar {
            background-color: #f5f5f5;
            border-bottom: 1px solid #c0c0c0;
        }
        QMenuBar::item {
            spacing: 5px;
            padding: 2px 10px;
            background: transparent;
            color: #333333;
        }
        QMenuBar::item:selected {
            background: #e6e6e6;
        }
        QMenu {
            background-color: white;
            border: 1px solid #c0c0c0;
        }
        QMenu::item {
            padding: 5px 30px 5px 30px;
            color: #333333;
        }
        QMenu::item:selected {
            background-color: #e6e6e6;
        }
        QStatusBar {
            background-color: #f5f5f5;
            color: #333333;
            border-top: 1px solid #c0c0c0;
        }
        QSplitter::handle {
            background-color: #c0c0c0;
        }
        QSplitter::handle:horizontal {
            width: 1px;
        }
        QSplitter::handle:vertical {
            height: 1px;
        }
    """
    return style

def setup_directories():
    """Setup application directories."""
    dirs = ['config', 'logs', 'plugins', 'data']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)

def main():
    """Main entry point for the application."""
    # Track startup progress stages
    startup_stages = [
        (5, "Starting application"),
        (10, "Initializing logging"),
        (15, "Setting up directories"),
        (20, "Checking environment"),
        (25, "Loading version information"),
        (30, "Loading plugin manager"),
        (50, "Creating main window"),
        (60, "Initializing database manager"),
        (70, "Connecting database manager"),
        (80, "Configuring plugins"),
        (95, "Starting UI")
    ]
    
    current_stage = 0
    splash = None
    logger = None
    
    try:
        print("[DEBUG] Starting netWORKS application")
        print(f"[DEBUG] Python version: {sys.version}")
        print(f"[DEBUG] Current directory: {os.getcwd()}")
        print(f"[DEBUG] System platform: {sys.platform}")
        
        # Display startup stage
        def update_stage():
            nonlocal current_stage
            if current_stage < len(startup_stages):
                progress, message = startup_stages[current_stage]
                print(f"[DEBUG] Startup stage {current_stage + 1}/{len(startup_stages)}: {message} ({progress}%)")
                if splash:
                    splash.update_progress(progress, message)
                if logger:
                    logger.debug(f"Startup stage {current_stage + 1}/{len(startup_stages)}: {message}")
                current_stage += 1
        
        update_stage()  # Stage 1: Starting application
        
        # Create Qt application
        print("[DEBUG] Creating Qt application")
        app = QApplication(sys.argv)
        
        # Set application style
        print("[DEBUG] Setting application style")
        app.setStyle("Fusion")
        app.setStyleSheet(setup_style())
        
        # Create and show splash screen
        print("[DEBUG] Creating splash screen")
        splash = SplashScreen()
        splash.show()
        app.processEvents()  # Process events to make sure splash screen appears
        
        # Initialize logging
        update_stage()  # Stage 2: Initializing logging
        print("[DEBUG] Setting up logging")
        logger = setup_logging()
        app.processEvents()
        
        # Setup directories
        update_stage()  # Stage 3: Setting up directories
        print("[DEBUG] Creating required directories")
        setup_directories()
        app.processEvents()
        
        # Check for critical paths and files
        update_stage()  # Stage 4: Checking environment
        print("[DEBUG] Checking environment")
        if not check_environment():
            logger.error("Environment check failed - critical paths/files missing")
            raise RuntimeError("Environment check failed - see logs for details")
        app.processEvents()
        
        # Load version information
        update_stage()  # Stage 5: Loading version information
        print("[DEBUG] Loading version information")
        manifest = load_manifest()
        if manifest:
            logger.info(f"Application version: {manifest['version_string']}")
            logger.info(f"Build date: {manifest['build_date']}")
            logger.info(f"API compatibility: {manifest['compatibility']['min_plugin_api']}")
            logger.info(f"Min Python version: {manifest['compatibility']['min_python_version']}")
        else:
            logger.warning("Failed to load version manifest, using default version information")
        app.processEvents()
        
        # Create plugin manager
        update_stage()  # Stage 6: Loading plugin manager
        print("[DEBUG] Creating plugin manager")
        try:
            plugin_manager = PluginManager(os.path.join("config", "plugins.json"))
        except Exception as e:
            logger.error(f"Error creating plugin manager: {str(e)}", exc_info=True)
            print(f"[ERROR] Plugin manager creation failed: {str(e)}")
            # Create a minimal plugin manager to allow the application to continue
            plugin_manager = PluginManager(os.path.join("config", "plugins.json"), skip_discovery=True)
        app.processEvents()
        
        # Create main window but don't show it yet
        update_stage()  # Stage 7: Creating main window
        print("[DEBUG] Creating main window")
        try:
            main_window = MainWindow(plugin_manager)
            # Note: We don't set the main window reference here anymore
            # It will be set in the plugin configuration stage (stage 10)
        except Exception as e:
            logger.error(f"Error creating main window: {str(e)}", exc_info=True)
            print(f"[ERROR] Main window creation failed: {str(e)}")
            raise  # This is critical - we can't continue without a main window
        app.processEvents()
        
        # Removed workspace manager creation - now using database manager
        update_stage()  # Stage 8: Initializing database manager (handled by core module)
        update_stage()  # Stage 9: Connecting database manager (handled by core module)
        
        # Set main window reference in plugin APIs
        update_stage()  # Stage 10: Configuring plugins
        print("[DEBUG] Configuring plugins with main window reference")
        
        # Use the plugin manager's method to set the main window reference
        plugin_manager.set_main_window(main_window)
        
        # Successfully set the main window for all plugins
        plugin_connection_results = {"success": len(plugin_manager.plugin_apis), "failure": 0}
        print(f"[DEBUG] Plugin configuration results: {plugin_connection_results['success']} succeeded, {plugin_connection_results['failure']} failed")
        logger.info(f"Plugin configuration results: {plugin_connection_results['success']} succeeded, {plugin_connection_results['failure']} failed")
        app.processEvents()
        
        # Show main window
        update_stage()  # Stage 11: Starting UI
        print("[DEBUG] Showing main window")
        main_window.show()
        logger.info("Application initialized and main window shown")
        app.processEvents()
        
        # Close splash screen after a short delay
        print("[DEBUG] Closing splash screen")
        QTimer.singleShot(1000, splash.close)
        
        # Set exception hook for unhandled exceptions
        def exception_hook(exctype, value, traceback):
            logger.critical("Unhandled exception", exc_info=(exctype, value, traceback))
            print(f"[ERROR] Unhandled exception: {exctype.__name__}: {value}")
            sys.__excepthook__(exctype, value, traceback)
        
        sys.excepthook = exception_hook
        
        # Set up a timer to periodically flush event queue
        # This helps prevent UI freezing issues
        def flush_events():
            app.processEvents()
        
        flush_timer = QTimer()
        flush_timer.timeout.connect(flush_events)
        flush_timer.start(100)  # 100ms interval
        
        print("[DEBUG] Starting application event loop")
        # Start Qt event loop
        return app.exec_()
        
    except Exception as e:
        error_msg = f"Error starting application: {str(e)}"
        
        # Try to use logger if available, otherwise print to console
        if 'logger' in locals() and logger:
            logger.error(error_msg, exc_info=True)
        else:
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
        
        # Try to show error dialog if QApplication exists
        try:
            if 'app' in locals() and app:
                from PySide6.QtWidgets import QMessageBox
                error_dialog = QMessageBox()
                error_dialog.setIcon(QMessageBox.Icon.Critical)
                error_dialog.setWindowTitle("Startup Error")
                error_dialog.setText("Fatal error during application startup")
                error_dialog.setDetailedText(f"{error_msg}\n\n{traceback.format_exc()}")
                error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
                error_dialog.exec()
        except Exception as dialog_e:
            print(f"[ERROR] Failed to show error dialog: {str(dialog_e)}")
        
        return 1

def check_environment():
    """Check if critical paths and files exist."""
    # Check for critical directories
    critical_dirs = ["core", "plugins", "config"]
    for directory in critical_dirs:
        if not os.path.isdir(directory):
            print(f"[ERROR] Critical directory missing: {directory}")
            return False
    
    # Check for critical files
    critical_files = [
        "requirements.txt",
        os.path.join("core", "__init__.py"),
        os.path.join("core", "ui", "main_window.py")
    ]
    for file in critical_files:
        if not os.path.isfile(file):
            print(f"[ERROR] Critical file missing: {file}")
            return False
    
    return True

class MainApp(QApplication):
    """Main application class."""
    
    def __init__(self, args):
        super().__init__(args)
        self.setApplicationName("netWORKS")
        version = get_version_string()
        self.setApplicationVersion(version)
        self.setOrganizationName("netWORKS")
        self.setOrganizationDomain("networks.local")
        self.setWindowIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        
        # Set application style
        self.setStyleSheet(setup_style())
        
        # Disable close on escape key
        self.setQuitOnLastWindowClosed(True)

if __name__ == "__main__":
    sys.exit(main()) 