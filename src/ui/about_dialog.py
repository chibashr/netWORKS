#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
About dialog for NetWORKS
"""

import json
import os
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
        self.resize(700, 500)
        
        # Create layouts
        self.layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # About tab
        self.about_tab = QWidget()
        self.about_layout = QVBoxLayout(self.about_tab)
        
        # Header with app name and full version (including build number)
        app_full_version = self.app.manifest.get("full_version", self.app.get_version())
        self.header_label = QLabel(f"<h1>NetWORKS v{app_full_version}</h1>")
        self.header_label.setAlignment(Qt.AlignCenter)
        
        # App description
        app_description = self.app.manifest.get("description", "Network management and monitoring tool")
        self.description_label = QLabel(app_description)
        self.description_label.setAlignment(Qt.AlignCenter)
        self.description_label.setWordWrap(True)
        
        # App information
        self.info_layout = QVBoxLayout()
        
        author = self.app.manifest.get("author", "NetWORKS Team")
        self.author_label = QLabel(f"<b>Author:</b> {author}")
        self.author_label.setAlignment(Qt.AlignCenter)
        
        license_info = self.app.manifest.get("license", "MIT")
        self.license_label = QLabel(f"<b>License:</b> {license_info}")
        self.license_label.setAlignment(Qt.AlignCenter)
        
        build_date = self.app.manifest.get("build_date", "")
        if build_date:
            self.build_date_label = QLabel(f"<b>Build Date:</b> {build_date}")
            self.build_date_label.setAlignment(Qt.AlignCenter)
        
        build_number = self.app.manifest.get("build_number", None)
        if build_number:
            self.build_number_label = QLabel(f"<b>Build Number:</b> {build_number}")
            self.build_number_label.setAlignment(Qt.AlignCenter)
        
        self.info_layout.addWidget(self.author_label)
        self.info_layout.addWidget(self.license_label)
        if build_date:
            self.info_layout.addWidget(self.build_date_label)
        if build_number:
            self.info_layout.addWidget(self.build_number_label)
        
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
        
        # Get changelog from manifest
        changelog = self.app.manifest.get("changelog", [])
        if changelog:
            changelog_html = self._format_changelog(changelog)
        else:
            changelog_html = "<p><i>No changelog available</i></p>"
        
        self.changelog_text.setHtml(changelog_html)
        
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
    
    def _format_changelog(self, changelog_data):
        """Format changelog data as HTML"""
        if not changelog_data:
            return "<p><i>No changelog available</i></p>"
        
        html_parts = []
        
        # Limit to the most recent 10 entries to avoid overwhelming the dialog
        recent_changelog = changelog_data[:10] if len(changelog_data) > 10 else changelog_data
        
        for entry in recent_changelog:
            if isinstance(entry, dict):
                version = entry.get("version", "Unknown")
                build = entry.get("build", "")
                date = entry.get("date", "")
                changes = entry.get("changes", [])
                
                # Format header
                header = f"<h3>Version {version}"
                if build:
                    header += f" (Build {build})"
                if date:
                    header += f" - {date}"
                header += "</h3>"
                
                html_parts.append(header)
                
                # Format changes
                if changes:
                    html_parts.append("<ul>")
                    for change in changes:
                        html_parts.append(f"<li>{change}</li>")
                    html_parts.append("</ul>")
                else:
                    html_parts.append("<p><i>No changes listed</i></p>")
                    
                html_parts.append("<hr>")
            elif isinstance(entry, str):
                # Handle old string format
                html_parts.append(f"<p>{entry}</p>")
        
        # Remove the last <hr> if present
        if html_parts and html_parts[-1] == "<hr>":
            html_parts.pop()
        
        return "".join(html_parts) 