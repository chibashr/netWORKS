#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
About dialog for NetWORKS
"""

from loguru import logger
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit,
    QTabWidget, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap


class AboutDialog(QDialog):
    """Dialog showing information about the application"""
    
    def __init__(self, app, parent=None):
        """Initialize the dialog"""
        super().__init__(parent)
        self.app = app
        
        # Set dialog properties
        self.setWindowTitle("About NetWORKS")
        self.resize(600, 400)
        
        # Create layouts
        self.layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # About tab
        self.about_tab = QWidget()
        self.about_layout = QVBoxLayout(self.about_tab)
        
        # Header with app name and version
        app_version = self.app.get_version()
        self.header_label = QLabel(f"<h1>NetWORKS v{app_version}</h1>")
        self.header_label.setAlignment(Qt.AlignCenter)
        
        # App description
        app_description = self.app.config.get("application.description", "Network management and monitoring tool")
        self.description_label = QLabel(app_description)
        self.description_label.setAlignment(Qt.AlignCenter)
        self.description_label.setWordWrap(True)
        
        # App information
        self.info_layout = QVBoxLayout()
        
        self.author_label = QLabel(f"<b>Author:</b> {self.app.config.get('application.author', 'NetWORKS Team')}")
        self.author_label.setAlignment(Qt.AlignCenter)
        
        self.license_label = QLabel(f"<b>License:</b> {self.app.config.get('application.license', 'MIT')}")
        self.license_label.setAlignment(Qt.AlignCenter)
        
        self.build_date_label = QLabel(f"<b>Build Date:</b> {self.app.config.get('application.build_date', '')}")
        self.build_date_label.setAlignment(Qt.AlignCenter)
        
        self.info_layout.addWidget(self.author_label)
        self.info_layout.addWidget(self.license_label)
        self.info_layout.addWidget(self.build_date_label)
        
        # Add widgets to about layout
        self.about_layout.addWidget(self.header_label)
        self.about_layout.addWidget(self.description_label)
        self.about_layout.addLayout(self.info_layout)
        self.about_layout.addStretch()
        
        # Changelog tab
        self.changelog_tab = QWidget()
        self.changelog_layout = QVBoxLayout(self.changelog_tab)
        
        self.changelog_label = QLabel("<h2>Version History</h2>")
        self.changelog_label.setAlignment(Qt.AlignCenter)
        
        self.changelog_text = QTextEdit()
        self.changelog_text.setReadOnly(True)
        
        # Get changelog from app
        changelog = self.app.config.get("application.version_history", [])
        changelog_text = "\n\n".join(changelog)
        self.changelog_text.setText(changelog_text)
        
        self.changelog_layout.addWidget(self.changelog_label)
        self.changelog_layout.addWidget(self.changelog_text)
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.about_tab, "About")
        self.tab_widget.addTab(self.changelog_tab, "Changelog")
        
        # Buttons
        self.button_layout = QHBoxLayout()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.close_button)
        
        # Add tab widget and buttons to main layout
        self.layout.addWidget(self.tab_widget)
        self.layout.addLayout(self.button_layout) 