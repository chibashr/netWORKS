#!/usr/bin/env python3
# Network Scanner - Bottom Panel UI

import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QHeaderView, QMenu, QMessageBox,
    QSizePolicy, QSpacerItem, QComboBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint, QSize
from PySide6.QtGui import QAction, QColor

class ScanHistoryPanel(QWidget):
    """Bottom panel UI component for displaying scan history."""
    
    def __init__(self, plugin):
        """Initialize the scan history panel.
        
        Args:
            plugin: The parent plugin instance
        """
        super().__init__()
        self.plugin = plugin
        self.logger = logging.getLogger(__name__)
        
        self.init_ui()
        self.connect_signals()
        self.update_scan_history()
    
    def init_ui(self):
        """Initialize the UI elements."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Control bar
        control_layout = QHBoxLayout()
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Scans", "all")
        self.filter_combo.addItem("Completed", "completed")
        self.filter_combo.addItem("Running", "running")
        self.filter_combo.addItem("Stopped", "stopped")
        self.filter_combo.addItem("Error", "error")
        self.filter_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d0dbe8;
                border-radius: 3px;
                padding: 4px 10px;
                background-color: white;
                min-height: 24px;
            }
            QComboBox:hover {
                border-color: #2c5aa0;
            }
            QComboBox:focus {
                border-color: #2c5aa0;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #d0dbe8;
            }
        """)
        
        control_layout.addWidget(QLabel("Filter:"))
        control_layout.addWidget(self.filter_combo)
        
        control_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Apply modern button styling to all buttons
        button_style = """
            QPushButton {
                background-color: #f0f4f8;
                border: 1px solid #d0dbe8;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: bold;
                color: #2c5aa0;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #e8f0ff;
                border-color: #2c5aa0;
            }
            QPushButton:pressed {
                background-color: #d0e0ff;
            }
            QPushButton:disabled {
                background-color: #f8f8f8;
                border-color: #e0e0e0;
                color: #a0a0a0;
            }
        """
        
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setStyleSheet(button_style)
        control_layout.addWidget(self.clear_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(button_style)
        control_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(control_layout)
        
        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Type", "Range", "Start Time", "End Time",
            "Devices Found", "Status", "Actions"
        ])
        
        # Configure table headers
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)  # Default size mode
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Let Range column stretch
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # Fixed size for Actions column
        header.setMinimumSectionSize(80)  # Set minimum width for columns
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Set better column widths
        self.table.setColumnWidth(0, 100)  # ID
        self.table.setColumnWidth(1, 120)  # Type
        # Column 2 (Range) will stretch
        self.table.setColumnWidth(3, 150)  # Start Time
        self.table.setColumnWidth(4, 150)  # End Time
        self.table.setColumnWidth(5, 100)  # Devices Found
        self.table.setColumnWidth(6, 100)  # Status
        self.table.setColumnWidth(7, 200)  # Actions - fixed width for buttons
        
        # Apply modern table styling to match device table
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e8f0;
                background-color: white;
                border: 1px solid #aabbcc;
                border-radius: 3px;
                selection-background-color: #e8f0ff;
                selection-color: #2c5aa0;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f4f8;
            }
            QTableWidget::item:selected {
                background-color: #e8f0ff;
                color: #2c5aa0;
            }
            QTableWidget::item:hover:!selected {
                background-color: #f5f9ff;
            }
            QTableWidget:focus {
                border: 1px solid #2c5aa0;
            }
            QTableWidget:alternate-background-color {
                background-color: #f8fbff;
            }
        """)
        
        # Style horizontal header
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f4f8;
                color: #2c5aa0;
                padding: 6px;
                border: none;
                border-right: 1px solid #d0dbe8;
                border-bottom: 1px solid #d0dbe8;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background-color: #e8f0ff;
            }
            QHeaderView::section:pressed {
                background-color: #d0e0ff;
            }
        """)
        
        layout.addWidget(self.table)
        
        # Summary label
        self.summary_label = QLabel("No scan history available")
        self.summary_label.setStyleSheet("color: #2c5aa0; font-weight: bold; padding: 5px;")
        layout.addWidget(self.summary_label)
    
    def connect_signals(self):
        """Connect UI signals to handlers."""
        # Button handlers
        self.clear_btn.clicked.connect(self.clear_history)
        self.refresh_btn.clicked.connect(self.update_scan_history)
        
        # Table context menu
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Filter changes
        self.filter_combo.currentIndexChanged.connect(self.update_scan_history)
        
        # Plugin signals
        self.plugin.scan_started.connect(self.update_scan_history)
        self.plugin.scan_finished.connect(self.update_scan_history)
    
    def update_scan_history(self):
        """Update the scan history table."""
        try:
            self.table.setRowCount(0)
            
            scan_history = self.plugin.get_scan_history()
            if not scan_history:
                self.summary_label.setText("No scan history available")
                return
            
            # Apply filter if not set to "all"
            status_filter = self.filter_combo.currentData()
            if status_filter != "all":
                scan_history = [scan for scan in scan_history if scan.get("status") == status_filter]
            
            # Ensure all datetime values are strings for proper sorting
            for scan in scan_history:
                # Convert datetime objects to strings if needed
                if isinstance(scan.get("start_time"), datetime):
                    scan["start_time"] = scan["start_time"].strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(scan.get("end_time"), datetime):
                    scan["end_time"] = scan["end_time"].strftime("%Y-%m-%d %H:%M:%S")
            
            # Sort by start time (descending)
            scan_history.sort(key=lambda x: x.get("start_time", ""), reverse=True)
            
            self.table.setRowCount(len(scan_history))
            
            # Define button style for action buttons
            action_button_style = """
                QPushButton {
                    background-color: #f0f4f8;
                    border: 1px solid #d0dbe8;
                    border-radius: 2px;
                    padding: 3px 5px;
                    color: #2c5aa0;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #e8f0ff;
                    border-color: #2c5aa0;
                }
                QPushButton:pressed {
                    background-color: #d0e0ff;
                }
            """
            
            for row, scan in enumerate(scan_history):
                # Extract scan data
                scan_id = scan.get("id", "")
                scan_type = scan.get("scan_type", "unknown")
                ip_range = scan.get("range", "")
                start_time = scan.get("start_time", "")
                end_time = scan.get("end_time", "")
                devices_found = scan.get("devices_found", 0)
                status = scan.get("status", "unknown")
                
                # Get template name instead of ID if available
                template = self.plugin.config.get("scan_templates", {}).get(scan_type, {})
                if template:
                    scan_type = template.get("name", scan_type)
                
                # Create table items
                id_item = QTableWidgetItem(scan_id)
                type_item = QTableWidgetItem(scan_type)
                range_item = QTableWidgetItem(ip_range)
                start_item = QTableWidgetItem(start_time)
                end_item = QTableWidgetItem(end_time if end_time else "Running...")
                devices_item = QTableWidgetItem(str(devices_found))
                status_item = QTableWidgetItem(status.capitalize())
                
                # Set item properties
                id_item.setData(Qt.UserRole, scan_id)
                
                # Set status color
                if status == "completed":
                    status_item.setBackground(QColor(200, 255, 200))
                elif status == "running":
                    status_item.setBackground(QColor(200, 200, 255))
                elif status == "stopped":
                    status_item.setBackground(QColor(255, 255, 200))
                elif status == "error":
                    status_item.setBackground(QColor(255, 200, 200))
                
                # Add items to table
                self.table.setItem(row, 0, id_item)
                self.table.setItem(row, 1, type_item)
                self.table.setItem(row, 2, range_item)
                self.table.setItem(row, 3, start_item)
                self.table.setItem(row, 4, end_item)
                self.table.setItem(row, 5, devices_item)
                self.table.setItem(row, 6, status_item)
                
                # Create actions widget with improved layout
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)
                
                # Create fixed-width buttons
                # View details button
                view_btn = QPushButton("View")
                view_btn.setFixedWidth(60)
                view_btn.setProperty("scan_id", scan_id)
                view_btn.clicked.connect(self.view_scan_details)
                view_btn.setStyleSheet(action_button_style)
                actions_layout.addWidget(view_btn)
                
                # Stop button (only for running scans)
                if status == "running":
                    stop_btn = QPushButton("Stop")
                    stop_btn.setFixedWidth(60)
                    stop_btn.setProperty("scan_id", scan_id)
                    stop_btn.clicked.connect(self.stop_scan)
                    stop_btn.setStyleSheet(action_button_style)
                    actions_layout.addWidget(stop_btn)
                
                # Repeat scan button
                repeat_btn = QPushButton("Repeat")
                repeat_btn.setFixedWidth(60)
                repeat_btn.setProperty("scan_id", scan_id)
                repeat_btn.clicked.connect(self.repeat_scan)
                repeat_btn.setStyleSheet(action_button_style)
                actions_layout.addWidget(repeat_btn)
                
                # Add a stretch to keep buttons aligned left
                actions_layout.addStretch()
                
                self.table.setCellWidget(row, 7, actions_widget)
            
            # Update summary
            total_completed = sum(1 for scan in scan_history if scan.get("status") == "completed")
            total_devices = sum(scan.get("devices_found", 0) for scan in scan_history)
            self.summary_label.setText(
                f"Total: {len(scan_history)} scans, {total_completed} completed, found {total_devices} devices total")
            
        except Exception as e:
            self.logger.error(f"Error updating scan history: {str(e)}", exc_info=True)
    
    def clear_history(self):
        """Clear the scan history."""
        # Confirm with user
        result = QMessageBox.question(
            self,
            "Clear Scan History",
            "Are you sure you want to clear all scan history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            self.plugin.scan_history.clear()
            self.plugin._save_scan_history()
            self.update_scan_history()
            self.plugin.api.log("Scan history cleared")
    
    def show_context_menu(self, position: QPoint):
        """Show context menu for scan history table."""
        if self.table.rowCount() == 0:
            return
            
        # Get selected item
        current_row = self.table.currentRow()
        if current_row < 0:
            return
            
        scan_id = self.table.item(current_row, 0).data(Qt.UserRole)
        
        # Create menu
        menu = QMenu(self)
        
        # Add actions
        view_action = QAction("View Scan Details", self)
        view_action.triggered.connect(lambda: self.view_scan_details(scan_id))
        menu.addAction(view_action)
        
        # Get scan status
        status_item = self.table.item(current_row, 6)
        status = status_item.text().lower() if status_item else ""
        
        # Add stop action if scan is running
        if status == "running":
            stop_action = QAction("Stop Scan", self)
            stop_action.triggered.connect(lambda: self.stop_scan(scan_id))
            menu.addAction(stop_action)
        
        # Add repeat action
        repeat_action = QAction("Repeat Scan", self)
        repeat_action.triggered.connect(lambda: self.repeat_scan(scan_id))
        menu.addAction(repeat_action)
        
        # Add separator
        menu.addSeparator()
        
        # Add remove action
        remove_action = QAction("Remove from History", self)
        remove_action.triggered.connect(lambda: self.remove_scan(scan_id))
        menu.addAction(remove_action)
        
        # Show menu
        menu.exec(self.table.mapToGlobal(position))

    def view_scan_details(self, scan_id=None):
        """View details of a scan."""
        # Get scan ID from sender if not provided
        if scan_id is None:
            sender = self.sender()
            if sender:
                scan_id = sender.property("scan_id")
        
        if not scan_id:
            return
            
        # Get scan data
        scan_data = None
        for scan in self.plugin.scan_history:
            if scan.get("id") == scan_id:
                scan_data = scan
                break
                
        if not scan_data:
            self.plugin.api.log(f"Scan {scan_id} not found", level="ERROR")
            return
            
        # Show details in a dialog
        from PySide6.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Scan Details: {scan_id}")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        details = QTextEdit()
        details.setReadOnly(True)
        details.setStyleSheet("font-family: monospace;")
        
        # Format scan data
        details_text = "Scan Details:\n\n"
        for key, value in scan_data.items():
            if key == "results":
                details_text += f"{key}: {len(value)} devices\n"
            else:
                details_text += f"{key}: {value}\n"
                
        details.setText(details_text)
        layout.addWidget(details)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #f0f4f8;
                border: 1px solid #d0dbe8;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: bold;
                color: #2c5aa0;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #e8f0ff;
                border-color: #2c5aa0;
            }
            QPushButton:pressed {
                background-color: #d0e0ff;
            }
        """)
        layout.addWidget(button_box)
        
        dialog.exec()
    
    def stop_scan(self, scan_id=None):
        """Stop a running scan."""
        # Get scan ID from sender if not provided
        if scan_id is None:
            sender = self.sender()
            if sender:
                scan_id = sender.property("scan_id")
        
        if not scan_id:
            return
            
        # Stop the scan
        self.plugin.stop_scan(scan_id)
        
        # Update UI
        self.update_scan_history()
    
    def repeat_scan(self, scan_id=None):
        """Repeat a scan."""
        # Get scan ID from sender if not provided
        if scan_id is None:
            sender = self.sender()
            if sender:
                scan_id = sender.property("scan_id")
        
        if not scan_id:
            return
            
        # Get scan data
        scan_data = None
        for scan in self.plugin.scan_history:
            if scan.get("id") == scan_id:
                scan_data = scan.copy()
                break
                
        if not scan_data:
            self.plugin.api.log(f"Scan {scan_id} not found", level="ERROR")
            return
            
        # Remove result-specific fields
        for field in ["id", "start_time", "end_time", "status", "results", "devices_found"]:
            if field in scan_data:
                del scan_data[field]
                
        # Start a new scan with the same settings
        try:
            new_scan_id = self.plugin.start_scan(scan_data)
            self.plugin.api.log(f"Repeated scan {scan_id} as {new_scan_id}")
        except Exception as e:
            self.plugin.api.log(f"Error repeating scan {scan_id}: {str(e)}", level="ERROR")
    
    def remove_scan(self, scan_id):
        """Remove a scan from history."""
        # Confirm with user
        result = QMessageBox.question(
            self,
            "Remove Scan",
            "Are you sure you want to remove this scan from history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            # Remove from scan history
            self.plugin.scan_history = [scan for scan in self.plugin.scan_history if scan.get("id") != scan_id]
            self.plugin._save_scan_history()
            self.update_scan_history()
            self.plugin.api.log(f"Removed scan {scan_id} from history")
    
    def on_scan_started(self, scan_data):
        """Handle scan started event."""
        self.update_scan_history()
        
        # Show message in log
        self.plugin.api.log(f"Scan started: {scan_data.get('scan_type')} on {scan_data.get('range')}")
    
    def on_scan_finished(self, scan_data):
        """Handle scan finished event."""
        self.update_scan_history()
        
        # Show message in log
        devices_found = scan_data.get("devices_found", 0)
        self.plugin.api.log(f"Scan finished: found {devices_found} devices")
    
    def on_scan_progress(self, progress_data):
        """Handle scan progress event."""
        # Update UI if needed
        self.update_scan_history()
        
        # Show message in log
        progress = progress_data.get("progress", 0)
        self.plugin.api.log(f"Scan progress: {progress}%")
    
    def refresh(self):
        """Refresh the scan history."""
        self.update_scan_history() 