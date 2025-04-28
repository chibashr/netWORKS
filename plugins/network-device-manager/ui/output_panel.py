#!/usr/bin/env python3
# Network Device Manager - Output Panel UI Component

import os
import csv
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFileDialog, QLineEdit,
    QGroupBox, QFormLayout, QMessageBox, QTabWidget,
    QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

class QuickCommandPanel(QWidget):
    """
    Panel for quickly running commands on selected devices.
    """
    
    def __init__(self, plugin_api, command_manager, connection_handler):
        super().__init__()
        self.api = plugin_api
        self.command_manager = command_manager
        self.connection_handler = connection_handler
        self.current_device = None
        self.device_manager = None
        self.command_output_signal = Signal(str, str, str)  # device_ip, command, output
        
        self._init_ui()
        
        # Connect directly to device_selected signals if available
        try:
            if hasattr(self.api, 'main_window') and hasattr(self.api.main_window, 'device_table'):
                self.api.log("QuickCommandPanel: Connecting to device table", level="DEBUG")
                if hasattr(self.api.main_window.device_table, 'device_selected'):
                    self.api.main_window.device_table.device_selected.connect(self.on_device_selected)
                    self.api.log("QuickCommandPanel: Connected to device_table signals", level="DEBUG")
        except Exception as e:
            self.api.log(f"QuickCommandPanel: Error connecting to signals: {str(e)}", level="ERROR")
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Device selection info
        device_info_layout = QHBoxLayout()
        self.device_label = QLabel("Selected Device: None")
        self.device_label.setStyleSheet("font-weight: bold;")
        device_info_layout.addWidget(self.device_label)
        
        self.device_type_combo = QComboBox()
        self.device_type_combo.addItem("Unknown", "unknown")
        self.device_type_combo.currentIndexChanged.connect(self._load_commands)
        device_info_layout.addWidget(QLabel("Device Type:"))
        device_info_layout.addWidget(self.device_type_combo)
        
        layout.addLayout(device_info_layout)
        
        # Main layout with commands and output
        main_layout = QHBoxLayout()
        
        # Left side - Commands list
        command_group = QGroupBox("Available Commands")
        command_layout = QVBoxLayout(command_group)
        
        # Command list
        self.command_list = QListWidget()
        self.command_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.command_list.itemSelectionChanged.connect(self._on_command_selected)
        command_layout.addWidget(self.command_list)
        
        # Command buttons
        command_button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run Command")
        self.run_button.clicked.connect(self._run_selected_command)
        self.run_button.setEnabled(False)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_output)
        
        command_button_layout.addWidget(self.run_button)
        command_button_layout.addWidget(self.clear_button)
        command_layout.addLayout(command_button_layout)
        
        main_layout.addWidget(command_group, 1)  # 1 part width
        
        # Right side - Output display
        output_group = QGroupBox("Command Output")
        output_layout = QVBoxLayout(output_group)
        
        # Command info
        self.command_info = QLabel("No command selected")
        output_layout.addWidget(self.command_info)
        
        # Output display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont("Courier New", 10))
        output_layout.addWidget(self.output_display)
        
        # Output buttons
        output_button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save Output")
        self.save_button.clicked.connect(self._save_output)
        self.save_button.setEnabled(False)
        
        output_button_layout.addWidget(self.save_button)
        output_button_layout.addStretch()
        
        output_layout.addLayout(output_button_layout)
        
        main_layout.addWidget(output_group, 2)  # 2 parts width (twice as wide)
        
        layout.addLayout(main_layout)
        
        # Connection status
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
    
    def set_device_manager(self, device_manager):
        """Set the device manager to use."""
        self.device_manager = device_manager
        self._load_device_types()
    
    def _load_device_types(self):
        """Load device types from command manager."""
        try:
            # Store current selection
            current_type = self.device_type_combo.currentData()
            
            # Clear and reload
            self.device_type_combo.clear()
            self.device_type_combo.addItem("Unknown", "unknown")
            
            # Add device types from command manager
            device_types = []
            command_types = self.command_manager.get_device_type_display_names()
            for device_type, display_name in command_types.items():
                device_types.append((device_type, display_name))
            
            # Sort types for better display
            sorted_types = sorted(device_types, key=lambda x: x[1])
            
            # Add sorted types
            for device_type, display_name in sorted_types:
                self.device_type_combo.addItem(display_name, device_type)
            
            # Try to restore previous selection
            if current_type:
                index = self.device_type_combo.findData(current_type)
                if index >= 0:
                    self.device_type_combo.setCurrentIndex(index)
        except Exception as e:
            self.api.log(f"Error loading device types: {str(e)}", level="ERROR")
    
    def _load_commands(self):
        """Load commands for the selected device type."""
        try:
            # Clear commands
            self.command_list.clear()
            
            # Get device type
            device_type = self.device_type_combo.currentData()
            if not device_type:
                return
            
            # Get commands
            commands = self.command_manager.get_commands_for_device_type(device_type)
            
            # Add commands to list
            for command_id, command_info in commands.items():
                item = QListWidgetItem(f"{command_info.get('command', '')}")
                item.setToolTip(command_info.get('description', ''))
                item.setData(Qt.ItemDataRole.UserRole, {
                    'id': command_id,
                    'command': command_info.get('command', ''),
                    'description': command_info.get('description', ''),
                    'output_type': command_info.get('output_type', 'text')
                })
                self.command_list.addItem(item)
        except Exception as e:
            self.api.log(f"Error loading commands: {str(e)}", level="ERROR")
    
    def update_device(self, device):
        """Update the selected device."""
        self.current_device = device
        
        if device:
            self.device_label.setText(f"Selected Device: {device.get('ip', 'Unknown')} ({device.get('hostname', 'Unknown')})")
            
            # Set device type if available
            device_type = device.get('device_type', 'unknown')
            index = self.device_type_combo.findData(device_type)
            if index >= 0:
                self.device_type_combo.setCurrentIndex(index)
            
            # Enable run button if command selected
            self.run_button.setEnabled(self.command_list.currentItem() is not None)
        else:
            self.device_label.setText("Selected Device: None")
            self.run_button.setEnabled(False)
    
    def _on_command_selected(self):
        """Handle command selection."""
        item = self.command_list.currentItem()
        if item and self.current_device:
            command_data = item.data(Qt.ItemDataRole.UserRole)
            self.command_info.setText(f"Command: {command_data.get('command')} - {command_data.get('description')}")
            self.run_button.setEnabled(True)
        else:
            self.command_info.setText("No command selected")
            self.run_button.setEnabled(False)
    
    def _run_selected_command(self):
        """Run the selected command on the current device."""
        if not self.current_device:
            self.status_label.setText("Error: No device selected")
            return
        
        item = self.command_list.currentItem()
        if not item:
            self.status_label.setText("Error: No command selected")
            return
        
        # Get command info
        command_data = item.data(Qt.ItemDataRole.UserRole)
        command = command_data.get('command')
        
        # Save the current device type to the device dictionary
        current_device_type = self.device_type_combo.currentData()
        if current_device_type and current_device_type != self.current_device.get('device_type'):
            self.current_device['device_type'] = current_device_type
            # Update the device in the device manager if available
            if self.device_manager:
                try:
                    self.device_manager.update_device(self.current_device)
                    self.api.log(f"Updated device type to {current_device_type} for device {self.current_device.get('ip')}", level="DEBUG")
                except Exception as e:
                    self.api.log(f"Failed to update device type in database: {str(e)}", level="WARNING")
        
        # Update UI
        self.status_label.setText(f"Connecting to {self.current_device.get('ip')}...")
        self.output_display.clear()
        self.output_display.append(f"Running command: {command}\n")
        
        # Connect and run command
        try:
            # Try to connect
            success, message, connection_id = self.connection_handler.connect(self.current_device, "ssh")
            
            if not success:
                # Try telnet if SSH fails
                self.output_display.append(f"SSH connection failed: {message}\n")
                self.output_display.append("Trying telnet...\n")
                success, message, connection_id = self.connection_handler.connect(self.current_device, "telnet")
            
            if success:
                # Run command
                self.status_label.setText(f"Connected to {self.current_device.get('ip')}, running command...")
                success, output = self.connection_handler.execute_command(connection_id, command)
                
                if success:
                    # Display output
                    self.output_display.append(output)
                    self.status_label.setText("Command completed successfully")
                    self.save_button.setEnabled(True)
                    
                    # Save command history
                    self._save_command_history(command, command_data.get('output_type', 'text'), output)
                else:
                    self.output_display.append(f"Error executing command: {output}")
                    self.status_label.setText("Command execution failed")
                
                # Disconnect
                self.connection_handler.disconnect(connection_id)
            else:
                self.output_display.append(f"Connection failed: {message}")
                self.status_label.setText("Connection failed")
        except Exception as e:
            self.output_display.append(f"Error: {str(e)}")
            self.status_label.setText("Error executing command")
            self.api.log(f"Error executing command: {str(e)}", level="ERROR")
    
    def _save_command_history(self, command, output_type, output):
        """Save command to history."""
        try:
            # Skip if no device manager
            if not self.device_manager:
                return
                
            # Get the output directory
            output_dir = self.device_manager.output_dir
            
            # Create device directory if it doesn't exist
            device_dir = output_dir / self.current_device['ip'].replace('.', '_')
            device_dir.mkdir(exist_ok=True)
            
            # Save output to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = device_dir / f"{command.replace(' ', '_')}_{timestamp}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            
            # Create history file if it doesn't exist
            history_file = device_dir / "command_history.csv"
            
            # Save to history file
            mode = 'a' if history_file.exists() else 'w'
            with open(history_file, mode, newline='') as f:
                writer = csv.writer(f)
                if mode == 'w':
                    writer.writerow(['Command', 'Timestamp', 'Type'])
                writer.writerow([command, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), output_type])
            
            # Add to database if available
            try:
                self.device_manager.add_command_output(
                    self.current_device['ip'],
                    command,
                    str(output_file),
                    output_type
                )
            except Exception as db_error:
                self.api.log(f"Error adding output to database: {str(db_error)}", level="DEBUG")
            
            self.api.log(f"Command output saved to {output_file}", level="DEBUG")
        except Exception as e:
            self.api.log(f"Error saving command history: {str(e)}", level="ERROR")
    
    def _save_output(self):
        """Save the command output to a file."""
        if not self.output_display.toPlainText():
            return
            
        try:
            # Get command name
            item = self.command_list.currentItem()
            if item:
                command_data = item.data(Qt.ItemDataRole.UserRole)
                command = command_data.get('command', 'command').replace(' ', '_')
            else:
                command = "command"
                
            # Generate file name suggestion
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            device_ip = self.current_device.get('ip', 'unknown').replace('.', '_')
            suggested_name = f"{device_ip}_{command}_{timestamp}.txt"
            
            # Open save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Command Output",
                suggested_name,
                "Text Files (*.txt)"
            )
            
            if file_path:
                # Save output
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.output_display.toPlainText())
                
                self.status_label.setText(f"Output saved to {file_path}")
        except Exception as e:
            self.status_label.setText(f"Error saving output: {str(e)}")
            self.api.log(f"Error saving output: {str(e)}", level="ERROR")
    
    def _clear_output(self):
        """Clear the output display."""
        self.output_display.clear()
        self.command_info.setText("No command selected")
        self.save_button.setEnabled(False)
        self.status_label.setText("Ready")
    
    @Slot(object)
    def on_device_selected(self, device):
        """Handle device selection."""
        try:
            self.update_device(device)
        except Exception as e:
            self.api.log(f"Error in device selection: {str(e)}", level="ERROR")

