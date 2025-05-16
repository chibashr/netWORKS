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
        """Initialize application components"""
        self.logger.info("Initializing application")
        
        # Show splash screen
        splash = SplashScreen()
        splash.show()
        
        # Check environment for data directories
        self._ensure_data_directories()
        
        # Load configuration
        splash.update_progress(20, "Loading configuration...")
        self.config = Config(self)
        self.config.load()
        
        # Initialize device manager
        splash.update_progress(40, "Initializing device manager...")
        self.device_manager = DeviceManager(self)
        
        # Initialize plugin manager
        splash.update_progress(60, "Loading plugins...")
        self.plugin_manager = PluginManager(self)
        
        # Initialize issue reporter
        splash.update_progress(80, "Initializing issue reporting system...")
        from .core.issue_reporter import IssueReporter
        self.issue_reporter = IssueReporter(self.config, self)
        
        # Update logging configuration based on settings
        try:
            logging_level = self.config.get("logging.level", "INFO")
            diagnose = self.config.get("logging.diagnose", True)
            backtrace = self.config.get("logging.backtrace", True)
            
            self.logger.info(f"Updating logging configuration: level={logging_level}, diagnose={diagnose}, backtrace={backtrace}")
            if hasattr(self.logging_manager, 'update_configuration'):
                self.logging_manager.update_configuration(logging_level, diagnose, backtrace)
            else:
                self.logger.warning("LoggingManager does not have update_configuration method, skipping configuration update")
        except Exception as e:
            self.logger.warning(f"Failed to update logging configuration: {e}")
        
        # Create main window
        splash.update_progress(90, "Creating main window...")
        self.main_window = MainWindow(self)
        
        # Complete progress and close splash screen
        splash.update_progress(100, "Startup complete...")
        splash.close()
        
        # Show workspace selection dialog before displaying the main window
        self.show_workspace_selection()
        
        # Now display the main window
        self.main_window.show()
        
        # Check for first run
        if self.config.is_first_run():
            self.logger.info("First run detected")
            # Mark as having been run to prevent showing on next startup
            self.config.mark_as_run()
            
            # Show first run dialog after a short delay to ensure main window is visible
            QTimer.singleShot(500, self.on_first_run)
            
        # Check for queued issues if we have a token
        if hasattr(self, 'issue_reporter') and self.issue_reporter.github_token:
            QTimer.singleShot(10000, self._check_issue_queue)
            
    def show_workspace_selection(self):
        """Show workspace selection dialog at startup"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QGroupBox, QRadioButton, QLineEdit, QTextEdit
        
        self.logger.info("Showing workspace selection dialog")
        
        # Get list of workspaces
        workspaces = self.device_manager.list_workspaces()
        
        # Create dialog
        dialog = QDialog()
        dialog.setWindowTitle("Workspace Selection")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        # Header section
        header_label = QLabel("Select a workspace to open or create a new one:")
        header_label.setStyleSheet("font-size: 12pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header_label)
        
        # Radio button options
        option_group = QGroupBox("Options")
        option_layout = QVBoxLayout(option_group)
        
        open_radio = QRadioButton("Open existing workspace")
        create_radio = QRadioButton("Create new workspace")
        
        # Default to "Open existing" if workspaces exist, otherwise default to "Create new"
        if workspaces:
            open_radio.setChecked(True)
        else:
            create_radio.setChecked(True)
            
        option_layout.addWidget(open_radio)
        option_layout.addWidget(create_radio)
        layout.addWidget(option_group)
        
        # Existing workspaces section
        existing_group = QGroupBox("Existing Workspaces")
        existing_layout = QVBoxLayout(existing_group)
        
        workspaces_list = QListWidget()
        
        # Default workspace should be first in the list
        default_idx = -1
        
        # Add workspaces to the list
        for i, workspace in enumerate(workspaces):
            name = workspace.get("name", "Unknown")
            description = workspace.get("description", "")
            display_text = f"{name} - {description}" if description else name
            workspaces_list.addItem(display_text)
            
            # Remember index of default workspace
            if name == "default":
                default_idx = i
        
        # Select default workspace if it exists
        if default_idx >= 0:
            workspaces_list.setCurrentRow(default_idx)
            
        existing_layout.addWidget(workspaces_list)
        layout.addWidget(existing_group)
        
        # New workspace section
        new_group = QGroupBox("New Workspace")
        new_layout = QVBoxLayout(new_group)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        name_edit = QLineEdit()
        name_layout.addWidget(name_edit)
        new_layout.addLayout(name_layout)
        
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        desc_edit = QTextEdit()
        desc_edit.setMaximumHeight(80)
        desc_layout.addWidget(desc_edit)
        new_layout.addLayout(desc_layout)
        
        layout.addWidget(new_group)
        
        # Show/hide appropriate sections based on radio button selection
        def update_sections():
            existing_group.setVisible(open_radio.isChecked())
            new_group.setVisible(create_radio.isChecked())
            dialog.adjustSize()
            
        open_radio.toggled.connect(update_sections)
        create_radio.toggled.connect(update_sections)
        
        # Initial update
        update_sections()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # If no workspaces exist, don't show the Skip button
        if workspaces:
            skip_button = QPushButton("Skip (Use Default)")
            button_layout.addWidget(skip_button)
            
            def on_skip():
                self.device_manager.load_workspace("default")
                self.main_window.refresh_workspace_ui()
                dialog.accept()
                
            skip_button.clicked.connect(on_skip)
        
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # Handle OK button
        def on_ok():
            if open_radio.isChecked():
                # Open selected workspace
                selected_item = workspaces_list.currentItem()
                if selected_item:
                    workspace_name = selected_item.text().split(" - ")[0]
                    success = self.device_manager.load_workspace(workspace_name)
                    if success:
                        self.logger.info(f"Loaded workspace: {workspace_name}")
                        self.main_window.refresh_workspace_ui()
                        dialog.accept()
                    else:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.critical(dialog, "Error", f"Failed to load workspace: {workspace_name}")
                else:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(dialog, "No Selection", "Please select a workspace to open.")
            else:
                # Create new workspace
                name = name_edit.text().strip()
                description = desc_edit.toPlainText().strip()
                
                if not name:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(dialog, "Invalid Name", "Please enter a name for the workspace.")
                    return
                    
                # Check if workspace already exists
                for ws in workspaces:
                    if ws.get("name") == name:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.warning(dialog, "Workspace Exists", f"A workspace named '{name}' already exists.")
                        return
                
                # Create the new workspace
                success = self.device_manager.create_workspace(name, description)
                if success:
                    # Load the new workspace
                    self.device_manager.load_workspace(name)
                    self.logger.info(f"Created and loaded workspace: {name}")
                    self.main_window.refresh_workspace_ui()
                    dialog.accept()
                else:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.critical(dialog, "Error", f"Failed to create workspace: {name}")
        
        # Handle Cancel button (use default workspace)
        def on_cancel():
            self.device_manager.load_workspace("default")
            self.main_window.refresh_workspace_ui()
            dialog.reject()
            
        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(on_cancel)
        
        # Make dialog modal to block until user makes a choice
        dialog.setModal(True)
        dialog.exec()

    def _ensure_data_directories(self):
        """Ensure data directories exist"""
        data_dirs = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "workspaces"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "downloads"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "backups"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "screenshots"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "issue_queue")
        ]
        
        for directory in data_dirs:
            os.makedirs(directory, exist_ok=True)

    def _check_issue_queue(self):
        """Check for queued issues and try to process them"""
        if hasattr(self, 'issue_reporter'):
            queue_size, is_processing = self.issue_reporter.get_queue_status()
            if queue_size > 0 and not is_processing:
                self.logger.info(f"Found {queue_size} queued issues. Attempting to process...")
                self.issue_reporter.process_queue()

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