#!/usr/bin/env python3
# NetSCAN - Device Table Component

import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMenu, QAbstractItemView, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon
import json
import datetime
import uuid

class DeviceTable(QTableWidget):
    """Table for displaying discovered network devices."""
    
    device_selected = Signal(object)  # Changed to emit list of devices or single device
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.devices = []  # List to store device data
        self.device_groups = {}  # Dictionary to store device groups {group_name: [device_id1, device_id2, ...]}
        self.custom_columns = []  # List to store custom column names
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        # Configure table properties
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # Enable multi-selection
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)  # Enable alternating row colors for better readability
        self.setShowGrid(True)  # Show grid lines
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Set up the columns
        self.setup_columns()
        
        # Set table style
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e8f0;
                background-color: white;
                border: 1px solid #aabbcc;
                border-radius: 3px;
                selection-background-color: #e8f0ff;
                selection-color: #2c5aa0;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f4f8;
            }
            QTableWidget::item:selected {
                background-color: #e8f0ff;
                color: #2c5aa0;
            }
            QTableWidget::item:hover:!selected {
                background-color: #f5f9ff;
            }
            QTableWidget:focus {
                border: 1px solid #2c5aa0;
            }
            QTableWidget:alternate-background-color {
                background-color: #f8fbff;
            }
        """)
        
        # Add context menu to header for column customization
        header = self.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_context_menu)
    
    def setup_columns(self):
        """Setup the table columns according to configuration."""
        # Get column configuration
        config_columns = self.main_window.config["ui"]["table"]["columns"]
        
        # Store custom columns for later use
        self.custom_columns = [col for col in config_columns if col not in [
            "ip", "hostname", "mac", "vendor", "ports", "last_seen", 
            "first_seen", "status", "scan_method", "alias"
        ]]
        
        # Set column count and headers
        self.setColumnCount(len(config_columns))
        self.setHorizontalHeaderLabels(config_columns)
        
        # Configure column properties for better resizing
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # Make all columns resizable by user
        
        # Set default widths for common columns
        column_widths = {
            "ip": 120,
            "hostname": 180,
            "mac": 140,
            "vendor": 150,
            "ports": 200,
            "last_seen": 150,
            "first_seen": 150,
            "status": 80,
            "scan_method": 100,
            "alias": 120
        }
        
        # Apply default widths where defined and identify columns that should stretch
        stretch_columns = []
        for i, column in enumerate(config_columns):
            if column in column_widths:
                self.setColumnWidth(i, column_widths[column])
            
            # Mark certain columns for stretching
            if column in ["hostname", "vendor", "ports", "notes"]:
                stretch_columns.append(i)
        
        # Make vertical header (row numbers) visible but compact
        v_header = self.verticalHeader()
        v_header.setDefaultSectionSize(30)  # Compact row height
        v_header.setVisible(True)
        
        # Enable sorting by clicking headers
        self.setSortingEnabled(True)
        
        # Apply stretch mode to columns that should expand
        for col_index in stretch_columns:
            if col_index < self.columnCount():
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
        
        # Set stretch last section to true to fill available space
        header.setStretchLastSection(True)
        
        # Set header style
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f4f8;
                color: #2c5aa0;
                padding: 6px;
                border: none;
                border-right: 1px solid #d0dbe8;
                border-bottom: 1px solid #d0dbe8;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background-color: #e8f0ff;
            }
            QHeaderView::section:pressed {
                background-color: #d0e0ff;
            }
        """)
        
        # Set vertical header style
        v_header.setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f4f8;
                color: #606060;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #d0dbe8;
                border-right: 1px solid #d0dbe8;
            }
        """)
        
        # Sort by IP by default
        self.sort_by_column("ip", "ascending")
    
    def add_device(self, device):
        """Add a device to the table."""
        try:
            # Validate device has required fields before adding
            if not device or not device.get('ip'):
                self.main_window.statusBar.showMessage("Cannot add device with missing IP address", 5000)
                return
                
            # Check if device already exists
            existing_row = self.find_device_row(device['ip'])
            if existing_row is not None:
                # Update existing device
                self.update_device_row(existing_row, device)
                return

            # Generate a unique ID if none exists
            if 'id' not in device:
                device['id'] = str(uuid.uuid4())

            # Add new device
            row_position = self.rowCount()
            self.insertRow(row_position)

            # Get column configuration
            config_columns = self.main_window.config["ui"]["table"]["columns"]

            # Fill in the data
            for col, column_name in enumerate(config_columns):
                item = QTableWidgetItem()
                
                if column_name == 'ip':
                    item.setText(device.get('ip', 'N/A'))
                elif column_name == 'hostname':
                    item.setText(device.get('hostname', 'Unknown'))
                elif column_name == 'mac':
                    item.setText(device.get('mac', 'N/A'))
                elif column_name == 'vendor':
                    item.setText(device.get('vendor', 'Unknown'))
                elif column_name == 'scan_method':
                    item.setText(device.get('scan_method', 'Unknown'))
                elif column_name == 'ports':
                    ports = []
                    if 'open_ports' in device:
                        for port in device['open_ports']:
                            if isinstance(port, dict):
                                ports.append(f"{port['port']}/{port['service']}")
                            else:
                                ports.append(str(port))
                    if 'udp_ports' in device:
                        for port in device['udp_ports']:
                            if isinstance(port, dict):
                                ports.append(f"{port['port']}/udp/{port['service']}")
                            else:
                                ports.append(f"{port}/udp")
                    item.setText(', '.join(ports) if ports else 'None')
                elif column_name == 'last_seen':
                    item.setText(device.get('last_seen', 'N/A'))
                elif column_name == 'first_seen':
                    item.setText(device.get('first_seen', 'N/A'))
                elif column_name == 'status':
                    item.setText(device.get('status', 'Unknown'))
                elif column_name == 'alias':
                    # Display alias directly from device or from metadata
                    alias = device.get('alias', '')
                    if not alias and 'metadata' in device and 'alias' in device['metadata']:
                        alias = device['metadata']['alias']
                    item.setText(alias)
                else:
                    # Try to get value from metadata
                    if 'metadata' in device and column_name in device['metadata']:
                        item.setText(str(device['metadata'][column_name]))
                    else:
                        item.setText('N/A')

                self.setItem(row_position, col, item)

            # Store the full device data
            self.devices.append(device)

        except Exception as e:
            self.main_window.statusBar.showMessage(f"Error adding device: {str(e)}")

    def update_device_row(self, row, device):
        """Update an existing device row with new data."""
        try:
            config_columns = self.main_window.config["ui"]["table"]["columns"]
            
            for col, column_name in enumerate(config_columns):
                item = self.item(row, col)
                if not item:
                    item = QTableWidgetItem()
                    self.setItem(row, col, item)
                
                if column_name == 'ip':
                    item.setText(device.get('ip', 'N/A'))
                elif column_name == 'hostname':
                    item.setText(device.get('hostname', 'Unknown'))
                elif column_name == 'mac':
                    item.setText(device.get('mac', 'N/A'))
                elif column_name == 'vendor':
                    item.setText(device.get('vendor', 'Unknown'))
                elif column_name == 'scan_method':
                    item.setText(device.get('scan_method', 'Unknown'))
                elif column_name == 'ports':
                    ports = []
                    if 'open_ports' in device:
                        for port in device['open_ports']:
                            if isinstance(port, dict):
                                ports.append(f"{port['port']}/{port['service']}")
                            else:
                                ports.append(str(port))
                    if 'udp_ports' in device:
                        for port in device['udp_ports']:
                            if isinstance(port, dict):
                                ports.append(f"{port['port']}/udp/{port['service']}")
                            else:
                                ports.append(f"{port}/udp")
                    item.setText(', '.join(ports) if ports else 'None')
                elif column_name == 'last_seen':
                    item.setText(device.get('last_seen', 'N/A'))
                elif column_name == 'first_seen':
                    item.setText(device.get('first_seen', 'N/A'))
                elif column_name == 'status':
                    item.setText(device.get('status', 'Unknown'))
                elif column_name == 'alias':
                    # Display alias directly from device or from metadata
                    alias = device.get('alias', '')
                    if not alias and 'metadata' in device and 'alias' in device['metadata']:
                        alias = device['metadata']['alias']
                    item.setText(alias)
                else:
                    # Try to get value from metadata
                    if 'metadata' in device and column_name in device['metadata']:
                        item.setText(str(device['metadata'][column_name]))
                    else:
                        item.setText('N/A')
            
            # Update the stored device data
            for i, stored_device in enumerate(self.devices):
                if stored_device['ip'] == device['ip']:
                    self.devices[i] = device
                    break

        except Exception as e:
            self.main_window.statusBar.showMessage(f"Error updating device: {str(e)}")

    def find_device_row(self, ip):
        """Find the row number for a device by IP address."""
        for row in range(self.rowCount()):
            if self.item(row, 0) and self.item(row, 0).text() == ip:
                return row
        return None

    def update_data(self, devices):
        """Update the table with new device data."""
        # Store the device data
        self.devices = devices
        
        # Clear existing data
        self.setRowCount(0)
        
        # Add devices to the table
        for device in devices:
            self.add_device(device)
        
        # Apply sorting
        sort_column = self.main_window.config["ui"]["table"]["sort_by"]
        sort_direction = self.main_window.config["ui"]["table"]["sort_direction"]
        self.sort_by_column(sort_column, sort_direction)
    
    def sort_by_column(self, column_name, direction="ascending"):
        """Sort the table by the specified column."""
        # Find the column index
        config_columns = self.main_window.config["ui"]["table"]["columns"]
        if column_name in config_columns:
            column_index = config_columns.index(column_name)
            
            # Set sort order
            if direction.lower() == "ascending":
                order = Qt.SortOrder.AscendingOrder
            else:
                order = Qt.SortOrder.DescendingOrder
            
            # Sort the table
            self.sortItems(column_index, order)
            
            # Update configuration
            self.main_window.config["ui"]["table"]["sort_by"] = column_name
            self.main_window.config["ui"]["table"]["sort_direction"] = direction.lower()
    
    def show_context_menu(self, position):
        """Show context menu for table items."""
        menu = QMenu(self)
        
        # Check if device(s) are selected
        selected_devices = self.get_selected_devices()
        
        # Add Device Manually is always available
        add_action = QAction("Add Device Manually", self)
        add_action.triggered.connect(self.add_device_manually)
        menu.addAction(add_action)
        
        # Add Group Management action
        manage_groups_action = QAction("Manage Device Groups...", self)
        manage_groups_action.triggered.connect(self.manage_device_groups)
        menu.addAction(manage_groups_action)
        
        if selected_devices:
            # Add separator before device-specific actions
            menu.addSeparator()
            
            # Add group submenu if devices are selected
            if selected_devices:
                groups_menu = QMenu("Add to Group", menu)
                
                # Add existing groups
                for group_name in self.device_groups.keys():
                    group_action = QAction(group_name, self)
                    # Use lambda with default argument to avoid late binding
                    group_action.triggered.connect(
                        lambda checked=False, g=group_name: self.add_selected_devices_to_group(g)
                    )
                    groups_menu.addAction(group_action)
                
                # Add separator and "New Group" option if there are any groups
                if self.device_groups:
                    groups_menu.addSeparator()
                
                # New Group action
                new_group_action = QAction("New Group...", self)
                new_group_action.triggered.connect(self.add_selected_devices_to_new_group)
                groups_menu.addAction(new_group_action)
                
                menu.addMenu(groups_menu)
                
            # Add edit action
            if len(selected_devices) == 1:
                edit_action = QAction("Edit Device Properties", self)
                edit_action.triggered.connect(lambda: self.edit_device_properties(selected_devices[0]))
                menu.addAction(edit_action)
            
            # Add remove action
            remove_action = QAction("Remove Selected Device(s)", self)
            remove_action.triggered.connect(lambda: self.remove_selected_devices())
            menu.addAction(remove_action)
            
            # Get plugin menu items
            try:
                # Handle single device plugin actions
                if len(selected_devices) == 1:
                    plugin_items = self.main_window.plugin_manager.get_plugin_menu_items(selected_devices[0])
                    if plugin_items:
                        # Add separator before plugin menus
                        menu.addSeparator()
                        
                        # Store parent menus
                        plugin_menus = {}
                        
                        # Add plugin menu items
                        for item in plugin_items:
                            # Check if the action should be enabled
                            enabled = True
                            if 'enabled_callback' in item:
                                try:
                                    enabled = item['enabled_callback'](selected_devices[0])
                                except Exception as e:
                                    self.main_window.bottom_panel.add_log_entry(f"Error checking menu item enabled state: {str(e)}", level="ERROR")
                                    enabled = False
                            
                            if enabled:
                                action = QAction(item['label'], self)
                                if item.get('icon_path'):
                                    action.setIcon(QIcon(item['icon_path']))
                                if item.get('shortcut'):
                                    action.setShortcut(item['shortcut'])
                                
                                # Connect the action to the callback
                                action.triggered.connect(lambda checked, cb=item['callback']: cb(selected_devices[0]))
                                
                                # Add to parent menu if specified, otherwise add to main menu
                                if item.get('parent_menu'):
                                    if item['parent_menu'] not in plugin_menus:
                                        plugin_menus[item['parent_menu']] = QMenu(item['parent_menu'], menu)
                                        menu.addMenu(plugin_menus[item['parent_menu']])
                                    plugin_menus[item['parent_menu']].addAction(action)
                                else:
                                    menu.addAction(action)
                
                # Add multi-device plugin actions for multiple selection
                if len(selected_devices) > 1:
                    # Get plugins that support multi-device operations
                    multi_device_items = self.main_window.plugin_manager.get_multi_device_menu_items(selected_devices)
                    
                    if multi_device_items:
                        # Add separator before plugin menus if not already added
                        if len(selected_devices) == 1 and not plugin_items:
                            menu.addSeparator()
                            
                        # Store parent menus
                        plugin_menus = {}
                        
                        # Add plugin menu items for multi-device operations
                        for item in multi_device_items:
                            action = QAction(item['label'], self)
                            if item.get('icon_path'):
                                action.setIcon(QIcon(item['icon_path']))
                                
                            # Connect the action to the callback with all selected devices
                            action.triggered.connect(lambda checked, cb=item['callback']: cb(selected_devices))
                            
                            # Add to parent menu if specified, otherwise add to main menu
                            if item.get('parent_menu'):
                                if item['parent_menu'] not in plugin_menus:
                                    plugin_menus[item['parent_menu']] = QMenu(item['parent_menu'], menu)
                                    menu.addMenu(plugin_menus[item['parent_menu']])
                                plugin_menus[item['parent_menu']].addAction(action)
                            else:
                                menu.addAction(action)
                    
            except Exception as e:
                self.main_window.bottom_panel.add_log_entry(f"Error getting plugin menu items: {str(e)}", level="ERROR")
        
        # Show the menu
        menu.exec(self.mapToGlobal(position))

    def show_header_context_menu(self, position):
        """Show context menu for table header to customize columns."""
        menu = QMenu(self)
        
        # Add customize columns action
        customize_action = QAction("Customize Columns...", self)
        customize_action.triggered.connect(self.main_window.customize_table_columns)
        menu.addAction(customize_action)
        
        # Show the menu
        menu.exec(self.horizontalHeader().viewport().mapToGlobal(position))
    
    def on_selection_changed(self):
        """Handle selection changes in the table."""
        selected_devices = self.get_selected_devices()  # Get multiple devices
        
        # Add debugging
        if hasattr(self.main_window, 'bottom_panel'):
            device_count = len(selected_devices)
            self.main_window.bottom_panel.add_log_entry(
                f"Device selection changed: {device_count} device(s) selected", 
                level="DEBUG"
            )
            if device_count == 1:
                self.main_window.bottom_panel.add_log_entry(
                    f"Selected device: {selected_devices[0].get('ip', 'Unknown')}, ID: {selected_devices[0].get('id', 'Unknown')}", 
                    level="DEBUG"
                )
            elif device_count > 1:
                device_ips = [d.get('ip', 'Unknown') for d in selected_devices]
                self.main_window.bottom_panel.add_log_entry(
                    f"Selected devices: {', '.join(device_ips)}", 
                    level="DEBUG"
                )
        
        # Emit the signal with selected device data (either list or single device for backward compatibility)
        if len(selected_devices) == 1:
            self.device_selected.emit(selected_devices[0])  # Single device for backward compatibility
            if hasattr(self.main_window, 'bottom_panel'):
                self.main_window.bottom_panel.add_log_entry(
                    "Emitting single device selection signal", 
                    level="DEBUG"
                )
        else:
            self.device_selected.emit(selected_devices)  # List of devices
            if hasattr(self.main_window, 'bottom_panel'):
                self.main_window.bottom_panel.add_log_entry(
                    f"Emitting multiple device selection signal with {len(selected_devices)} devices", 
                    level="DEBUG"
                )
        
        # Update the bottom panel's device details tab with first selected device for compatibility
        if self.main_window and hasattr(self.main_window, 'bottom_panel'):
            if selected_devices:
                self.main_window.bottom_panel.update_device_details(selected_devices[0])
            else:
                self.main_window.bottom_panel.update_device_details(None)
    
    def get_selected_devices(self):
        """Get all currently selected device data.
        
        Returns:
            List[Dict]: List of selected device dictionaries
        """
        selected_devices = []
        
        # Get all selected rows
        selected_items = self.selectedItems()
        selected_rows = set()
        
        for item in selected_items:
            selected_rows.add(item.row())
        
        # Get device data for each selected row
        for row in selected_rows:
            # Get the IP address from the first column
            try:
                ip = self.item(row, 0).text()
                
                # Find the device in our stored devices list
                for device in self.devices:
                    if device.get('ip') == ip:
                        selected_devices.append(device)
                        break
            except (AttributeError, IndexError):
                # Skip rows with missing data
                continue
        
        return selected_devices
    
    def get_selected_device(self):
        """Get the currently selected device data (for backward compatibility).
        
        Returns:
            Dict or None: The first selected device dictionary or None
        """
        selected_devices = self.get_selected_devices()
        return selected_devices[0] if selected_devices else None

    def get_all_devices(self):
        """Get all devices from the table.
        
        Returns:
            list: List of device dictionaries
        """
        devices = []
        for row in range(self.rowCount()):
            device = {}
            
            # Extract data from each column
            device['ip'] = self.item(row, self.get_column_index('ip')).text() if self.item(row, self.get_column_index('ip')) else ''
            device['mac'] = self.item(row, self.get_column_index('mac')).text() if self.item(row, self.get_column_index('mac')) else ''
            device['hostname'] = self.item(row, self.get_column_index('hostname')).text() if self.item(row, self.get_column_index('hostname')) else ''
            
            # Get vendor if that column exists
            vendor_col = self.get_column_index('vendor')
            if vendor_col >= 0 and self.item(row, vendor_col):
                device['vendor'] = self.item(row, vendor_col).text()
            
            # Get OS if that column exists
            os_col = self.get_column_index('os')
            if os_col >= 0 and self.item(row, os_col):
                device['os'] = self.item(row, os_col).text()
            
            # Add item data for any custom columns or metadata
            for custom_col in self.custom_columns:
                col_index = self.get_column_index(custom_col)
                if col_index >= 0 and self.item(row, col_index):
                    if 'metadata' not in device:
                        device['metadata'] = {}
                    device['metadata'][custom_col] = self.item(row, col_index).text()
            
            # Unique ID for the device
            device['id'] = self.item(row, 0).data(Qt.UserRole) if self.item(row, 0) else str(uuid.uuid4())
            
            # Include device groups if available
            if hasattr(self, 'device_groups'):
                for group_name, group_devices in self.device_groups.items():
                    if device['id'] in group_devices:
                        if 'groups' not in device:
                            device['groups'] = []
                        device['groups'].append(group_name)
            
            devices.append(device)
        
        return devices

    def remove_device(self):
        """Remove the selected device from the table and workspace."""
        selected_device = self.get_selected_device()
        if not selected_device:
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Remove Device",
            f"Are you sure you want to remove {selected_device.get('hostname', 'Unknown')} ({selected_device.get('ip', 'N/A')})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from workspace using the core-workspace plugin
            try:
                if hasattr(self.main_window, 'plugin_manager'):
                    workspace_plugin_api = self.main_window.plugin_manager.plugin_apis.get("core-workspace")
                    if workspace_plugin_api:
                        workspace_plugin_api.call_function("remove_device", selected_device['id'])
            except Exception as e:
                logging.error(f"Error removing device from workspace: {str(e)}")
            
            # Remove from table
            current_row = self.currentRow()
            if current_row >= 0:
                self.removeRow(current_row)
                
                # Remove from devices list
                for i, device in enumerate(self.devices):
                    if device['id'] == selected_device['id']:
                        self.devices.pop(i)
                        break

    def add_device_manually(self):
        """Show a dialog to add a device manually."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
            QPushButton, QDialogButtonBox, QComboBox, QLabel,
            QHBoxLayout, QGroupBox, QScrollArea, QWidget,
            QTableWidget, QTableWidgetItem, QHeaderView
        )
        
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Device Manually")
            dialog.setMinimumWidth(550)
            dialog.setMinimumHeight(500)
            
            # Main layout with scroll area
            main_layout = QVBoxLayout(dialog)
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            
            # Create standard fields group
            standard_group = QGroupBox("Device Information")
            form_layout = QFormLayout(standard_group)
            
            # Required Fields
            ip_input = QLineEdit()
            ip_input.setPlaceholderText("Required: 192.168.1.1")
            form_layout.addRow("IP Address:", ip_input)
            
            # Optional Fields
            hostname_input = QLineEdit()
            hostname_input.setPlaceholderText("Optional: device-name")
            form_layout.addRow("Hostname:", hostname_input)
            
            mac_input = QLineEdit()
            mac_input.setPlaceholderText("Optional: 00:11:22:33:44:55")
            form_layout.addRow("MAC Address:", mac_input)
            
            status_combo = QComboBox()
            status_combo.addItems(["active", "inactive", "unknown"])
            status_combo.setCurrentText("active")
            form_layout.addRow("Status:", status_combo)
            
            alias_input = QLineEdit()
            alias_input.setPlaceholderText("Optional: Friendly Name")
            form_layout.addRow("Alias:", alias_input)
            
            # Create metadata group
            metadata_group = QGroupBox("Additional Details")
            metadata_layout = QFormLayout(metadata_group)
            
            os_input = QLineEdit()
            os_input.setPlaceholderText("Windows 10, Linux, etc.")
            metadata_layout.addRow("OS:", os_input)
            
            notes_input = QLineEdit()
            notes_input.setPlaceholderText("Any notes about this device")
            metadata_layout.addRow("Notes:", notes_input)
            
            # Custom fields group
            custom_fields_group = QGroupBox("Custom Fields")
            custom_layout = QVBoxLayout(custom_fields_group)
            
            # Table for custom fields
            custom_fields_table = QTableWidget(0, 3)  # Name, Value, Delete button
            custom_fields_table.setHorizontalHeaderLabels(["Field Name", "Value", "Delete"])
            custom_fields_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            custom_fields_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            custom_fields_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            
            # Function to add delete button to a row
            def add_delete_button(row):
                delete_button = QPushButton("✕")
                delete_button.setFixedWidth(30)
                delete_button.clicked.connect(lambda: custom_fields_table.removeRow(row))
                
                # Update row numbers for all delete buttons when a row is removed
                delete_button.clicked.connect(lambda: update_delete_buttons())
                
                custom_fields_table.setCellWidget(row, 2, delete_button)
            
            # Function to update row numbers for all delete buttons
            def update_delete_buttons():
                for r in range(custom_fields_table.rowCount()):
                    if custom_fields_table.cellWidget(r, 2):
                        custom_fields_table.removeCellWidget(r, 2)
                        add_delete_button(r)
            
            custom_layout.addWidget(custom_fields_table)
            
            # Add button for custom fields
            add_field_button = QPushButton("Add Custom Field")
            def add_custom_field():
                row = custom_fields_table.rowCount()
                custom_fields_table.insertRow(row)
                custom_fields_table.setItem(row, 0, QTableWidgetItem(""))
                custom_fields_table.setItem(row, 1, QTableWidgetItem(""))
                add_delete_button(row)
            add_field_button.clicked.connect(add_custom_field)
            custom_layout.addWidget(add_field_button)
            
            # Add form and groups to scroll layout
            scroll_layout.addWidget(standard_group)
            scroll_layout.addWidget(metadata_group)
            scroll_layout.addWidget(custom_fields_group)
            
            # Finish scroll area setup
            scroll_area.setWidget(scroll_widget)
            main_layout.addWidget(scroll_area)
            
            # Add button box
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            main_layout.addWidget(button_box)
            
            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Validate IP (required)
                ip = ip_input.text().strip()
                if not ip:
                    self.main_window.statusBar.showMessage("IP address is required", 5000)
                    return
                
                # Create device data
                device_data = {
                    'ip': ip,
                    'hostname': hostname_input.text().strip(),
                    'mac': mac_input.text().strip(),
                    'status': status_combo.currentText(),
                    'alias': alias_input.text().strip(),
                    'metadata': {
                        'os': os_input.text().strip(),
                        'notes': notes_input.text().strip(),
                        'added_manually': True,
                        'added_on': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
                
                # Add custom fields
                for row in range(custom_fields_table.rowCount()):
                    field_name = custom_fields_table.item(row, 0).text().strip()
                    field_value = custom_fields_table.item(row, 1).text().strip()
                    if field_name:  # Only add non-empty field names
                        device_data['metadata'][field_name] = field_value
                
                # Check if device already exists
                existing_row = self.find_device_row(ip)
                if existing_row is not None:
                    # Update instead of add
                    self.update_device_row(existing_row, device_data)
                    self.main_window.statusBar.showMessage(f"Updated existing device: {ip}", 5000)
                else:
                    # Add new device
                    self.add_device(device_data)
                    self.main_window.statusBar.showMessage(f"Added device: {ip}", 5000)
                
                # Update workspace if available
                try:
                    if hasattr(self.main_window, 'plugin_manager'):
                        workspace_plugin_api = self.main_window.plugin_manager.plugin_apis.get("core-workspace")
                        if workspace_plugin_api:
                            workspace_plugin_api.call_function("add_device", device_data)
                except Exception as e:
                    logging.error(f"Error adding device to workspace: {str(e)}")
                
                # Log the activity
                if hasattr(self.main_window, 'bottom_panel'):
                    self.main_window.bottom_panel.add_log_entry(f"Added device manually: {ip}", level="INFO")
                
        except Exception as e:
            self.main_window.statusBar.showMessage(f"Error adding device: {str(e)}")
            if hasattr(self.main_window, 'bottom_panel'):
                self.main_window.bottom_panel.add_log_entry(f"Error adding device: {str(e)}", level="ERROR")

    def edit_device_properties(self, device):
        """Show a dialog to edit device properties."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
            QPushButton, QDialogButtonBox, QComboBox, QLabel,
            QHBoxLayout, QGroupBox, QScrollArea, QWidget,
            QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
            QCheckBox, QMessageBox
        )
        from PySide6.QtCore import Qt
        
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Device: {device.get('ip', 'Unknown')}")
            dialog.setMinimumWidth(550)
            dialog.setMinimumHeight(550)
            
            # Main layout with scroll area
            main_layout = QVBoxLayout(dialog)
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            
            # Create standard fields group
            standard_group = QGroupBox("Standard Fields")
            form_layout = QFormLayout(standard_group)
            
            # Create IP input (read-only since it's the primary identifier)
            ip_input = QLineEdit()
            ip_input.setText(device.get('ip', ''))
            ip_input.setReadOnly(True)  # IP address can't be changed
            form_layout.addRow("IP Address:", ip_input)
            
            # Create hostname input
            hostname_input = QLineEdit()
            hostname_input.setText(device.get('hostname', ''))
            hostname_input.setPlaceholderText("device-name")
            form_layout.addRow("Hostname:", hostname_input)
            
            # Create MAC input
            mac_input = QLineEdit()
            mac_input.setText(device.get('mac', ''))
            mac_input.setPlaceholderText("00:11:22:33:44:55")
            form_layout.addRow("MAC Address:", mac_input)
            
            # Create status dropdown
            status_combo = QComboBox()
            status_combo.addItems(["active", "inactive", "unknown"])
            current_status = device.get('status', 'unknown')
            status_index = status_combo.findText(current_status)
            if status_index >= 0:
                status_combo.setCurrentIndex(status_index)
            form_layout.addRow("Status:", status_combo)
            
            # Create alias input
            alias_input = QLineEdit()
            alias_input.setText(device.get('alias', ''))
            alias_input.setPlaceholderText("Friendly Name")
            form_layout.addRow("Alias:", alias_input)
            
            # Get existing metadata
            metadata = device.get('metadata', {})
            
            # Create metadata group
            metadata_group = QGroupBox("Additional Details")
            metadata_layout = QFormLayout(metadata_group)
            
            # OS input
            os_input = QLineEdit()
            os_input.setText(metadata.get('os', ''))
            os_input.setPlaceholderText("Windows 10, Linux, etc.")
            metadata_layout.addRow("OS:", os_input)
            
            # Notes input
            notes_input = QLineEdit()
            notes_input.setText(metadata.get('notes', ''))
            notes_input.setPlaceholderText("Any notes about this device")
            metadata_layout.addRow("Notes:", notes_input)
            
            # Custom fields group
            custom_fields_group = QGroupBox("Custom Fields")
            custom_layout = QVBoxLayout(custom_fields_group)
            
            # Table for custom fields
            custom_fields_table = QTableWidget(0, 3)  # Name, Value, Delete column
            custom_fields_table.setHorizontalHeaderLabels(["Field Name", "Value", "Delete"])
            custom_fields_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            custom_fields_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            custom_fields_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            
            # Function to add delete button to a row
            def add_delete_button(row):
                delete_button = QPushButton("✕")
                delete_button.setFixedWidth(30)
                delete_button.clicked.connect(lambda: custom_fields_table.removeRow(row))
                
                # Update row numbers for all delete buttons when a row is removed
                delete_button.clicked.connect(lambda: update_delete_buttons())
                
                custom_fields_table.setCellWidget(row, 2, delete_button)
            
            # Function to update row numbers for all delete buttons
            def update_delete_buttons():
                for r in range(custom_fields_table.rowCount()):
                    if custom_fields_table.cellWidget(r, 2):
                        custom_fields_table.removeCellWidget(r, 2)
                        add_delete_button(r)
            
            # Add existing metadata fields (except standard ones)
            standard_metadata_fields = ['os', 'notes', 'added_manually', 'added_on', 'last_edited', 
                                        'discovery_source', 'discovery_timestamp', 'discovery_method']
            for field_name, field_value in metadata.items():
                # Skip standard metadata fields
                if field_name in standard_metadata_fields:
                    continue
                    
                # Add custom field to table
                row = custom_fields_table.rowCount()
                custom_fields_table.insertRow(row)
                custom_fields_table.setItem(row, 0, QTableWidgetItem(field_name))
                custom_fields_table.setItem(row, 1, QTableWidgetItem(str(field_value)))
                add_delete_button(row)
            
            custom_layout.addWidget(custom_fields_table)
            
            # Add button for custom fields
            add_field_button = QPushButton("Add Custom Field")
            def add_custom_field():
                row = custom_fields_table.rowCount()
                custom_fields_table.insertRow(row)
                custom_fields_table.setItem(row, 0, QTableWidgetItem(""))
                custom_fields_table.setItem(row, 1, QTableWidgetItem(""))
                add_delete_button(row)
            add_field_button.clicked.connect(add_custom_field)
            custom_layout.addWidget(add_field_button)
            
            # Create raw fields group for direct editing of all fields
            raw_fields_group = QGroupBox("All Fields (Advanced)")
            raw_fields_group.setCheckable(True)
            raw_fields_group.setChecked(False)  # Collapsed by default
            raw_layout = QVBoxLayout(raw_fields_group)
            
            # Table for all fields
            raw_fields_table = QTableWidget(0, 3)  # Name, Value, Delete
            raw_fields_table.setHorizontalHeaderLabels(["Field Name", "Value", "Delete"])
            raw_fields_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            raw_fields_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            raw_fields_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            
            # Function to add delete button to a raw field row
            def add_raw_delete_button(row):
                delete_button = QPushButton("✕")
                delete_button.setFixedWidth(30)
                delete_button.clicked.connect(lambda: raw_fields_table.removeRow(row))
                
                # Update row numbers for all delete buttons when a row is removed
                delete_button.clicked.connect(lambda: update_raw_delete_buttons())
                
                raw_fields_table.setCellWidget(row, 2, delete_button)
            
            # Function to update row numbers for all delete buttons in raw fields table
            def update_raw_delete_buttons():
                for r in range(raw_fields_table.rowCount()):
                    if raw_fields_table.cellWidget(r, 2):
                        raw_fields_table.removeCellWidget(r, 2)
                        add_raw_delete_button(r)
            
            # Add all device fields
            for field_name, field_value in device.items():
                # Skip metadata field as it's handled specially
                if field_name == 'metadata' or field_name == 'ip':
                    continue
                    
                # Convert complex values to string representation
                if isinstance(field_value, (dict, list)):
                    field_value = json.dumps(field_value)
                    
                row = raw_fields_table.rowCount()
                raw_fields_table.insertRow(row)
                field_item = QTableWidgetItem(field_name)
                # Make ID and other critical fields read-only
                if field_name == 'id':
                    field_item.setFlags(field_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                raw_fields_table.setItem(row, 0, field_item)
                raw_fields_table.setItem(row, 1, QTableWidgetItem(str(field_value)))
                add_raw_delete_button(row)
            
            raw_layout.addWidget(raw_fields_table)
            add_raw_button = QPushButton("Add Field")
            def add_raw_field():
                row = raw_fields_table.rowCount()
                raw_fields_table.insertRow(row)
                raw_fields_table.setItem(row, 0, QTableWidgetItem(""))
                raw_fields_table.setItem(row, 1, QTableWidgetItem(""))
                add_raw_delete_button(row)
            add_raw_button.clicked.connect(add_raw_field)
            raw_layout.addWidget(add_raw_button)
            
            # Warning label
            warning_label = QLabel("Warning: Editing raw fields may cause unexpected behavior. Critical fields like 'id' cannot be modified.")
            warning_label.setStyleSheet("color: red")
            warning_label.setWordWrap(True)
            raw_layout.addWidget(warning_label)
            
            # Add form and groups to scroll layout
            scroll_layout.addWidget(standard_group)
            scroll_layout.addWidget(metadata_group)
            scroll_layout.addWidget(custom_fields_group)
            scroll_layout.addWidget(raw_fields_group)
            
            # Finish scroll area setup
            scroll_area.setWidget(scroll_widget)
            main_layout.addWidget(scroll_area)
            
            # Add button box
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            main_layout.addWidget(button_box)
            
            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Create a copy of the device to modify
                updated_device = device.copy()
                
                # Update standard fields
                updated_device['hostname'] = hostname_input.text().strip() or device.get('hostname', '')
                updated_device['mac'] = mac_input.text().strip() or device.get('mac', '')
                updated_device['status'] = status_combo.currentText()
                updated_device['alias'] = alias_input.text().strip()
                
                # Update metadata
                if 'metadata' not in updated_device:
                    updated_device['metadata'] = {}
                
                updated_device['metadata']['os'] = os_input.text().strip()
                updated_device['metadata']['notes'] = notes_input.text().strip()
                updated_device['metadata']['last_edited'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Update custom fields - first clear existing custom fields
                for field in list(updated_device['metadata'].keys()):
                    if field not in standard_metadata_fields:
                        del updated_device['metadata'][field]
                
                # Then add the custom fields from the table
                for row in range(custom_fields_table.rowCount()):
                    field_name = custom_fields_table.item(row, 0).text().strip()
                    field_value = custom_fields_table.item(row, 1).text().strip()
                    if field_name:  # Only add non-empty field names
                        updated_device['metadata'][field_name] = field_value
                
                # Update raw fields (advanced) if the group is checked
                if raw_fields_group.isChecked():
                    # Get all raw fields to delete (except protected ones)
                    fields_to_delete = set()
                    current_fields = set()
                    
                    for field_name in updated_device.keys():
                        if field_name != 'metadata' and field_name != 'ip':
                            fields_to_delete.add(field_name)
                    
                    # Add fields from table
                    for row in range(raw_fields_table.rowCount()):
                        field_name = raw_fields_table.item(row, 0).text().strip()
                        field_value = raw_fields_table.item(row, 1).text().strip()
                        
                        if field_name and field_name != 'metadata' and field_name != 'ip':
                            current_fields.add(field_name)
                            # Try to convert string representations back to complex types
                            try:
                                if field_value.startswith('{') and field_value.endswith('}'):
                                    field_value = json.loads(field_value)
                                elif field_value.startswith('[') and field_value.endswith(']'):
                                    field_value = json.loads(field_value)
                            except json.JSONDecodeError:
                                # If conversion fails, keep as string
                                pass
                                
                            updated_device[field_name] = field_value
                    
                    # Delete fields that were not in the table
                    for field_name in fields_to_delete - current_fields:
                        if field_name != 'id':  # Don't delete ID
                            del updated_device[field_name]
                
                # Find and update the row in the table
                row = self.find_device_row(updated_device['ip'])
                if row is not None:
                    self.update_device_row(row, updated_device)
                
                # Update database if available
                if hasattr(self.main_window, 'database_manager'):
                    self.main_window.database_manager.save_device(updated_device)
                
                self.main_window.statusBar.showMessage(f"Device {updated_device.get('ip')} updated successfully")
                
                # Log the activity
                if hasattr(self.main_window, 'bottom_panel'):
                    self.main_window.bottom_panel.add_log_entry(f"Updated device: {updated_device.get('ip')}", level="INFO")
                
                # Emit signal that device data has changed
                self.device_selected.emit(updated_device)
                
        except Exception as e:
            self.main_window.statusBar.showMessage(f"Error updating device: {str(e)}")
            if hasattr(self.main_window, 'bottom_panel'):
                self.main_window.bottom_panel.add_log_entry(f"Error updating device: {str(e)}", level="ERROR")

    def get_group_names(self):
        """Get list of all device group names.
        
        Returns:
            List[str]: List of group names
        """
        return list(self.device_groups.keys())
    
    def create_device_group(self, group_name: str) -> bool:
        """Create a new device group.
        
        Args:
            group_name: Name of the group to create
        
        Returns:
            bool: True if creation was successful, False otherwise
        """
        if not group_name or group_name.strip() == "":
            return False
            
        if group_name in self.device_groups:
            return False  # Group already exists
            
        self.device_groups[group_name] = []
        return True
    
    def delete_device_group(self, group_name: str) -> bool:
        """Delete a device group.
        
        Args:
            group_name: Name of the group to delete
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if group_name not in self.device_groups:
            return False
            
        del self.device_groups[group_name]
        return True
    
    def add_device_to_group(self, device_id: str, group_name: str) -> bool:
        """Add a device to a group.
        
        Args:
            device_id: ID of the device to add
            group_name: Name of the group to add to
        
        Returns:
            bool: True if operation was successful, False otherwise
        """
        if group_name not in self.device_groups:
            return False
            
        # Check if device exists
        device_exists = False
        for device in self.devices:
            if device.get('id') == device_id:
                device_exists = True
                break
                
        if not device_exists:
            return False
            
        # Don't add if already in the group
        if device_id in self.device_groups[group_name]:
            return True
            
        self.device_groups[group_name].append(device_id)
        return True
    
    def remove_device_from_group(self, device_id: str, group_name: str) -> bool:
        """Remove a device from a group.
        
        Args:
            device_id: ID of the device to remove
            group_name: Name of the group to remove from
        
        Returns:
            bool: True if operation was successful, False otherwise
        """
        if group_name not in self.device_groups:
            return False
            
        if device_id not in self.device_groups[group_name]:
            return False
            
        self.device_groups[group_name].remove(device_id)
        return True
    
    def get_devices_in_group(self, group_name: str) -> List[Dict]:
        """Get all devices in a group.
        
        Args:
            group_name: Name of the group
        
        Returns:
            List[Dict]: List of device dictionaries in the group
        """
        if group_name not in self.device_groups:
            return []
            
        group_devices = []
        for device_id in self.device_groups[group_name]:
            for device in self.devices:
                if device.get('id') == device_id:
                    group_devices.append(device)
                    break
                    
        return group_devices
    
    def get_device_groups(self, device_id: str) -> List[str]:
        """Get all groups a device belongs to.
        
        Args:
            device_id: ID of the device
        
        Returns:
            List[str]: List of group names the device belongs to
        """
        device_groups = []
        for group_name, device_ids in self.device_groups.items():
            if device_id in device_ids:
                device_groups.append(group_name)
                
        return device_groups
    
    def manage_device_groups(self):
        """Show dialog for managing device groups."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
            QPushButton, QLabel, QInputDialog, QMessageBox, QSplitter,
            QTreeWidget, QTreeWidgetItem
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Device Groups")
        dialog.resize(800, 500)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Explanation label
        label = QLabel("Create and manage device groups:")
        layout.addWidget(label)
        
        # Create splitter for groups and devices
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === Left side: Groups management ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        group_label = QLabel("Device Groups:")
        left_layout.addWidget(group_label)
        
        # List widget for groups
        group_list = QListWidget()
        group_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Populate group list
        for group_name in self.device_groups.keys():
            item = QListWidgetItem(group_name)
            group_list.addItem(item)
        
        left_layout.addWidget(group_list)
        
        # Group management buttons
        group_button_layout = QHBoxLayout()
        
        add_group_button = QPushButton("Add Group")
        rename_group_button = QPushButton("Rename")
        delete_group_button = QPushButton("Delete")
        
        group_button_layout.addWidget(add_group_button)
        group_button_layout.addWidget(rename_group_button)
        group_button_layout.addWidget(delete_group_button)
        
        left_layout.addLayout(group_button_layout)
        
        # === Right side: Group member management ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        devices_label = QLabel("Devices:")
        right_layout.addWidget(devices_label)
        
        # Tree widget for devices with checkboxes
        device_tree = QTreeWidget()
        device_tree.setHeaderLabels(["Device", "IP", "Hostname"])
        device_tree.setColumnWidth(0, 250)
        
        def populate_device_tree(selected_group=None):
            device_tree.clear()
            
            for device in self.devices:
                item = QTreeWidgetItem(device_tree)
                item.setText(0, device.get('alias', device.get('hostname', 'Unknown')))
                item.setText(1, device.get('ip', 'N/A'))
                item.setText(2, device.get('hostname', 'Unknown'))
                
                # Store device ID in item
                item.setData(0, Qt.ItemDataRole.UserRole, device.get('id', ''))
                
                # Check the item if device is in selected group
                if selected_group and device.get('id', '') in self.device_groups.get(selected_group, []):
                    item.setCheckState(0, Qt.CheckState.Checked)
                else:
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                    
        # Initialize with no group selected
        populate_device_tree()
        
        right_layout.addWidget(device_tree)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        # Button layout for dialog
        dialog_button_layout = QHBoxLayout()
        
        # Add spacer to push buttons to the right
        dialog_button_layout.addStretch()
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        dialog_button_layout.addWidget(cancel_button)
        
        # Save button
        save_button = QPushButton("Save")
        save_button.clicked.connect(dialog.accept)
        dialog_button_layout.addWidget(save_button)
        
        layout.addLayout(dialog_button_layout)
        
        # === Connect signals ===
        
        # Add group button
        def on_add_group():
            group_name, ok = QInputDialog.getText(
                dialog, "Add Group", "Enter group name:"
            )
            if ok and group_name:
                if group_name in self.device_groups:
                    QMessageBox.warning(
                        dialog, "Warning", f"Group '{group_name}' already exists."
                    )
                    return
                
                # Add group to list
                item = QListWidgetItem(group_name)
                group_list.addItem(item)
                group_list.setCurrentItem(item)
                
                # Create empty group
                self.device_groups[group_name] = []
                
                # Update device tree
                populate_device_tree(group_name)
        
        add_group_button.clicked.connect(on_add_group)
        
        # Rename group button
        def on_rename_group():
            selected_items = group_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(
                    dialog, "Warning", "Please select a group to rename."
                )
                return
            
            current_name = selected_items[0].text()
            new_name, ok = QInputDialog.getText(
                dialog, "Rename Group", "Enter new name:", text=current_name
            )
            
            if ok and new_name and new_name != current_name:
                if new_name in self.device_groups:
                    QMessageBox.warning(
                        dialog, "Warning", f"Group '{new_name}' already exists."
                    )
                    return
                
                # Update group list
                selected_items[0].setText(new_name)
                
                # Update device groups dictionary
                self.device_groups[new_name] = self.device_groups.pop(current_name)
        
        rename_group_button.clicked.connect(on_rename_group)
        
        # Delete group button
        def on_delete_group():
            selected_items = group_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(
                    dialog, "Warning", "Please select a group to delete."
                )
                return
            
            group_name = selected_items[0].text()
            
            reply = QMessageBox.question(
                dialog,
                "Confirm Deletion",
                f"Are you sure you want to delete the group '{group_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Remove from list
                row = group_list.row(selected_items[0])
                group_list.takeItem(row)
                
                # Remove from device groups dictionary
                if group_name in self.device_groups:
                    del self.device_groups[group_name]
                
                # Update device tree (with no group selected)
                populate_device_tree()
        
        delete_group_button.clicked.connect(on_delete_group)
        
        # Group selection change
        def on_group_selection_changed():
            selected_items = group_list.selectedItems()
            if selected_items:
                selected_group = selected_items[0].text()
                populate_device_tree(selected_group)
            else:
                populate_device_tree()
        
        group_list.itemSelectionChanged.connect(on_group_selection_changed)
        
        # Device checkbox state change
        def on_device_check_changed(item, column):
            if column != 0:
                return
                
            selected_items = group_list.selectedItems()
            if not selected_items:
                # If no group is selected, reset the checkbox
                is_checked = item.checkState(0) == Qt.CheckState.Checked
                if is_checked:
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                    QMessageBox.warning(
                        dialog, "Warning", "Please select a group first."
                    )
                return
                
            group_name = selected_items[0].text()
            device_id = item.data(0, Qt.ItemDataRole.UserRole)
            is_checked = item.checkState(0) == Qt.CheckState.Checked
            
            if is_checked:
                # Add device to group
                if device_id not in self.device_groups[group_name]:
                    self.device_groups[group_name].append(device_id)
            else:
                # Remove device from group
                if device_id in self.device_groups[group_name]:
                    self.device_groups[group_name].remove(device_id)
        
        device_tree.itemChanged.connect(on_device_check_changed)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # The groups are already updated in the handlers
            self.main_window.statusBar.showMessage("Device groups updated", 5000)
            
            # Save to database if available
            if hasattr(self.main_window, 'database_manager') and self.main_window.database_manager:
                try:
                    self.main_window.database_manager.save_device_groups(self.device_groups)
                    self.main_window.bottom_panel.add_log_entry("Device groups saved to database", level="INFO")
                except Exception as e:
                    self.main_window.bottom_panel.add_log_entry(f"Error saving device groups: {str(e)}", level="ERROR")
    
    def add_selected_devices_to_group(self, group_name):
        """Add selected devices to an existing group."""
        selected_devices = self.get_selected_devices()
        if not selected_devices:
            return
            
        count = 0
        for device in selected_devices:
            if self.add_device_to_group(device.get('id', ''), group_name):
                count += 1
                
        self.main_window.statusBar.showMessage(f"Added {count} device(s) to group '{group_name}'", 5000)
        
        # Update database if available
        if hasattr(self.main_window, 'database_manager') and self.main_window.database_manager:
            try:
                self.main_window.database_manager.save_device_groups(self.device_groups)
            except Exception as e:
                self.main_window.bottom_panel.add_log_entry(f"Error saving device groups: {str(e)}", level="ERROR")
    
    def add_selected_devices_to_new_group(self):
        """Add selected devices to a new group."""
        selected_devices = self.get_selected_devices()
        if not selected_devices:
            return
            
        # Prompt for group name
        from PySide6.QtWidgets import QInputDialog
        
        group_name, ok = QInputDialog.getText(
            self, "New Group", "Enter group name:"
        )
        
        if not ok or not group_name:
            return
            
        # Create new group
        if not self.create_device_group(group_name):
            self.main_window.statusBar.showMessage(f"Group '{group_name}' already exists", 5000)
            return
            
        # Add selected devices to group
        count = 0
        for device in selected_devices:
            if self.add_device_to_group(device.get('id', ''), group_name):
                count += 1
                
        self.main_window.statusBar.showMessage(f"Added {count} device(s) to new group '{group_name}'", 5000)
        
        # Update database if available
        if hasattr(self.main_window, 'database_manager') and self.main_window.database_manager:
            try:
                self.main_window.database_manager.save_device_groups(self.device_groups)
            except Exception as e:
                self.main_window.bottom_panel.add_log_entry(f"Error saving device groups: {str(e)}", level="ERROR")
    
    def remove_selected_devices(self):
        """Remove selected devices from table and workspace."""
        selected_devices = self.get_selected_devices()
        if not selected_devices:
            return
            
        # Ask for confirmation
        device_count = len(selected_devices)
        confirmation_message = f"Are you sure you want to remove {device_count} selected device(s)?"
        
        reply = QMessageBox.question(
            self,
            "Remove Devices",
            confirmation_message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Process devices
            removed_count = 0
            
            # Start with last row to avoid index changes during removal
            rows_to_remove = []
            
            # Get all rows to remove
            for device in selected_devices:
                row = self.find_device_row(device.get('ip', ''))
                if row is not None:
                    rows_to_remove.append(row)
                    
                    # Remove from workspace using the core-workspace plugin
                    try:
                        if hasattr(self.main_window, 'plugin_manager'):
                            workspace_plugin_api = self.main_window.plugin_manager.plugin_apis.get("core-workspace")
                            if workspace_plugin_api:
                                workspace_plugin_api.call_function("remove_device", device['id'])
                    except Exception as e:
                        logging.error(f"Error removing device from workspace: {str(e)}")
                        
                    # Remove from all groups
                    device_id = device.get('id', '')
                    for group_name, device_ids in self.device_groups.items():
                        if device_id in device_ids:
                            device_ids.remove(device_id)
                            
                    removed_count += 1
            
            # Sort rows in descending order to remove from bottom to top
            rows_to_remove.sort(reverse=True)
            
            # Remove rows
            for row in rows_to_remove:
                self.removeRow(row)
                
            # Update devices list
            self.devices = [d for d in self.devices if d['id'] not in [device['id'] for device in selected_devices]]
            
            # Update database if available
            if hasattr(self.main_window, 'database_manager') and self.main_window.database_manager:
                try:
                    self.main_window.database_manager.save_device_groups(self.device_groups)
                except Exception as e:
                    self.main_window.bottom_panel.add_log_entry(f"Error saving device groups: {str(e)}", level="ERROR")
                    
            self.main_window.statusBar.showMessage(f"Removed {removed_count} device(s)", 5000)

    def get_column_index(self, column_name):
        """Get the index of a column by its name.
        
        Args:
            column_name (str): The name of the column
            
        Returns:
            int: The column index, or -1 if not found
        """
        for i in range(self.columnCount()):
            if self.horizontalHeaderItem(i) and self.horizontalHeaderItem(i).text().lower() == column_name.lower():
                return i
        return -1 