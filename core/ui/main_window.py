#!/usr/bin/env python3
# netWORKS - Main Window UI Component
"""
Main window module for the netWORKS application.
This file defines the MainWindow class, which is the central UI component of the application.
"""

import sys
import os
import json
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QSplitter, QToolBar, QStatusBar, QMessageBox, QLabel, QProgressBar, QTabWidget,
    QToolButton, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QSize, QEvent, QTimer, Signal
from PySide6.QtGui import QIcon, QAction

from core.ui.panels.left_panel import LeftPanel
from core.ui.panels.right_panel import RightPanel
from core.ui.panels.bottom_panel import BottomPanel
from core.ui.table.device_table import DeviceTable
from core.ui.menu.main_menu import setup_main_menu
from core.database.device_manager import DeviceDatabaseManager
from core.database.bridge_db_manager import BridgeDatabaseManager
from core.workspace import WorkspaceManager
from core.ui.toolbar import WorkspaceToolbar
from core.ui.dialogs import WorkspaceSelectionDialog

# Import modularized components
from core.ui.workspace import (
    show_workspace_dialog, on_workspace_selected, 
    create_new_workspace, save_workspace_data, 
    autosave_workspace, import_workspace_data, export_workspace_data
)
from core.ui.update import (
    check_for_updates, show_update_dialog, 
    start_update_process, disable_update_reminders
)
from core.ui.toolbar import (
    create_toolbar_group, add_toolbar_separator,
    update_toolbar_groups_visibility
)
from core.ui.table import (
    customize_table_columns, manage_device_aliases
)
from core.ui.panels import (
    register_panel, remove_panel, toggle_left_panel,
    toggle_right_panel, toggle_bottom_panel,
    refresh_plugin_panels
)
from core.ui.dialogs import show_error_dialog

