#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI components for Network Scanner Plugin
"""

from loguru import logger
from PySide6.QtWidgets import (
    QLabel, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QDockWidget,
    QPushButton, QTabWidget, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QGridLayout, QFormLayout, QGroupBox, QCheckBox, QComboBox,
    QSplitter, QProgressBar, QMessageBox, QLineEdit, QTableWidget, 
    QTableWidgetItem, QDialog, QDialogButtonBox, QMenu, QFileDialog,
    QRadioButton, QInputDialog, QHeaderView
)
from PySide6.QtCore import Qt, QSize, QTimer, QThread
from PySide6.QtGui import QIcon, QAction, QColor, QIntValidator

def create_main_widget():
    """Create the main plugin widget"""
    # Main widget
    main_widget = QWidget()
    main_layout = QVBoxLayout(main_widget)
    main_layout.setContentsMargins(8, 8, 8, 8)  # Add proper margins
    main_layout.setSpacing(10)  # Increase spacing between main sections
    
    # Create a top section for controls
    top_section = QWidget()
    top_layout = QVBoxLayout(top_section)
    top_layout.setContentsMargins(0, 0, 0, 0)
    top_layout.setSpacing(8)
    
    # Input and controls
    control_group = QGroupBox("Network Scan Controls")
    control_layout = QFormLayout(control_group)
    control_layout.setSpacing(8)  # Increase spacing between form rows
    control_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # Allow fields to expand
    
    # Interface selection
    interface_layout = QHBoxLayout()
    interface_layout.setSpacing(8)
    interface_combo = QComboBox()
    
    refresh_interfaces_button = QPushButton("Refresh")
    refresh_interfaces_button.setToolTip("Refresh network interface list")
    interface_layout.addWidget(interface_combo, 1)
    interface_layout.addWidget(refresh_interfaces_button)
    control_layout.addRow("Network Interface:", interface_layout)
    
    # Network range input - now in its own section with more space
    network_range_label = QLabel("Network Range:")
    network_range_edit = QLineEdit()
    network_range_edit.setPlaceholderText("e.g., 192.168.1.0/24 or 10.0.0.1-10.0.0.254")
    control_layout.addRow(network_range_label, network_range_edit)
    
    # Scan type with manager button
    scan_type_layout = QHBoxLayout()
    scan_type_layout.setSpacing(8)
    
    scan_type_combo = QComboBox()
    
    scan_type_manager_button = QPushButton("Manage")
    scan_type_manager_button.setToolTip("Manage scan profiles and types")
    
    scan_type_layout.addWidget(scan_type_combo, 1)
    scan_type_layout.addWidget(scan_type_manager_button)
    
    control_layout.addRow("Scan Type:", scan_type_layout)
    
    # Scan controls in separate section with buttons side by side
    button_layout = QHBoxLayout()
    button_layout.setSpacing(10)  # Increase spacing between buttons
    
    # Create a button grid with 2x2 layout for better organization
    button_grid = QGridLayout()
    button_grid.setSpacing(8)
    button_grid.setHorizontalSpacing(10)
    button_grid.setVerticalSpacing(8)
    
    # Set a fixed minimum width for all buttons to prevent overlapping
    button_width = 100
    
    # Scan button
    scan_button = QPushButton("Start Scan")
    scan_button.setMinimumWidth(button_width)
    button_grid.addWidget(scan_button, 0, 0)
    
    # Quick Ping Scan button
    quick_ping_button = QPushButton("Quick Ping")
    quick_ping_button.setMinimumWidth(button_width)
    quick_ping_button.setToolTip("Fast ping scan without using nmap")
    button_grid.addWidget(quick_ping_button, 0, 1)
    
    # Advanced Scan button
    advanced_scan_button = QPushButton("Advanced...")
    advanced_scan_button.setMinimumWidth(button_width)
    advanced_scan_button.setToolTip("Open the advanced scan configuration dialog")
    button_grid.addWidget(advanced_scan_button, 1, 0)
    
    # Stop button
    stop_button = QPushButton("Stop")
    stop_button.setMinimumWidth(button_width)
    stop_button.setEnabled(False)
    button_grid.addWidget(stop_button, 1, 1)
    
    # Add the grid to the layout
    button_layout.addLayout(button_grid)
    
    # Add stretch to push buttons to the left
    button_layout.addStretch(1)
    
    # Add button layout to form with empty label to align properly
    control_layout.addRow("", button_layout)
    
    # Create a horizontal layout for checkboxes to save space
    checkbox_layout = QHBoxLayout()
    checkbox_layout.setSpacing(20)  # Add spacing between checkboxes
    
    # OS Detection
    os_detection_widget = QWidget()
    os_detection_layout = QHBoxLayout(os_detection_widget)
    os_detection_layout.setContentsMargins(0, 0, 0, 0)
    os_detection_label = QLabel("OS Detection:")
    os_detection_check = QCheckBox()
    os_detection_layout.addWidget(os_detection_label)
    os_detection_layout.addWidget(os_detection_check)
    checkbox_layout.addWidget(os_detection_widget)
    
    # Port Scanning
    port_scan_widget = QWidget()
    port_scan_layout = QHBoxLayout(port_scan_widget)
    port_scan_layout.setContentsMargins(0, 0, 0, 0)
    port_scan_label = QLabel("Port Scanning:")
    port_scan_check = QCheckBox()
    port_scan_layout.addWidget(port_scan_label)
    port_scan_layout.addWidget(port_scan_check)
    checkbox_layout.addWidget(port_scan_widget)
    
    # Add spacer to push checkboxes to the left
    checkbox_layout.addStretch(1)
    
    # Add the checkbox layout to the control layout
    control_widget = QWidget()
    control_widget.setLayout(checkbox_layout)
    control_layout.addRow("", control_widget)
    
    # Add the control group to the top section
    top_layout.addWidget(control_group)
    
    # Progress section
    progress_widget = QWidget()
    progress_layout = QVBoxLayout(progress_widget)
    progress_layout.setContentsMargins(4, 4, 4, 4)
    progress_layout.setSpacing(4)
    
    # Status label
    status_label = QLabel("Ready")
    progress_layout.addWidget(status_label)
    
    # Progress bar
    progress_bar = QProgressBar()
    progress_bar.setRange(0, 100)
    progress_bar.setValue(0)
    progress_layout.addWidget(progress_bar)
    
    # Add progress widget to top section
    top_layout.addWidget(progress_widget)
    
    # Results section
    results_group = QGroupBox("Scan Results")
    results_layout = QVBoxLayout(results_group)
    results_layout.setContentsMargins(8, 12, 8, 8)  # Add internal margins for better readability
    
    # Results list
    results_text = QTextEdit()
    results_text.setReadOnly(True)
    results_layout.addWidget(results_text)
    
    # Create a splitter to allow resizing between controls and results
    main_splitter = QSplitter(Qt.Vertical)
    main_splitter.addWidget(top_section)
    main_splitter.addWidget(results_group)
    main_splitter.setStretchFactor(0, 0)  # Don't stretch the top section
    main_splitter.setStretchFactor(1, 1)  # Let the results section take extra space
    main_splitter.setSizes([200, 400])  # Set initial sizes
    
    # Add the splitter to the main layout
    main_layout.addWidget(main_splitter)
    
    # Build a dictionary of UI components to return
    ui_components = {
        'main_widget': main_widget,
        'interface_combo': interface_combo,
        'refresh_interfaces_button': refresh_interfaces_button,
        'network_range_edit': network_range_edit,
        'scan_type_combo': scan_type_combo,
        'scan_type_manager_button': scan_type_manager_button,
        'scan_button': scan_button,
        'quick_ping_button': quick_ping_button,
        'advanced_scan_button': advanced_scan_button,
        'stop_button': stop_button,
        'os_detection_check': os_detection_check,
        'port_scan_check': port_scan_check,
        'status_label': status_label,
        'progress_bar': progress_bar,
        'results_text': results_text,
        'main_splitter': main_splitter
    }
    
    return ui_components

def create_dock_widget(main_widget, name="Network Scanner"):
    """Create a dock widget containing the main widget"""
    dock = QDockWidget(name)
    dock.setWidget(main_widget)
    dock.setObjectName("NetworkScannerDock")
    dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
    
    # Set minimum width to prevent controls from being too cramped
    main_widget.setMinimumWidth(300)
    
    return dock

def create_scan_type_manager_dialog(parent, settings):
    """Create the scan type manager dialog"""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Scan Type Manager")
    dialog.setMinimumWidth(700)
    dialog.setMinimumHeight(400)
    
    layout = QVBoxLayout(dialog)
    layout.setSpacing(12)
    
    # Add description
    description_label = QLabel(
        "Manage your scan profiles. You can create new profiles, edit existing ones, or delete custom profiles."
    )
    description_label.setWordWrap(True)
    description_label.setStyleSheet("padding: 8px; background-color: #f0f0f0; border-radius: 4px;")
    layout.addWidget(description_label)
    
    # Create a table to display profiles
    profile_table = QTableWidget()
    profile_table.setColumnCount(5)
    profile_table.setHorizontalHeaderLabels(["Name", "Description", "Arguments", "OS Detection", "Port Scan"])
    profile_table.horizontalHeader().setStretchLastSection(True)
    profile_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
    profile_table.setSelectionBehavior(QTableWidget.SelectRows)
    profile_table.setSelectionMode(QTableWidget.SingleSelection)
    layout.addWidget(profile_table)
    
    # Function to refresh the table
    def refresh_table():
        profile_table.setRowCount(0)
        profiles = settings["scan_profiles"]["value"]
        
        for i, (profile_id, profile) in enumerate(profiles.items()):
            is_builtin = profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]
            
            profile_table.insertRow(i)
            
            # Name column
            name_item = QTableWidgetItem(profile.get("name", profile_id))
            if is_builtin:
                name_item.setToolTip("Built-in profile (can't be deleted)")
                # Set a background color for built-in profiles
                name_item.setBackground(QColor("#f0f0f0"))
            name_item.setData(Qt.UserRole, profile_id)  # Store profile ID
            profile_table.setItem(i, 0, name_item)
            
            # Description column
            profile_table.setItem(i, 1, QTableWidgetItem(profile.get("description", "")))
            
            # Arguments column
            profile_table.setItem(i, 2, QTableWidgetItem(profile.get("arguments", "")))
            
            # OS Detection column
            os_detection_item = QTableWidgetItem("Yes" if profile.get("os_detection", False) else "No")
            os_detection_item.setTextAlignment(Qt.AlignCenter)
            profile_table.setItem(i, 3, os_detection_item)
            
            # Port Scan column
            port_scan_item = QTableWidgetItem("Yes" if profile.get("port_scan", False) else "No")
            port_scan_item.setTextAlignment(Qt.AlignCenter)
            profile_table.setItem(i, 4, port_scan_item)
            
        profile_table.resizeColumnsToContents()
        # Ensure description column gets some minimum width
        if profile_table.columnWidth(1) < 150:
            profile_table.setColumnWidth(1, 150)
    
    # First populate the table
    refresh_table()
    
    # Button layout
    button_layout = QHBoxLayout()
    new_button = QPushButton("New Profile")
    edit_button = QPushButton("Edit Profile")
    delete_button = QPushButton("Delete Profile")
    # Initially disable edit/delete until a row is selected
    edit_button.setEnabled(False)
    delete_button.setEnabled(False)
    
    button_layout.addWidget(new_button)
    button_layout.addWidget(edit_button)
    button_layout.addWidget(delete_button)
    button_layout.addStretch(1)
    
    layout.addLayout(button_layout)
    
    # Add dialog buttons
    dialog_buttons = QDialogButtonBox(QDialogButtonBox.Close)
    dialog_buttons.rejected.connect(dialog.reject)
    layout.addWidget(dialog_buttons)
    
    # Handle selection change
    def on_selection_changed():
        selected_indexes = profile_table.selectedIndexes()
        if selected_indexes:
            row = selected_indexes[0].row()
            profile_id = profile_table.item(row, 0).data(Qt.UserRole)
            is_builtin = profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]
            
            edit_button.setEnabled(True)
            delete_button.setEnabled(not is_builtin)
        else:
            edit_button.setEnabled(False)
            delete_button.setEnabled(False)
    
    profile_table.itemSelectionChanged.connect(on_selection_changed)
    
    # Create the profile edit dialog function
    def edit_profile_dialog(profile_id=None, is_new=False):
        edit_dialog = QDialog(dialog)
        edit_dialog.setWindowTitle("New Scan Profile" if is_new else "Edit Scan Profile")
        edit_dialog.setMinimumWidth(450)
        
        edit_layout = QVBoxLayout(edit_dialog)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Profile ID (for new profiles only)
        profile_id_edit = QLineEdit()
        if is_new:
            form_layout.addRow("Profile ID:", profile_id_edit)
            profile_id_edit.setPlaceholderText("e.g., custom_scan (no spaces, lowercase)")
        
        # Name
        profile_name_edit = QLineEdit()
        form_layout.addRow("Display Name:", profile_name_edit)
        
        # Description
        profile_desc_edit = QLineEdit()
        form_layout.addRow("Description:", profile_desc_edit)
        
        # Arguments
        profile_args_edit = QLineEdit()
        form_layout.addRow("Arguments:", profile_args_edit)
        profile_args_edit.setPlaceholderText("e.g., -sn -F")
        
        # OS Detection
        profile_os_check = QCheckBox()
        form_layout.addRow("OS Detection:", profile_os_check)
        
        # Port Scanning
        profile_port_check = QCheckBox()
        form_layout.addRow("Port Scanning:", profile_port_check)
        
        # Timeout
        profile_timeout_edit = QLineEdit()
        profile_timeout_edit.setValidator(QIntValidator(30, 600))
        form_layout.addRow("Timeout (seconds):", profile_timeout_edit)
        
        # If editing, populate with existing values
        if not is_new and profile_id:
            profile = settings["scan_profiles"]["value"].get(profile_id, {})
            profile_name_edit.setText(profile.get("name", ""))
            profile_desc_edit.setText(profile.get("description", ""))
            profile_args_edit.setText(profile.get("arguments", ""))
            profile_os_check.setChecked(profile.get("os_detection", False))
            profile_port_check.setChecked(profile.get("port_scan", False))
            profile_timeout_edit.setText(str(profile.get("timeout", 300)))
        
        edit_layout.addLayout(form_layout)
        
        # Add dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(edit_dialog.accept)
        button_box.rejected.connect(edit_dialog.reject)
        edit_layout.addWidget(button_box)
        
        # Show dialog and handle result
        if edit_dialog.exec() == QDialog.Accepted:
            # Get values from form
            if is_new:
                new_id = profile_id_edit.text().strip().lower().replace(" ", "_")
                if not new_id:
                    QMessageBox.warning(dialog, "Invalid ID", "Profile ID cannot be empty.")
                    return
                
                # Check if ID exists
                if new_id in settings["scan_profiles"]["value"]:
                    QMessageBox.warning(dialog, "Profile Exists", f"A profile with ID '{new_id}' already exists.")
                    return
                
                profile_id = new_id
            
            # Create updated profile
            updated_profile = {
                "name": profile_name_edit.text(),
                "description": profile_desc_edit.text(),
                "arguments": profile_args_edit.text(),
                "os_detection": profile_os_check.isChecked(),
                "port_scan": profile_port_check.isChecked(),
                "timeout": int(profile_timeout_edit.text() or "300")
            }
            
            # Update settings
            profiles = settings["scan_profiles"]["value"].copy()
            profiles[profile_id] = updated_profile
            settings["scan_profiles"]["value"] = profiles
            
            # Update scan type choices if needed
            if profile_id not in settings["scan_type"]["choices"]:
                choices = list(settings["scan_type"]["choices"])
                choices.append(profile_id)
                settings["scan_type"]["choices"] = choices
            
            # Refresh the table
            refresh_table()
            
            return True
        
        return False
    
    # Connect button handlers
    new_button.clicked.connect(lambda: edit_profile_dialog(is_new=True))
    edit_button.clicked.connect(lambda: 
        edit_profile_dialog(
            profile_table.item(profile_table.selectedIndexes()[0].row(), 0).data(Qt.UserRole)
        ) if profile_table.selectedIndexes() else None
    )
    
    def on_delete_profile():
        if not profile_table.selectedIndexes():
            return
            
        row = profile_table.selectedIndexes()[0].row()
        profile_id = profile_table.item(row, 0).data(Qt.UserRole)
        
        # Check if built-in
        if profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]:
            QMessageBox.warning(dialog, "Cannot Delete", "Built-in profiles cannot be deleted.")
            return
            
        # Confirm deletion
        result = QMessageBox.question(
            dialog, 
            "Confirm Deletion",
            f"Are you sure you want to delete the profile '{profile_id}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            # Delete the profile
            profiles = settings["scan_profiles"]["value"].copy()
            if profile_id in profiles:
                del profiles[profile_id]
                settings["scan_profiles"]["value"] = profiles
                
                # Also remove from choices if needed
                if profile_id in settings["scan_type"]["choices"]:
                    choices = list(settings["scan_type"]["choices"])
                    choices.remove(profile_id)
                    settings["scan_type"]["choices"] = choices
                
                # Refresh the table
                refresh_table()
    
    delete_button.clicked.connect(on_delete_profile)
    
    # Return everything needed
    return {
        'dialog': dialog,
        'refresh_table': refresh_table,
        'profile_table': profile_table,
        'edit_profile_dialog': edit_profile_dialog
    }

def show_advanced_scan_dialog(parent, settings):
    """Show the advanced scan configuration dialog"""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Advanced Scan Configuration")
    dialog.setMinimumWidth(500)
    
    layout = QVBoxLayout(dialog)
    
    # Create a form layout for all options
    form_layout = QFormLayout()
    form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
    
    # Scan Type Selection
    scan_type_combo = QComboBox()
    scan_type_combo.addItems(settings["scan_type"]["choices"])
    scan_type_combo.setCurrentText(settings["scan_type"]["value"])
    form_layout.addRow("Scan Type:", scan_type_combo)
    
    # Network Range
    network_range_edit = QLineEdit()
    network_range_edit.setPlaceholderText("e.g., 192.168.1.0/24 or 10.0.0.1-10.0.0.254")
    form_layout.addRow("Network Range:", network_range_edit)
    
    # Timeout
    timeout_edit = QLineEdit()
    timeout_edit.setValidator(QIntValidator(30, 900))
    timeout_edit.setText(str(settings["scan_timeout"]["value"]))
    form_layout.addRow("Timeout (seconds):", timeout_edit)
    
    # OS Detection
    os_detection_check = QCheckBox()
    os_detection_check.setChecked(settings["os_detection"]["value"])
    form_layout.addRow("OS Detection:", os_detection_check)
    
    # Port Scan
    port_scan_check = QCheckBox()
    port_scan_check.setChecked(settings["port_scan"]["value"])
    form_layout.addRow("Port Scanning:", port_scan_check)
    
    # Use Sudo/Elevated Permissions
    sudo_check = QCheckBox()
    sudo_check.setChecked(settings["use_sudo"]["value"])
    form_layout.addRow("Use Elevated Permissions:", sudo_check)
    
    # Custom Arguments
    custom_args_edit = QLineEdit()
    custom_args_edit.setText(settings["custom_scan_args"]["value"])
    custom_args_edit.setPlaceholderText("e.g., -p 22,80,443 -sV")
    form_layout.addRow("Custom Arguments:", custom_args_edit)
    
    layout.addLayout(form_layout)
    
    # Add help text
    help_text = QLabel(
        "Custom arguments will override default settings. Use with caution.\n"
        "Elevated permissions may be required for some scan types (e.g., SYN scans)."
    )
    help_text.setWordWrap(True)
    help_text.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
    layout.addWidget(help_text)
    
    # Add buttons
    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)
    
    # Show the dialog
    result = dialog.exec()
    if result == QDialog.Accepted:
        # Collect results
        return {
            'scan_type': scan_type_combo.currentText(),
            'network_range': network_range_edit.text(),
            'timeout': int(timeout_edit.text() or "600"),
            'os_detection': os_detection_check.isChecked(),
            'port_scan': port_scan_check.isChecked(),
            'use_sudo': sudo_check.isChecked(),
            'custom_scan_args': custom_args_edit.text()
        }
    else:
        return None

def show_error_message(parent, title, message):
    """Show an error message dialog"""
    QMessageBox.critical(parent, title, message)
    
def show_info_message(parent, title, message):
    """Show an information message dialog"""
    QMessageBox.information(parent, title, message)
    
def show_question_dialog(parent, title, message):
    """Show a question dialog with Yes/No buttons"""
    return QMessageBox.question(
        parent, title, message, 
        QMessageBox.Yes | QMessageBox.No
    ) == QMessageBox.Yes 