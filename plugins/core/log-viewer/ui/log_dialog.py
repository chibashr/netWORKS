#!/usr/bin/env python3
# Log Viewer Dialog

import os
import sys
import logging
import datetime
from typing import Dict, List, Optional, Any, Union

from PySide6.QtCore import Qt, QSortFilterProxyModel, QRegularExpression, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTableView, QHeaderView, QFileDialog, QMessageBox,
    QDateEdit, QFrame, QSplitter, QTextEdit, QProgressDialog, QApplication
)

# Set up logging for this module
logger = logging.getLogger(__name__)

def init_logging():
    """Initialize logging if not already set up."""
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        # Add a console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        logger.debug("Log dialog logging initialized")

# Initialize logging
init_logging()

class LogFilterProxyModel(QSortFilterProxyModel):
    """Filter model for log entries."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level_filter = ""
        self.source_filter = ""
        self.source_exact = ""
        self.plugin_filter = ""
        self.message_filter = ""
        self.date_from = None
        self.date_to = None
        
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Determine if a row should be accepted based on the filter criteria."""
        try:
            model = self.sourceModel()
            
            # Check level filter
            if self.level_filter:
                level_idx = model.index(source_row, 2, source_parent)
                if not level_idx.isValid():
                    return False
                level = model.data(level_idx)
                if level != self.level_filter:
                    return False
            
            # Get source for both source_exact and plugin filter
            source_idx = model.index(source_row, 1, source_parent)
            if not source_idx.isValid():
                return False
            source = model.data(source_idx)
            
            # Check exact source filter
            if self.source_exact and self.source_exact != "All Sources":
                if source != self.source_exact:
                    return False
            
            # Check plugin filter
            if self.plugin_filter and self.plugin_filter != "All Plugins":
                # Determine if source is from the filtered plugin
                plugin_match = False
                if '_' in source:
                    parts = source.split('_')
                    if len(parts) >= 2 and parts[0] == 'plugin':
                        plugin_name = '_'.join(parts[1:])
                        if plugin_name == self.plugin_filter:
                            plugin_match = True
                
                if not plugin_match:
                    return False
            
            # Check source filter (text-based)
            if self.source_filter:
                if not self.source_filter.lower() in source.lower():
                    return False
            
            # Check message filter
            if self.message_filter:
                message_idx = model.index(source_row, 3, source_parent)
                if not message_idx.isValid():
                    return False
                message = model.data(message_idx)
                if not self.message_filter.lower() in message.lower():
                    return False
            
            # Check date filters
            if self.date_from or self.date_to:
                timestamp_idx = model.index(source_row, 0, source_parent)
                if not timestamp_idx.isValid():
                    return False
                timestamp_str = model.data(timestamp_idx)
                
                try:
                    # Extract date part (remove milliseconds)
                    timestamp_str = timestamp_str.split(',')[0]
                    timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    
                    if self.date_from and timestamp.date() < self.date_from.date():
                        return False
                    
                    if self.date_to and timestamp.date() > self.date_to.date():
                        return False
                except (ValueError, AttributeError, IndexError) as e:
                    logger.warning(f"Date filtering error: {str(e)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in filter: {str(e)}", exc_info=True)
            return False
        
    def set_level_filter(self, level):
        """Set level filter."""
        self.level_filter = level
        self.invalidateFilter()
        
    def set_source_filter(self, source):
        """Set source text filter."""
        self.source_filter = source
        self.invalidateFilter()
        
    def set_source_exact(self, source):
        """Set exact source filter."""
        self.source_exact = source
        self.invalidateFilter()
        
    def set_plugin_filter(self, plugin):
        """Set plugin filter."""
        self.plugin_filter = plugin
        self.invalidateFilter()
        
    def set_message_filter(self, message):
        """Set message filter."""
        self.message_filter = message
        self.invalidateFilter()
        
    def set_date_range(self, date_from, date_to):
        """Set date range filter."""
        self.date_from = date_from
        self.date_to = date_to
        self.invalidateFilter()


