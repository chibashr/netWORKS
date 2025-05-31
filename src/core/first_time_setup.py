#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
First-time setup module for NetWORKS application
Handles initialization of directories, settings, and first-run setup when running from executable
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

try:
    from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                   QPushButton, QProgressBar, QTextEdit, QCheckBox,
                                   QGroupBox, QGridLayout, QMessageBox, QApplication, QWidget)
    from PySide6.QtCore import Qt, QTimer, QThread, Signal
    from PySide6.QtGui import QPixmap, QFont
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


class SetupWorker(QThread):
    """Worker thread for performing setup tasks"""
    progress_updated = Signal(int, str)
    setup_completed = Signal(bool, str)
    
    def __init__(self, app_dir: Path, create_sample_data: bool = False):
        super().__init__()
        self.app_dir = app_dir
        self.create_sample_data = create_sample_data
        
    def run(self):
        """Run the setup process"""
        try:
            self.progress_updated.emit(10, "Creating application directories...")
            self._create_directories()
            
            self.progress_updated.emit(30, "Initializing configuration...")
            self._create_default_config()
            
            self.progress_updated.emit(50, "Setting up workspaces...")
            self._create_default_workspace()
            
            self.progress_updated.emit(70, "Initializing plugins...")
            self._create_plugin_structure()
            
            if self.create_sample_data:
                self.progress_updated.emit(85, "Creating sample data...")
                self._create_sample_data()
            
            self.progress_updated.emit(95, "Finalizing setup...")
            self._finalize_setup()
            
            self.progress_updated.emit(100, "Setup completed successfully!")
            self.setup_completed.emit(True, "First-time setup completed successfully!")
            
        except Exception as e:
            self.setup_completed.emit(False, f"Setup failed: {str(e)}")
    
    def _create_directories(self):
        """Create all necessary application directories using standardized structure"""
        # Try to load directory configuration from build
        directory_config = self._load_directory_config()
        
        if directory_config:
            print("Using standardized directory structure from build configuration")
            self._create_directories_from_config(directory_config)
        else:
            print("Using fallback directory structure")
            self._create_fallback_directories()
    
    def _load_directory_config(self):
        """Load directory configuration from build"""
        try:
            # Look for directory_config.json in the application directory
            config_path = self.app_dir / "directory_config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Could not load directory configuration: {e}")
        return None
    
    def _create_directories_from_config(self, directory_config):
        """Create directories based on the standardized configuration"""
        directory_structure = directory_config.get("directory_structure", {})
        
        for dir_name, dir_info in directory_structure.items():
            # Create main directory
            main_dir = self.app_dir / dir_info["path"]
            main_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created: {dir_info['path']} - {dir_info['description']}")
            
            # Create subdirectories
            for subdir in dir_info.get("subdirs", []):
                sub_path = main_dir / subdir
                sub_path.mkdir(parents=True, exist_ok=True)
                print(f"  └─ {subdir}/")
                
                # Create .gitkeep for empty directories to ensure persistence
                gitkeep_path = sub_path / ".gitkeep"
                if not gitkeep_path.exists():
                    gitkeep_path.touch()
            
            # Create .gitkeep for main directory if it has no subdirs
            if not dir_info.get("subdirs"):
                gitkeep_path = main_dir / ".gitkeep"
                if not gitkeep_path.exists():
                    gitkeep_path.touch()
    
    def _create_fallback_directories(self):
        """Create directories using fallback structure (for compatibility)"""
        # Simplified, non-redundant directory structure
        directories = [
            # Configuration
            "config/settings",
            "config/backups",
            # Workspaces (separate from config to avoid redundancy)
            "workspaces/default",
            # Data storage
            "data/downloads", 
            "data/backups",
            "data/screenshots",
            "data/issue_queue",
            # Runtime directories
            "logs/crashes",
            "exports",
            "command_outputs/history",
            "command_outputs/outputs",
            # Plugins
            "plugins"
        ]
        
        for directory in directories:
            dir_path = self.app_dir / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create .gitkeep files for persistence
            gitkeep_path = dir_path / ".gitkeep"
            if not gitkeep_path.exists():
                gitkeep_path.touch()
        
        print(f"Created {len(directories)} directories using fallback structure")
    
    def _create_default_config(self):
        """Create default application configuration"""
        config_dir = self.app_dir / "config" / "settings"
        
        # Create application settings with configurable directory paths
        app_settings = {
            "version": "0.9.11",
            "first_run": False,
            "setup_date": datetime.now().isoformat(),
            "theme": "light",
            "auto_save_enabled": True,
            "auto_save_interval": 300,
            "log_level": "INFO",
            "check_for_updates": True,
            "plugins_enabled": True,
            "external_plugins_directory": str(self.app_dir / "plugins"),  # Explicit path to user plugins directory
            
            # Configurable directory paths (can be changed in settings)
            "directory_paths": {
                "workspaces_dir": str(self.app_dir / "workspaces"),
                "data_dir": str(self.app_dir / "data"),
                "logs_dir": str(self.app_dir / "logs"),
                "config_dir": str(self.app_dir / "config"),
                "exports_dir": str(self.app_dir / "exports"),
                "command_outputs_dir": str(self.app_dir / "command_outputs"),
                "plugins_dir": str(self.app_dir / "plugins")
            },
            
            # Directory persistence settings
            "directory_settings": {
                "persistent_directories": True,  # Don't recreate existing directories
                "auto_create_missing": True,     # Create missing directories on startup
                "preserve_gitkeep": True,        # Keep .gitkeep files for empty directories
                "structure_version": "2.0"       # Track directory structure version
            }
        }
        
        settings_file = config_dir / "app_settings.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(app_settings, f, indent=2)
        
        # Create workspace-specific configuration
        workspace_config = {
            "workspace_name": "default",
            "created_date": datetime.now().isoformat(),
            "description": "Default workspace for NetWORKS",
            "plugins": {
                "enabled": [],
                "disabled": [],
                "configurations": {}
            },
            "directory_structure": {
                "workspace_data": str(self.app_dir / "workspaces" / "default"),
                "isolated_storage": True,  # Each workspace has isolated storage
                "inherit_global_settings": True
            }
        }
        
        workspace_config_dir = self.app_dir / "workspaces" / "default"
        workspace_config_dir.mkdir(parents=True, exist_ok=True)
        workspace_config_file = workspace_config_dir / "workspace_config.json"
        with open(workspace_config_file, 'w', encoding='utf-8') as f:
            json.dump(workspace_config, f, indent=2)
    
    def _create_default_workspace(self):
        """Create the default workspace"""
        workspace_dir = self.app_dir / "workspaces" / "default"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Create workspace configuration
        workspace_config = {
            "name": "default",
            "description": "Default workspace",
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "enabled_plugins": [],
            "settings": {
                "auto_save": True,
                "backup_count": 5
            }
        }
        
        config_file = workspace_dir / "workspace.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(workspace_config, f, indent=2)
        
        # Create workspace data directory
        data_dir = self.app_dir / "data" / "workspaces" / "default"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create devices file
        devices_file = data_dir / "devices.json"
        with open(devices_file, 'w', encoding='utf-8') as f:
            json.dump({"devices": [], "groups": []}, f, indent=2)
    
    def _create_plugin_structure(self):
        """Create plugin directory structure"""
        plugins_dir = self.app_dir / "plugins"
        
        # Create a readme file for users (replaced Unicode arrow with ASCII)
        readme_content = """# NetWORKS Plugins Directory

This directory contains external plugins for NetWORKS.

## How to Install Plugins

1. Copy plugin folders to this directory
2. Restart NetWORKS
3. Enable plugins in the Plugin Manager (Tools -> Plugin Manager)

## Plugin Development

See the documentation in the `docs/plugins/` directory for information on developing plugins.

## Built-in Plugins

Built-in plugins are included with the application and don't need to be placed here.
They include:
- Command Manager
- Config Manager  
- Network Scanner
- Sample Plugin (for reference)

For more information, visit: https://github.com/networks/networks
"""
        
        readme_file = plugins_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def _create_sample_data(self):
        """Create sample data for demonstration"""
        data_dir = self.app_dir / "data" / "workspaces" / "default"
        
        # Create sample devices
        sample_devices = {
            "devices": [
                {
                    "id": "sample-device-1",
                    "name": "Sample Router",
                    "type": "router",
                    "ip_address": "192.168.1.1",
                    "description": "Sample network device for demonstration",
                    "group": "Network Infrastructure",
                    "properties": {
                        "vendor": "Cisco",
                        "model": "ISR 4431",
                        "os_version": "16.09.03"
                    }
                },
                {
                    "id": "sample-device-2", 
                    "name": "Sample Switch",
                    "type": "switch",
                    "ip_address": "192.168.1.2",
                    "description": "Sample switch device",
                    "group": "Network Infrastructure",
                    "properties": {
                        "vendor": "Cisco",
                        "model": "Catalyst 9300",
                        "port_count": 48
                    }
                }
            ],
            "groups": [
                {
                    "name": "Network Infrastructure",
                    "description": "Core network devices",
                    "color": "#4CAF50"
                }
            ]
        }
        
        devices_file = data_dir / "devices.json"
        with open(devices_file, 'w', encoding='utf-8') as f:
            json.dump(sample_devices, f, indent=2)
    
    def _finalize_setup(self):
        """Finalize the setup process"""
        # Create setup completion marker
        config_dir = self.app_dir / "config"
        config_dir.mkdir(exist_ok=True)  # Ensure config directory exists
        
        setup_marker = config_dir / ".setup_completed"
        with open(setup_marker, 'w', encoding='utf-8') as f:
            f.write(f"Setup completed on: {datetime.now().isoformat()}\n")
            f.write(f"NetWORKS version: 0.9.12\n")
            f.write(f"Directory structure version: 2.0\n")


