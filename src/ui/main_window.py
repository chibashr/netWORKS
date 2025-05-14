#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main window for NetWORKS
"""

import os
from loguru import logger
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QToolBar, QStatusBar, QMenuBar, QMenu, 
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeView, QFrame, QLabel, QToolButton, QPushButton, QTableView,
    QHeaderView, QAbstractItemView, QSizePolicy, QInputDialog, QLineEdit, QMessageBox, QDialog, QListWidget, QTableWidget, QTableWidgetItem
)
from PySide6.QtGui import QIcon, QAction, QFont, QKeySequence
from PySide6.QtCore import Qt, QSize, Signal, Slot, QModelIndex, QSettings
from PySide6.QtWidgets import QStyle

from .device_table import DeviceTableModel, DeviceTableView, QAbstractItemView
from .device_tree import DeviceTreeModel, DeviceTreeView
from .plugin_manager_dialog import PluginManagerDialog
from .log_panel import LogPanel


class MainWindow(QMainWindow):
    """Main window for NetWORKS"""
    
    def __init__(self, app):
        """Initialize the main window"""
        super().__init__()
        logger.debug("Initializing main window")
        
        self.app = app
        self.device_manager = app.device_manager
        self.plugin_manager = app.plugin_manager
        self.config = app.config
        
        # Set window properties
        self.updateWindowTitle()
        self.resize(1200, 800)
        
        # Initialize UI components
        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._create_statusbar()
        self._create_central_widget()
        self._create_dock_widgets()
        
        # Connect signals
        self._connect_signals()
        
        # Restore window state, size and position if available
        self._restore_window_state()
        
        logger.info("Main window initialized")
        
    def updateWindowTitle(self):
        """Update the window title to include current workspace"""
        app_version = self.app.get_version()
        workspace = self.device_manager.current_workspace
        self.setWindowTitle(f"NetWORKS v{app_version} - Workspace: {workspace}")
        
    def _create_actions(self):
        """Create actions for menus and toolbars"""
        # File menu actions
        self.action_new_device = QAction("New Device", self)
        self.action_new_device.setStatusTip("Create a new device")
        self.action_new_device.triggered.connect(self.on_new_device)
        
        self.action_new_group = QAction("New Group", self)
        self.action_new_group.setStatusTip("Create a new device group")
        self.action_new_group.triggered.connect(self.on_new_group)
        
        self.action_save = QAction("Save", self)
        self.action_save.setShortcut(QKeySequence.Save)
        self.action_save.setStatusTip("Save all devices")
        self.action_save.triggered.connect(self.on_save)
        
        # Workspace actions
        self.action_new_workspace = QAction("New Workspace", self)
        self.action_new_workspace.setStatusTip("Create a new workspace")
        self.action_new_workspace.triggered.connect(self.on_new_workspace)
        
        self.action_open_workspace = QAction("Open Workspace", self)
        self.action_open_workspace.setStatusTip("Open an existing workspace")
        self.action_open_workspace.triggered.connect(self.on_open_workspace)
        
        self.action_save_workspace = QAction("Save Workspace", self)
        self.action_save_workspace.setStatusTip("Save current workspace")
        self.action_save_workspace.triggered.connect(self.on_save_workspace)
        
        self.action_manage_workspaces = QAction("Manage Workspaces", self)
        self.action_manage_workspaces.setStatusTip("Manage workspaces")
        self.action_manage_workspaces.triggered.connect(self.on_manage_workspaces)
        
        self.action_exit = QAction("Exit", self)
        self.action_exit.setShortcut(QKeySequence.Quit)
        self.action_exit.setStatusTip("Exit the application")
        self.action_exit.triggered.connect(self.close)
        
        # Edit menu actions
        self.action_select_all = QAction("Select All", self)
        self.action_select_all.setShortcut(QKeySequence.SelectAll)
        self.action_select_all.setStatusTip("Select all devices")
        self.action_select_all.triggered.connect(self.on_select_all)
        
        self.action_deselect_all = QAction("Deselect All", self)
        self.action_deselect_all.setStatusTip("Deselect all devices")
        self.action_deselect_all.triggered.connect(self.on_deselect_all)
        
        self.action_delete = QAction("Delete", self)
        self.action_delete.setShortcut(QKeySequence.Delete)
        self.action_delete.setStatusTip("Delete selected devices")
        self.action_delete.triggered.connect(self.on_delete)
        
        # View menu actions
        self.action_refresh = QAction("Refresh", self)
        self.action_refresh.setShortcut(QKeySequence.Refresh)
        self.action_refresh.setStatusTip("Refresh device status")
        self.action_refresh.triggered.connect(self.on_refresh)
        
        # Tools menu actions
        self.action_plugin_manager = QAction("Plugin Manager", self)
        self.action_plugin_manager.setStatusTip("Manage plugins")
        self.action_plugin_manager.triggered.connect(self.on_plugin_manager)
        
        self.action_settings = QAction("Settings", self)
        self.action_settings.setShortcut(QKeySequence.Preferences)
        self.action_settings.setStatusTip("Configure application settings")
        self.action_settings.triggered.connect(self.on_settings)
        
        # Help menu actions
        self.action_documentation = QAction("Documentation", self)
        self.action_documentation.setStatusTip("View program documentation")
        self.action_documentation.triggered.connect(self.on_documentation)
        
        self.action_about = QAction("About", self)
        self.action_about.setStatusTip("About NetWORKS")
        self.action_about.triggered.connect(self.on_about)
        
        # Recycle bin action
        self.action_recycle_bin = QAction("Recycle Bin", self)
        try:
            from qtawesome import icon
            self.action_recycle_bin.setIcon(icon('fa5s.trash-restore'))
        except:
            # If qtawesome is not available, use a standard icon
            self.action_recycle_bin.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.action_recycle_bin.setStatusTip("View and restore deleted devices")
        self.action_recycle_bin.triggered.connect(self.on_recycle_bin)
        
    def _create_menus(self):
        """Create menu bar and menus"""
        self.menu_bar = self.menuBar()
        
        # File menu
        self.menu_file = self.menu_bar.addMenu("File")
        self.menu_file.addAction(self.action_new_device)
        self.menu_file.addAction(self.action_new_group)
        self.menu_file.addSeparator()
        
        # Workspace submenu
        self.menu_workspaces = self.menu_file.addMenu("Workspaces")
        self.menu_workspaces.addAction(self.action_new_workspace)
        self.menu_workspaces.addAction(self.action_open_workspace)
        self.menu_workspaces.addAction(self.action_save_workspace)
        self.menu_workspaces.addAction(self.action_manage_workspaces)
        
        # Add recycle bin action to the file menu
        self.menu_file.addAction(self.action_recycle_bin)
        
        self.menu_file.addAction(self.action_save)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)
        
        # Edit menu
        self.menu_edit = self.menu_bar.addMenu("Edit")
        self.menu_edit.addAction(self.action_select_all)
        self.menu_edit.addAction(self.action_deselect_all)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.action_delete)
        
        # View menu
        self.menu_view = self.menu_bar.addMenu("View")
        self.menu_view.addAction(self.action_refresh)
        
        # Tools menu
        self.menu_tools = self.menu_bar.addMenu("Tools")
        self.menu_tools.addAction(self.action_plugin_manager)
        self.menu_tools.addAction(self.action_settings)
        
        # Help menu
        self.menu_help = self.menu_bar.addMenu("Help")
        self.menu_help.addAction(self.action_documentation)
        self.menu_help.addAction(self.action_about)
        
        # Plugin menus (will be populated by plugins)
        self.plugin_menus = {}
        
    def _create_toolbar(self):
        """Create toolbar"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # Add actions to toolbar
        self.toolbar.addAction(self.action_new_device)
        self.toolbar.addAction(self.action_new_group)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_save)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_refresh)
        
    def _create_statusbar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Workspace indicator
        self.status_workspace = QLabel(f"Workspace: {self.device_manager.current_workspace}")
        self.status_bar.addWidget(self.status_workspace)
        
        # Spacer
        spacer_label = QLabel()
        spacer_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.status_bar.addWidget(spacer_label)
        
        self.status_device_count = QLabel("0 devices")
        self.status_bar.addPermanentWidget(self.status_device_count)
        
        self.status_selection = QLabel("0 selected")
        self.status_bar.addPermanentWidget(self.status_selection)
        
        self.status_bar.showMessage("Ready")
        
    def _create_central_widget(self):
        """Create central widget with device table"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create device table (without splitter now)
        self.device_table = DeviceTableView(self.device_manager)
        self.main_layout.addWidget(self.device_table.get_container_widget())
        
    def _create_dock_widgets(self):
        """Create dock widgets"""
        # Device tree dock widget (left panel)
        self.dock_device_tree = QDockWidget("Devices", self)
        self.dock_device_tree.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Create device tree
        self.device_tree_model = DeviceTreeModel(self.device_manager)
        self.device_tree = DeviceTreeView(self.device_manager)
        self.device_tree.setModel(self.device_tree_model)
        
        self.dock_device_tree.setWidget(self.device_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_device_tree)
        
        # Properties dock widget (right panel)
        self.dock_properties = QDockWidget("Properties", self)
        self.dock_properties.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Create properties panel
        self.properties_widget = QTabWidget()
        
        # Details tab
        self.details_tab = QWidget()
        self.details_layout = QVBoxLayout(self.details_tab)
        
        # Create a form layout for properties
        from PySide6.QtWidgets import QFormLayout, QScrollArea
        
        self.properties_scroll = QScrollArea()
        self.properties_scroll.setWidgetResizable(True)
        self.properties_form_widget = QWidget()
        self.properties_form_widget.setStyleSheet("background-color: white;")
        self.properties_form = QFormLayout(self.properties_form_widget)
        
        self.property_labels = {}
        for prop in ["alias", "hostname", "ip_address", "mac_address", "status"]:
            self.property_labels[prop] = QLabel("--")
            self.properties_form.addRow(f"{prop.replace('_', ' ').title()}:", self.property_labels[prop])
            
        # Add notes field
        self.notes_label = QLabel("--")
        self.notes_label.setWordWrap(True)
        self.properties_form.addRow("Notes:", self.notes_label)
        
        # Custom properties section
        self.custom_props_label = QLabel("Custom Properties")
        self.custom_props_label.setFont(QFont("", 10, QFont.Bold))
        self.properties_form.addRow(self.custom_props_label)
        
        # Space for custom properties (will be filled dynamically)
        self.custom_props_layout = QFormLayout()
        self.properties_form.addRow(self.custom_props_layout)
        
        self.properties_scroll.setWidget(self.properties_form_widget)
        self.details_layout.addWidget(self.properties_scroll)
        
        self.properties_widget.addTab(self.details_tab, "Details")
        
        # Additional tabs will be added by plugins
        
        self.dock_properties.setWidget(self.properties_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_properties)
        
        # Log dock widget (bottom panel)
        self.dock_log = QDockWidget("Log", self)
        self.dock_log.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        
        # Use LogPanel in the dock widget
        self.log_panel = LogPanel()
        self.dock_log.setWidget(self.log_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_log)
        
    def _connect_signals(self):
        """Connect signals from device manager and plugin manager"""
        # Device manager signals
        self.device_manager.device_added.connect(self.on_device_added)
        self.device_manager.device_removed.connect(self.on_device_removed)
        self.device_manager.device_changed.connect(self.on_device_changed)
        self.device_manager.group_added.connect(self.on_group_added)
        self.device_manager.group_removed.connect(self.on_group_removed)
        self.device_manager.selection_changed.connect(self.on_selection_changed)
        
        # Plugin manager signals
        self.plugin_manager.plugin_loaded.connect(self.on_plugin_loaded)
        self.plugin_manager.plugin_unloaded.connect(self.on_plugin_unloaded)
        
    def update_status_bar(self):
        """Update status bar with current counts"""
        device_count = len(self.device_manager.get_devices())
        self.status_device_count.setText(f"{device_count} device{'s' if device_count != 1 else ''}")
        
        selection_count = len(self.device_manager.get_selected_devices())
        self.status_selection.setText(f"{selection_count} selected")
        
    def add_plugin_ui_components(self, plugin_info):
        """Add UI components from a plugin"""
        if not plugin_info.instance:
            return
            
        plugin = plugin_info.instance
        
        # Add toolbar actions
        toolbar_actions = plugin.get_toolbar_actions()
        if toolbar_actions:
            self.toolbar.addSeparator()
            for action in toolbar_actions:
                self.toolbar.addAction(action)
                
        # Add menu actions
        menu_actions = plugin.get_menu_actions()
        for menu_name, actions in menu_actions.items():
            # Create the menu if it doesn't exist
            if menu_name not in self.plugin_menus:
                self.plugin_menus[menu_name] = self.menu_bar.addMenu(menu_name)
                
            # Add actions to the menu
            for action in actions:
                self.plugin_menus[menu_name].addAction(action)
                
        # Add device panels to properties widget
        device_panels = plugin.get_device_panels()
        for panel_name, widget in device_panels:
            self.properties_widget.addTab(widget, panel_name)
            
        # Add dock widgets
        dock_widgets = plugin.get_dock_widgets()
        for widget_name, widget, area in dock_widgets:
            dock = QDockWidget(widget_name, self)
            dock.setWidget(widget)
            self.addDockWidget(area, dock)
            
    def remove_plugin_ui_components(self, plugin_info):
        """Remove UI components from a plugin"""
        # This method is more complex because we need to keep track of 
        # which components belong to which plugin. For a simple demo,
        # we'll just leave this as a stub.
        logger.debug(f"Removing UI components for plugin: {plugin_info}")
        
    def update_property_panel(self, devices=None):
        """Update property panel with device info
        
        Args:
            devices: A list of selected devices or None if no selection
        """
        # Clear custom properties
        while self.custom_props_layout.count():
            item = self.custom_props_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Convert single device to list for consistent handling
        if devices and not isinstance(devices, list):
            devices = [devices]
                
        # Hide custom properties section if no devices selected
        no_selection = not devices or len(devices) == 0
        self.custom_props_label.setVisible(not no_selection)
        
        if no_selection:
            # Reset all fields when no devices are selected
            for label in self.property_labels.values():
                label.setText("--")
            self.notes_label.setText("--")
            logger.debug("No devices selected, cleared property panel")
            return
            
        if len(devices) == 1:
            # Single device selection - show all properties
            device = devices[0]
            logger.debug(f"Showing properties for single device: {device.get_property('alias', 'Unnamed')}")
            
            # Update core properties
            for prop, label in self.property_labels.items():
                label.setText(str(device.get_property(prop, "--")))
                
            # Update notes
            self.notes_label.setText(device.get_property("notes", "--"))
            
            # Add custom properties
            core_props = ["id", "alias", "hostname", "ip_address", "mac_address", "status", "notes", "tags"]
            for key, value in device.get_properties().items():
                if key not in core_props:
                    # Add custom property to the form
                    if isinstance(value, (list, dict)):
                        value = str(value)
                    label = QLabel(str(value))
                    label.setWordWrap(True)
                    self.custom_props_layout.addRow(f"{key.replace('_', ' ').title()}:", label)
        else:
            # Multiple device selection - show common properties
            logger.debug(f"Showing properties for {len(devices)} devices")
            
            # Get device names for better logging
            device_names = [d.get_property('alias', f'Device {d.id}') for d in devices]
            logger.debug(f"Multiple devices selected: {', '.join(device_names[:5])}" + 
                       (f" and {len(device_names) - 5} more" if len(device_names) > 5 else ""))
            
            # Collect all properties from all devices
            all_properties = {}
            common_properties = {}
            core_props = ["id", "alias", "hostname", "ip_address", "mac_address", "status", "notes", "tags"]
            
            # First, gather all properties and their values
            for device in devices:
                for key, value in device.get_properties().items():
                    if key not in all_properties:
                        all_properties[key] = []
                    
                    # Convert complex types to string for comparison
                    if isinstance(value, (list, dict)):
                        value = str(value)
                        
                    all_properties[key].append(value)
            
            # Update core properties - show common value or "Multiple values"
            for prop, label in self.property_labels.items():
                if prop in all_properties:
                    values = all_properties[prop]
                    if len(set(values)) == 1:  # All values are the same
                        label.setText(str(values[0]))
                    else:
                        label.setText("<Multiple values>")
                else:
                    label.setText("--")
            
            # Update notes - show if they're all the same, otherwise indicate multiple values
            if "notes" in all_properties:
                notes_values = all_properties["notes"]
                if len(set(notes_values)) == 1:
                    self.notes_label.setText(notes_values[0])
                else:
                    self.notes_label.setText("<Multiple values>")
            else:
                self.notes_label.setText("--")
            
            # Add custom properties (excluding core properties)
            for key, values in all_properties.items():
                if key not in core_props:
                    if len(set(values)) == 1:  # All values are the same
                        label = QLabel(str(values[0]))
                    else:
                        label = QLabel("<Multiple values>")
                        
                    label.setWordWrap(True)
                    self.custom_props_layout.addRow(f"{key.replace('_', ' ').title()}:", label)
        
    # Event handlers
    
    @Slot()
    def on_new_device(self):
        """Create a new device"""
        logger.debug("Creating new device")
        
        # Use the device table's properties dialog to add a new device
        device_table = self.findChild(DeviceTableView)
        if device_table:
            device_table._on_action_add_device(None)
        else:
            # Fallback if the device table is not found
            from ..core.device_manager import Device
            device = Device(name="New Device")
            self.device_manager.add_device(device)
        
    @Slot()
    def on_new_group(self):
        """Create a new device group"""
        logger.debug("Creating new group")
        self.device_manager.create_group("New Group")
        
    @Slot()
    def on_save(self):
        """Save all devices"""
        logger.debug("Saving devices")
        self.device_manager.save_devices()
        self.status_bar.showMessage("Devices saved", 3000)
        
    @Slot()
    def on_select_all(self):
        """Select all devices"""
        logger.debug("Selecting all devices")
        devices = self.device_manager.get_devices()
        if devices:
            for device in devices:
                self.device_manager.select_device(device, exclusive=False)
                
    @Slot()
    def on_deselect_all(self):
        """Deselect all devices"""
        logger.debug("Deselecting all devices")
        self.device_manager.clear_selection()
        
    @Slot()
    def on_delete(self):
        """Delete selected devices"""
        selected_devices = self.device_manager.get_selected_devices()
        logger.debug(f"Deleting {len(selected_devices)} selected devices")
        
        for device in selected_devices.copy():
            self.device_manager.remove_device(device)
            
    @Slot()
    def on_refresh(self):
        """Refresh device status"""
        logger.debug("Refreshing devices")
        self.device_manager.refresh_devices()
        self.status_bar.showMessage("Devices refreshed", 3000)
        
    @Slot()
    def on_plugin_manager(self):
        """Open plugin manager dialog"""
        logger.debug("Opening plugin manager")
        dialog = PluginManagerDialog(self.plugin_manager, self)
        dialog.exec()
        
    @Slot()
    def on_settings(self):
        """Open settings dialog"""
        logger.debug("Opening settings dialog")
        # This will be implemented later or by a plugin
        self.status_bar.showMessage("Settings dialog not implemented yet", 3000)
        
    @Slot()
    def on_new_workspace(self):
        """Create a new workspace"""
        logger.debug("Creating new workspace")
        from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
        
        name, ok = QInputDialog.getText(
            self, "New Workspace", "Enter workspace name:", 
            QLineEdit.Normal, ""
        )
        
        if ok and name:
            description, _ = QInputDialog.getText(
                self, "Workspace Description", "Enter description (optional):", 
                QLineEdit.Normal, ""
            )
            
            success = self.device_manager.create_workspace(name, description)
            if success:
                # Ask if user wants to switch to new workspace
                response = QMessageBox.question(
                    self, "Switch Workspace",
                    f"Workspace '{name}' created. Switch to it now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if response == QMessageBox.Yes:
                    self.device_manager.load_workspace(name)
                    # Update UI with new workspace
                    self.updateWindowTitle()
                    self.status_workspace.setText(f"Workspace: {self.device_manager.current_workspace}")
                    self.status_bar.showMessage(f"Switched to workspace: {name}", 3000)
                    
                    # Refresh UI components to reflect the new workspace
                    if hasattr(self, "device_table"):
                        self.device_table.refresh()
                    if hasattr(self, "device_panel"):
                        self.device_panel.refresh()
                    if hasattr(self, "device_tree"):
                        self.device_tree.refresh()
                        
                    # Update device count in status bar
                    self.update_status_bar()
                else:
                    self.status_bar.showMessage(f"Created workspace: {name}", 3000)
            else:
                self.status_bar.showMessage(f"Failed to create workspace: {name}", 3000)
    
    @Slot()
    def on_open_workspace(self):
        """Open an existing workspace"""
        logger.debug("Opening workspace")
        from PySide6.QtWidgets import QInputDialog
        
        workspaces = self.device_manager.list_workspaces()
        if not workspaces:
            self.status_bar.showMessage("No workspaces available", 3000)
            return
            
        workspace_names = [w.get("name", "Unknown") for w in workspaces]
        
        name, ok = QInputDialog.getItem(
            self, "Open Workspace", "Select workspace:", 
            workspace_names, 0, False
        )
        
        if ok and name:
            # Save current workspace before switching
            self.device_manager.save_workspace()
            
            # Load selected workspace
            success = self.device_manager.load_workspace(name)
            if success:
                # Update UI with new workspace
                self.updateWindowTitle()
                self.status_workspace.setText(f"Workspace: {self.device_manager.current_workspace}")
                self.status_bar.showMessage(f"Switched to workspace: {name}", 3000)
                
                # Refresh UI components to reflect the new workspace
                if hasattr(self, "device_table"):
                    self.device_table.refresh()
                if hasattr(self, "device_panel"):
                    self.device_panel.refresh()
                if hasattr(self, "device_tree"):
                    self.device_tree.refresh()
                    
                # Update device count in status bar
                self.update_status_bar()
            else:
                self.status_bar.showMessage(f"Failed to load workspace: {name}", 3000)
    
    @Slot()
    def on_save_workspace(self):
        """Save current workspace"""
        logger.debug("Saving workspace")
        success = self.device_manager.save_workspace()
        if success:
            self.status_bar.showMessage(f"Workspace saved: {self.device_manager.current_workspace}", 3000)
        else:
            self.status_bar.showMessage("Failed to save workspace", 3000)
    
    @Slot()
    def on_manage_workspaces(self):
        """Manage workspaces"""
        logger.debug("Managing workspaces")
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Workspaces")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # List of workspaces
        list_widget = QListWidget()
        layout.addWidget(QLabel("Available Workspaces:"))
        layout.addWidget(list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        delete_button = QPushButton("Delete")
        switch_button = QPushButton("Switch")
        close_button = QPushButton("Close")
        
        button_layout.addWidget(delete_button)
        button_layout.addWidget(switch_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        # Load workspaces
        workspaces = self.device_manager.list_workspaces()
        for workspace in workspaces:
            name = workspace.get("name", "Unknown")
            description = workspace.get("description", "")
            display_text = f"{name} - {description}" if description else name
            list_widget.addItem(display_text)
            
        # Select current workspace
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.text().startswith(self.device_manager.current_workspace):
                list_widget.setCurrentItem(item)
                break
        
        # Connect buttons
        def on_delete():
            current_item = list_widget.currentItem()
            if current_item:
                name = current_item.text().split(" - ")[0]
                if name == "default":
                    self.status_bar.showMessage("Cannot delete default workspace", 3000)
                    return
                    
                response = QMessageBox.question(
                    dialog, "Confirm Deletion",
                    f"Are you sure you want to delete workspace '{name}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if response == QMessageBox.Yes:
                    success = self.device_manager.delete_workspace(name)
                    if success:
                        list_widget.takeItem(list_widget.currentRow())
                        self.status_bar.showMessage(f"Deleted workspace: {name}", 3000)
                    else:
                        self.status_bar.showMessage(f"Failed to delete workspace: {name}", 3000)
        
        def on_switch():
            current_item = list_widget.currentItem()
            if current_item:
                name = current_item.text().split(" - ")[0]
                if name != self.device_manager.current_workspace:
                    # Save current workspace before switching
                    self.device_manager.save_workspace()
                    
                    # Load selected workspace
                    success = self.device_manager.load_workspace(name)
                    if success:
                        # Update UI with new workspace
                        self.updateWindowTitle()
                        self.status_workspace.setText(f"Workspace: {self.device_manager.current_workspace}")
                        self.status_bar.showMessage(f"Switched to workspace: {name}", 3000)
                        
                        # Refresh UI components to reflect the new workspace
                        if hasattr(self, "device_table"):
                            self.device_table.refresh()
                        if hasattr(self, "device_panel"):
                            self.device_panel.refresh()
                        if hasattr(self, "device_tree"):
                            self.device_tree.refresh()
                            
                        # Update device count in status bar
                        self.update_status_bar()
                        dialog.accept()
                    else:
                        self.status_bar.showMessage(f"Failed to load workspace: {name}", 3000)
        
        delete_button.clicked.connect(on_delete)
        switch_button.clicked.connect(on_switch)
        close_button.clicked.connect(dialog.accept)
        
        dialog.exec()
        
    @Slot()
    def on_recycle_bin(self):
        """Handle recycle bin action"""
        logger.debug("Opening recycle bin")
        
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
            QTableWidgetItem, QHeaderView, QPushButton, QMessageBox
        )
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Recycle Bin")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Get devices from recycle bin
        recycled_devices = self.device_manager.get_recycle_bin_devices()
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel(f"Recycle Bin - {len(recycled_devices)} deleted device(s)")
        header_layout.addWidget(header_label)
        
        # Add a spacer to push buttons to the right
        from PySide6.QtWidgets import QSpacerItem, QSizePolicy
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        header_layout.addItem(spacer)
        
        # Add refresh button
        refresh_button = QPushButton("Refresh")
        header_layout.addWidget(refresh_button)
        
        layout.addLayout(header_layout)
        
        # Create table for devices
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Alias", "Hostname", "IP Address", "Status", "Groups"])
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)
        
        # Add devices to table
        table.setRowCount(len(recycled_devices))
        for i, device in enumerate(recycled_devices):
            table.setItem(i, 0, QTableWidgetItem(device.get_property("alias", "")))
            table.setItem(i, 1, QTableWidgetItem(device.get_property("hostname", "")))
            table.setItem(i, 2, QTableWidgetItem(device.get_property("ip_address", "")))
            table.setItem(i, 3, QTableWidgetItem(device.get_property("status", "")))
            
            # Groups column shows the groups this device was in before deletion
            groups = device.get_property("_recycled_groups", [])
            table.setItem(i, 4, QTableWidgetItem(", ".join(groups)))
            
            # Store device object in first column's item
            table.item(i, 0).setData(Qt.UserRole, device)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        restore_button = QPushButton("Restore Selected")
        restore_all_button = QPushButton("Restore All")
        delete_button = QPushButton("Delete Selected Permanently")
        empty_button = QPushButton("Empty Recycle Bin")
        
        button_layout.addWidget(restore_button)
        button_layout.addWidget(restore_all_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(empty_button)
        
        layout.addLayout(button_layout)
        
        # Enable buttons only if there are devices
        has_devices = len(recycled_devices) > 0
        restore_all_button.setEnabled(has_devices)
        empty_button.setEnabled(has_devices)
        
        # Handle refresh
        def refresh_table():
            recycled_devices = self.device_manager.get_recycle_bin_devices()
            header_label.setText(f"Recycle Bin - {len(recycled_devices)} deleted device(s)")
            
            table.setRowCount(len(recycled_devices))
            for i, device in enumerate(recycled_devices):
                table.setItem(i, 0, QTableWidgetItem(device.get_property("alias", "")))
                table.setItem(i, 1, QTableWidgetItem(device.get_property("hostname", "")))
                table.setItem(i, 2, QTableWidgetItem(device.get_property("ip_address", "")))
                table.setItem(i, 3, QTableWidgetItem(device.get_property("status", "")))
                
                # Groups column shows the groups this device was in before deletion
                groups = device.get_property("_recycled_groups", [])
                table.setItem(i, 4, QTableWidgetItem(", ".join(groups)))
                
                # Store device object in first column's item
                table.item(i, 0).setData(Qt.UserRole, device)
                
            # Update button state
            has_devices = len(recycled_devices) > 0
            restore_all_button.setEnabled(has_devices)
            empty_button.setEnabled(has_devices)
        
        # Handle restore button
        def restore_selected():
            selected_rows = table.selectionModel().selectedRows()
            if not selected_rows:
                return
                
            devices_to_restore = []
            for index in selected_rows:
                device = table.item(index.row(), 0).data(Qt.UserRole)
                devices_to_restore.append(device)
                
            if devices_to_restore:
                for device in devices_to_restore:
                    self.device_manager.restore_device(device)
                    
                count = len(devices_to_restore)
                QMessageBox.information(
                    dialog,
                    "Devices Restored",
                    f"{count} device{'s' if count != 1 else ''} restored from the recycle bin."
                )
                refresh_table()
        
        # Handle restore all button
        def restore_all():
            if not recycled_devices:
                return
                
            self.device_manager.restore_all_devices()
            QMessageBox.information(
                dialog,
                "All Devices Restored",
                f"All {len(recycled_devices)} device{'s' if len(recycled_devices) != 1 else ''} restored from the recycle bin."
            )
            refresh_table()
        
        # Handle delete button
        def delete_selected():
            selected_rows = table.selectionModel().selectedRows()
            if not selected_rows:
                return
                
            devices_to_delete = []
            for index in selected_rows:
                device = table.item(index.row(), 0).data(Qt.UserRole)
                devices_to_delete.append(device)
                
            if devices_to_delete:
                count = len(devices_to_delete)
                result = QMessageBox.question(
                    dialog,
                    "Confirm Permanent Deletion",
                    f"Are you sure you want to permanently delete {count} device{'s' if count != 1 else ''}?\nThis action cannot be undone.",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if result == QMessageBox.Yes:
                    for device in devices_to_delete:
                        self.device_manager.permanently_delete_device(device)
                        
                    QMessageBox.information(
                        dialog,
                        "Devices Deleted",
                        f"{count} device{'s' if count != 1 else ''} permanently deleted."
                    )
                    refresh_table()
        
        # Handle empty button
        def empty_recycle_bin():
            if not recycled_devices:
                return
                
            result = QMessageBox.question(
                dialog,
                "Confirm Empty Recycle Bin",
                f"Are you sure you want to permanently delete all {len(recycled_devices)} device{'s' if len(recycled_devices) != 1 else ''} in the recycle bin?\nThis action cannot be undone.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                self.device_manager.empty_recycle_bin()
                QMessageBox.information(
                    dialog,
                    "Recycle Bin Emptied",
                    "All devices have been permanently deleted."
                )
                refresh_table()
        
        # Connect signals
        refresh_button.clicked.connect(refresh_table)
        restore_button.clicked.connect(restore_selected)
        restore_all_button.clicked.connect(restore_all)
        delete_button.clicked.connect(delete_selected)
        empty_button.clicked.connect(empty_recycle_bin)
        
        # Enable restore and delete buttons only when items are selected
        def on_selection_changed():
            has_selection = len(table.selectionModel().selectedRows()) > 0
            restore_button.setEnabled(has_selection)
            delete_button.setEnabled(has_selection)
        
        table.selectionModel().selectionChanged.connect(on_selection_changed)
        on_selection_changed()  # Initial state
        
        # Show dialog
        dialog.exec()
        
    @Slot()
    def on_documentation(self):
        """Show the documentation dialog"""
        from .documentation_dialog import DocumentationDialog
        dialog = DocumentationDialog(self)
        dialog.exec()
        
    @Slot()
    def on_about(self):
        """Show the about dialog"""
        from .about_dialog import AboutDialog
        dialog = AboutDialog(self.app, self)
        dialog.exec()
        
    # Signal handlers
    
    @Slot(object)
    def on_device_added(self, device):
        """Handle device added signal"""
        logger.debug(f"Device added: {device}")
        self.update_status_bar()
        
    @Slot(object)
    def on_device_removed(self, device):
        """Handle device removed signal"""
        logger.debug(f"Device removed: {device}")
        self.update_status_bar()
        
    @Slot(object)
    def on_device_changed(self, device):
        """Handle device changed signal"""
        logger.debug(f"Device changed: {device}")
        
    @Slot(object)
    def on_group_added(self, group):
        """Handle group added signal"""
        logger.debug(f"Group added: {group}")
        
    @Slot(object)
    def on_group_removed(self, group):
        """Handle group removed signal"""
        logger.debug(f"Group removed: {group}")
        
    @Slot(list)
    def on_selection_changed(self, devices):
        """Handle selection changed signal"""
        logger.debug(f"Selection changed: {len(devices)} devices selected")
        self.update_status_bar()
        
        # Pass all selected devices to the property panel
        self.update_property_panel(devices)
        
    @Slot(object)
    def on_plugin_loaded(self, plugin_info):
        """Handle plugin loaded signal"""
        logger.debug(f"Plugin loaded: {plugin_info}")
        self.add_plugin_ui_components(plugin_info)
        
    @Slot(object)
    def on_plugin_unloaded(self, plugin_info):
        """Handle plugin unloaded signal"""
        logger.debug(f"Plugin unloaded: {plugin_info}")
        self.remove_plugin_ui_components(plugin_info)
        
    def closeEvent(self, event):
        """Save window state and size on close"""
        # Save window state, position and size
        settings = QSettings(self.app.applicationName(), "WindowState")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("size", self.size())
        settings.setValue("pos", self.pos())
        logger.debug("Window state and position saved")
        
        # Save the current workspace
        self.device_manager.save_workspace()
        
        # Unload all plugins
        self.plugin_manager.unload_all_plugins()
        
        # Accept the event
        event.accept()
        
    def _restore_window_state(self):
        """Restore window state from settings"""
        try:
            settings = QSettings(self.app.applicationName(), "WindowState")
            # Restore geometry if available
            if settings.contains("geometry"):
                self.restoreGeometry(settings.value("geometry"))
                logger.debug("Window geometry restored")
            
            # Restore window state (dock positions etc.)
            if settings.contains("windowState"):
                self.restoreState(settings.value("windowState"))
                logger.debug("Window state restored")
                
            # Fallback to size and position if geometry not available
            elif settings.contains("size") and settings.contains("pos"):
                self.resize(settings.value("size"))
                self.move(settings.value("pos"))
                logger.debug("Window size and position restored")
                
        except Exception as e:
            logger.error(f"Failed to restore window state: {e}")
            # If restoration fails, use default size and position
            self.resize(1200, 800)
        
    def findMenu(self, menu_name):
        """Find a menu by name
        
        Args:
            menu_name: The name of the menu to find
            
        Returns:
            QMenu: The menu if found, None otherwise
        """
        logger.debug(f"Looking for menu: {menu_name}")
        
        # Check main menubar
        for menu in self.menuBar().findChildren(QMenu, options=Qt.FindDirectChildrenOnly):
            if menu.title() == menu_name:
                return menu
            
        # Check if we have the menu stored as an attribute
        if hasattr(self, f"menu_{menu_name.lower().replace(' ', '_')}"):
            return getattr(self, f"menu_{menu_name.lower().replace(' ', '_')}")
        
        # Not found
        logger.debug(f"Menu '{menu_name}' not found")
        return None 