class LogViewerDialog(QDialog):
    """Dialog for viewing, filtering and downloading log entries."""
    
    def __init__(self, plugin):
        """Initialize the dialog.
        
        Args:
            plugin: The log viewer plugin instance
        """
        try:
            # Get parent window from plugin if available
            parent = None
            if hasattr(plugin, 'api') and hasattr(plugin.api, 'main_window'):
                parent = plugin.api.main_window
                logger.debug(f"Using main window as parent: {parent}")
            
            super().__init__(parent)
            logger.debug("Initializing LogViewerDialog")
            
            self.plugin = plugin
            self.logs = []
            self.selected_log = None
            
            # Set up the dialog UI
            self.setup_ui()
            
            # Set up the model and proxy
            self.model = QStandardItemModel(self)
            self.model.setHorizontalHeaderLabels(["Timestamp", "Source", "Level", "Message"])
            
            self.proxy_model = LogFilterProxyModel(self)
            self.proxy_model.setSourceModel(self.model)
            self.logs_table.setModel(self.proxy_model)
            
            # Load logs
            self.load_logs()
            
            # Connect signals
            self.logs_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
            self.level_combo.currentTextChanged.connect(self.apply_filters)
            self.source_combo.currentTextChanged.connect(self.apply_filters)
            self.plugin_combo.currentTextChanged.connect(self.apply_filters)
            self.source_filter.textChanged.connect(self.apply_filters)
            self.message_filter.textChanged.connect(self.apply_filters)
            self.date_from.dateChanged.connect(self.apply_filters)
            self.date_to.dateChanged.connect(self.apply_filters)
            self.download_button.clicked.connect(self.download_logs)
            self.refresh_button.clicked.connect(self.load_logs)
            self.fix_structure_button.clicked.connect(self.fix_log_structure)
            
            # Set window modality and other properties
            self.setWindowModality(Qt.ApplicationModal)
            self.setAttribute(Qt.WA_DeleteOnClose, False)  # Don't delete when closed
            
            logger.debug("LogViewerDialog initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing LogViewerDialog: {str(e)}", exc_info=True)
            QMessageBox.critical(None, "Error", f"Failed to initialize log viewer: {str(e)}")
            
    def setup_ui(self):
        """Set up the dialog UI."""
        try:
            logger.debug("Setting up UI")
            
            # Set window properties
            self.setWindowTitle("Log Viewer")
            self.resize(900, 600)
            self.setMinimumSize(700, 500)
            
            # Create main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # Create filters frame
            filters_frame = QFrame()
            filters_frame.setFrameShape(QFrame.StyledPanel)
            filters_layout = QVBoxLayout(filters_frame)
            
            # Create filters title
            filters_title = QLabel("Filters")
            font = QFont()
            font.setBold(True)
            filters_title.setFont(font)
            filters_layout.addWidget(filters_title)
            
            # Create filter controls layout (upper row)
            filter_controls_upper = QHBoxLayout()
            
            # Level filter
            level_label = QLabel("Level:")
            self.level_combo = QComboBox()
            self.level_combo.addItem("All")
            self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
            filter_controls_upper.addWidget(level_label)
            filter_controls_upper.addWidget(self.level_combo)
            filter_controls_upper.addSpacing(10)
            
            # Source dropdown filter (new)
            source_label = QLabel("Source:")
            self.source_combo = QComboBox()
            self.source_combo.addItem("All Sources")
            self.source_combo.setMinimumWidth(150)
            filter_controls_upper.addWidget(source_label)
            filter_controls_upper.addWidget(self.source_combo)
            filter_controls_upper.addSpacing(10)
            
            # Plugin dropdown filter (new)
            plugin_label = QLabel("Plugin:")
            self.plugin_combo = QComboBox()
            self.plugin_combo.addItem("All Plugins")
            self.plugin_combo.setMinimumWidth(150)
            filter_controls_upper.addWidget(plugin_label)
            filter_controls_upper.addWidget(self.plugin_combo)
            
            filters_layout.addLayout(filter_controls_upper)
            
            # Create filter controls layout (lower row)
            filter_controls_lower = QHBoxLayout()
            
            # Source text filter (kept for convenience)
            source_filter_label = QLabel("Source Filter:")
            self.source_filter = QLineEdit()
            self.source_filter.setPlaceholderText("Filter by source")
            filter_controls_lower.addWidget(source_filter_label)
            filter_controls_lower.addWidget(self.source_filter)
            filter_controls_lower.addSpacing(10)
            
            # Message filter
            message_label = QLabel("Message:")
            self.message_filter = QLineEdit()
            self.message_filter.setPlaceholderText("Filter by message content")
            filter_controls_lower.addWidget(message_label)
            filter_controls_lower.addWidget(self.message_filter)
            
            filters_layout.addLayout(filter_controls_lower)
            
            # Date range filter
            date_layout = QHBoxLayout()
            date_from_label = QLabel("From:")
            self.date_from = QDateEdit()
            self.date_from.setCalendarPopup(True)
            self.date_from.setDate(datetime.date.today() - datetime.timedelta(days=7))
            
            date_to_label = QLabel("To:")
            self.date_to = QDateEdit()
            self.date_to.setCalendarPopup(True)
            self.date_to.setDate(datetime.date.today())
            
            date_layout.addWidget(date_from_label)
            date_layout.addWidget(self.date_from)
            date_layout.addSpacing(10)
            date_layout.addWidget(date_to_label)
            date_layout.addWidget(self.date_to)
            date_layout.addStretch()
            
            # Add refresh button
            self.refresh_button = QPushButton("Refresh")
            date_layout.addWidget(self.refresh_button)
            
            # Add fix structure button
            self.fix_structure_button = QPushButton("Fix Structure")
            self.fix_structure_button.setToolTip("Fix logs where source and level fields are swapped")
            date_layout.addWidget(self.fix_structure_button)
            
            # Add download button
            self.download_button = QPushButton("Download Logs")
            date_layout.addWidget(self.download_button)
            
            filters_layout.addLayout(date_layout)
            
            # Add filters to main layout
            main_layout.addWidget(filters_frame)
            
            # Create splitter for table and details
            splitter = QSplitter(Qt.Vertical)
            splitter.setChildrenCollapsible(False)
            
            # Create logs table
            self.logs_table = QTableView()
            self.logs_table.setSelectionBehavior(QTableView.SelectRows)
            self.logs_table.setSelectionMode(QTableView.SingleSelection)
            self.logs_table.setSortingEnabled(True)
            self.logs_table.verticalHeader().setVisible(False)
            self.logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            self.logs_table.horizontalHeader().setStretchLastSection(True)
            splitter.addWidget(self.logs_table)
            
            # Create detail view
            detail_frame = QFrame()
            detail_layout = QVBoxLayout(detail_frame)
            
            detail_label = QLabel("Details")
            detail_label.setFont(font)
            detail_layout.addWidget(detail_label)
            
            self.detail_text = QTextEdit()
            self.detail_text.setReadOnly(True)
            detail_layout.addWidget(self.detail_text)
            
            splitter.addWidget(detail_frame)
            
            # Set initial splitter sizes (2:1 ratio)
            splitter.setSizes([400, 200])
            
            main_layout.addWidget(splitter)
            
            logger.debug("UI setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up UI: {str(e)}", exc_info=True)
            raise
    
    def load_logs(self):
        """Load logs from the plugin."""
        try:
            logger.debug("Loading logs")
            
            # Show a progress dialog
            progress = QProgressDialog("Loading logs...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(500)  # Show after 500ms
            progress.setValue(10)
            
            # Clear existing model
            self.model.removeRows(0, self.model.rowCount())
            
            # Get logs from plugin
            if hasattr(self.plugin, 'get_logs') and callable(self.plugin.get_logs):
                progress.setValue(30)
                self.logs = self.plugin.get_logs()
                progress.setValue(60)
            else:
                logger.error("Plugin does not have a valid get_logs method")
                QMessageBox.critical(self, "Error", "The plugin does not provide a valid method to retrieve logs.")
                progress.cancel()
                return
            
            # Extract unique sources for the source selection dropdown
            unique_sources = set()
            unique_plugins = set()
                
            # Add logs to model
            for log in self.logs:
                # Extract timestamp, source, level, and message
                timestamp = log.get("timestamp", "")
                source = log.get("source", "")
                level = log.get("level", "")
                message = log.get("message", "")
                
                # Clean up source data - fix any parsing issues
                if '_' in source:  # Handle plugin_name format
                    parts = source.split('_')
                    if len(parts) >= 2 and parts[0] == 'plugin':
                        # This is a plugin log, extract the plugin name
                        plugin_name = '_'.join(parts[1:])
                        unique_plugins.add(plugin_name)
                
                # Add to unique sources set
                unique_sources.add(source)
                
                # Create items for the row
                items = [
                    QStandardItem(timestamp),
                    QStandardItem(source),
                    QStandardItem(level),
                    QStandardItem(message)
                ]
                
                # Set colors based on level with more distinctive colors
                if level == "ERROR" or level == "CRITICAL":
                    color = QColor(255, 150, 150)  # Stronger red
                    font = QFont()
                    font.setBold(True)
                    for item in items:
                        item.setBackground(color)
                        item.setFont(font)
                elif level == "WARNING":
                    color = QColor(255, 220, 150)  # Orange-yellow
                    for item in items:
                        item.setBackground(color)
                elif level == "INFO":
                    color = QColor(200, 255, 200)  # Light green
                    for item in items:
                        item.setBackground(color)
                elif level == "DEBUG":
                    color = QColor(220, 220, 255)  # Light blue
                    for item in items:
                        item.setBackground(color)
                
                self.model.appendRow(items)
                
                # Update progress periodically
                if self.model.rowCount() % 100 == 0:
                    progress.setValue(60 + min(30, int(self.model.rowCount() / len(self.logs) * 30)))
                    QApplication.processEvents()
                    
                    if progress.wasCanceled():
                        break
            
            # Update source filter with unique sources
            progress.setValue(95)
            self.update_source_filters(unique_sources, unique_plugins)
            
            # Resize columns to content
            self.logs_table.resizeColumnsToContents()
            
            # Sort by timestamp descending (most recent first)
            self.logs_table.sortByColumn(0, Qt.DescendingOrder)
            
            progress.setValue(100)
            logger.debug(f"Loaded {len(self.logs)} logs")
            
        except Exception as e:
            logger.error(f"Error loading logs: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load logs: {str(e)}")
            
    def update_source_filters(self, unique_sources, unique_plugins):
        """Update source and plugin filter dropdowns."""
        try:
            # Update source dropdown
            self.source_combo.clear()
            self.source_combo.addItem("All Sources")
            for source in sorted(unique_sources):
                self.source_combo.addItem(source)
                
            # Update plugin dropdown
            self.plugin_combo.clear()
            self.plugin_combo.addItem("All Plugins")
            for plugin in sorted(unique_plugins):
                self.plugin_combo.addItem(plugin)
        except Exception as e:
            logger.error(f"Error updating source filters: {str(e)}", exc_info=True)
    
    def apply_filters(self):
        """Apply filters to the logs."""
        try:
            logger.debug("Applying filters")
            
            # Get filter values
            level = self.level_combo.currentText()
            source_exact = self.source_combo.currentText()
            plugin = self.plugin_combo.currentText()
            source = self.source_filter.text()
            message = self.message_filter.text()
            date_from = self.date_from.date()
            date_to = self.date_to.date()
            
            # Apply to proxy model
            if level == "All":
                self.proxy_model.set_level_filter("")
            else:
                self.proxy_model.set_level_filter(level)
            
            # Apply all filter types    
            self.proxy_model.set_source_exact(source_exact)
            self.proxy_model.set_plugin_filter(plugin)
            self.proxy_model.set_source_filter(source)
            self.proxy_model.set_message_filter(message)
            self.proxy_model.set_date_range(self.date_from, self.date_to)
            
            logger.debug(f"Applied filters - visible rows: {self.proxy_model.rowCount()}")
            
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to apply filters: {str(e)}")
    
    def on_selection_changed(self):
        """Handle selection change in the logs table."""
        try:
            logger.debug("Selection changed")
            
            # Get selected row
            indexes = self.logs_table.selectionModel().selectedRows()
            if not indexes:
                self.detail_text.clear()
                self.selected_log = None
                return
                
            # Get original index from proxy model
            proxy_index = indexes[0]
            source_index = self.proxy_model.mapToSource(proxy_index)
            row = source_index.row()
            
            # Get log data
            if row >= 0 and row < len(self.logs):
                log = self.logs[row]
                self.selected_log = log
                
                # Format detail text
                detail = f"Timestamp: {log.get('timestamp', '')}\n"
                detail += f"Source: {log.get('source', '')}\n"
                detail += f"Level: {log.get('level', '')}\n"
                detail += f"Message: {log.get('message', '')}\n\n"
                
                # Add exception if exists
                if log.get("exception"):
                    detail += "Exception:\n" + log.get("exception")
                
                self.detail_text.setText(detail)
                logger.debug(f"Selected log: {log.get('timestamp', '')} - {log.get('level', '')}")
            else:
                self.detail_text.clear()
                self.selected_log = None
                
        except Exception as e:
            logger.error(f"Error handling selection change: {str(e)}", exc_info=True)
            # Don't show message box here as it could interrupt user workflow
            self.detail_text.setText(f"Error displaying log details: {str(e)}")
    
    def download_logs(self):
        """Download filtered logs to a file."""
        try:
            logger.debug("Downloading logs")
            
            # Get filtered logs
            filtered_logs = []
            for row in range(self.proxy_model.rowCount()):
                proxy_index = self.proxy_model.index(row, 0)
                source_index = self.proxy_model.mapToSource(proxy_index)
                source_row = source_index.row()
                
                if source_row >= 0 and source_row < len(self.logs):
                    filtered_logs.append(self.logs[source_row])
            
            if not filtered_logs:
                QMessageBox.warning(self, "No Logs", "There are no logs to download with the current filter settings.")
                return
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Logs",
                os.path.expanduser("~/logs_export.txt"),
                "Text Files (*.txt);;All Files (*.*)"
            )
            
            if not file_path:
                return
                
            # Save logs
            if self.plugin.download_logs(filtered_logs, file_path):
                QMessageBox.information(
                    self,
                    "Success",
                    f"Successfully exported {len(filtered_logs)} logs to {file_path}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save logs to {file_path}"
                )
                
            logger.debug(f"Exported {len(filtered_logs)} logs to {file_path}")
            
        except Exception as e:
            logger.error(f"Error downloading logs: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to download logs: {str(e)}")

    def fix_log_structure(self):
        """Fix the log structure by swapping source and level fields for all visible logs."""
        try:
            logger.debug("Fixing log structure - swapping source and level fields")
            
            # Show confirmation dialog
            result = QMessageBox.question(
                self,
                "Fix Log Structure",
                "This will swap source and level fields for all visible logs. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if result != QMessageBox.Yes:
                return
                
            # Count how many rows are visible
            row_count = self.proxy_model.rowCount()
            if row_count == 0:
                QMessageBox.information(self, "No Logs", "No logs visible to fix.")
                return
            
            # Swap source and level in the model
            for row in range(self.model.rowCount()):
                source_item = self.model.item(row, 1)  # Source column
                level_item = self.model.item(row, 2)   # Level column
                
                if source_item and level_item:
                    # Swap the data
                    source_value = source_item.text()
                    level_value = level_item.text()
                    
                    # Validate that swap is needed (source contains level-like data)
                    if source_value in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                        source_item.setText(level_value)
                        level_item.setText(source_value)
                        
                        # Also update the underlying data
                        if row < len(self.logs):
                            self.logs[row]["source"], self.logs[row]["level"] = self.logs[row]["level"], self.logs[row]["source"]
            
            # Reset colors based on (now corrected) level
            for row in range(self.model.rowCount()):
                level_item = self.model.item(row, 2)  # Level column
                
                if level_item:
                    level = level_item.text()
                    items = [
                        self.model.item(row, 0),  # Timestamp
                        self.model.item(row, 1),  # Source
                        level_item,               # Level
                        self.model.item(row, 3)   # Message
                    ]
                    
                    # Reset background to default
                    for item in items:
                        if item:
                            item.setBackground(QColor(255, 255, 255))
                            font = QFont()
                            item.setFont(font)
                    
                    # Set colors based on level with more distinctive colors
                    if level == "ERROR" or level == "CRITICAL":
                        color = QColor(255, 150, 150)  # Stronger red
                        font = QFont()
                        font.setBold(True)
                        for item in items:
                            if item:
                                item.setBackground(color)
                                item.setFont(font)
                    elif level == "WARNING":
                        color = QColor(255, 220, 150)  # Orange-yellow
                        for item in items:
                            if item:
                                item.setBackground(color)
                    elif level == "INFO":
                        color = QColor(200, 255, 200)  # Light green
                        for item in items:
                            if item:
                                item.setBackground(color)
                    elif level == "DEBUG":
                        color = QColor(220, 220, 255)  # Light blue
                        for item in items:
                            if item:
                                item.setBackground(color)
            
            # Update unique sources and plugins
            unique_sources = set()
            unique_plugins = set()
            
            for log in self.logs:
                source = log.get("source", "")
                unique_sources.add(source)
                
                # Extract plugin name if applicable
                if '_' in source:
                    parts = source.split('_')
                    if len(parts) >= 2 and parts[0] == 'plugin':
                        plugin_name = '_'.join(parts[1:])
                        unique_plugins.add(plugin_name)
            
            # Update filter dropdowns
            self.update_source_filters(unique_sources, unique_plugins)
            
            QMessageBox.information(
                self,
                "Success",
                f"Successfully fixed structure for {row_count} log entries."
            )
            
            logger.debug(f"Fixed log structure for {row_count} entries")
            
        except Exception as e:
            logger.error(f"Error fixing log structure: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to fix log structure: {str(e)}")

# Notify that the module was loaded successfully
logger.debug("Log dialog module loaded successfully") 