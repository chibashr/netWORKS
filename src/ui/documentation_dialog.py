#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Documentation dialog for NetWORKS
"""

import os
import markdown
from loguru import logger
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTreeWidget,
    QTreeWidgetItem, QSplitter, QTextBrowser, QWidget, QComboBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon


class DocumentationDialog(QDialog):
    """Dialog showing program documentation"""
    
    def __init__(self, parent=None):
        """Initialize the dialog"""
        super().__init__(parent)
        
        # Set dialog properties
        self.setWindowTitle("NetWORKS Documentation")
        self.resize(900, 600)
        
        # Create layouts
        self.layout = QVBoxLayout(self)
        
        # Create splitter for navigation and content
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        
        # Create navigation panel
        self.nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create topic selector combo box
        self.topic_selector = QComboBox()
        self.topic_selector.addItem("User Guide", "user")
        self.topic_selector.addItem("API Documentation", "api")
        self.topic_selector.addItem("Plugin Development", "plugins")
        self.topic_selector.currentIndexChanged.connect(self.on_topic_changed)
        
        # Create document tree
        self.doc_tree = QTreeWidget()
        self.doc_tree.setHeaderHidden(True)
        self.doc_tree.setMinimumWidth(200)
        self.doc_tree.itemClicked.connect(self.on_tree_item_clicked)
        
        self.nav_layout.addWidget(self.topic_selector)
        self.nav_layout.addWidget(self.doc_tree)
        
        # Create content panel
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        
        # Add widgets to splitter
        self.splitter.addWidget(self.nav_widget)
        self.splitter.addWidget(self.content_browser)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        
        # Add splitter to main layout
        self.layout.addWidget(self.splitter)
        
        # Create buttons
        self.button_layout = QHBoxLayout()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.close_button)
        
        # Add buttons to main layout
        self.layout.addLayout(self.button_layout)
        
        # Initialize documentation
        self.docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs")
        self.current_topic = "user"
        self.load_documentation_tree()
        
    def load_documentation_tree(self):
        """Load the documentation tree based on the selected topic"""
        self.doc_tree.clear()
        
        if self.current_topic == "user":
            self.load_user_documentation()
        elif self.current_topic == "api":
            self.load_api_documentation()
        elif self.current_topic == "plugins":
            self.load_plugin_documentation()
            
        # Expand all items
        self.doc_tree.expandAll()
        
        # Select the first item
        if self.doc_tree.topLevelItemCount() > 0:
            first_item = self.doc_tree.topLevelItem(0)
            self.doc_tree.setCurrentItem(first_item)
            self.on_tree_item_clicked(first_item, 0)
        
    def load_user_documentation(self):
        """Load user documentation tree"""
        # General documentation
        self.add_doc_item("Introduction", os.path.join(self.docs_path, "README.md"))
        self.add_doc_item("Getting Started", os.path.join(self.docs_path, "index.md"))
        
        # Workspaces
        workspaces_item = QTreeWidgetItem(["Workspaces"])
        self.doc_tree.addTopLevelItem(workspaces_item)
        self.add_doc_item("Managing Workspaces", os.path.join(self.docs_path, "workspaces.md"), workspaces_item)
    
    def load_api_documentation(self):
        """Load API documentation tree"""
        # API Root
        api_path = os.path.join(self.docs_path, "api")
        self.add_doc_item("API Overview", os.path.join(api_path, "README.md"))
        
        # Core API
        core_item = QTreeWidgetItem(["Core API"])
        self.doc_tree.addTopLevelItem(core_item)
        self.add_doc_item("Core Components", os.path.join(api_path, "core.md"), core_item)
        
        # UI API
        ui_item = QTreeWidgetItem(["UI API"])
        self.doc_tree.addTopLevelItem(ui_item)
        self.add_doc_item("UI Components", os.path.join(api_path, "ui.md"), ui_item)
        
        # Signals
        signals_item = QTreeWidgetItem(["Signals"])
        self.doc_tree.addTopLevelItem(signals_item)
        self.add_doc_item("Signal Documentation", os.path.join(api_path, "signals.md"), signals_item)

    def load_plugin_documentation(self):
        """Load plugin documentation tree"""
        # Plugin Root
        plugins_path = os.path.join(self.docs_path, "plugins")
        self.add_doc_item("Plugin Overview", os.path.join(plugins_path, "README.md"))
        
        # Look for additional plugin documentation files
        for filename in os.listdir(plugins_path):
            filepath = os.path.join(plugins_path, filename)
            if os.path.isfile(filepath) and filename.endswith('.md') and filename != "README.md":
                # Create readable name from filename
                name = filename[:-3].replace('_', ' ').title()
                self.add_doc_item(name, filepath)
    
    def add_doc_item(self, name, filepath, parent=None):
        """Add a documentation item to the tree"""
        if not os.path.exists(filepath):
            return None
            
        item = QTreeWidgetItem([name])
        item.setData(0, Qt.UserRole, filepath)
        
        if parent:
            parent.addChild(item)
        else:
            self.doc_tree.addTopLevelItem(item)
            
        return item
    
    def on_tree_item_clicked(self, item, column):
        """Handle tree item clicked"""
        filepath = item.data(0, Qt.UserRole)
        if filepath and os.path.exists(filepath):
            self.display_markdown_file(filepath)
    
    def on_topic_changed(self, index):
        """Handle topic selection changed"""
        self.current_topic = self.topic_selector.currentData()
        self.load_documentation_tree()
    
    def display_markdown_file(self, filepath):
        """Display markdown file in the content browser"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
                
            # Convert relative paths in images to absolute paths
            # This is needed for correctly displaying images in the documentation
            doc_dir = os.path.dirname(filepath)
            
            # Convert markdown to HTML
            html = markdown.markdown(
                markdown_text,
                extensions=['tables', 'fenced_code', 'codehilite']
            )
            
            # Apply custom styling
            styled_html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
                    h1, h2, h3, h4 {{ color: #2c3e50; }}
                    pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; }}
                    code {{ background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ text-align: left; padding: 8px; border: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                </style>
            </head>
            <body>
                {html}
            </body>
            </html>
            """
            
            self.content_browser.setHtml(styled_html)
            
        except Exception as e:
            logger.error(f"Error displaying markdown file: {e}")
            self.content_browser.setHtml(f"<h1>Error</h1><p>Failed to load documentation: {e}</p>") 