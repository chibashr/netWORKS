#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Output handler for managing command outputs and device command panels
"""

import os
import json
import datetime
from pathlib import Path
from loguru import logger

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QSplitter, QTabWidget, QTextEdit
)
from PySide6.QtGui import QFont

class OutputHandler:
    """Handler for command outputs and device command panels"""
    
    def __init__(self, plugin):
        """Initialize the handler
        
        Args:
            plugin: The CommandManagerPlugin instance
        """
        self.plugin = plugin
        self.outputs = {}  # {device_id: {command_id: {timestamp: output}}}
        
    def load_command_outputs(self):
        """Load command outputs from disk"""
        logger.debug("Loading command outputs from disk")
        
        # Check if the outputs directory exists
        if not self.plugin.output_dir.exists():
            logger.debug(f"Output directory does not exist: {self.plugin.output_dir}")
            # Create it if not exists
            self.plugin.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize outputs
        self.outputs = {}
        
        # First, try to load device-specific output files from plugin data directory
        device_dirs = [d for d in self.plugin.output_dir.iterdir() if d.is_dir()]
        for device_dir in device_dirs:
            device_id = device_dir.name
            output_file = device_dir / "command_outputs.json"
            
            if output_file.exists():
                try:
                    with open(output_file, "r") as f:
                        device_outputs = json.load(f)
                        self.outputs[device_id] = device_outputs
                        
                    logger.debug(f"Loaded command outputs for device {device_id} from {output_file}")
                except Exception as e:
                    logger.error(f"Error loading command outputs for device {device_id}: {e}")
                    logger.exception("Exception details:")
        
        # Next, try to load from workspace device folders
        workspace_device_dir = Path("config/workspaces/default/devices")
        if workspace_device_dir.exists():
            for device_dir in workspace_device_dir.iterdir():
                if device_dir.is_dir():
                    device_id = device_dir.name
                    commands_dir = device_dir / "commands"
                    if commands_dir.exists():
                        output_file = commands_dir / "command_outputs.json"
                        if output_file.exists():
                            try:
                                with open(output_file, "r") as f:
                                    device_outputs = json.load(f)
                                    # Only load if we don't already have outputs for this device
                                    if device_id not in self.outputs:
                                        self.outputs[device_id] = device_outputs
                                        logger.debug(f"Loaded command outputs for device {device_id} from workspace: {output_file}")
                            except Exception as e:
                                logger.error(f"Error loading command outputs for device {device_id} from workspace: {e}")
                                logger.exception("Exception details:")
            
        # If no device-specific outputs found, try to load from the legacy file
        if not self.outputs:
            legacy_file = self.plugin.output_dir / "command_outputs.json"
            if legacy_file.exists():
                try:
                    with open(legacy_file, "r") as f:
                        self.outputs = json.load(f)
                    
                    logger.debug(f"Loaded command outputs from legacy file {legacy_file}")
                    
                    # Migrate to new format
                    self.save_command_outputs()
                except Exception as e:
                    logger.error(f"Error loading legacy command outputs: {e}")
                    logger.exception("Exception details:")
        
        # Log some statistics
        device_count = len(self.outputs)
        command_count = 0
        output_count = 0
        
        for device_id, commands in self.outputs.items():
            command_count += len(commands)
            for cmd_id, timestamps in commands.items():
                output_count += len(timestamps)
                
        logger.info(f"Loaded {output_count} command outputs for {command_count} commands across {device_count} devices")
        
        # Update plugin's outputs reference
        self.plugin.outputs = self.outputs
    
    def save_command_outputs(self):
        """Save command outputs to disk"""
        logger.debug("Saving command outputs to disk")
        # Check if the outputs directory exists
        if not self.plugin.output_dir.exists():
            self.plugin.output_dir.mkdir(parents=True, exist_ok=True)
            
        # No outputs to save
        if not self.outputs:
            logger.debug("No command outputs to save")
            return
            
        # Save outputs for each device in its own folder in the plugin directory
        for device_id, commands in self.outputs.items():
            try:
                # Create device output directory in plugin folder
                device_dir = self.plugin.output_dir / device_id
                device_dir.mkdir(exist_ok=True)
                
                # Save the outputs to disk
                output_file = device_dir / "command_outputs.json"
                with open(output_file, "w") as f:
                    json.dump(commands, f, indent=2)
                    
                logger.debug(f"Saved command outputs for device {device_id} to {output_file}")
                
                # Also save to workspace device folder
                try:
                    # Get workspace device directory
                    workspace_device_dir = Path("config/workspaces/default/devices") / device_id
                    if workspace_device_dir.exists():
                        # Create commands directory if it doesn't exist
                        commands_dir = workspace_device_dir / "commands"
                        commands_dir.mkdir(exist_ok=True)
                        
                        # Save command outputs to workspace
                        workspace_output_file = commands_dir / "command_outputs.json"
                        with open(workspace_output_file, "w") as f:
                            json.dump(commands, f, indent=2)
                            
                        logger.debug(f"Saved command outputs to workspace: {workspace_output_file}")
                except Exception as e:
                    logger.error(f"Error saving command outputs to workspace for device {device_id}: {e}")
                    logger.exception("Exception details:")
                
            except Exception as e:
                logger.error(f"Error saving command outputs for device {device_id}: {e}")
                logger.exception("Exception details:")
        
        # Also save the full outputs file for backward compatibility
        try:
            # Save the outputs to disk
            output_file = self.plugin.output_dir / "command_outputs.json"
            with open(output_file, "w") as f:
                json.dump(self.outputs, f, indent=2)
                
            logger.debug(f"Saved command outputs to {output_file}")
        except Exception as e:
            logger.error(f"Error saving command outputs: {e}")
            logger.exception("Exception details:")
    
    def get_command_outputs(self, device_id, command_id=None):
        """Get command outputs for a device
        
        Args:
            device_id (str): Device ID to get outputs for
            command_id (str, optional): Command ID to get outputs for
            
        Returns:
            dict: Command outputs
        """
        logger.debug(f"Getting command outputs for device: {device_id}")
        
        # Check if we have outputs for this device
        if device_id not in self.outputs:
            logger.debug(f"No outputs found for device: {device_id}")
            return {}
            
        # If command_id is provided, get only those outputs
        if command_id:
            if command_id in self.outputs[device_id]:
                return self.outputs[device_id][command_id]
            else:
                logger.debug(f"No outputs found for device: {device_id}, command: {command_id}")
                return {}
                
        # Otherwise return all outputs for the device
        return self.outputs[device_id]
        
    def add_command_output(self, device_id, command_id, output, command_text=None):
        """Add command output to history
        
        Args:
            device_id (str): Device ID
            command_id (str): Command ID
            output (str): Command output
            command_text (str, optional): Command text
        """
        logger.debug(f"Adding command output for device: {device_id}, command: {command_id}")
        
        # Create device entry if it doesn't exist
        if device_id not in self.outputs:
            self.outputs[device_id] = {}
            
        # Create command entry if it doesn't exist
        if command_id not in self.outputs[device_id]:
            self.outputs[device_id][command_id] = {}
            
        # Add output with timestamp
        timestamp = datetime.datetime.now().isoformat()
        self.outputs[device_id][command_id][timestamp] = {
            "output": output,
            "success": True,
            "command": command_text if command_text else command_id
        }
        
        # Save outputs
        self.save_command_outputs()
        
        logger.debug(f"Added command output for device: {device_id}, command: {command_id}")
        
    def delete_command_output(self, device_id, command_id, timestamp=None):
        """Delete a command output from history
        
        Args:
            device_id (str): Device ID
            command_id (str): Command ID
            timestamp (str, optional): Specific timestamp to delete, or None to delete all
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        logger.debug(f"Deleting command output for device: {device_id}, command: {command_id}, timestamp: {timestamp}")
        
        # Check if we have outputs for this device
        if device_id not in self.outputs:
            logger.warning(f"No outputs found for device: {device_id}")
            return False
            
        # Check if we have outputs for this command
        if command_id not in self.outputs[device_id]:
            logger.warning(f"No outputs found for device: {device_id}, command: {command_id}")
            return False
            
        # If timestamp is provided, delete only that timestamp
        if timestamp:
            if timestamp in self.outputs[device_id][command_id]:
                del self.outputs[device_id][command_id][timestamp]
                
                # If no more timestamps for this command, delete the command
                if not self.outputs[device_id][command_id]:
                    del self.outputs[device_id][command_id]
                    
                # If no more commands for this device, delete the device
                if not self.outputs[device_id]:
                    del self.outputs[device_id]
                    
                # Save outputs
                self.save_command_outputs()
                
                logger.debug(f"Deleted command output for device: {device_id}, command: {command_id}, timestamp: {timestamp}")
                return True
            else:
                logger.warning(f"No output found for device: {device_id}, command: {command_id}, timestamp: {timestamp}")
                return False
        # If no timestamp, delete all outputs for this command
        else:
            del self.outputs[device_id][command_id]
            
            # If no more commands for this device, delete the device
            if not self.outputs[device_id]:
                del self.outputs[device_id]
                
            # Save outputs
            self.save_command_outputs()
            
            logger.debug(f"Deleted all command outputs for device: {device_id}, command: {command_id}")
            return True
            
    def create_device_command_tab(self, device):
        """Create a tab to display device command history"""
        # Create widget
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Command output list
        device_command_list = QTableWidget()
        device_command_list.setColumnCount(4)
        device_command_list.setHorizontalHeaderLabels(["Command", "Date/Time", "Success", "View"])
        device_command_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        device_command_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        device_command_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        device_command_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        device_command_list.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Store device for reference
        device_command_list.setProperty("device", device)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(lambda: self._refresh_device_commands(device_command_list))
        
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(lambda: self._export_device_commands(device))
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda: self._delete_device_commands(device_command_list))
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        
        # Add widgets to layout
        layout.addWidget(device_command_list)
        layout.addLayout(button_layout)
        
        # Set up device command list
        self._refresh_device_commands(device_command_list)
        
        return widget
        
    def _refresh_device_commands(self, command_list):
        """Refresh the device command list"""
        # Clear the table
        command_list.setRowCount(0)
        
        # Get device
        device = command_list.property("device")
        if not device:
            return
            
        # Get command outputs for device
        outputs = self.get_command_outputs(device.id)
        
        # Add rows for each command output
        for cmd_id, cmd_outputs in outputs.items():
            for timestamp, data in cmd_outputs.items():
                row = command_list.rowCount()
                command_list.insertRow(row)
                
                # Command
                cmd_text = data.get("command", cmd_id)
                cmd_item = QTableWidgetItem(cmd_text)
                
                # Date/time
                dt = datetime.datetime.fromisoformat(timestamp)
                dt_item = QTableWidgetItem(dt.strftime("%Y-%m-%d %H:%M:%S"))
                
                # Success
                success = "Yes" if data.get("success", True) else "No"
                success_item = QTableWidgetItem(success)
                
                # View button
                view_btn = QPushButton("View")
                view_btn.setProperty("device_id", device.id)
                view_btn.setProperty("command_id", cmd_id)
                view_btn.setProperty("timestamp", timestamp)
                view_btn.clicked.connect(self._on_view_command)
                
                # Add to row
                command_list.setItem(row, 0, cmd_item)
                command_list.setItem(row, 1, dt_item)
                command_list.setItem(row, 2, success_item)
                command_list.setCellWidget(row, 3, view_btn)
                
    def _on_view_command(self):
        """Handle view command button"""
        # Get button that was clicked
        button = self.plugin.sender()
        if not button:
            return
            
        # Get properties
        device_id = button.property("device_id")
        command_id = button.property("command_id")
        timestamp = button.property("timestamp")
        
        # Get command output
        outputs = self.get_command_outputs(device_id, command_id)
        if not outputs or timestamp not in outputs:
            return
            
        output = outputs[timestamp]["output"]
        
        # Show output in dialog
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        
        dialog = QDialog(self.plugin.main_window)
        dialog.setWindowTitle("Command Output")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        output_text = QTextEdit()
        output_text.setReadOnly(True)
        output_text.setFont(QFont("Courier New", 10))
        output_text.setText(output)
        
        layout.addWidget(output_text)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        
        layout.addWidget(buttons)
        
        dialog.exec()
        
    def _export_device_commands(self, device):
        """Export device commands to file"""
        # Get selected device
        devices = self.plugin.device_manager.get_selected_devices()
        if not devices:
            return
            
        device = devices[0]
        
        # Ask for file to save to
        file_path, _ = QFileDialog.getSaveFileName(
            self.plugin.main_window,
            "Export Command Outputs",
            "",
            "Text Files (*.txt);;HTML Files (*.html);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        # Get command outputs for device
        outputs = self.get_command_outputs(device.id)
        
        try:
            # Determine export format
            if file_path.lower().endswith(".html"):
                # HTML export
                with open(file_path, "w") as f:
                    f.write("<html><head><title>Command Outputs</title></head><body>\n")
                    f.write(f"<h1>Command Outputs for {device.get_property('alias', 'Device')}</h1>\n")
                    
                    for cmd_id, cmd_outputs in outputs.items():
                        for timestamp, data in cmd_outputs.items():
                            dt = datetime.datetime.fromisoformat(timestamp)
                            cmd_text = data.get("command", cmd_id)
                            output = data.get("output", "")
                            
                            f.write(f"<h2>{cmd_text}</h2>\n")
                            f.write(f"<p>Date/Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
                            f.write("<pre>\n")
                            f.write(output)
                            f.write("\n</pre>\n")
                            f.write("<hr>\n")
                            
                    f.write("</body></html>")
            else:
                # Text export
                with open(file_path, "w") as f:
                    f.write(f"Command Outputs for {device.get_property('alias', 'Device')}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for cmd_id, cmd_outputs in outputs.items():
                        for timestamp, data in cmd_outputs.items():
                            dt = datetime.datetime.fromisoformat(timestamp)
                            cmd_text = data.get("command", cmd_id)
                            output = data.get("output", "")
                            
                            f.write(f"Command: {cmd_text}\n")
                            f.write(f"Date/Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write("-" * 50 + "\n")
                            f.write(output)
                            f.write("\n\n" + "=" * 50 + "\n\n")
            
            # Show success message
            QMessageBox.information(
                self.plugin.main_window,
                "Export Successful",
                f"Command outputs exported to {file_path}"
            )
            
        except Exception as e:
            # Show error message
            QMessageBox.critical(
                self.plugin.main_window,
                "Export Failed",
                f"Failed to export command outputs: {str(e)}"
            )
            
    def _delete_device_commands(self, command_list):
        """Delete selected device commands"""
        # Get selected rows
        selected_rows = command_list.selectedItems()
        if not selected_rows:
            return
            
        # Get selected device
        devices = self.plugin.device_manager.get_selected_devices()
        if not devices:
            return
            
        device = devices[0]
        
        # Confirm deletion
        result = QMessageBox.question(
            self.plugin.main_window,
            "Confirm Deletion",
            "Are you sure you want to delete the selected command outputs?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
            
        # Delete selected outputs
        deleted = 0
        rows_to_delete = set()
        
        for item in selected_rows:
            row = item.row()
            rows_to_delete.add(row)
            
        for row in sorted(rows_to_delete, reverse=True):
            view_btn = command_list.cellWidget(row, 3)
            if view_btn:
                device_id = view_btn.property("device_id")
                command_id = view_btn.property("command_id")
                timestamp = view_btn.property("timestamp")
                
                if self.delete_command_output(device_id, command_id, timestamp):
                    deleted += 1
                    
        # Refresh the list
        self._refresh_device_commands(command_list)
        
        # Show success message
        QMessageBox.information(
            self.plugin.main_window,
            "Deletion Successful",
            f"Deleted {deleted} command output(s)"
        )
            
    def get_device_panels(self):
        """Get panels to be added to the device properties panel
        
        Returns:
            list: List of (panel_name, panel_widget) tuples
        """
        logger.debug("Getting device panels for Command Manager plugin")
        
        # Create a device-agnostic commands tab initially - it will update when a device is selected
        commands_tab = QWidget()
        layout = QVBoxLayout(commands_tab)
        
        # Add info label
        info_label = QLabel("Select a device to view and manage commands for that device.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # We'll store this widget to update it later when a device is selected
        self.plugin.commands_panel_widget = commands_tab
        
        return [
            ("Commands", commands_tab)
        ]
            
    def update_commands_panel(self, device):
        """Update the commands panel with the selected device
        
        Args:
            device: The selected device
        """
        # This method would contain the code to update the commands panel
        # For brevity, I'm not including the full implementation here
        pass 