#!/usr/bin/env python3
# Network Device Manager - Credential Dialog

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QGroupBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox, QWidget
)
from PySide6.QtCore import Qt, Signal, Slot

class CredentialDialog(QDialog):
    """Dialog for managing device credentials."""
    
    def __init__(self, parent, credential_manager):
        super().__init__(parent)
        self.credential_manager = credential_manager
        
        self.setWindowTitle("Manage Device Credentials")
        self.resize(700, 500)
        
        self._init_ui()
        self._load_credentials()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Credentials table
        self.cred_table = QTableWidget(0, 3)
        self.cred_table.setHorizontalHeaderLabels(["Type", "Name", "Actions"])
        self.cred_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.cred_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.cred_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.cred_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cred_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.cred_table)
        
        # Add credential section
        add_group = QGroupBox("Add Credentials")
        add_layout = QFormLayout(add_group)
        
        # Credential type
        self.cred_type = QComboBox()
        self.cred_type.addItem("Default", "default")
        self.cred_type.addItem("Device", "device")
        self.cred_type.addItem("Subnet", "subnet")
        self.cred_type.addItem("Group", "group")
        self.cred_type.currentIndexChanged.connect(self._cred_type_changed)
        
        # Target (for device, subnet, group)
        self.cred_target = QLineEdit()
        self.cred_target.setPlaceholderText("IP address, subnet (e.g. 192.168.1.0/24), or group name")
        
        # Credentials
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.enable_password = QLineEdit()
        self.enable_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Show password checkbox
        self.show_passwords = QCheckBox("Show passwords")
        self.show_passwords.toggled.connect(self._toggle_password_visibility)
        
        # Add fields to form
        add_layout.addRow("Type:", self.cred_type)
        add_layout.addRow("Target:", self.cred_target)
        add_layout.addRow("Username:", self.username)
        add_layout.addRow("Password:", self.password)
        add_layout.addRow("Enable Password:", self.enable_password)
        add_layout.addRow("", self.show_passwords)
        
        # Add button
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Credentials")
        self.add_button.clicked.connect(self._add_credentials)
        
        button_layout.addWidget(self.add_button)
        button_layout.addStretch()
        
        # Add layouts to main layout
        layout.addWidget(add_group)
        layout.addLayout(button_layout)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        
        layout.addWidget(close_button)
        
        # Initialize state
        self._cred_type_changed()
    
    def _cred_type_changed(self):
        """Handle credential type change."""
        cred_type = self.cred_type.currentData()
        
        # Show/hide target field based on type
        self.cred_target.setEnabled(cred_type != "default")
        self.cred_target.setPlaceholderText({
            "default": "Global default credentials",
            "device": "Device IP address",
            "subnet": "Subnet (e.g. 192.168.1.0/24)",
            "group": "Group name"
        }[cred_type])
    
    def _toggle_password_visibility(self, show):
        """Toggle password visibility."""
        self.password.setEchoMode(QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password)
        self.enable_password.setEchoMode(QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password)
    
    def _load_credentials(self):
        """Load credentials into the table."""
        # Clear table
        self.cred_table.setRowCount(0)
        
        # Get all credential entries
        entries = self.credential_manager.get_all_credential_entries()
        
        # Add entries to table
        for row, entry in enumerate(entries):
            self.cred_table.insertRow(row)
            
            # Type
            self.cred_table.setItem(row, 0, QTableWidgetItem(entry['type']))
            
            # Name
            self.cred_table.setItem(row, 1, QTableWidgetItem(entry['name']))
            
            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            # Create a closure to capture the entry_id
            entry_id = entry['id']
            
            edit_button = QPushButton("Edit")
            # Fix: add handling for the 'checked' parameter that Qt's clicked signal sends
            edit_button.clicked.connect(lambda checked=False, eid=entry_id: self._edit_credentials(eid))
            
            delete_button = QPushButton("Delete")
            # Fix: add handling for the 'checked' parameter that Qt's clicked signal sends
            delete_button.clicked.connect(lambda checked=False, eid=entry_id: self._delete_credentials(eid))
            
            action_layout.addWidget(edit_button)
            action_layout.addWidget(delete_button)
            
            self.cred_table.setCellWidget(row, 2, action_widget)
    
    def _add_credentials(self):
        """Add credentials."""
        try:
            # Get values
            cred_type = self.cred_type.currentData()
            target = self.cred_target.text()
            username = self.username.text()
            password = self.password.text()
            enable_password = self.enable_password.text() or None
            
            # Validate
            if cred_type != "default" and not target:
                QMessageBox.warning(self, "Validation Error", "Target is required for this credential type.")
                return
                
            if not username:
                QMessageBox.warning(self, "Validation Error", "Username is required.")
                return
                
            if not password:
                QMessageBox.warning(self, "Validation Error", "Password is required.")
                return
            
            # Add credentials based on type
            if cred_type == "default":
                self.credential_manager.set_default_credentials(username, password, enable_password)
            elif cred_type == "device":
                self.credential_manager.set_credentials(target, username, password, enable_password)
            elif cred_type == "subnet":
                self.credential_manager.set_credentials_by_subnet(target, username, password, enable_password)
            elif cred_type == "group":
                self.credential_manager.set_credentials_by_group(target, username, password, enable_password)
            
            # Reload credentials
            self._load_credentials()
            
            # Clear form
            self.cred_target.clear()
            self.username.clear()
            self.password.clear()
            self.enable_password.clear()
            
            QMessageBox.information(self, "Success", "Credentials saved successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error saving credentials: {str(e)}")
    
    def _edit_credentials(self, entry_id):
        """Edit credentials."""
        try:
            # Get credentials
            cred_entry = next((e for e in self.credential_manager.get_all_credential_entries() if e['id'] == entry_id), None)
            if not cred_entry:
                QMessageBox.warning(self, "Error", "Credential entry not found.")
                return
                
            # Get credential details
            cred_type = cred_entry['type'].lower()
            if cred_type == "default":
                creds = self.credential_manager.get_default_credentials()
                if creds:
                    # Set form values
                    self.cred_type.setCurrentIndex(self.cred_type.findData("default"))
                    self.username.setText(creds['username'])
                    self.password.setText(creds['password'])
                    self.enable_password.setText(creds.get('enable_password', ''))
            else:
                # Extract ID based on type
                if cred_type == "device":
                    creds = self.credential_manager.get_credentials(entry_id)
                    self.cred_type.setCurrentIndex(self.cred_type.findData("device"))
                elif cred_type == "subnet":
                    creds = self.credential_manager.get_credentials_by_subnet(entry_id[7:])  # Remove "subnet:" prefix
                    self.cred_type.setCurrentIndex(self.cred_type.findData("subnet"))
                elif cred_type == "group":
                    creds = self.credential_manager.get_credentials_by_group(entry_id[6:])  # Remove "group:" prefix
                    self.cred_type.setCurrentIndex(self.cred_type.findData("group"))
                
                if creds:
                    # Set form values
                    self.cred_target.setText(cred_entry['name'])
                    self.username.setText(creds['username'])
                    self.password.setText(creds['password'])
                    self.enable_password.setText(creds.get('enable_password', ''))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading credentials: {str(e)}")
    
    def _delete_credentials(self, entry_id):
        """Delete credentials."""
        try:
            # Confirm deletion
            if QMessageBox.question(
                self, 
                "Confirm Deletion", 
                "Are you sure you want to delete these credentials?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
                
            # Delete credentials
            self.credential_manager.remove_credentials(entry_id)
            
            # Reload credentials
            self._load_credentials()
            
            QMessageBox.information(self, "Success", "Credentials deleted successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error deleting credentials: {str(e)}") 