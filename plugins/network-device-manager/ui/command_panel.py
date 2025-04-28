#!/usr/bin/env python3
# Network Device Manager - Command Panel UI Component

import os
import csv
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QGroupBox, QFormLayout, QDialog,
    QLineEdit, QFileDialog, QMessageBox, QSplitter, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QCheckBox, QTabWidget, QProgressBar,
    QTableWidget, QTableWidgetItem, QMenu, QAbstractItemView, QSizePolicy,
    QSpacerItem
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QTimer, QSettings
from PySide6.QtGui import QFont, QTextCursor, QAction, QIcon, QColor, QTextCharFormat

# Common styles that can be used throughout the application
BUTTON_STYLE = """
    QPushButton {
        background-color: #f5f5f5;
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        padding: 6px 12px;
        color: #333;
        font-weight: 500;
        min-height: 26px;
    }
    QPushButton:hover {
        background-color: #e6e6e6;
        border-color: #adadad;
    }
    QPushButton:pressed {
        background-color: #d4d4d4;
        border-color: #8c8c8c;
        padding-top: 7px;
        padding-bottom: 5px;
        padding-left: 13px;
        padding-right: 11px;
        box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.125);
    }
    QPushButton:disabled {
        background-color: #f8f8f8;
        border-color: #e0e0e0;
        color: #a0a0a0;
    }
"""

PRIMARY_BUTTON_STYLE = """
    QPushButton {
        background-color: #007bff;
        border: 1px solid #0062cc;
        border-radius: 4px;
        padding: 6px 12px;
        color: white;
        font-weight: 500;
        min-height: 26px;
    }
    QPushButton:hover {
        background-color: #0069d9;
        border-color: #0056b3;
    }
    QPushButton:pressed {
        background-color: #0056b3;
        border-color: #004085;
        padding-top: 7px;
        padding-bottom: 5px;
        padding-left: 13px;
        padding-right: 11px;
        box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.2);
    }
    QPushButton:disabled {
        background-color: #80bdff;
        border-color: #80bdff;
        color: #f8f9fa;
    }
"""

DANGER_BUTTON_STYLE = """
    QPushButton {
        background-color: #dc3545;
        border: 1px solid #bd2130;
        border-radius: 4px;
        padding: 6px 12px;
        color: white;
        font-weight: 500;
        min-height: 26px;
    }
    QPushButton:hover {
        background-color: #c82333;
        border-color: #bd2130;
    }
    QPushButton:pressed {
        background-color: #bd2130;
        border-color: #a71d2a;
        padding-top: 7px;
        padding-bottom: 5px;
        padding-left: 13px;
        padding-right: 11px;
        box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.2);
    }
    QPushButton:disabled {
        background-color: #f5c6cb;
        border-color: #f5c6cb;
        color: #f8f9fa;
    }
"""

COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        padding: 4px 10px;
        background-color: white;
        min-height: 26px;
    }
    QComboBox:hover {
        border-color: #adadad;
    }
    QComboBox:focus {
        border-color: #80bdff;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #d0d0d0;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #d0d0d0;
        selection-background-color: #007bff;
        selection-color: white;
    }
"""

TABLE_STYLE = """
    QTableWidget {
        border: 1px solid #d0d0d0;
        gridline-color: #f0f0f0;
        selection-background-color: #cce5ff;
        selection-color: #000;
    }
    QTableWidget::item {
        padding: 4px;
        border-bottom: 1px solid #f0f0f0;
    }
    QTableWidget::item:selected {
        background-color: #cce5ff;
    }
    QHeaderView::section {
        background-color: #f8f9fa;
        border: 1px solid #d0d0d0;
        padding: 6px;
        font-weight: bold;
    }
    QScrollBar:vertical {
        border: 1px solid #d0d0d0;
        background: white;
        width: 12px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        min-height: 20px;
        border-radius: 6px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
        height: 0px;
    }
