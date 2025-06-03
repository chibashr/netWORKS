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
    QApplication, QFileDialog
)
from PySide6.QtGui import QIcon, QAction, QFont, QKeySequence, QBrush, QColor
from PySide6.QtCore import Qt, QSize, Signal, Slot, QModelIndex, QSettings, QTimer, QByteArray, QPoint
from PySide6.QtWidgets import QStyle
import html
import re

from .device_table import DeviceTableModel, DeviceTableView, QAbstractItemView
from .device_tree import DeviceTreeModel, DeviceTreeView
from .plugin_manager_dialog import PluginManagerDialog
from .log_panel import LogPanel
from ..core.connectivity_manager import require_connectivity


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
        self.connectivity_manager = app.connectivity_manager
        
        # Set window properties for easy resizing
        self.updateWindowTitle()
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)  # Set reasonable minimum size
        
        # Ensure window is resizable
        self.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        )
        
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
        app_full_version = self.app.manifest.get("full_version", self.app.get_version())
        workspace = self.device_manager.current_workspace
        connectivity_status = self.connectivity_manager.get_status_text() if self.connectivity_manager else "Unknown"
        
        # Include connectivity status in window title if offline
        if connectivity_status == "Offline":
            self.setWindowTitle(f"NetWORKS v{app_full_version} - Workspace: {workspace} [OFFLINE]")
        else:
            self.setWindowTitle(f"NetWORKS v{app_full_version} - Workspace: {workspace}")
        
    def refresh_workspace_ui(self):
        """Refresh all UI components after workspace change"""
        logger.debug(f"Refreshing UI for workspace: {self.device_manager.current_workspace}")
        
        # Update window title
        self.updateWindowTitle()
        
        # Update status bar
        self.status_workspace.setText(f"Workspace: {self.device_manager.current_workspace}")
        self.status_bar.showMessage(f"Loaded workspace: {self.device_manager.current_workspace}", 3000)
        
        # Refresh device table
        if hasattr(self, "device_table"):
            self.device_table.refresh()
            
        # Refresh device panel
        if hasattr(self, "device_panel"):
            self.device_panel.refresh()
            
        # Refresh device tree
        if hasattr(self, "device_tree"):
            self.device_tree.refresh()
            
        # Update device count in status bar
        self.update_status_bar()
        
        # Restore the UI layout for this workspace
        self._restore_window_state()
        
        logger.debug("UI refresh complete")
        
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
        
        self.action_report_issue = QAction("Report Issue", self)
        self.action_report_issue.setStatusTip("Report an issue or request a feature")
        self.action_report_issue.triggered.connect(self.on_report_issue)
        
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
        self.menu_help.addAction(self.action_report_issue)
        self.menu_help.addAction(self.action_check_updates)
        self.menu_help.addAction(self.action_about)
        
        # Plugin menus (will be populated by plugins)
        self.plugin_menus = {}
        
    def _create_toolbar(self):
        """Create the main toolbar as a tab widget for better space utilization"""
        # Create a container widget for the tab-based toolbar
        self.toolbar_container = QWidget()
        self.toolbar_container.setObjectName("ToolbarContainer")
        self.toolbar_container.setMaximumHeight(65)  # Reduced from 70 to fit smaller buttons
        
        # Create layout for the container
        toolbar_layout = QHBoxLayout(self.toolbar_container)
        toolbar_layout.setContentsMargins(4, 2, 4, 2)
        toolbar_layout.setSpacing(0)
        
        # Create tab widget for toolbar sections
        self.toolbar_tabs = QTabWidget()
        self.toolbar_tabs.setObjectName("ToolbarTabs")
        self.toolbar_tabs.setTabPosition(QTabWidget.North)
        self.toolbar_tabs.setMaximumHeight(61)  # Reduced from 66 to fit smaller buttons
        
        # Style the tab widget for a toolbar appearance
        self.toolbar_tabs.setStyleSheet("""
            QTabWidget {
                background-color: #f8f8f8;
                border: none;
                border-bottom: 1px solid #e0e0e0;
            }
            QTabWidget::pane {
                border: none;
                background-color: #f8f8f8;
                margin: 0px;
                padding: 0px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #e8e8e8;
                border: 1px solid #d0d0d0;
                border-bottom: none;
                border-radius: 4px 4px 0px 0px;
                padding: 4px 12px;
                margin-right: 2px;
                font-size: 10px;
                font-weight: 500;
                color: #555555;
            }
            QTabBar::tab:selected {
                background-color: #f8f8f8;
                border-bottom: 1px solid #f8f8f8;
                color: #333333;
            }
            QTabBar::tab:hover {
                background-color: #f0f0f0;
            }
        """)
        
        # Create the Core tab
        self._create_toolbar_tab("Core", [
            self.action_new_device,
            self.action_new_group,
            None,  # Separator
            self.action_save,
            None,  # Separator
            self.action_refresh
        ])
        
        # Add tab widget to toolbar layout
        toolbar_layout.addWidget(self.toolbar_tabs)
        
        # Add toolbar container to main window
        self.addToolBar(Qt.TopToolBarArea, self._create_toolbar_widget())
        
        # Plugin tabs will be added dynamically
        self.plugin_toolbar_tabs = {}
        
    def _create_toolbar_widget(self):
        """Create a QToolBar containing the tab widget"""
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setObjectName("MainToolbar")
        toolbar.setMovable(True)
        toolbar.setFloatable(False)
        toolbar.addWidget(self.toolbar_container)
        
        # Store reference for later use
        self.toolbar = toolbar
        return toolbar
    
    def _create_toolbar_tab(self, tab_name, actions):
        """Create a tab with toolbar buttons
        
        Args:
            tab_name: Name of the tab
            actions: List of actions (None for separators)
        """
        if not actions:
            return
            
        # Create tab widget
        tab_widget = QWidget()
        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(8, 4, 8, 4)  # Reduced vertical margins
        tab_layout.setSpacing(8)  # Increased spacing between buttons for clearer separation
        
        # Add actions as buttons
        for action in actions:
            if action is None:
                # Create separator with better visual styling
                separator = QFrame()
                separator.setFrameShape(QFrame.VLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setFixedWidth(2)
                separator.setMinimumHeight(25)  # Reduced height to match smaller buttons
                separator.setStyleSheet("""
                    QFrame {
                        color: #c0c0c0; 
                        background-color: #c0c0c0;
                        margin: 4px 6px;
                        border: none;
                    }
                """)
                tab_layout.addWidget(separator)
            else:
                # Create button for action
                button = QPushButton()
                # Manually set button properties from action (QPushButton doesn't have setDefaultAction)
                button.setText(action.text())
                button.setIcon(action.icon())
                button.setToolTip(action.statusTip() or action.text())
                button.setEnabled(action.isEnabled())
                button.setMaximumHeight(32)  # Reduced from 40 to fit better
                button.setMinimumHeight(30)  # Set minimum height for consistency
                button.setMinimumWidth(85)   # Slightly increased for better appearance
                
                # Connect button click to action trigger
                button.clicked.connect(action.trigger)
                
                # Enhanced button styling without unsupported transform properties
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #f5f5f5;
                        border: 1px solid #d0d0d0;
                        border-radius: 5px;
                        padding: 6px 14px;
                        font-size: 11px;
                        font-weight: 500;
                        color: #333333;
                        text-align: center;
                        margin: 1px;
                    }
                    QPushButton:hover {
                        background-color: #e8e8e8;
                        border-color: #b0b0b0;
                    }
                    QPushButton:pressed {
                        background-color: #d8d8d8;
                        border-color: #a0a0a0;
                    }
                    QPushButton:disabled {
                        background-color: #f8f8f8;
                        color: #999999;
                        border-color: #e0e0e0;
                    }
                """)
                
                tab_layout.addWidget(button)
        
        # Add stretch to push buttons to the left
        tab_layout.addStretch()
        
        # Add tab to tab widget
        self.toolbar_tabs.addTab(tab_widget, tab_name)
    
    def _create_statusbar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Workspace indicator
        self.status_workspace = QLabel(f"Workspace: {self.device_manager.current_workspace}")
        self.status_bar.addWidget(self.status_workspace)
        
        # Connectivity status
        self.status_connectivity = QLabel("Checking...")
        self.status_connectivity.setObjectName("ConnectivityStatus")
        self.status_bar.addWidget(self.status_connectivity)
        self._update_connectivity_status()
        
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
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        self.dock_device_tree.setObjectName("DevicesTreeDock")
        self.dock_device_tree.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.dock_device_tree.setMinimumWidth(200)
        self.dock_device_tree.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # Create device tree
        self.device_tree_model = DeviceTreeModel(self.device_manager)
        self.device_tree = DeviceTreeView(self.device_manager)
        self.device_tree.setModel(self.device_tree_model)
        
        self.dock_device_tree.setWidget(self.device_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_device_tree)
        
        # Properties dock widget (right panel)
        self.dock_properties = QDockWidget("Properties", self)
        self.dock_properties.setObjectName("PropertiesDock")
        self.dock_properties.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.dock_properties.setMinimumWidth(250)
        self.dock_properties.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
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
        # Add double click handler
        self.properties_table.cellDoubleClicked.connect(self._handle_property_double_click)
        
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
        self.dock_log.setObjectName("LogDock")
        self.dock_log.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.dock_log.setMinimumHeight(100)
        self.dock_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
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
        
        # Connectivity manager signals
        if self.connectivity_manager:
            self.connectivity_manager.connectivity_changed.connect(self.on_connectivity_changed)
    
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
        
        # Add toolbar actions with tab support
        toolbar_actions = plugin.get_toolbar_actions()
        if toolbar_actions:
            # Check if plugin provides grouped actions
            if isinstance(toolbar_actions, dict):
                # Plugin provides grouped actions - create tabs for each group
                for group_name, actions in toolbar_actions.items():
                    tab_name = f"{plugin_info.name} - {group_name}"
                    self._create_toolbar_tab(tab_name, actions)
                    # Store for cleanup
                    if plugin_info.id not in self.plugin_toolbar_tabs:
                        self.plugin_toolbar_tabs[plugin_info.id] = []
                    self.plugin_toolbar_tabs[plugin_info.id].append(tab_name)
            else:
                # Legacy flat list of actions - create single tab
                tab_name = plugin_info.name
                self._create_toolbar_tab(tab_name, toolbar_actions)
                # Store for cleanup
                if plugin_info.id not in self.plugin_toolbar_tabs:
                    self.plugin_toolbar_tabs[plugin_info.id] = []
                self.plugin_toolbar_tabs[plugin_info.id].append(tab_name)
        
        # Add menu actions - organize Tools menu by plugin
        menu_actions = plugin.get_menu_actions()
        for menu_name, actions in menu_actions.items():
            # Check if it's a Tools menu item - organize these by plugin
            if menu_name == "Tools":
                # Create or get plugin submenu in Tools
                plugin_submenu = self._get_or_create_plugin_tools_submenu(plugin_info)
                for action in actions:
                    plugin_submenu.addAction(action)
                    # Store the submenu and action for later removal
                    if not hasattr(plugin_info, 'ui_components'):
                        plugin_info.ui_components = {}
                    if 'tools_submenu_actions' not in plugin_info.ui_components:
                        plugin_info.ui_components['tools_submenu_actions'] = []
                    plugin_info.ui_components['tools_submenu_actions'].append((plugin_submenu, action))
            else:
                # Handle other menu actions as before
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
        dock_widgets = getattr(plugin, 'get_dock_widgets', lambda: [])()
        for widget_name, widget, area in dock_widgets:
            dock = QDockWidget(widget_name, self)
            # Set object name to ensure proper state saving/restoring
            safe_name = widget_name.replace(" ", "")
            dock.setObjectName(f"{plugin_info.id}_{safe_name}Dock")
            dock.setWidget(widget)
            self.addDockWidget(area, dock)
            # Store for later removal
            if not hasattr(plugin_info, 'ui_components'):
                plugin_info.ui_components = {}
            if 'dock_widgets' not in plugin_info.ui_components:
                plugin_info.ui_components['dock_widgets'] = []
            plugin_info.ui_components['dock_widgets'].append((widget_name, dock))
    
    def _get_or_create_plugin_tools_submenu(self, plugin_info):
        """Get or create a submenu for a plugin in the Tools menu
        
        Args:
            plugin_info: The plugin information object
            
        Returns:
            QMenu: The plugin's submenu in the Tools menu
        """
        # Check if we already have a submenu for this plugin
        submenu_key = f"plugin_tools_{plugin_info.id}"
        
        if not hasattr(self, 'plugin_tools_submenus'):
            self.plugin_tools_submenus = {}
            
        if submenu_key not in self.plugin_tools_submenus:
            # Create plugin submenu in Tools menu
            plugin_submenu = self.menu_tools.addMenu(plugin_info.name)
            plugin_submenu.setObjectName(submenu_key)
            
            # Style the submenu
            plugin_submenu.setStyleSheet("""
                QMenu {
                    font-weight: normal;
                }
                QMenu::item {
                    padding: 6px 20px;
                }
            """)
            
            self.plugin_tools_submenus[submenu_key] = plugin_submenu
            
            # Store for cleanup
            if not hasattr(plugin_info, 'ui_components'):
                plugin_info.ui_components = {}
            if 'tools_submenu' not in plugin_info.ui_components:
                plugin_info.ui_components['tools_submenu'] = []
            plugin_info.ui_components['tools_submenu'].append((submenu_key, plugin_submenu))
            
        return self.plugin_tools_submenus[submenu_key]
    
    def remove_plugin_ui_components(self, plugin_info):
        """Remove UI components from a plugin"""
        logger.debug(f"Removing UI components for plugin: {plugin_info}")
        
        # Clean up toolbar tabs for this plugin
        if plugin_info.id in self.plugin_toolbar_tabs:
            for tab_name in self.plugin_toolbar_tabs[plugin_info.id]:
                # Find and remove the tab
                for i in range(self.toolbar_tabs.count()):
                    if self.toolbar_tabs.tabText(i) == tab_name:
                        # Remove the tab and its widget
                        widget = self.toolbar_tabs.widget(i)
                        self.toolbar_tabs.removeTab(i)
                        if widget:
                            widget.deleteLater()
                        break
            del self.plugin_toolbar_tabs[plugin_info.id]
        
        if not hasattr(plugin_info, 'ui_components'):
            logger.debug(f"No UI components to remove for plugin: {plugin_info}")
            return
            
        # Remove Tools submenu actions
        if 'tools_submenu_actions' in plugin_info.ui_components:
            for submenu, action in plugin_info.ui_components['tools_submenu_actions']:
                submenu.removeAction(action)
                
        # Remove Tools submenu if it's empty
        if 'tools_submenu' in plugin_info.ui_components:
            for submenu_key, submenu in plugin_info.ui_components['tools_submenu']:
                if submenu.isEmpty():
                    # Remove submenu from Tools menu
                    self.menu_tools.removeAction(submenu.menuAction())
                    # Remove from our tracking
                    if hasattr(self, 'plugin_tools_submenus') and submenu_key in self.plugin_tools_submenus:
                        del self.plugin_tools_submenus[submenu_key]
                    
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
    
    def _rebuild_toolbar_after_plugin_removal(self):
        """Rebuild toolbar after plugin removal - not needed for tab-based system"""
        # This method is kept for compatibility but does nothing
        # since tabs are removed individually in remove_plugin_ui_components
        pass
    
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
            
            # Get loaded plugin IDs for property categorization
            plugin_ids = []
            if hasattr(self.app, 'plugin_manager'):
                for plugin_info in self.app.plugin_manager.get_plugins():
                    if plugin_info.state and plugin_info.state.is_loaded and plugin_info.id:
                        plugin_ids.append(plugin_info.id)
            
            # Add core properties first (in a specific order)
            core_props = ["id", "alias", "hostname", "ip_address", "mac_address", "status", "notes", "tags"]
            for prop in core_props:
                if prop in device_props:
                    value = device_props[prop]
                    formatted_value = self._format_property_value(value)
                    self._add_property_row(prop, value, formatted_value)
            
            # Separate remaining properties into plugin and custom
            plugin_props = {}
            custom_props = {}
            
            # Identify plugin properties using common separators (plugin_id:prop, plugin_id.prop, plugin_id_prop)
            for key in sorted([k for k in device_props.keys() if k not in core_props]):
                is_plugin_prop = False
                for plugin_id in plugin_ids:
                    # Check common separator patterns
                    if (key.startswith(f"{plugin_id}:") or 
                        key.startswith(f"{plugin_id}.") or 
                        key.startswith(f"{plugin_id}_")):
                        plugin_props[key] = device_props[key]
                        is_plugin_prop = True
                        break
                
                # If not a plugin property, it's a custom property
                if not is_plugin_prop:
                    custom_props[key] = device_props[key]
            
            # Add plugin properties if any exist
            if plugin_props:
                self._add_separator_row("Plugin Properties")
                for key in sorted(plugin_props.keys()):
                    value = plugin_props[key]
                    formatted_value = self._format_property_value(value)
                    self._add_property_row(key, value, formatted_value)
            
            # Add custom properties
            if custom_props:
                self._add_separator_row("Custom Properties")
                for key in sorted(custom_props.keys()):
                    value = custom_props[key]
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
            
            # Get loaded plugin IDs for property categorization
            plugin_ids = []
            if hasattr(self.app, 'plugin_manager'):
                for plugin_info in self.app.plugin_manager.get_plugins():
                    if plugin_info.state and plugin_info.state.is_loaded and plugin_info.id:
                        plugin_ids.append(plugin_info.id)
            
            # Separate remaining properties into plugin and custom
            plugin_props = {}
            custom_props = {}
            
            # Identify plugin properties
            for key in sorted([k for k in all_properties.keys() if k not in core_props]):
                is_plugin_prop = False
                for plugin_id in plugin_ids:
                    # Check common separator patterns
                    if (key.startswith(f"{plugin_id}:") or 
                        key.startswith(f"{plugin_id}.") or 
                        key.startswith(f"{plugin_id}_")):
                        plugin_props[key] = all_properties[key]
                        is_plugin_prop = True
                        break
                
                # If not a plugin property, it's a custom property
                if not is_plugin_prop:
                    custom_props[key] = all_properties[key]
            
            # Add plugin properties if any exist
            if plugin_props:
                self._add_separator_row("Plugin Properties")
                for key in sorted(plugin_props.keys()):
                    values = plugin_props[key]
                    if len(set(str(v) for v in values)) == 1:
                        formatted_value = self._format_property_value(values[0])
                        self._add_property_row(key, values[0], formatted_value)
                    else:
                        self._add_property_row(key, values, "<Multiple values>")
            
            # Add custom properties
            if custom_props:
                self._add_separator_row("Custom Properties")
                for key in sorted(custom_props.keys()):
                    values = custom_props[key]
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
        
        # Apply styling based on data type
        # If it's a URL, make it look like a link
        if isinstance(raw_value, str) and (raw_value.startswith('http://') or raw_value.startswith('https://')):
            value_item.setForeground(QBrush(QColor("blue")))
            font = value_item.font()
            font.setUnderline(True)
            value_item.setFont(font)
            value_item.setToolTip("Double-click to open in browser")
        # If it's a complex data type that can be expanded, style accordingly
        elif isinstance(raw_value, (dict, list)) or (isinstance(raw_value, str) and len(raw_value) > 100):
            if isinstance(raw_value, dict):
                value_item.setToolTip(f"Double-click to view dictionary details ({len(raw_value)} items)")
            elif isinstance(raw_value, list):
                value_item.setToolTip(f"Double-click to view list details ({len(raw_value)} items)")
            else:
                value_item.setToolTip("Double-click to view full text")
            
            # Use a slightly different style to indicate it's interactive
            value_item.setForeground(QBrush(QColor("#505050")))
            font = value_item.font()
            font.setBold(True)
            value_item.setFont(font)
            
            # Add a visual indicator for expandable items
            if isinstance(raw_value, dict):
                value_item.setText(f"📋 {formatted_value}")
            elif isinstance(raw_value, list):
                value_item.setText(f"📋 {formatted_value}")
            elif isinstance(raw_value, str) and len(raw_value) > 100:
                value_item.setText(f"📝 {formatted_value}")
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
        dialog = SettingsDialog(self.config, self.app.plugin_manager, self)
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
                self.refresh_workspace_ui()
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
                        # Refresh all UI components
                        self.refresh_workspace_ui()
                        dialog.accept()
                    else:
                        self.status_bar.showMessage(f"Failed to load workspace: {name}", 3000)
        
        delete_button.clicked.connect(on_delete)
        switch_button.clicked.connect(on_switch)
        close_button.clicked.connect(dialog.reject)
        
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
    def on_report_issue(self):
        """Show the report issue dialog"""
        from .report_issue_dialog import ReportIssueDialog
        dialog = ReportIssueDialog(self.app, self)
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
        """Initialize and setup the update checker"""
        try:
            from ..core.update_checker import UpdateChecker
            self.update_checker = UpdateChecker(self.config)
            
            # Set the connectivity manager for network checks
            if hasattr(self, 'connectivity_manager') and self.connectivity_manager:
                self.update_checker.set_connectivity_manager(self.connectivity_manager)
            
            # Connect signals
            self.update_checker.update_available.connect(self.on_update_available)
            
            logger.debug("Update checker initialized")
        except Exception as e:
            logger.error(f"Failed to initialize update checker: {e}")
            self.update_checker = None

    @require_connectivity()
    def check_for_updates(self, silent=True):
        """Check for updates"""
        if not hasattr(self, 'update_checker') or not self.update_checker:
            logger.warning("Update checker not available")
            return
            
        def check_thread():
            try:
                branch = self.update_checker.get_branch()
                logger.info(f"Checking for updates on branch: {branch}")
                self.update_checker.check_for_updates(branch)
            except Exception as e:
                logger.error(f"Error checking for updates: {e}")
        
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
            # For dictionaries, show a preview of the content instead of just item count
            if not value:
                return "Empty dictionary"
            
            # Create a preview of dictionary contents
            preview_items = []
            for i, (k, v) in enumerate(value.items()):
                if i >= 3:  # Limit to first 3 key-value pairs
                    preview_items.append("...")
                    break
                # Format the key-value pair
                v_str = str(v)
                if isinstance(v, str) and len(v) > 20:
                    v_str = v[:17] + "..."
                elif isinstance(v, (dict, list)):
                    v_str = f"({type(v).__name__})"
                preview_items.append(f"{k}: {v_str}")
            
            return f"{{{', '.join(preview_items)}}} ({len(value)} items)"
            
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
                
        # For all other types, convert to string
        return str(value)

    def _show_detailed_property(self, key, value):
        """Show a property value in detail in a dialog
        
        Args:
            key: The property key
            value: The property value
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Property Details: {key}")
        dialog.resize(600, 450)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Add the property name and basic info
        header_layout = QHBoxLayout()
        
        # Property name
        name_label = QLabel(f"<b>{key}</b>")
        name_label.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(name_label)
        
        # Type information
        type_label = QLabel(f"Type: <code>{type(value).__name__}</code>")
        type_label.setStyleSheet("color: #606060;")
        header_layout.addWidget(type_label, alignment=Qt.AlignRight)
        
        layout.addLayout(header_layout)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Create a view button layout with options for different view modes
        view_options_layout = QHBoxLayout()
        
        # JSON view button
        json_view_btn = QPushButton("JSON View")
        json_view_btn.setCheckable(True)
        json_view_btn.setChecked(True)
        
        # Table view button (for dictionaries and list of dictionaries)
        table_view_btn = QPushButton("Table View")
        table_view_btn.setCheckable(True)
        table_view_btn.setEnabled(self._can_display_as_table(value))
        
        # Raw view button
        raw_view_btn = QPushButton("Raw View")
        raw_view_btn.setCheckable(True)
        
        # Add buttons to layout
        view_options_layout.addWidget(json_view_btn)
        view_options_layout.addWidget(table_view_btn)
        view_options_layout.addWidget(raw_view_btn)
        view_options_layout.addStretch()
        
        # Add view options to main layout
        layout.addLayout(view_options_layout)
        
        # Create a stacked widget to hold different views
        from PySide6.QtWidgets import QStackedWidget, QTableWidget, QTableWidgetItem
        stacked_widget = QStackedWidget()
        
        # JSON View with syntax highlighting for structured data
        json_view = QTextBrowser()
        json_view.setOpenExternalLinks(True)
        json_view.setStyleSheet("""
            QTextBrowser {
                font-family: "Consolas", "Monaco", monospace;
                font-size: 12px;
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        # Format content based on the type and create JSON view
        self._format_json_view(json_view, value)
        stacked_widget.addWidget(json_view)
        
        # Table View for dictionaries and lists of dictionaries
        table_view = QTableWidget()
        table_view.setAlternatingRowColors(True)
        table_view.horizontalHeader().setStretchLastSection(True)
        table_view.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #E0E0E0;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #D0D0D0;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)
        
        # Populate table view if possible
        self._populate_table_view(table_view, value)
        stacked_widget.addWidget(table_view)
        
        # Raw View
        raw_view = QTextBrowser()
        raw_view.setStyleSheet("""
            QTextBrowser {
                font-family: "Consolas", "Monaco", monospace;
                font-size: 12px;
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        raw_view.setPlainText(str(value))
        stacked_widget.addWidget(raw_view)
        
        layout.addWidget(stacked_widget)
        
        # Set up button group for view selection
        from PySide6.QtWidgets import QButtonGroup
        view_button_group = QButtonGroup()
        view_button_group.addButton(json_view_btn, 0)
        view_button_group.addButton(table_view_btn, 1)
        view_button_group.addButton(raw_view_btn, 2)
        
        # Connect button group to stacked widget
        view_button_group.buttonClicked.connect(
            lambda button: stacked_widget.setCurrentIndex(view_button_group.id(button))
        )
        
        # Add bottom button row
        button_layout = QHBoxLayout()
        
        # Copy button
        copy_button = QPushButton("Copy")
        copy_button.setToolTip("Copy to clipboard")
        copy_button.clicked.connect(lambda: self._copy_property_value_to_clipboard(value))
        button_layout.addWidget(copy_button)
        
        # Export button for structured data
        if isinstance(value, (dict, list)):
            export_button = QPushButton("Export")
            export_button.setToolTip("Export to file")
            export_button.clicked.connect(lambda: self._export_property_value(key, value))
            button_layout.addWidget(export_button)
        
        # Spacer to push close button to the right
        button_layout.addStretch()
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _can_display_as_table(self, value):
        """Check if the value can be displayed as a table
        
        Args:
            value: The value to check
            
        Returns:
            bool: True if the value can be displayed as a table
        """
        # Simple dictionary with simple values
        if isinstance(value, dict):
            return True
            
        # List of dictionaries with consistent keys
        if isinstance(value, list) and len(value) > 0 and all(isinstance(item, dict) for item in value):
            # Check if all dictionaries have the same keys
            keys = set(value[0].keys())
            return all(set(item.keys()) == keys for item in value)
        
        # Single level nested dictionary where all second-level values are simple types
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, dict):
                    for inner_k, inner_v in v.items():
                        if isinstance(inner_v, (dict, list)):
                            return False
            return True
            
        return False
    
    def _format_json_view(self, text_browser, value):
        """Format a value for display in the JSON view
        
        Args:
            text_browser: The QTextBrowser to display the content in
            value: The value to format
        """
        if isinstance(value, dict):
            try:
                import json
                formatted_json = json.dumps(value, indent=2, sort_keys=True)
                
                # Apply basic syntax highlighting using HTML
                highlighted_text = self._highlight_json(formatted_json)
                text_browser.setHtml(highlighted_text)
            except Exception:
                # Fallback to plain text if JSON highlighting fails
                text_browser.setPlainText(str(value))
                
        elif isinstance(value, list):
            # Different handling based on list content
            if all(isinstance(item, dict) for item in value) and len(value) > 0:
                # List of dictionaries - format as JSON with syntax highlighting
                try:
                    import json
                    formatted_json = json.dumps(value, indent=2, sort_keys=True)
                    highlighted_text = self._highlight_json(formatted_json)
                    text_browser.setHtml(highlighted_text)
                except Exception:
                    # Fallback to simple list format
                    content = "<ol>\n"
                    for item in value:
                        content += f"<li>{html.escape(str(item))}</li>\n"
                    content += "</ol>"
                    text_browser.setHtml(content)
            else:
                # Simple list with numbered items
                import html
                content = "<ol>\n"
                for item in value:
                    content += f"<li>{html.escape(str(item))}</li>\n"
                content += "</ol>"
                text_browser.setHtml(content)
        else:
            # For strings, handle URLs and multi-line text appropriately
            if isinstance(value, str):
                import html
                if value.startswith('http://') or value.startswith('https://'):
                    text_browser.setHtml(f'<a href="{html.escape(value)}">{html.escape(value)}</a>')
                elif '\n' in value:
                    # For multi-line text, preserve formatting with <pre> tags
                    text_browser.setHtml(f'<pre>{html.escape(value)}</pre>')
                else:
                    text_browser.setPlainText(value)
            else:
                text_browser.setPlainText(str(value))
    
    def _populate_table_view(self, table_widget, value):
        """Populate a table widget with the provided data
        
        Args:
            table_widget: The QTableWidget to populate
            value: The value to display in the table
        """
        table_widget.clear()
        
        # Case 1: Dictionary with simple values
        if isinstance(value, dict) and not any(isinstance(v, (dict, list)) for v in value.values()):
            table_widget.setColumnCount(2)
            table_widget.setHorizontalHeaderLabels(["Key", "Value"])
            table_widget.setRowCount(len(value))
            
            for i, (k, v) in enumerate(sorted(value.items())):
                key_item = QTableWidgetItem(str(k))
                value_item = QTableWidgetItem(str(v))
                key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
                value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
                
                # Format boolean values
                if isinstance(v, bool):
                    value_item.setText("Yes" if v else "No")
                
                table_widget.setItem(i, 0, key_item)
                table_widget.setItem(i, 1, value_item)
                
            table_widget.resizeColumnsToContents()
            
        # Case 2: List of dictionaries with consistent keys
        elif isinstance(value, list) and len(value) > 0 and all(isinstance(item, dict) for item in value):
            # Get all keys from the first dictionary
            keys = list(value[0].keys())
            
            # Set column count and headers
            table_widget.setColumnCount(len(keys))
            table_widget.setHorizontalHeaderLabels(keys)
            table_widget.setRowCount(len(value))
            
            # Add data
            for row, item in enumerate(value):
                for col, key in enumerate(keys):
                    # Get value or empty string if key is missing
                    val = item.get(key, "")
                    table_item = QTableWidgetItem(str(val))
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    table_widget.setItem(row, col, table_item)
                    
            table_widget.resizeColumnsToContents()
            
        # Case 3: Nested dictionary (2 levels)
        elif isinstance(value, dict) and any(isinstance(v, dict) for v in value.values()):
            # Collect all second-level keys across all nested dictionaries
            all_inner_keys = set()
            for k, v in value.items():
                if isinstance(v, dict):
                    all_inner_keys.update(v.keys())
            
            # Convert to sorted list for consistent column order
            inner_keys = sorted(all_inner_keys)
            
            # Set column count and headers (first column for the outer key, rest for inner keys)
            table_widget.setColumnCount(1 + len(inner_keys))
            headers = ["Item"] + inner_keys
            table_widget.setHorizontalHeaderLabels(headers)
            
            # Count rows (one for each outer key that has a dictionary value)
            rows = sum(1 for k, v in value.items() if isinstance(v, dict))
            rows = max(1, rows)  # Ensure at least one row
            table_widget.setRowCount(rows)
            
            # Add data
            row = 0
            for outer_key, outer_value in sorted(value.items()):
                if isinstance(outer_value, dict):
                    # Set outer key in first column
                    key_item = QTableWidgetItem(str(outer_key))
                    key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
                    table_widget.setItem(row, 0, key_item)
                    
                    # Fill inner values
                    for col, inner_key in enumerate(inner_keys, 1):
                        inner_value = outer_value.get(inner_key, "")
                        value_item = QTableWidgetItem(str(inner_value))
                        value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
                        table_widget.setItem(row, col, value_item)
                    
                    row += 1
                    
            table_widget.resizeColumnsToContents()
        
        # If we couldn't make a table view, show a message
        if table_widget.rowCount() == 0:
            table_widget.setRowCount(1)
            table_widget.setColumnCount(1)
            table_widget.setHorizontalHeaderLabels(["Message"])
            message = QTableWidgetItem("Cannot display this data in table format")
            message.setFlags(message.flags() & ~Qt.ItemIsEditable)
            message.setTextAlignment(Qt.AlignCenter)
            table_widget.setItem(0, 0, message)
            
        # Optimize the view
        table_widget.horizontalHeader().setStretchLastSection(True)
        table_widget.resizeRowsToContents()
    
    def _highlight_json(self, json_str):
        """Apply basic syntax highlighting to JSON string
        
        Args:
            json_str: JSON string to highlight
            
        Returns:
            HTML formatted string with syntax highlighting
        """
        import html
        highlighted = html.escape(json_str)
        
        # Highlight strings (anything in quotes)
        highlighted = re.sub(
            r'(".*?")(?=:)', 
            r'<span style="color: #0000CD;">\1</span>', 
            highlighted
        )
        # Highlight values
        highlighted = re.sub(
            r': (".*?")(,|\n|$)', 
            r': <span style="color: #008000;">\1</span>\2', 
            highlighted
        )
        # Highlight numbers
        highlighted = re.sub(
            r'(: |\[)(\d+\.?\d*)(,|\n|$|\])', 
            r'\1<span style="color: #0000FF;">\2</span>\3', 
            highlighted
        )
        # Highlight booleans and null
        highlighted = re.sub(
            r': (true|false|null)(,|\n|$)', 
            r': <span style="color: #B22222;">\1</span>\2', 
            highlighted
        )
        
        # Wrap in pre tag for formatting
        return f'<pre style="margin: 0;">{highlighted}</pre>'
    
    def _copy_property_value_to_clipboard(self, value):
        """Copy property value to clipboard
        
        Args:
            value: The value to copy
        """
        clipboard = QApplication.clipboard()
        
        if isinstance(value, (dict, list)):
            import json
            try:
                # Format as JSON for structured data
                formatted_json = json.dumps(value, indent=2)
                clipboard.setText(formatted_json)
            except:
                clipboard.setText(str(value))
        else:
            clipboard.setText(str(value))
            
        self.status_bar.showMessage("Value copied to clipboard", 2000)
    
    def _export_property_value(self, key, value):
        """Export property value to a file
        
        Args:
            key: The property key/name
            value: The value to export
        """
        if not isinstance(value, (dict, list)):
            return
            
        # Create a file dialog to get the save location
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setNameFilter("JSON files (*.json);;All files (*.*)")
        file_dialog.setDefaultSuffix("json")
        file_dialog.selectFile(f"{key}.json")
        
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            
            try:
                with open(file_path, 'w') as f:
                    import json
                    json.dump(value, f, indent=2)
                self.status_bar.showMessage(f"Exported to {file_path}", 3000)
            except Exception as e:
                logger.error(f"Error exporting property value: {e}")
                QMessageBox.critical(
                    self, 
                    "Export Error", 
                    f"An error occurred while exporting: {str(e)}"
                )
    
    def _handle_property_double_click(self, row, column):
        """Handle double click on a property row
        
        Args:
            row: The row that was double-clicked
            column: The column that was double-clicked
        """
        # Only process double clicks on the value column (1) for valid rows
        if column == 1 and row < self.properties_table.rowCount():
            # Skip if it's a separator row (span > 1)
            if self.properties_table.columnSpan(row, 0) > 1:
                return
                
            # Get the property value and name
            value_item = self.properties_table.item(row, 1)
            name_item = self.properties_table.item(row, 0)
            
            if value_item and name_item:
                raw_value = value_item.data(Qt.UserRole)
                key = name_item.text()
                
                # Check if this is an editable property and we have a single device selected
                selected_devices = self.device_manager.get_selected_devices()
                if len(selected_devices) == 1 and self._is_editable_property(key):
                    self._edit_property_inline(row, key, raw_value, selected_devices[0])
                    return
                
                # Open detailed view for dictionaries, lists, or long strings
                if isinstance(raw_value, (dict, list)) or (isinstance(raw_value, str) and len(raw_value) > 100):
                    self._show_detailed_property(key, raw_value)
                # For URLs, open in browser
                elif isinstance(raw_value, str) and (raw_value.startswith('http://') or raw_value.startswith('https://')):
                    import webbrowser
                    webbrowser.open(raw_value)
    
    def _is_editable_property(self, property_key):
        """Check if a property can be edited inline
        
        Args:
            property_key: The property key to check
            
        Returns:
            bool: True if the property can be edited
        """
        # Core properties that can be edited
        editable_core_props = ["alias", "hostname", "ip_address", "mac_address", "notes", "tags"]
        
        # Check if it's a core editable property
        if property_key in editable_core_props:
            return True
            
        # Allow editing of custom properties (not plugin properties)
        if not any(sep in property_key for sep in [':', '.', '_']) or property_key.startswith('custom_'):
            return True
            
        return False
    
    def _edit_property_inline(self, row, property_key, current_value, device):
        """Enable inline editing of a property
        
        Args:
            row: The table row
            property_key: The property to edit
            current_value: Current property value
            device: The device being edited
        """
        # Get the value item
        value_item = self.properties_table.item(row, 1)
        if not value_item:
            return
            
        # Create an input dialog for editing
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        
        # Format the current value for editing
        if isinstance(current_value, list):
            edit_value = ', '.join(str(v) for v in current_value)
        else:
            edit_value = str(current_value) if current_value is not None else ""
        
        # Show input dialog
        new_value, ok = QInputDialog.getText(
            self,
            f"Edit {property_key}",
            f"Enter new value for '{property_key}':",
            text=edit_value
        )
        
        if ok and new_value != edit_value:
            # Process the new value
            processed_value = self._process_edited_value(property_key, new_value)
            
            # Update the device
            try:
                device.set_property(property_key, processed_value)
                
                # Update the display
                formatted_value = self._format_property_value(processed_value)
                value_item.setText(formatted_value)
                value_item.setData(Qt.UserRole, processed_value)
                
                # Emit device changed signal
                self.device_manager.device_changed.emit(device)
                
                self.status_bar.showMessage(f"Updated {property_key} for {device.get_property('alias', 'device')}", 3000)
                
            except Exception as e:
                logger.error(f"Error updating property {property_key}: {e}")
                QMessageBox.warning(
                    self,
                    "Edit Error",
                    f"Failed to update property '{property_key}': {str(e)}"
                )
    
    def _process_edited_value(self, property_key, new_value):
        """Process an edited value based on the property type
        
        Args:
            property_key: The property being edited
            new_value: The new string value from input
            
        Returns:
            The processed value in the correct type
        """
        # Handle special properties that should be lists
        if property_key in ['tags']:
            if not new_value.strip():
                return []
            # Split by comma and clean up
            return [tag.strip() for tag in new_value.split(',') if tag.strip()]
        
        # For other properties, return as string (but empty string as None for cleanliness)
        return new_value if new_value.strip() else None
    
    @Slot(bool)
    def on_connectivity_changed(self, is_online):
        """Handle connectivity status changes
        
        Args:
            is_online: True if online, False if offline
        """
        logger.info(f"Connectivity changed: {'Online' if is_online else 'Offline'}")
        self._update_connectivity_status()
        self.updateWindowTitle()  # Update window title to reflect connectivity
        
        # Show a temporary message in the status bar
        if is_online:
            self.status_bar.showMessage("Internet connectivity restored", 3000)
        else:
            self.status_bar.showMessage("No internet connection detected", 5000)
    
    def _update_connectivity_status(self):
        """Update the connectivity status indicator in the status bar"""
        if not self.connectivity_manager:
            self.status_connectivity.setText("Unknown")
            self.status_connectivity.setStyleSheet("color: gray;")
            return
            
        is_online = self.connectivity_manager.is_online()
        status_text = self.connectivity_manager.get_status_text()
        
        if is_online:
            self.status_connectivity.setText(f"🌐 {status_text}")
            self.status_connectivity.setStyleSheet("color: green; font-weight: bold;")
            self.status_connectivity.setToolTip("Internet connection available")
        else:
            self.status_connectivity.setText(f"📵 {status_text}")
            self.status_connectivity.setStyleSheet("color: red; font-weight: bold;")
            self.status_connectivity.setToolTip("No internet connection - some features may be limited")