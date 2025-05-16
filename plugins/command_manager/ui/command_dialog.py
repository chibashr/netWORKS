#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command Dialog for Command Manager plugin
"""

import os
import json
import datetime
from pathlib import Path
import threading

from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, 
    QSplitter, QTextEdit, QMenu, QFileDialog, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QProgressBar, QWidget,
    QCheckBox, QGroupBox, QFormLayout, QDialogButtonBox, QTabWidget
)
from PySide6.QtGui import QAction, QIcon, QFont, QTextCursor


class CommandWorker(QObject):
    """Worker for running commands in the background"""
    
    command_started = Signal(object, object)  # device, command
    command_complete = Signal(object, object, object, object)  # device, command, result, command_set
    command_progress = Signal(int, int)  # current, total
    all_commands_complete = Signal()
    
    def __init__(self, plugin, devices, commands, command_set=None):
        """Initialize the worker"""
        super().__init__()
        
        self.plugin = plugin
        self.devices = devices
        self.commands = commands
        self.command_set = command_set
        self.stop_requested = False
        
    def run(self):
        """Run the commands on the devices"""
        from loguru import logger
        logger.debug(f"Starting command execution for {len(self.devices)} devices and {len(self.commands)} commands")
        
        # Calculate total number of commands for progress tracking
        total_commands = len(self.devices) * len(self.commands)
        completed_commands = 0
        
        for device in self.devices:
            if self.stop_requested:
                logger.debug("Stop requested - halting command execution")
                break
                
            # Get device properties for better logging
            device_name = device.get_property("alias", "Unnamed Device")
            device_ip = device.get_property("ip_address", "Unknown IP")
            logger.debug(f"Processing device: {device_name} ({device_ip})")
            
            # Get device groups if available
            device_groups = []
            if hasattr(self.plugin.device_manager, 'get_device_groups_for_device'):
                try:
                    device_groups = self.plugin.device_manager.get_device_groups_for_device(device.id)
                    logger.debug(f"Device {device_name} is in groups: {[g['name'] for g in device_groups]}")
                except Exception as e:
                    logger.error(f"Error getting device groups for device {device_name}: {e}")
            
            # Try to get credentials in this order:
            # 1. Device-specific credentials
            # 2. Group credentials (if device is in any groups)
            # 3. Subnet credentials
            
            # Get device-specific credentials
            credentials = self.plugin.get_device_credentials(device.id, device_ip)
            
            # If no device credentials, try group credentials
            if not credentials and device_groups:
                for group in device_groups:
                    group_credentials = self.plugin.get_group_credentials(group['name'])
                    if group_credentials:
                        logger.debug(f"Using group credentials from '{group['name']}' for device: {device_name}")
                        credentials = group_credentials
                        break
            
            # If still no credentials, try subnet credentials
            if not credentials and device_ip:
                # Extract subnet
                parts = device_ip.split('.')
                if len(parts) == 4:
                    subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
                    subnet_credentials = self.plugin.get_subnet_credentials(subnet)
                    if subnet_credentials:
                        logger.debug(f"Using subnet credentials from '{subnet}' for device: {device_name}")
                        credentials = subnet_credentials
            
            if not credentials:
                logger.warning(f"No credentials found for device: {device_name} ({device_ip})")
                # Emit signal with an error result for each command
                for command in self.commands:
                    result = {
                        "success": False,
                        "output": f"Command: {command['command']}\n\nNo credentials available for this device."
                    }
                    self.command_complete.emit(device, command, result, self.command_set)
                    
                    # Update progress
                    completed_commands += 1
                    self.command_progress.emit(completed_commands, total_commands)
                continue
                
            logger.debug(f"Using credentials for device: {device_name}, type: {credentials.get('connection_type', 'ssh')}")
            
            for command in self.commands:
                if self.stop_requested:
                    logger.debug("Stop requested - halting command execution")
                    break
                    
                # Log the command being executed
                logger.debug(f"Executing command: {command['command']} on device: {device_name}")
                
                # Emit signal that we're starting a command
                self.command_started.emit(device, command)
                
                try:
                    # Run the command
                    result = self.plugin.run_command(device, command["command"], credentials)
                    
                    # Emit signal with result
                    self.command_complete.emit(device, command, result, self.command_set)
                    
                    # Add to history if successful
                    if result["success"]:
                        # Create a command ID from the command set and alias
                        command_set_id = ""
                        if self.command_set:
                            command_set_id = f"{self.command_set.device_type}_{self.command_set.firmware_version}"
                            
                        command_id = f"{command_set_id}_{command['alias']}".replace(" ", "_")
                        
                        # Add output to history
                        self.plugin.add_command_output(
                            device.id,
                            command_id,
                            result["output"],
                            command["command"]
                        )
                        logger.debug(f"Command execution successful, output saved for: {device_name}, command: {command['alias']}")
                    else:
                        logger.warning(f"Command execution failed for: {device_name}, command: {command['alias']}")
                except Exception as e:
                    logger.error(f"Error executing command: {command['command']} on device: {device_name}: {e}")
                    # Create an error result and emit signal
                    result = {
                        "success": False,
                        "output": f"Command: {command['command']}\n\nError: {str(e)}"
                    }
                    self.command_complete.emit(device, command, result, self.command_set)
                
                # Update progress
                completed_commands += 1
                self.command_progress.emit(completed_commands, total_commands)
                
        # All commands complete
        logger.debug("All commands completed")
        self.all_commands_complete.emit()
        
    def stop(self):
        """Stop the worker"""
        self.stop_requested = True


class CommandDialog(QDialog):
    """Dialog for running commands on devices"""
    
    def __init__(self, plugin, devices=None, parent=None):
        """Initialize the dialog
        
        Args:
            plugin: The command manager plugin
            devices: Optional list of devices to pre-select
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.plugin = plugin
        self.worker_thread = None
        self.worker = None
        self.selected_devices = devices or []
        
        # Set dialog properties
        self.setWindowTitle("Command Manager")
        self.resize(900, 600)
        
        # Create UI components
        self._create_ui()
        
        # Refresh devices
        self.refresh_devices()
        
        # Refresh command sets
        self.refresh_command_sets()
        
        # Pre-select devices if provided
        if self.selected_devices:
            self.set_selected_devices(self.selected_devices)
        
    def _create_ui(self):
        """Create the UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Splitter for device list and command output
        splitter = QSplitter(Qt.Vertical)
        
        # ==================
        # Top panel (devices and commands)
        # ==================
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Device list panel
        device_panel = QWidget()
        device_layout = QVBoxLayout(device_panel)
        device_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add target selection tabs
        self.target_tabs = QTabWidget()
        
        # Device tab
        device_tab = QWidget()
        device_tab_layout = QVBoxLayout(device_tab)
        device_tab_layout.setContentsMargins(5, 5, 5, 5)
        
        device_label = QLabel("Devices:")
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(2)
        self.device_table.setHorizontalHeaderLabels(["Device", "IP Address"])
        self.device_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.device_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.device_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.device_table.setSelectionMode(QTableWidget.MultiSelection)
        
        device_tab_layout.addWidget(device_label)
        device_tab_layout.addWidget(self.device_table)
        
        # Group tab
        group_tab = QWidget()
        group_tab_layout = QVBoxLayout(group_tab)
        group_tab_layout.setContentsMargins(5, 5, 5, 5)
        
        group_label = QLabel("Device Groups:")
        self.group_table = QTableWidget()
        self.group_table.setColumnCount(2)
        self.group_table.setHorizontalHeaderLabels(["Group Name", "Device Count"])
        self.group_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.group_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.group_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.group_table.setSelectionMode(QTableWidget.MultiSelection)
        
        group_tab_layout.addWidget(group_label)
        group_tab_layout.addWidget(self.group_table)
        
        # Subnet tab
        subnet_tab = QWidget()
        subnet_tab_layout = QVBoxLayout(subnet_tab)
        subnet_tab_layout.setContentsMargins(5, 5, 5, 5)
        
        subnet_label = QLabel("Subnets:")
        self.subnet_table = QTableWidget()
        self.subnet_table.setColumnCount(2)
        self.subnet_table.setHorizontalHeaderLabels(["Subnet", "Device Count"])
        self.subnet_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.subnet_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.subnet_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.subnet_table.setSelectionMode(QTableWidget.MultiSelection)
        
        subnet_tab_layout.addWidget(subnet_label)
        subnet_tab_layout.addWidget(self.subnet_table)
        
        # Add tabs to tab widget
        self.target_tabs.addTab(device_tab, "Devices")
        self.target_tabs.addTab(group_tab, "Groups")
        self.target_tabs.addTab(subnet_tab, "Subnets")
        
        # Add Credential Manager button below the device list
        device_cred_layout = QHBoxLayout()
        self.manage_credentials_btn = QPushButton("👤 Manage Credentials")
        self.manage_credentials_btn.setToolTip("Configure device credentials")
        self.manage_credentials_btn.clicked.connect(self._on_manage_credentials)
        
        # Add Batch Export button
        self.batch_export_btn = QPushButton("📊 Batch Export")
        self.batch_export_btn.setToolTip("Export commands from multiple devices")
        self.batch_export_btn.clicked.connect(self._on_batch_export)
        
        device_cred_layout.addWidget(self.manage_credentials_btn)
        device_cred_layout.addWidget(self.batch_export_btn)
        device_cred_layout.addStretch()
        
        device_layout.addWidget(self.target_tabs)
        device_layout.addLayout(device_cred_layout)
        
        # Command list panel
        command_panel = QWidget()
        command_layout = QVBoxLayout(command_panel)
        command_layout.setContentsMargins(0, 0, 0, 0)
        
        # Command set selector
        command_set_widget = QWidget()
        command_set_layout = QHBoxLayout(command_set_widget)
        command_set_layout.setContentsMargins(0, 0, 0, 0)
        
        device_type_label = QLabel("Device Type:")
        self.device_type_combo = QComboBox()
        self.device_type_combo.currentIndexChanged.connect(self._on_device_type_changed)
        
        firmware_label = QLabel("Firmware:")
        self.firmware_combo = QComboBox()
        self.firmware_combo.currentIndexChanged.connect(self._on_firmware_changed)
        
        # Command set management buttons
        manage_button = QPushButton("Manage Sets")
        manage_button.clicked.connect(self._on_manage_sets)
        
        import_button = QPushButton("Import")
        import_button.clicked.connect(self._on_import_set)
        
        command_set_layout.addWidget(device_type_label)
        command_set_layout.addWidget(self.device_type_combo, 1)
        command_set_layout.addWidget(firmware_label)
        command_set_layout.addWidget(self.firmware_combo, 1)
        command_set_layout.addWidget(manage_button)
        command_set_layout.addWidget(import_button)
        
        # Command list
        command_label = QLabel("Commands:")
        self.command_table = QTableWidget()
        self.command_table.setColumnCount(3)
        self.command_table.setHorizontalHeaderLabels(["Alias", "Command", "Description"])
        self.command_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.command_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.command_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.command_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.command_table.setSelectionMode(QTableWidget.MultiSelection)
        
        command_layout.addWidget(command_set_widget)
        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_table)
        
        # Add panels to splitter
        top_layout.addWidget(device_panel, 1)
        top_layout.addWidget(command_panel, 1)
        
        # ==================
        # Bottom panel (output)
        # ==================
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Output label and progress
        output_header = QWidget()
        output_header_layout = QHBoxLayout(output_header)
        output_header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.output_label = QLabel("Command Output:")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        output_header_layout.addWidget(self.output_label, 1)
        output_header_layout.addWidget(self.progress_bar)
        
        # Output text view
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        font = QFont("Courier New", 9)
        self.output_text.setFont(font)
        
        bottom_layout.addWidget(output_header)
        bottom_layout.addWidget(self.output_text)
        
        # Add panels to splitter
        splitter.addWidget(top_panel)
        splitter.addWidget(bottom_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        # Add splitter to layout
        layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.run_selected_button = QPushButton("Run Selected Commands")
        self.run_selected_button.clicked.connect(self._on_run_selected)
        
        self.run_all_button = QPushButton("Run All Commands")
        self.run_all_button.clicked.connect(self._on_run_all)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._on_stop)
        
        self.clear_button = QPushButton("Clear Output")
        self.clear_button.clicked.connect(self._on_clear_output)
        
        self.export_button = QPushButton("Export Output")
        self.export_button.clicked.connect(self._on_export_output)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        
        button_layout.addWidget(self.run_selected_button)
        button_layout.addWidget(self.run_all_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def refresh_devices(self):
        """Refresh the device list"""
        from loguru import logger
        logger.debug("Refreshing device list")
        
        # Clear existing items
        self.device_table.setRowCount(0)
        self.group_table.setRowCount(0)
        self.subnet_table.setRowCount(0)
        
        if not self.plugin.device_manager:
            logger.error("Device manager not available")
            return
        
        # Add devices
        devices = self.plugin.device_manager.get_devices()
        self.device_table.setRowCount(len(devices))
        
        for i, device in enumerate(devices):
            # Device name (use alias if available, otherwise hostname, otherwise "Unknown Device")
            name = device.get_property("alias", device.get_property("hostname", "Unknown Device"))
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, device)  # Store device object in the item
            self.device_table.setItem(i, 0, name_item)
            
            # IP address
            ip = device.get_property("ip_address", "")
            ip_item = QTableWidgetItem(ip)
            self.device_table.setItem(i, 1, ip_item)
        
        # Add device groups
        if hasattr(self.plugin.device_manager, 'get_device_groups'):
            try:
                device_groups = self.plugin.device_manager.get_device_groups()
                self.group_table.setRowCount(len(device_groups))
                
                for i, group in enumerate(device_groups):
                    # Group name
                    name_item = QTableWidgetItem(group['name'])
                    name_item.setData(Qt.UserRole, group)  # Store group object in the item
                    self.group_table.setItem(i, 0, name_item)
                    
                    # Device count
                    count_item = QTableWidgetItem(str(len(group['devices'])))
                    self.group_table.setItem(i, 1, count_item)
            except Exception as e:
                logger.error(f"Error getting device groups: {e}")
        
        # Add subnets (group devices by subnet)
        try:
            subnets = {}
            for device in devices:
                ip = device.get_property("ip_address", "")
                if ip:
                    # Extract subnet (first three octets)
                    parts = ip.split('.')
                    if len(parts) == 4:
                        subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
                        if subnet not in subnets:
                            subnets[subnet] = []
                        subnets[subnet].append(device)
            
            self.subnet_table.setRowCount(len(subnets))
            
            for i, (subnet, subnet_devices) in enumerate(subnets.items()):
                # Subnet
                subnet_item = QTableWidgetItem(subnet)
                subnet_info = {'subnet': subnet, 'devices': subnet_devices}
                subnet_item.setData(Qt.UserRole, subnet_info)
                self.subnet_table.setItem(i, 0, subnet_item)
                
                # Device count
                count_item = QTableWidgetItem(str(len(subnet_devices)))
                self.subnet_table.setItem(i, 1, count_item)
        except Exception as e:
            logger.error(f"Error grouping devices by subnet: {e}")
        
    def refresh_command_sets(self):
        """Refresh the command set selectors"""
        # Block signals
        self.device_type_combo.blockSignals(True)
        self.firmware_combo.blockSignals(True)
        
        # Store current selections
        current_device_type = self.device_type_combo.currentText()
        current_firmware = self.firmware_combo.currentText()
        
        # Clear existing items
        self.device_type_combo.clear()
        self.firmware_combo.clear()
        
        # Get available device types
        device_types = self.plugin.get_device_types()
        
        # Add device types
        self.device_type_combo.addItems(device_types)
        
        # Restore selection or select first item
        index = self.device_type_combo.findText(current_device_type)
        if index >= 0:
            self.device_type_combo.setCurrentIndex(index)
        elif self.device_type_combo.count() > 0:
            self.device_type_combo.setCurrentIndex(0)
        
        # Unblock signals
        self.device_type_combo.blockSignals(False)
        self.firmware_combo.blockSignals(False)
        
        # Refresh firmware versions
        self._on_device_type_changed()
        
        # Restore firmware selection
        index = self.firmware_combo.findText(current_firmware)
        if index >= 0:
            self.firmware_combo.setCurrentIndex(index)
            
    def _on_device_type_changed(self):
        """Handle device type selection change"""
        # Block signals
        self.firmware_combo.blockSignals(True)
        
        # Clear firmware combo
        self.firmware_combo.clear()
        
        # Get selected device type
        device_type = self.device_type_combo.currentText()
        
        if device_type:
            # Get firmware versions for selected device type
            firmware_versions = self.plugin.get_firmware_versions(device_type)
            
            # Add firmware versions
            self.firmware_combo.addItems(firmware_versions)
            
        # Unblock signals
        self.firmware_combo.blockSignals(False)
        
        # Refresh commands
        self._on_firmware_changed()
        
    def _on_firmware_changed(self):
        """Handle firmware selection change"""
        # Clear command table
        self.command_table.setRowCount(0)
        
        # Get selected device type and firmware
        device_type = self.device_type_combo.currentText()
        firmware = self.firmware_combo.currentText()
        
        if not device_type or not firmware:
            return
            
        # Get command set
        command_set = self.plugin.get_command_set(device_type, firmware)
        
        if not command_set:
            return
            
        # Add commands to table
        for command in command_set.commands:
            row = self.command_table.rowCount()
            self.command_table.insertRow(row)
            
            # Command info
            alias = QTableWidgetItem(command.alias)
            command_text = QTableWidgetItem(command.command)
            description = QTableWidgetItem(command.description)
            
            # Store command data
            alias.setData(Qt.UserRole, {
                "command": command.command,
                "alias": command.alias,
                "description": command.description
            })
            
            # Add to table
            self.command_table.setItem(row, 0, alias)
            self.command_table.setItem(row, 1, command_text)
            self.command_table.setItem(row, 2, description)
            
    def _on_manage_sets(self):
        """Handle manage command sets button"""
        # Open command set editor
        from .command_set_editor import CommandSetEditor
        editor = CommandSetEditor(self.plugin, self)
        
        if editor.exec() == QDialog.Accepted:
            # Refresh command sets
            self.refresh_command_sets()
            
    def _on_import_set(self):
        """Handle import command set button"""
        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Command Set",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        # Load file
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                
            # Validate command set
            required_fields = ["device_type", "firmware_version", "commands"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Create command set
            from ..utils.command_set import CommandSet
            command_set = CommandSet.from_dict(data)
            
            # Add command set
            self.plugin.add_command_set(command_set)
            
            # Refresh command sets
            self.refresh_command_sets()
            
            # Select the imported command set
            device_type_index = self.device_type_combo.findText(command_set.device_type)
            if device_type_index >= 0:
                self.device_type_combo.setCurrentIndex(device_type_index)
                
                firmware_index = self.firmware_combo.findText(command_set.firmware_version)
                if firmware_index >= 0:
                    self.firmware_combo.setCurrentIndex(firmware_index)
                    
            # Show success message
            QMessageBox.information(
                self,
                "Import Successful",
                f"Command set '{command_set.device_type} {command_set.firmware_version}' imported successfully."
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Import Failed",
                f"Failed to import command set: {e}"
            )
            
    def _on_run_selected(self):
        """Run selected commands on selected devices"""
        from loguru import logger
        
        # Get selected target type
        current_tab = self.target_tabs.currentWidget()
        
        # Get selected commands
        selected_commands = []
        for item in self.command_table.selectedItems():
            row = item.row()
            # Only process each row once (in case multiple cells in the row are selected)
            if row not in [command["row"] for command in selected_commands]:
                command_item = self.command_table.item(row, 0)
                if command_item:
                    command_data = command_item.data(Qt.UserRole)
                    if command_data:
                        command_data["row"] = row
                        selected_commands.append(command_data)
        
        if not selected_commands:
            QMessageBox.warning(self, "No Commands Selected", "Please select at least one command to run.")
            return
        
        # Get selected target devices based on the active tab
        selected_devices = []
        if current_tab == self.target_tabs.widget(0):  # Devices tab
            # Get selected devices
            for item in self.device_table.selectedItems():
                row = item.row()
                device_item = self.device_table.item(row, 0)
                if device_item and device_item.data(Qt.UserRole) not in selected_devices:
                    selected_devices.append(device_item.data(Qt.UserRole))
        elif current_tab == self.target_tabs.widget(1):  # Groups tab
            # Get devices from selected groups
            for item in self.group_table.selectedItems():
                row = item.row()
                group_item = self.group_table.item(row, 0)
                if group_item:
                    group = group_item.data(Qt.UserRole)
                    if group and 'devices' in group:
                        for device in group['devices']:
                            if device not in selected_devices:
                                selected_devices.append(device)
        elif current_tab == self.target_tabs.widget(2):  # Subnets tab
            # Get devices from selected subnets
            for item in self.subnet_table.selectedItems():
                row = item.row()
                subnet_item = self.subnet_table.item(row, 0)
                if subnet_item:
                    subnet_info = subnet_item.data(Qt.UserRole)
                    if subnet_info and 'devices' in subnet_info:
                        for device in subnet_info['devices']:
                            if device not in selected_devices:
                                selected_devices.append(device)
        
        if not selected_devices:
            QMessageBox.warning(self, "No Devices Selected", "Please select at least one device to run commands on.")
            return
        
        # Get current command set
        device_type = self.device_type_combo.currentText()
        firmware = self.firmware_combo.currentText()
        command_set = None
        if device_type and firmware:
            command_set = self.plugin.get_command_set(device_type, firmware)
        
        # Run the commands
        self._run_commands(selected_devices, selected_commands, command_set)

    def _on_run_all(self):
        """Run all commands on selected devices"""
        from loguru import logger
        
        # Get selected target type
        current_tab = self.target_tabs.currentWidget()
        
        # Get all commands
        all_commands = []
        for row in range(self.command_table.rowCount()):
            command_item = self.command_table.item(row, 0)
            if command_item:
                command_data = command_item.data(Qt.UserRole)
                if command_data:
                    command_data["row"] = row
                    all_commands.append(command_data)
        
        if not all_commands:
            QMessageBox.warning(self, "No Commands Available", "There are no commands available to run.")
            return
        
        # Get selected target devices based on the active tab
        selected_devices = []
        if current_tab == self.target_tabs.widget(0):  # Devices tab
            # Get selected devices
            for item in self.device_table.selectedItems():
                row = item.row()
                device_item = self.device_table.item(row, 0)
                if device_item and device_item.data(Qt.UserRole) not in selected_devices:
                    selected_devices.append(device_item.data(Qt.UserRole))
        elif current_tab == self.target_tabs.widget(1):  # Groups tab
            # Get devices from selected groups
            for item in self.group_table.selectedItems():
                row = item.row()
                group_item = self.group_table.item(row, 0)
                if group_item:
                    group = group_item.data(Qt.UserRole)
                    if group and 'devices' in group:
                        for device in group['devices']:
                            if device not in selected_devices:
                                selected_devices.append(device)
        elif current_tab == self.target_tabs.widget(2):  # Subnets tab
            # Get devices from selected subnets
            for item in self.subnet_table.selectedItems():
                row = item.row()
                subnet_item = self.subnet_table.item(row, 0)
                if subnet_item:
                    subnet_info = subnet_item.data(Qt.UserRole)
                    if subnet_info and 'devices' in subnet_info:
                        for device in subnet_info['devices']:
                            if device not in selected_devices:
                                selected_devices.append(device)
        
        if not selected_devices:
            QMessageBox.warning(self, "No Devices Selected", "Please select at least one device to run commands on.")
            return
        
        # Get current command set
        device_type = self.device_type_combo.currentText()
        firmware = self.firmware_combo.currentText()
        command_set = None
        if device_type and firmware:
            command_set = self.plugin.get_command_set(device_type, firmware)
        
        # Run the commands
        self._run_commands(selected_devices, all_commands, command_set)
        
    def _run_commands(self, devices, commands, command_set=None):
        """Run commands on devices"""
        # Check if already running
        if self.worker_thread:
            QMessageBox.warning(
                self,
                "Commands Already Running",
                "Please wait for the current commands to complete."
            )
            return
            
        # Calculate total number of commands
        total_commands = len(devices) * len(commands)
        
        # Set up progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, total_commands)
        self.progress_bar.setValue(0)
        
        # Clear output
        self.output_text.clear()
        
        # Add header
        device_names = [device.get_property("alias", "Unnamed Device") for device in devices]
        command_names = [command["alias"] for command in commands]
        
        self.output_text.append(f"=== Running {len(commands)} command(s) on {len(devices)} device(s) ===")
        self.output_text.append(f"Devices: {', '.join(device_names)}")
        self.output_text.append(f"Commands: {', '.join(command_names)}")
        self.output_text.append("")
        
        # Create worker and thread
        self.worker = CommandWorker(self.plugin, devices, commands, command_set)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.command_started.connect(self._on_command_started)
        self.worker.command_complete.connect(self._on_command_complete)
        self.worker.command_progress.connect(self._on_command_progress)
        self.worker.all_commands_complete.connect(self._on_all_commands_complete)
        
        # Update UI
        self.run_selected_button.setEnabled(False)
        self.run_all_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Start the thread
        self.worker_thread.start()
        
    def _on_command_started(self, device, command):
        """Handle command start event"""
        # Add header to text view
        device_name = device.get_property("alias", "Unnamed Device")
        
        self.output_text.append(f"=== Starting command on: {device_name} ===")
        self.output_text.append(f"Command: {command['command']}")
        self.output_text.append("Executing...")
        
        # Scroll to end - use QTextCursor's MoveOperation.End
        self.output_text.moveCursor(QTextCursor.End)

    def _on_command_progress(self, current, total):
        """Handle command progress updates"""
        self.progress_bar.setValue(current)
        
    def _on_command_complete(self, device, command, result, command_set):
        """Handle command completion"""
        # Add output to text view
        device_name = device.get_property("alias", "Unnamed Device")
        
        self.output_text.append(f"=== Device: {device_name} ===")
        self.output_text.append(f"Command: {command['command']}")
        self.output_text.append(f"Status: {'Success' if result['success'] else 'Failed'}")
        self.output_text.append("")
        self.output_text.append(result["output"])
        self.output_text.append("")
        self.output_text.append("=" * 80)
        self.output_text.append("")
        
        # Scroll to end - use QTextCursor's MoveOperation.End
        self.output_text.moveCursor(QTextCursor.End)
        
    def _on_all_commands_complete(self):
        """Handle all commands complete"""
        # Update UI
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.run_selected_button.setEnabled(True)
        self.run_all_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Add footer
        self.output_text.append("All commands completed.")
        
        # Scroll to end - use QTextCursor's MoveOperation.End
        self.output_text.moveCursor(QTextCursor.End)
        
        # Clean up
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None
            
    def _on_stop(self):
        """Handle stop button"""
        # Stop the worker
        if self.worker:
            self.worker.stop()
            
        # Update UI
        self.stop_button.setEnabled(False)
        
    def _on_clear_output(self):
        """Handle clear output button"""
        self.output_text.clear()
        
    def _on_export_output(self):
        """Handle export output button"""
        # Check if there's output to export
        if not self.output_text.toPlainText():
            QMessageBox.warning(
                self,
                "No Output",
                "There is no output to export."
            )
            return
            
        # Show file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Output",
            "command_output.txt",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        # Save output to file
        try:
            with open(file_path, "w") as f:
                f.write(self.output_text.toPlainText())
                
            QMessageBox.information(
                self,
                "Export Successful",
                f"Output exported to {file_path}"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Export Failed",
                f"Failed to export output: {e}"
            )
            
    def set_selected_devices(self, devices):
        """Set the selected devices in the table
        
        Args:
            devices: List of device objects to select
        """
        # Switch to the Devices tab
        self.target_tabs.setCurrentIndex(0)
        
        # Select the devices in the table
        self.device_table.clearSelection()
        
        for row in range(self.device_table.rowCount()):
            device_item = self.device_table.item(row, 0)
            if device_item and device_item.data(Qt.UserRole) in devices:
                self.device_table.selectRow(row)
                    
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Stop any running commands
        if self.worker:
            self.worker.stop()
            
        # Clean up
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None
            
        # Accept the event
        event.accept()

    def _on_manage_credentials(self):
        """Handle manage credentials button"""
        # Get the selected devices
        selected_devices = []
        for item in self.device_table.selectedItems():
            # Make sure we only count each row once
            if item.column() == 0:
                device_id = item.data(Qt.UserRole)
                device = self.plugin.device_manager.get_device(device_id)
                if device and device not in selected_devices:
                    selected_devices.append(device)
        
        # Open the credential manager with the selected devices
        from ..ui.credential_manager import CredentialManager
        cred_manager = CredentialManager(self.plugin, selected_devices, self)
        cred_manager.setWindowTitle("Device Credential Manager")
        cred_manager.resize(700, 550)
        cred_manager.exec()

    def _on_batch_export(self):
        """Handle batch export button"""
        from plugins.command_manager.reports.command_batch_export import CommandBatchExport
        
        try:
            # Create and display the batch export dialog
            dialog = CommandBatchExport(self.plugin, self)
            
            # Set window title to be more descriptive
            dialog.setWindowTitle("Export Commands from Multiple Devices")
            
            # Execute the dialog
            dialog.exec()
            
        except Exception as e:
            from loguru import logger
            logger.error(f"Error opening Command Batch Export: {e}")
            logger.exception("Exception details:")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error Opening Command Batch Export",
                f"An error occurred while opening the Command Batch Export: {str(e)}"
            ) 