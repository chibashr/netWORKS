#!/usr/bin/env python3
# Network Device Manager - Configuration Dialog

from PySide6.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QLineEdit, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFormLayout, QGroupBox, QMessageBox,
    QRadioButton, QButtonGroup, QSpinBox
)
from PySide6.QtCore import Qt, Signal, Slot

class CredentialDialog(QDialog):
    """Dialog for adding or editing credentials."""
    
    def __init__(self, parent, credential_manager, editing=None):
        super().__init__(parent)
        self.credential_manager = credential_manager
        self.editing = editing  # Credential ID if editing, None if adding new
        
        self.setWindowTitle("Device Credentials")
        self.resize(400, 300)
        
        self._init_ui()
        
        # Load credential data if editing
        if editing:
            self._load_credential_data()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Credential type
        type_group = QGroupBox("Credential Type")
        type_layout = QVBoxLayout(type_group)
        
        self.type_buttons = QButtonGroup(self)
        
        self.device_radio = QRadioButton("Device Specific")
        self.subnet_radio = QRadioButton("Subnet")
        self.group_radio = QRadioButton("Device Group")
        self.default_radio = QRadioButton("Default (Fallback)")
        
        self.type_buttons.addButton(self.device_radio, 0)
        self.type_buttons.addButton(self.subnet_radio, 1)
        self.type_buttons.addButton(self.group_radio, 2)
        self.type_buttons.addButton(self.default_radio, 3)
        
        type_layout.addWidget(self.device_radio)
        type_layout.addWidget(self.subnet_radio)
        type_layout.addWidget(self.group_radio)
        type_layout.addWidget(self.default_radio)
        
        # Default to device specific
        self.device_radio.setChecked(True)
        
        # Connect radio button changes
        self.type_buttons.buttonClicked.connect(self._update_identifier_field)
        
        layout.addWidget(type_group)
        
        # Credential identifier
        id_group = QGroupBox("Identifier")
        id_layout = QFormLayout(id_group)
        
        self.id_label = QLabel("Device IP:")
        self.id_input = QLineEdit()
        
        id_layout.addRow(self.id_label, self.id_input)
        
        layout.addWidget(id_group)
        
        # Credentials
        cred_group = QGroupBox("Credentials")
        cred_layout = QFormLayout(cred_group)
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.enable_password_check = QCheckBox("Use Enable Password")
        self.enable_password_input = QLineEdit()
        self.enable_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.enable_password_input.setEnabled(False)
        
        # Connect enable password checkbox
        self.enable_password_check.stateChanged.connect(
            lambda state: self.enable_password_input.setEnabled(state == Qt.CheckState.Checked)
        )
        
        cred_layout.addRow("Username:", self.username_input)
        cred_layout.addRow("Password:", self.password_input)
        cred_layout.addRow(self.enable_password_check)
        cred_layout.addRow("Enable Password:", self.enable_password_input)
        
        layout.addWidget(cred_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def _update_identifier_field(self, button):
        """Update the identifier field based on the selected credential type."""
        if button == self.device_radio:
            self.id_label.setText("Device IP:")
            self.id_input.setPlaceholderText("e.g., 192.168.1.1")
        elif button == self.subnet_radio:
            self.id_label.setText("Subnet:")
            self.id_input.setPlaceholderText("e.g., 192.168.1.0/24")
        elif button == self.group_radio:
            self.id_label.setText("Group Name:")
            self.id_input.setPlaceholderText("e.g., switches")
        elif button == self.default_radio:
            self.id_label.setText("Default:")
            self.id_input.setText("default")
            self.id_input.setEnabled(False)
    
    def _load_credential_data(self):
        """Load credential data for editing."""
        if not self.editing:
            return
            
        # Determine credential type and set radio button
        if self.editing == "default":
            self.default_radio.setChecked(True)
            self.id_input.setText("default")
            self.id_input.setEnabled(False)
            credentials = self.credential_manager.get_default_credentials()
        elif self.editing.startswith("subnet:"):
            self.subnet_radio.setChecked(True)
            self.id_label.setText("Subnet:")
            self.id_input.setPlaceholderText("e.g., 192.168.1.0/24")
            self.id_input.setText(self.editing[7:])  # Remove "subnet:" prefix
            credentials = self.credential_manager.get_credentials_by_subnet(self.editing[7:])
        elif self.editing.startswith("group:"):
            self.group_radio.setChecked(True)
            self.id_label.setText("Group Name:")
            self.id_input.setPlaceholderText("e.g., switches")
            self.id_input.setText(self.editing[6:])  # Remove "group:" prefix
            credentials = self.credential_manager.get_credentials_by_group(self.editing[6:])
        else:
            self.device_radio.setChecked(True)
            self.id_label.setText("Device IP:")
            self.id_input.setPlaceholderText("e.g., 192.168.1.1")
            self.id_input.setText(self.editing)
            credentials = self.credential_manager.get_credentials(self.editing)
        
        # Set credential values
        if credentials:
            self.username_input.setText(credentials.get('username', ''))
            self.password_input.setText(credentials.get('password', ''))
            
            if credentials.get('enable_password'):
                self.enable_password_check.setChecked(True)
                self.enable_password_input.setEnabled(True)
                self.enable_password_input.setText(credentials.get('enable_password', ''))
    
    def get_values(self):
        """Get the credential values from the dialog."""
        # Get credential type
        cred_type = self.type_buttons.checkedId()
        
        # Get identifier
        identifier = self.id_input.text().strip()
        
        # Get credentials
        username = self.username_input.text()
        password = self.password_input.text()
        enable_password = self.enable_password_input.text() if self.enable_password_check.isChecked() else None
        
        return {
            'type': cred_type,
            'identifier': identifier,
            'username': username,
            'password': password,
            'enable_password': enable_password
        }

class ConfigDialog(QDialog):
    """Dialog for plugin configuration."""
    
    def __init__(self, parent, plugin_instance):
        super().__init__(parent)
        self.plugin = plugin_instance
        self.credential_manager = self.plugin.credential_manager
        self.command_manager = self.plugin.command_manager
        
        self.setWindowTitle("Network Device Manager Configuration")
        self.resize(800, 600)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Tabs
        tabs = QTabWidget()
        
        # Credentials tab
        cred_tab = QWidget()
        cred_layout = QVBoxLayout(cred_tab)
        
        # Credentials table
        self.cred_table = QTableWidget(0, 3)
        self.cred_table.setHorizontalHeaderLabels(["Type", "Name", "Username"])
        self.cred_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.cred_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.cred_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.cred_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        cred_layout.addWidget(self.cred_table)
        
        # Credential buttons
        cred_button_layout = QHBoxLayout()
        
        add_cred_button = QPushButton("Add")
        add_cred_button.clicked.connect(self._add_credential)
        
        edit_cred_button = QPushButton("Edit")
        edit_cred_button.clicked.connect(self._edit_credential)
        
        remove_cred_button = QPushButton("Remove")
        remove_cred_button.clicked.connect(self._remove_credential)
        
        cred_button_layout.addWidget(add_cred_button)
        cred_button_layout.addWidget(edit_cred_button)
        cred_button_layout.addWidget(remove_cred_button)
        cred_button_layout.addStretch()
        
        cred_layout.addLayout(cred_button_layout)
        
        # Commands tab
        cmd_tab = QWidget()
        cmd_layout = QVBoxLayout(cmd_tab)
        
        # Device type selection
        device_type_layout = QHBoxLayout()
        device_type_layout.addWidget(QLabel("Device Type:"))
        
        self.device_type_combo = QComboBox()
        self._load_device_types()
        
        device_type_layout.addWidget(self.device_type_combo)
        device_type_layout.addStretch()
        
        cmd_layout.addLayout(device_type_layout)
        
        # Commands table
        self.cmd_table = QTableWidget(0, 3)
        self.cmd_table.setHorizontalHeaderLabels(["Command", "Description", "Output Type"])
        self.cmd_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cmd_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.cmd_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        cmd_layout.addWidget(self.cmd_table)
        
        # Command buttons
        cmd_button_layout = QHBoxLayout()
        
        add_cmd_button = QPushButton("Add")
        add_cmd_button.clicked.connect(self._add_command)
        
        edit_cmd_button = QPushButton("Edit")
        edit_cmd_button.clicked.connect(self._edit_command)
        
        remove_cmd_button = QPushButton("Remove")
        remove_cmd_button.clicked.connect(self._remove_command)
        
        import_cmd_button = QPushButton("Import")
        import_cmd_button.clicked.connect(self._import_commands)
        
        export_cmd_button = QPushButton("Export")
        export_cmd_button.clicked.connect(self._export_commands)
        
        cmd_button_layout.addWidget(add_cmd_button)
        cmd_button_layout.addWidget(edit_cmd_button)
        cmd_button_layout.addWidget(remove_cmd_button)
        cmd_button_layout.addWidget(import_cmd_button)
        cmd_button_layout.addWidget(export_cmd_button)
        cmd_button_layout.addStretch()
        
        cmd_layout.addLayout(cmd_button_layout)
        
        # Settings tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        # Connection settings
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout(conn_group)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" seconds")
        
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(3)
        
        conn_layout.addRow("Connection Timeout:", self.timeout_spin)
        conn_layout.addRow("Connection Retries:", self.retry_spin)
        
        settings_layout.addWidget(conn_group)
        
        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        
        self.auto_save_check = QCheckBox("Automatically save command output")
        self.auto_save_check.setChecked(True)
        
        output_layout.addRow(self.auto_save_check)
        
        settings_layout.addWidget(output_group)
        
        # Add stretch to push settings to the top
        settings_layout.addStretch()
        
        # Add tabs
        tabs.addTab(cred_tab, "Credentials")
        tabs.addTab(cmd_tab, "Commands")
        tabs.addTab(settings_tab, "Settings")
        
        layout.addWidget(tabs)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # Load data
        self._load_credentials()
        self._load_commands()
        self._load_settings()
        
        # Connect signals
        self.device_type_combo.currentIndexChanged.connect(self._load_commands)
    
    def _load_credentials(self):
        """Load credentials into the table."""
        # Clear table
        self.cred_table.setRowCount(0)
        
        # Get credentials
        entries = self.credential_manager.get_all_credential_entries()
        
        # Add to table
        for i, entry in enumerate(entries):
            self.cred_table.insertRow(i)
            
            # Type
            self.cred_table.setItem(i, 0, QTableWidgetItem(entry['type']))
            
            # Name
            self.cred_table.setItem(i, 1, QTableWidgetItem(entry['name']))
            
            # Username
            cred_id = entry['id']
            username = "N/A"
            
            if entry['type'] == "Device":
                credentials = self.credential_manager.get_credentials(cred_id)
            elif entry['type'] == "Subnet":
                credentials = self.credential_manager.get_credentials_by_subnet(entry['name'])
            elif entry['type'] == "Group":
                credentials = self.credential_manager.get_credentials_by_group(entry['name'])
            else:  # Default
                credentials = self.credential_manager.get_default_credentials()
                
            if credentials:
                username = credentials.get('username', 'N/A')
                
            self.cred_table.setItem(i, 2, QTableWidgetItem(username))
            
            # Store credential ID
            self.cred_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, entry['id'])
    
    def _load_device_types(self):
        """Load device types into combo box."""
        # Clear combo box
        self.device_type_combo.clear()
        
        # Get device types
        device_types = self.command_manager.get_device_type_display_names()
        
        # Add to combo box
        for device_type, display_name in device_types.items():
            self.device_type_combo.addItem(display_name, device_type)
    
    def _load_commands(self):
        """Load commands for the selected device type."""
        # Get selected device type
        device_type = self.device_type_combo.currentData()
        if not device_type:
            return
            
        # Clear table
        self.cmd_table.setRowCount(0)
        
        # Get commands
        commands = self.command_manager.get_commands_for_device_type(device_type)
        
        # Add to table
        for i, (command_id, command_info) in enumerate(commands.items()):
            self.cmd_table.insertRow(i)
            
            # Command
            self.cmd_table.setItem(i, 0, QTableWidgetItem(command_info.get('command', '')))
            
            # Description
            self.cmd_table.setItem(i, 1, QTableWidgetItem(command_info.get('description', '')))
            
            # Output type
            self.cmd_table.setItem(i, 2, QTableWidgetItem(command_info.get('output_type', 'text')))
            
            # Store command ID
            self.cmd_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, command_id)
    
    def _load_settings(self):
        """Load settings."""
        # In a real implementation, these would come from stored settings
        pass
    
    def _add_credential(self):
        """Add a new credential."""
        dialog = CredentialDialog(self, self.credential_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            
            try:
                # Save based on type
                if values['type'] == 0:  # Device
                    self.credential_manager.set_credentials(
                        values['identifier'],
                        values['username'],
                        values['password'],
                        values['enable_password']
                    )
                elif values['type'] == 1:  # Subnet
                    self.credential_manager.set_credentials_by_subnet(
                        values['identifier'],
                        values['username'],
                        values['password'],
                        values['enable_password']
                    )
                elif values['type'] == 2:  # Group
                    self.credential_manager.set_credentials_by_group(
                        values['identifier'],
                        values['username'],
                        values['password'],
                        values['enable_password']
                    )
                elif values['type'] == 3:  # Default
                    self.credential_manager.set_default_credentials(
                        values['username'],
                        values['password'],
                        values['enable_password']
                    )
                
                # Reload credentials
                self._load_credentials()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error saving credential: {str(e)}")
    
    def _edit_credential(self):
        """Edit an existing credential."""
        selected_rows = self.cred_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        # Get credential ID
        row = selected_rows[0].row()
        cred_id = self.cred_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Open edit dialog
        dialog = CredentialDialog(self, self.credential_manager, cred_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            
            try:
                # Remove old credential
                self.credential_manager.remove_credentials(cred_id)
                
                # Save based on type
                if values['type'] == 0:  # Device
                    self.credential_manager.set_credentials(
                        values['identifier'],
                        values['username'],
                        values['password'],
                        values['enable_password']
                    )
                elif values['type'] == 1:  # Subnet
                    self.credential_manager.set_credentials_by_subnet(
                        values['identifier'],
                        values['username'],
                        values['password'],
                        values['enable_password']
                    )
                elif values['type'] == 2:  # Group
                    self.credential_manager.set_credentials_by_group(
                        values['identifier'],
                        values['username'],
                        values['password'],
                        values['enable_password']
                    )
                elif values['type'] == 3:  # Default
                    self.credential_manager.set_default_credentials(
                        values['username'],
                        values['password'],
                        values['enable_password']
                    )
                
                # Reload credentials
                self._load_credentials()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error saving credential: {str(e)}")
    
    def _remove_credential(self):
        """Remove a credential."""
        selected_rows = self.cred_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        # Get credential ID
        row = selected_rows[0].row()
        cred_id = self.cred_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Confirm deletion
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete this credential?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
            
        try:
            # Remove credential
            self.credential_manager.remove_credentials(cred_id)
            
            # Reload credentials
            self._load_credentials()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error removing credential: {str(e)}")
    
    def _add_command(self):
        """Add a new command."""
        # In a real implementation, this would open a dialog to add a command
        QMessageBox.information(self, "Not Implemented", "This feature is not yet implemented.")
    
    def _edit_command(self):
        """Edit an existing command."""
        # In a real implementation, this would open a dialog to edit a command
        QMessageBox.information(self, "Not Implemented", "This feature is not yet implemented.")
    
    def _remove_command(self):
        """Remove a command."""
        # In a real implementation, this would remove the selected command
        QMessageBox.information(self, "Not Implemented", "This feature is not yet implemented.")
    
    def _import_commands(self):
        """Import commands from a file."""
        # This would call the existing import_commands method
        self.plugin.command_panel._import_commands()
        
        # Reload device types and commands
        self._load_device_types()
        self._load_commands()
    
    def _export_commands(self):
        """Export commands to a file."""
        # In a real implementation, this would export the selected device type commands
        QMessageBox.information(self, "Not Implemented", "This feature is not yet implemented.") 