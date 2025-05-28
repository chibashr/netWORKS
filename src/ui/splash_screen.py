#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Splash screen for NetWORKS
"""

from PySide6.QtWidgets import QSplashScreen, QProgressBar, QLabel, QVBoxLayout, QWidget
from PySide6.QtGui import QPixmap, QColor, QPainter, QFont
from PySide6.QtCore import Qt, QSize, QRect
from loguru import logger
import os
import json


class SplashScreen(QSplashScreen):
    """Splash screen shown during application startup"""
    
    def __init__(self):
        """Initialize the splash screen"""
        logger.debug("Initializing splash screen")
        
        # Read version from manifest
        version = self._get_version_from_manifest()
        
        # Create a pixmap for the splash screen
        splash_size = QSize(600, 400)
        pixmap = QPixmap(splash_size)
        pixmap.fill(Qt.white)
        
        # Create a painter to draw on the pixmap
        painter = QPainter(pixmap)
        
        # Set background color
        painter.fillRect(QRect(0, 0, splash_size.width(), splash_size.height()), QColor(240, 240, 240))
        
        # Draw the application name
        title_font = QFont("Arial", 40, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(0, 0, 0))  # Changed to black for better visibility
        painter.drawText(QRect(0, 50, splash_size.width(), 100), Qt.AlignCenter, "NetWORKS")
        
        # Draw subtitle
        subtitle_font = QFont("Arial", 14)
        painter.setFont(subtitle_font)
        painter.setPen(QColor(60, 60, 60))  # Dark gray for subtitle
        painter.drawText(QRect(0, 120, splash_size.width(), 50), Qt.AlignCenter, "Device Management Platform")
        
        # Draw version
        version_font = QFont("Arial", 10)
        painter.setFont(version_font)
        painter.setPen(QColor(80, 80, 80))  # Medium gray for version
        painter.drawText(QRect(0, splash_size.height() - 80, splash_size.width(), 20), Qt.AlignCenter, f"Version {version}")
        
        # Finish painting
        painter.end()
        
        super().__init__(pixmap)
        
        # Create a widget to hold the progress bar and status label
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 10, 40, 20)
        
        # Create status label
        self.status_label = QLabel("Starting...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #000000; font-size: 12px; background: transparent;")
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 3px;
            }
        """)
        
        # Add widgets to layout
        self.content_layout.addWidget(self.status_label)
        self.content_layout.addWidget(self.progress_bar)
        
        # Position the content widget only at the bottom portion
        content_height = 60
        self.content_widget.setGeometry(0, splash_size.height() - content_height, splash_size.width(), content_height)
        self.content_widget.setStyleSheet("background: transparent;")
        
        logger.debug("Splash screen initialized")

    def _get_version_from_manifest(self):
        """Read version from manifest.json file"""
        try:
            # Get the path to the manifest file (relative to the project root)
            manifest_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "manifest.json")
            
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    return manifest.get('version', '0.1.0')
            else:
                logger.warning(f"Manifest file not found at {manifest_path}")
                return '0.1.0'
        except Exception as e:
            logger.error(f"Error reading version from manifest: {e}")
            return '0.1.0'

    def update_progress(self, percentage=None, message=None, current_step=None, total_steps=None):
        """
        Update the progress bar and status message
        
        Can be called in two ways:
        1. update_progress(percentage, message)
        2. update_progress(message, current_step, total_steps)  # Legacy format
        """
        # Handle the case where the method is called with the legacy format
        if percentage is not None and message is None and current_step is not None and total_steps is not None:
            # Old format: update_progress(message, current_step, total_steps)
            message = percentage
            percentage = int((current_step / total_steps) * 100)
        
        # Update progress bar if percentage provided
        if percentage is not None:
            self.progress_bar.setValue(percentage)
        
        # Update message if provided
        if message is not None:
            self.status_label.setText(message)
            
        # Force a repaint to update the display
        self.repaint()
        
        # Log the progress update
        if message:
            logger.debug(f"Splash progress: {self.progress_bar.value()}% - {message}")
        else:
            logger.debug(f"Splash progress: {self.progress_bar.value()}%")

    def mousePressEvent(self, event):
        """Prevent closing the splash screen when clicked"""
        pass 