class OutputPanel(QWidget):
    """
    Panel for displaying command output.
    Simplified to focus on viewing command results only.
    """
    
    def __init__(self, plugin_api, output_dir):
        super().__init__()
        self.api = plugin_api
        self.output_dir = Path(output_dir)
        self.current_device = None
        self.current_output_path = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Title and info area
        title_layout = QHBoxLayout()
        title = QLabel("Command Output")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.output_info = QLabel("No output selected")
        
        title_layout.addWidget(title)
        title_layout.addWidget(self.output_info, 1)  # Give it stretch
        
        layout.addLayout(title_layout)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self._download_output)
        self.download_button.setEnabled(False)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_output_display)
        
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Output viewer
        self.output_viewer = QTextEdit()
        self.output_viewer.setReadOnly(True)
        self.output_viewer.setFont(QFont("Courier New", 10))
        
        layout.addWidget(self.output_viewer, 1)  # Give it stretch
    
    def _clear_output_display(self):
        """Clear the output viewer display."""
        self.output_viewer.clear()
        self.output_info.setText("No output selected")
        self.download_button.setEnabled(False)
        self.current_output_path = None
    
    def update_device(self, device):
        """Update panel with device information."""
        self.current_device = device
    
    def filter_by_device(self, device_ip):
        """No-op in simplified version - kept for compatibility."""
        pass
    
    def view_output(self, output_path, command):
        """View output content."""
        try:
            # Store current output path
            self.current_output_path = output_path
            
            # Update info
            path = Path(output_path)
            device = path.parent.name
            self.output_info.setText(f"Device: {device}, Command: {command}")
            
            # Check if file exists
            if not os.path.exists(output_path):
                self.output_viewer.setText(f"File not found: {output_path}")
                return
                
            # Read file
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Display content
            self.output_viewer.setText(content)
            
            # Enable download button
            self.download_button.setEnabled(True)
        except Exception as e:
            self.api.log(f"Error viewing output: {str(e)}", level="ERROR")
            self.output_viewer.setText(f"Error viewing output: {str(e)}")
    
    def _download_output(self):
        """Download selected output."""
        if not self.current_output_path:
            return
            
        try:
            # Open file dialog to select download location
            filters = "All Files (*.*)"
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Command Output",
                "",
                filters
            )
            
            if not save_path:
                return
                
            # Copy file to selected location
            import shutil
            shutil.copy2(self.current_output_path, save_path)
            
            self.api.log(f"Output saved to {save_path}")
            QMessageBox.information(self, "Output Saved", f"Command output saved to {save_path}")
        except Exception as e:
            self.api.log(f"Error downloading output: {str(e)}", level="ERROR")
            QMessageBox.warning(self, "Download Error", f"Error downloading output: {str(e)}")
    
    def view_output_text(self, command, output_text, device_ip):
        """Display command output text directly in the panel without reading from a file."""
        try:
            # Update info
            self.output_info.setText(f"Device: {device_ip}, Command: {command}")
            
            # Display content
            self.output_viewer.setText(output_text)
            
            # No output path, so disable download button
            self.download_button.setEnabled(False)
            
            self.api.log(f"Displayed command output for {command} on {device_ip}", level="DEBUG")
        except Exception as e:
            self.api.log(f"Error displaying output text: {str(e)}", level="ERROR")
            self.output_viewer.setText(f"Error displaying output: {str(e)}") 