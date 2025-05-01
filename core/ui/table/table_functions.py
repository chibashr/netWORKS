"""
Table management functions for the netWORKS application.
These functions were extracted from main_window.py to improve modularity.
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QLabel, QCheckBox, QWidget, QSpacerItem, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QLineEdit
)
from PySide6.QtCore import Qt, QSize

# Setup logger
logger = logging.getLogger(__name__)

def customize_table_columns(main_window):
    """Show dialog for customizing device table columns."""
    dialog = QDialog(main_window)
    dialog.setWindowTitle("Customize Columns")
    dialog.resize(500, 400)
    
    # Create layout
    layout = QVBoxLayout(dialog)
    
    # Explanation label
    label = QLabel("Select columns to display in the device table:")
    layout.addWidget(label)
    
    # Available columns
    all_columns = [
        "ip", "hostname", "mac", "vendor", "scan_method", 
        "ports", "last_seen", "first_seen", "status", "alias"
    ]
    
    # Add metadata columns from devices
    for device in main_window.device_table.devices:
        if "metadata" in device:
            for key in device["metadata"]:
                if key not in all_columns and key != "tags":
                    all_columns.append(key)
    
    # Currently selected columns
    current_columns = main_window.config["ui"]["table"]["columns"]
    
    # Create list widget for column selection with better styling
    list_widget = QListWidget()
    list_widget.setStyleSheet("""
        QListWidget {
            background-color: white;
            border: 1px solid #d0dbe8;
            border-radius: 3px;
        }
        QListWidget::item {
            padding: 5px;
            border-bottom: 1px solid #f0f4f8;
        }
        QListWidget::item:hover {
            background-color: #f5f9ff;
        }
        QListWidget::item:selected {
            background-color: #e8f0ff;
            color: #2c5aa0;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 1px solid #d0dbe8;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:unchecked:hover {
            border-color: #2c5aa0;
        }
        QCheckBox::indicator:checked {
            background-color: #2c5aa0;
            border-color: #2c5aa0;
            image: url(core/ui/icons/check.png);
        }
    """)
    
    for column in all_columns:
        item = QListWidgetItem(column)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        if column in current_columns:
            item.setCheckState(Qt.CheckState.Checked)
        else:
            item.setCheckState(Qt.CheckState.Unchecked)
        list_widget.addItem(item)
    
    layout.addWidget(list_widget)
    
    # Quick selection buttons
    selection_layout = QHBoxLayout()
    
    select_all_btn = QPushButton("Select All")
    select_all_btn.setStyleSheet("""
        QPushButton {
            background-color: #f0f4f8;
            border: 1px solid #d0dbe8;
            border-radius: 3px;
            padding: 6px 12px;
            color: #2c5aa0;
        }
        QPushButton:hover {
            background-color: #e8f0ff;
            border-color: #2c5aa0;
        }
        QPushButton:pressed {
            background-color: #d0e0ff;
            padding-top: 7px;
            padding-bottom: 5px;
            padding-left: 13px;
            padding-right: 11px;
            box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.125);
        }
    """)
    select_all_btn.clicked.connect(lambda: [list_widget.item(i).setCheckState(Qt.CheckState.Checked) for i in range(list_widget.count())])
    
    deselect_all_btn = QPushButton("Deselect All")
    deselect_all_btn.setStyleSheet("""
        QPushButton {
            background-color: #f0f4f8;
            border: 1px solid #d0dbe8;
            border-radius: 3px;
            padding: 6px 12px;
            color: #2c5aa0;
        }
        QPushButton:hover {
            background-color: #e8f0ff;
            border-color: #2c5aa0;
        }
        QPushButton:pressed {
            background-color: #d0e0ff;
            padding-top: 7px;
            padding-bottom: 5px;
            padding-left: 13px;
            padding-right: 11px;
            box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.125);
        }
    """)
    deselect_all_btn.clicked.connect(lambda: [list_widget.item(i).setCheckState(Qt.CheckState.Unchecked) for i in range(list_widget.count())])
    
    reset_default_btn = QPushButton("Reset to Default")
    reset_default_btn.setStyleSheet("""
        QPushButton {
            background-color: #f0f4f8;
            border: 1px solid #d0dbe8;
            border-radius: 3px;
            padding: 6px 12px;
            color: #2c5aa0;
        }
        QPushButton:hover {
            background-color: #e8f0ff;
            border-color: #2c5aa0;
        }
        QPushButton:pressed {
            background-color: #d0e0ff;
            padding-top: 7px;
            padding-bottom: 5px;
            padding-left: 13px;
            padding-right: 11px;
            box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.125);
        }
    """)
    
    # Define default columns
    default_columns = ["ip", "hostname", "mac", "vendor", "ports", "status"]
    
    def reset_to_default():
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.text() in default_columns:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
                
    reset_default_btn.clicked.connect(reset_to_default)
    
    selection_layout.addWidget(select_all_btn)
    selection_layout.addWidget(deselect_all_btn)
    selection_layout.addWidget(reset_default_btn)
    
    layout.addLayout(selection_layout)
    
    # Button layout
    button_layout = QHBoxLayout()
    
    # Add spacer to push buttons to the right
    spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    button_layout.addItem(spacer)
    
    # Cancel button
    cancel_button = QPushButton("Cancel")
    cancel_button.setStyleSheet("""
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
            padding-top: 7px;
            padding-bottom: 5px;
            padding-left: 13px;
            padding-right: 11px;
        }
    """)
    cancel_button.clicked.connect(dialog.reject)
    button_layout.addWidget(cancel_button)
    
    # Apply button
    apply_button = QPushButton("Apply")
    apply_button.setStyleSheet("""
        QPushButton {
            background-color: #2c5aa0;
            border: 1px solid #224b84;
            border-radius: 3px;
            padding: 6px 12px;
            font-weight: bold;
            color: white;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #224b84;
        }
        QPushButton:pressed {
            background-color: #1b3c69;
            padding-top: 7px;
            padding-bottom: 5px;
            padding-left: 13px;
            padding-right: 11px;
        }
    """)
    apply_button.clicked.connect(dialog.accept)
    button_layout.addWidget(apply_button)
    
    layout.addLayout(button_layout)
    
    # Show dialog
    if dialog.exec_() == QDialog.DialogCode.Accepted:
        # Update columns in config
        selected_columns = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_columns.append(item.text())
        
        # Update config
        main_window.config["ui"]["table"]["columns"] = selected_columns
        main_window.save_config()
        
        # Update table
        main_window.device_table.configure_columns(selected_columns)
        
        return True
    
    return False

def manage_device_aliases(main_window):
    """Show dialog for managing device aliases."""
    dialog = QDialog(main_window)
    dialog.setWindowTitle("Manage Device Aliases")
    dialog.resize(600, 400)
    
    # Create layout
    layout = QVBoxLayout(dialog)
    
    # Explanation label
    label = QLabel("Set custom aliases for devices on your network:")
    layout.addWidget(label)
    
    # Create table for aliases
    alias_table = QTableWidget()
    alias_table.setColumnCount(3)
    alias_table.setHorizontalHeaderLabels(["IP Address", "Hostname", "Alias"])
    
    # Set column stretching
    header = alias_table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    
    # Populate table with devices
    devices = main_window.device_table.devices
    alias_table.setRowCount(len(devices))
    
    for row, device in enumerate(devices):
        # IP Address
        ip_item = QTableWidgetItem(device.get("ip", "N/A"))
        ip_item.setFlags(ip_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        alias_table.setItem(row, 0, ip_item)
        
        # Hostname
        hostname_item = QTableWidgetItem(device.get("hostname", "Unknown"))
        hostname_item.setFlags(hostname_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        alias_table.setItem(row, 1, hostname_item)
        
        # Alias (editable)
        alias_item = QTableWidgetItem(device.get("alias", ""))
        alias_item.setFlags(alias_item.flags() | Qt.ItemFlag.ItemIsEditable)
        alias_table.setItem(row, 2, alias_item)
    
    layout.addWidget(alias_table)
    
    # Button layout
    button_layout = QHBoxLayout()
    
    # Add spacer to push buttons to the right
    spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    button_layout.addItem(spacer)
    
    # Cancel button
    cancel_button = QPushButton("Cancel")
    cancel_button.clicked.connect(dialog.reject)
    button_layout.addWidget(cancel_button)
    
    # Apply button
    apply_button = QPushButton("Apply")
    apply_button.clicked.connect(dialog.accept)
    button_layout.addWidget(apply_button)
    
    layout.addLayout(button_layout)
    
    # Show dialog
    if dialog.exec_() == QDialog.DialogCode.Accepted:
        # Update device aliases
        for row in range(alias_table.rowCount()):
            ip = alias_table.item(row, 0).text()
            alias = alias_table.item(row, 2).text()
            
            # Find device in device list
            for device in main_window.device_table.devices:
                if device.get("ip") == ip:
                    # Set alias in device data
                    device["alias"] = alias
                    
                    # Add alias to metadata if not already there
                    if "metadata" not in device:
                        device["metadata"] = {}
                    device["metadata"]["alias"] = alias
                    
                    # Save to database if available
                    if hasattr(main_window, 'database_manager') and main_window.database_manager:
                        main_window.database_manager.save_device(device)
        
        # Refresh device table
        main_window.device_table.update_data(main_window.device_table.devices)
        
        # Make sure 'alias' column is available
        if "alias" not in main_window.config["ui"]["table"]["columns"]:
            customize_table_columns(main_window)
            
        return True
        
    return False 