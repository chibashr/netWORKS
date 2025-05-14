#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Device table model and view for NetWORKS
"""

from loguru import logger
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Signal, Slot
from PySide6.QtWidgets import (QTableView, QHeaderView, QAbstractItemView, QMenu, QApplication, QWidget, QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QLabel, QTextEdit, QPushButton, QHBoxLayout, QComboBox, QTabWidget, QListWidget, QListWidgetItem, QMessageBox, QGroupBox, QCheckBox, QTableWidget, QTableWidgetItem, QFileDialog, QWizard, QWizardPage, QScrollArea)
from PySide6.QtGui import QColor, QBrush, QFont, QIcon, QAction
from ..core.device_manager import Device
import csv
import io


class DeviceTableModel(QAbstractTableModel):
    """Model for device table"""
    
    def __init__(self, device_manager):
        """Initialize the model"""
        super().__init__()
        
        self.device_manager = device_manager
        self._devices = []
        
        # All available headers (columns)
        self._all_headers = ["Alias", "Hostname", "IP Address", "MAC Address", "Status", "Tags", "Groups"]
        self._all_column_keys = ["alias", "hostname", "ip_address", "mac_address", "status", "tags", "groups"]
        
        # Currently visible headers
        self._headers = self._all_headers.copy()
        self._column_keys = self._all_column_keys.copy()
        
        # Additional columns from plugins
        self._plugin_columns = []  # (header, key, callback)
        
        # Custom property columns
        self._custom_prop_headers = []
        self._custom_prop_keys = []
        
        # Cache for device groups
        self._device_groups = {}  # device.id -> [group_names]
        
        # Group filter
        self._filter_group = None
        
        # Connect to device manager signals
        self.device_manager.device_added.connect(self.on_device_added)
        self.device_manager.device_removed.connect(self.on_device_removed)
        self.device_manager.device_changed.connect(self.on_device_changed)
        self.device_manager.group_added.connect(self.on_model_changed)
        self.device_manager.group_removed.connect(self.on_model_changed)
        
        # Initialize data
        self.refresh_devices()
        
    def filter_by_group(self, group):
        """Filter devices by group"""
        self._filter_group = group
        self.refresh_devices()
        
    def get_all_headers(self):
        """Get all available headers"""
        # Discover custom properties from all devices
        self._discover_custom_properties()
        
        # Combine standard headers, plugin headers, and custom property headers
        all_headers = self._all_headers.copy()
        plugin_headers = [header for header, _, _ in self._plugin_columns]
        
        return all_headers + plugin_headers + self._custom_prop_headers
        
    def get_visible_headers(self):
        """Get currently visible headers"""
        return self._headers
        
    def _discover_custom_properties(self):
        """Discover custom properties from all devices"""
        self._custom_prop_headers = []
        self._custom_prop_keys = []
        
        # Core properties to exclude
        core_props = ["id", "alias", "hostname", "ip_address", "mac_address", "status", "notes", "tags"]
        
        # Collect custom properties from all devices
        custom_props = {}
        for device in self.device_manager.get_devices():
            for key, value in device.get_properties().items():
                if key not in core_props and key not in self._all_column_keys:
                    # Skip complex values like lists and dicts
                    if not isinstance(value, (list, dict)):
                        custom_props[key] = True
        
        # Sort the custom properties alphabetically
        sorted_props = sorted(custom_props.keys())
        
        # Create headers for custom properties
        for key in sorted_props:
            header = key.replace('_', ' ').title()
            self._custom_prop_headers.append(header)
            self._custom_prop_keys.append(key)
        
    def set_visible_headers(self, headers):
        """Set which headers (columns) are visible"""
        # Make sure all custom properties are discovered
        self._discover_custom_properties()
        
        # Validate headers
        valid_headers = [h for h in headers if h in self.get_all_headers()]
        
        if not valid_headers:
            return False
            
        # Update headers and column keys
        self._headers = []
        self._column_keys = []
        
        # Add standard headers first
        for i, header in enumerate(self._all_headers):
            if header in valid_headers:
                self._headers.append(header)
                self._column_keys.append(self._all_column_keys[i])
                
        # Then add plugin headers
        for header, key, callback in self._plugin_columns:
            if header in valid_headers:
                self._headers.append(header)
                
        # Then add custom property headers
        for i, header in enumerate(self._custom_prop_headers):
            if header in valid_headers:
                self._headers.append(header)
                self._column_keys.append(self._custom_prop_keys[i])
        
        # Notify view of layout change
        self.layoutChanged.emit()
        return True
        
    def refresh_devices(self):
        """Refresh the device list"""
        # Begin model reset to ensure proper clearing
        self.beginResetModel()
        
        # Get devices based on filter
        if self._filter_group:
            # Get devices from the specified group
            self._devices = self._filter_group.get_all_devices()
        else:
            # Get all devices
            self._devices = self.device_manager.get_devices()
        
        # Update device groups cache
        self._update_device_groups()
        
        # Discover custom properties
        self._discover_custom_properties()
        
        # End model reset
        self.endResetModel()
        
        # Log the refresh for debugging
        logger.debug(f"Refreshed device table with {len(self._devices)} devices")
        
    def _update_device_groups(self):
        """Update the device groups cache"""
        self._device_groups = {}
        
        # Get all groups
        groups = self.device_manager.get_groups()
        
        # For each group, add its name to the devices in it
        for group in groups:
            # Skip the root group (All Devices)
            if group == self.device_manager.root_group:
                continue
                
            for device in group.devices:
                if device.id not in self._device_groups:
                    self._device_groups[device.id] = []
                
                self._device_groups[device.id].append(group.name)
        
    def add_column(self, header, key, callback=None):
        """Add a column to the table"""
        if header in self._headers:
            return False
            
        self._headers.append(header)
        
        if callback:
            self._plugin_columns.append((header, key, callback))
        else:
            self._column_keys.append(key)
            
        self.layoutChanged.emit()
        return True
        
    def remove_column(self, header):
        """Remove a column from the table"""
        if header not in self._headers:
            return False
            
        index = self._headers.index(header)
        self._headers.pop(index)
        
        # Check if it's a plugin column or regular column
        for i, (col_header, key, callback) in enumerate(self._plugin_columns):
            if col_header == header:
                self._plugin_columns.pop(i)
                break
        else:
            if index < len(self._column_keys):
                self._column_keys.pop(index)
                
        self.layoutChanged.emit()
        return True
        
    def rowCount(self, parent=None):
        """Return the number of rows"""
        return len(self._devices)
        
    def columnCount(self, parent=None):
        """Return the number of columns"""
        return len(self._headers)
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return the header data"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
        
    def data(self, index, role=Qt.DisplayRole):
        """Return the cell data"""
        if not index.isValid():
            return None
            
        if index.row() >= len(self._devices) or index.row() < 0:
            return None
            
        device = self._devices[index.row()]
        column = index.column()
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            # Check if it's a plugin column
            for header, key, callback in self._plugin_columns:
                if header == self._headers[column]:
                    return callback(device)
            
            # Regular column or custom property column
            if column < len(self._column_keys):
                key = self._column_keys[column]
                
                # Special handling for device groups
                if key == "groups":
                    groups = self._device_groups.get(device.id, [])
                    return ", ".join(groups) if groups else ""
                
                value = device.get_property(key, "")
                
                # Special handling for tag lists
                if key == "tags" and isinstance(value, list):
                    return ", ".join(value)
                
                return value
                
            return None
            
        elif role == Qt.BackgroundRole:
            # Highlight selected devices
            if device in self.device_manager.get_selected_devices():
                return QBrush(QColor(240, 248, 255))  # Light blue
                
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter
            
        elif role == Qt.UserRole:
            # Return the device object
            return device
            
        return None
        
    def flags(self, index):
        """Return the cell flags"""
        if not index.isValid():
            return Qt.NoItemFlags
            
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
    @Slot(object)
    def on_device_added(self, device):
        """Handle device added signal"""
        if device not in self._devices:
            self._devices.append(device)
            # Check if device has new custom properties
            self._discover_custom_properties()
            self.layoutChanged.emit()
            
    @Slot(object)
    def on_device_removed(self, device):
        """Handle device removed signal"""
        if device in self._devices:
            row = self._devices.index(device)
            self.beginRemoveRows(QModelIndex(), row, row)
            self._devices.remove(device)
            self.endRemoveRows()
            # Re-discover custom properties in case this was the only device with a particular property
            self._discover_custom_properties()
            
    @Slot(object)
    def on_device_changed(self, device):
        """Handle device changed signal"""
        if device in self._devices:
            # Update device groups cache for this device
            self._update_device_groups()
            
            # Check if device has new custom properties
            old_custom_props = set(self._custom_prop_keys)
            self._discover_custom_properties()
            new_custom_props = set(self._custom_prop_keys)
            
            # If custom properties have changed, update the view
            if old_custom_props != new_custom_props:
                self.layoutChanged.emit()
            else:
                # Just update the specific row
                row = self._devices.index(device)
                left_index = self.index(row, 0)
                right_index = self.index(row, self.columnCount() - 1)
                self.dataChanged.emit(left_index, right_index)
            
    @Slot()
    def on_model_changed(self):
        """Handle model changed signal"""
        self.refresh_devices()


class DeviceTableView(QTableView):
    """Custom table view for devices"""
    
    double_clicked = Signal(object)
    context_menu_requested = Signal(object, QMenu)
    
    def __init__(self, device_manager):
        """Initialize the view"""
        super().__init__()
        
        self.device_manager = device_manager
        self._context_menu_actions = []  # List of (name, callback, priority) tuples
        self._ignore_selection_changes = False  # Flag to prevent recursive selection updates
        
        # Create and set the model
        self.table_model = DeviceTableModel(self.device_manager)
        
        # Create a proxy model for filtering and sorting
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # Filter on all columns
        
        # Set the proxy model
        self.setModel(self.proxy_model)
        
        # Set up the view
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Set up the horizontal header
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.setSortIndicator(0, Qt.AscendingOrder)
        
        # Create a filter layout to put above the table
        self.filter_widget = QWidget()
        self.filter_layout = QHBoxLayout(self.filter_widget)
        self.filter_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create a search filter
        self.filter_label = QLabel("Filter:")
        self.filter_layout.addWidget(self.filter_label)
        
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search in all columns...")
        self.filter_edit.textChanged.connect(self.filter_table)
        self.filter_layout.addWidget(self.filter_edit)
        
        # Create a group filter
        self.group_label = QLabel("Group:")
        self.filter_layout.addWidget(self.group_label)
        
        self.group_combo = QComboBox()
        self.refresh_group_combo()
        self.group_combo.currentIndexChanged.connect(self.filter_by_group)
        self.filter_layout.addWidget(self.group_combo)
        
        # Create a button to customize columns
        self.columns_button = QPushButton("Columns")
        self.columns_button.clicked.connect(self.show_column_selector)
        self.filter_layout.addWidget(self.columns_button)
        
        # Add select all/none buttons
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self._on_action_select_all)
        self.filter_layout.addWidget(self.select_all_button)
        
        self.select_none_button = QPushButton("Deselect All")
        self.select_none_button.clicked.connect(self._on_action_deselect_all)
        self.filter_layout.addWidget(self.select_none_button)
        
        # Connect signals
        self.clicked.connect(self.on_item_clicked)
        self.doubleClicked.connect(self.on_item_double_clicked)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.selectionModel().selectionChanged.connect(self.on_selection_model_changed)
        
        # Connect to device manager signals for group changes
        self.device_manager.group_added.connect(self.refresh_group_combo)
        self.device_manager.group_removed.connect(self.refresh_group_combo)
        self.device_manager.group_changed.connect(self.refresh_group_combo)
        
        # Register default context menu actions
        self.register_context_menu_action("Add Device", self._on_action_add_device, 10)
        self.register_context_menu_action("Import Devices...", self._on_action_import_devices, 20)
        self.register_context_menu_action("Edit Properties", self._on_action_edit_properties, 200)
        self.register_context_menu_action("Add to Group", self._on_action_add_to_group, 300)
        self.register_context_menu_action("Create New Group", self._on_action_create_group, 310)
        self.register_context_menu_action("Select All", self._on_action_select_all, 400)
        self.register_context_menu_action("Deselect All", self._on_action_deselect_all, 410)
        self.register_context_menu_action("Delete", self._on_action_delete, 900)
        
    def refresh(self):
        """Refresh the device table view and its components"""
        # Refresh the device data in the model
        self.table_model.refresh_devices()
        # Refresh the group combo to ensure it's up to date
        self.refresh_group_combo()
        # Clear any current filter
        self.filter_edit.clear()
        # Reset selection
        self.clearSelection()
    
    def refresh_group_combo(self):
        """Refresh the group filter dropdown"""
        # Save current selection
        current_text = self.group_combo.currentText() if self.group_combo.count() > 0 else ""
        
        # Clear and refill
        self.group_combo.clear()
        self.group_combo.addItem("All Groups")
        
        # Add all groups
        for group in self.device_manager.get_groups():
            if group != self.device_manager.root_group:
                self.group_combo.addItem(group.name, group)
                
        # Try to restore previous selection
        if current_text:
            index = self.group_combo.findText(current_text)
            if index >= 0:
                self.group_combo.setCurrentIndex(index)
    
    def filter_table(self, text):
        """Filter the table based on the text"""
        self.proxy_model.setFilterFixedString(text)
        
    def filter_by_group(self, index):
        """Filter the table by selected group"""
        if index == 0:  # All Groups
            self.table_model.filter_by_group(None)
        else:
            group = self.group_combo.itemData(index)
            self.table_model.filter_by_group(group)
            
    def show_column_selector(self):
        """Show a dialog to select which columns to display"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Columns")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Get all available columns from the model
        available_standard_columns = self.table_model._all_headers
        available_plugin_columns = [header for header, _, _ in self.table_model._plugin_columns]
        available_custom_columns = self.table_model._custom_prop_headers
        visible_columns = self.table_model.get_visible_headers()
        
        # Create sections for different column types
        if available_standard_columns:
            standard_group = QGroupBox("Standard Columns")
            standard_layout = QVBoxLayout(standard_group)
            
            standard_checkboxes = []
            for column in available_standard_columns:
                checkbox = QCheckBox(column)
                checkbox.setChecked(column in visible_columns)
                standard_checkboxes.append((column, checkbox))
                standard_layout.addWidget(checkbox)
                
            layout.addWidget(standard_group)
        
        if available_plugin_columns:
            plugin_group = QGroupBox("Plugin Columns")
            plugin_layout = QVBoxLayout(plugin_group)
            
            plugin_checkboxes = []
            for column in available_plugin_columns:
                checkbox = QCheckBox(column)
                checkbox.setChecked(column in visible_columns)
                plugin_checkboxes.append((column, checkbox))
                plugin_layout.addWidget(checkbox)
                
            layout.addWidget(plugin_group)
            
        if available_custom_columns:
            custom_group = QGroupBox("Custom Property Columns")
            custom_layout = QVBoxLayout(custom_group)
            
            custom_checkboxes = []
            for column in available_custom_columns:
                checkbox = QCheckBox(column)
                checkbox.setChecked(column in visible_columns)
                custom_checkboxes.append((column, checkbox))
                custom_layout.addWidget(checkbox)
                
            layout.addWidget(custom_group)
        
        # Combine all checkboxes
        all_checkboxes = []
        if 'standard_checkboxes' in locals():
            all_checkboxes.extend(standard_checkboxes)
        if 'plugin_checkboxes' in locals():
            all_checkboxes.extend(plugin_checkboxes)
        if 'custom_checkboxes' in locals():
            all_checkboxes.extend(custom_checkboxes)
            
        # Add buttons
        button_layout = QHBoxLayout()
        
        select_all = QPushButton("Select All")
        select_none = QPushButton("Select None")
        reset = QPushButton("Reset to Default")
        
        button_layout.addWidget(select_all)
        button_layout.addWidget(select_none)
        button_layout.addWidget(reset)
        
        layout.addLayout(button_layout)
        
        # Connect button signals
        def on_select_all():
            for _, checkbox in all_checkboxes:
                checkbox.setChecked(True)
                
        def on_select_none():
            for _, checkbox in all_checkboxes:
                checkbox.setChecked(False)
                
        def on_reset():
            # Default columns
            default_columns = ["Alias", "Hostname", "IP Address", "MAC Address", "Status", "Tags", "Groups"]
            for column, checkbox in all_checkboxes:
                checkbox.setChecked(column in default_columns)
                
        select_all.clicked.connect(on_select_all)
        select_none.clicked.connect(on_select_none)
        reset.clicked.connect(on_reset)
        
        # Add dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        if dialog.exec():
            # Get selected columns
            selected_columns = [column for column, checkbox in all_checkboxes if checkbox.isChecked()]
            
            # Ensure at least one column is visible
            if not selected_columns:
                QMessageBox.warning(self, "Column Selection", "At least one column must be visible.")
                return
                
            # Update model
            self.table_model.set_visible_headers(selected_columns)
            
    def get_container_widget(self):
        """Get a widget containing the table and filter controls"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        layout.addWidget(self.filter_widget)
        layout.addWidget(self)
        
        return container
    
    def register_context_menu_action(self, name, callback, priority=500):
        """
        Register a context menu action
        
        Args:
            name: Name of the action (displayed in menu)
            callback: Function to call when action is selected
                     Should accept (device) as argument, or None for table actions
            priority: Priority of the action (lower values appear first)
        
        Returns:
            bool: True if registered successfully
        """
        # Check if action with this name already exists
        for i, (action_name, _, _) in enumerate(self._context_menu_actions):
            if action_name == name:
                # Replace the callback
                self._context_menu_actions[i] = (name, callback, priority)
                return True
        
        # Add new action
        self._context_menu_actions.append((name, callback, priority))
        # Sort by priority
        self._context_menu_actions.sort(key=lambda x: x[2])
        return True
    
    def unregister_context_menu_action(self, name):
        """
        Unregister a context menu action
        
        Args:
            name: Name of the action to remove
        
        Returns:
            bool: True if unregistered successfully
        """
        for i, (action_name, _, _) in enumerate(self._context_menu_actions):
            if action_name == name:
                del self._context_menu_actions[i]
                return True
        return False
    
    def on_item_clicked(self, index):
        """Handle item clicked"""
        if not index.isValid():
            return
            
        device = index.data(Qt.UserRole)
        if not device:
            return
            
        # Get modifiers (we don't need to handle selection behavior here any more)
        # The built-in selection model will handle this, and our selection_changed handler
        # will sync the selection to the device_manager
        modifiers = QApplication.keyboardModifiers()
        logger.debug(f"Item clicked with modifiers: {modifiers}")
        
        # Our on_selection_model_changed method will handle updating the device_manager selection
        # based on the UI selection that happens automatically in Qt
    
    def on_item_double_clicked(self, index):
        """Handle item double clicked"""
        if not index.isValid():
            return
            
        device = index.data(Qt.UserRole)
        if device:
            self.double_clicked.emit(device)
    
    def device_properties_dialog(self, device=None):
        """
        Show a dialog for adding or editing device properties
        
        Args:
            device: Device to edit, or None to create a new device
        
        Returns:
            The modified or new device if accepted, None if cancelled
        """
        is_new = device is None
        dialog = QDialog()
        dialog.setWindowTitle(f"{'Add' if is_new else 'Edit'} Device Properties")
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Create tab widget for organizing properties
        tab_widget = QTabWidget()
        
        # Function to create a handler for the "Show in Table" button
        def make_show_in_table_handler(property_key):
            def handle_show_in_table():
                # Get current visible headers
                table_view = self
                table_model = table_view.table_model
                visible_headers = table_model.get_visible_headers()
                
                # Add this property's header if not already visible
                header_name = property_key.replace('_', ' ').title()
                if header_name not in visible_headers:
                    new_headers = visible_headers + [header_name]
                    table_model.set_visible_headers(new_headers)
                    QMessageBox.information(
                        dialog,
                        "Column Added",
                        f"'{header_name}' column has been added to the device table."
                    )
                else:
                    QMessageBox.information(
                        dialog,
                        "Column Already Visible",
                        f"'{header_name}' column is already visible in the device table."
                    )
            return handle_show_in_table
        
        # Basic tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_form = QFormLayout()
        
        # Core property fields
        alias_edit = QLineEdit(device.get_property("alias", "") if device else "")
        alias_edit.setPlaceholderText("Device name/alias")
        basic_form.addRow("Alias:", alias_edit)
        
        hostname_edit = QLineEdit(device.get_property("hostname", "") if device else "")
        hostname_edit.setPlaceholderText("Enter hostname or FQDN")
        basic_form.addRow("Hostname:", hostname_edit)
        
        ip_edit = QLineEdit(device.get_property("ip_address", "") if device else "")
        ip_edit.setPlaceholderText("Enter IP address")
        basic_form.addRow("IP Address:", ip_edit)
        
        mac_edit = QLineEdit(device.get_property("mac_address", "") if device else "")
        mac_edit.setPlaceholderText("Enter MAC address")
        basic_form.addRow("MAC Address:", mac_edit)
        
        status_combo = QComboBox()
        status_values = ["unknown", "up", "down", "warning", "error", "maintenance"]
        status_combo.addItems(status_values)
        current_status = device.get_property("status", "unknown") if device else "unknown"
        if current_status in status_values:
            status_combo.setCurrentText(current_status)
        basic_form.addRow("Status:", status_combo)
        
        # Add the form to the basic tab
        basic_layout.addLayout(basic_form)
        tab_widget.addTab(basic_tab, "Basic")
        
        # Notes tab
        notes_tab = QWidget()
        notes_layout = QVBoxLayout(notes_tab)
        notes_edit = QTextEdit(device.get_property("notes", "") if device else "")
        notes_edit.setPlaceholderText("Enter notes about this device")
        notes_layout.addWidget(notes_edit)
        tab_widget.addTab(notes_tab, "Notes")
        
        # Tags tab
        tags_tab = QWidget()
        tags_layout = QVBoxLayout(tags_tab)
        
        # Search filter for tags
        tags_filter_layout = QHBoxLayout()
        tags_filter_label = QLabel("Search Tags:")
        tags_filter_edit = QLineEdit()
        tags_filter_edit.setPlaceholderText("Filter tags...")
        tags_filter_layout.addWidget(tags_filter_label)
        tags_filter_layout.addWidget(tags_filter_edit)
        tags_layout.addLayout(tags_filter_layout)
        
        # Create a scroll area for tags to prevent infinite vertical stretching
        tags_scroll = QScrollArea()
        tags_scroll.setWidgetResizable(True)
        tags_scroll.setMaximumHeight(300)  # Limit maximum height
        tags_container = QWidget()
        tags_container_layout = QVBoxLayout(tags_container)
        
        # Tag list
        tags_list = QListWidget()
        tags_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # Add existing tags if editing a device
        current_tags = device.get_property("tags", []) if device else []
        for tag in current_tags:
            item = QListWidgetItem(tag)
            tags_list.addItem(item)
        
        # Set a reasonable minimum size for the tags list
        tags_list.setMinimumHeight(150)
        
        tags_container_layout.addWidget(tags_list)
        tags_scroll.setWidget(tags_container)
        tags_layout.addWidget(tags_scroll)
        
        # Tag controls
        tags_control_layout = QHBoxLayout()
        new_tag = QLineEdit()
        new_tag.setPlaceholderText("New tag")
        add_tag_button = QPushButton("Add")
        remove_tag_button = QPushButton("Remove Selected")
        
        tags_control_layout.addWidget(new_tag)
        tags_control_layout.addWidget(add_tag_button)
        tags_control_layout.addWidget(remove_tag_button)
        
        tags_layout.addLayout(tags_control_layout)
        
        # Add tag function
        def add_tag():
            tag = new_tag.text().strip()
            if tag and not tags_list.findItems(tag, Qt.MatchExactly):
                tags_list.addItem(QListWidgetItem(tag))
                new_tag.clear()
                
        # Remove selected tags
        def remove_selected_tags():
            for item in reversed(tags_list.selectedItems()):
                row = tags_list.row(item)
                tags_list.takeItem(row)
        
        # Add tag filter function
        def filter_tags(text):
            filter_text = text.lower()
            for i in range(tags_list.count()):
                item = tags_list.item(i)
                item.setHidden(filter_text and filter_text not in item.text().lower())
                
        add_tag_button.clicked.connect(add_tag)
        remove_tag_button.clicked.connect(remove_selected_tags)
        tags_filter_edit.textChanged.connect(filter_tags)
        
        # Add enter key press to add tag
        def on_tag_return_pressed():
            if new_tag.text().strip():
                add_tag()
                
        new_tag.returnPressed.connect(on_tag_return_pressed)
        
        # Add tags tab to tab widget
        tab_widget.addTab(tags_tab, "Tags")
        
        # Custom properties tab
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)
        
        # Form layout for existing custom properties
        custom_props_layout = QFormLayout()
        custom_props = {}
        
        # Add existing custom properties if editing a device
        current_custom_props = []
        core_props = ["id", "alias", "hostname", "ip_address", "mac_address", "status", "notes", "tags"]
        
        if device:
            for key, value in device.get_properties().items():
                if key not in core_props:
                    current_custom_props.append(key)
                    prop_layout = QHBoxLayout()
                    
                    # Property value field
                    edit = QLineEdit(str(value))
                    prop_layout.addWidget(edit)
                    custom_props[key] = edit
                    
                    # Add to table button
                    show_in_table_btn = QPushButton("Show in Table")
                    show_in_table_btn.setToolTip("Add this property as a column in the device table")
                    prop_key = key  # Create a local copy of the key for the closure
                    
                    show_in_table_btn.clicked.connect(make_show_in_table_handler(prop_key))
                    prop_layout.addWidget(show_in_table_btn)
                    
                    custom_props_layout.addRow(f"{key}:", prop_layout)
        
        custom_layout.addLayout(custom_props_layout)
        
        # Find common custom properties from other devices
        suggested_props = []
        if self.device_manager:
            # Collect custom properties from all devices
            for other_device in self.device_manager.get_devices():
                # Skip the current device
                if device and other_device.id == device.id:
                    continue
                
                for key, value in other_device.get_properties().items():
                    # Skip core properties and properties already on this device
                    if key not in core_props and key not in current_custom_props:
                        # Skip complex values
                        if not isinstance(value, (list, dict)):
                            suggested_props.append((key, str(value), other_device))
            
            # If we have suggestions, add them to the dialog
            if suggested_props:
                suggestions_group = QGroupBox("Suggested Properties")
                suggestions_layout = QVBoxLayout(suggestions_group)
                
                suggestions_label = QLabel("The following properties are used by other devices:")
                suggestions_label.setWordWrap(True)
                suggestions_layout.addWidget(suggestions_label)
                
                for prop_key, prop_value, source_device in suggested_props:
                    # Create a row for each suggested property
                    prop_widget = QWidget()
                    prop_layout = QHBoxLayout(prop_widget)
                    prop_layout.setContentsMargins(0, 0, 0, 0)
                    
                    # Add checkbox to select the property
                    checkbox = QCheckBox(f"{prop_key} ({source_device.get_property('alias', 'Unknown')})")
                    checkbox.setToolTip(f"Value from {source_device.get_property('alias', 'Unknown')}: {prop_value}")
                    
                    # Add button to add this property
                    add_button = QPushButton("Add")
                    add_button.setToolTip(f"Add this property with value: {prop_value}")
                    
                    prop_key_copy = prop_key
                    prop_value_copy = prop_value
                    
                    def make_add_handler(key, value, checkbox):
                        def handle_add():
                            # Add the property if not already added
                            if key not in custom_props:
                                prop_layout = QHBoxLayout()
                                
                                # Property value field
                                edit = QLineEdit(value)
                                prop_layout.addWidget(edit)
                                custom_props[key] = edit
                                
                                # Add to table button
                                show_in_table_btn = QPushButton("Show in Table")
                                show_in_table_btn.setToolTip("Add this property as a column in the device table")
                                
                                show_in_table_btn.clicked.connect(make_show_in_table_handler(key))
                                prop_layout.addWidget(show_in_table_btn)
                                
                                custom_props_layout.addRow(f"{key}:", prop_layout)
                                
                                # Disable the checkbox and button
                                checkbox.setEnabled(False)
                                checkbox.setText(f"{key} (Added)")
                                add_button.setEnabled(False)
                        return handle_add
                    
                    add_button.clicked.connect(make_add_handler(prop_key_copy, prop_value_copy, checkbox))
                    
                    prop_layout.addWidget(checkbox)
                    prop_layout.addWidget(add_button)
                    prop_layout.addStretch()
                    
                    suggestions_layout.addWidget(prop_widget)
                
                # Add a button to add all selected properties
                add_selected_button = QPushButton("Add Selected Properties")
                suggestions_layout.addWidget(add_selected_button)
                
                # Handler to add all selected properties
                def add_selected_properties():
                    # Find all checked properties
                    for i in range(suggestions_layout.count()):
                        widget = suggestions_layout.itemAt(i).widget()
                        if isinstance(widget, QWidget) and not isinstance(widget, (QLabel, QPushButton)):
                            # Find the checkbox
                            checkbox = None
                            for child in widget.findChildren(QCheckBox):
                                checkbox = child
                                break
                            
                            if checkbox and checkbox.isChecked() and checkbox.isEnabled():
                                # Extract the property key and value
                                text = checkbox.text()
                                key = text.split(" (")[0]
                                
                                # Find the matching suggested property
                                for prop_key, prop_value, _ in suggested_props:
                                    if prop_key == key:
                                        # Add the property
                                        prop_layout = QHBoxLayout()
                                        
                                        # Property value field
                                        edit = QLineEdit(prop_value)
                                        prop_layout.addWidget(edit)
                                        custom_props[key] = edit
                                        
                                        # Add to table button
                                        show_in_table_btn = QPushButton("Show in Table")
                                        show_in_table_btn.setToolTip("Add this property as a column in the device table")
                                        
                                        show_in_table_btn.clicked.connect(make_show_in_table_handler(key))
                                        prop_layout.addWidget(show_in_table_btn)
                                        
                                        custom_props_layout.addRow(f"{key}:", prop_layout)
                                        
                                        # Disable the checkbox
                                        checkbox.setEnabled(False)
                                        checkbox.setText(f"{key} (Added)")
                                        break
                
                add_selected_button.clicked.connect(add_selected_properties)
                
                # Add the suggestions group to the custom tab
                custom_layout.addWidget(suggestions_group)
        
        # Add custom property controls
        add_prop_layout = QHBoxLayout()
        new_prop_name = QLineEdit()
        new_prop_name.setPlaceholderText("Property Name")
        new_prop_value = QLineEdit()
        new_prop_value.setPlaceholderText("Property Value")
        add_prop_button = QPushButton("Add Property")
        
        add_prop_layout.addWidget(new_prop_name)
        add_prop_layout.addWidget(new_prop_value)
        add_prop_layout.addWidget(add_prop_button)
        
        custom_layout.addLayout(add_prop_layout)
        
        # Help text for custom properties
        help_text = QLabel("Custom properties can be used to store additional information about a device.\n"
                          "They can also be displayed as columns in the device table for easy sorting and filtering.")
        help_text.setWordWrap(True)
        custom_layout.addWidget(help_text)
        
        # Add stretch to push controls to the top
        custom_layout.addStretch()
        
        # Add custom tab to tab widget
        tab_widget.addTab(custom_tab, "Custom Properties")
        
        # Add tab widget to main layout
        layout.addWidget(tab_widget)
        
        # Function to add a new property
        def add_property():
            prop_name = new_prop_name.text().strip()
            prop_value = new_prop_value.text().strip()
            
            if not prop_name:
                return
                
            core_props = ["id", "alias", "hostname", "ip_address", "mac_address", "status", "notes", "tags"]
            if prop_name in core_props:
                QMessageBox.warning(
                    dialog,
                    "Reserved Property",
                    f"The property name '{prop_name}' is reserved for system use.\nPlease choose a different name."
                )
                return
            
            # Create a new property row with edit field and 'Show in Table' button
            prop_layout = QHBoxLayout()
            
            # Property value field
            edit = QLineEdit(prop_value)
            prop_layout.addWidget(edit)
            custom_props[prop_name] = edit
            
            # Add to table button
            show_in_table_btn = QPushButton("Show in Table")
            show_in_table_btn.setToolTip("Add this property as a column in the device table")
            
            show_in_table_btn.clicked.connect(make_show_in_table_handler(prop_name))
            prop_layout.addWidget(show_in_table_btn)
            
            custom_props_layout.addRow(f"{prop_name}:", prop_layout)
            
            new_prop_name.clear()
            new_prop_value.clear()
        
        add_prop_button.clicked.connect(add_property)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        if dialog.exec():
            # Get all tags from the list
            tags = [tags_list.item(i).text() for i in range(tags_list.count())]
            
            # Update existing or create new device
            if is_new:
                # Create new device
                new_device = Device(
                    alias=alias_edit.text().strip() or "New Device",
                    hostname=hostname_edit.text().strip(),
                    ip_address=ip_edit.text().strip(),
                    mac_address=mac_edit.text().strip(),
                    status=status_combo.currentText(),
                    notes=notes_edit.toPlainText(),
                    tags=tags
                )
                
                # Add custom properties
                for key, edit in custom_props.items():
                    new_device.set_property(key, edit.text())
                
                return new_device
            else:
                # Update existing device
                device.set_property("alias", alias_edit.text())
                device.set_property("hostname", hostname_edit.text())
                device.set_property("ip_address", ip_edit.text())
                device.set_property("mac_address", mac_edit.text())
                device.set_property("status", status_combo.currentText())
                device.set_property("notes", notes_edit.toPlainText())
                device.set_property("tags", tags)
                
                # Update custom properties
                for key, edit in custom_props.items():
                    device.set_property(key, edit.text())
                
                return device
        
        return None

    def on_context_menu(self, pos):
        """Show context menu"""
        indices = self.selectedIndexes()
        if not indices:
            return
            
        # Get unique rows
        rows = set()
        devices = []
        for index in indices:
            row = index.row()
            rows.add(row)
        
        # Get corresponding devices
        for row in rows:
            # Get the model index for this row
            device_index = self.model().index(row, 0)
            device = device_index.data(Qt.UserRole)
            if device:
                devices.append(device)
                
        # Exit if no devices
        if not devices:
            return
            
        # Create context menu
        menu = QMenu()
        
        # SECTION 1: Device Management Actions
        if len(devices) == 1:
            menu.addAction("Edit Properties", lambda: self._handle_action(self._on_action_edit_properties, devices))
        else:
            menu.addAction(f"Edit Selected Devices ({len(devices)})", lambda: self._handle_action(self._on_action_edit_properties, devices))
            
        menu.addAction("Delete", lambda: self._handle_action(self._on_action_delete, devices))
        
        # SECTION 2: Group Management
        menu.addSeparator()
        
        add_to_group_menu = menu.addMenu("Add to Group")
        self._populate_add_to_group_menu(add_to_group_menu, devices)
        
        # Add "Remove from Group" submenu
        remove_from_group_menu = menu.addMenu("Remove from Group")
        self._populate_remove_from_group_menu(remove_from_group_menu, devices)
        
        menu.addAction("Create Group from Selection", lambda: self._handle_action(self._on_action_create_group, devices))
        
        # SECTION 3: Device Creation and Import
        menu.addSeparator()
        menu.addAction("Add Device", lambda: self._handle_action(self._on_action_add_device, None))
        menu.addAction("Import Devices...", lambda: self._handle_action(self._on_action_import_devices, None))
        
        # SECTION 4: Selection Controls
        menu.addSeparator()
        menu.addAction("Select All", self._on_action_select_all)
        menu.addAction("Deselect All", self._on_action_deselect_all)
        
        # SECTION 5: Custom Plugin Actions (not duplicating existing ones)
        # Filter out registered actions we've already added directly
        built_in_actions = {
            "Add Device", "Import Devices...", "Edit Properties", 
            "Add to Group", "Remove from Group", "Create New Group", "Create Group from Selection",
            "Select All", "Deselect All", "Delete"
        }
        
        # Get filtered and sorted actions
        filtered_actions = []
        for name, callback, priority in self._context_menu_actions:
            if name not in built_in_actions:
                filtered_actions.append((name, callback, priority))
                
        if filtered_actions:
            menu.addSeparator()
            sorted_actions = sorted(filtered_actions, key=lambda x: x[2])
            
            for name, callback, _ in sorted_actions:
                # Create a closure that captures the current callback
                action = menu.addAction(name)
                # Create a local copy of the callback to ensure it's properly captured in the lambda
                local_callback = callback
                # Use the same _handle_action pattern for consistency with built-in actions
                action.triggered.connect(
                    lambda checked=False, cb=local_callback: self._handle_action(cb, devices)
                )
        
        # Emit signal for plugins to add to menu
        self.context_menu_requested.emit(devices, menu)
        
        # Show menu
        menu.exec(self.viewport().mapToGlobal(pos))

    def _handle_action(self, callback, devices):
        """Handle a context menu action"""
        # Special handling for actions that don't need device arguments
        if callback in [self._on_action_select_all, self._on_action_deselect_all]:
            callback()
            return
            
        if devices:
            # Check if devices is a list or a single device
            if isinstance(devices, list):
                if len(devices) == 1:
                    # Single device from a list
                    callback(devices[0])
                else:
                    # Multiple devices
                    callback(devices)
            else:
                # Single device (not in a list)
                callback(devices)
        else:
            # No device selected
            callback(None)

    def _on_action_edit_properties(self, device_or_devices):
        """Edit device properties"""
        # Check if we have a list of devices for multi-edit
        if isinstance(device_or_devices, list):
            if device_or_devices:
                logger.debug(f"Editing properties for {len(device_or_devices)} devices")
                self._edit_multiple_devices(device_or_devices)
            return
            
        # Single device edit
        device = device_or_devices
        if not device:
            return
            
        logger.debug(f"Editing properties for device: {device}")
        self.device_properties_dialog(device)
    
    def _edit_multiple_devices(self, devices):
        """Edit properties for multiple devices at once"""
        if not devices:
            return
            
        dialog = QDialog()
        dialog.setWindowTitle(f"Edit {len(devices)} Devices")
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Create tab widget for organizing properties
        tab_widget = QTabWidget()
        
        # Basic tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_form = QFormLayout()
        
        # Instructions
        info_label = QLabel("Edit properties for multiple devices. Empty fields will keep existing values.")
        basic_layout.addWidget(info_label)
        
        # Core property fields
        alias_edit = QLineEdit()
        alias_edit.setPlaceholderText("Leave empty to keep current values")
        basic_form.addRow("Alias:", alias_edit)
        
        hostname_edit = QLineEdit()
        hostname_edit.setPlaceholderText("Leave empty to keep current values")
        basic_form.addRow("Hostname:", hostname_edit)
        
        ip_edit = QLineEdit()
        ip_edit.setPlaceholderText("Leave empty to keep current values")
        basic_form.addRow("IP Address:", ip_edit)
        
        mac_edit = QLineEdit()
        mac_edit.setPlaceholderText("Leave empty to keep current values")
        basic_form.addRow("MAC Address:", mac_edit)
        
        status_combo = QComboBox()
        status_values = ["--Keep Current--", "unknown", "up", "down", "warning", "error", "maintenance"]
        status_combo.addItems(status_values)
        basic_form.addRow("Status:", status_combo)
        
        # Add the form to the basic tab
        basic_layout.addLayout(basic_form)
        tab_widget.addTab(basic_tab, "Basic")
        
        # Tags tab
        tags_tab = QWidget()
        tags_layout = QVBoxLayout(tags_tab)
        
        # Tag list
        tags_list = QListWidget()
        tags_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
            
        tags_layout.addWidget(QLabel("Add these tags to all selected devices:"))
        tags_layout.addWidget(tags_list)
        
        # Tag controls
        tags_control_layout = QHBoxLayout()
        new_tag = QLineEdit()
        new_tag.setPlaceholderText("New tag")
        add_tag_button = QPushButton("Add")
        remove_tag_button = QPushButton("Remove Selected")
        
        tags_control_layout.addWidget(new_tag)
        tags_control_layout.addWidget(add_tag_button)
        tags_control_layout.addWidget(remove_tag_button)
        
        tags_layout.addLayout(tags_control_layout)
        
        # Add tag function
        def add_tag():
            tag = new_tag.text().strip()
            if tag and not tags_list.findItems(tag, Qt.MatchExactly):
                tags_list.addItem(QListWidgetItem(tag))
                new_tag.clear()
                
        # Remove selected tags
        def remove_selected_tags():
            for item in reversed(tags_list.selectedItems()):
                row = tags_list.row(item)
                tags_list.takeItem(row)
                
        # Add tag filter function
        def filter_tags(text):
            filter_text = text.lower()
            for i in range(tags_list.count()):
                item = tags_list.item(i)
                item.setHidden(filter_text and filter_text not in item.text().lower())
                
        add_tag_button.clicked.connect(add_tag)
        remove_tag_button.clicked.connect(remove_selected_tags)
        tags_filter_edit.textChanged.connect(filter_tags)
        
        # Add enter key press to add tag
        def on_tag_return_pressed():
            if new_tag.text().strip():
                add_tag()
                
        new_tag.returnPressed.connect(on_tag_return_pressed)
        
        # Add tags tab to tab widget
        tab_widget.addTab(tags_tab, "Tags")
        
        # Add tab widget to dialog
        layout.addWidget(tab_widget)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        if dialog.exec():
            # Process the changes for all devices
            for device in devices:
                # Only update properties that were actually changed
                if alias_edit.text():
                    device.set_property("alias", alias_edit.text())
                    
                if hostname_edit.text():
                    device.set_property("hostname", hostname_edit.text())
                    
                if ip_edit.text():
                    device.set_property("ip_address", ip_edit.text())
                    
                if mac_edit.text():
                    device.set_property("mac_address", mac_edit.text())
                    
                if status_combo.currentIndex() > 0:  # Not --Keep Current--
                    device.set_property("status", status_combo.currentText())
                
                # Add new tags to the device
                current_tags = device.get_property("tags", [])
                for i in range(tags_list.count()):
                    tag = tags_list.item(i).text()
                    if tag not in current_tags:
                        current_tags.append(tag)
                device.set_property("tags", current_tags)
                
                # Notify of changes
                self.device_manager.device_changed.emit(device)

    def _on_action_delete(self, device_or_devices):
        """Delete the device(s)"""
        if not device_or_devices:
            return
                
        # Handle single device or list of devices
        devices = device_or_devices if isinstance(device_or_devices, list) else [device_or_devices]
        
        if len(devices) == 1:
            # Single device
            device = devices[0]
            result = QMessageBox.question(
                self, 
                "Confirm Deletion",
                f"Are you sure you want to delete device '{device.get_property('alias')}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.Yes:
                self.device_manager.remove_device(device)
        else:
            # Multiple devices
            result = QMessageBox.question(
                self, 
                "Confirm Deletion",
                f"Are you sure you want to delete {len(devices)} devices?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.Yes:
                for device in devices:
                    self.device_manager.remove_device(device)

    def _on_action_add_to_group(self, data):
        """Add device(s) to a group"""
        # Extract devices and group from data
        if isinstance(data, tuple) and len(data) == 2:
            devices, group = data
        else:
            logger.error(f"Invalid data format for add_to_group: {data}")
            return
            
        # Get list of devices
        if not isinstance(devices, list):
            devices = [devices]
            
        if not devices:
            return
            
        # Ask if user wants to auto-group by type
        auto_group = False
        if len(devices) > 1:
            reply = QMessageBox.question(
                self,
                "Auto-group by Type",
                "Would you like to automatically create subgroups based on device types?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            auto_group = (reply == QMessageBox.Yes)
        
        # Helper function to get the device type
        def get_device_type(device):
            # Use device_type property if it exists
            device_type = device.get_property("device_type", "")
            if not device_type:
                # Try to determine from other properties
                if device.get_property("is_switch", False) or device.get_property("is_router", False):
                    device_type = "network"
                elif device.get_property("is_server", False):
                    device_type = "server"
                elif device.get_property("is_workstation", False):
                    device_type = "workstation"
                elif device.get_property("is_printer", False):
                    device_type = "printer"
                else:
                    # Default fallback
                    device_type = "unknown"
            return device_type
        
        # Process devices
        added_count = 0
        
        if auto_group:
            # Group devices by type
            device_types = {}
            for device in devices:
                device_type = get_device_type(device)
                if device_type not in device_types:
                    device_types[device_type] = []
                device_types[device_type].append(device)
            
            # Process each type
            for device_type, type_devices in device_types.items():
                # Skip if no devices
                if not type_devices:
                    continue
                    
                # Create a subgroup for this type if it doesn't exist
                type_name = device_type.replace("_", " ").title()
                type_group_name = f"{group.name}: {type_name}"
                
                # Check if the subgroup already exists
                type_group = None
                for subgroup in group.subgroups:
                    if subgroup.name == type_group_name:
                        type_group = subgroup
                        break
                        
                # Create the subgroup if it doesn't exist
                if not type_group:
                    type_group = self.device_manager.create_group(
                        type_group_name,
                        f"Devices of type {type_name} in {group.name}",
                        group
                    )
                    
                # Add devices to the type group
                for device in type_devices:
                    if device not in type_group.devices:
                        self.device_manager.add_device_to_group(device, type_group)
                        added_count += 1
        else:
            # Add devices directly to the group
            for device in devices:
                if device not in group.devices:
                    self.device_manager.add_device_to_group(device, group)
                    added_count += 1
        
        # Save changes
        self.device_manager.save_devices()
        
        # Show a message to the user with the result
        if added_count > 0:
            QMessageBox.information(
                self, 
                "Devices Added",
                f"Added {added_count} device{'s' if added_count != 1 else ''} to group '{group.name}'."
            )
        else:
            QMessageBox.information(
                self,
                "No Changes",
                f"The selected device{'s' if len(devices) > 1 else ''} {'were' if len(devices) > 1 else 'was'} already in group '{group.name}'."
            )

    def _on_action_create_group(self, device_or_devices):
        """Create a new group with selected device(s)"""
        if not device_or_devices:
            return
            
        # Get list of devices
        devices = device_or_devices if isinstance(device_or_devices, list) else [device_or_devices]
        if not devices:
            return
            
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Group")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # Group name
        form = QFormLayout()
        group_name = QLineEdit()
        form.addRow("Group Name:", group_name)
        
        group_desc = QLineEdit()
        form.addRow("Description:", group_desc)
        
        # Parent group selection
        groups = self.device_manager.get_groups()
        parent_combo = QComboBox()
        for group in groups:
            parent_combo.addItem(group.name, group)
        form.addRow("Parent Group:", parent_combo)
        
        # Auto-group by device type
        auto_group_checkbox = QCheckBox("Auto-group by device type")
        auto_group_checkbox.setToolTip("Create subgroups based on device types")
        layout.addLayout(form)
        layout.addWidget(auto_group_checkbox)
        
        # Add dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        # Show dialog
        if dialog.exec():
            # Get dialog values
            name = group_name.text().strip()
            desc = group_desc.text().strip()
            parent = parent_combo.currentData()
            auto_group = auto_group_checkbox.isChecked()
            
            if not name:
                QMessageBox.warning(
                    self,
                    "Invalid Group Name",
                    "Please enter a valid group name."
                )
                return
                
            try:
                # Create new group
                group = self.device_manager.create_group(name, desc, parent)
                
                # Helper function to get the device type
                def get_device_type(device):
                    # Use device_type property if it exists
                    device_type = device.get_property("device_type", "")
                    if not device_type:
                        # Try to determine from other properties
                        if device.get_property("is_switch", False) or device.get_property("is_router", False):
                            device_type = "network"
                        elif device.get_property("is_server", False):
                            device_type = "server"
                        elif device.get_property("is_workstation", False):
                            device_type = "workstation"
                        elif device.get_property("is_printer", False):
                            device_type = "printer"
                        else:
                            # Default fallback
                            device_type = "unknown"
                    return device_type
                
                # Process each device
                added_devices = 0
                if auto_group:
                    # Group devices by type
                    device_types = {}
                    for device in devices:
                        device_type = get_device_type(device)
                        if device_type not in device_types:
                            device_types[device_type] = []
                        device_types[device_type].append(device)
                    
                    # Create subgroups for each type
                    for device_type, type_devices in device_types.items():
                        # Skip if no devices
                        if not type_devices:
                            continue
                            
                        # Create a subgroup for this type
                        type_name = device_type.replace("_", " ").title()
                        type_group_name = f"{name}: {type_name}"
                        type_group = self.device_manager.create_group(type_group_name, f"{desc} - {type_name}", group)
                        
                        # Add devices to this type group
                        for device in type_devices:
                            self.device_manager.add_device_to_group(device, type_group)
                            added_devices += 1
                else:
                    # Add all devices directly to the group
                    for device in devices:
                        self.device_manager.add_device_to_group(device, group)
                        added_devices += 1
                
                # Show result message
                QMessageBox.information(
                    self,
                    "Group Created",
                    f"Created group '{name}' with {added_devices} devices."
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error Creating Group",
                    f"An error occurred while creating the group: {str(e)}"
                )
                logger.error(f"Error creating group: {e}")
                # Raise the exception again to see the full stack trace in the console
                raise

    def _on_action_add_device(self, device):
        """Add a new device"""
        new_device = self.device_properties_dialog(None)
        if new_device:
            # Add to device manager
            self.device_manager.add_device(new_device)
            
    def _on_action_import_devices(self, device):
        """Import devices from a file"""
        # Find the DeviceTreeView to use its import dialog
        from .device_tree import DeviceTreeView
        
        tree_view = None
        
        # Try to find the tree view in the parent's children
        for widget in self.parent().findChildren(DeviceTreeView):
            tree_view = widget
            break
            
        # If not found, try searching the whole application
        if not tree_view:
            for widget in QApplication.instance().allWidgets():
                if isinstance(widget, DeviceTreeView):
                    tree_view = widget
                    break
                
        if tree_view:
            tree_view._show_import_dialog()
        else:
            QMessageBox.warning(
                self,
                "Import Devices",
                "Device import feature is currently unavailable. DeviceTreeView not found."
            )

    def _on_action_select_all(self):
        """Select all devices in the current view"""
        logger.debug("Selecting all visible devices")
        # Use the built-in selectAll method which will trigger selectionChanged
        self.selectAll()
            
    def _on_action_deselect_all(self):
        """Deselect all devices"""
        logger.debug("Deselecting all devices")
        # Clear the selection which will trigger selectionChanged
        self.selectionModel().clearSelection()

    def _populate_add_to_group_menu(self, menu, devices):
        """Populate the Add to Group submenu
        
        Args:
            menu: The QMenu to populate
            devices: List of devices to add to a group
        """
        # Get all groups
        groups = self.device_manager.get_groups()
        
        # Skip the root group (All Devices)
        groups = [g for g in groups if g != self.device_manager.root_group]
        
        if not groups:
            action = menu.addAction("No Groups Available")
            action.setEnabled(False)
            return
            
        # Create a copy of the devices list to avoid reference issues in the lambda
        devices_copy = devices.copy() if isinstance(devices, list) else [devices]
            
        # Add actions for each group
        for group in sorted(groups, key=lambda g: g.name):
            # Create a closure that captures the current group
            action = menu.addAction(group.name)
            # When triggered, this will call _on_action_add_to_group with the tuple (devices, group)
            action.triggered.connect(
                lambda checked=False, g=group, d=devices_copy: self._on_action_add_to_group((d, g))
            )

    def _populate_remove_from_group_menu(self, menu, devices):
        """Populate the Remove from Group submenu
        
        Args:
            menu: The QMenu to populate
            devices: List of devices to remove from their current groups
        """
        # Get all groups
        groups = self.device_manager.get_groups()
        
        # Skip the root group (All Devices)
        groups = [g for g in groups if g != self.device_manager.root_group]
        
        if not groups:
            action = menu.addAction("No Groups Available")
            action.setEnabled(False)
            return
            
        # Create a copy of the devices list to avoid reference issues in the lambda
        devices_copy = devices.copy() if isinstance(devices, list) else [devices]
            
        # Add actions for each group
        for group in sorted(groups, key=lambda g: g.name):
            # Create a closure that captures the current group
            action = menu.addAction(group.name)
            # When triggered, this will call _on_action_remove_from_group with the tuple (devices, group)
            action.triggered.connect(
                lambda checked=False, g=group, d=devices_copy: self._on_action_remove_from_group((d, g))
            )

    def _on_action_remove_from_group(self, data):
        """Remove devices from a group"""
        # Check if we got a tuple of (devices, group)
        if isinstance(data, tuple) and len(data) == 2:
            devices, group = data
            device_count = len(devices)
            logger.debug(f"Removing {device_count} devices from group '{group.name}'")
            
            # Remove each device from the group
            removed_count = 0
            for device in devices:
                # Only remove if in the group
                if device in group.devices:
                    self.device_manager.remove_device_from_group(device, group)
                    removed_count += 1
                else:
                    logger.debug(f"Device {device.get_property('alias', 'Unnamed')} not in group {group.name}")
            
            # Save after all devices are removed
            self.device_manager.save_devices()
            
            # Show a message to the user with the result
            from PySide6.QtWidgets import QMessageBox
            if removed_count > 0:
                QMessageBox.information(
                    self, 
                    "Devices Removed",
                    f"Removed {removed_count} device{'s' if removed_count != 1 else ''} from group '{group.name}'."
                )
            else:
                QMessageBox.information(
                    self,
                    "No Changes",
                    f"The selected device{'s' if device_count > 1 else ''} {'were' if device_count > 1 else 'was'} not in group '{group.name}'."
                )
            
            return
            
        # Legacy handling for backward compatibility
        device_or_devices = data
        
        # Multiple devices
        if isinstance(device_or_devices, list):
            devices = device_or_devices
        else:
            # Single device
            devices = [device_or_devices]
            
        # No devices to remove
        if not devices:
            return
            
        # Get all groups
        groups = [g for g in self.device_manager.get_groups() 
                 if g != self.device_manager.root_group]
                 
        if not groups:
            self.device_manager.create_group("New Group")
            groups = [g for g in self.device_manager.get_groups() 
                     if g != self.device_manager.root_group]
                     
        # Show group selection dialog
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Remove from Group")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # Header with device count
        header = QLabel(f"Select group to remove {len(devices)} device{'s' if len(devices) > 1 else ''} from:")
        layout.addWidget(header)
        
        # Group list
        list_widget = QListWidget()
        for group in sorted(groups, key=lambda g: g.name):
            list_widget.addItem(group.name)
            
        layout.addWidget(list_widget)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog
        if dialog.exec() == QDialog.Accepted:
            # Get selected group
            selected_item = list_widget.currentItem()
            if selected_item:
                group_name = selected_item.text()
                group = self.device_manager.get_group(group_name)
                
                if group:
                    removed_count = 0
                    for device in devices:
                        # Only remove if in the group
                        if device in group.devices:
                            self.device_manager.remove_device_from_group(device, group)
                            removed_count += 1
                            
                    self.device_manager.save_devices()
                    
                    # Show a message to the user with the result
                    if removed_count > 0:
                        QMessageBox.information(
                            self, 
                            "Devices Removed",
                            f"Removed {removed_count} device{'s' if removed_count != 1 else ''} from group '{group_name}'."
                        )
                    else:
                        QMessageBox.information(
                            self,
                            "No Changes",
                            f"The selected device{'s' if len(devices) > 1 else ''} {'were' if len(devices) > 1 else 'was'} not in group '{group_name}'."
                        )

    def on_selection_model_changed(self, selected, deselected):
        """Handle changes to the selection model
        
        This method synchronizes the Qt selection model with the device_manager selection
        """
        # Only respond to UI-driven selection changes if this was triggered by user interaction
        # not by programmatic selection changes
        if self._ignore_selection_changes:
            return

        # Get all currently selected model indices
        selected_indices = self.selectionModel().selectedRows()
        
        # Get corresponding devices
        selected_devices = []
        for index in selected_indices:
            device = index.data(Qt.UserRole)
            if device:
                selected_devices.append(device)
                
        # Determine what's been newly selected and deselected
        previously_selected = self.device_manager.get_selected_devices()
        
        # Log the operation
        logger.debug(f"Selection model changed: {len(selected_devices)} devices now selected in UI")
        
        # Update the device manager selection without triggering recursive updates
        self._sync_selection_to_device_manager(selected_devices)
        
    def _sync_selection_to_device_manager(self, selected_devices):
        """Sync the UI selection to the device manager
        
        This avoids recursive updates by directly setting the device_manager's selection
        """
        # Get currently selected devices in the manager
        currently_selected = self.device_manager.get_selected_devices()
        
        # Update the device manager's selection directly
        self.device_manager.selected_devices = selected_devices.copy()
        
        # Only emit the signal if the selection has actually changed
        if set(selected_devices) != set(currently_selected):
            self.device_manager.selection_changed.emit(selected_devices)
            logger.debug(f"Emitted selection_changed with {len(selected_devices)} devices")
            
            # Log names of selected devices for debugging
            if selected_devices:
                device_names = [d.get_property('alias', f'Device {d.id}') for d in selected_devices]
                logger.debug(f"Selected devices: {', '.join(device_names[:5])}" + 
                           (f" and {len(device_names) - 5} more" if len(device_names) > 5 else ""))