"""

class CommandExecutionThread(QThread):
    """Thread for executing commands on a device."""
    
    command_output = Signal(str, bool)  # Output, success/failure
    command_complete = Signal(bool, str)  # Success/failure, message
    
    def __init__(self, connection_handler, connection_id, command):
        super().__init__()
        self.connection_handler = connection_handler
        self.connection_id = connection_id
        self.command = command
    
    def run(self):
        """Execute the command."""
        try:
            success, output = self.connection_handler.execute_command(
                self.connection_id, self.command
            )
            
            if success:
                self.command_output.emit(output, True)
                self.command_complete.emit(True, "Command executed successfully")
            else:
                self.command_output.emit(output, False)
                self.command_complete.emit(False, f"Command failed: {output}")
        except Exception as e:
            self.command_output.emit(str(e), False)
            self.command_complete.emit(False, f"Command execution error: {str(e)}")

class CommandDialog(QDialog):
    """Dialog for executing commands on a device."""
    
    def __init__(self, parent, device, command_manager, connection_handler, device_manager):
        super().__init__(parent)
        self.device = device
        self.command_manager = command_manager
        self.connection_handler = connection_handler
        self.device_manager = device_manager
        self.api = parent.api
        self.connection_id = None
        self.settings = QSettings("netWORKS", "NetworkDeviceManager")
        
        self.setWindowTitle(f"Commands - {device['ip'] if device else 'No Device'}")
        self.resize(900, 700)
        
        # Set the application style
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                color: #333;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                margin-top: 1ex;
                padding-top: 0.5ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
            }
            QSplitter::handle {
                background-color: #d0d0d0;
            }
            QTreeWidget {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
            }
        """)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Top info area - Device information
        info_layout = QHBoxLayout()
        
        # Device info panel
        device_info = QWidget()
        device_layout = QVBoxLayout(device_info)
        device_layout.setContentsMargins(10, 10, 10, 10)
        device_layout.setSpacing(5)
        
        device_info.setStyleSheet("""
            QWidget {
                background-color: #f0f4f8;
                border: 1px solid #d0dbe8;
                border-radius: 4px;
            }
            QLabel {
                background-color: transparent;
                border: none;
                color: #2c5aa0;
            }
        """)
        
        if self.device:
            hostname = self.device.get("hostname", "Unknown")
            ip = self.device.get("ip_address", "Unknown")
            platform = self.device.get("platform", "Unknown")
            device_type = self.device.get("device_type", "Unknown")
            
            device_layout.addWidget(QLabel(f"<b>Device:</b> {hostname}"))
            device_layout.addWidget(QLabel(f"<b>IP:</b> {ip}"))
            device_layout.addWidget(QLabel(f"<b>Platform:</b> {platform}"))
            device_layout.addWidget(QLabel(f"<b>Type:</b> {device_type}"))
        else:
            device_layout.addWidget(QLabel("<b>No device selected</b>"))
        
        info_layout.addWidget(device_info)
        
        # Connection status and controls
        conn_widget = QWidget()
        conn_layout = QVBoxLayout(conn_widget)
        conn_layout.setContentsMargins(10, 10, 10, 10)
        conn_layout.setSpacing(5)
        
        conn_widget.setStyleSheet("""
            QWidget {
                background-color: #f0f4f8;
                border: 1px solid #d0dbe8;
                border-radius: 4px;
            }
            QLabel {
                background-color: transparent;
                border: none;
            }
            QProgressBar {
                border: 1px solid #d0dbe8;
                border-radius: 3px;
                background-color: white;
                text-align: center;
                color: #2c5aa0;
            }
            QProgressBar::chunk {
                background-color: #2c5aa0;
                width: 10px;
            }
        """)
        
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: #e04646; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.connect_btn.clicked.connect(self._connect_to_device)
        status_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        self.disconnect_btn.clicked.connect(self._disconnect_from_device)
        self.disconnect_btn.setEnabled(False)
        status_layout.addWidget(self.disconnect_btn)
        
        conn_layout.addLayout(status_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        conn_layout.addWidget(self.progress_bar)
        
        info_layout.addWidget(conn_widget)
        layout.addLayout(info_layout)
        
        # Command section
        cmd_layout = QHBoxLayout()
        
        cmd_layout.addWidget(QLabel("Command:"))
        
        # Command selector
        self.cmd_combo = QComboBox()
        self.cmd_combo.setEditable(True)
        self.cmd_combo.setMinimumWidth(400)
        self.cmd_combo.setStyleSheet(COMBOBOX_STYLE)
        self.cmd_combo.setInsertPolicy(QComboBox.NoInsert)
        self.cmd_combo.lineEdit().returnPressed.connect(self._execute_command)
        cmd_layout.addWidget(self.cmd_combo)
        
        # Execute button
        self.execute_btn = QPushButton("Execute")
        self.execute_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.execute_btn.clicked.connect(self._execute_command)
        self.execute_btn.setEnabled(False)
        cmd_layout.addWidget(self.execute_btn)
        
        layout.addLayout(cmd_layout)
        
        # Main content area
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        
        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))  # Use a modern monospace font
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d0dbe8;
                border-radius: 4px;
            }
        """)
        
        # Command history table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Command", "Time", "Status", "Actions"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self._show_history_context_menu)
        self.history_table.setStyleSheet(TABLE_STYLE)
        
        # Add widgets to splitter
        splitter.addWidget(self.output_text)
        splitter.addWidget(self.history_table)
        splitter.setSizes([400, 200])
        
        layout.addWidget(splitter)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()
        
        # Save output button
        self.save_btn = QPushButton("Save Output")
        self.save_btn.setStyleSheet(BUTTON_STYLE)
        self.save_btn.clicked.connect(self._save_output)
        self.save_btn.setEnabled(False)
        bottom_layout.addWidget(self.save_btn)
        
        # Add spacer to push buttons to the right
        bottom_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.setStyleSheet(BUTTON_STYLE)
        self.close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
        
        # Load command history
        self._load_command_history()
        
        # Load available commands
        self._load_commands()
    
    def _show_history_context_menu(self, position):
        """Show context menu for history table."""
        menu = QMenu()
        rerun_action = QAction("Run Again", self)
        copy_action = QAction("Copy Command", self)
        copy_output_action = QAction("Copy Output", self)
        delete_action = QAction("Delete", self)
        
        menu.addAction(rerun_action)
        menu.addAction(copy_action)
        menu.addAction(copy_output_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        
        # Get selected item
        selected_row = self.history_table.currentRow()
        if selected_row >= 0:
            # Connect actions
            rerun_action.triggered.connect(lambda: self._rerun_command(selected_row))
            copy_action.triggered.connect(lambda: self._copy_command(selected_row))
            copy_output_action.triggered.connect(lambda: self._copy_output(selected_row))
            delete_action.triggered.connect(lambda: self._delete_history_item(selected_row))
            
            # Show menu
            menu.exec(self.history_table.mapToGlobal(position))
    
    def _load_command_history(self):
        """Load command history from settings."""
        # Clear table
        self.history_table.setRowCount(0)
        
        # Get history from settings
        history = self.settings.value("command_history", [])
        if not history:
            return
            
        # Add history to table
        for i, item in enumerate(history):
            command = item.get("command", "")
            timestamp = item.get("timestamp", "")
            status = item.get("status", "")
            output = item.get("output", "")
            
            # Add row
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            
            # Add items
            self.history_table.setItem(row, 0, QTableWidgetItem(command))
            self.history_table.setItem(row, 1, QTableWidgetItem(timestamp))
            
            status_item = QTableWidgetItem(status)
            if status == "Success":
                status_item.setForeground(QColor("#28a745"))
            else:
                status_item.setForeground(QColor("#dc3545"))
            self.history_table.setItem(row, 2, status_item)
            
            # Add actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(2)
            
            run_btn = QPushButton("Run")
            run_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    padding: 3px 6px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            run_btn.clicked.connect(lambda checked, row=row: self._rerun_command(row))
            
            copy_btn = QPushButton("Copy")
            copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #17a2b8;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    padding: 3px 6px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #138496;
                }
            """)
            copy_btn.clicked.connect(lambda checked, row=row: self._copy_command(row))
            
            # Add buttons to layout
            actions_layout.addWidget(run_btn)
            actions_layout.addWidget(copy_btn)
            
            # Add widget to table
            self.history_table.setCellWidget(row, 3, actions_widget)
            
            # Store output in item data
            self.history_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, output)
    
    def _rerun_command(self, row):
        """Rerun command from history."""
        if row < 0 or row >= self.history_table.rowCount():
            return
            
        # Get command
        command = self.history_table.item(row, 0).text()
        
        # Set command in combo box
        self.cmd_combo.setCurrentText(command)
        
        # Execute command
        self._execute_command()
    
    def _copy_command(self, row):
        """Copy command from history to clipboard."""
        if row < 0 or row >= self.history_table.rowCount():
            return
            
        # Get command
        command = self.history_table.item(row, 0).text()
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(command)
    
    def _copy_output(self, row):
        """Copy output from history to clipboard."""
        if row < 0 or row >= self.history_table.rowCount():
            return
            
        # Get output
        output = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(output)
    
    def _delete_history_item(self, row):
        """Delete history item."""
        if row < 0 or row >= self.history_table.rowCount():
            return
            
        # Remove row
        self.history_table.removeRow(row)
        
        # Save history
        self._save_history_to_settings()
    
    def _save_history_to_settings(self):
        """Save history to settings."""
        history = []
        
        # Get history from table
        for row in range(self.history_table.rowCount()):
            command = self.history_table.item(row, 0).text()
            timestamp = self.history_table.item(row, 1).text()
            status = self.history_table.item(row, 2).text()
            output = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            
            history.append({
                "command": command,
                "timestamp": timestamp,
                "status": status,
                "output": output
            })
        
        # Save to settings
        self.settings.setValue("command_history", history)
    
    def _load_device_types(self):
        """Load device types from command manager."""
        try:
            # Clear combo box
            self.cmd_combo.clear()
            
            # Add "unknown" type
            self.cmd_combo.addItem("Unknown", "unknown")
            
            # Add device types from command manager
            device_types = self.command_manager.get_device_type_display_names()
            for device_type, display_name in device_types.items():
                self.cmd_combo.addItem(display_name, device_type)
        except Exception as e:
            self.api.log(f"Error loading device types: {str(e)}", level="ERROR")
    
    def _load_commands(self):
        """Load commands for the selected device type."""
        try:
            # Clear tree
            self.cmd_combo.clear()
            
            # Get device type
            device_type = self.cmd_combo.currentData()
            if not device_type:
                return
                
            # Get commands for device type
            commands = self.command_manager.get_commands_for_device_type(device_type)
            
            # Add commands to tree
            for command_id, command_info in commands.items():
                item = QTreeWidgetItem()
                item.setText(0, command_info.get('command', ''))
                item.setText(1, command_info.get('description', ''))
                item.setData(0, Qt.ItemDataRole.UserRole, command_id)
                item.setData(1, Qt.ItemDataRole.UserRole, command_info.get('output_type', 'text'))
                
                self.cmd_combo.addItem(item.text(0), item.data(0, Qt.ItemDataRole.UserRole))
            
            # Expand all items
            self.cmd_combo.expandAll()
        except Exception as e:
            self.api.log(f"Error loading commands: {str(e)}", level="ERROR")
    
    def _connect_to_device(self):
        """Connect to the device."""
        try:
            # Get connection type
            connection_type = self.cmd_combo.currentData()
            
            # Update status
            self.status_label.setText("Connecting...")
            
            # Connect to device
            success, message, connection_id = self.connection_handler.connect(
                self.device, connection_type
            )
            
            # Update status
            if success:
                self.status_label.setText("Connected")
                self.connection_id = connection_id
                self.execute_btn.setEnabled(True)
                self.connect_btn.setText("Disconnect")
                self.connect_btn.clicked.disconnect()
                self.connect_btn.clicked.connect(self._disconnect_from_device)
            else:
                self.status_label.setText(f"Connection failed: {message}")
                self.connection_id = None
                self.execute_btn.setEnabled(False)
        except Exception as e:
            self.status_label.setText(f"Connection error: {str(e)}")
            self.api.log(f"Connection error: {str(e)}", level="ERROR")
    
    def _disconnect_from_device(self):
        """Disconnect from the device."""
        try:
            if self.connection_id:
                # Disconnect
                self.connection_handler.disconnect(self.connection_id)
                
                # Update UI
                self.status_label.setText("Disconnected")
                self.connection_id = None
                self.execute_btn.setEnabled(False)
                self.connect_btn.setText("Connect")
                self.connect_btn.clicked.disconnect()
                self.connect_btn.clicked.connect(self._connect_to_device)
        except Exception as e:
            self.api.log(f"Disconnect error: {str(e)}", level="ERROR")
    
    def _execute_command(self):
        """Execute the selected command."""
        try:
            # Get command from custom or predefined
            selected_items = self.cmd_combo.selectedItems()
            if selected_items and selected_items[0].parent():
                # Predefined command selected
                command_item = selected_items[0]
                command_id = command_item.data(0, Qt.ItemDataRole.UserRole)
                device_type = self.cmd_combo.currentData()
                command_details = self.command_manager.get_command_details(device_type, command_id)
                
                if not command_details:
                    QMessageBox.warning(self, "Command Error", f"Command {command_id} not found for device type {device_type}")
                    return
                
                command = command_details['command']
                output_type = command_details.get('output_type', 'text')
            else:
                # Custom command
                command = self.cmd_combo.currentText().strip()
                output_type = 'text'
                
            if not command:
                QMessageBox.warning(self, "Command Error", "No command specified")
                return
            
            # Save the device type to the device dictionary
            device_type = self.cmd_combo.currentData()
            if device_type and device_type != self.device.get('device_type'):
                self.device['device_type'] = device_type
                # Update the device in the device manager if available
                if self.device_manager:
                    try:
                        self.device_manager.update_device(self.device)
                        self.api.log(f"Updated device type to {device_type} for device {self.device.get('ip')}", level="DEBUG")
                    except Exception as e:
                        self.api.log(f"Failed to update device type in database: {str(e)}", level="WARNING")
            
            # Check if we're already connected
            if not self.connection_id:
                # Auto-connect if not connected
                connection_type = self.cmd_combo.currentData()
                success, message, self.connection_id = self.connection_handler.connect(
                    self.device, connection_type
                )
                
                if not success:
                    QMessageBox.warning(self, "Connection Error", message)
                    return
                
                # Update connection status
                self.status_label.setText(f"Connected ({connection_type})")
                self.connect_btn.setText("Disconnect")
            
            # Clear output
            self.output_text.clear()
            
            # Create and start thread
            self.execute_thread = CommandExecutionThread(
                self.connection_handler, self.connection_id, command
            )
            self.execute_thread.command_output.connect(self._handle_command_output)
            self.execute_thread.command_complete.connect(self._handle_command_complete)
            self.execute_thread.start()
            
            # Disable execute button while running
            self.execute_btn.setEnabled(False)
            
            # Save command history
            self._save_command_history(command, output_type)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error executing command: {str(e)}")
    
    def _handle_command_output(self, output, success):
        """Handle command output from thread."""
        if success:
            self.output_text.append(output)
        else:
            self.output_text.append(f"ERROR: {output}")
    
    def _handle_command_complete(self, success, message):
        """Handle command completion."""
        # Re-enable execute button
        self.execute_btn.setEnabled(True)
        
        # Show message
        if success:
            self.output_text.append("\nCommand completed successfully.")
            self.save_btn.setEnabled(True)
        else:
            self.output_text.append(f"\nCommand failed: {message}")
            self.save_btn.setEnabled(False)
    
    def _save_output(self):
        """Save command output."""
        try:
            # Create output directory if it doesn't exist
            output_dir = Path(self.api.get_plugin_data_dir()) / "outputs" / self.device['ip']
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            command_file = self.cmd_combo.currentText().replace(' ', '_').replace('/', '_')[:20]
            
            # Determine file extension based on output type
            if self.cmd_combo.currentData() == "tabular":
                extension = "csv"
            else:
                extension = "txt"
                
            output_path = output_dir / f"{command_file}_{timestamp}.{extension}"
            
            # Get output text
            output_text = self.output_text.toPlainText()
            
            # Write output to file
            with open(output_path, 'w', encoding='utf-8') as f:
                # Remove command and status lines if present
                lines = output_text.split('\n')
                filtered_lines = [line for line in lines if not line.startswith("Executing:") and 
                                  not line.startswith("Command completed")]
                
                if self.cmd_combo.currentData() == "tabular" and extension == "csv":
                    # Try to parse as CSV
                    writer = csv.writer(f)
                    for line in filtered_lines:
                        # Skip empty lines
                        if not line.strip():
                            continue
                            
                        # Split by whitespace and write as CSV
                        writer.writerow(line.split())
                else:
                    # Write as plain text
                    f.write('\n'.join(filtered_lines))
            
            # Add to database
            self.device_manager.add_command_output(
                self.device['ip'],
                self.cmd_combo.currentText(),
                str(output_path),
                self.cmd_combo.currentData()
            )
            
            # Show success message
            self.api.log(f"Output saved to {output_path}")
            QMessageBox.information(self, "Output Saved", f"Command output saved to {output_path}")
            
            # Update device panel if it exists
            if hasattr(self.parent(), 'device_panel') and self.parent().device_panel:
                self.parent().device_panel._update_command_history()
        except Exception as e:
            self.api.log(f"Error saving output: {str(e)}", level="ERROR")
            QMessageBox.warning(self, "Save Error", f"Error saving output: {str(e)}")
    
    def _save_command_history(self, command, output_type):
        """Save command to history."""
        try:
            # Get the output directory path
            output_dir = self.device_manager.output_dir if hasattr(self.device_manager, 'output_dir') else Path("data/outputs")
            
            # Create device directory if it doesn't exist
            device_dir = output_dir / self.device['ip'].replace('.', '_')
            device_dir.mkdir(exist_ok=True)
            
            # Create history file if it doesn't exist
            history_file = device_dir / "command_history.csv"
            
            # Get current time
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Save to history file
            mode = 'a' if history_file.exists() else 'w'
            with open(history_file, mode, newline='') as f:
                writer = csv.writer(f)
                if mode == 'w':
                    writer.writerow(['Command', 'Timestamp', 'Type'])
                writer.writerow([command, timestamp, output_type])
                
            # Debug log
            self.api.log(f"Command saved to history: {command}", level="DEBUG")
        except Exception as e:
            self.api.log(f"Error saving command history: {str(e)}", level="ERROR")

