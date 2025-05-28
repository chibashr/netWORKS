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
    main_layout.setContentsMargins(6, 6, 6, 6)  # Reduced margins
    main_layout.setSpacing(6)  # Reduced spacing
    
    # Create a compact top section for controls
    top_section = QWidget()
    top_layout = QVBoxLayout(top_section)
    top_layout.setContentsMargins(0, 0, 0, 0)
    top_layout.setSpacing(4)  # Minimal spacing
    
    # Network Interface row
    interface_layout = QHBoxLayout()
    interface_layout.setSpacing(6)
    interface_layout.addWidget(QLabel("Interface:"))
    interface_combo = QComboBox()
    interface_combo.setSizePolicy(interface_combo.sizePolicy().horizontalPolicy(), interface_combo.sizePolicy().verticalPolicy())
    interface_layout.addWidget(interface_combo, 1)
    refresh_interfaces_button = QPushButton("Refresh")
    refresh_interfaces_button.setMaximumWidth(70)
    refresh_interfaces_button.setToolTip("Refresh network interface list")
    interface_layout.addWidget(refresh_interfaces_button)
    top_layout.addLayout(interface_layout)
    
    # Network Range row
    range_layout = QHBoxLayout()
    range_layout.setSpacing(6)
    range_layout.addWidget(QLabel("Range:"))
    network_range_edit = QLineEdit()
    network_range_edit.setPlaceholderText("e.g., 192.168.1.0/24")
    range_layout.addWidget(network_range_edit, 1)
    top_layout.addLayout(range_layout)
    
    # Scan Type row
    scan_type_layout = QHBoxLayout()
    scan_type_layout.setSpacing(6)
    scan_type_layout.addWidget(QLabel("Scan Type:"))
    scan_type_combo = QComboBox()
    scan_type_layout.addWidget(scan_type_combo, 1)
    scan_type_manager_button = QPushButton("Manager")
    scan_type_manager_button.setMaximumWidth(70)
    scan_type_manager_button.setToolTip("Manage scan profiles and types")
    scan_type_layout.addWidget(scan_type_manager_button)
    top_layout.addLayout(scan_type_layout)
    
    # Options row (checkboxes inline)
    options_layout = QHBoxLayout()
    options_layout.setSpacing(15)
    
    os_detection_check = QCheckBox("OS Detection")
    port_scan_check = QCheckBox("Port Scanning")
    options_layout.addWidget(os_detection_check)
    options_layout.addWidget(port_scan_check)
    options_layout.addStretch(1)
    top_layout.addLayout(options_layout)
    
    # Button row - more compact arrangement
    button_layout = QHBoxLayout()
    button_layout.setSpacing(6)
    
    # Make buttons more compact
    button_width = 75
    
    scan_button = QPushButton("Start Scan")
    scan_button.setMaximumWidth(button_width + 10)
    button_layout.addWidget(scan_button)
    
    quick_ping_button = QPushButton("Quick Ping")
    quick_ping_button.setMaximumWidth(button_width + 10)
    quick_ping_button.setToolTip("Fast ping scan without using nmap")
    button_layout.addWidget(quick_ping_button)
    
    stop_button = QPushButton("Stop")
    stop_button.setMaximumWidth(button_width - 10)
    stop_button.setEnabled(False)
    button_layout.addWidget(stop_button)
    
    button_layout.addStretch(1)  # Push buttons to the left
    top_layout.addLayout(button_layout)
    
    # Progress section - more compact
    progress_layout = QVBoxLayout()
    progress_layout.setSpacing(2)
    
    status_label = QLabel("Ready")
    status_label.setMaximumHeight(20)  # Limit height
    progress_layout.addWidget(status_label)
    
    progress_bar = QProgressBar()
    progress_bar.setRange(0, 100)
    progress_bar.setValue(0)
    progress_bar.setMaximumHeight(20)  # Limit height
    progress_layout.addWidget(progress_bar)
    
    top_layout.addLayout(progress_layout)
    
    # Results section with working toggle
    results_section = QWidget()
    results_main_layout = QVBoxLayout(results_section)
    results_main_layout.setContentsMargins(0, 0, 0, 0)
    results_main_layout.setSpacing(4)
    
    # Results header with toggle button
    results_header = QWidget()
    results_header_layout = QHBoxLayout(results_header)
    results_header_layout.setContentsMargins(6, 4, 6, 4)
    results_header_layout.setSpacing(6)
    
    results_title = QLabel("Detailed Scan Logs")
    results_title.setStyleSheet("font-weight: bold;")
    results_header_layout.addWidget(results_title)
    results_header_layout.addStretch(1)
    
    results_toggle_button = QPushButton("Hide")
    results_toggle_button.setMaximumWidth(60)
    results_toggle_button.setCheckable(True)
    results_toggle_button.setChecked(False)  # Start unchecked (logs visible)
    results_header_layout.addWidget(results_toggle_button)
    
    results_main_layout.addWidget(results_header)
    
    # Results content (the part that gets hidden/shown)
    results_content = QWidget()
    results_content_layout = QVBoxLayout(results_content)
    results_content_layout.setContentsMargins(6, 0, 6, 6)
    results_content_layout.setSpacing(0)
    
    results_text = QTextEdit()
    results_text.setReadOnly(True)
    results_text.setMinimumHeight(100)  # Set a reasonable minimum
    results_content_layout.addWidget(results_text)
    
    results_main_layout.addWidget(results_content)
    
    # Create main splitter
    main_splitter = QSplitter(Qt.Vertical)
    main_splitter.addWidget(top_section)
    main_splitter.addWidget(results_section)
    main_splitter.setStretchFactor(0, 0)  # Don't stretch the top section
    main_splitter.setStretchFactor(1, 1)  # Let the results section take extra space
    
    # Set initial sizes - make top section more compact
    main_splitter.setSizes([180, 300])
    
    # Connect toggle button to show/hide functionality
    def toggle_results():
        is_hidden = results_toggle_button.isChecked()
        if is_hidden:
            results_content.hide()
            results_toggle_button.setText("Show")
            # Store current splitter sizes and minimize results section
            current_sizes = main_splitter.sizes()
            if not hasattr(results_section, '_stored_size'):
                results_section._stored_size = current_sizes[1]
            # Set results section to just header height
            header_height = results_header.sizeHint().height()
            main_splitter.setSizes([current_sizes[0], header_height + 10])
        else:
            results_content.show()
            results_toggle_button.setText("Hide")
            # Restore previous size
            current_sizes = main_splitter.sizes()
            restored_size = getattr(results_section, '_stored_size', 300)
            main_splitter.setSizes([current_sizes[0], restored_size])
    
    results_toggle_button.clicked.connect(toggle_results)
    
    # Ensure results_content is initially visible
    results_content.setVisible(True)
    
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
        'stop_button': stop_button,
        'os_detection_check': os_detection_check,
        'port_scan_check': port_scan_check,
        'status_label': status_label,
        'progress_bar': progress_bar,
        'results_text': results_text,
        'results_toggle_button': results_toggle_button,
        'main_splitter': main_splitter,
        'results_content': results_content,
        'results_section': results_section
    }
    
    return ui_components

