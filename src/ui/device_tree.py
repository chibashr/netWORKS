#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Device tree model and view for NetWORKS
"""

from loguru import logger
from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, Signal, Slot
from PySide6.QtWidgets import (QTreeView, QAbstractItemView, QMenu, QWidget,
                              QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                              QFileDialog, QLabel, QPushButton, QTextEdit,
                              QComboBox, QTableWidget, QTableWidgetItem, 
                              QHeaderView, QLineEdit, QFormLayout, QGroupBox,
                              QCheckBox, QWizard, QWizardPage, QMessageBox,
                              QDialogButtonBox, QInputDialog, QApplication,
                              QButtonGroup, QRadioButton, QPlainTextEdit)
from PySide6.QtGui import QIcon, QFont, QColor, QBrush
from ..core.device_manager import Device
import os

# Try to import optional dependencies for icons
try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False
    logger.debug("qtawesome not available - using fallback icons")


class DeviceTreeItem:
    """Item in the device tree"""
    
    def __init__(self, data, parent=None, device=None, group=None):
        """Initialize the tree item"""
        self.item_data = data
        self.parent_item = parent
        self.child_items = []
        self.device = device
        self.group = group
        
    def appendChild(self, item):
        """Add a child to this item"""
        self.child_items.append(item)
        
    def child(self, row):
        """Get a child item"""
        if row < 0 or row >= len(self.child_items):
            return None
        return self.child_items[row]
        
    def childCount(self):
        """Get the number of children"""
        return len(self.child_items)
        
    def columnCount(self):
        """Get the number of columns"""
        return len(self.item_data)
        
    def data(self, column):
        """Get data for a column"""
        if column < 0 or column >= len(self.item_data):
            return None
        return self.item_data[column]
        
    def parent(self):
        """Get parent item"""
        return self.parent_item
        
    def row(self):
        """Get row number"""
        if self.parent_item:
            try:
                return self.parent_item.child_items.index(self)
            except ValueError:
                # Item not found in parent's child list
                logger.debug(f"DeviceTreeItem not found in parent's child list: {self.item_data[0]}")
                return 0
        return 0
        
    def removeChild(self, row):
        """Remove a child item"""
        if row < 0 or row >= len(self.child_items):
            return False
        self.child_items.pop(row)
        return True
        
    def removeAllChildren(self):
        """Remove all child items"""
        self.child_items = []
        
    def findChild(self, device=None, group=None):
        """Find a child item by device or group"""
        if device:
            for child in self.child_items:
                if child.device and child.device.id == device.id:
                    return child
        elif group:
            for child in self.child_items:
                if child.group and child.group.name == group.name:
                    return child
        return None


class DeviceTreeModel(QAbstractItemModel):
    """Model for device tree"""
    
    def __init__(self, device_manager):
        """Initialize the model"""
        super().__init__()
        
        self.device_manager = device_manager
        
        # Create root item
        self.root_item = DeviceTreeItem(["Name", "ID"])
        
        # Connect to device manager signals
        self.device_manager.device_added.connect(self.on_device_added)
        self.device_manager.device_removed.connect(self.on_device_removed)
        self.device_manager.device_changed.connect(self.on_device_changed)
        self.device_manager.group_added.connect(self.on_group_added)
        self.device_manager.group_removed.connect(self.on_group_removed)
        self.device_manager.group_changed.connect(self.on_group_changed)
        
        # Initialize tree
        self.setup_model_data()
        
    def setup_model_data(self):
        """Set up the model data"""
        # Signal the model is about to be reset
        self.beginResetModel()
        
        # Reset the model data
        self._reset_model_data()
        
        # Signal the model has been reset
        self.endResetModel()
        
    def _reset_model_data(self):
        """Reset the model data without reset signals"""
        # Clear existing structure
        self.root_item.removeAllChildren()
        
        # Add root group (All Devices)
        root_group = self.device_manager.root_group
        self.add_group(root_group, self.root_item)
        
    def add_group(self, group, parent_item):
        """Add a group to the tree"""
        group_item = DeviceTreeItem([group.name, ""], parent_item, group=group)
        parent_item.appendChild(group_item)
        
        # Add devices in this group
        for device in group.devices:
            self.add_device(device, group_item)
            
        # Add subgroups recursively
        for subgroup in group.subgroups:
            self.add_group(subgroup, group_item)
            
        return group_item
        
    def add_device(self, device, parent_item):
        """Add a device to the tree"""
        # Display alias/hostname/IP in priority order
        display_name = device.get_property("alias", "") or device.get_property("hostname", "") or device.get_property("ip_address", "") or "Unnamed Device"
        device_item = DeviceTreeItem(
            [display_name, device.id],
            parent_item,
            device=device
        )
        parent_item.appendChild(device_item)
        return device_item
        
    def index(self, row, column, parent=QModelIndex()):
        """Create an index for an item"""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
            
        parent_item = self.get_item(parent)
        child_item = parent_item.child(row)
        
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()
        
    def parent(self, index):
        """Get parent index for an item"""
        if not index.isValid():
            return QModelIndex()
            
        child_item = self.get_item(index)
        parent_item = child_item.parent()
        
        if parent_item == self.root_item:
            return QModelIndex()
            
        try:
            return self.createIndex(parent_item.row(), 0, parent_item)
        except ValueError as e:
            # Log the error and return an invalid index
            logger.error(f"Error creating parent index: {e}")
            return QModelIndex()
            
    def rowCount(self, parent=QModelIndex()):
        """Get row count for a parent index"""
        parent_item = self.get_item(parent)
        return parent_item.childCount()
        
    def columnCount(self, parent=QModelIndex()):
        """Get column count for a parent index"""
        return self.root_item.columnCount()
        
    def data(self, index, role):
        """Get data for an index"""
        if not index.isValid():
            return None
            
        item = self.get_item(index)
        
        if role == Qt.DisplayRole:
            return item.data(index.column())
        elif role == Qt.UserRole:
            # Return the device or group object
            return item.device or item.group
        elif role == Qt.FontRole and item.group:
            # Make group names bold
            font = QFont()
            font.setBold(True)
            return font
        elif role == Qt.BackgroundRole and item.device:
            # Highlight selected devices
            if item.device in self.device_manager.get_selected_devices():
                return QBrush(QColor(240, 248, 255))  # Light blue
                
        return None
        
    def headerData(self, section, orientation, role):
        """Get header data"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.root_item.data(section)
        return None
        
    def flags(self, index):
        """Get flags for an index"""
        if not index.isValid():
            return Qt.NoItemFlags
            
        item = self.get_item(index)
        
        # Groups are not selectable
        if item.group:
            return Qt.ItemIsEnabled
            
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
    def get_item(self, index):
        """Get item for an index"""
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
                
        return self.root_item
        
    @Slot(object)
    def on_device_added(self, device):
        """Handle device added signal"""
        # Rebuild the model with proper reset signals
        self.beginResetModel()
        self._reset_model_data()
        self.endResetModel()
        
    @Slot(object)
    def on_device_removed(self, device):
        """Handle device removed signal"""
        # Rebuild the model with proper reset signals
        self.beginResetModel()
        self._reset_model_data()
        self.endResetModel()
        
    @Slot(object)
    def on_device_changed(self, device):
        """Handle device changed signal"""
        # Find the device in the tree and update just that item
        # instead of rebuilding the entire tree
        self._update_device_display(device)

    def _update_device_display(self, device):
        """Update a device's display in the tree without resetting the model"""
        # This method updates a device's display name without resetting the model
        
        # Find all instances of the device in the tree (it could be in multiple groups)
        self._update_device_in_item(self.root_item, device)

    def _update_device_in_item(self, item, device):
        """Update a device within a tree item and its children recursively"""
        # Check all children of this item
        for child in item.child_items:
            # If this child is the device we're looking for
            if child.device and child.device.id == device.id:
                # Update the display name in the data array
                display_name = device.get_property("alias", "") or device.get_property("hostname", "") or device.get_property("ip_address", "") or "Unnamed Device"
                child.item_data[0] = display_name
                
                # Get the model index for this item
                row = child.row()
                if row >= 0:
                    parent_index = self.createIndex(item.row(), 0, item) if item != self.root_item else QModelIndex()
                    index = self.index(row, 0, parent_index)
                    # Emit dataChanged signal to update the view
                    self.dataChanged.emit(index, index)
                
            # Recursively check this child's children if it's a group
            if child.group:
                self._update_device_in_item(child, device)
        
    @Slot(object)
    def on_group_added(self, group):
        """Handle group added signal"""
        # Rebuild the model with proper reset signals
        self.beginResetModel()
        self._reset_model_data()
        self.endResetModel()
        
    @Slot(object)
    def on_group_removed(self, group):
        """Handle group removed signal"""
        # Rebuild the model with proper reset signals
        self.beginResetModel()
        self._reset_model_data()
        self.endResetModel()

    @Slot(object)
    def on_group_changed(self, group):
        """Handle group changed signal - rebuild for now as group membership may have changed"""
        # Rebuild the model with proper reset signals
        self.beginResetModel()
        self._reset_model_data()
        self.endResetModel()