class MainWindow(QMainWindow):
    """Main application window for NetSCAN."""
    
    def __init__(self, plugin_manager):
        super().__init__()
        
        self.plugin_manager = plugin_manager
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing main window")
        
        # Initialize menus dictionary
        self.menus = {}
        self.menu_actions = {}
        
        # Initialize database manager
        self.database_manager = BridgeDatabaseManager(self)
        self.logger.debug("Database manager initialized")
        
        # Initialize workspace manager
        self.workspace_manager = WorkspaceManager(self)
        self.logger.debug("Workspace manager initialized")
        
        # Initialize config first
        self.load_config()
        
        # Create the toolbar first
        self.setup_toolbar()
        
        # Setup main menu and transfer actions to ribbon
        self.setup_menus()
        
        # Initialize UI components
        self.init_ui()
        
        # Set up workspace toolbar
        self.setup_workspace_toolbar()
        
        # Set up autosave timer
        from PySide6.QtCore import QTimer
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave_workspace)
        # Get autosave interval from config (in seconds, default 5 minutes)
        autosave_interval = self.config.get("app", {}).get("auto_save_interval", 300) * 1000  # Convert to milliseconds
        self.autosave_timer.start(autosave_interval)
        self.logger.info(f"Autosave timer started with interval of {autosave_interval/1000} seconds")
        
        # Check for updates after a small delay to ensure UI is fully loaded
        QTimer.singleShot(2000, self.check_for_updates)
        
        # Set main window reference in plugin APIs after UI is initialized
        try:
            for plugin_id, plugin_info in self.plugin_manager.plugins.items():
                if plugin_info.get("enabled", False) and plugin_info.get("instance"):
                    plugin_api = self.plugin_manager.plugin_apis.get(plugin_id)
                    if plugin_api:
                        try:
                            plugin_api.set_main_window(self)
                            self.logger.info(f"Set main window reference for plugin {plugin_id}")
                        except Exception as e:
                            self.logger.error(f"Error setting main window for plugin {plugin_id}: {str(e)}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Error initializing plugins: {str(e)}", exc_info=True)
            # Show error dialog but continue
            self.show_error_dialog("Plugin Initialization Error", 
                                  f"There was an error initializing one or more plugins: {str(e)}\n\n"
                                  "The application will continue to run with limited functionality.")
    
    def load_config(self):
        """Load application configuration."""
        config_path = os.path.join('config', 'settings.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                self.config = self.get_default_config()
                print(f"Error loading config: {e}")
        else:
            self.config = self.get_default_config()
            os.makedirs('config', exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
    
    def get_default_config(self):
        """Return default configuration."""
        return {
            "app": {
                "theme": "light",
                "auto_save_interval": 300
            },
            "ui": {
                "panels": {
                    "left": {"visible": True, "width": 250},
                    "right": {"visible": True, "width": 300},
                    "bottom": {"visible": True, "height": 200}
                },
                "toolbar": {
                    "visible": True,
                    "pinned": False,
                    "position": "top",
                    "categories": {}
                },
                "table": {
                    "columns": [
                        "ip",
                        "hostname",
                        "mac",
                        "vendor",
                        "scan_method",
                        "ports",
                        "last_seen"
                    ],
                    "sort_by": "ip",
                    "sort_direction": "ascending"
                }
            }
        }
    
    def init_ui(self):
        """Initialize the user interface."""
        self.logger.debug("Setting up main window UI")
        self.setWindowTitle("NetSCAN")
        self.resize(1200, 800)
        
        # Import global styles
        try:
            from core.ui.styles import apply_button_styles, BUTTON_STYLE, TOOL_BUTTON_STYLE
            self.logger.debug("Imported global UI styles")
        except ImportError:
            self.logger.warning("Global UI styles not found, using default styles")
            
        # Main layout for central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create horizontal splitter for left panel, central area, and right panel
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create left panel
        self.left_panel = LeftPanel(self)
        self.h_splitter.addWidget(self.left_panel)
        
        # Create central area with device table and bottom panel
        central_area = QWidget()
        central_layout = QVBoxLayout(central_area)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        
        # Create device table
        self.device_table = DeviceTable(self)
        central_layout.addWidget(self.device_table)
        
        # Create vertical splitter for device table and bottom panel
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.addWidget(central_area)
        
        # Create bottom panel
        self.bottom_panel = BottomPanel(self)
        self.v_splitter.addWidget(self.bottom_panel)
        
        # Add vertical splitter to horizontal splitter
        self.h_splitter.addWidget(self.v_splitter)
        
        # Create right panel
        self.right_panel = RightPanel(self)
        self.h_splitter.addWidget(self.right_panel)
        
        # Set initial splitter sizes based on config
        self.h_splitter.setSizes([
            self.config["ui"]["panels"]["left"]["width"],
            self.width() - self.config["ui"]["panels"]["left"]["width"] - self.config["ui"]["panels"]["right"]["width"],
            self.config["ui"]["panels"]["right"]["width"]
        ])
        
        self.v_splitter.setSizes([
            self.height() - self.config["ui"]["panels"]["bottom"]["height"],
            self.config["ui"]["panels"]["bottom"]["height"]
        ])
        
        # Force panel visibility
        self.left_panel.setVisible(True)
        self.right_panel.setVisible(True)
        self.bottom_panel.setVisible(True)
        
        # Add splitter to main layout
        main_layout.addWidget(self.h_splitter)
        
        # Status bar setup
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)
        
        # Status message
        self.status_label = QLabel("Ready")
        self.statusBar.addWidget(self.status_label)
        
        # Apply global button styles to all buttons after the toolbar is set up
        QTimer.singleShot(100, self.apply_button_styles_to_toolbar)
        
        # Update toolbar groups visibility after all initialization is done
        QTimer.singleShot(100, self.update_toolbar_groups_visibility)
        
        self.logger.debug("Main window UI setup complete")
    
    def apply_button_styles_to_toolbar(self):
        """Apply consistent button styles to all toolbar buttons."""
        try:
            from core.ui.styles import apply_button_styles
            # Apply styles to all toolbar buttons
            apply_button_styles(self.toolbar)
            self.logger.debug("Applied button styles to toolbar")
        except Exception as e:
            self.logger.warning(f"Could not apply button styles to toolbar: {str(e)}")
    
    def setup_toolbar(self):
        """Set up the application ribbon toolbar."""
        # Create toolbar with tabs
        self.toolbar = QTabWidget()
        self.toolbar.setMovable(False)
        self.toolbar.setDocumentMode(True)
        
        # Apply styling to tabs and buttons
        self.toolbar.setStyleSheet("""
            /* Tabbar styling - simple with just underlines */
            QTabBar::tab {
                background: transparent;
                color: #555555;
                border: none;
                padding: 6px 12px;
                margin-right: 5px;
                font-weight: normal;
                min-width: 70px;
                min-height: 20px;
            }
            
            QTabBar::tab:selected {
                background: transparent;
                color: #2c5aa0;
                border-bottom: 2px solid #2c5aa0;
                font-weight: bold;
            }
            
            QTabBar::tab:hover:!selected {
                background: transparent;
                color: #496b99;
                border-bottom: 1px solid #c0d0f0;
            }
            
            /* Button styling */
            QToolButton {
                background-color: transparent;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                padding: 2px;
                color: #2c5aa0;
                font-size: 8pt;
                font-weight: bold;
                min-width: 45px;
                min-height: 40px;
                text-align: center;
            }
            QToolButton:hover {
                background-color: #e8f0ff;
                border: 1px solid #c0d0f0;
            }
            QToolButton:pressed {
                background-color: #d0e0ff;
                border: 1px solid #a0b0e0;
                padding-top: 3px;
                padding-left: 3px;
                padding-bottom: 1px;
                padding-right: 1px;
            }
            QToolButton:checked {
                background-color: #d0e0ff;
                border: 1px solid #a0b0e0;
            }
            
            /* Group styling - material design inspired panels */
            QWidget[ribbonGroup="true"] {
                background-color: transparent;
                border-right: 1px solid #e0e0e0;
                margin: 1px;
                padding: 2px;
            }
            QLabel[groupTitle="true"] {
                color: #666666;
                font-weight: bold;
                font-size: 8pt;
                text-align: center;
                padding-top: 2px;
            }
        """)
        
        # Create tabs
        self.home_tab = QWidget()
        self.view_tab = QWidget()
        self.tools_tab = QWidget()
        self.plugins_tab = QWidget()
        self.help_tab = QWidget()
        
        # Add tabs to toolbar
        self.toolbar.addTab(self.home_tab, "Home")
        self.toolbar.addTab(self.view_tab, "View")
        self.toolbar.addTab(self.tools_tab, "Tools")
        self.toolbar.addTab(self.plugins_tab, "Plugins")
        self.toolbar.addTab(self.help_tab, "Help")
        
        # Set layouts for tabs with left alignment
        self.home_tab.setLayout(QHBoxLayout())
        self.home_tab.layout().setSpacing(0)
        self.home_tab.layout().setContentsMargins(2, 1, 2, 0)
        self.home_tab.layout().setAlignment(Qt.AlignLeft)
        
        self.view_tab.setLayout(QHBoxLayout())
        self.view_tab.layout().setSpacing(0)
        self.view_tab.layout().setContentsMargins(2, 1, 2, 0)
        self.view_tab.layout().setAlignment(Qt.AlignLeft)
        
        self.tools_tab.setLayout(QHBoxLayout())
        self.tools_tab.layout().setSpacing(0)
        self.tools_tab.layout().setContentsMargins(2, 1, 2, 0)
        self.tools_tab.layout().setAlignment(Qt.AlignLeft)
        
        self.plugins_tab.setLayout(QHBoxLayout())
        self.plugins_tab.layout().setSpacing(0)
        self.plugins_tab.layout().setContentsMargins(2, 1, 2, 0)
        self.plugins_tab.layout().setAlignment(Qt.AlignLeft)
        
        self.help_tab.setLayout(QHBoxLayout())
        self.help_tab.layout().setSpacing(0)
        self.help_tab.layout().setContentsMargins(2, 1, 2, 0)
        self.help_tab.layout().setAlignment(Qt.AlignLeft)
        
        # Create toolbar groups
        self.file_group = self.create_toolbar_group("File", self.home_tab)
        
        # Create Workspace group 
        self.workspace_group = self.create_toolbar_group("Workspace", self.home_tab)
        
        # Create other standard groups
        self.edit_group = self.create_toolbar_group("Edit", self.home_tab)
        self.add_toolbar_separator(self.home_tab)
        self.clipboard_group = self.create_toolbar_group("Clipboard", self.home_tab)
        
        # Add Save button to File group
        save_action = QAction("Save", self)
        save_action.setIcon(QIcon.fromTheme("document-save"))
        save_action.setToolTip("Save devices and settings to database")
        save_action.triggered.connect(self.save_workspace_data)
        
        save_button = QToolButton()
        save_button.setDefaultAction(save_action)
        save_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.file_group.layout().addWidget(save_button)
        
        # Add Import/Export buttons
        import_action = QAction("Import", self)
        import_action.setIcon(QIcon.fromTheme("document-open"))
        import_action.setToolTip("Import devices and settings from file")
        import_action.triggered.connect(self.import_workspace_data)
        
        import_button = QToolButton()
        import_button.setDefaultAction(import_action)
        import_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.file_group.layout().addWidget(import_button)
        
        export_action = QAction("Export", self)
        export_action.setIcon(QIcon.fromTheme("document-save-as"))
        export_action.setToolTip("Export devices and settings to file")
        export_action.triggered.connect(self.export_workspace_data)
        
        export_button = QToolButton()
        export_button.setDefaultAction(export_action)
        export_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.file_group.layout().addWidget(export_button)
        
        # Add Workspace management buttons
        new_workspace_action = QAction("New Workspace", self)
        new_workspace_action.setIcon(QIcon.fromTheme("document-new"))
        new_workspace_action.setToolTip("Create a new workspace")
        new_workspace_action.triggered.connect(self.create_new_workspace)
        
        new_workspace_button = QToolButton()
        new_workspace_button.setDefaultAction(new_workspace_action)
        new_workspace_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.workspace_group.layout().addWidget(new_workspace_button)
        
        switch_workspace_action = QAction("Switch Workspace", self)
        switch_workspace_action.setIcon(QIcon.fromTheme("view-refresh"))
        switch_workspace_action.setToolTip("Switch to a different workspace")
        switch_workspace_action.triggered.connect(self.show_workspace_dialog)
        
        switch_workspace_button = QToolButton()
        switch_workspace_button.setDefaultAction(switch_workspace_action)
        switch_workspace_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.workspace_group.layout().addWidget(switch_workspace_button)
        
        # Add groups to view tab
        self.display_group = self.create_toolbar_group("Display", self.view_tab)
        self.add_toolbar_separator(self.view_tab)
        self.panel_group = self.create_toolbar_group("Panels", self.view_tab)
        self.add_toolbar_separator(self.view_tab)
        
        # Add groups to tools tab
        self.scan_group = self.create_toolbar_group("Scan", self.tools_tab)
        self.add_toolbar_separator(self.tools_tab)
        self.device_group = self.create_toolbar_group("Devices", self.tools_tab)
        self.add_toolbar_separator(self.tools_tab)
        self.utilities_group = self.create_toolbar_group("Utilities", self.tools_tab)
        self.add_toolbar_separator(self.tools_tab)
        self.diagnostics_group = self.create_toolbar_group("Diagnostics", self.tools_tab)
        
        # Add groups to plugins tab
        self.plugins_group = self.create_toolbar_group("Installed Plugins", self.plugins_tab)
        self.network_group = self.create_toolbar_group("Network", self.plugins_tab)
        
        # Add groups to help tab
        self.help_group = self.create_toolbar_group("Help & Support", self.help_tab)
        self.add_toolbar_separator(self.help_tab)
        self.about_group = self.create_toolbar_group("About", self.help_tab)
        
        # Apply additional button styling
        self.apply_button_styles_to_toolbar()
        
        # Create a toolbar container and add to main window
        toolbar_widget = QToolBar("Main Toolbar")
        toolbar_widget.setMovable(False)
        toolbar_widget.setFloatable(False)
        
        self.toolbar_container = QWidget()
        self.toolbar_container.setLayout(QVBoxLayout())
        self.toolbar_container.layout().setContentsMargins(0, 0, 0, 0)
        self.toolbar_container.layout().setSpacing(0)
        self.toolbar_container.layout().addWidget(self.toolbar)
        
        toolbar_widget.addWidget(self.toolbar_container)
        self.addToolBar(Qt.TopToolBarArea, toolbar_widget)
        
        # Event handling for tab changes
        self.toolbar.currentChanged.connect(self.toolbar_tab_changed)
        
        # Handle visibility toggles
        self.toolbar_visible = True
        self.toolbar_pinned = True
        
        # Make sure toolbar is visible
        self.toolbar_container.setVisible(self.toolbar_visible)
    
    def create_new_workspace(self):
        """Show dialog to create a new workspace."""
        return create_new_workspace(self)
    
    def create_toolbar_group(self, title, parent_tab):
        """Create a group in the toolbar with the given title."""
        return create_toolbar_group(self, title, parent_tab)
    
    def add_toolbar_separator(self, parent_tab):
        """Add a separator to the toolbar tab."""
        return add_toolbar_separator(self, parent_tab)
    
    def update_toolbar_groups_visibility(self):
        """Update the visibility of toolbar groups."""
        return update_toolbar_groups_visibility(self)
    
    def transfer_menu_actions_to_toolbar(self):
        """Transfer menu actions to the ribbon toolbar tabs based on their category."""
        if not hasattr(self, 'menuBar'):
            self.logger.debug("Menu bar not available for transfer")
            return
        
        # Map menu names to ribbon tabs
        menu_to_tab = {
            'File': {'tab': self.home_tab, 'group': self.file_group},
            'Edit': {'tab': self.home_tab, 'group': self.edit_group},
            'View': {'tab': self.view_tab, 'group': self.display_group},
            'Tools': {'tab': self.tools_tab, 'group': self.utilities_group},
            'Plugins': {'tab': self.plugins_tab, 'group': self.plugins_group},
            'Help': {'tab': self.help_tab, 'group': self.help_group},
            'Diagnostics': {'tab': self.tools_tab, 'group': self.diagnostics_group},
            'Network': {'tab': self.plugins_tab, 'group': self.network_group},
            'Security': {'tab': self.tools_tab, 'group': self.create_toolbar_group("Security", self.tools_tab)}
        }
        
        # Default icon themes for different menus
        default_icons = {
            'File': 'document-new',
            'Edit': 'edit',
            'View': 'view-preview',
            'Tools': 'tools',
            'Plugins': 'plugin',
            'Help': 'help-contents',
            'Diagnostics': 'debug',
            'Network': 'network',
            'Security': 'security'
        }
        
        # Process each menu in the menu bar
        for menu_name, menu in self.menus.items():
            if menu_name in menu_to_tab:
                # Get corresponding tab and group
                target = menu_to_tab[menu_name]
                
                # Add all actions from this menu to the target group
                for action in menu.actions():
                    if not action.isSeparator():
                        # Create button for the action
                        from PySide6.QtWidgets import QToolButton
                        button = QToolButton()
                        button.setDefaultAction(action)
                        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                        
                        # If action doesn't have an icon, set a default one
                        if action.icon().isNull():
                            action.setIcon(QIcon.fromTheme(default_icons.get(menu_name, 'document')))
                        
                        # Add the button to the group
                        target['group'].layout().addWidget(button)
        
        self.logger.debug("Menu actions transferred to ribbon toolbar")

    def add_toolbar_widget(self, widget, tab_name="Home", group_name=None):
        """Add a widget or action to the toolbar.
        
        Args:
            widget (QWidget or QAction): The widget or action to add to the toolbar.
            tab_name (str): The name of the tab to add the widget to.
            group_name (str, optional): The name of the group to add the widget to.
                                     If not provided, will add to the first group in the tab.
        
        Returns:
            bool: True if the widget was added successfully, False otherwise.
        """
        # Make sure the toolbar is visible
        self.toolbar.setVisible(True)
        
        # Find the requested tab
        tab = None
        for i in range(self.toolbar.count()):
            if self.toolbar.tabText(i) == tab_name:
                tab = self.toolbar.widget(i)
                break
        
        # If tab not found, create it
        if not tab:
            tab = QWidget()
            tab.setLayout(QHBoxLayout())
            tab.layout().setSpacing(2)
            tab.layout().setContentsMargins(5, 5, 5, 5)
            self.toolbar.addTab(tab, tab_name)
        
        # If group specified, find or create it
        if group_name:
            group = None
            
            # Check if group already exists
            for i in range(tab.layout().count()):
                item = tab.layout().itemAt(i).widget()
                if item and item.property("ribbonGroup"):
                    title_label = item.layout().itemAt(0).widget()
                    if title_label and title_label.text() == group_name:
                        # Found matching group, get content widget
                        group = item.layout().itemAt(1).widget()
                        break
            
            # If group not found, create it
            if not group:
                group_container = QWidget()
                group_container.setProperty("ribbonGroup", True)
                group_container.setLayout(QVBoxLayout())
                group_container.layout().setSpacing(2)
                group_container.layout().setContentsMargins(5, 2, 5, 2)
                
                # Add styling to match our borderless design
                group_container.setStyleSheet("""
                    QWidget {
                        background-color: transparent;
                        border: none;
                        border-radius: 0;
                        margin: 2px;
                        padding: 4px;
                    }
                """)
                
                title_label = QLabel(group_name)
                title_label.setProperty("ribbonGroupTitle", True)
                title_label.setAlignment(Qt.AlignCenter)
                title_label.setStyleSheet("""
                    QLabel {
                        color: #2c5aa0;
                        font-size: 8pt;
                        padding: 2px 3px;
                        margin-top: 2px;
                        margin-bottom: 2px;
                        font-weight: bold;
                        text-align: center;
                        background-color: transparent;
                        border-radius: 0;
                        border-bottom: 1px solid #aabbcc;
                    }
                """)
                
                group = QWidget()
                group.setLayout(QHBoxLayout())
                group.layout().setSpacing(2)
                group.layout().setContentsMargins(0, 0, 0, 0)
                
                group_container.layout().addWidget(title_label)
                group_container.layout().addWidget(group)
                
                tab.layout().addWidget(group_container)
        else:
            # Use first group in tab if available
            if tab.layout().count() > 0:
                item = tab.layout().itemAt(0).widget()
                if item and item.property("ribbonGroup"):
                    group = item.layout().itemAt(1).widget()
                else:
                    # Create a default group
                    group = self.create_toolbar_group("General", tab)
            else:
                # Create a default group
                group = self.create_toolbar_group("General", tab)
        
        # Add the widget/action to the group
        if isinstance(widget, QAction):
            # Create a tool button for the action
            from PySide6.QtWidgets import QToolButton
            button = QToolButton()
            button.setDefaultAction(widget)
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            # Add to the group
            group.layout().addWidget(button)
        else:
            # It's a regular widget, just add it
            group.layout().addWidget(widget)
        
        # Switch to the tab where we added the widget
        for i in range(self.toolbar.count()):
            if self.toolbar.widget(i) == tab:
                self.toolbar.setCurrentIndex(i)
                break
        
        return True
    
    def toggle_toolbar(self, checked):
        """Toggle toolbar visibility."""
        self.toolbar.setVisible(checked)
        self.config["ui"]["toolbar"]["visible"] = checked
    
    def toggle_toolbar_pin(self, pinned):
        """Toggle the pin state of the toolbar."""
        self.toolbar_pinned = pinned
        
        # When unpinned, hide the toolbar content but keep tabs visible
        if not self.toolbar_pinned:
            # Save current tab for restoring later
            self.last_tab_index = self.toolbar.currentIndex()
            
            # Hide the toolbar contents except for tab bar
            for i in range(self.toolbar.count()):
                widget = self.toolbar.widget(i)
                if widget:
                    widget.setMaximumHeight(0)
                    widget.setVisible(False)
        else:
            # Show all tabs and restore previous tab
            for i in range(self.toolbar.count()):
                widget = self.toolbar.widget(i)
                if widget:
                    widget.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX 
                    widget.setVisible(True)
            
            # Restore the previously active tab if it exists
            if hasattr(self, 'last_tab_index'):
                self.toolbar.setCurrentIndex(self.last_tab_index)
    
    def _on_toolbar_visibility_changed(self, visible):
        """Handle toolbar visibility changes."""
        try:
            self.toolbar_visibility_action.setChecked(visible)
            if "ui" not in self.config:
                self.config["ui"] = {}
            if "toolbar" not in self.config["ui"]:
                self.config["ui"]["toolbar"] = {"visible": True, "pinned": False, "position": "top", "categories": {}}
            self.config["ui"]["toolbar"]["visible"] = visible
            self.logger.debug(f"Toolbar visibility changed to {visible}")
        except Exception as e:
            self.logger.error(f"Error updating toolbar visibility: {str(e)}")
    
    def toggle_left_panel(self, checked):
        """Toggle left panel visibility."""
        return toggle_left_panel(self, checked)
    
    def toggle_right_panel(self, checked):
        """Toggle right panel visibility."""
        return toggle_right_panel(self, checked)
    
    def toggle_bottom_panel(self, checked):
        """Toggle bottom panel visibility."""
        return toggle_bottom_panel(self, checked)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_config()
        event.accept()
    
    def save_config(self):
        """Save application configuration."""
        # Update config with current panel sizes
        left_width = self.left_panel.width()
        right_width = self.right_panel.width()
        bottom_height = self.bottom_panel.height()
        
        self.config["ui"]["panels"]["left"]["width"] = left_width
        self.config["ui"]["panels"]["right"]["width"] = right_width
        self.config["ui"]["panels"]["bottom"]["height"] = bottom_height
        
        # Save to file
        config_path = os.path.join('config', 'settings.json')
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def event(self, event):
        """Handle Qt events for the main window."""
        if event.type() == QEvent.Type.WindowActivate:
            self.logger.debug("Window activated")
        elif event.type() == QEvent.Type.WindowDeactivate:
            self.logger.debug("Window deactivated")
        return super().event(event)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        self.logger.debug(f"Mouse press event at {event.pos()}")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        self.logger.debug(f"Mouse release event at {event.pos()}")
        super().mouseReleaseEvent(event)

    def show_progress(self, show=True):
        """Show or hide the progress bar."""
        self.progress_bar.setVisible(show)
        if not show:
            self.progress_bar.setValue(0)
    
    def update_progress(self, value, maximum=None):
        """Update the progress bar value and optionally its maximum."""
        if maximum is not None:
            self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)

    def register_panel(self, panel, location, name=None):
        """Register a panel in the specified location."""
        return register_panel(self, panel, location, name)
    
    def remove_panel(self, panel):
        """Remove a panel from the UI."""
        return remove_panel(self, panel)
    
    def show_error_dialog(self, title, message):
        """Show an error dialog with the specified title and message."""
        return show_error_dialog(self, title, message)
    
    def customize_table_columns(self):
        """Show dialog for customizing device table columns."""
        return customize_table_columns(self)
    
    def manage_device_aliases(self):
        """Show dialog for managing device aliases."""
        return manage_device_aliases(self)
    
    def refresh_plugin_panels(self):
        """Refresh all plugin panels in the UI."""
        return refresh_plugin_panels(self)
    
    def check_for_updates(self):
        """Check for application updates."""
        return check_for_updates(self)
    
    def show_update_dialog(self, update_info):
        """Show the update dialog with update details."""
        return show_update_dialog(self, update_info)
    
    def start_update_process(self, update_info, dialog=None):
        """Start the update process by opening the download URL."""
        return start_update_process(self, update_info, dialog)
    
    def disable_update_reminders(self, dialog=None):
        """Disable update reminders by updating configuration."""
        return disable_update_reminders(self, dialog)
    
    def show_workspace_dialog(self):
        """Show the workspace selection dialog at startup."""
        return show_workspace_dialog(self)
    
    def on_workspace_selected(self, workspace_id):
        """Handle workspace selection from dialog."""
        return on_workspace_selected(self, workspace_id)
    
    def create_new_workspace(self):
        """Show dialog to create a new workspace."""
        return create_new_workspace(self)
    
    def save_workspace_data(self):
        """Save current workspace data."""
        return save_workspace_data(self)
    
    def autosave_workspace(self):
        """Automatically save workspace data at regular intervals."""
        return autosave_workspace(self)
    
    def import_workspace_data(self):
        """Import devices and settings from a file."""
        return import_workspace_data(self)
    
    def export_workspace_data(self):
        """Export devices and settings to a file."""
        return export_workspace_data(self)

    def toolbar_tab_changed(self, index):
        """Handle tab change events in the toolbar."""
        self.logger.debug(f"Toolbar tab changed: {index}")

    def setup_menus(self):
        """Setup the main menu bar and then hide it, using ribbon only."""
        # Set up main menu using the menu component
        from core.ui.menu.main_menu import setup_main_menu
        setup_main_menu(self)
        
        # Transfer all menu actions to the ribbon before hiding the menu bar
        self.transfer_menu_actions_to_toolbar()
        
        # Hide the menu bar since we're using the ribbon exclusively
        self.menuBar().setVisible(False)
        
        # Ensure all menus have proper mouse tracking and visibility settings
        for menu_name, menu in self.menus.items():
            menu.setMouseTracking(True)
            menu.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        self.logger.debug("Menu setup complete with ribbon-only interface")

    def setup_workspace_toolbar(self):
        """Set up the workspace toolbar component."""
        try:
            # Create workspace toolbar
            from core.ui.toolbar import WorkspaceToolbar
            
            # Check if we already have a reference to prevent duplication
            if not hasattr(self, 'workspace_toolbar'):
                # Create workspace toolbar instance
                self.workspace_toolbar = WorkspaceToolbar(self)
                
                # Add to the file group in the ribbon
                if hasattr(self, 'file_group'):
                    self.file_group.layout().addWidget(self.workspace_toolbar)
                    self.logger.debug("Added workspace toolbar to file group")
                else:
                    self.logger.warning("Could not add workspace toolbar to ribbon - no suitable group found")
        except Exception as e:
            self.logger.error(f"Error setting up workspace toolbar: {str(e)}")