def create_dock_widget(main_widget, name="Network Scanner"):
    """Create a dock widget containing the main widget"""
    dock = QDockWidget(name)
    dock.setWidget(main_widget)
    dock.setObjectName("NetworkScannerDock")
    dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
    
    # Set minimum width to prevent controls from being too cramped but more compact
    main_widget.setMinimumWidth(280)
    
    return dock

def create_scan_type_manager_dialog(parent, settings, plugin=None):
    """Create the scan type manager dialog"""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Scan Type Manager")
    dialog.setMinimumWidth(700)
    dialog.setMinimumHeight(400)
    
    layout = QVBoxLayout(dialog)
    layout.setSpacing(12)
    
    # Add description
    description_label = QLabel(
        "Manage your scan profiles. You can create new profiles, edit existing ones, or delete custom profiles. "
        "Changes are automatically saved and will update all scan type dropdowns."
    )
    description_label.setWordWrap(True)
    description_label.setStyleSheet("padding: 8px; background-color: #f0f0f0; border-radius: 4px;")
    layout.addWidget(description_label)
    
    # Create a table to display profiles
    profile_table = QTableWidget()
    profile_table.setColumnCount(6)
    profile_table.setHorizontalHeaderLabels(["Name", "Description", "Arguments", "OS Detection", "Port Scan", "Timeout"])
    profile_table.horizontalHeader().setStretchLastSection(True)
    profile_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
    profile_table.setSelectionBehavior(QTableWidget.SelectRows)
    profile_table.setSelectionMode(QTableWidget.SingleSelection)
    layout.addWidget(profile_table)
    
    # Use the passed plugin instance, or try to find it as fallback
    if plugin is None:
        if hasattr(parent, 'plugin'):
            plugin = parent.plugin
        else:
            # Try to find the plugin through the parent's children or other means
            # This is a fallback - ideally the plugin should be passed directly
            for child in parent.findChildren(object):
                if hasattr(child, 'add_scan_profile'):
                    plugin = child
                    break
    
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
            
            # Timeout column
            timeout_item = QTableWidgetItem(str(profile.get("timeout", 300)))
            timeout_item.setTextAlignment(Qt.AlignCenter)
            profile_table.setItem(i, 5, timeout_item)
            
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
    duplicate_button = QPushButton("Duplicate Profile")
    # Initially disable edit/delete until a row is selected
    edit_button.setEnabled(False)
    delete_button.setEnabled(False)
    duplicate_button.setEnabled(False)
    
    button_layout.addWidget(new_button)
    button_layout.addWidget(edit_button)
    button_layout.addWidget(duplicate_button)
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
            duplicate_button.setEnabled(True)
        else:
            edit_button.setEnabled(False)
            delete_button.setEnabled(False)
            duplicate_button.setEnabled(False)
    
    profile_table.itemSelectionChanged.connect(on_selection_changed)
    
    # Create the profile edit dialog function
    def edit_profile_dialog(profile_id=None, is_new=False, duplicate_from=None):
        edit_dialog = QDialog(dialog)
        if is_new:
            edit_dialog.setWindowTitle("New Scan Profile")
        elif duplicate_from:
            edit_dialog.setWindowTitle(f"Duplicate Profile: {duplicate_from}")
        else:
            edit_dialog.setWindowTitle("Edit Scan Profile")
        edit_dialog.setMinimumWidth(450)
        
        edit_layout = QVBoxLayout(edit_dialog)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Profile ID (for new profiles only)
        profile_id_edit = QLineEdit()
        if is_new or duplicate_from:
            form_layout.addRow("Profile ID:", profile_id_edit)
            profile_id_edit.setPlaceholderText("e.g., custom_scan (no spaces, lowercase)")
            if duplicate_from:
                profile_id_edit.setText(f"{duplicate_from}_copy")
        
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
        profile_timeout_edit.setValidator(QIntValidator(30, 3600))
        form_layout.addRow("Timeout (seconds):", profile_timeout_edit)
        profile_timeout_edit.setPlaceholderText("300")
        
        # If editing or duplicating, populate with existing values
        if not is_new and profile_id:
            profile = settings["scan_profiles"]["value"].get(profile_id, {})
            profile_name_edit.setText(profile.get("name", ""))
            profile_desc_edit.setText(profile.get("description", ""))
            profile_args_edit.setText(profile.get("arguments", ""))
            profile_os_check.setChecked(profile.get("os_detection", False))
            profile_port_check.setChecked(profile.get("port_scan", False))
            profile_timeout_edit.setText(str(profile.get("timeout", 300)))
        elif duplicate_from:
            # Populate with values from the profile being duplicated
            source_profile = settings["scan_profiles"]["value"].get(duplicate_from, {})
            profile_name_edit.setText(f"{source_profile.get('name', '')} (Copy)")
            profile_desc_edit.setText(source_profile.get("description", ""))
            profile_args_edit.setText(source_profile.get("arguments", ""))
            profile_os_check.setChecked(source_profile.get("os_detection", False))
            profile_port_check.setChecked(source_profile.get("port_scan", False))
            profile_timeout_edit.setText(str(source_profile.get("timeout", 300)))
        
        edit_layout.addLayout(form_layout)
        
        # Add dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(edit_dialog.accept)
        button_box.rejected.connect(edit_dialog.reject)
        edit_layout.addWidget(button_box)
        
        # Show dialog and handle result
        if edit_dialog.exec() == QDialog.Accepted:
            # Get values from form
            if is_new or duplicate_from:
                new_id = profile_id_edit.text().strip().lower().replace(" ", "_")
                if not new_id:
                    QMessageBox.warning(dialog, "Invalid ID", "Profile ID cannot be empty.")
                    return False
                
                # Check if ID exists
                if new_id in settings["scan_profiles"]["value"]:
                    QMessageBox.warning(dialog, "Profile Exists", f"A profile with ID '{new_id}' already exists.")
                    return False
                
                profile_id = new_id
            
            # Validate required fields
            if not profile_name_edit.text().strip():
                QMessageBox.warning(dialog, "Invalid Name", "Profile name cannot be empty.")
                return False
                
            if not profile_args_edit.text().strip():
                QMessageBox.warning(dialog, "Invalid Arguments", "Profile arguments cannot be empty.")
                return False
            
            # Create updated profile
            updated_profile = {
                "name": profile_name_edit.text().strip(),
                "description": profile_desc_edit.text().strip(),
                "arguments": profile_args_edit.text().strip(),
                "os_detection": profile_os_check.isChecked(),
                "port_scan": profile_port_check.isChecked(),
                "timeout": int(profile_timeout_edit.text() or "300")
            }
            
            # Use plugin methods if available, otherwise update settings directly
            success = False
            if plugin and hasattr(plugin, 'add_scan_profile') and (is_new or duplicate_from):
                success = plugin.add_scan_profile(profile_id, updated_profile)
            elif plugin and hasattr(plugin, 'update_scan_profile') and not is_new:
                success = plugin.update_scan_profile(profile_id, updated_profile)
            else:
                # Fallback to direct settings update
                profiles = settings["scan_profiles"]["value"].copy()
                profiles[profile_id] = updated_profile
                settings["scan_profiles"]["value"] = profiles
                success = True
            
            if success:
                # Refresh the table
                refresh_table()
                QMessageBox.information(dialog, "Success", f"Profile '{profile_id}' saved successfully.")
                return True
            else:
                QMessageBox.warning(dialog, "Error", f"Failed to save profile '{profile_id}'.")
                return False
        
        return False
    
    # Connect button handlers
    new_button.clicked.connect(lambda: edit_profile_dialog(is_new=True))
    edit_button.clicked.connect(lambda: 
        edit_profile_dialog(
            profile_table.item(profile_table.selectedIndexes()[0].row(), 0).data(Qt.UserRole)
        ) if profile_table.selectedIndexes() else None
    )
    
    duplicate_button.clicked.connect(lambda:
        edit_profile_dialog(
            duplicate_from=profile_table.item(profile_table.selectedIndexes()[0].row(), 0).data(Qt.UserRole)
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
        profile_name = profile_table.item(row, 0).text()
        result = QMessageBox.question(
            dialog, 
            "Confirm Deletion",
            f"Are you sure you want to delete the profile '{profile_name}' ({profile_id})?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            # Use plugin method if available, otherwise update settings directly
            success = False
            if plugin and hasattr(plugin, 'delete_scan_profile'):
                success = plugin.delete_scan_profile(profile_id)
            else:
                # Fallback to direct settings update
                profiles = settings["scan_profiles"]["value"].copy()
                if profile_id in profiles:
                    del profiles[profile_id]
                    settings["scan_profiles"]["value"] = profiles
                    success = True
            
            if success:
                refresh_table()
                QMessageBox.information(dialog, "Success", f"Profile '{profile_name}' deleted successfully.")
            else:
                QMessageBox.warning(dialog, "Error", f"Failed to delete profile '{profile_name}'.")
    
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