class DeviceTreeView(QTreeView):
    """Custom tree view for devices"""
    
    device_double_clicked = Signal(object)
    
    def __init__(self, device_manager):
        """Initialize the view"""
        super().__init__()
        
        self.device_manager = device_manager
        
        # Configure view
        self.setHeaderHidden(True)
        self.setExpandsOnDoubleClick(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Connect signals
        self.clicked.connect(self.on_item_clicked)
        self.doubleClicked.connect(self.on_item_double_clicked)
        self.customContextMenuRequested.connect(self.on_context_menu)
        
        # Expand root item
        self.expandToDepth(0)
        
    def refresh(self):
        """Refresh the device tree view to reflect current data"""
        # Get the model and reset its data
        model = self.model()
        if model and hasattr(model, 'setup_model_data'):
            model.setup_model_data()
        # Clear any selection
        self.clearSelection()
        # Re-expand root item
        self.expandToDepth(0)
        
    def on_item_clicked(self, index):
        """Handle item clicked"""
        if not index.isValid():
            return
            
        # Get selected indexes
        selection = self.selectionModel()
        selected_indexes = selection.selectedIndexes()
        
        # Only process indexes for the first column (to avoid duplicate processing)
        selected_indexes = [idx for idx in selected_indexes if idx.column() == 0]
        
        if not selected_indexes:
            return
            
        # Get selected devices
        selected_devices = []
        for idx in selected_indexes:
            item = idx.data(Qt.UserRole)
            if hasattr(item, 'id'):  # It's a device
                selected_devices.append(item)
                
        # Update device selection
        if selected_devices:
            modifiers = QApplication.keyboardModifiers()
            exclusive = modifiers != Qt.ControlModifier
            
            if exclusive:
                self.device_manager.clear_selection()
                
            for device in selected_devices:
                self.device_manager.select_device(device, exclusive=False)
            
    def on_item_double_clicked(self, index):
        """Handle item double clicked"""
        if not index.isValid():
            return
            
        item = index.data(Qt.UserRole)
        
        if hasattr(item, 'id'):  # It's a device
            self.device_double_clicked.emit(item)
        else:  # It's a group
            self._show_group_manager_dialog(item)
            
    def on_context_menu(self, position):
        """Handle context menu request"""
        index = self.indexAt(position)
        
        # Create context menu
        menu = QMenu(self)
        
        if index.isValid():
            item = index.data(Qt.UserRole)
            
            if hasattr(item, 'id'):  # It's a device
                # Device context menu
                action_properties = menu.addAction("Properties")
                action_delete = menu.addAction("Delete")
                
                # Show menu and handle result
                action = menu.exec_(self.viewport().mapToGlobal(position))
                
                if action == action_properties:
                    self.device_double_clicked.emit(item)
                elif action == action_delete:
                    self.device_manager.remove_device(item)
                    
            else:  # It's a group
                # Group context menu
                action_new_device = menu.addAction("New Device")
                action_new_group = menu.addAction("New Group")
                action_delete = menu.addAction("Delete Group")
                
                # Show menu and handle result
                action = menu.exec_(self.viewport().mapToGlobal(position))
                
                if action == action_new_device:
                    device = Device(name="New Device")
                    self.device_manager.add_device(device)
                    self.device_manager.add_device_to_group(device, item)
                elif action == action_new_group:
                    self.device_manager.create_group("New Group", parent_group=item)
                elif action == action_delete:
                    self.device_manager.remove_group(item)
        else:
            # Root level context menu
            action_new_group = menu.addAction("New Group")
            action_import_devices = menu.addAction("Import Devices...")
            
            # Show menu and handle result
            action = menu.exec_(self.viewport().mapToGlobal(position))
            
            if action == action_new_group:
                self.device_manager.create_group("New Group")
            elif action == action_import_devices:
                self._show_import_dialog()

    def _show_import_dialog(self):
        """Show dialog for importing devices"""
        from ..core.importer import DeviceImporter
        
        # Create an instance of the importer
        importer = DeviceImporter(self.device_manager)
        
        # Let the importer handle the import process through its run_import_wizard method
        importer.run_import_wizard(self)

    def _show_group_manager_dialog(self, group):
        """Show dialog for managing a group"""
        if not group:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Group: {group.name}")
        dialog.resize(700, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Properties tab
        properties_tab = QWidget()
        properties_layout = QVBoxLayout(properties_tab)
        
        # Group properties form
        form_layout = QFormLayout()
        
        # Name field
        name_edit = QLineEdit(group.name)
        form_layout.addRow("Name:", name_edit)
        
        # Description field
        description_edit = QTextEdit(group.description)
        form_layout.addRow("Description:", description_edit)
        
        # Parent group selection
        parent_label = QLabel("Parent Group:")
        parent_combo = QComboBox()
        
        # Get all groups except this one and its descendants
        def add_groups_to_combo(group_list, exclude_group):
            for g in group_list:
                if g != exclude_group:
                    # Check if g is not a descendant of exclude_group
                    is_descendant = False
                    parent = g.parent
                    while parent:
                        if parent == exclude_group:
                            is_descendant = True
                            break
                        parent = parent.parent
                            
                    if not is_descendant:
                        parent_combo.addItem(g.name, g)
        
        add_groups_to_combo(self.device_manager.get_groups(), group)
        
        # Select current parent
        if group.parent:
            index = parent_combo.findText(group.parent.name)
            if index >= 0:
                parent_combo.setCurrentIndex(index)
                
        form_layout.addRow(parent_label, parent_combo)
        
        properties_layout.addLayout(form_layout)
        tab_widget.addTab(properties_tab, "Properties")
        
        # Devices tab
        devices_tab = QWidget()
        devices_tab_layout = QVBoxLayout(devices_tab)
        
        # Create device table
        devices_table = QTableWidget()
        devices_table.setColumnCount(4)
        devices_table.setHorizontalHeaderLabels(["Alias", "Hostname", "IP Address", "Status"])
        devices_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        devices_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        devices_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Add devices to table
        devices_table.setRowCount(len(group.devices))
        for i, device in enumerate(group.devices):
            devices_table.setItem(i, 0, QTableWidgetItem(device.get_property("alias", "")))
            devices_table.setItem(i, 1, QTableWidgetItem(device.get_property("hostname", "")))
            devices_table.setItem(i, 2, QTableWidgetItem(device.get_property("ip_address", "")))
            devices_table.setItem(i, 3, QTableWidgetItem(device.get_property("status", "")))
            
        devices_tab_layout.addWidget(devices_table)
        
        # Device actions
        device_buttons_layout = QHBoxLayout()
        add_device_button = QPushButton("Add Device")
        remove_device_button = QPushButton("Remove Selected")
        
        device_buttons_layout.addWidget(add_device_button)
        device_buttons_layout.addWidget(remove_device_button)
        devices_tab_layout.addLayout(device_buttons_layout)
        
        # Add devices tab
        tab_widget.addTab(devices_tab, f"Devices ({len(group.devices)})")
        
        # Subgroups tab
        subgroups_tab = QWidget()
        subgroups_layout = QVBoxLayout(subgroups_tab)
        
        # Create subgroups table
        subgroups_table = QTableWidget()
        subgroups_table.setColumnCount(2)
        subgroups_table.setHorizontalHeaderLabels(["Name", "Devices"])
        subgroups_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        subgroups_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        subgroups_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        subgroups_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Add subgroups to table
        subgroups_table.setRowCount(len(group.subgroups))
        for i, subgroup in enumerate(group.subgroups):
            subgroups_table.setItem(i, 0, QTableWidgetItem(subgroup.name))
            subgroups_table.setItem(i, 1, QTableWidgetItem(str(len(subgroup.get_all_devices()))))
            
        subgroups_layout.addWidget(subgroups_table)
        
        # Subgroup actions
        subgroup_buttons_layout = QHBoxLayout()
        add_subgroup_button = QPushButton("Add Subgroup")
        remove_subgroup_button = QPushButton("Remove Selected")
        
        subgroup_buttons_layout.addWidget(add_subgroup_button)
        subgroup_buttons_layout.addWidget(remove_subgroup_button)
        subgroups_layout.addLayout(subgroup_buttons_layout)
        
        # Add subgroups tab
        tab_widget.addTab(subgroups_tab, f"Subgroups ({len(group.subgroups)})")
        
        # Add tab widget to dialog
        layout.addWidget(tab_widget)
        
        # Add action buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        
        # Connect signals
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        # Add device button
        def on_add_device():
            # Show device selector dialog
            device_dialog = QDialog(dialog)
            device_dialog.setWindowTitle("Add Devices to Group")
            device_dialog.resize(500, 400)
            
            device_dialog_layout = QVBoxLayout(device_dialog)
            
            # Get all devices not already in the group
            all_devices = self.device_manager.get_devices()
            available_devices = [d for d in all_devices if d not in group.devices]
            
            if not available_devices:
                QMessageBox.information(
                    dialog,
                    "No Devices Available",
                    "All devices are already in this group."
                )
                return
                
            # Create device list
            device_list = QTableWidget()
            device_list.setColumnCount(4)
            device_list.setHorizontalHeaderLabels(["Alias", "Hostname", "IP Address", "Status"])
            device_list.setSelectionBehavior(QAbstractItemView.SelectRows)
            device_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
            device_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
            device_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            # Add devices to list
            device_list.setRowCount(len(available_devices))
            for i, device in enumerate(available_devices):
                device_list.setItem(i, 0, QTableWidgetItem(device.get_property("alias", "")))
                device_list.setItem(i, 1, QTableWidgetItem(device.get_property("hostname", "")))
                device_list.setItem(i, 2, QTableWidgetItem(device.get_property("ip_address", "")))
                device_list.setItem(i, 3, QTableWidgetItem(device.get_property("status", "")))
                
                # Store device object in item
                device_list.item(i, 0).setData(Qt.UserRole, device)
                
            device_dialog_layout.addWidget(device_list)
            
            # Add buttons
            device_dialog_buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            device_dialog_layout.addWidget(device_dialog_buttons)
            
            device_dialog_buttons.accepted.connect(device_dialog.accept)
            device_dialog_buttons.rejected.connect(device_dialog.reject)
            
            if device_dialog.exec():
                # Get selected devices
                selected_rows = device_list.selectionModel().selectedRows()
                selected_devices = []
                
                for index in selected_rows:
                    device = device_list.item(index.row(), 0).data(Qt.UserRole)
                    selected_devices.append(device)
                    
                # Add devices to group
                for device in selected_devices:
                    self.device_manager.add_device_to_group(device, group)
                    
                # Refresh devices table
                devices_table.setRowCount(len(group.devices))
                for i, device in enumerate(group.devices):
                    devices_table.setItem(i, 0, QTableWidgetItem(device.get_property("alias", "")))
                    devices_table.setItem(i, 1, QTableWidgetItem(device.get_property("hostname", "")))
                    devices_table.setItem(i, 2, QTableWidgetItem(device.get_property("ip_address", "")))
                    devices_table.setItem(i, 3, QTableWidgetItem(device.get_property("status", "")))
                    
                # Update tab title
                tab_widget.setTabText(1, f"Devices ({len(group.devices)})")
                
        add_device_button.clicked.connect(on_add_device)
        
        # Remove device button
        def on_remove_device():
            # Get selected devices
            selected_rows = devices_table.selectionModel().selectedRows()
            if not selected_rows:
                return
                
            # Confirm removal
            result = QMessageBox.question(
                dialog,
                "Confirm Removal",
                f"Remove {len(selected_rows)} device(s) from group '{group.name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Get devices from table
                devices_to_remove = []
                for index in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                    row = index.row()
                    # Find device by alias
                    alias = devices_table.item(row, 0).text()
                    for device in group.devices:
                        if device.get_property("alias", "") == alias:
                            devices_to_remove.append(device)
                            break
                
                # Remove devices from group
                for device in devices_to_remove:
                    self.device_manager.remove_device_from_group(device, group)
                    
                # Refresh devices table
                devices_table.setRowCount(len(group.devices))
                for i, device in enumerate(group.devices):
                    devices_table.setItem(i, 0, QTableWidgetItem(device.get_property("alias", "")))
                    devices_table.setItem(i, 1, QTableWidgetItem(device.get_property("hostname", "")))
                    devices_table.setItem(i, 2, QTableWidgetItem(device.get_property("ip_address", "")))
                    devices_table.setItem(i, 3, QTableWidgetItem(device.get_property("status", "")))
                    
                # Update tab title
                tab_widget.setTabText(1, f"Devices ({len(group.devices)})")
                
        remove_device_button.clicked.connect(on_remove_device)
        
        # Add subgroup button
        def on_add_subgroup():
            # Show add subgroup dialog
            name, ok = QInputDialog.getText(
                dialog,
                "New Subgroup",
                "Enter name for new subgroup:"
            )
            
            if ok and name:
                # Check if group with this name already exists
                if self.device_manager.get_group(name):
                    QMessageBox.warning(
                        dialog,
                        "Group Already Exists",
                        f"A group named '{name}' already exists."
                    )
                    return
                    
                # Create new group
                new_group = self.device_manager.create_group(name, parent_group=group)
                
                # Refresh subgroups table
                subgroups_table.setRowCount(len(group.subgroups))
                for i, subgroup in enumerate(group.subgroups):
                    subgroups_table.setItem(i, 0, QTableWidgetItem(subgroup.name))
                    subgroups_table.setItem(i, 1, QTableWidgetItem(str(len(subgroup.get_all_devices()))))
                    
                # Update tab title
                tab_widget.setTabText(2, f"Subgroups ({len(group.subgroups)})")
                
        add_subgroup_button.clicked.connect(on_add_subgroup)
        
        # Remove subgroup button
        def on_remove_subgroup():
            # Get selected subgroups
            selected_rows = subgroups_table.selectionModel().selectedRows()
            if not selected_rows:
                return
                
            # Confirm removal
            result = QMessageBox.question(
                dialog,
                "Confirm Removal",
                f"Remove {len(selected_rows)} subgroup(s) from group '{group.name}'?\nThis will also remove all devices in these subgroups.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Get subgroups from table
                subgroups_to_remove = []
                for index in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                    row = index.row()
                    # Find subgroup by name
                    name = subgroups_table.item(row, 0).text()
                    for subgroup in group.subgroups:
                        if subgroup.name == name:
                            subgroups_to_remove.append(subgroup)
                            break
                
                # Remove subgroups
                for subgroup in subgroups_to_remove:
                    self.device_manager.remove_group(subgroup)
                    
                # Refresh subgroups table
                subgroups_table.setRowCount(len(group.subgroups))
                for i, subgroup in enumerate(group.subgroups):
                    subgroups_table.setItem(i, 0, QTableWidgetItem(subgroup.name))
                    subgroups_table.setItem(i, 1, QTableWidgetItem(str(len(subgroup.get_all_devices()))))
                    
                # Update tab title
                tab_widget.setTabText(2, f"Subgroups ({len(group.subgroups)})")
                
        remove_subgroup_button.clicked.connect(on_remove_subgroup)
        
        # Handle OK button
        if dialog.exec():
            # Update group properties
            new_name = name_edit.text().strip()
            new_description = description_edit.toPlainText()
            new_parent = parent_combo.currentData()
            
            # Update group
            if new_name != group.name:
                # Check if name is already used
                if self.device_manager.get_group(new_name):
                    QMessageBox.warning(
                        self,
                        "Group Name Exists",
                        f"A group named '{new_name}' already exists. Changes not saved."
                    )
                    return
                    
                group.name = new_name
                
            group.description = new_description
            
            # Update parent if changed
            if new_parent != group.parent:
                # Remove from current parent
                if group.parent:
                    group.parent.remove_subgroup(group)
                    
                # Add to new parent
                if new_parent:
                    new_parent.add_subgroup(group)
                    
                group.parent = new_parent
                
            # Notify of changes
            self.device_manager.group_changed.emit(group)