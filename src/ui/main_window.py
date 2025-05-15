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
    QHeaderView, QAbstractItemView, QSizePolicy, QInputDialog, QLineEdit, QMessageBox, QDialog, QListWidget, QTableWidget, QTableWidgetItem, QTextBrowser,
    QApplication
)
from PySide6.QtGui import QIcon, QAction, QFont, QKeySequence, QBrush, QColor
from PySide6.QtCore import Qt, QSize, Signal, Slot, QModelIndex, QSettings, QTimer, QByteArray, QPoint
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
        
        # Initialize autosave
        self._setup_autosave()
        
        # Restore window state, size and position if available
        self._restore_window_state()
        
        # Initialize update checker
        self._setup_update_checker()
        
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
        
        self.action_check_updates = QAction("Check for Updates", self)
        self.action_check_updates.setStatusTip("Check for application updates")
        self.action_check_updates.triggered.connect(self.on_check_updates)
        
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
        self.menu_help.addAction(self.action_check_updates)
        self.menu_help.addAction(self.action_about)
        
        # Plugin menus (will be populated by plugins)
        self.plugin_menus = {}
        
    def _create_toolbar(self):
        """Create toolbar"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))  # Reduced from 24x24
        
        # Make the toolbar more compact
        self.toolbar.setStyleSheet("""
            QToolBar {
                spacing: 2px;
                padding: 1px;
                margin: 0px;
            }
            QToolButton {
                padding: 2px;
                margin: 0px;
            }
        """)
        
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
        self.details_layout.setContentsMargins(4, 4, 4, 4)
        
        # Create a table for properties instead of a form layout
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QMenu
        
        # Property table
        self.properties_table = QTableWidget()
        self.properties_table.setColumnCount(2)
        self.properties_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.properties_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.properties_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.properties_table.setAlternatingRowColors(True)
        self.properties_table.verticalHeader().setVisible(False)
        self.properties_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.properties_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.properties_table.customContextMenuRequested.connect(self._show_property_context_menu)
        
        # Apply modern styling
        self.properties_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #F0F0F0;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #D0D0D0;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #E0F0FF;
                color: #000000;
            }
        """)
        
        # Toolbar for property actions
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 4)
        
        export_btn = QPushButton("Export")
        export_btn.setToolTip("Export properties to clipboard or file")
        export_btn.clicked.connect(self._export_properties)
        
        filter_edit = QLineEdit()
        filter_edit.setPlaceholderText("Filter properties...")
        filter_edit.textChanged.connect(self._filter_properties)
        filter_edit.setClearButtonEnabled(True)
        
        toolbar_layout.addWidget(filter_edit)
        toolbar_layout.addWidget(export_btn)
        
        self.details_layout.addLayout(toolbar_layout)
        self.details_layout.addWidget(self.properties_table)
        
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
            # Check if it's an existing menu or a new plugin menu
            existing_menu = self.findMenu(menu_name)
            if existing_menu:
                # Add actions to existing menu
                for action in actions:
                    existing_menu.addAction(action)
                    # Store the menu and action for later removal
                    if not hasattr(plugin_info, 'ui_components'):
                        plugin_info.ui_components = {}
                    if 'menu_actions' not in plugin_info.ui_components:
                        plugin_info.ui_components['menu_actions'] = []
                    plugin_info.ui_components['menu_actions'].append((menu_name, action))
            else:
                # Create a new plugin menu if it doesn't exist
                if menu_name not in self.plugin_menus:
                    self.plugin_menus[menu_name] = self.menu_bar.addMenu(menu_name)
                    
                # Add actions to the plugin menu
                for action in actions:
                    self.plugin_menus[menu_name].addAction(action)
                    # Store the menu and action for later removal
                    if not hasattr(plugin_info, 'ui_components'):
                        plugin_info.ui_components = {}
                    if 'plugin_menu_actions' not in plugin_info.ui_components:
                        plugin_info.ui_components['plugin_menu_actions'] = []
                    plugin_info.ui_components['plugin_menu_actions'].append((menu_name, action))
                
        # Add device panels to properties widget
        device_panels = plugin.get_device_panels()
        for panel_name, widget in device_panels:
            self.properties_widget.addTab(widget, panel_name)
            # Store for later removal
            if not hasattr(plugin_info, 'ui_components'):
                plugin_info.ui_components = {}
            if 'device_panels' not in plugin_info.ui_components:
                plugin_info.ui_components['device_panels'] = []
            plugin_info.ui_components['device_panels'].append((panel_name, widget))
            
        # Add dock widgets
        dock_widgets = plugin.get_dock_widgets()
        for widget_name, widget, area in dock_widgets:
            dock = QDockWidget(widget_name, self)
            dock.setWidget(widget)
            self.addDockWidget(area, dock)
            # Store for later removal
            if not hasattr(plugin_info, 'ui_components'):
                plugin_info.ui_components = {}
            if 'dock_widgets' not in plugin_info.ui_components:
                plugin_info.ui_components['dock_widgets'] = []
            plugin_info.ui_components['dock_widgets'].append((widget_name, dock))
            
    def remove_plugin_ui_components(self, plugin_info):
        """Remove UI components from a plugin"""
        logger.debug(f"Removing UI components for plugin: {plugin_info}")
        
        if not hasattr(plugin_info, 'ui_components'):
            logger.debug(f"No UI components to remove for plugin: {plugin_info}")
            return
            
        # Remove menu actions from existing menus
        if 'menu_actions' in plugin_info.ui_components:
            for menu_name, action in plugin_info.ui_components['menu_actions']:
                menu = self.findMenu(menu_name)
                if menu and action in menu.actions():
                    menu.removeAction(action)
                    
        # Remove actions from plugin menus
        if 'plugin_menu_actions' in plugin_info.ui_components:
            for menu_name, action in plugin_info.ui_components['plugin_menu_actions']:
                if menu_name in self.plugin_menus:
                    menu = self.plugin_menus[menu_name]
                    menu.removeAction(action)
                    # Remove menu if it's empty
                    if len(menu.actions()) == 0:
                        self.menu_bar.removeAction(menu.menuAction())
                        del self.plugin_menus[menu_name]
        
        # Remove device panels
        if 'device_panels' in plugin_info.ui_components:
            for panel_name, widget in plugin_info.ui_components['device_panels']:
                index = self.properties_widget.indexOf(widget)
                if index >= 0:
                    self.properties_widget.removeTab(index)
                    
        # Remove dock widgets
        if 'dock_widgets' in plugin_info.ui_components:
            for widget_name, dock in plugin_info.ui_components['dock_widgets']:
                self.removeDockWidget(dock)
                dock.deleteLater()
                
        # Clear the components
        plugin_info.ui_components = {}
        
    def update_property_panel(self, devices=None):
        """Update property panel with device info
        
        Args:
            devices: A list of selected devices or None if no selection
        """
        # Clear table
        self.properties_table.setRowCount(0)
                
        # Convert single device to list for consistent handling
        if devices and not isinstance(devices, list):
            devices = [devices]
                
        # Early return if no devices selected
        no_selection = not devices or len(devices) == 0
        if no_selection:
            # Show placeholder text
            self.properties_table.setRowCount(1)
            item = QTableWidgetItem("No devices selected")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setTextAlignment(Qt.AlignCenter)
            self.properties_table.setSpan(0, 0, 1, 2)
            self.properties_table.setItem(0, 0, item)
            logger.debug("No devices selected, cleared property panel")
            return
            
        # Store all properties for filtering
        self.current_properties = {}
            
        if len(devices) == 1:
            # Single device selection - show all properties
            device = devices[0]
            logger.debug(f"Showing properties for single device: {device.get_property('alias', 'Unnamed')}")
            
            # Get all properties
            device_props = device.get_properties()
            
            # Add core properties first (in a specific order)
            core_props = ["id", "alias", "hostname", "ip_address", "mac_address", "status", "notes", "tags"]
            for prop in core_props:
                if prop in device_props:
                    value = device_props[prop]
                    formatted_value = self._format_property_value(value)
                    self._add_property_row(prop, value, formatted_value)
                    
            # Add a separator row
            self._add_separator_row("Custom Properties")
                    
            # Add custom properties
            custom_props = sorted([k for k in device_props.keys() if k not in core_props])
            for key in custom_props:
                value = device_props[key]
                formatted_value = self._format_property_value(value)
                self._add_property_row(key, value, formatted_value)
                
        else:
            # Multiple device selection - show common properties
            logger.debug(f"Showing properties for {len(devices)} devices")
            
            # Get device names for better logging
            device_names = [d.get_property('alias', f'Device {d.id}') for d in devices]
            logger.debug(f"Multiple devices selected: {', '.join(device_names[:5])}" + 
                       (f" and {len(device_names) - 5} more" if len(device_names) > 5 else ""))
            
            # Collect all properties from all devices
            all_properties = {}
            core_props = ["id", "alias", "hostname", "ip_address", "mac_address", "status", "notes", "tags"]
            
            # First, gather all properties and their values
            for device in devices:
                for key, value in device.get_properties().items():
                    if key not in all_properties:
                        all_properties[key] = []
                    
                    all_properties[key].append(value)
            
            # Add a header row with device count
            self._add_separator_row(f"{len(devices)} Devices Selected")
            
            # Add core properties first
            for prop in core_props:
                if prop in all_properties:
                    values = all_properties[prop]
                    # Check if all values are the same
                    if len(set(str(v) for v in values)) == 1:
                        formatted_value = self._format_property_value(values[0])
                        self._add_property_row(prop, values[0], formatted_value)
                    else:
                        self._add_property_row(prop, values, "<Multiple values>")
            
            # Add a separator for custom properties
            self._add_separator_row("Custom Properties")
            
            # Add custom properties (excluding core properties)
            custom_props = sorted([k for k in all_properties.keys() if k not in core_props])
            for key in custom_props:
                values = all_properties[key]
                if len(set(str(v) for v in values)) == 1:
                    formatted_value = self._format_property_value(values[0])
                    self._add_property_row(key, values[0], formatted_value)
                else:
                    self._add_property_row(key, values, "<Multiple values>")
                    
        # Resize rows to contents
        self.properties_table.resizeRowsToContents()
    
    def _add_property_row(self, key, raw_value, formatted_value):
        """Add a property row to the table
        
        Args:
            key: Property name
            raw_value: The raw value (stored for context menu)
            formatted_value: The formatted display value
        """
        row = self.properties_table.rowCount()
        self.properties_table.insertRow(row)
        
        # Property name (with title case formatting)
        name_item = QTableWidgetItem(key.replace('_', ' ').title())
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        name_item.setToolTip(key)
        self.properties_table.setItem(row, 0, name_item)
        
        # Property value
        value_item = QTableWidgetItem(formatted_value)
        value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
        value_item.setData(Qt.UserRole, raw_value)  # Store raw value for context menu
        
        # If it's a URL, make it look like a link
        if isinstance(raw_value, str) and (raw_value.startswith('http://') or raw_value.startswith('https://')):
            value_item.setForeground(QBrush(QColor("blue")))
            font = value_item.font()
            font.setUnderline(True)
            value_item.setFont(font)
            value_item.setToolTip("Click to open in browser")
        else:
            value_item.setToolTip(formatted_value)
            
        self.properties_table.setItem(row, 1, value_item)
        
        # Store for filtering
        self.current_properties[key] = {
            'raw': raw_value,
            'formatted': formatted_value,
            'row': row
        }
    
    def _add_separator_row(self, text):
        """Add a separator/header row to the table
        
        Args:
            text: Text to display in the separator
        """
        row = self.properties_table.rowCount()
        self.properties_table.insertRow(row)
        
        # Create a header-style item spanning both columns
        separator_item = QTableWidgetItem(text)
        separator_item.setFlags(separator_item.flags() & ~Qt.ItemIsEditable)
        separator_item.setBackground(QBrush(QColor("#F0F0F0")))
        font = separator_item.font()
        font.setBold(True)
        separator_item.setFont(font)
        
        self.properties_table.setSpan(row, 0, 1, 2)
        self.properties_table.setItem(row, 0, separator_item)
    
    def _filter_properties(self, filter_text):
        """Filter properties based on user input
        
        Args:
            filter_text: Text to filter by
        """
        filter_text = filter_text.lower()
        
        # Show/hide rows based on filter
        for key, prop_data in self.current_properties.items():
            row = prop_data['row']
            matches = (
                filter_text in key.lower() or
                filter_text in str(prop_data['formatted']).lower()
            )
            self.properties_table.setRowHidden(row, not matches)
    
    def _show_property_context_menu(self, position):
        """Show context menu for property table
        
        Args:
            position: Position where the menu should be shown
        """
        menu = QMenu()
        
        copy_action = menu.addAction("Copy Value")
        copy_name_action = menu.addAction("Copy Property Name")
        copy_both_action = menu.addAction("Copy Name and Value")
        menu.addSeparator()
        copy_all_action = menu.addAction("Copy All Properties")
        
        # Get selected items
        selected_indexes = self.properties_table.selectedIndexes()
        if not selected_indexes:
            return
            
        # If a URL is selected, add open link action
        for index in selected_indexes:
            if index.column() == 1:  # Value column
                item = self.properties_table.item(index.row(), index.column())
                raw_value = item.data(Qt.UserRole)
                if isinstance(raw_value, str) and (raw_value.startswith('http://') or raw_value.startswith('https://')):
                    menu.addSeparator()
                    open_url_action = menu.addAction("Open URL")
                    break
                    
        # If complex data is selected, add view details action
        for index in selected_indexes:
            if index.column() == 1:  # Value column
                item = self.properties_table.item(index.row(), index.column())
                raw_value = item.data(Qt.UserRole)
                if isinstance(raw_value, (dict, list)) or (isinstance(raw_value, str) and len(raw_value) > 100):
                    menu.addSeparator()
                    view_details_action = menu.addAction("View Details")
                    break
        
        # Show the menu and get the selected action
        action = menu.exec_(self.properties_table.mapToGlobal(position))
        
        if not action:
            return
            
        # Handle actions
        if action == copy_action:
            self._copy_selected_values()
        elif action == copy_name_action:
            self._copy_selected_names()
        elif action == copy_both_action:
            self._copy_selected_pairs()
        elif action == copy_all_action:
            self._copy_all_properties()
        elif 'open_url_action' in locals() and action == open_url_action:
            self._open_selected_url()
        elif 'view_details_action' in locals() and action == view_details_action:
            self._view_selected_details()
    
    def _copy_selected_values(self):
        """Copy selected property values to clipboard"""
        values = []
        for index in self.properties_table.selectedIndexes():
            if index.column() == 1:  # Value column
                values.append(self.properties_table.item(index.row(), index.column()).text())
                
        if values:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(values))
            self.status_bar.showMessage("Values copied to clipboard", 2000)
    
    def _copy_selected_names(self):
        """Copy selected property names to clipboard"""
        names = []
        for index in self.properties_table.selectedIndexes():
            if index.column() == 0:  # Name column
                names.append(self.properties_table.item(index.row(), index.column()).text())
                
        if names:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(names))
            self.status_bar.showMessage("Property names copied to clipboard", 2000)
    
    def _copy_selected_pairs(self):
        """Copy selected property name-value pairs to clipboard"""
        pairs = []
        selected_rows = set()
        
        # Get all selected rows
        for index in self.properties_table.selectedIndexes():
            selected_rows.add(index.row())
            
        # For each row, get the name and value
        for row in selected_rows:
            name_item = self.properties_table.item(row, 0)
            value_item = self.properties_table.item(row, 1)
            
            if name_item and value_item:
                name = name_item.text()
                value = value_item.text()
                pairs.append(f"{name}: {value}")
                
        if pairs:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(pairs))
            self.status_bar.showMessage("Properties copied to clipboard", 2000)
    
    def _copy_all_properties(self):
        """Copy all properties to clipboard"""
        pairs = []
        
        # Get all rows except separators
        for row in range(self.properties_table.rowCount()):
            # Skip rows that span columns (separators)
            if self.properties_table.columnSpan(row, 0) > 1:
                continue
                
            name_item = self.properties_table.item(row, 0)
            value_item = self.properties_table.item(row, 1)
            
            if name_item and value_item:
                name = name_item.text()
                value = value_item.text()
                pairs.append(f"{name}: {value}")
                
        if pairs:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(pairs))
            self.status_bar.showMessage("All properties copied to clipboard", 2000)
    
    def _open_selected_url(self):
        """Open the selected URL in the default browser"""
        for index in self.properties_table.selectedIndexes():
            if index.column() == 1:  # Value column
                item = self.properties_table.item(index.row(), index.column())
                raw_value = item.data(Qt.UserRole)
                if isinstance(raw_value, str) and (raw_value.startswith('http://') or raw_value.startswith('https://')):
                    import webbrowser
                    webbrowser.open(raw_value)
                    break
    
    def _view_selected_details(self):
        """Show details for complex data types"""
        for index in self.properties_table.selectedIndexes():
            if index.column() == 1:  # Value column
                item = self.properties_table.item(index.row(), index.column())
                raw_value = item.data(Qt.UserRole)
                name_item = self.properties_table.item(index.row(), 0)
                key = name_item.text() if name_item else "Property"
                self._show_detailed_property(key, raw_value)
                break
    
    def _export_properties(self):
        """Export properties to clipboard or file"""
        menu = QMenu()
        copy_clipboard = menu.addAction("Copy to Clipboard")
        menu.addSeparator()
        export_csv = menu.addAction("Export as CSV")
        export_json = menu.addAction("Export as JSON")
        
        # Get position to show menu
        button = self.sender()
        action = menu.exec_(button.mapToGlobal(QPoint(0, button.height())))
        
        if action == copy_clipboard:
            self._copy_all_properties()
        elif action == export_csv:
            self._export_as_csv()
        elif action == export_json:
            self._export_as_json()
    
    def _export_as_csv(self):
        """Export properties as CSV file"""
        from PySide6.QtWidgets import QFileDialog
        import csv
        
        # Get filename from user
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Properties", "", "CSV Files (*.csv)"
        )
        
        if not filename:
            return
            
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Property", "Value"])
                
                # Write all rows except separators
                for row in range(self.properties_table.rowCount()):
                    # Skip rows that span columns (separators)
                    if self.properties_table.columnSpan(row, 0) > 1:
                        continue
                        
                    name_item = self.properties_table.item(row, 0)
                    value_item = self.properties_table.item(row, 1)
                    
                    if name_item and value_item:
                        writer.writerow([name_item.text(), value_item.text()])
                        
            self.status_bar.showMessage(f"Properties exported to {filename}", 3000)
        except Exception as e:
            logger.error(f"Failed to export properties as CSV: {e}")
            self.status_bar.showMessage("Failed to export properties", 3000)
    
    def _export_as_json(self):
        """Export properties as JSON file"""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        # Get filename from user
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Properties", "", "JSON Files (*.json)"
        )
        
        if not filename:
            return
            
        try:
            properties = {}
            
            # Get all rows except separators
            for row in range(self.properties_table.rowCount()):
                # Skip rows that span columns (separators)
                if self.properties_table.columnSpan(row, 0) > 1:
                    continue
                    
                name_item = self.properties_table.item(row, 0)
                value_item = self.properties_table.item(row, 1)
                
                if name_item and value_item:
                    # Use original key format (not title case)
                    name = name_item.toolTip() or name_item.text().lower().replace(' ', '_')
                    # Use raw value if available
                    value = value_item.data(Qt.UserRole)
                    if value is None:
                        value = value_item.text()
                    properties[name] = value
                    
            with open(filename, 'w') as jsonfile:
                json.dump(properties, jsonfile, indent=2)
                        
            self.status_bar.showMessage(f"Properties exported to {filename}", 3000)
        except Exception as e:
            logger.error(f"Failed to export properties as JSON: {e}")
            self.status_bar.showMessage("Failed to export properties", 3000)
    
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
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        dialog.exec()
        
    @Slot()
    def on_new_workspace(self):
        """Create a new workspace"""
        logger.debug("Creating new workspace")
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Workspace")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Workspace Name:"))
        name_edit = QLineEdit()
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)
        
        # Description field
        layout.addWidget(QLabel("Description:"))
        desc_edit = QTextEdit()
        layout.addWidget(desc_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        create_button = QPushButton("Create")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(create_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Handle creation
        def on_create():
            name = name_edit.text().strip()
            description = desc_edit.toPlainText().strip()
            
            if not name:
                QMessageBox.warning(dialog, "Invalid Name", "Please enter a name for the workspace.")
                return
                
            # Check if workspace already exists
            workspaces = self.device_manager.list_workspaces()
            for ws in workspaces:
                if ws.get("name") == name:
                    QMessageBox.warning(dialog, "Workspace Exists", f"A workspace named '{name}' already exists.")
                    return
            
            # Save current workspace before creating a new one
            self.device_manager.save_workspace()
            
            # Create the new workspace
            self.device_manager.create_workspace(name, description)
            
            # Switch to the new workspace (will load it)
            success = self.device_manager.load_workspace(name)
            if success:
                # Update UI with new workspace
                self.updateWindowTitle()
                self.status_workspace.setText(f"Workspace: {name}")
                self.status_bar.showMessage(f"Created and switched to workspace: {name}", 3000)
                
                # Save the current layout to the new workspace
                self._save_workspace_layout()
                
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "Error", f"Failed to load workspace: {name}")
        
        create_button.clicked.connect(on_create)
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec()
    
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
                    # Save current window layout before switching
                    self._save_workspace_layout()
                    
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
                            
                        # Restore the layout of the new workspace
                        self._restore_window_state()
                            
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
        
    @Slot()
    def on_check_updates(self):
        """Handle check for updates action"""
        logger.debug("Manual check for updates requested")
        # Show message while checking
        self.status_bar.showMessage("Checking for updates...", 3000)
        # Check for updates and show result even if no updates available
        self.check_for_updates(silent=False)
        
    @Slot(str, str, str)
    def on_update_available(self, current_version, new_version, release_notes):
        """Handle update available signal
        
        Args:
            current_version: Current version string
            new_version: New version string
            release_notes: Release notes for the new version
        """
        logger.info(f"Update available: {current_version} -> {new_version}")
        
        # Check if this version has been skipped
        skipped_version = self.config.get("general.skipped_version", "")
        if skipped_version == new_version:
            logger.debug(f"Update {new_version} was previously skipped")
            return
        
        # Show update dialog
        from .update_dialog import UpdateDialog
        dialog = UpdateDialog(current_version, new_version, release_notes, self)
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
        
        # Also save the window layout specifically for this workspace
        self._save_workspace_layout()
        
        # Unload all plugins
        self.plugin_manager.unload_all_plugins()
        
        # Accept the event
        event.accept()
        
    def _save_workspace_layout(self):
        """Save window layout for the current workspace"""
        workspace_name = self.device_manager.current_workspace
        workspace_dir = os.path.join(self.device_manager.workspaces_dir, workspace_name)
        
        # Create workspace settings directory if it doesn't exist
        settings_dir = os.path.join(workspace_dir, "settings")
        os.makedirs(settings_dir, exist_ok=True)
        
        # Save window state to workspace-specific settings
        settings = QSettings(os.path.join(settings_dir, "window_layout.ini"), QSettings.IniFormat)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("size", self.size())
        settings.setValue("pos", self.pos())
        logger.debug(f"Saved window layout for workspace: {workspace_name}")
        
    def _restore_window_state(self):
        """Restore window state from settings"""
        try:
            # First try to load workspace-specific layout if available
            workspace_name = self.device_manager.current_workspace
            workspace_dir = os.path.join(self.device_manager.workspaces_dir, workspace_name)
            settings_dir = os.path.join(workspace_dir, "settings")
            layout_file = os.path.join(settings_dir, "window_layout.ini")
            
            if os.path.exists(layout_file):
                logger.debug(f"Restoring workspace-specific layout for: {workspace_name}")
                settings = QSettings(layout_file, QSettings.IniFormat)
                
                if settings.contains("geometry"):
                    # Ensure we have the correct type (QByteArray)
                    geometry_value = settings.value("geometry")
                    if not isinstance(geometry_value, QByteArray):
                        geometry_value = QByteArray(geometry_value)
                    
                    self.restoreGeometry(geometry_value)
                    logger.debug("Workspace-specific geometry restored")
                
                if settings.contains("windowState"):
                    # Ensure we have the correct type (QByteArray)
                    state_value = settings.value("windowState")
                    if not isinstance(state_value, QByteArray):
                        state_value = QByteArray(state_value)
                    
                    self.restoreState(state_value)
                    logger.debug("Workspace-specific window state restored")
                    
                return  # Successfully restored workspace-specific layout
            
            # Fall back to application-wide settings if workspace-specific not available
            settings = QSettings(self.app.applicationName(), "WindowState")
            # Restore geometry if available
            if settings.contains("geometry"):
                # Ensure we have the correct type (QByteArray)
                geometry_value = settings.value("geometry")
                if not isinstance(geometry_value, QByteArray):
                    geometry_value = QByteArray(geometry_value)
                
                self.restoreGeometry(geometry_value)
                logger.debug("Window geometry restored")
            
            # Restore window state (dock positions etc.)
            if settings.contains("windowState"):
                # Ensure we have the correct type (QByteArray)
                state_value = settings.value("windowState")
                if not isinstance(state_value, QByteArray):
                    state_value = QByteArray(state_value)
                
                self.restoreState(state_value)
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

    def _setup_autosave(self):
        """Setup autosave functionality"""
        # Create autosave timer
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.on_autosave)
        
        # Track whether changes have been made
        self.workspace_changed = False
        
        # Update autosave settings from config
        self._update_autosave_settings()
        
        # Connect to config changes to update autosave settings
        self.config.config_changed.connect(self._update_autosave_settings)
        
        # Connect to device manager signals to track changes
        self.device_manager.device_added.connect(self._on_workspace_changed)
        self.device_manager.device_removed.connect(self._on_workspace_changed)
        self.device_manager.device_changed.connect(self._on_workspace_changed)
        self.device_manager.group_added.connect(self._on_workspace_changed)
        self.device_manager.group_removed.connect(self._on_workspace_changed)
        
    def _update_autosave_settings(self):
        """Update autosave settings from config"""
        # Check if autosave is enabled
        enabled = self.config.get("autosave.enabled", False)
        
        # If enabled, start the timer with the configured interval
        if enabled:
            interval = self.config.get("autosave.interval", 5)
            self.autosave_timer.setInterval(interval * 60 * 1000)  # Convert minutes to milliseconds
            
            # Start the timer if it's not already running
            if not self.autosave_timer.isActive():
                self.autosave_timer.start()
                logger.debug(f"Autosave enabled with interval {interval} minutes")
        else:
            # Stop the timer if it's running
            if self.autosave_timer.isActive():
                self.autosave_timer.stop()
                logger.debug("Autosave disabled")
        
    def _on_workspace_changed(self, *args):
        """Track that workspace has changed for smart autosave"""
        self.workspace_changed = True
    
    @Slot()
    def on_autosave(self):
        """Handle autosave"""
        # Check if we should only save on changes
        only_on_changes = self.config.get("autosave.only_on_changes", True)
        
        # If only saving on changes and no changes made, skip
        if only_on_changes and not self.workspace_changed:
            logger.debug("Autosave skipped - no changes made")
            return
            
        logger.debug("Autosaving workspace")
        
        # Check if we should create backups
        create_backups = self.config.get("autosave.create_backups", True)
        
        if create_backups:
            self._create_backup()
            
        # Save the workspace
        self.device_manager.save_workspace()
        
        # Reset changed flag
        self.workspace_changed = False
        
        # Show notification if enabled
        show_notification = self.config.get("autosave.show_notification", False)
        if show_notification:
            self.status_bar.showMessage("Workspace autosaved", 3000)
            
    def _create_backup(self):
        """Create a backup of the current workspace"""
        import os
        import shutil
        import datetime
        
        try:
            # Get backup settings
            backup_dir = self.config.get("autosave.backup_directory", "")
            max_backups = self.config.get("autosave.max_backups", 10)
            
            # If no backup directory specified, use default in config directory
            if not backup_dir:
                backup_dir = os.path.join(self.config.config_dir, "backups")
                
            # Ensure backup directory exists
            os.makedirs(backup_dir, exist_ok=True)
            
            # Get workspace directory
            workspace_name = self.device_manager.current_workspace
            workspace_dir = os.path.join(self.device_manager.workspaces_dir, workspace_name)
            
            # Create backup filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{workspace_name}_{timestamp}.zip"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Create zip backup
            import zipfile
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(workspace_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(workspace_dir))
                        zipf.write(file_path, arcname)
            
            logger.debug(f"Created workspace backup: {backup_path}")
            
            # Clean up old backups if we have more than max_backups
            self._cleanup_old_backups(backup_dir, workspace_name, max_backups)
            
        except Exception as e:
            logger.error(f"Failed to create workspace backup: {e}")
            
    def _cleanup_old_backups(self, backup_dir, workspace_name, max_backups):
        """Clean up old backups if there are more than max_backups"""
        import os
        import glob
        
        try:
            # Get list of backup files for this workspace
            backup_pattern = os.path.join(backup_dir, f"{workspace_name}_*.zip")
            backup_files = glob.glob(backup_pattern)
            
            # Sort by modification time (oldest first)
            backup_files.sort(key=os.path.getmtime)
            
            # Delete oldest backups if we have too many
            while len(backup_files) > max_backups:
                oldest_backup = backup_files.pop(0)
                os.remove(oldest_backup)
                logger.debug(f"Deleted old workspace backup: {oldest_backup}")
                
        except Exception as e:
            logger.error(f"Failed to clean up old backups: {e}")
        
    def _setup_update_checker(self):
        """Set up the update checker"""
        from src.core.update_checker import UpdateChecker
        
        self.update_checker = UpdateChecker(self.config)
        
        # Connect signals
        self.update_checker.update_available.connect(self.on_update_available)
        
        # Check for updates on startup if enabled
        if self.config.get("general.check_updates", True):
            # Schedule update check after a delay to not slow down startup
            QTimer.singleShot(5000, self.check_for_updates)

    def check_for_updates(self, silent=True):
        """Check for updates
        
        Args:
            silent: If True, don't show message if no updates are available
        """
        logger.debug("Checking for updates")
        
        # Get branch from configuration
        branch = self.update_checker.get_branch()
        
        # Check for updates in the background
        def check_thread():
            result = self.update_checker.check_for_updates(branch)
            
            # Show message if no updates available and not in silent mode
            if not silent and not result[0]:
                # Use invokeMethod to safely update UI from another thread
                QTimer.singleShot(0, lambda: self.status_bar.showMessage("No updates available", 3000))
        
        # Run in another thread to not block UI
        import threading
        thread = threading.Thread(target=check_thread)
        thread.daemon = True
        thread.start() 

    def _format_property_value(self, value):
        """Format a property value for display based on type
        
        Args:
            value: The value to format
            
        Returns:
            str: Formatted value as a string
        """
        # Return placeholder for None values
        if value is None:
            return "--"
            
        # Handle different data types
        if isinstance(value, bool):
            return "Yes" if value else "No"
            
        elif isinstance(value, (int, float)):
            # Format large numbers with commas
            if isinstance(value, int) and abs(value) >= 10000:
                return f"{value:,}"
            # Format floats with appropriate decimal places
            elif isinstance(value, float):
                # Limit to 4 decimal places but trim trailing zeros
                return f"{value:.4f}".rstrip('0').rstrip('.') if '.' in f"{value:.4f}" else f"{value:.0f}"
            return str(value)
            
        elif isinstance(value, list):
            # Format lists as comma-separated values
            if not value:
                return "Empty list"
            return ", ".join(str(item) for item in value)
            
        elif isinstance(value, dict):
            # For dictionaries, return a summary
            if not value:
                return "Empty dictionary"
            return f"Dictionary with {len(value)} items"
            
        elif isinstance(value, str):
            # Check if it's a date/time string (ISO format or common formats)
            import re
            date_patterns = [
                # ISO date: 2023-10-15 or 2023-10-15T14:30:25
                r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?$',
                # Common date: 10/15/2023 or 15/10/2023
                r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})$',
                # Date with time: 2023-10-15 14:30:25 or 10/15/2023 14:30:25
                r'^(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}) \d{1,2}:\d{2}(:\d{2})?$'
            ]
            
            # If it matches a date pattern, try to parse and format it
            for pattern in date_patterns:
                if re.match(pattern, value):
                    try:
                        import datetime
                        # Try different formats
                        for fmt in [
                            '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', 
                            '%m/%d/%Y', '%d/%m/%Y',
                            '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S'
                        ]:
                            try:
                                date_obj = datetime.datetime.strptime(value, fmt)
                                # Format with a nice human-readable format
                                return date_obj.strftime('%b %d, %Y %I:%M %p').replace(' 12:00 AM', '')
                            except ValueError:
                                continue
                    except (ValueError, ImportError):
                        pass  # If parsing fails, just use the original string
            
            # For long text, truncate with ellipsis
            if len(value) > 100:
                return value[:97] + "..."
                
        # Default: just convert to string
        return str(value)

    def _show_detailed_property(self, key, value):
        """Show a property value in detail in a dialog
        
        Args:
            key: The property key
            value: The property value
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Property: {key}")
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Create a text browser for displaying detailed content
        text_browser = QTextBrowser()
        
        # Format the content based on the type
        if isinstance(value, dict):
            import json
            try:
                formatted_json = json.dumps(value, indent=2)
                text_browser.setPlainText(formatted_json)
            except Exception:
                text_browser.setPlainText(str(value))
        elif isinstance(value, list):
            # Format lists nicely, one item per line
            if all(isinstance(item, dict) for item in value):
                # If list of dictionaries, format as JSON
                import json
                try:
                    formatted_json = json.dumps(value, indent=2)
                    text_browser.setPlainText(formatted_json)
                except Exception:
                    text_browser.setPlainText("\n".join([f"- {item}" for item in value]))
            else:
                # Simple list formatting
                text_browser.setPlainText("\n".join([f"- {item}" for item in value]))
        else:
            text_browser.setPlainText(str(value))
            
        layout.addWidget(text_browser)
        
        # Add a close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.exec() 