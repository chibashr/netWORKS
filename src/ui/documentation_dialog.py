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
    QTreeWidgetItem, QSplitter, QTextBrowser, QWidget, QComboBox, QLineEdit
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
        self.resize(1000, 700)
        
        # Create layouts
        self.layout = QVBoxLayout(self)
        
        # Create header with search
        self._create_header()
        
        # Create splitter for navigation and content
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        
        # Create navigation panel
        self._create_navigation_panel()
        
        # Create content panel
        self._create_content_panel()
        
        # Add widgets to splitter
        self.splitter.addWidget(self.nav_widget)
        self.splitter.addWidget(self.content_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        
        # Add splitter to main layout
        self.layout.addWidget(self.splitter)
        
        # Create buttons
        self._create_buttons()
        
        # Initialize documentation
        self.docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs")
        self.current_topic = "user"
        self.current_file = None
        self.load_documentation_tree()
        
    def _create_header(self):
        """Create header with search functionality"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 8)
        
        # Title
        title_label = QLabel("Documentation")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2c2c2c;")
        header_layout.addWidget(title_label)
        
        # Search box
        header_layout.addStretch()
        search_label = QLabel("Search:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search documentation...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        self.search_edit.setMaximumWidth(250)
        
        header_layout.addWidget(search_label)
        header_layout.addWidget(self.search_edit)
        
        self.layout.addWidget(header_widget)
    
    def _create_navigation_panel(self):
        """Create enhanced navigation panel"""
        self.nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(0, 0, 4, 0)
        
        # Topic selector with improved styling
        topic_label = QLabel("Documentation Category:")
        topic_label.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
        self.nav_layout.addWidget(topic_label)
        
        self.topic_selector = QComboBox()
        self.topic_selector.addItem("📖 User Guide", "user")
        self.topic_selector.addItem("🔧 API Documentation", "api")
        self.topic_selector.addItem("🔌 Plugin Development", "plugins")
        self.topic_selector.addItem("❓ Troubleshooting", "troubleshooting")
        self.topic_selector.currentIndexChanged.connect(self.on_topic_changed)
        self.topic_selector.setStyleSheet("""
            QComboBox {
                padding: 6px;
                margin-bottom: 8px;
            }
        """)
        self.nav_layout.addWidget(self.topic_selector)
        
        # Document tree with improved styling
        tree_label = QLabel("Topics:")
        tree_label.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
        self.nav_layout.addWidget(tree_label)
        
        self.doc_tree = QTreeWidget()
        self.doc_tree.setHeaderHidden(True)
        self.doc_tree.setMinimumWidth(250)
        self.doc_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.doc_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QTreeWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #e0f0ff;
                color: #2c2c2c;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        self.nav_layout.addWidget(self.doc_tree)
        
        # Navigation buttons
        nav_buttons_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back")
        self.forward_button = QPushButton("Forward →")
        self.home_button = QPushButton("🏠 Home")
        
        self.back_button.setEnabled(False)
        self.forward_button.setEnabled(False)
        
        self.back_button.clicked.connect(self.go_back)
        self.forward_button.clicked.connect(self.go_forward)
        self.home_button.clicked.connect(self.go_home)
        
        nav_buttons_layout.addWidget(self.back_button)
        nav_buttons_layout.addWidget(self.forward_button)
        nav_buttons_layout.addWidget(self.home_button)
        
        self.nav_layout.addLayout(nav_buttons_layout)
        
        # Initialize navigation history
        self.nav_history = []
        self.nav_position = -1
    
    def _create_content_panel(self):
        """Create enhanced content panel"""
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(4, 0, 0, 0)
        
        # Content header
        content_header = QWidget()
        content_header_layout = QHBoxLayout(content_header)
        content_header_layout.setContentsMargins(0, 0, 0, 8)
        
        self.content_title = QLabel("Select a topic to view documentation")
        self.content_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #2c2c2c;")
        content_header_layout.addWidget(self.content_title)
        
        # Content tools
        content_header_layout.addStretch()
        self.print_button = QPushButton("🖨 Print")
        self.export_button = QPushButton("📄 Export")
        self.zoom_in_button = QPushButton("🔍+")
        self.zoom_out_button = QPushButton("🔍-")
        
        self.print_button.clicked.connect(self.print_content)
        self.export_button.clicked.connect(self.export_content)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        
        for btn in [self.print_button, self.export_button, self.zoom_in_button, self.zoom_out_button]:
            btn.setMaximumWidth(80)
            btn.setToolTip(btn.text().split(' ', 1)[-1])
            content_header_layout.addWidget(btn)
        
        content_layout.addWidget(content_header)
        
        # Content browser with enhanced styling
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #ffffff;
                font-family: "Segoe UI", "Roboto", sans-serif;
                font-size: 10pt;
                line-height: 1.5;
                padding: 12px;
            }
        """)
        
        content_layout.addWidget(self.content_browser)
        
        # Initialize zoom level
        self.zoom_level = 100
    
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
    
    def display_markdown_file(self, filepath, add_to_history=True):
        """Display a markdown file with enhanced rendering and navigation support"""
        if not os.path.exists(filepath):
            self.content_browser.setHtml("<h1>File Not Found</h1><p>The requested documentation file could not be found.</p>")
            self.content_title.setText("File Not Found")
            return
            
        try:
            # Add to navigation history
            if add_to_history:
                # Remove any history after current position
                self.nav_history = self.nav_history[:self.nav_position + 1]
                # Add new file to history
                self.nav_history.append(filepath)
                self.nav_position = len(self.nav_history) - 1
                self._update_nav_buttons()
            
            # Read the file
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Convert markdown to HTML with enhancements
            html_content = markdown.markdown(
                content, 
                extensions=['codehilite', 'tables', 'toc', 'fenced_code']
            )
            
            # Apply custom styling
            styled_html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', 'Roboto', sans-serif;
                        line-height: 1.6;
                        color: #2c2c2c;
                        max-width: none;
                        margin: 0;
                        padding: 0;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #2c2c2c;
                        border-bottom: 1px solid #e0e0e0;
                        padding-bottom: 0.3em;
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                    }}
                    h1 {{ font-size: 1.8em; }}
                    h2 {{ font-size: 1.5em; }}
                    h3 {{ font-size: 1.3em; }}
                    code {{
                        background-color: #f5f5f5;
                        padding: 2px 4px;
                        border-radius: 3px;
                        font-family: 'Consolas', 'Monaco', monospace;
                        font-size: 0.9em;
                    }}
                    pre {{
                        background-color: #f8f8f8;
                        border: 1px solid #e0e0e0;
                        border-radius: 4px;
                        padding: 12px;
                        overflow-x: auto;
                        margin: 1em 0;
                    }}
                    pre code {{
                        background-color: transparent;
                        padding: 0;
                    }}
                    blockquote {{
                        border-left: 4px solid #d0d0d0;
                        margin: 1em 0;
                        padding-left: 1em;
                        color: #606060;
                        font-style: italic;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 1em 0;
                    }}
                    th, td {{
                        border: 1px solid #d0d0d0;
                        padding: 8px 12px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f5f5f5;
                        font-weight: bold;
                    }}
                    a {{
                        color: #4a90e2;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                    ul, ol {{
                        padding-left: 2em;
                    }}
                    li {{
                        margin-bottom: 0.5em;
                    }}
                    .highlight {{
                        background-color: #fffacd;
                        padding: 2px 4px;
                        border-radius: 3px;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # Set the content
            self.content_browser.setHtml(styled_html)
            
            # Update content title
            filename = os.path.basename(filepath)
            self.content_title.setText(filename.replace('.md', '').replace('_', ' ').title())
            self.current_file = filepath
            
        except Exception as e:
            logger.error(f"Error displaying markdown file: {e}")
            error_html = f"""
            <html>
            <body>
                <h1>Error Loading Documentation</h1>
                <p>An error occurred while loading the documentation file:</p>
                <p><strong>File:</strong> {filepath}</p>
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Please check that the file exists and is readable.</p>
            </body>
            </html>
            """
            self.content_browser.setHtml(error_html)
            self.content_title.setText("Error")
    
    def _create_buttons(self):
        """Create dialog buttons"""
        self.button_layout = QHBoxLayout()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.close_button)
        
        # Add buttons to main layout
        self.layout.addLayout(self.button_layout)
    
    def on_search_text_changed(self, text):
        """Handle search text changes"""
        if not text.strip():
            # Show all items if search is empty
            self._show_all_tree_items()
            return
            
        # Hide all items first
        self._hide_all_tree_items()
        
        # Search through items and show matches
        search_terms = text.lower().split()
        self._search_tree_items(self.doc_tree.invisibleRootItem(), search_terms)
    
    def _show_all_tree_items(self):
        """Show all items in the tree"""
        iterator = QTreeWidgetItemIterator(self.doc_tree)
        while iterator.value():
            iterator.value().setHidden(False)
            iterator += 1
    
    def _hide_all_tree_items(self):
        """Hide all items in the tree"""
        iterator = QTreeWidgetItemIterator(self.doc_tree)
        while iterator.value():
            iterator.value().setHidden(True)
            iterator += 1
    
    def _search_tree_items(self, parent_item, search_terms):
        """Recursively search tree items"""
        from PySide6.QtWidgets import QTreeWidgetItemIterator
        
        # Check all child items
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            text = child.text(0).lower()
            
            # Check if any search term matches
            matches = any(term in text for term in search_terms)
            
            if matches:
                child.setHidden(False)
                # Show parent items too
                parent = child.parent()
                while parent:
                    parent.setHidden(False)
                    parent = parent.parent()
            
            # Recursively search children
            self._search_tree_items(child, search_terms)
    
    def go_back(self):
        """Navigate backwards in history"""
        if self.nav_position > 0:
            self.nav_position -= 1
            filepath = self.nav_history[self.nav_position]
            self.display_markdown_file(filepath, add_to_history=False)
            self._update_nav_buttons()
    
    def go_forward(self):
        """Navigate forwards in history"""
        if self.nav_position < len(self.nav_history) - 1:
            self.nav_position += 1
            filepath = self.nav_history[self.nav_position]
            self.display_markdown_file(filepath, add_to_history=False)
            self._update_nav_buttons()
    
    def go_home(self):
        """Go to first document in current topic"""
        if self.doc_tree.topLevelItemCount() > 0:
            first_item = self.doc_tree.topLevelItem(0)
            self.doc_tree.setCurrentItem(first_item)
            self.on_tree_item_clicked(first_item, 0)
    
    def _update_nav_buttons(self):
        """Update navigation button states"""
        self.back_button.setEnabled(self.nav_position > 0)
        self.forward_button.setEnabled(self.nav_position < len(self.nav_history) - 1)
    
    def print_content(self):
        """Print the current content"""
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            self.content_browser.print_(printer)
    
    def export_content(self):
        """Export content to file"""
        from PySide6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Documentation", "", 
            "HTML Files (*.html);;PDF Files (*.pdf);;Text Files (*.txt)"
        )
        if filename:
            if filename.endswith('.html'):
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.content_browser.toHtml())
            elif filename.endswith('.txt'):
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.content_browser.toPlainText())
            elif filename.endswith('.pdf'):
                # PDF export would require additional dependencies
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Export", "PDF export is not yet implemented.")
    
    def zoom_in(self):
        """Increase font size"""
        self.zoom_level = min(200, self.zoom_level + 10)
        self._apply_zoom()
    
    def zoom_out(self):
        """Decrease font size"""
        self.zoom_level = max(50, self.zoom_level - 10)
        self._apply_zoom()
    
    def _apply_zoom(self):
        """Apply current zoom level"""
        font = self.content_browser.font()
        font.setPointSizeF(10 * (self.zoom_level / 100.0))
        self.content_browser.setFont(font) 