class FirstTimeSetupDialog(QDialog):
    """Dialog for first-time setup of NetWORKS"""
    
    def __init__(self, app_dir: Path, parent=None):
        super().__init__(parent)
        self.app_dir = app_dir
        self.setup_worker = None
        
        self.setWindowTitle("NetWORKS First-Time Setup")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        # Apply light mode styling
        self._apply_light_theme()
        
        self._setup_ui()
        
    def _apply_light_theme(self):
        """Apply light theme styling to the setup dialog"""
        self.setStyleSheet("""
        QDialog {
            background-color: #f5f5f5;
            color: #333333;
        }
        QGroupBox {
            background-color: #f8f8f8;
            border: 1px solid #dddddd;
            border-radius: 4px;
            margin-top: 15px;
            padding-top: 10px;
            font-weight: bold;
            color: #333333;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
            background-color: #f8f8f8;
            color: #333333;
        }
        QLabel {
            color: #333333;
            background-color: transparent;
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
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #999999;
            border-color: #dddddd;
        }
        QCheckBox {
            color: #333333;
            background-color: transparent;
        }
        QCheckBox::indicator {
            width: 15px;
            height: 15px;
            border: 1px solid #cccccc;
            background-color: white;
            border-radius: 2px;
        }
        QCheckBox::indicator:checked {
            background-color: #4a90e2;
            border-color: #4a90e2;
        }
        QCheckBox::indicator:checked::after {
            content: "✓";
            color: white;
            font-weight: bold;
        }
        QProgressBar {
            border: 1px solid #cccccc;
            border-radius: 3px;
            background-color: #f0f0f0;
            text-align: center;
            color: #333333;
        }
        QProgressBar::chunk {
            background-color: #4a90e2;
            border-radius: 2px;
        }
        QTextEdit {
            background-color: white;
            color: #333333;
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        """)
        
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Welcome section
        welcome_group = QGroupBox("Welcome to NetWORKS!")
        welcome_layout = QVBoxLayout(welcome_group)
        
        welcome_label = QLabel(
            "This appears to be your first time running NetWORKS.\n\n"
            "The setup process will create necessary directories and initialize "
            "the application with default settings.\n\n"
            "This will only take a moment."
        )
        welcome_label.setWordWrap(True)
        welcome_layout.addWidget(welcome_label)
        
        layout.addWidget(welcome_group)
        
        # Options section
        options_group = QGroupBox("Setup Options")
        options_layout = QVBoxLayout(options_group)
        
        self.sample_data_checkbox = QCheckBox("Create sample devices for demonstration")
        self.sample_data_checkbox.setChecked(True)
        self.sample_data_checkbox.setToolTip(
            "Creates a few sample devices to help you get started with NetWORKS"
        )
        options_layout.addWidget(self.sample_data_checkbox)
        
        layout.addWidget(options_group)
        
        # Progress section
        progress_group = QGroupBox("Setup Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready to begin setup...")
        progress_layout.addWidget(self.progress_label)
        
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(80)
        self.log_output.setVisible(False)
        progress_layout.addWidget(self.log_output)
        
        layout.addWidget(progress_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_button = QPushButton("Start Setup")
        self.start_button.clicked.connect(self._start_setup)
        button_layout.addWidget(self.start_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        self.close_button.setEnabled(False)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def _start_setup(self):
        """Start the setup process"""
        self.start_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_output.setVisible(True)
        
        # Create and start setup worker
        self.setup_worker = SetupWorker(
            self.app_dir, 
            create_sample_data=self.sample_data_checkbox.isChecked()
        )
        self.setup_worker.progress_updated.connect(self._update_progress)
        self.setup_worker.setup_completed.connect(self._setup_completed)
        self.setup_worker.start()
    
    def _update_progress(self, value: int, message: str):
        """Update progress display"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        self.log_output.append(f"[{value:3d}%] {message}")
    
    def _setup_completed(self, success: bool, message: str):
        """Handle setup completion"""
        if success:
            self.progress_label.setText("Setup completed successfully!")
            self.log_output.append(f"\n✓ {message}")
            self.accept()
        else:
            self.progress_label.setText("Setup failed!")
            self.log_output.append(f"\n✗ {message}")
            QMessageBox.critical(self, "Setup Failed", 
                               f"First-time setup failed:\n\n{message}\n\n"
                               "Please check that you have write permissions to the application directory.")
        
        self.close_button.setEnabled(True)
        self.start_button.setEnabled(True)


class FirstTimeSetup:
    """Handles first-time setup for NetWORKS application"""
    
    def __init__(self, app_dir: Optional[Path] = None):
        """Initialize first-time setup"""
        if app_dir is None:
            # Determine application directory
            if getattr(sys, 'frozen', False):
                # Running as executable
                self.app_dir = Path(sys.executable).parent
            else:
                # Running as script
                self.app_dir = Path(__file__).parent.parent.parent
        else:
            # Ensure app_dir is always a Path object, even if passed as string
            self.app_dir = Path(app_dir)
    
    def is_first_run(self) -> bool:
        """Check if this is the first run of the application"""
        setup_marker = self.app_dir / "config" / ".setup_completed"
        
        # Check if running as executable and no setup has been completed
        if getattr(sys, 'frozen', False):
            # Running as executable - check for setup marker
            return not setup_marker.exists()
        else:
            # Running as script - check if basic directories exist
            config_dir = self.app_dir / "config"
            return not config_dir.exists() or not setup_marker.exists()
    
    def run_setup(self, show_dialog: bool = True) -> bool:
        """Run the first-time setup process"""
        if not self.is_first_run():
            return True
        
        print("First-time setup required...")
        
        if show_dialog and PYSIDE_AVAILABLE:
            # Show GUI setup dialog
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            dialog = FirstTimeSetupDialog(self.app_dir)
            result = dialog.exec()
            
            return result == QDialog.DialogCode.Accepted
        else:
            # Run console setup
            return self._run_console_setup()
    
    def _run_console_setup(self) -> bool:
        """Run setup in console mode (no GUI)"""
        try:
            print("Setting up NetWORKS directories and configuration...")
            
            # Create setup worker and run synchronously
            worker = SetupWorker(self.app_dir, create_sample_data=False)
            
            print("Creating application directories...")
            worker._create_directories()
            
            print("Initializing configuration...")
            worker._create_default_config()
            
            print("Setting up workspaces...")
            worker._create_default_workspace()
            
            print("Initializing plugins...")
            worker._create_plugin_structure()
            
            print("Finalizing setup...")
            worker._finalize_setup()
            
            print("First-time setup completed successfully!")
            return True
            
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def get_app_directory(self) -> Path:
        """Get the application directory"""
        return self.app_dir


def run_first_time_setup_if_needed() -> bool:
    """Run first-time setup if this is the first run"""
    setup = FirstTimeSetup()
    
    if setup.is_first_run():
        print("NetWORKS First-Time Setup")
        print("=" * 30)
        
        # Determine if we can show GUI
        show_gui = PYSIDE_AVAILABLE and not any(arg in sys.argv for arg in ['--no-gui', '--console'])
        
        return setup.run_setup(show_dialog=show_gui)
    
    return True


if __name__ == "__main__":
    # Test the setup process
    success = run_first_time_setup_if_needed()
    if success:
        print("Setup completed successfully!")
    else:
        print("Setup failed!")
        sys.exit(1) 