#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Credential Manager for Command Manager plugin
"""

import os
import json
import ipaddress

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, 
    QLineEdit, QCheckBox, QFormLayout, QDialogButtonBox,
    QTabWidget, QWidget, QMessageBox, QGroupBox, QListWidget,
    QListWidgetItem
)
from PySide6.QtGui import QIcon


class CredentialManager(QDialog):
    """Dialog for managing device credentials"""
    
    def __init__(self, plugin, devices=None, parent=None):
        """Initialize the dialog"""
        super().__init__(parent)
        
        self.plugin = plugin
        self.devices = devices or []
        
        # Set dialog properties
        self.setWindowTitle("Credential Manager")
        self.resize(600, 500)
        
        # Create UI components
        self._create_ui()
        
        # Load credential data
        self._load_data()
        
    def _create_ui(self):
        """Create the UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Add title label at the top
        title_label = QLabel("Device Credential Manager")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Add description
        desc_label = QLabel("Configure access credentials for devices, groups, and subnets")
        desc_label.setStyleSheet("font-size: 10pt; margin-bottom: 15px;")
        layout.addWidget(desc_label)
        
        # Tabbed interface
        self.tabs = QTabWidget()
        
        # Create tabs
        self._create_device_tab()
        self._create_group_tab()
        self._create_subnet_tab()
        
        # Add tabs to layout
        layout.addWidget(self.tabs)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Add help text
        help_label = QLabel("Note: Credentials are stored securely and used for device access.")
        help_label.setStyleSheet("font-style: italic; color: #666;")
        
        layout.addWidget(help_label)
        layout.addWidget(button_box)
        
    def _create_device_tab(self):
        """Create the device credentials tab"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Device list panel
        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 10, 0)
        
        # Add header and explanation
        list_layout.addWidget(QLabel("<b>Devices:</b>"))
        list_layout.addWidget(QLabel("Select a device to configure its credentials"))
        
        # Device list with search box
        self.device_list = QListWidget()
        self.device_list.setAlternatingRowColors(True)
        self.device_list.currentItemChanged.connect(self._on_device_selected)
        list_layout.addWidget(self.device_list)
        
        # Form panel
        form_panel = QWidget()
        form_layout = QVBoxLayout(form_panel)
        form_layout.setContentsMargins(10, 0, 0, 0)
        
        # Add header
        form_layout.addWidget(QLabel("<b>Device Credentials:</b>"))
        form_layout.addWidget(QLabel("Configure connection settings for the selected device"))
        
        # Credential form
        cred_group = QGroupBox()
        cred_group.setStyleSheet("QGroupBox { padding-top: 15px; }")
        self.device_form = QFormLayout(cred_group)
        
        # Connection type
        self.device_conn_type = QComboBox()
        self.device_conn_type.addItems(["SSH", "Telnet"])
        self.device_form.addRow("Connection Type:", self.device_conn_type)
        
        # Username
        self.device_username = QLineEdit()
        self.device_username.setPlaceholderText("Enter username")
        self.device_form.addRow("Username:", self.device_username)
        
        # Password
        self.device_password = QLineEdit()
        self.device_password.setEchoMode(QLineEdit.Password)
        self.device_password.setPlaceholderText("Enter password")
        self.device_form.addRow("Password:", self.device_password)
        
        # Enable password
        self.device_enable = QLineEdit()
        self.device_enable.setEchoMode(QLineEdit.Password)
        self.device_enable.setPlaceholderText("Enter enable password (optional)")
        self.device_form.addRow("Enable Password:", self.device_enable)
        
        form_layout.addWidget(cred_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.device_save_btn = QPushButton("Save Credentials")
        self.device_save_btn.clicked.connect(self._on_save_device)
        self.device_save_btn.setEnabled(False)
        
        self.device_delete_btn = QPushButton("Delete Credentials")
        self.device_delete_btn.clicked.connect(self._on_delete_device)
        self.device_delete_btn.setEnabled(False)
        
        button_layout.addWidget(self.device_save_btn)
        button_layout.addWidget(self.device_delete_btn)
        button_layout.addStretch()
        
        form_layout.addLayout(button_layout)
        form_layout.addStretch()
        
        # Add panels to main layout
        layout.addWidget(list_panel, 1)
        layout.addWidget(form_panel, 2)
        
        # Add tab
        self.tabs.addTab(tab, "Device Credentials")
        
    def _create_group_tab(self):
        """Create the group credentials tab"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Group list panel
        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 10, 0)
        
        # Add header and explanation
        list_layout.addWidget(QLabel("<b>Device Groups:</b>"))
        list_layout.addWidget(QLabel("Select a device group to configure its credentials"))
        
        # Group list with improved styling
        self.group_list = QListWidget()
        self.group_list.setAlternatingRowColors(True)
        self.group_list.currentItemChanged.connect(self._on_group_selected)
        list_layout.addWidget(self.group_list)
        
        # Form panel
        form_panel = QWidget()
        form_layout = QVBoxLayout(form_panel)
        form_layout.setContentsMargins(10, 0, 0, 0)
        
        # Add header
        form_layout.addWidget(QLabel("<b>Group Credentials:</b>"))
        form_layout.addWidget(QLabel("Configure connection settings for the selected group"))
        
        # Credential form
        cred_group = QGroupBox()
        cred_group.setStyleSheet("QGroupBox { padding-top: 15px; }")
        self.group_form = QFormLayout(cred_group)
        
        # Connection type
        self.group_conn_type = QComboBox()
        self.group_conn_type.addItems(["SSH", "Telnet"])
        self.group_form.addRow("Connection Type:", self.group_conn_type)
        
        # Username
        self.group_username = QLineEdit()
        self.group_username.setPlaceholderText("Enter username")
        self.group_form.addRow("Username:", self.group_username)
        
        # Password
        self.group_password = QLineEdit()
        self.group_password.setEchoMode(QLineEdit.Password)
        self.group_password.setPlaceholderText("Enter password")
        self.group_form.addRow("Password:", self.group_password)
        
        # Enable password
        self.group_enable = QLineEdit()
        self.group_enable.setEchoMode(QLineEdit.Password)
        self.group_enable.setPlaceholderText("Enter enable password (optional)")
        self.group_form.addRow("Enable Password:", self.group_enable)
        
        form_layout.addWidget(cred_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.group_save_btn = QPushButton("Save Credentials")
        self.group_save_btn.clicked.connect(self._on_save_group)
        self.group_save_btn.setEnabled(False)
        
        self.group_delete_btn = QPushButton("Delete Credentials")
        self.group_delete_btn.clicked.connect(self._on_delete_group)
        self.group_delete_btn.setEnabled(False)
        
        button_layout.addWidget(self.group_save_btn)
        button_layout.addWidget(self.group_delete_btn)
        button_layout.addStretch()
        
        form_layout.addLayout(button_layout)
        form_layout.addStretch()
        
        # Add panels to main layout
        layout.addWidget(list_panel, 1)
        layout.addWidget(form_panel, 2)
        
        # Add tab
        self.tabs.addTab(tab, "Group Credentials")
        
    def _create_subnet_tab(self):
        """Create the subnet credentials tab"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Subnet list panel
        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 10, 0)
        
        # Add header and explanation
        list_layout.addWidget(QLabel("<b>Subnets:</b>"))
        list_layout.addWidget(QLabel("Manage subnet credentials for automatic device connection"))
        
        # Subnet list with improved styling
        self.subnet_list = QListWidget()
        self.subnet_list.setAlternatingRowColors(True)
        self.subnet_list.currentItemChanged.connect(self._on_subnet_selected)
        list_layout.addWidget(self.subnet_list)
        
        # Add subnet section
        add_subnet_layout = QHBoxLayout()
        self.new_subnet = QLineEdit()
        self.new_subnet.setPlaceholderText("e.g. 192.168.1.0/24")
        
        add_btn = QPushButton("Add Subnet")
        add_btn.clicked.connect(self._on_add_subnet)
        
        add_subnet_layout.addWidget(self.new_subnet)
        add_subnet_layout.addWidget(add_btn)
        
        list_layout.addLayout(add_subnet_layout)
        
        # Form panel
        form_panel = QWidget()
        form_layout = QVBoxLayout(form_panel)
        form_layout.setContentsMargins(10, 0, 0, 0)
        
        # Add header
        form_layout.addWidget(QLabel("<b>Subnet Credentials:</b>"))
        form_layout.addWidget(QLabel("Configure default connection settings for this subnet"))
        
        # Credential form
        cred_group = QGroupBox()
        cred_group.setStyleSheet("QGroupBox { padding-top: 15px; }")
        self.subnet_form = QFormLayout(cred_group)
        
        # Connection type
        self.subnet_conn_type = QComboBox()
        self.subnet_conn_type.addItems(["SSH", "Telnet"])
        self.subnet_form.addRow("Connection Type:", self.subnet_conn_type)
        
        # Username
        self.subnet_username = QLineEdit()
        self.subnet_username.setPlaceholderText("Enter username")
        self.subnet_form.addRow("Username:", self.subnet_username)
        
        # Password
        self.subnet_password = QLineEdit()
        self.subnet_password.setEchoMode(QLineEdit.Password)
        self.subnet_password.setPlaceholderText("Enter password")
        self.subnet_form.addRow("Password:", self.subnet_password)
        
        # Enable password
        self.subnet_enable = QLineEdit()
        self.subnet_enable.setEchoMode(QLineEdit.Password)
        self.subnet_enable.setPlaceholderText("Enter enable password (optional)")
        self.subnet_form.addRow("Enable Password:", self.subnet_enable)
        
        form_layout.addWidget(cred_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.subnet_save_btn = QPushButton("Save Credentials")
        self.subnet_save_btn.clicked.connect(self._on_save_subnet)
        self.subnet_save_btn.setEnabled(False)
        
        self.subnet_delete_btn = QPushButton("Delete Credentials")
        self.subnet_delete_btn.clicked.connect(self._on_delete_subnet)
        self.subnet_delete_btn.setEnabled(False)
        
        button_layout.addWidget(self.subnet_save_btn)
        button_layout.addWidget(self.subnet_delete_btn)
        button_layout.addStretch()
        
        form_layout.addLayout(button_layout)
        form_layout.addStretch()
        
        # Add panels to main layout
        layout.addWidget(list_panel, 1)
        layout.addWidget(form_panel, 2)
        
        # Add tab
        self.tabs.addTab(tab, "Subnet Credentials")
    
    def _load_data(self):
        """Load credential data"""
        self._load_devices()
        self._load_groups()
        self._load_subnets()
        
    def _load_devices(self):
        """Load device list and credentials"""
        # Clear list
        self.device_list.clear()
        
        # Current devices first
        for device in self.devices:
            item = QListWidgetItem(device.get_property("alias", "Unnamed Device"))
            item.setData(Qt.UserRole, device.id)
            self.device_list.addItem(item)
            
        # Then all devices with credentials
        device_credentials = self.plugin.get_all_device_credentials()
        for device_id, creds in device_credentials.items():
            # Skip if already in list
            found = False
            for i in range(self.device_list.count()):
                if self.device_list.item(i).data(Qt.UserRole) == device_id:
                    found = True
                    break
                    
            if found:
                continue
                
            # Try to get device info
            device = self.plugin.device_manager.get_device(device_id)
            if device:
                item = QListWidgetItem(device.get_property("alias", "Unnamed Device"))
            else:
                item = QListWidgetItem(f"Device {device_id}")
                
            item.setData(Qt.UserRole, device_id)
            self.device_list.addItem(item)
            
    def _load_groups(self):
        """Load group list and credentials"""
        # Clear list
        self.group_list.clear()
        
        # Get all groups
        groups = self.plugin.device_manager.get_groups()
        for group in groups:
            item = QListWidgetItem(group.name)
            item.setData(Qt.UserRole, group.name)
            self.group_list.addItem(item)
            
        # Then all groups with credentials
        group_credentials = self.plugin.get_all_group_credentials()
        for group_name in group_credentials.keys():
            # Skip if already in list
            found = False
            for i in range(self.group_list.count()):
                if self.group_list.item(i).data(Qt.UserRole) == group_name:
                    found = True
                    break
                    
            if found:
                continue
                
            # Add group
            item = QListWidgetItem(group_name)
            item.setData(Qt.UserRole, group_name)
            self.group_list.addItem(item)
            
    def _load_subnets(self):
        """Load subnet list and credentials"""
        # Clear list
        self.subnet_list.clear()
        
        # Get all subnets with credentials
        subnet_credentials = self.plugin.get_all_subnet_credentials()
        for subnet in subnet_credentials.keys():
            item = QListWidgetItem(subnet)
            item.setData(Qt.UserRole, subnet)
            self.subnet_list.addItem(item)
    
    def _on_device_selected(self, current, previous):
        """Handle device selection"""
        if not current:
            self.device_save_btn.setEnabled(False)
            self.device_delete_btn.setEnabled(False)
            return
            
        # Get device ID
        device_id = current.data(Qt.UserRole)
        
        # Get credentials
        credentials = self.plugin.get_device_credentials(device_id)
        
        # Fill form
        if credentials:
            # Set connection type
            conn_type = credentials.get("connection_type", "ssh").upper()
            index = self.device_conn_type.findText(conn_type)
            if index >= 0:
                self.device_conn_type.setCurrentIndex(index)
                
            # Set username
            self.device_username.setText(credentials.get("username", ""))
            
            # Set password
            self.device_password.setText(credentials.get("password", ""))
            
            # Set enable password
            self.device_enable.setText(credentials.get("enable_password", ""))
            
            # Enable delete button
            self.device_delete_btn.setEnabled(True)
        else:
            # Clear form
            self.device_conn_type.setCurrentIndex(0)
            self.device_username.clear()
            self.device_password.clear()
            self.device_enable.clear()
            
            # Disable delete button
            self.device_delete_btn.setEnabled(False)
            
        # Enable save button
        self.device_save_btn.setEnabled(True)
        
    def _on_group_selected(self, current, previous):
        """Handle group selection"""
        if not current:
            self.group_save_btn.setEnabled(False)
            self.group_delete_btn.setEnabled(False)
            return
            
        # Get group name
        group_name = current.data(Qt.UserRole)
        
        # Get credentials
        credentials = self.plugin.get_all_group_credentials().get(group_name, {})
        
        # Fill form
        if credentials:
            # Set connection type
            conn_type = credentials.get("connection_type", "ssh").upper()
            index = self.group_conn_type.findText(conn_type)
            if index >= 0:
                self.group_conn_type.setCurrentIndex(index)
                
            # Set username
            self.group_username.setText(credentials.get("username", ""))
            
            # Set password
            self.group_password.setText(credentials.get("password", ""))
            
            # Set enable password
            self.group_enable.setText(credentials.get("enable_password", ""))
            
            # Enable delete button
            self.group_delete_btn.setEnabled(True)
        else:
            # Clear form
            self.group_conn_type.setCurrentIndex(0)
            self.group_username.clear()
            self.group_password.clear()
            self.group_enable.clear()
            
            # Disable delete button
            self.group_delete_btn.setEnabled(False)
            
        # Enable save button
        self.group_save_btn.setEnabled(True)
        
    def _on_subnet_selected(self, current, previous):
        """Handle subnet selection"""
        if not current:
            self.subnet_save_btn.setEnabled(False)
            self.subnet_delete_btn.setEnabled(False)
            return
            
        # Get subnet
        subnet = current.data(Qt.UserRole)
        
        # Get credentials
        credentials = self.plugin.get_all_subnet_credentials().get(subnet, {})
        
        # Fill form
        if credentials:
            # Set connection type
            conn_type = credentials.get("connection_type", "ssh").upper()
            index = self.subnet_conn_type.findText(conn_type)
            if index >= 0:
                self.subnet_conn_type.setCurrentIndex(index)
                
            # Set username
            self.subnet_username.setText(credentials.get("username", ""))
            
            # Set password
            self.subnet_password.setText(credentials.get("password", ""))
            
            # Set enable password
            self.subnet_enable.setText(credentials.get("enable_password", ""))
            
            # Enable delete button
            self.subnet_delete_btn.setEnabled(True)
        else:
            # Clear form
            self.subnet_conn_type.setCurrentIndex(0)
            self.subnet_username.clear()
            self.subnet_password.clear()
            self.subnet_enable.clear()
            
            # Disable delete button
            self.subnet_delete_btn.setEnabled(False)
            
        # Enable save button
        self.subnet_save_btn.setEnabled(True)
        
    def _on_save_device(self):
        """Handle save device button"""
        # Get selected device
        current = self.device_list.currentItem()
        if not current:
            return
            
        # Get device ID
        device_id = current.data(Qt.UserRole)
        
        # Validate form
        username = self.device_username.text().strip()
        if not username:
            QMessageBox.warning(
                self,
                "Missing Username",
                "Please enter a username."
            )
            return
            
        # Create credentials
        credentials = {
            "connection_type": self.device_conn_type.currentText().lower(),
            "username": username,
            "password": self.device_password.text(),
            "enable_password": self.device_enable.text()
        }
        
        # Save credentials
        self.plugin.set_device_credentials(device_id, credentials)
        
        # Show success message
        QMessageBox.information(
            self,
            "Credentials Saved",
            f"Credentials for device saved successfully."
        )
        
    def _on_delete_device(self):
        """Handle delete device button"""
        # Get selected device
        current = self.device_list.currentItem()
        if not current:
            return
            
        # Get device ID
        device_id = current.data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete these credentials?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
            
        # Delete credentials
        self.plugin.delete_device_credentials(device_id)
        
        # Refresh UI
        self._on_device_selected(current, None)
        
    def _on_save_group(self):
        """Handle save group button"""
        # Get selected group
        current = self.group_list.currentItem()
        if not current:
            return
            
        # Get group name
        group_name = current.data(Qt.UserRole)
        
        # Validate form
        username = self.group_username.text().strip()
        if not username:
            QMessageBox.warning(
                self,
                "Missing Username",
                "Please enter a username."
            )
            return
            
        # Create credentials
        credentials = {
            "connection_type": self.group_conn_type.currentText().lower(),
            "username": username,
            "password": self.group_password.text(),
            "enable_password": self.group_enable.text()
        }
        
        # Save credentials
        self.plugin.set_group_credentials(group_name, credentials)
        
        # Show success message
        QMessageBox.information(
            self,
            "Credentials Saved",
            f"Credentials for group saved successfully."
        )
        
    def _on_delete_group(self):
        """Handle delete group button"""
        # Get selected group
        current = self.group_list.currentItem()
        if not current:
            return
            
        # Get group name
        group_name = current.data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete these credentials?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
            
        # Delete credentials
        self.plugin.delete_group_credentials(group_name)
        
        # Refresh UI
        self._on_group_selected(current, None)
        
    def _on_add_subnet(self):
        """Handle add subnet button"""
        # Get subnet
        subnet = self.new_subnet.text().strip()
        
        # Validate subnet
        if not subnet:
            QMessageBox.warning(
                self,
                "Missing Subnet",
                "Please enter a subnet."
            )
            return
            
        try:
            # Validate subnet format
            subnet_obj = ipaddress.ip_network(subnet, strict=False)
            subnet = str(subnet_obj)
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Subnet",
                "Please enter a valid subnet in CIDR notation (e.g. 192.168.1.0/24)."
            )
            return
            
        # Check if subnet already exists
        for i in range(self.subnet_list.count()):
            if self.subnet_list.item(i).data(Qt.UserRole) == subnet:
                # Select existing subnet
                self.subnet_list.setCurrentRow(i)
                return
                
        # Add subnet to list
        item = QListWidgetItem(subnet)
        item.setData(Qt.UserRole, subnet)
        self.subnet_list.addItem(item)
        
        # Select new subnet
        self.subnet_list.setCurrentItem(item)
        
        # Clear input field
        self.new_subnet.clear()
        
    def _on_save_subnet(self):
        """Handle save subnet button"""
        # Get selected subnet
        current = self.subnet_list.currentItem()
        if not current:
            return
            
        # Get subnet
        subnet = current.data(Qt.UserRole)
        
        # Validate form
        username = self.subnet_username.text().strip()
        if not username:
            QMessageBox.warning(
                self,
                "Missing Username",
                "Please enter a username."
            )
            return
            
        # Create credentials
        credentials = {
            "connection_type": self.subnet_conn_type.currentText().lower(),
            "username": username,
            "password": self.subnet_password.text(),
            "enable_password": self.subnet_enable.text()
        }
        
        # Save credentials
        self.plugin.set_subnet_credentials(subnet, credentials)
        
        # Show success message
        QMessageBox.information(
            self,
            "Credentials Saved",
            f"Credentials for subnet saved successfully."
        )
        
    def _on_delete_subnet(self):
        """Handle delete subnet button"""
        # Get selected subnet
        current = self.subnet_list.currentItem()
        if not current:
            return
            
        # Get subnet
        subnet = current.data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete these credentials?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
            
        # Delete credentials
        self.plugin.delete_subnet_credentials(subnet)
        
        # Remove from list
        row = self.subnet_list.currentRow()
        self.subnet_list.takeItem(row)
        
        # Clear form
        self.subnet_conn_type.setCurrentIndex(0)
        self.subnet_username.clear()
        self.subnet_password.clear()
        self.subnet_enable.clear()
        
        # Disable buttons
        self.subnet_save_btn.setEnabled(False)
        self.subnet_delete_btn.setEnabled(False) 