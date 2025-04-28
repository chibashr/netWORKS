#!/usr/bin/env python3
# Network Device Manager - Device Panel UI Component

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFormLayout, QGroupBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, Slot
from pathlib import Path
import csv
from datetime import datetime

class DevicePanel(QWidget):
    """
    Panel for displaying and managing device information.
    Shows device details and provides controls for device operations.
    """
    
    def __init__(self, plugin_api, device_manager):
        super().__init__()
        self.api = plugin_api
        self.device_manager = device_manager
        # Get credential_manager from the device_manager's credential_manager attribute
        self.credential_manager = device_manager.credential_manager if hasattr(device_manager, 'credential_manager') else None
        self.current_device = None
        
        self._init_ui()
        
        # Connect directly to device_selected signals if available
        try:
            # Try to connect to main window's device table if it exists
            if hasattr(self.api, 'main_window') and hasattr(self.api.main_window, 'device_table'):
                self.api.log("DevicePanel: Connecting directly to main window's device table", level="DEBUG")
                if hasattr(self.api.main_window.device_table, 'device_selected'):
                    self.api.main_window.device_table.device_selected.connect(self.on_device_selected)
                    self.api.log("DevicePanel: Successfully connected to device_table device_selected signal", level="DEBUG")
        except Exception as e:
            self.api.log(f"DevicePanel: Error connecting to device selection signals: {str(e)}", level="ERROR")
    
    @Slot(object)
    def on_device_selected(self, device):
        """Public slot to handle device selection events directly."""
        try:
            self.api.log(f"DevicePanel.on_device_selected: Received direct selection signal for device: {device.get('ip') if isinstance(device, dict) else 'Unknown type'}", level="DEBUG")
            self.update_device(device)
        except Exception as e:
            self.api.log(f"DevicePanel.on_device_selected error: {str(e)}", level="ERROR")
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Device Manager")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Device info section
        self.device_info_group = QGroupBox("Device Information")
        device_info_layout = QFormLayout(self.device_info_group)
        
        self.device_ip_label = QLabel("No device selected")
        self.device_mac_label = QLabel("-")
        self.device_hostname_label = QLabel("-")
        self.device_type_combo = QComboBox()
        self.device_type_combo.setEnabled(False)
        self.device_type_combo.currentIndexChanged.connect(self._on_device_type_changed)
        
        device_info_layout.addRow("IP Address:", self.device_ip_label)
        device_info_layout.addRow("MAC Address:", self.device_mac_label)
        device_info_layout.addRow("Hostname:", self.device_hostname_label)
        device_info_layout.addRow("Device Type:", self.device_type_combo)
        
        layout.addWidget(self.device_info_group)
        
        # Command execution section
        self.command_group = QGroupBox("Execute Commands")
        command_layout = QVBoxLayout(self.command_group)
        
        # Connection type selection
        conn_type_layout = QHBoxLayout()
        conn_type_layout.addWidget(QLabel("Connection:"))
        self.conn_type_combo = QComboBox()
        self.conn_type_combo.addItem("SSH", "ssh")
        self.conn_type_combo.addItem("Telnet", "telnet")
        conn_type_layout.addWidget(self.conn_type_combo)
        conn_type_layout.addStretch()
        command_layout.addLayout(conn_type_layout)
        
        # Command list
        command_layout.addWidget(QLabel("Available Commands:"))
        self.command_list = QListWidget()
        self.command_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        command_layout.addWidget(self.command_list)
        
        # Command buttons
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Selected")
        self.run_button.clicked.connect(self._run_selected_commands)
        self.run_button.setEnabled(False)
        button_layout.addWidget(self.run_button)
        
        self.credentials_button = QPushButton("Credentials")
        self.credentials_button.clicked.connect(self._manage_credentials)
        button_layout.addWidget(self.credentials_button)
        
        command_layout.addLayout(button_layout)
        
        # Status indicator
        self.status_label = QLabel("Ready")
        command_layout.addWidget(self.status_label)
        
        layout.addWidget(self.command_group)
        
        # Command history section
        self.command_history_group = QGroupBox("Command History")
        history_layout = QVBoxLayout(self.command_history_group)
        
        self.command_history_table = QTableWidget(0, 3)
        self.command_history_table.setHorizontalHeaderLabels(["Command", "Time", "Type"])
        self.command_history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.command_history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.command_history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.command_history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        history_layout.addWidget(self.command_history_table)
        
        # History buttons
        history_button_layout = QHBoxLayout()
        self.view_output_button = QPushButton("View Output")
        self.view_output_button.clicked.connect(self._view_selected_output)
        self.view_output_button.setEnabled(False)
        
        self.download_output_button = QPushButton("Download")
        self.download_output_button.clicked.connect(self._download_selected_output)
        self.download_output_button.setEnabled(False)
        
        history_button_layout.addWidget(self.view_output_button)
        history_button_layout.addWidget(self.download_output_button)
        history_layout.addLayout(history_button_layout)
        
        layout.addWidget(self.command_history_group)
        
        # Add credential status at the bottom
        self.credentials_group = QGroupBox("Credentials")
        credentials_layout = QVBoxLayout(self.credentials_group)
        
        self.credentials_status = QLabel("No credentials set")
        credentials_layout.addWidget(self.credentials_status)
        
        layout.addWidget(self.credentials_group)
        
        # Load device types
        self._load_device_types()
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Connect history selection changed
        self.command_history_table.selectionModel().selectionChanged.connect(self._on_history_selection_changed)
    
    def update_device(self, device):
        """Update panel with device information."""
        # Add more detailed debug logging
        try:
            if device is None:
                self.api.log("DevicePanel.update_device called with None device", level="DEBUG")
            elif isinstance(device, dict):
                self.api.log(f"DevicePanel.update_device called with device: IP={device.get('ip')}, ID={device.get('id')}", level="DEBUG")
            else:
                self.api.log(f"DevicePanel.update_device called with unexpected type: {type(device)}", level="WARNING")
                return  # Early return for invalid types
            
            # Store the device reference
            self.current_device = device
            
            if device:
                try:
                    # Update device info with more robust error handling
                    self.device_ip_label.setText(device.get('ip', '-'))
                    self.device_mac_label.setText(device.get('mac', '-'))
                    self.device_hostname_label.setText(device.get('hostname', '-'))
                    
                    # Enable controls
                    self.conn_type_combo.setEnabled(True)
                    self.device_type_combo.setEnabled(True)
                    
                    # Set device type
                    device_type = device.get('device_type', 'unknown')
                    index = self.device_type_combo.findData(device_type)
                    if index >= 0:
                        self.device_type_combo.setCurrentIndex(index)
                    else:
                        self.device_type_combo.setCurrentIndex(0)  # Default to first type
                    
                    # Load commands for the device type
                    self._load_commands_for_device_type(device_type)
                        
                    # Update command history
                    self._update_command_history()
                    
                    # Update credentials status
                    self._update_credentials_status()
                    
                    # Log success
                    self.api.log(f"Successfully updated device panel with device: {device.get('ip')}", level="DEBUG")
                except Exception as e:
                    self.api.log(f"Error updating device info UI elements: {str(e)}", level="ERROR")
            else:
                try:
                    # Clear device info
                    self.device_ip_label.setText("No device selected")
                    self.device_mac_label.setText("-")
                    self.device_hostname_label.setText("-")
                    
                    # Disable controls
                    self.conn_type_combo.setEnabled(False)
                    self.device_type_combo.setEnabled(False)
                    
                    # Clear command list
                    self.command_list.clear()
                    
                    # Clear command history
                    self.command_history_table.setRowCount(0)
                    
                    # Clear credentials status
                    self.credentials_status.setText("No credentials set")
                    
                    self.api.log("Device panel cleared due to None device", level="DEBUG")
                except Exception as e:
                    self.api.log(f"Error clearing device panel: {str(e)}", level="ERROR")
            
            # Disable output buttons
            self.view_output_button.setEnabled(False)
            self.download_output_button.setEnabled(False)
        except Exception as e:
            self.api.log(f"Unexpected error in update_device: {str(e)}", level="ERROR")
    
    def _load_device_types(self):
        """Load device types from the command manager."""
        try:
            # Get existing device types
            current_type = self.device_type_combo.currentData()
            
            # Clear the combo box
            self.device_type_combo.clear()
            
            # Add types from command manager
            device_types = []
            
            # Add "unknown" type first
            device_types.append(("unknown", "Unknown"))
            
            # Get device types from command manager if available
            # Try multiple ways to get command_manager
            command_manager = None
            
            # First, try to get from device_manager
            if hasattr(self.device_manager, 'command_manager'):
                command_manager = self.device_manager.command_manager
            
            # If not found, try to get from plugin instance
            if not command_manager and hasattr(self.api, 'get_plugin_instance'):
                plugin = self.api.get_plugin_instance('network-device-manager')
                if plugin and hasattr(plugin, 'command_manager'):
                    command_manager = plugin.command_manager
            
            # Try to get from main window plugin manager as last resort
            if not command_manager and hasattr(self.api, 'main_window'):
                plugin_mgr = getattr(self.api.main_window, 'plugin_manager', None)
                if plugin_mgr and hasattr(plugin_mgr, 'plugins'):
                    plugin_info = plugin_mgr.plugins.get('network-device-manager', {})
                    plugin_instance = plugin_info.get('instance')
                    if plugin_instance and hasattr(plugin_instance, 'command_manager'):
                        command_manager = plugin_instance.command_manager
            
            if command_manager:
                command_types = command_manager.get_device_type_display_names()
                for device_type, display_name in command_types.items():
                    device_types.append((device_type, display_name))
            
            # Sort types for better display (but keep unknown first)
            device_types = [device_types[0]] + sorted(device_types[1:], key=lambda x: x[1])
            
            # Add all types to combo box
            for device_type, display_name in device_types:
                self.device_type_combo.addItem(display_name, device_type)
            
            # Try to restore the previously selected type
            if current_type:
                index = self.device_type_combo.findData(current_type)
                if index >= 0:
                    self.device_type_combo.setCurrentIndex(index)
                    
            # Store command manager reference for later use
            self.command_manager = command_manager
        except Exception as e:
            self.api.log(f"Error loading device types: {str(e)}", level="ERROR")
            
    def _on_device_type_changed(self, index):
        """Handle device type change."""
        if not self.current_device:
            return
            
        try:
            # Get the selected device type
            device_type = self.device_type_combo.currentData()
            
            # Update device type in database
            if device_type:
                self.current_device['device_type'] = device_type
                self.device_manager.update_device(self.current_device)
                self.api.log(f"Device type updated to {device_type}")
            
                # Load commands for this device type
                self._load_commands_for_device_type(device_type)
        except Exception as e:
            self.api.log(f"Error updating device type: {str(e)}", level="ERROR")
            
    def _load_commands_for_device_type(self, device_type):
        """Load commands for the selected device type."""
        try:
            # Clear the command list
            self.command_list.clear()
            
            # Check if we have a command manager
            if not hasattr(self, 'command_manager') or not self.command_manager:
                self.api.log("Command manager not available", level="WARNING")
                return
                
            # Get commands for this device type
            commands = self.command_manager.get_commands_for_device_type(device_type)
            
            # Add commands to the list
            for command_id, command_info in commands.items():
                command_text = command_info.get('command', '')
                item = QListWidgetItem(command_text)
                item.setToolTip(command_info.get('description', ''))
                # Store additional information
                item.setData(Qt.ItemDataRole.UserRole, {
                    'id': command_id,
                    'command': command_text,
                    'description': command_info.get('description', ''),
                    'output_type': command_info.get('output_type', 'text')
                })
                self.command_list.addItem(item)
                
            # Enable run button if we have commands
            self.run_button.setEnabled(self.command_list.count() > 0 and self.current_device is not None)
        except Exception as e:
            self.api.log(f"Error loading commands: {str(e)}", level="ERROR")
    
    def _run_selected_commands(self):
        """Run selected commands."""
        if not self.current_device:
            self.status_label.setText("No device selected")
            return
            
        selected_items = self.command_list.selectedItems()
        if not selected_items:
            self.status_label.setText("No commands selected")
            return
        
        # Get selected commands with their metadata
        commands = []
        for item in selected_items:
            command_data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(command_data, dict):
                commands.append(command_data)
            else:
                # Fallback if data is not a dict
                commands.append({
                    'command': item.text(),
                    'output_type': 'text'
                })
        
        # Save the current device type to the device dictionary
        device_type = self.device_type_combo.currentData()
        if device_type and device_type != self.current_device.get('device_type'):
            self.current_device['device_type'] = device_type
            # Update the device in the device manager
            try:
                self.device_manager.update_device(self.current_device)
                self.api.log(f"Updated device type to {device_type} for device {self.current_device.get('ip')}", level="DEBUG")
            except Exception as e:
                self.api.log(f"Failed to update device type in database: {str(e)}", level="WARNING")
        
        # Get connection type
        connection_type = self.conn_type_combo.currentData()
        
        try:
            # Update status
            self.status_label.setText(f"Connecting to {self.current_device.get('ip')}...")
            self.run_button.setEnabled(False)
            
            # Get connection handler from plugin
            connection_handler = self._get_connection_handler()
            if not connection_handler:
                self.status_label.setText("Connection handler not available")
                self.run_button.setEnabled(True)
                return
            
            # Get output panel from plugin
            output_panel = self._get_output_panel()
            
            # Connect to device
            success, message, connection_id = connection_handler.connect(
                self.current_device, 
                connection_type
            )
            
            if not success:
                self.status_label.setText(f"Connection failed: {message}")
                self.run_button.setEnabled(True)
                return
            
            # Run each command
            self.status_label.setText("Running commands...")
            
            for cmd_data in commands:
                cmd = cmd_data.get('command', '')
                output_type = cmd_data.get('output_type', 'text')
                
                # Execute the command
                success, output = connection_handler.execute_command(connection_id, cmd)
                
                if success:
                    # Save the output
                    self._save_command_output(cmd, output, output_type)
                    
                    # Show in output panel if available
                    if output_panel:
                        output_panel.view_output_text(cmd, output, self.current_device.get('ip', 'unknown'))
                else:
                    self.api.log(f"Command failed: {cmd} - {output}", level="ERROR")
                    if output_panel:
                        output_panel.view_output_text(cmd, f"Command execution failed: {output}", 
                                                    self.current_device.get('ip', 'unknown'))
            
            # Disconnect
            connection_handler.disconnect(connection_id)
            
            # Update command history
            self._update_command_history()
            
            # Update status
            self.status_label.setText("Commands completed")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self.api.log(f"Error executing commands: {str(e)}", level="ERROR")
        finally:
            self.run_button.setEnabled(True)
    
    def _get_connection_handler(self):
        """Get the connection handler from the plugin."""
        # Try multiple ways to get connection handler
        
        # First check if plugin can be accessed via API
        if hasattr(self.api, 'get_plugin_instance'):
            plugin = self.api.get_plugin_instance('network-device-manager')
            if plugin and hasattr(plugin, 'connection_handler'):
                return plugin.connection_handler
        
        # If not found, try to get from main window's plugin manager
        if hasattr(self.api, 'main_window'):
            plugin_mgr = getattr(self.api.main_window, 'plugin_manager', None)
            if plugin_mgr and hasattr(plugin_mgr, 'plugins'):
                plugin_info = plugin_mgr.plugins.get('network-device-manager', {})
                plugin_instance = plugin_info.get('instance')
                if plugin_instance and hasattr(plugin_instance, 'connection_handler'):
                    return plugin_instance.connection_handler
        
        return None
    
    def _get_output_panel(self):
        """Get the output panel from the plugin."""
        # Try multiple ways to get output panel
        
        # First check if plugin can be accessed via API
        if hasattr(self.api, 'get_plugin_instance'):
            plugin = self.api.get_plugin_instance('network-device-manager')
            if plugin and hasattr(plugin, 'output_panel'):
                return plugin.output_panel
        
        # If not found, try to get from main window's plugin manager
        if hasattr(self.api, 'main_window'):
            plugin_mgr = getattr(self.api.main_window, 'plugin_manager', None)
            if plugin_mgr and hasattr(plugin_mgr, 'plugins'):
                plugin_info = plugin_mgr.plugins.get('network-device-manager', {})
                plugin_instance = plugin_info.get('instance')
                if plugin_instance and hasattr(plugin_instance, 'output_panel'):
                    return plugin_instance.output_panel
        
        return None
    
    def _save_command_output(self, command, output, output_type):
        """Save command output to file and database."""
        try:
            # Get the output directory
            output_dir = None
            if hasattr(self.device_manager, 'output_dir'):
                output_dir = self.device_manager.output_dir
            else:
                # Try to get from plugin
                plugin = self._get_plugin_instance()
                if plugin and hasattr(plugin, 'output_dir'):
                    output_dir = plugin.output_dir
            
            if not output_dir:
                self.api.log("Output directory not found", level="ERROR")
                return
            
            # Create device directory if it doesn't exist
            device_dir = output_dir / self.current_device['ip'].replace('.', '_')
            device_dir.mkdir(exist_ok=True)
            
            # Create output file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = device_dir / f"{command.replace(' ', '_')}_{timestamp}.txt"
            
            # Save output to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            
            # Save to command history file
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
            self.api.log(f"Error saving command output: {str(e)}", level="ERROR")
    
    def _get_plugin_instance(self):
        """Get the plugin instance."""
        # First check if plugin can be accessed via API
        if hasattr(self.api, 'get_plugin_instance'):
            return self.api.get_plugin_instance('network-device-manager')
        
        # If not found, try to get from main window's plugin manager
        if hasattr(self.api, 'main_window'):
            plugin_mgr = getattr(self.api.main_window, 'plugin_manager', None)
            if plugin_mgr and hasattr(plugin_mgr, 'plugins'):
                plugin_info = plugin_mgr.plugins.get('network-device-manager', {})
                return plugin_info.get('instance')
        
        return None
    
    def _update_command_history(self):
        """Update command history table."""
        if not self.current_device:
            return
            
        try:
            # Clear table first
            self.command_history_table.setRowCount(0)
            
            # Check if device_manager is available and has get_command_outputs method
            if not hasattr(self.device_manager, 'get_command_outputs'):
                self.api.log("Device manager doesn't have get_command_outputs method", level="WARNING")
                return
                
            # Get command outputs from device manager
            try:
                outputs = self.device_manager.get_command_outputs(self.current_device['ip'])
            except Exception as db_error:
                self.api.log(f"Error getting command outputs: {str(db_error)}", level="ERROR")
                # Try alternative approach - read from file system if available
                outputs = self._get_command_history_from_files()
            
            # If no outputs found, just return
            if not outputs:
                return
                
            # Add outputs to table
            for i, output in enumerate(outputs):
                self.command_history_table.insertRow(i)
                
                # Command
                command = output.get('command', 'Unknown command')
                self.command_history_table.setItem(i, 0, QTableWidgetItem(command))
                
                # Timestamp
                timestamp = output.get('timestamp', 'Unknown time')
                self.command_history_table.setItem(i, 1, QTableWidgetItem(str(timestamp)))
                
                # Output type
                output_type = output.get('output_type', 'text')
                self.command_history_table.setItem(i, 2, QTableWidgetItem(output_type))
                
                # Store output ID in the command item
                if 'id' in output:
                    self.command_history_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, output['id'])
                
                # Store output path in the timestamp item
                if 'output_path' in output:
                    self.command_history_table.item(i, 1).setData(Qt.ItemDataRole.UserRole, output['output_path'])
            
            # Connect to selection change
            self.command_history_table.selectionModel().selectionChanged.connect(self._on_history_selection_changed)
        except Exception as e:
            self.api.log(f"Error updating command history: {str(e)}", level="ERROR")
    
    def _get_command_history_from_files(self):
        """Fallback method to get command history from files when database is unavailable."""
        try:
            # Check if we can determine the output directory
            output_dir = None
            
            # Try to get from device_manager
            if hasattr(self.device_manager, 'output_dir'):
                output_dir = self.device_manager.output_dir
            
            # If not found, try standard location
            if not output_dir:
                # Get plugin directory
                plugin_dir = None
                if hasattr(self.api, 'get_plugin_dir'):
                    plugin_dir = self.api.get_plugin_dir()
                elif hasattr(self.api, 'plugin_dir'):
                    plugin_dir = self.api.plugin_dir
                
                if plugin_dir:
                    output_dir = Path(plugin_dir) / "data" / "outputs"
                else:
                    # Fallback to a relative path
                    output_dir = Path("plugins/network-device-manager/data/outputs")
            
            # Check if directory exists
            if not isinstance(output_dir, Path):
                output_dir = Path(output_dir)
                
            if not output_dir.exists():
                return []
                
            # Look for device directory
            device_dir = output_dir / self.current_device['ip'].replace('.', '_')
            if not device_dir.exists():
                return []
                
            # Check for command history file
            history_file = device_dir / "command_history.csv"
            if not history_file.exists():
                return []
                
            outputs = []
            with open(history_file, 'r', newline='') as f:
                reader = csv.reader(f)
                # Skip header row
                next(reader, None)
                
                for i, row in enumerate(reader):
                    if len(row) >= 3:
                        command, timestamp, output_type = row[0], row[1], row[2]
                        
                        # Create entry similar to database output
                        output = {
                            'id': i,
                            'command': command,
                            'timestamp': timestamp,
                            'output_type': output_type,
                            'output_path': str(device_dir / f"{command.replace(' ', '_')}_{timestamp.replace(':', '-').replace(' ', '_')}.txt")
                        }
                        outputs.append(output)
            
            return outputs
        except Exception as e:
            self.api.log(f"Error reading command history from files: {str(e)}", level="DEBUG")
            return []
    
    def _on_history_selection_changed(self, selected, deselected):
        """Handle history selection change."""
        enable_buttons = len(self.command_history_table.selectedItems()) > 0
        self.view_output_button.setEnabled(enable_buttons)
        self.download_output_button.setEnabled(enable_buttons)
    
    def _view_selected_output(self):
        """View selected command output."""
        selected_rows = self.command_history_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        output_path = self.command_history_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        command = self.command_history_table.item(row, 0).text()
        
        try:
            # Try to get output panel
            output_panel = None
            bottom_panel = None
            plugin_instance = None
            
            # First, check if plugin can be accessed via API
            if hasattr(self.api, 'get_plugin_instance'):
                plugin_instance = self.api.get_plugin_instance('network-device-manager')
                if plugin_instance:
                    if hasattr(plugin_instance, 'output_panel'):
                        output_panel = plugin_instance.output_panel
                    if hasattr(plugin_instance, 'bottom_panel'):
                        bottom_panel = plugin_instance.bottom_panel
            
            # If not found, try to get from main window's plugin manager
            if (not output_panel or not bottom_panel) and self.api.main_window:
                plugin_mgr = getattr(self.api.main_window, 'plugin_manager', None)
                if plugin_mgr:
                    for plugin_id, plugin_info in plugin_mgr.plugins.items():
                        if plugin_id == 'network-device-manager' and 'instance' in plugin_info:
                            plugin_instance = plugin_info['instance']
                            break
                    
                    if plugin_instance:
                        if not output_panel and hasattr(plugin_instance, 'output_panel'):
                            output_panel = plugin_instance.output_panel
                        if not bottom_panel and hasattr(plugin_instance, 'bottom_panel'):
                            bottom_panel = plugin_instance.bottom_panel
            
            if not output_panel:
                self.api.log("Output panel not found", level="ERROR")
                return
            
            # Show output in panel
            output_panel.view_output(output_path, command)
            
            # Ensure the bottom panel is shown only when viewing output
            if bottom_panel:
                self.api.log("Showing command output in bottom panel", level="DEBUG")
                
                # Add the bottom panel to the main UI if it's not already there
                if plugin_instance and hasattr(plugin_instance, 'api'):
                    # First check if the tab already exists
                    tab_exists = False
                    
                    # Check if the main window has tabs and if our tab is already there
                    if hasattr(plugin_instance.api, 'main_window') and hasattr(plugin_instance.api.main_window, 'tab_widget'):
                        tab_widget = plugin_instance.api.main_window.tab_widget
                        for i in range(tab_widget.count()):
                            if tab_widget.widget(i) == bottom_panel:
                                tab_exists = True
                                break
                    
                    if not tab_exists:
                        plugin_instance.api.add_tab(bottom_panel, "Command Output")
                
                # Make sure the output panel is visible and switch to it
                bottom_panel.setCurrentIndex(0)
                
                # Bring the tab to front if we have access to the main window
                if hasattr(plugin_instance, 'api') and hasattr(plugin_instance.api, 'main_window'):
                    if hasattr(plugin_instance.api.main_window, 'tab_widget'):
                        tab_widget = plugin_instance.api.main_window.tab_widget
                        for i in range(tab_widget.count()):
                            if tab_widget.widget(i) == bottom_panel:
                                tab_widget.setCurrentIndex(i)
                                break
        except Exception as e:
            self.api.log(f"Error viewing output: {str(e)}", level="ERROR")
    
    def _download_selected_output(self):
        """Download selected command output."""
        selected_rows = self.command_history_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        output_path = self.command_history_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        
        try:
            # Open file dialog to select download location
            filters = "All Files (*.*)"
            save_path, _ = self.api.get_save_file_path(
                "Save Command Output",
                filters=filters,
                default_path=output_path
            )
            
            if save_path:
                # Copy file to selected location
                import shutil
                shutil.copy2(output_path, save_path)
                
                self.api.log(f"Output saved to {save_path}")
        except Exception as e:
            self.api.log(f"Error downloading output: {str(e)}", level="ERROR")
    
    def _update_credentials_status(self):
        """Update credentials status label."""
        try:
            if not self.current_device or not self.credential_manager:
                self.credentials_status.setText("No credentials set")
                return
                
            # Check for device-specific credentials
            device_ip = self.current_device.get('ip')
            if not device_ip:
                self.credentials_status.setText("No device IP")
                return
                
            # Check credentials in order of specificity
            creds = self.credential_manager.get_credentials(device_ip)
            if creds:
                self.credentials_status.setText(f"Device: {creds['username']}")
                return
                
            # Check subnet credentials
            # This is a simplified check - in a real implementation,
            # you would check if the device IP is in the subnet
            for subnet_entry in self.credential_manager.get_all_credential_entries():
                if subnet_entry['type'] == 'Subnet':
                    # Check if IP is in subnet (simplified)
                    subnet = subnet_entry['name']
                    if device_ip.startswith(subnet.split('.')[0]):
                        subnet_id = f"subnet:{subnet}"
                        creds = self.credential_manager.get_credentials(subnet_id)
                        if creds:
                            self.credentials_status.setText(f"Subnet ({subnet}): {creds['username']}")
                            return
            
            # Check for default credentials
            creds = self.credential_manager.get_default_credentials()
            if creds:
                self.credentials_status.setText(f"Default: {creds['username']}")
                return
                
            self.credentials_status.setText("No credentials set")
        except Exception as e:
            self.api.log(f"Error updating credentials status: {str(e)}", level="ERROR")
            self.credentials_status.setText("Error checking credentials")
    
    def _manage_credentials(self):
        """Open the credentials management dialog."""
        try:
            # Call the manage_credentials method in the plugin
            # Pass the parent and credential_manager directly to the dialog
            from ui.credential_dialog import CredentialDialog
            dialog = CredentialDialog(self.api.main_window, self.credential_manager)
            dialog.exec()
            
            # Update credentials status
            self._update_credentials_status()
        except Exception as e:
            self.api.log(f"Error managing credentials: {str(e)}", level="ERROR") 