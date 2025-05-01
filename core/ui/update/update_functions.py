"""
Update management functions for the netWORKS application.
These functions were extracted from main_window.py to improve modularity.
"""

import os
import json
import logging
import requests
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QMessageBox, QCheckBox, 
    QSpacerItem, QSizePolicy, QTextBrowser
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

# Setup logger
logger = logging.getLogger(__name__)

def check_for_updates(main_window):
    """Check for application updates."""
    try:
        # Skip update check if disabled in config
        if main_window.config.get("app", {}).get("disable_update_checks", False):
            main_window.logger.info("Update checks are disabled in configuration")
            return
        
        from core.version import check_for_updates, get_version_string
        
        # Get current version
        current_version = get_version_string()
        
        # Check for updates
        main_window.logger.info("Checking for updates...")
        update_available, update_info = check_for_updates()
        
        if update_available:
            # Log the update
            main_window.logger.info(f"Update available: {current_version} -> {update_info['version']}")
            
            # Show update dialog
            main_window.show_update_dialog(update_info)
        else:
            main_window.logger.info("No updates available")
            
    except Exception as e:
        main_window.logger.error(f"Error checking for updates: {str(e)}", exc_info=True)

def show_update_dialog(main_window, update_info):
    """Show the update dialog with update details.
    
    Args:
        update_info: Dictionary with update information
    """
    try:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextBrowser
        from PySide6.QtGui import QPixmap
        
        # Create dialog
        dialog = QDialog(main_window)
        dialog.setWindowTitle("Update Available")
        dialog.setMinimumWidth(600)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #333333;
            }
            QLabel[heading="true"] {
                font-size: 18px;
                font-weight: bold;
                color: #2c5aa0;
            }
            QTextBrowser {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                background-color: #f8f8f8;
            }
        """)
        
        # Layout
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        # Header with logo
        header_layout = QHBoxLayout()
        logo_label = QLabel()
        
        # Try to load logo
        try:
            logo_path = os.path.join("assets", "logo.png")
            if os.path.exists(logo_path):
                pixmap = QPixmap(logo_path)
                logo_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                logo_label.setText("netWORKS")
                logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c5aa0;")
        except Exception:
            logo_label.setText("netWORKS")
            logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c5aa0;")
        
        header_layout.addWidget(logo_label)
        
        # Update info
        header_text = QLabel()
        header_text.setProperty("heading", True)
        header_text.setText(f"Update Available: v{update_info['version']}")
        header_layout.addWidget(header_text)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Divider
        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(divider)
        
        # Version info
        from core.version import get_version_string
        version_info = QLabel(f"Current Version: v{get_version_string()}<br>New Version: v{update_info['version']}")
        layout.addWidget(version_info)
        
        # Plugin compatibility info
        if update_info.get('plugin_compatibility'):
            compat_label = QLabel("<h3>Plugin Compatibility:</h3>")
            layout.addWidget(compat_label)
            
            compat_browser = QTextBrowser()
            compat_browser.setMaximumHeight(100)
            
            # Format compatibility info
            if isinstance(update_info['plugin_compatibility'], dict):
                compat_text = f"<p>Minimum netWORKS version: {update_info['plugin_compatibility'].get('min_app_version', 'N/A')}</p>"
                
                affected_plugins = update_info['plugin_compatibility'].get('affected_plugins', [])
                if affected_plugins:
                    compat_text += "<p>Affected plugins:</p><ul>"
                    for plugin in affected_plugins:
                        compat_text += f"<li>{plugin}</li>"
                    compat_text += "</ul>"
                
                min_api = update_info['plugin_compatibility'].get('min_plugin_api', '')
                if min_api:
                    compat_text += f"<p>Minimum Plugin API version: {min_api}</p>"
            else:
                compat_text = f"<p>{update_info['plugin_compatibility']}</p>"
            
            compat_browser.setHtml(compat_text)
            layout.addWidget(compat_browser)
        
        # Release notes
        if update_info.get('release_notes'):
            notes_label = QLabel("<h3>What's New:</h3>")
            layout.addWidget(notes_label)
            
            notes_browser = QTextBrowser()
            notes_browser.setHtml(f"<p>{update_info['release_notes'].replace('- ', '• ')}</p>")
            layout.addWidget(notes_browser)
        
        # Download info
        download_label = QLabel(f"<p>To update, you need to download and install the latest version.</p>")
        layout.addWidget(download_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        button_layout.addItem(spacer)
        
        # Do not update button
        do_not_update_button = QPushButton("Do Not Update")
        do_not_update_button.setFixedWidth(150)
        do_not_update_button.clicked.connect(dialog.reject)
        button_layout.addWidget(do_not_update_button)
        
        # Update button
        update_button = QPushButton("Download Update")
        update_button.setFixedWidth(150)
        update_button.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #1c5a85;
            }
        """)
        update_button.clicked.connect(lambda: main_window.start_update_process(update_info, dialog))
        button_layout.addWidget(update_button)
        
        # Don't show again checkbox
        main_window.skip_updates_checkbox = QCheckBox("Don't check for updates automatically")
        layout.addWidget(main_window.skip_updates_checkbox)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        dialog.exec()
        
        # Handle checkbox result
        if hasattr(main_window, 'skip_updates_checkbox') and main_window.skip_updates_checkbox.isChecked():
            main_window.disable_update_reminders()
            
    except Exception as e:
        main_window.logger.error(f"Error showing update dialog: {str(e)}", exc_info=True)

def start_update_process(main_window, update_info, dialog=None):
    """Start the update process by opening the download URL."""
    try:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        # Open download URL in browser
        QDesktopServices.openUrl(QUrl(update_info['download_url']))
        
        # Show message that download is starting
        main_window.statusBar.showMessage("Opening download page in your browser...", 5000)
        
        # Close dialog if provided
        if dialog:
            dialog.accept()
            
    except Exception as e:
        main_window.logger.error(f"Error starting update process: {str(e)}", exc_info=True)
        main_window.show_error_dialog("Update Error", f"Failed to start update: {str(e)}")

def disable_update_reminders(main_window, dialog=None):
    """Disable update reminders by updating configuration."""
    try:
        if "app" not in main_window.config:
            main_window.config["app"] = {}
        
        main_window.config["app"]["disable_update_checks"] = True
        main_window.save_config()
        main_window.logger.info("Update reminders disabled")
        
        if dialog:
            dialog.accept()
            
    except Exception as e:
        main_window.logger.error(f"Error disabling update reminders: {str(e)}")
        if dialog:
            dialog.reject() 