class CommandPanel(QWidget):
    """Panel for executing commands on devices."""
    
    def __init__(self, plugin_api, command_manager, connection_handler):
        super().__init__()
        self.api = plugin_api
        self.command_manager = command_manager
        self.connection_handler = connection_handler
        self.device_manager = None
        self.device_panel = None
        self.current_device = None
        
        self._init_ui()
        
        # Connect directly to device_selected signals if available
        try:
            # Try to connect to main window's device table if it exists
            if hasattr(self.api, 'main_window') and hasattr(self.api.main_window, 'device_table'):
                self.api.log("CommandPanel: Connecting directly to main window's device table", level="DEBUG")
                if hasattr(self.api.main_window.device_table, 'device_selected'):
                    self.api.main_window.device_table.device_selected.connect(self.on_device_selected)
                    self.api.log("CommandPanel: Successfully connected to device_table device_selected signal", level="DEBUG")
        except Exception as e:
            self.api.log(f"CommandPanel: Error connecting to device selection signals: {str(e)}", level="ERROR")
    
    @Slot(object)
    def on_device_selected(self, device):
        """Public slot to handle device selection events directly."""
        try:
            self.api.log(f"CommandPanel.on_device_selected: Received direct selection signal for device: {device.get('ip') if isinstance(device, dict) else 'Unknown type'}", level="DEBUG")
            self.update_device(device)
        except Exception as e:
            self.api.log(f"CommandPanel.on_device_selected error: {str(e)}", level="ERROR")
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Device Commands")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Device info
        self.device_info = QLabel("No device selected")
        layout.addWidget(self.device_info)
        
        execute_button = QPushButton("Execute Command")
        execute_button.clicked.connect(self._execute_command)
        
        layout.addWidget(execute_button)
        
        # Add import/manage commands buttons
        button_layout = QHBoxLayout()
        
        import_button = QPushButton("Import Commands")
        import_button.clicked.connect(self._import_commands)
        
        manage_button = QPushButton("Manage Commands")
        manage_button.clicked.connect(self._manage_commands)
        
        button_layout.addWidget(import_button)
        button_layout.addWidget(manage_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def update_device(self, device):
        """Update panel with device information."""
        self.current_device = device
        
        if device:
            self.device_info.setText(f"Selected Device: {device['ip']} ({device.get('hostname', 'Unknown')})")
        else:
            self.device_info.setText("No device selected")
    
    def set_device_manager(self, device_manager):
        """Set the device manager instance."""
        self.device_manager = device_manager
    
    def set_device_panel(self, device_panel):
        """Set the device panel instance."""
        self.device_panel = device_panel
    
    def _execute_command(self):
        """Open dialog to execute a command."""
        if not self.current_device:
            return
            
        # Use the device_manager from the parent component if available
        if not self.device_manager:
            self.api.log("Device manager not available. Some functionality may be limited.", level="WARNING")
            return
        
        # Create and show dialog
        dialog = CommandDialog(
            self, 
            self.current_device, 
            self.command_manager, 
            self.connection_handler,
            self.device_manager
        )
        dialog.exec()
    
    def show_command_dialog(self, device):
        """Show command dialog for a device."""
        self.current_device = device
        self._execute_command()
    
    def _import_commands(self):
        """Import commands from a JSON file."""
        try:
            # Open file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Command Set",
                "",
                "JSON Files (*.json)"
            )
            
            if not file_path:
                return
                
            # Import command set
            success, message = self.command_manager.import_command_set(file_path)
            
            # Show result
            if success:
                QMessageBox.information(self, "Import Successful", message)
            else:
                QMessageBox.warning(self, "Import Failed", message)
        except Exception as e:
            self.api.log(f"Error importing commands: {str(e)}", level="ERROR")
            QMessageBox.warning(self, "Import Error", f"Error importing commands: {str(e)}")
    
    def _manage_commands(self):
        """Open dialog to manage command sets."""
        try:
            # Import the dialog (to avoid circular imports)
            from ui.command_set_dialog import CommandSetDialog
            
            # Create and show the dialog with our command_manager directly
            dialog = CommandSetDialog(self.api.main_window, self.command_manager)
            dialog.exec()
            
            self.api.log("Command set management complete")
        except Exception as e:
            self.api.log(f"Error managing commands: {str(e)}", level="ERROR")
            QMessageBox.warning(self, "Error", f"Error managing command sets: {str(e)}") 
