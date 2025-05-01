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
        print("[DEBUG] Setting up directories")
        setup_directories()
        app.processEvents()
        
        # Check environment
        update_stage()  # Stage 4: Checking environment
        print("[DEBUG] Checking environment")
        env_ok, env_message = check_environment()
        logger.info(f"Environment check: {env_message}")
        if not env_ok:
            logger.warning(f"Environment issue: {env_message}")
            # Show dialog based on environment check result
            QMessageBox.warning(None, "Environment Warning", env_message)
        app.processEvents()
        
        # Load version information
        update_stage()  # Stage 5: Loading version information
        print("[DEBUG] Loading version information")
        version_string = get_version_string()
        version_manifest = load_manifest()
        logger.info(f"Application version: {version_string}")
        app.processEvents()
        
        # Load plugin manager
        update_stage()  # Stage 6: Loading plugin manager
        print("[DEBUG] Loading plugin manager")
        plugin_manager = PluginManager(os.path.join("config", "plugins.json"))
        
        # Discover and load available plugins
        plugin_manager.discover_plugins()
        app.processEvents()
        
        # Create main window
        update_stage()  # Stage 7: Creating main window
        print("[DEBUG] Creating main window")
        main_window = MainWindow(plugin_manager)
        
        # Handle database initialization
        update_stage()  # Stage 8: Initializing database manager
        print("[DEBUG] Initializing database manager")
        logger.debug("Database manager initialization handled by main window")
        app.processEvents()
        
        # Handle database connection
        update_stage()  # Stage 9: Connecting database manager
        print("[DEBUG] Connecting database manager")
        logger.debug("Database connection handled by main window")
        app.processEvents()
        
        # Configure plugins
        update_stage()  # Stage 10: Configuring plugins
        print("[DEBUG] Configuring plugins")
        logger.debug("Plugin configuration handled by main window")
        app.processEvents()
        
        # Start UI
        update_stage()  # Stage 11: Starting UI
        print("[DEBUG] Starting UI")
        logger.debug("Starting user interface")
        app.processEvents()
        
        # Close splash screen
        print("[DEBUG] Closing splash screen")
        splash.close()
        logger.debug("Splash screen closed")
        
        # Show workspace selection dialog
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem
        
        def show_workspace_dialog():
            dialog = QDialog(main_window)
            dialog.setWindowTitle("Workspace Selection")
            dialog.setMinimumSize(500, 400)
            layout = QVBoxLayout(dialog)
            
            # Add header
            header_label = QLabel("Select a workspace or create a new one")
            header_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
            layout.addWidget(header_label)
            
            # Get available workspaces
            workspaces = main_window.workspace_manager.get_workspaces()
            
            # Check if we have any workspaces besides default
            if len(workspaces) <= 1:
                # Just use default workspace and close dialog
                return False
            
            # Add list widget for workspaces
            workspace_list = QListWidget()
            workspace_list.setStyleSheet("QListWidget::item { padding: 8px; }")
            
            # Add workspaces to list
            for workspace_id, workspace_data in workspaces.items():
                # Skip default workspace
                if workspace_data.get('name', '').lower() == 'default' and workspace_id == main_window.workspace_manager.current_workspace_id:
                    continue
                    
                item = QListWidgetItem(f"{workspace_data.get('name', 'Unnamed')} - {workspace_data.get('devices_count', 0)} devices")
                item.setData(Qt.UserRole, workspace_id)
                workspace_list.addItem(item)
            
            # Select first item
            if workspace_list.count() > 0:
                workspace_list.setCurrentRow(0)
                
            layout.addWidget(workspace_list)
            
            # Add buttons
            button_layout = QHBoxLayout()
            
            new_workspace_btn = QPushButton("Create New Workspace")
            open_workspace_btn = QPushButton("Open Selected Workspace")
            cancel_btn = QPushButton("Use Default Workspace")
            
            # Connect signals
            def on_new_workspace():
                # Show new workspace dialog
                from PySide6.QtWidgets import QInputDialog
                name, ok = QInputDialog.getText(dialog, "New Workspace", "Enter name for new workspace:")
                if ok and name:
                    # Create new workspace
                    workspace_id = main_window.workspace_manager.create_workspace(name)
                    if workspace_id:
                        # Open new workspace
                        main_window.workspace_manager.open_workspace(workspace_id)
                        dialog.accept()
            
            def on_open_workspace():
                # Get selected workspace ID
                selected_items = workspace_list.selectedItems()
                if selected_items:
                    workspace_id = selected_items[0].data(Qt.UserRole)
                    # Open selected workspace
                    main_window.workspace_manager.open_workspace(workspace_id)
                    dialog.accept()
            
            new_workspace_btn.clicked.connect(on_new_workspace)
            open_workspace_btn.clicked.connect(on_open_workspace)
            cancel_btn.clicked.connect(dialog.reject)
            
            button_layout.addWidget(new_workspace_btn)
            button_layout.addWidget(open_workspace_btn)
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            
            # Execute dialog
            return dialog.exec_() == QDialog.Accepted
            
        # Show workspace dialog after a short delay to ensure UI is fully loaded
        QTimer.singleShot(500, show_workspace_dialog)
        
        # Show main window
        main_window.show()
        logger.debug("Main window displayed")
        
        # Set exception handler
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
            return False, f"Critical directory missing: {directory}"
    
    # Check for critical files
    critical_files = [
        "requirements.txt",
        os.path.join("core", "__init__.py"),
        os.path.join("core", "ui", "main_window.py")
    ]
    for file in critical_files:
        if not os.path.isfile(file):
            print(f"[ERROR] Critical file missing: {file}")
            return False, f"Critical file missing: {file}"
    
    return True, "All critical paths and files exist"

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