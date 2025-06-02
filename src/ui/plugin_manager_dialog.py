#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Plugin manager dialog for NetWORKS
"""

from loguru import logger
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
    QListWidgetItem, QLabel, QTextEdit, QCheckBox, QWidget, QTabWidget,
    QGroupBox, QFormLayout, QMessageBox, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QScrollArea, QApplication, QDialogButtonBox, QSplitter, QInputDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QSettings, QTimer, QSize, QMargins, QRect, QPoint
from PySide6.QtGui import QIcon, QFont, QAction, QPixmap, QColor, QPainter, QPalette, QBrush, QLinearGradient, QShowEvent, QHideEvent, QIntValidator
import os

# Import from core
from src.core.plugin_manager import PluginState


class PluginListItem(QListWidgetItem):
    """Custom list widget item for plugins"""
    
    def __init__(self, plugin_info):
        """Initialize the list item"""
        super().__init__(plugin_info.name)
        
        self.plugin_info = plugin_info
        self.setToolTip(plugin_info.description)
        
        # Set icon based on plugin status
        self.update_icon()
        
    def update_icon(self):
        """Update the icon based on plugin status"""
        # Update the display text to show status
        status_text = ""
        
        if self.plugin_info.state.is_disabled:
            status_text = " [Disabled]"
            self.setForeground(Qt.gray)
            self.setIcon(QIcon())
        elif self.plugin_info.state.is_loaded:
            status_text = " [Loaded]"
            self.setForeground(Qt.black)
            # Use a green dot icon or similar for loaded plugins
            # This would be better with actual icons
            self.setIcon(QIcon())
        elif self.plugin_info.state.is_enabled:
            status_text = " [Enabled]"
            self.setForeground(Qt.darkGreen)
            self.setIcon(QIcon())
        elif self.plugin_info.state == self.plugin_info.state.ERROR:
            status_text = " [Error]"
            self.setForeground(Qt.red)
            self.setIcon(QIcon())
            
        self.setText(f"{self.plugin_info.name}{status_text}")


class PluginManagerDialog(QDialog):
    """Dialog for managing plugins"""
    
    def __init__(self, plugin_manager, parent=None):
        """Initialize the dialog"""
        super().__init__(parent)
        
        self.plugin_manager = plugin_manager
        
        # Set dialog properties
        self.setWindowTitle("Plugin Manager")
        self.resize(900, 600)
        
        # Create layout
        self.layout = QVBoxLayout(self)
        
        # Create top layout with plugin list and details
        self.top_layout = QHBoxLayout()
        
        # Plugin list with filter
        self.plugin_list_group = QGroupBox("Plugins")
        self.plugin_list_layout = QVBoxLayout(self.plugin_list_group)
        
        # Add search/filter
        self.filter_layout = QHBoxLayout()
        self.filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter plugins...")
        self.filter_input.textChanged.connect(self.filter_plugins)
        self.filter_layout.addWidget(self.filter_label)
        self.filter_layout.addWidget(self.filter_input)
        self.plugin_list_layout.addLayout(self.filter_layout)
        
        # Plugin list
        self.plugin_list = QListWidget()
        self.plugin_list.currentItemChanged.connect(self.on_plugin_selected)
        self.plugin_list_layout.addWidget(self.plugin_list)
        
        # Plugin action buttons
        self.plugin_actions_layout = QHBoxLayout()
        
        self.enable_button = QPushButton("Enable")
        self.enable_button.clicked.connect(self.on_enable_clicked)
        self.enable_button.setToolTip("Enable the selected plugin")
        self.enable_button.setEnabled(False)
        
        self.disable_button = QPushButton("Disable")
        self.disable_button.clicked.connect(self.on_disable_clicked)
        self.disable_button.setToolTip("Disable the selected plugin")
        self.disable_button.setEnabled(False)
        
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.on_load_clicked)
        self.load_button.setToolTip("Load the selected plugin")
        self.load_button.setEnabled(False)
        
        self.unload_button = QPushButton("Unload")
        self.unload_button.clicked.connect(self.on_unload_clicked)
        self.unload_button.setToolTip("Unload the selected plugin")
        self.unload_button.setEnabled(False)
        
        self.plugin_actions_layout.addWidget(self.enable_button)
        self.plugin_actions_layout.addWidget(self.disable_button)
        self.plugin_actions_layout.addWidget(self.load_button)
        self.plugin_actions_layout.addWidget(self.unload_button)
        
        self.plugin_list_layout.addLayout(self.plugin_actions_layout)
        
        # Add help text below action buttons
        self.action_help_label = QLabel(
            "1. Enable/Disable: Mark plugins for activation\n"
            "2. Load/Unload: Immediately start/stop plugins\n"
            "3. Save Changes: Apply Enable/Disable changes"
        )
        self.action_help_label.setStyleSheet("color: #666; font-style: italic; font-size: 9pt;")
        self.action_help_label.setWordWrap(True)
        self.plugin_list_layout.addWidget(self.action_help_label)
        
        # Plugin details
        self.plugin_details_group = QGroupBox("Plugin Details")
        self.plugin_details_layout = QVBoxLayout(self.plugin_details_group)
        
        # Create tab widget for details and settings
        self.plugin_tabs = QTabWidget()
        
        # Details tab
        self.details_tab = QWidget()
        self.details_layout = QVBoxLayout(self.details_tab)
        self.details_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create form layout for plugin details
        self.form_layout = QFormLayout()
        self.form_layout.setVerticalSpacing(10)
        self.form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Add plugin details
        self.id_label = QLabel("")
        self.id_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Plugin ID:", self.id_label)
        
        self.name_label = QLabel("")
        self.name_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Name:", self.name_label)
        
        self.version_label = QLabel("")
        self.version_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Version:", self.version_label)
        
        self.author_label = QLabel("")
        self.author_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Author:", self.author_label)
        
        # Prepare labels for min/max app version
        self.min_version_label = QLabel("")
        self.min_version_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Min App Version:", self.min_version_label)
        
        self.max_version_label = QLabel("")
        self.max_version_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Max App Version:", self.max_version_label)
        
        # Prepare label for dependencies
        self.deps_label = QLabel("")
        self.deps_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Dependencies:", self.deps_label)
        
        # Prepare labels for requirements
        self.reqs_label = QLabel("")
        self.reqs_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Python Requirements:", self.reqs_label)
        
        self.sys_reqs_label = QLabel("")
        self.sys_reqs_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("System Requirements:", self.sys_reqs_label)
        
        # Add entry point and path labels
        self.entry_point_label = QLabel("")
        self.entry_point_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Entry Point:", self.entry_point_label)
        
        self.path_label = QLabel("")
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.form_layout.addRow("Path:", self.path_label)
        
        # Add status label for showing current plugin status
        self.status_label = QLabel("")
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #444; font-weight: bold;")
        self.form_layout.addRow("Status:", self.status_label)
        
        self.details_layout.addLayout(self.form_layout)
        
        # Add a log widget for displaying plugin initialization progress
        self.log_group = QGroupBox("Plugin Load Log")
        self.log_layout = QVBoxLayout(self.log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setPlaceholderText("Plugin initialization log will appear here...")
        
        self.log_layout.addWidget(self.log_text)
        
        self.details_layout.addWidget(self.log_group)
        self.details_layout.addStretch(1)
        
        # Settings tab
        self.settings_tab = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_tab)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_container = QWidget()
        self.settings_form = QFormLayout(self.settings_container)
        self.settings_scroll.setWidget(self.settings_container)
        self.settings_layout.addWidget(self.settings_scroll)
        
        # Add a label for when no settings are available
        self.no_settings_label = QLabel("No settings available for this plugin")
        self.no_settings_label.setAlignment(Qt.AlignCenter)
        self.settings_form.addWidget(self.no_settings_label)
        
        # Documentation tab
        self.documentation_tab = QWidget()
        self.documentation_layout = QVBoxLayout(self.documentation_tab)
        
        # Documentation viewer
        self.documentation_view = QTextEdit()
        self.documentation_view.setReadOnly(True)
        self.documentation_view.setMinimumHeight(200)
        self.documentation_view.setStyleSheet("font-family: monospace;")
        
        # Add markdown support later if available
        self.no_docs_label = QLabel("No documentation available for this plugin")
        self.no_docs_label.setAlignment(Qt.AlignCenter)
        self.documentation_layout.addWidget(self.no_docs_label)
        self.documentation_layout.addWidget(self.documentation_view)
        self.documentation_view.hide()
        
        # Add tabs to tab widget
        self.plugin_tabs.addTab(self.details_tab, "Details")
        self.plugin_tabs.addTab(self.settings_tab, "Settings")
        self.plugin_tabs.addTab(self.documentation_tab, "Documentation")
        
        # Add tab widget to details layout
        self.plugin_details_layout.addWidget(self.plugin_tabs)
        
        # Add list and details to top layout
        self.top_layout.addWidget(self.plugin_list_group, 1)
        self.top_layout.addWidget(self.plugin_details_group, 2)
        
        # Status bar to show pending changes
        self.status_bar = QLabel("No pending changes")
        self.status_bar.setFrameShape(QLabel.Panel)
        self.status_bar.setFrameShadow(QLabel.Sunken)
        self.status_bar.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        
        # Create button layout
        self.button_layout = QHBoxLayout()
        
        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.on_reload_clicked)
        self.reload_button.setToolTip("Reload the current plugin")
        
        self.refresh_button = QPushButton("Refresh List")
        self.refresh_button.clicked.connect(self.on_refresh_clicked)
        self.refresh_button.setToolTip("Refresh the plugin list")
        
        # Add new buttons for plugin directory and reload all plugins
        self.open_plugin_dir_button = QPushButton("Open Plugin Directory")
        self.open_plugin_dir_button.clicked.connect(self.on_open_plugin_directory_clicked)
        self.open_plugin_dir_button.setToolTip("Open the plugin directory in file explorer")
        
        self.reload_all_plugins_button = QPushButton("Reload All Plugins")
        self.reload_all_plugins_button.clicked.connect(self.on_reload_all_plugins_clicked)
        self.reload_all_plugins_button.setToolTip("Reload all plugins (discover new plugins and refresh existing ones)")
        
        self.save_changes_button = QPushButton("Save Changes")
        self.save_changes_button.clicked.connect(self.on_save_changes_clicked)
        self.save_changes_button.setToolTip("Save all changes to plugin states and settings")
        # Default to enabled - will be automatically updated based on changes
        self.save_changes_button.setEnabled(False)
        # Make the save button more prominent
        self.save_changes_button.setStyleSheet("font-weight: bold;")
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        self.button_layout.addWidget(self.reload_button)
        self.button_layout.addWidget(self.refresh_button)
        self.button_layout.addWidget(self.open_plugin_dir_button)
        self.button_layout.addWidget(self.reload_all_plugins_button)
        self.button_layout.addWidget(self.save_changes_button)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.close_button)
        
        # Add layouts to main layout
        self.layout.addLayout(self.top_layout)
        self.layout.addWidget(self.status_bar)
        self.layout.addLayout(self.button_layout)
        
        # Settings widgets dictionary
        self.setting_widgets = {}
        
        # Track plugin state changes for Apply All
        self.pending_plugin_changes = {}  # plugin_id -> {enabled: bool, settings: {setting_id: value}}
        
        # Plugin log messages dictionary (plugin_id -> [messages])
        self.plugin_logs = {}
        
        # Connect to plugin manager signals
        self.plugin_manager.plugin_loaded.connect(self.on_plugin_loaded)
        self.plugin_manager.plugin_unloaded.connect(self.on_plugin_unloaded)
        self.plugin_manager.plugin_enabled.connect(self.on_plugin_enabled)
        self.plugin_manager.plugin_disabled.connect(self.on_plugin_disabled)
        self.plugin_manager.plugin_state_changed.connect(self.on_plugin_state_changed)
        self.plugin_manager.plugin_status_changed.connect(self.on_plugin_status_changed)
        
        # Load plugins
        self.load_plugins()
        
    def load_plugins(self):
        """Load plugins into the list"""
        logger.debug("Loading plugins into the dialog list view")
        
        # Store currently selected plugin ID to restore selection later
        current_id = None
        current_item = self.plugin_list.currentItem()
        if current_item and current_item.plugin_info:
            current_id = current_item.plugin_info.id
            logger.debug(f"Current selection: {current_id}")
        
        # Clear the list
        self.plugin_list.clear()
        
        # Refresh the plugins from plugin manager to ensure we have the latest state
        plugins = self.plugin_manager.get_plugins()
        logger.debug(f"Refreshing plugin list with {len(plugins)} plugins")
        
        # Add each plugin to the list
        for plugin in sorted(plugins, key=lambda p: p.name):
            item = PluginListItem(plugin)
            self.plugin_list.addItem(item)
            logger.debug(f"Added plugin to list: {plugin.id} (enabled={plugin.enabled}, loaded={plugin.loaded})")
            
        # Select the first plugin if none was previously selected
        if self.plugin_list.count() > 0:
            if current_id:
                # Try to restore previous selection
                for i in range(self.plugin_list.count()):
                    item = self.plugin_list.item(i)
                    if item.plugin_info.id == current_id:
                        logger.debug(f"Restoring selection to previously selected plugin: {current_id}")
                        self.plugin_list.setCurrentItem(item)
                        break
                else:
                    # If previously selected plugin not found, select the first one
                    logger.debug("Previously selected plugin not found, selecting first plugin")
                    self.plugin_list.setCurrentRow(0)
            else:
                # No previous selection, select the first one
                logger.debug("No previous selection, selecting first plugin")
                self.plugin_list.setCurrentRow(0)
        else:
            logger.debug("No plugins to display, clearing details")
            self.clear_details()
            
        # Update the "Save Changes" button state
        self._update_save_button_state()
        
    def clear_details(self):
        """Clear the plugin details"""
        self.id_label.setText("")
        self.name_label.setText("")
        self.version_label.setText("")
        self.author_label.setText("")
        self.min_version_label.setText("")
        self.max_version_label.setText("")
        self.deps_label.setText("")
        self.reqs_label.setText("")
        self.sys_reqs_label.setText("")
        self.entry_point_label.setText("")
        self.path_label.setText("")
        self.status_label.setText("")
        self.log_text.clear()
        self.clear_settings()
        
        # Clear documentation
        self.documentation_view.clear()
        self.documentation_view.hide()
        self.no_docs_label.show()
        
        # Disable all action buttons
        self.enable_button.setEnabled(False)
        self.disable_button.setEnabled(False)
        self.load_button.setEnabled(False)
        self.unload_button.setEnabled(False)
        self.reload_button.setEnabled(False)
        
        # Update save button state based on whether there are pending changes
        self._update_save_button_state()
        
    def update_details(self, plugin_info):
        """Update the plugin details"""
        if not plugin_info:
            self.clear_details()
            return
            
        # Update basic details
        self.id_label.setText(plugin_info.id)
        self.name_label.setText(plugin_info.name)
        self.version_label.setText(plugin_info.version)
        self.author_label.setText(plugin_info.author or "Unknown")
        self.min_version_label.setText(plugin_info.min_app_version or "")
        self.max_version_label.setText(plugin_info.max_app_version or "")
        
        # Handle dependencies - support both string and object formats for backward compatibility
        deps_text = ""
        if plugin_info.dependencies:
            deps_list = []
            for dep in plugin_info.dependencies:
                if isinstance(dep, str):
                    # Legacy format: dependency is just a string
                    deps_list.append(dep)
                elif isinstance(dep, dict) and 'id' in dep:
                    # New format: dependency is an object with id and version
                    version = dep.get('version', '*')
                    deps_list.append(f"{dep['id']} ({version})")
                else:
                    # Fallback: convert to string
                    deps_list.append(str(dep))
            deps_text = "\n".join(deps_list)
        
        self.deps_label.setText(deps_text)
        self.reqs_label.setText("\n".join(plugin_info.requirements["python"]) or "")
        self.sys_reqs_label.setText("\n".join(plugin_info.requirements["system"]) or "")
        self.entry_point_label.setText(plugin_info.entry_point or "")
        self.path_label.setText(plugin_info.path or "")
        
        # Set status based on current plugin state
        self.status_label.setText(f"Current state: {plugin_info.state.name}")
        
        # Load plugin log if available
        if plugin_info.id in self.plugin_logs:
            self.log_text.clear()
            for log_entry in self.plugin_logs[plugin_info.id]:
                self.log_text.append(log_entry)
            
            # Scroll to the bottom
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        else:
            self.log_text.clear()
            self.log_text.setPlaceholderText("No initialization log available.")
        
        # Set status with appropriate color
        status_text = plugin_info.state.name.capitalize()
        
        if plugin_info.state.is_disabled:
            self.id_label.setStyleSheet("color: #888;")
            self.name_label.setStyleSheet("color: #888;")
            self.version_label.setStyleSheet("color: #888;")
            self.author_label.setStyleSheet("color: #888;")
            self.min_version_label.setStyleSheet("color: #888;")
            self.max_version_label.setStyleSheet("color: #888;")
            self.deps_label.setStyleSheet("color: #888;")
            self.reqs_label.setStyleSheet("color: #888;")
            self.sys_reqs_label.setStyleSheet("color: #888;")
            self.entry_point_label.setStyleSheet("color: #888;")
            self.path_label.setStyleSheet("color: #888;")
            self.status_label.setStyleSheet("color: #888; font-weight: bold;")
        elif plugin_info.state.is_loaded:
            self.id_label.setStyleSheet("color: #3c763d;")
            self.name_label.setStyleSheet("color: #3c763d;")
            self.version_label.setStyleSheet("color: #3c763d;")
            self.author_label.setStyleSheet("color: #3c763d;")
            self.min_version_label.setStyleSheet("color: #3c763d;")
            self.max_version_label.setStyleSheet("color: #3c763d;")
            self.deps_label.setStyleSheet("color: #3c763d;")
            self.reqs_label.setStyleSheet("color: #3c763d;")
            self.sys_reqs_label.setStyleSheet("color: #3c763d;")
            self.entry_point_label.setStyleSheet("color: #3c763d;")
            self.path_label.setStyleSheet("color: #3c763d;")
            self.status_label.setStyleSheet("color: #3c763d; font-weight: bold;")
        elif plugin_info.state.is_enabled:
            self.id_label.setStyleSheet("color: #31708f;")
            self.name_label.setStyleSheet("color: #31708f;")
            self.version_label.setStyleSheet("color: #31708f;")
            self.author_label.setStyleSheet("color: #31708f;")
            self.min_version_label.setStyleSheet("color: #31708f;")
            self.max_version_label.setStyleSheet("color: #31708f;")
            self.deps_label.setStyleSheet("color: #31708f;")
            self.reqs_label.setStyleSheet("color: #31708f;")
            self.sys_reqs_label.setStyleSheet("color: #31708f;")
            self.entry_point_label.setStyleSheet("color: #31708f;")
            self.path_label.setStyleSheet("color: #31708f;")
            self.status_label.setStyleSheet("color: #31708f; font-weight: bold;")
        elif plugin_info.state == plugin_info.state.ERROR:
            self.id_label.setStyleSheet("color: #a94442;")
            self.name_label.setStyleSheet("color: #a94442;")
            self.version_label.setStyleSheet("color: #a94442;")
            self.author_label.setStyleSheet("color: #a94442;")
            self.min_version_label.setStyleSheet("color: #a94442;")
            self.max_version_label.setStyleSheet("color: #a94442;")
            self.deps_label.setStyleSheet("color: #a94442;")
            self.reqs_label.setStyleSheet("color: #a94442;")
            self.sys_reqs_label.setStyleSheet("color: #a94442;")
            self.entry_point_label.setStyleSheet("color: #a94442;")
            self.path_label.setStyleSheet("color: #a94442;")
            self.status_label.setStyleSheet("color: #a94442; font-weight: bold;")
        
        # Update description
        self.documentation_view.setText(plugin_info.description)
        
        # Check if this plugin has pending changes
        has_pending_state_change = False
        if plugin_info.id in self.pending_plugin_changes:
            pending_state = self.pending_plugin_changes[plugin_info.id].get("enabled")
            if pending_state is not None:
                # Only show pending state change if it's actually different from current state
                if pending_state != plugin_info.state.is_enabled:
                    has_pending_state_change = True
                    
                    # Update the status text to indicate pending change
                    if pending_state:
                        self.id_label.setText(f"{plugin_info.id} (will be enabled on save)")
                        self.name_label.setText(f"{plugin_info.name} (will be enabled on save)")
                        self.version_label.setText(f"{plugin_info.version} (will be enabled on save)")
                        self.author_label.setText(f"{plugin_info.author or 'Unknown'} (will be enabled on save)")
                        self.min_version_label.setText(f"{plugin_info.min_app_version or ''} (will be enabled on save)")
                        self.max_version_label.setText(f"{plugin_info.max_app_version or ''} (will be enabled on save)")
                        self.deps_label.setText(f"{self.deps_label.text()} (will be enabled on save)")
                        self.reqs_label.setText(f"{self.reqs_label.text()} (will be enabled on save)")
                        self.sys_reqs_label.setText(f"{self.sys_reqs_label.text()} (will be enabled on save)")
                        self.entry_point_label.setText(f"{plugin_info.entry_point} (will be enabled on save)")
                        self.path_label.setText(f"{plugin_info.path} (will be enabled on save)")
                        self.id_label.setStyleSheet("color: orange;")
                        self.name_label.setStyleSheet("color: orange;")
                        self.version_label.setStyleSheet("color: orange;")
                        self.author_label.setStyleSheet("color: orange;")
                        self.min_version_label.setStyleSheet("color: orange;")
                        self.max_version_label.setStyleSheet("color: orange;")
                        self.deps_label.setStyleSheet("color: orange;")
                        self.reqs_label.setStyleSheet("color: orange;")
                        self.sys_reqs_label.setStyleSheet("color: orange;")
                        self.entry_point_label.setStyleSheet("color: orange;")
                        self.path_label.setStyleSheet("color: orange;")
                    else:
                        self.id_label.setText(f"{plugin_info.id} (will be disabled on save)")
                        self.name_label.setText(f"{plugin_info.name} (will be disabled on save)")
                        self.version_label.setText(f"{plugin_info.version} (will be disabled on save)")
                        self.author_label.setText(f"{plugin_info.author or 'Unknown'} (will be disabled on save)")
                        self.min_version_label.setText(f"{plugin_info.min_app_version or ''} (will be disabled on save)")
                        self.max_version_label.setText(f"{plugin_info.max_app_version or ''} (will be disabled on save)")
                        self.deps_label.setText(f"{self.deps_label.text()} (will be disabled on save)")
                        self.reqs_label.setText(f"{self.reqs_label.text()} (will be disabled on save)")
                        self.sys_reqs_label.setText(f"{self.sys_reqs_label.text()} (will be disabled on save)")
                        self.entry_point_label.setText(f"{plugin_info.entry_point} (will be disabled on save)")
                        self.path_label.setText(f"{plugin_info.path} (will be disabled on save)")
                        self.id_label.setStyleSheet("color: #888;")
                        self.name_label.setStyleSheet("color: #888;")
                        self.version_label.setStyleSheet("color: #888;")
                        self.author_label.setStyleSheet("color: #888;")
                        self.min_version_label.setStyleSheet("color: #888;")
                        self.max_version_label.setStyleSheet("color: #888;")
                        self.deps_label.setStyleSheet("color: #888;")
                        self.reqs_label.setStyleSheet("color: #888;")
                        self.sys_reqs_label.setStyleSheet("color: #888;")
                        self.entry_point_label.setStyleSheet("color: #888;")
                        self.path_label.setStyleSheet("color: #888;")
                    self.id_label.setStyleSheet("padding: 5px; color: orange;")
                    self.name_label.setStyleSheet("padding: 5px; color: orange;")
                    self.version_label.setStyleSheet("padding: 5px; color: orange;")
                    self.author_label.setStyleSheet("padding: 5px; color: orange;")
                    self.min_version_label.setStyleSheet("padding: 5px; color: orange;")
                    self.max_version_label.setStyleSheet("padding: 5px; color: orange;")
                    self.deps_label.setStyleSheet("padding: 5px; color: orange;")
                    self.reqs_label.setStyleSheet("padding: 5px; color: orange;")
                    self.sys_reqs_label.setStyleSheet("padding: 5px; color: orange;")
                    self.entry_point_label.setStyleSheet("padding: 5px; color: orange;")
                    self.path_label.setStyleSheet("padding: 5px; color: orange;")
                else:
                    # If there's no actual change, remove it from pending changes
                    logger.debug(f"Removing unnecessary enable/disable change for {plugin_info.id} as state already matches")
                    self.pending_plugin_changes[plugin_info.id]["enabled"] = None
                    if not self.pending_plugin_changes[plugin_info.id]["settings"]:
                        del self.pending_plugin_changes[plugin_info.id]
        
        # Update settings tab - settings are only available for loaded plugins
        self.update_settings(plugin_info)
        
        # Update documentation
        self.update_documentation(plugin_info)
        
        # Update the status bar
        self._update_status_bar()
        
        # Update the save button state
        self._update_save_button_state()
        
        # Set the enable button state to match the plugin's current state
        # (not the pending state) to accurately reflect the actual plugin state
        if hasattr(self, 'enable_button') and self.enable_button is not None:
            self.enable_button.blockSignals(True)
            if hasattr(self.enable_button, 'setChecked'):
                self.enable_button.setChecked(plugin_info.state.is_enabled)
            self.enable_button.blockSignals(False)
        
        # Update action buttons (enable/disable/load/unload) to correctly reflect
        # both current state and pending changes
        self._update_action_buttons(plugin_info)
        
    def update_documentation(self, plugin_info):
        """Update the plugin documentation"""
        if not plugin_info or not plugin_info.path:
            self.documentation_view.clear()
            self.documentation_view.hide()
            self.no_docs_label.show()
            return
            
        # Look for API.md file in the plugin directory
        api_doc_path = os.path.join(plugin_info.path, "API.md")
        readme_path = os.path.join(plugin_info.path, "README.md")
        
        if os.path.exists(api_doc_path):
            try:
                with open(api_doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.documentation_view.setPlainText(content)
                self.documentation_view.show()
                self.no_docs_label.hide()
            except Exception as e:
                logger.error(f"Error loading API.md for plugin {plugin_info.id}: {e}")
                self.documentation_view.setPlainText(f"Error loading documentation: {str(e)}")
                self.documentation_view.show()
                self.no_docs_label.hide()
        elif os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.documentation_view.setPlainText(content)
                self.documentation_view.show()
                self.no_docs_label.hide()
            except Exception as e:
                logger.error(f"Error loading README.md for plugin {plugin_info.id}: {e}")
                self.documentation_view.setPlainText(f"Error loading documentation: {str(e)}")
                self.documentation_view.show()
                self.no_docs_label.hide()
        else:
            self.documentation_view.clear()
            self.documentation_view.hide()
            self.no_docs_label.setText("No documentation (API.md) found for this plugin")
            self.no_docs_label.show()
        
    def clear_settings(self):
        """Clear plugin settings"""
        # Clear the form layout
        while self.settings_form.count() > 0:
            item = self.settings_form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.setting_widgets = {}
        
        # Add the no settings label
        self.no_settings_label = QLabel("No settings available for this plugin")
        self.no_settings_label.setAlignment(Qt.AlignCenter)
        self.settings_form.addWidget(self.no_settings_label)
        
        # Update the Save Changes button state
        self._update_save_button_state()
        
    def update_settings(self, plugin_info):
        """Update plugin settings"""
        # Clear settings
        self.clear_settings()
        
        # If plugin is not loaded or doesn't have an instance, return
        if not plugin_info.state.is_loaded or not plugin_info.instance:
            return
            
        # Get settings from plugin
        settings = getattr(plugin_info.instance, 'get_settings', lambda: {})()
        
        # If no settings, return
        if not settings:
            return
            
        # Remove the no settings label
        if hasattr(self, 'no_settings_label') and self.no_settings_label:
            self.no_settings_label.setParent(None)
            self.no_settings_label.deleteLater()
            self.no_settings_label = None
        
        # Add settings to form layout
        for setting_id, setting in settings.items():
            # Create label
            label = QLabel(setting["name"])
            label.setToolTip(setting["description"])
            
            # Create widget based on setting type
            widget = None
            
            if setting["type"] == "string":
                widget = QLineEdit(str(setting["value"]))
                widget.textChanged.connect(lambda text, s_id=setting_id, p_id=plugin_info.id: 
                    self._on_setting_changed(p_id, s_id, text))
                
            elif setting["type"] == "int":
                widget = QSpinBox()
                widget.setMinimum(-1000000)
                widget.setMaximum(1000000)
                widget.setValue(int(setting["value"]))
                widget.valueChanged.connect(lambda value, s_id=setting_id, p_id=plugin_info.id: 
                    self._on_setting_changed(p_id, s_id, value))
                
            elif setting["type"] == "float":
                widget = QDoubleSpinBox()
                widget.setMinimum(-1000000.0)
                widget.setMaximum(1000000.0)
                widget.setValue(float(setting["value"]))
                widget.valueChanged.connect(lambda value, s_id=setting_id, p_id=plugin_info.id: 
                    self._on_setting_changed(p_id, s_id, value))
                
            elif setting["type"] == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(setting["value"]))
                widget.stateChanged.connect(lambda state, s_id=setting_id, p_id=plugin_info.id: 
                    self._on_setting_changed(p_id, s_id, state == Qt.Checked))
                
            elif setting["type"] == "choice":
                widget = QComboBox()
                widget.addItems(setting["choices"])
                if setting["value"] in setting["choices"]:
                    widget.setCurrentText(setting["value"])
                widget.currentTextChanged.connect(lambda text, s_id=setting_id, p_id=plugin_info.id: 
                    self._on_setting_changed(p_id, s_id, text))
                    
            elif setting["type"] == "json":
                # For JSON type settings (like scan profiles), create a special widget
                # This is a simplified representation for complex data structures
                if setting_id == "scan_profiles":
                    # For scan profiles, show a combobox of available profiles
                    widget = QComboBox()
                    profile_keys = list(setting["value"].keys())
                    widget.addItems(profile_keys)
                    widget.setCurrentIndex(0)
                    widget.currentTextChanged.connect(lambda text, s_id=setting_id, p_id=plugin_info.id: 
                        self._handle_profile_selection(p_id, s_id, text))
                    
                    # Add a button to edit the selected profile
                    profile_button = QPushButton("Manage Profiles")
                    profile_button.clicked.connect(lambda checked=False, s_id=setting_id, p_id=plugin_info.id: 
                        self._show_profile_editor(p_id, s_id))
                    
                    # Create a horizontal layout to hold the combo and button
                    json_layout = QHBoxLayout()
                    json_layout.addWidget(widget)
                    json_layout.addWidget(profile_button)
                    
                    # Create a container widget for the layout
                    container = QWidget()
                    container.setLayout(json_layout)
                    widget = container  # The form will use this container
                else:
                    # For other JSON settings, show a simple edit button
                    widget = QPushButton("Edit JSON Data")
                    widget.clicked.connect(lambda checked=False, s_id=setting_id, p_id=plugin_info.id: 
                        self._show_json_editor(p_id, s_id))
                    
            # Add tooltip with description
            if widget:
                widget.setToolTip(setting["description"])
                
                # Add to form layout
                self.settings_form.addRow(label, widget)
                
                # Store widget in dictionary
                self.setting_widgets[setting_id] = {
                    "widget": widget,
                    "type": setting["type"],
                    "original_value": setting["value"]
                }
                
        # Update the Save Changes button state
        self._update_save_button_state()
        
    def _on_setting_changed(self, plugin_id, setting_id, value):
        """Handle setting value changed"""
        # Make sure plugin is in pending changes
        if plugin_id not in self.pending_plugin_changes:
            self.pending_plugin_changes[plugin_id] = {"enabled": None, "settings": {}}
            
        # Get the original value
        original_value = None
        if setting_id in self.setting_widgets:
            original_value = self.setting_widgets[setting_id]["original_value"]
            
        # Only track if changed from original
        if value != original_value:
            # Add to pending changes
            self.pending_plugin_changes[plugin_id]["settings"][setting_id] = value
            
            # Update visual indication
            for i in range(self.plugin_list.count()):
                item = self.plugin_list.item(i)
                if item.plugin_info.id == plugin_id:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    break
        else:
            # Remove from pending changes if it was there
            if setting_id in self.pending_plugin_changes[plugin_id]["settings"]:
                del self.pending_plugin_changes[plugin_id]["settings"][setting_id]
                
            # Check if we should update visual indication
            if not self.pending_plugin_changes[plugin_id]["settings"] and self.pending_plugin_changes[plugin_id].get("enabled") is None:
                for i in range(self.plugin_list.count()):
                    item = self.plugin_list.item(i)
                    if item.plugin_info.id == plugin_id:
                        font = item.font()
                        font.setBold(False)
                        item.setFont(font)
                        break
        
        # Update the Save Changes button state
        self._update_save_button_state()
        
    def _get_plugin_settings_changes(self, plugin_id):
        """Collect settings changes for a plugin"""
        current_item = None
        for i in range(self.plugin_list.count()):
            item = self.plugin_list.item(i)
            if item.plugin_info.id == plugin_id:
                current_item = item
                break
                
        if not current_item:
            return {}
            
        plugin_info = current_item.plugin_info
        
        if not plugin_info.state.is_loaded or not plugin_info.instance:
            return {}
            
        # Get values from widgets
        updated_settings = {}
        for setting_id, setting_data in self.setting_widgets.items():
            widget = setting_data["widget"]
            setting_type = setting_data["type"]
            value = None
            
            if setting_type == "string":
                value = widget.text()
                
            elif setting_type == "int":
                value = widget.value()
                
            elif setting_type == "float":
                value = widget.value()
                
            elif setting_type == "bool":
                value = widget.isChecked()
                
            elif setting_type == "choice":
                value = widget.currentText()
                
            elif setting_type == "json":
                # Handle JSON type data
                # Since we're using buttons to edit JSON, we need to retrieve
                # the pending changes directly rather than from the widget
                if plugin_id in self.pending_plugin_changes and setting_id in self.pending_plugin_changes[plugin_id]["settings"]:
                    value = self.pending_plugin_changes[plugin_id]["settings"][setting_id]
                    
            if value is not None:
                # Check if the value is different from the current plugin setting
                current_value = plugin_info.instance.get_setting_value(setting_id)
                if value != current_value:
                    updated_settings[setting_id] = value
                    
        return updated_settings
    
    @Slot()
    def on_save_changes_clicked(self):
        """Handle save changes button clicked"""
        # Check if there are any changes to apply
        if not self._are_there_pending_changes():
            # Double-check current selected plugin state against checkbox
            current_item = self.plugin_list.currentItem()
            if current_item and current_item.plugin_info:
                plugin_info = current_item.plugin_info
                plugin_id = plugin_info.id
                new_enabled_state = self.enable_button.isChecked()
                current_enabled_state = plugin_info.state.is_enabled
                
                # If checkbox state differs from actual state, add it to pending changes
                if new_enabled_state != current_enabled_state:
                    logger.debug(f"Forced detection of pending state change: {plugin_id} {current_enabled_state} -> {new_enabled_state}")
                    if plugin_id not in self.pending_plugin_changes:
                        self.pending_plugin_changes[plugin_id] = {"enabled": None, "settings": {}}
                    self.pending_plugin_changes[plugin_id]["enabled"] = new_enabled_state
                else:
                    # If no real changes detected
                    QMessageBox.information(self, "No Changes", "There are no pending changes to save.")
                    return
            else:
                # If no item selected
                QMessageBox.information(self, "No Changes", "There are no pending changes to save.")
                return
            
        # Build a detailed changes list
        detailed_changes = []
        enable_plugins = []
        disable_plugins = []
        settings_plugins = []
        
        # Create a copy of the pending changes dictionary to prevent modification during iteration
        pending_changes_copy = dict(self.pending_plugin_changes)
        
        for plugin_id, changes in pending_changes_copy.items():
            plugin_info = self.plugin_manager.get_plugin(plugin_id)
            if not plugin_info:
                continue
                
            # Check for enable/disable changes
            if changes.get("enabled") is not None:
                current_state = plugin_info.state.is_enabled
                new_state = changes["enabled"]
                
                if new_state == True and current_state == False:
                    # This is an enable action
                    enable_plugins.append(plugin_info.name)
                    detailed_changes.append(f"ENABLE plugin: {plugin_info.name}")
                elif new_state == False and current_state == True:
                    # This is a disable action
                    disable_plugins.append(plugin_info.name) 
                    detailed_changes.append(f"DISABLE plugin: {plugin_info.name}")
                
            # Check for settings changes
            if changes.get("settings") and len(changes["settings"]) > 0:
                settings_plugins.append(plugin_info.name)
                detailed_changes.append(f"Update {len(changes['settings'])} settings for: {plugin_info.name}")
        
        # Log all pending changes for debugging
        logger.debug(f"Pending changes before save: {len(pending_changes_copy)} plugins have changes")
        for plugin_id, changes in pending_changes_copy.items():
            plugin_info = self.plugin_manager.get_plugin(plugin_id)
            plugin_name = plugin_info.name if plugin_info else "Unknown"
            logger.debug(f"Pending changes for {plugin_id} ({plugin_name}): enabled={changes.get('enabled')}, settings={len(changes.get('settings', {}))}")
        
        # Show confirmation dialog with detailed changes
        confirm_message = "Are you sure you want to save the following changes?\n\n"
        confirm_message += "\n".join(detailed_changes)
        
        confirm = QMessageBox.question(
            self,
            "Save Changes",
            confirm_message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if confirm != QMessageBox.Yes:
            logger.debug("User cancelled save changes operation")
            return
        
        logger.debug("User confirmed save changes operation, applying changes")
        
        # Show a busy cursor while applying changes
        self.setCursor(Qt.WaitCursor)
        self.status_bar.setText("Applying changes...")
        self.status_bar.setStyleSheet("padding: 5px; background-color: #f0f0f0; font-weight: bold;")
        QApplication.processEvents()  # Ensure the UI updates
            
        # Process all pending changes
        results = {
            "enabled": [],
            "disabled": [],
            "settings_updated": [],
            "failed": []
        }
        
        # First handle enable/disable changes - use the copy again
        for plugin_id, changes in pending_changes_copy.items():
            plugin_info = self.plugin_manager.get_plugin(plugin_id)
            if not plugin_info:
                logger.warning(f"Plugin not found when applying changes: {plugin_id}")
                results["failed"].append(f"{plugin_id} (plugin not found)")
                continue
                
            # Handle enabled state change if requested
            if changes.get("enabled") is not None:
                new_state = changes["enabled"]
                current_state = plugin_info.state.is_enabled
                logger.debug(f"Processing enable/disable change for plugin {plugin_id}: current={current_state}, new={new_state}")
                
                # Only apply changes if they differ from current state
                if new_state != current_state:
                    if new_state and not plugin_info.state.is_enabled:
                        # Enable the plugin
                        logger.info(f"Enabling plugin: {plugin_id}")
                        success = self.plugin_manager.enable_plugin(plugin_id)
                        if success:
                            # If enabling, also try to load
                            if not plugin_info.state.is_loaded:
                                logger.info(f"Attempting to load newly enabled plugin: {plugin_id}")
                                load_success = self.plugin_manager.load_plugin(plugin_id)
                                if load_success:
                                    results["enabled"].append(plugin_info.name)
                                    logger.info(f"Successfully enabled and loaded plugin: {plugin_id}")
                                else:
                                    results["failed"].append(f"{plugin_info.name} (enabled but failed to load)")
                                    logger.error(f"Failed to load plugin after enabling: {plugin_id}")
                            else:
                                results["enabled"].append(plugin_info.name)
                                logger.info(f"Successfully enabled plugin: {plugin_id}")
                        else:
                            results["failed"].append(f"{plugin_info.name} (failed to enable)")
                            logger.error(f"Failed to enable plugin: {plugin_id}")
                            
                    elif not new_state and plugin_info.state.is_enabled:
                        # Disable the plugin (unloads it too)
                        logger.info(f"Disabling plugin: {plugin_id}")
                        
                        # First unload if currently loaded
                        if plugin_info.state.is_loaded or plugin_info.instance is not None:
                            logger.info(f"Unloading plugin before disabling: {plugin_id}")
                            unload_success = self.plugin_manager.unload_plugin(plugin_id)
                            if not unload_success:
                                logger.warning(f"Failed to unload plugin {plugin_id} during disable operation, forcing cleanup")
                                
                                # Force manual cleanup
                                if plugin_info.instance is not None:
                                    try:
                                        if hasattr(plugin_info.instance, 'cleanup') and callable(plugin_info.instance.cleanup):
                                            try:
                                                plugin_info.instance.cleanup()
                                            except Exception as e:
                                                logger.error(f"Error during plugin cleanup: {e}")
                                                
                                        # Force instance to None
                                        plugin_info.instance = None
                                        
                                        # Force garbage collection
                                        import gc
                                        gc.collect()
                                    except Exception as e:
                                        logger.error(f"Error during force cleanup: {e}")
                                        plugin_info.instance = None
                                    
                        # Then disable it
                        success = self.plugin_manager.disable_plugin(plugin_id)
                        if success:
                            # Double-check that plugin is really unloaded
                            if plugin_info.instance is not None:
                                logger.warning(f"Plugin instance still exists after disabling - forcing clear")
                                plugin_info.instance = None
                                
                                # Force garbage collection
                                import gc
                                gc.collect()
                                
                            results["disabled"].append(plugin_info.name)
                            logger.info(f"Successfully disabled plugin: {plugin_id}")
                        else:
                            results["failed"].append(f"{plugin_info.name} (failed to disable)")
                            logger.error(f"Failed to disable plugin: {plugin_id}")
                else:
                    logger.debug(f"Skipping enable/disable for plugin {plugin_id} as state already matches: {current_state}")
            
            # Update settings if any and the plugin is loaded
            if plugin_info.state.is_loaded and plugin_info.instance and changes.get("settings"):
                settings_success = True
                failed_settings = []
                
                for setting_id, value in changes["settings"].items():
                    if not plugin_info.instance.update_setting(setting_id, value):
                        settings_success = False
                        failed_settings.append(setting_id)
                        
                if settings_success:
                    results["settings_updated"].append(plugin_info.name)
                else:
                    results["failed"].append(f"{plugin_info.name} (failed to update settings: {', '.join(failed_settings)})")
        
        # Get the current selected plugin before we reload the list
        current_plugin_id = None
        current_item = self.plugin_list.currentItem()
        if current_item and current_item.plugin_info:
            current_plugin_id = current_item.plugin_info.id
            
        # Clear all pending changes
        logger.debug("Clearing all pending changes")
        self.pending_plugin_changes = {}
        
        # Refresh the UI to reflect changes
        logger.debug("Reloading plugin list to refresh UI")
        self.load_plugins()
        
        # Try to select the previously selected plugin
        if current_plugin_id:
            for i in range(self.plugin_list.count()):
                item = self.plugin_list.item(i)
                if item.plugin_info.id == current_plugin_id:
                    self.plugin_list.setCurrentItem(item)
                    # Force an immediate update to the details panel with the refreshed state
                    self.update_details(item.plugin_info)
                    # Ensure buttons reflect the current state, not pending changes
                    self._update_action_buttons(item.plugin_info)
                    break
        
        # Restore cursor
        self.setCursor(Qt.ArrowCursor)
                
        # Update status bar with results summary
        result_text = []
        if results["enabled"]:
            result_text.append(f"{len(results['enabled'])} plugin(s) enabled")
        if results["disabled"]:
            result_text.append(f"{len(results['disabled'])} plugin(s) disabled")
        if results["settings_updated"]:
            result_text.append(f"{len(results['settings_updated'])} plugin(s) settings updated")
        if results["failed"]:
            result_text.append(f"{len(results['failed'])} plugin(s) had errors")
            
        if result_text:
            self.status_bar.setText(f"Changes applied: {', '.join(result_text)}")
            self.status_bar.setStyleSheet("padding: 5px; background-color: #d0f0d0; font-weight: bold;")
        else:
            self.status_bar.setText("No changes were required")
            self.status_bar.setStyleSheet("padding: 5px; background-color: #f0f0f0; font-weight: normal;")
        
        # Final verification - ensure ALL disabled plugins have no instances
        for i in range(self.plugin_list.count()):
            item = self.plugin_list.item(i)
            plugin_info = item.plugin_info
            
            if plugin_info.state == PluginState.DISABLED and plugin_info.instance is not None:
                logger.warning(f"Plugin {plugin_info.id} is disabled but still has instance - forcing cleanup")
                try:
                    if hasattr(plugin_info.instance, 'cleanup') and callable(plugin_info.instance.cleanup):
                        try:
                            plugin_info.instance.cleanup()
                        except Exception as e:
                            logger.error(f"Error during final cleanup: {e}")
                    
                    # Force instance to None
                    plugin_info.instance = None
                    
                    # Force garbage collection
                    import gc
                    gc.collect()
                except Exception as e:
                    logger.error(f"Error during final cleanup: {e}")
                    plugin_info.instance = None
        
    def _get_changes_summary(self):
        """Get a summary of pending changes to show in confirmation dialog"""
        summary = ""
        enable_count = 0
        disable_count = 0
        settings_changes = []
        
        logger.debug("Generating changes summary for confirmation dialog")
        
        # First check the currently selected plugin against its checkbox state
        current_item = self.plugin_list.currentItem()
        if current_item and current_item.plugin_info:
            plugin_info = current_item.plugin_info
            plugin_id = plugin_info.id
            
            new_enabled_state = self.enable_button.isChecked()  # Current checkbox state
            current_enabled_state = plugin_info.state.is_enabled         # Current plugin state
            
            # If checkbox differs from current state, ensure this is tracked
            if new_enabled_state != current_enabled_state:
                logger.debug(f"Checkbox state differs from plugin state for {plugin_id}: {current_enabled_state} -> {new_enabled_state}")
                if plugin_id not in self.pending_plugin_changes:
                    self.pending_plugin_changes[plugin_id] = {"enabled": None, "settings": {}}
                self.pending_plugin_changes[plugin_id]["enabled"] = new_enabled_state
        
        # Now process all pending changes for the summary
        for plugin_id, changes in self.pending_plugin_changes.items():
            plugin_info = self.plugin_manager.get_plugin(plugin_id)
            if not plugin_info:
                continue
                
            # Track enable/disable changes
            if changes.get("enabled") is not None:
                current_state = plugin_info.state.is_enabled
                new_state = changes["enabled"]
                
                logger.debug(f"Processing change for summary: {plugin_id} current={current_state}, new={new_state}")
                
                if new_state == True and current_state == False:
                    # This is an enable action
                    enable_count += 1
                    logger.debug(f"Change will ENABLE plugin {plugin_id}")
                elif new_state == False and current_state == True:
                    # This is a disable action
                    disable_count += 1
                    logger.debug(f"Change will DISABLE plugin {plugin_id}")
                    
            # Track settings changes
            if changes.get("settings") and len(changes["settings"]) > 0:
                settings_changes.append(f"{plugin_info.name} ({len(changes['settings'])} settings)")
                
        # Build summary text
        if enable_count > 0:
            summary += f"Enable {enable_count} plugin{'s' if enable_count > 1 else ''}\n"
            
        if disable_count > 0:
            summary += f"Disable {disable_count} plugin{'s' if disable_count > 1 else ''}\n"
            
        if settings_changes:
            summary += f"Update settings for: {', '.join(settings_changes)}\n"
        
        logger.debug(f"Generated summary: {summary}")    
        return summary
    
    @Slot(QListWidgetItem, QListWidgetItem)
    def on_plugin_selected(self, current, previous):
        """Handle plugin selection"""
        if current:
            self.update_details(current.plugin_info)
            # Update action buttons based on the current plugin's state
            self._update_action_buttons(current.plugin_info)
        else:
            self.clear_details()
            
    @Slot(int)
    def on_plugin_enabled_changed(self, state):
        """Handle plugin enabled changed"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            logger.warning("on_plugin_enabled_changed: No current item selected")
            return
            
        plugin_info = current_item.plugin_info
        plugin_id = plugin_info.id
        
        # The state parameter is the Qt.CheckState value (0=unchecked, 2=checked)
        new_enabled_state = (state == Qt.Checked)
        current_enabled_state = plugin_info.state.is_enabled
        
        logger.debug(f"Plugin checkbox state changed for {plugin_id}: state={state}, Qt.Checked={Qt.Checked}, isChecked={new_enabled_state}")
        logger.debug(f"Plugin {plugin_id} current state: enabled={current_enabled_state}")
        
        # Track the desired state in pending changes
        if plugin_id not in self.pending_plugin_changes:
            self.pending_plugin_changes[plugin_id] = {"enabled": None, "settings": {}}
            logger.debug(f"Created pending changes entry for plugin {plugin_id}")
            
        # IMPORTANT: Always record the new state in pending changes
        # This ensures the checkbox state is always captured correctly
        self.pending_plugin_changes[plugin_id]["enabled"] = new_enabled_state
        logger.debug(f"Updated pending state change for plugin {plugin_id}: enabled={new_enabled_state}")
        
        # Only update UI if there's an actual change from the current plugin state
        if new_enabled_state != current_enabled_state:
            logger.debug(f"The new state {new_enabled_state} differs from current state {current_enabled_state}, updating UI")
            
            # Update visual indication that there are pending changes
            font = current_item.font()
            font.setBold(True)
            current_item.setFont(font)
            
            # Show indicator of pending change
            # Make status text show the pending change
            if new_enabled_state:
                status_suffix = " (will be enabled on save)"
                self.id_label.setStyleSheet("color: orange;")
                self.name_label.setStyleSheet("color: orange;")
                self.version_label.setStyleSheet("color: orange;")
                self.author_label.setStyleSheet("color: orange;")
                self.min_version_label.setStyleSheet("color: orange;")
                self.max_version_label.setStyleSheet("color: orange;")
                self.deps_label.setStyleSheet("color: orange;")
                self.reqs_label.setStyleSheet("color: orange;")
                self.sys_reqs_label.setStyleSheet("color: orange;")
                self.entry_point_label.setStyleSheet("color: orange;")
                self.path_label.setStyleSheet("color: orange;")
            else:
                status_suffix = " (will be disabled on save)"
                self.id_label.setStyleSheet("color: #888;")
                self.name_label.setStyleSheet("color: #888;")
                self.version_label.setStyleSheet("color: #888;")
                self.author_label.setStyleSheet("color: #888;")
                self.min_version_label.setStyleSheet("color: #888;")
                self.max_version_label.setStyleSheet("color: #888;")
                self.deps_label.setStyleSheet("color: #888;")
                self.reqs_label.setStyleSheet("color: #888;")
                self.sys_reqs_label.setStyleSheet("color: #888;")
                self.entry_point_label.setStyleSheet("color: #888;")
                self.path_label.setStyleSheet("color: #888;")
                
            current_status = self.id_label.text().split(" (will be")[0]  # Remove any existing suffix
            self.id_label.setText(current_status + status_suffix)
            self.name_label.setText(current_status + status_suffix)
            self.version_label.setText(current_status + status_suffix)
            self.author_label.setText(current_status + status_suffix)
            self.min_version_label.setText(current_status + status_suffix)
            self.max_version_label.setText(current_status + status_suffix)
            self.deps_label.setText(current_status + status_suffix)
            self.reqs_label.setText(current_status + status_suffix)
            self.sys_reqs_label.setText(current_status + status_suffix)
            self.entry_point_label.setText(current_status + status_suffix)
            self.path_label.setText(current_status + status_suffix)
            
            # Always enable the save button when there's a state change
            self.save_changes_button.setEnabled(True)
            self.save_changes_button.setStyleSheet("background-color: #d0e8ff; font-weight: bold;")
            logger.debug(f"Save Changes button enabled due to plugin state change for {plugin_id}")
        else:
            logger.debug(f"The new state {new_enabled_state} is the same as current state {current_enabled_state}")
                
        # Update the Save Changes button state
        self._update_save_button_state()
    
    def _update_status_bar(self):
        """Update the status bar with pending changes summary"""
        if not self._are_there_pending_changes():
            self.status_bar.setText("No pending changes")
            self.status_bar.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
            return
            
        # Get counts
        enable_count = 0
        disable_count = 0
        settings_count = 0
        affected_plugins = set()
        
        for plugin_id, changes in self.pending_plugin_changes.items():
            plugin_info = self.plugin_manager.get_plugin(plugin_id)
            if not plugin_info:
                continue
                
            affected_plugins.add(plugin_info.name)
            
            if changes.get("enabled") is not None:
                if changes["enabled"]:
                    enable_count += 1
                else:
                    disable_count += 1
                    
            if changes.get("settings") and len(changes["settings"]) > 0:
                settings_count += 1
                
        # Create summary text
        summary = f"Pending changes: {len(affected_plugins)} plugins affected "
        details = []
        
        if enable_count > 0:
            details.append(f"{enable_count} to enable")
            
        if disable_count > 0:
            details.append(f"{disable_count} to disable")
            
        if settings_count > 0:
            details.append(f"{settings_count} with setting changes")
            
        if details:
            summary += f"({', '.join(details)})"
            
        self.status_bar.setText(summary)
        self.status_bar.setStyleSheet("padding: 5px; background-color: #ffe8cc; font-weight: bold;")
            
    def _update_action_buttons(self, plugin_info):
        """Update action button states based on plugin state"""
        # Default all to disabled
        self.enable_button.setEnabled(False)
        self.disable_button.setEnabled(False)
        self.load_button.setEnabled(False)
        self.unload_button.setEnabled(False)
        self.reload_button.setEnabled(False)
        
        if not plugin_info:
            return
            
        # Check pending changes first
        pending_enabled = None
        if plugin_info.id in self.pending_plugin_changes:
            pending_enabled = self.pending_plugin_changes[plugin_info.id].get("enabled")
        
        # Get actual current state
        current_enabled = plugin_info.state.is_enabled
        is_loaded = plugin_info.state.is_loaded
        
        # Log states for debugging
        logger.debug(f"Plugin {plugin_info.id} state: enabled={current_enabled}, loaded={is_loaded}, pending_enabled={pending_enabled}")
        
        # Determine which actions make sense based on current state (ignoring pending changes)
        if current_enabled:
            # Plugin is currently enabled
            self.disable_button.setEnabled(True)
            
            if is_loaded:
                # Plugin is loaded - can unload or reload
                self.unload_button.setEnabled(True)
                self.reload_button.setEnabled(True)
            else:
                # Plugin is enabled but not loaded - can load
                self.load_button.setEnabled(True)
        else:
            # Plugin is currently disabled - can enable
            self.enable_button.setEnabled(True)
            
        # Override based on pending state if necessary
        if pending_enabled is not None:
            # If a change is pending, update button state
            if pending_enabled:
                # Will be enabled, show disable button
                self.enable_button.setEnabled(False)
                self.disable_button.setEnabled(True)
            else:
                # Will be disabled, show enable button
                self.enable_button.setEnabled(True)
                self.disable_button.setEnabled(False)
                # Cannot load/unload if will be disabled
                self.load_button.setEnabled(False)
                self.unload_button.setEnabled(False)
                self.reload_button.setEnabled(False)
        
    def _are_there_pending_changes(self):
        """Check if there are any pending changes"""
        logger.debug("Checking for pending changes...")
        
        # First check if there are any plugin enable/disable changes
        for plugin_id, changes in self.pending_plugin_changes.items():
            if changes.get("enabled") is not None:
                plugin_info = self.plugin_manager.get_plugin(plugin_id)
                current_state = plugin_info.state.is_enabled if plugin_info else False
                pending_state = changes["enabled"]
                
                if current_state != pending_state:
                    logger.debug(f"Found pending enabled state change for {plugin_id}: {current_state} -> {pending_state}")
                    return True
                else:
                    logger.debug(f"Plugin {plugin_id} has 'enabled' in pending changes but matches current state ({current_state})")
                
            # Check for setting changes
            if changes.get("settings") and len(changes["settings"]) > 0:
                logger.debug(f"Found pending settings changes for {plugin_id}: {len(changes['settings'])} settings")
                return True
                
        # Also check the currently selected plugin's settings in case they haven't been saved
        current_item = self.plugin_list.currentItem()
        if current_item and current_item.plugin_info:
            plugin_id = current_item.plugin_info.id
            plugin_info = current_item.plugin_info
            
            # Check settings if the plugin is loaded and has an instance
            if plugin_info.state.is_loaded and plugin_info.instance:
                for setting_id, setting_data in self.setting_widgets.items():
                    widget = setting_data["widget"]
                    setting_type = setting_data["type"]
                    original_value = setting_data["original_value"]
                    
                    # Get current value
                    current_value = None
                    if setting_type == "string":
                        current_value = widget.text()
                    elif setting_type == "int":
                        current_value = widget.value()
                    elif setting_type == "float":
                        current_value = widget.value()
                    elif setting_type == "bool":
                        current_value = widget.isChecked()
                    elif setting_type == "choice":
                        current_value = widget.currentText()
                        
                    # If value changed, there are pending changes
                    if current_value != original_value:
                        logger.debug(f"Found pending setting change: {setting_id} value changed from {original_value} to {current_value}")
                        return True
                        
            # Check if this plugin's enabled state is going to change
            # Check if checkbox state differs from plugin's actual state
            new_enabled_state = self.enable_button.isChecked()
            current_enabled_state = plugin_info.state.is_enabled
            
            if new_enabled_state != current_enabled_state:
                logger.debug(f"Found pending enabled state change for selected plugin {plugin_id}: {current_enabled_state} -> {new_enabled_state}")
                return True
                
        logger.debug("No pending changes found")
        return False
        
    def _handle_profile_selection(self, plugin_id, setting_id, profile_key):
        """Handle selection of a scan profile in the combobox"""
        logger.debug(f"Profile selected: {profile_key} for plugin {plugin_id}")
        # This could be used to show details about the selected profile
        # or to update other UI elements based on the selection
        # For now, we'll just log it
        
    def _show_profile_editor(self, plugin_id, setting_id):
        """Show a dialog to edit scan profiles"""
        logger.debug(f"Opening profile editor for plugin {plugin_id}")
        
        # Get the plugin info
        plugin_info = self.plugin_manager.get_plugin(plugin_id)
        if not plugin_info or not plugin_info.instance:
            logger.error(f"Cannot edit profiles: Plugin {plugin_id} is not loaded")
            QMessageBox.warning(
                self, 
                "Plugin Not Loaded",
                "Cannot edit profiles because the plugin is not loaded. Please load the plugin first."
            )
            return
            
        # Get the profiles settings from the plugin
        settings = getattr(plugin_info.instance, 'get_settings', lambda: {})()
        if not settings or setting_id not in settings:
            logger.error(f"Cannot find setting {setting_id} for plugin {plugin_id}")
            QMessageBox.warning(
                self, 
                "Setting Not Found",
                f"Cannot find setting {setting_id} for plugin {plugin_id}"
            )
            return
            
        # Get the profiles data
        profiles = settings[setting_id]["value"]
        
        # Create a custom dialog for profiles editing
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Scan Profiles - {plugin_info.name}")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(500)
        
        layout = QVBoxLayout(dialog)
        
        # Add explanation text
        explanation = QLabel(
            "Scan profiles define different scanning configurations. "
            "Select a profile to view or edit its settings, or create a new profile."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        
        # Create a horizontal split for profiles list and details
        splitter = QSplitter()
        layout.addWidget(splitter, 1)  # Give the splitter most of the space
        
        # Left side: profiles list
        profiles_widget = QWidget()
        profiles_layout = QVBoxLayout(profiles_widget)
        
        profiles_layout.addWidget(QLabel("Available Profiles:"))
        
        profiles_list = QListWidget()
        for profile_id in profiles.keys():
            item = QListWidgetItem(profile_id)
            if profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]:
                item.setToolTip("Built-in profile")
                # Add visual indication that this is a built-in profile
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
            else:
                item.setToolTip("Custom profile")
            profiles_list.addItem(item)
        
        profiles_layout.addWidget(profiles_list, 1)  # Give the list most of the space
        
        # Add profile buttons
        profile_buttons_layout = QHBoxLayout()
        add_button = QPushButton("Add Profile")
        delete_button = QPushButton("Delete Profile")
        # Disable delete button initially
        delete_button.setEnabled(False)
        
        profile_buttons_layout.addWidget(add_button)
        profile_buttons_layout.addWidget(delete_button)
        profiles_layout.addLayout(profile_buttons_layout)
        
        splitter.addWidget(profiles_widget)
        
        # Right side: profile details
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        # Create a form layout for editing the selected profile
        details_form = QFormLayout()
        
        # Add form fields
        display_name = QLineEdit()
        details_form.addRow("Display Name:", display_name)
        
        description = QLineEdit()
        description.setPlaceholderText("Description of the scan profile")
        details_form.addRow("Description:", description)
        
        arguments = QLineEdit()
        arguments.setPlaceholderText("nmap arguments, e.g. -sn -F")
        details_form.addRow("Arguments:", arguments)
        
        os_detection = QCheckBox()
        details_form.addRow("OS Detection:", os_detection)
        
        port_scan = QCheckBox()
        details_form.addRow("Port Scanning:", port_scan)
        
        timeout = QLineEdit()
        # Allow only numbers between 30 and 600
        timeout.setValidator(QIntValidator(30, 600))
        details_form.addRow("Timeout (seconds):", timeout)
        
        details_layout.addWidget(QLabel("Profile Details:"))
        details_layout.addLayout(details_form)
        details_layout.addStretch(1)  # Push everything up
        
        # Add apply button for the details
        apply_button = QPushButton("Apply Changes")
        apply_button.setEnabled(False)  # Disabled until profile is selected
        details_layout.addWidget(apply_button)
        
        splitter.addWidget(details_widget)
        
        # Add dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Function to load profile data
        def load_profile_data(item):
            profile_id = item.text()
            if profile_id in profiles:
                profile = profiles[profile_id]
                
                display_name.setText(profile.get("name", profile_id))
                description.setText(profile.get("description", ""))
                arguments.setText(profile.get("arguments", ""))
                os_detection.setChecked(profile.get("os_detection", False))
                port_scan.setChecked(profile.get("port_scan", False))
                timeout.setText(str(profile.get("timeout", 300)))
                
                # Enable or disable editing based on whether this is a built-in profile
                is_builtin = profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]
                display_name.setEnabled(True)
                description.setEnabled(True)
                arguments.setEnabled(True)
                os_detection.setEnabled(True)
                port_scan.setEnabled(True)
                timeout.setEnabled(True)
                apply_button.setEnabled(True)
                delete_button.setEnabled(not is_builtin)
        
        # Function to apply changes to the selected profile
        def apply_changes():
            if not profiles_list.currentItem():
                return
                
            profile_id = profiles_list.currentItem().text()
            if profile_id in profiles:
                # Get values from form
                name = display_name.text()
                desc = description.text()
                args = arguments.text()
                os_detect = os_detection.isChecked()
                port_scanning = port_scan.isChecked()
                
                try:
                    timeout_val = int(timeout.text())
                    if timeout_val < 30:
                        timeout_val = 30
                    elif timeout_val > 600:
                        timeout_val = 600
                except ValueError:
                    timeout_val = 300
                
                # Update the profile
                profiles[profile_id] = {
                    "name": name,
                    "description": desc,
                    "arguments": args,
                    "os_detection": os_detect,
                    "port_scan": port_scanning,
                    "timeout": timeout_val
                }
                
                QMessageBox.information(
                    dialog,
                    "Profile Updated",
                    f"Profile '{profile_id}' has been updated."
                )
        
        # Function to add a new profile
        def add_profile():
            new_id, ok = QInputDialog.getText(
                dialog,
                "New Profile",
                "Enter a unique profile ID (lowercase, no spaces):",
                text="custom_scan"  # Default suggestion
            )
            
            if not ok or not new_id:
                return
                
            # Validate ID (lowercase, no spaces, etc.)
            new_id = new_id.lower().strip().replace(" ", "_")
            
            # Check if ID already exists
            if new_id in profiles:
                QMessageBox.warning(
                    dialog,
                    "Profile Exists",
                    f"A profile with ID '{new_id}' already exists. Please choose a different ID."
                )
                return
                
            # Create a new profile with default values
            profiles[new_id] = {
                "name": new_id.replace("_", " ").title(),
                "description": "Custom scan profile",
                "arguments": "-sn",
                "os_detection": False,
                "port_scan": False,
                "timeout": 300
            }
            
            # Add to list and select it
            item = QListWidgetItem(new_id)
            item.setToolTip("Custom profile")
            profiles_list.addItem(item)
            profiles_list.setCurrentItem(item)
            
            # Load the new profile data
            load_profile_data(item)
        
        # Function to delete the selected profile
        def delete_profile():
            if not profiles_list.currentItem():
                return
                
            profile_id = profiles_list.currentItem().text()
            
            # Don't allow deleting built-in profiles
            if profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]:
                QMessageBox.warning(
                    dialog,
                    "Cannot Delete",
                    "Built-in profiles cannot be deleted."
                )
                return
                
            # Confirm deletion
            confirm = QMessageBox.question(
                dialog,
                "Confirm Deletion",
                f"Are you sure you want to delete the profile '{profile_id}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                # Remove from profiles
                if profile_id in profiles:
                    del profiles[profile_id]
                    
                    # Remove from list
                    item = profiles_list.takeItem(profiles_list.currentRow())
                    del item
                    
                    # Clear form
                    display_name.clear()
                    description.clear()
                    arguments.clear()
                    os_detection.setChecked(False)
                    port_scan.setChecked(False)
                    timeout.setText("300")
                    
                    # Disable apply button
                    apply_button.setEnabled(False)
                    delete_button.setEnabled(False)
        
        # Connect signals
        profiles_list.currentItemChanged.connect(load_profile_data)
        apply_button.clicked.connect(apply_changes)
        add_button.clicked.connect(add_profile)
        delete_button.clicked.connect(delete_profile)
        
        # Select the first profile if available
        if profiles_list.count() > 0:
            profiles_list.setCurrentRow(0)
        
        # Show the dialog
        if dialog.exec() == QDialog.Accepted:
            # Update the plugin setting with the modified profiles
            if plugin_id not in self.pending_plugin_changes:
                self.pending_plugin_changes[plugin_id] = {"enabled": None, "settings": {}}
                
            self.pending_plugin_changes[plugin_id]["settings"][setting_id] = profiles
            
            # Update visual indication
            for i in range(self.plugin_list.count()):
                item = self.plugin_list.item(i)
                if item.plugin_info.id == plugin_id:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    break
            
            # Update the Save Changes button state
            self._update_save_button_state()
            
            # Show success message
            QMessageBox.information(
                self, 
                "Profiles Updated",
                "The scan profiles have been updated. Click 'Save Changes' to apply the changes."
            )
            
            # Refresh the UI
            self.update_settings(plugin_info)
        
    def _show_json_editor(self, plugin_id, setting_id):
        """Show a dialog to edit JSON data"""
        logger.debug(f"Opening JSON editor for plugin {plugin_id}, setting {setting_id}")
        
        # Get the plugin info
        plugin_info = self.plugin_manager.get_plugin(plugin_id)
        if not plugin_info or not plugin_info.instance:
            logger.error(f"Cannot edit JSON: Plugin {plugin_id} is not loaded")
            QMessageBox.warning(
                self, 
                "Plugin Not Loaded",
                "Cannot edit JSON data because the plugin is not loaded. Please load the plugin first."
            )
            return
            
        # Get the settings from the plugin
        settings = getattr(plugin_info.instance, 'get_settings', lambda: {})()
        if not settings or setting_id not in settings:
            logger.error(f"Cannot find setting {setting_id} for plugin {plugin_id}")
            QMessageBox.warning(
                self, 
                "Setting Not Found",
                f"Cannot find setting {setting_id} for plugin {plugin_id}"
            )
            return
            
        # Get the JSON data
        json_data = settings[setting_id]["value"]
        
        # Convert to string representation for editing
        import json
        try:
            json_str = json.dumps(json_data, indent=4)
        except Exception as e:
            logger.error(f"Error converting JSON to string: {e}")
            QMessageBox.warning(
                self, 
                "JSON Error",
                f"An error occurred while trying to convert the data to JSON: {e}"
            )
            return
            
        # Create a dialog for editing
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit {settings[setting_id]['name']} - {plugin_info.name}")
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(600)
        
        layout = QVBoxLayout(dialog)
        
        # Add explanation text
        explanation = QLabel(settings[setting_id]["description"])
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        
        # Add editor
        editor = QTextEdit()
        editor.setPlainText(json_str)
        editor.setFont(QFont("Courier New", 10))  # Use monospace font
        layout.addWidget(editor)
        
        # Add warning about JSON format
        warning = QLabel("Warning: The JSON data must be valid. Invalid JSON will not be saved.")
        warning.setStyleSheet("color: red;")
        layout.addWidget(warning)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show the dialog
        if dialog.exec() == QDialog.Accepted:
            # Parse the JSON
            try:
                new_json_data = json.loads(editor.toPlainText())
                
                # Update the setting
                if plugin_id not in self.pending_plugin_changes:
                    self.pending_plugin_changes[plugin_id] = {"enabled": None, "settings": {}}
                    
                self.pending_plugin_changes[plugin_id]["settings"][setting_id] = new_json_data
                
                # Update visual indication
                for i in range(self.plugin_list.count()):
                    item = self.plugin_list.item(i)
                    if item.plugin_info.id == plugin_id:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                        break
                
                # Update the Save Changes button state
                self._update_save_button_state()
                
                # Show success message
                QMessageBox.information(
                    self, 
                    "JSON Updated",
                    "The JSON data has been updated. Click 'Save Changes' to apply the changes."
                )
                
                # Refresh the UI
                self.update_settings(plugin_info)
                
            except json.JSONDecodeError as e:
                # Show error
                QMessageBox.critical(
                    self, 
                    "Invalid JSON",
                    f"The JSON data is invalid and cannot be saved. Error: {e}"
                )
                
    def _update_save_button_state(self):
        """Update the Save Changes button state based on pending changes"""
        has_changes = self._are_there_pending_changes()
        self.save_changes_button.setEnabled(has_changes)
        
        if has_changes:
            # Highlight the button to make it more obvious
            self.save_changes_button.setStyleSheet(
                "background-color: #d0e8ff; font-weight: bold; padding: 4px; border-radius: 4px;"
            )
            
            # Also update status bar to show pending changes
            self._update_status_bar()
        else:
            # Reset style when no changes
            self.save_changes_button.setStyleSheet("font-weight: bold;")
            self.status_bar.setText("No pending changes")
            self.status_bar.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
    
    @Slot()
    def on_reload_clicked(self):
        """Handle reload button clicked"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            return
            
        plugin_info = current_item.plugin_info
        
        if plugin_info.state.is_loaded:
            logger.debug(f"Reloading plugin: {plugin_info.id}")
            self.plugin_manager.reload_plugin(plugin_info.id)
            
            # Update the item display
            current_item.update_icon()
            
            QMessageBox.information(
                self,
                "Plugin Reloaded",
                f"Plugin '{plugin_info.name}' has been reloaded."
            )
            
    @Slot()
    def on_refresh_clicked(self):
        """Handle refresh button clicked"""
        logger.debug("Refreshing plugins")
        self.plugin_manager.discover_plugins()
        self.load_plugins()
        
    @Slot(object)
    def on_plugin_loaded(self, plugin_info):
        """Handle plugin loaded signal"""
        # Find the item for this plugin
        for i in range(self.plugin_list.count()):
            item = self.plugin_list.item(i)
            if item.plugin_info.id == plugin_info.id:
                item.plugin_info = plugin_info
                item.update_icon()
                break
                
    @Slot(object)
    def on_plugin_unloaded(self, plugin_info):
        """Handle plugin unloaded signal"""
        # Find the item for this plugin
        for i in range(self.plugin_list.count()):
            item = self.plugin_list.item(i)
            if item.plugin_info.id == plugin_info.id:
                item.plugin_info = plugin_info
                item.update_icon()
                break
                
    @Slot(object)
    def on_plugin_enabled(self, plugin_info):
        """Handle plugin enabled signal"""
        # Find the item for this plugin
        for i in range(self.plugin_list.count()):
            item = self.plugin_list.item(i)
            if item.plugin_info.id == plugin_info.id:
                item.plugin_info = plugin_info
                item.update_icon()
                break
                
    @Slot(object)
    def on_plugin_disabled(self, plugin_info):
        """Handle plugin disabled signal"""
        # Find the item for this plugin
        for i in range(self.plugin_list.count()):
            item = self.plugin_list.item(i)
            if item.plugin_info.id == plugin_info.id:
                item.plugin_info = plugin_info
                item.update_icon()
                break
                
    @Slot(object)
    def on_plugin_state_changed(self, plugin_info):
        """Handle plugin state changed signal"""
        # Find the item for this plugin
        for i in range(self.plugin_list.count()):
            item = self.plugin_list.item(i)
            if item.plugin_info.id == plugin_info.id:
                item.plugin_info = plugin_info
                item.update_icon()
                
                # If this is the currently displayed plugin, update the details
                current_item = self.plugin_list.currentItem()
                if current_item and current_item.plugin_info.id == plugin_info.id:
                    self.update_details(plugin_info)
                
                break
                
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Disconnect from plugin manager signals
        self.plugin_manager.plugin_loaded.disconnect(self.on_plugin_loaded)
        self.plugin_manager.plugin_unloaded.disconnect(self.on_plugin_unloaded)
        self.plugin_manager.plugin_enabled.disconnect(self.on_plugin_enabled)
        self.plugin_manager.plugin_disabled.disconnect(self.on_plugin_disabled)
        self.plugin_manager.plugin_state_changed.disconnect(self.on_plugin_state_changed)
        
        # Accept the event
        event.accept()

    def filter_plugins(self, text):
        """Filter the plugin list based on text input"""
        for i in range(self.plugin_list.count()):
            item = self.plugin_list.item(i)
            if text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    @Slot()
    def on_enable_clicked(self):
        """Handle enable button clicked"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            return
            
        plugin_info = current_item.plugin_info
        plugin_id = plugin_info.id
        
        # Add to pending changes
        if plugin_id not in self.pending_plugin_changes:
            self.pending_plugin_changes[plugin_id] = {"enabled": None, "settings": {}}
            
        self.pending_plugin_changes[plugin_id]["enabled"] = True
        
        # Update UI
        self.enable_button.setChecked(True)
        
        # Update status text
        current_status = self.id_label.text().split(" (will be")[0]
        self.id_label.setText(f"{current_status} (will be enabled on save)")
        self.name_label.setText(f"{current_status} (will be enabled on save)")
        self.version_label.setText(f"{current_status} (will be enabled on save)")
        self.author_label.setText(f"{current_status} (will be enabled on save)")
        self.min_version_label.setText(f"{current_status} (will be enabled on save)")
        self.max_version_label.setText(f"{current_status} (will be enabled on save)")
        self.deps_label.setText(f"{current_status} (will be enabled on save)")
        self.reqs_label.setText(f"{current_status} (will be enabled on save)")
        self.sys_reqs_label.setText(f"{current_status} (will be enabled on save)")
        self.entry_point_label.setText(f"{current_status} (will be enabled on save)")
        self.path_label.setText(f"{current_status} (will be enabled on save)")
        self.id_label.setStyleSheet("color: orange;")
        self.name_label.setStyleSheet("color: orange;")
        self.version_label.setStyleSheet("color: orange;")
        self.author_label.setStyleSheet("color: orange;")
        self.min_version_label.setStyleSheet("color: orange;")
        self.max_version_label.setStyleSheet("color: orange;")
        self.deps_label.setStyleSheet("color: orange;")
        self.reqs_label.setStyleSheet("color: orange;")
        self.sys_reqs_label.setStyleSheet("color: orange;")
        self.entry_point_label.setStyleSheet("color: orange;")
        self.path_label.setStyleSheet("color: orange;")
        
        # Update status bar
        self._update_status_bar()
        
        # Update button states
        self._update_action_buttons(plugin_info)
        
        # Apply visual indication of pending change
        font = current_item.font()
        font.setBold(True)
        current_item.setFont(font)
        
        # Enable save button
        self._update_save_button_state()
        
    @Slot()
    def on_disable_clicked(self):
        """Handle disable button clicked"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            return
            
        plugin_info = current_item.plugin_info
        plugin_id = plugin_info.id
        
        # Add to pending changes
        if plugin_id not in self.pending_plugin_changes:
            self.pending_plugin_changes[plugin_id] = {"enabled": None, "settings": {}}
            
        self.pending_plugin_changes[plugin_id]["enabled"] = False
        
        # If the plugin is currently loaded, unload it immediately
        if plugin_info.state.is_loaded:
            logger.info(f"Immediately unloading plugin {plugin_id} when disable button is clicked")
            
            # Show "Unloading..." message with busy cursor
            self.setCursor(Qt.WaitCursor)
            self.status_bar.setText(f"Unloading plugin: {plugin_info.name}...")
            self.status_bar.setStyleSheet("padding: 5px; background-color: #ffe8cc; font-weight: bold;")
            QApplication.processEvents()  # Ensure the UI updates
            
            # Force unload the plugin 
            success = self.plugin_manager.unload_plugin(plugin_id)
            
            # Restore cursor
            self.setCursor(Qt.ArrowCursor)
            
            if success:
                # Force refresh the plugin state
                plugin_info = self.plugin_manager.get_plugin(plugin_id)
                current_item.plugin_info = plugin_info
                current_item.update_icon()
                
                # Show success feedback
                self.status_bar.setText(f"Plugin '{plugin_info.name}' unloaded. It will be disabled when changes are saved.")
                logger.info(f"Successfully unloaded plugin {plugin_id} immediately on disable click")
            else:
                # Show error feedback
                self.status_bar.setText(f"Failed to unload plugin '{plugin_info.name}'. See logs for details.")
                logger.error(f"Failed to unload plugin {plugin_id} on disable click")
        
        # Update UI
        self.enable_button.setChecked(False)
        
        # Update status text
        current_status = self.id_label.text().split(" (will be")[0]
        self.id_label.setText(f"{current_status} (will be disabled on save)")
        self.name_label.setText(f"{current_status} (will be disabled on save)")
        self.version_label.setText(f"{current_status} (will be disabled on save)")
        self.author_label.setText(f"{current_status} (will be disabled on save)")
        self.min_version_label.setText(f"{current_status} (will be disabled on save)")
        self.max_version_label.setText(f"{current_status} (will be disabled on save)")
        self.deps_label.setText(f"{current_status} (will be disabled on save)")
        self.reqs_label.setText(f"{current_status} (will be disabled on save)")
        self.sys_reqs_label.setText(f"{current_status} (will be disabled on save)")
        self.entry_point_label.setText(f"{current_status} (will be disabled on save)")
        self.path_label.setText(f"{current_status} (will be disabled on save)")
        self.id_label.setStyleSheet("color: #888;")
        self.name_label.setStyleSheet("color: #888;")
        self.version_label.setStyleSheet("color: #888;")
        self.author_label.setStyleSheet("color: #888;")
        self.min_version_label.setStyleSheet("color: #888;")
        self.max_version_label.setStyleSheet("color: #888;")
        self.deps_label.setStyleSheet("color: #888;")
        self.reqs_label.setStyleSheet("color: #888;")
        self.sys_reqs_label.setStyleSheet("color: #888;")
        self.entry_point_label.setStyleSheet("color: #888;")
        self.path_label.setStyleSheet("color: #888;")
        
        # Update status bar
        self._update_status_bar()
        
        # Update button states
        self._update_action_buttons(plugin_info)
        
        # Apply visual indication of pending change
        font = current_item.font()
        font.setBold(True)
        current_item.setFont(font)
        
        # Enable save button
        self._update_save_button_state()
        
        # Refresh the plugin details view to show current state
        self.update_details(plugin_info)
        
    @Slot()
    def on_load_clicked(self):
        """Handle load button clicked"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            return
            
        plugin_info = current_item.plugin_info
        plugin_id = plugin_info.id
        
        # Attempt to load the plugin immediately (no pending changes)
        instance = self.plugin_manager.load_plugin(plugin_id)
        
        if instance:
            # Update UI to reflect the new state
            self.update_details(plugin_info)
            current_item.update_icon()
            QMessageBox.information(
                self, 
                "Plugin Loaded",
                f"Plugin '{plugin_info.name}' has been loaded successfully."
            )
        else:
            QMessageBox.warning(
                self, 
                "Load Failed",
                f"Failed to load plugin '{plugin_info.name}'. Check the logs for details."
            )
            
    @Slot()
    def on_unload_clicked(self):
        """Handle unload button clicked"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            return
            
        plugin_info = current_item.plugin_info
        plugin_id = plugin_info.id
        
        logger.debug(f"Unloading plugin via UI: {plugin_id} (current state: {plugin_info.state.name})")
        
        # Show "Unloading..." message with busy cursor
        self.setCursor(Qt.WaitCursor)
        self.status_bar.setText(f"Unloading plugin: {plugin_info.name}...")
        self.status_bar.setStyleSheet("padding: 5px; background-color: #ffe8cc; font-weight: bold;")
        QApplication.processEvents()  # Ensure the UI updates
        
        # Attempt to unload the plugin immediately (no pending changes)
        success = self.plugin_manager.unload_plugin(plugin_id)
        
        # Get fresh plugin info after unload attempt
        plugin_info = self.plugin_manager.get_plugin(plugin_id)
        current_item.plugin_info = plugin_info
        
        # Restore cursor
        self.setCursor(Qt.ArrowCursor)
        
        if success:
            # Log success for debugging
            logger.debug(f"Successfully unloaded plugin {plugin_id}, state is now {plugin_info.state.name}")
            
            # Forcibly update the icon to reflect the new state
            current_item.update_icon()
            
            # Update UI to reflect the new state
            self.update_details(plugin_info)
            
            # Force update action buttons
            self._update_action_buttons(plugin_info)
            
            # Show success message
            self.status_bar.setText(f"Plugin '{plugin_info.name}' successfully unloaded.")
            self.status_bar.setStyleSheet("padding: 5px; background-color: #d0f0d0; font-weight: bold;")
            
            QMessageBox.information(
                self, 
                "Plugin Unloaded",
                f"Plugin '{plugin_info.name}' has been unloaded successfully."
            )
        else:
            # Log failure for debugging
            logger.error(f"Failed to unload plugin {plugin_id}, state remained {plugin_info.state.name}")
            
            # Update UI anyway in case of partial state change
            current_item.update_icon()
            self.update_details(plugin_info)
            self._update_action_buttons(plugin_info)
            
            # Show error message
            self.status_bar.setText(f"Failed to unload plugin '{plugin_info.name}'. See logs for details.")
            self.status_bar.setStyleSheet("padding: 5px; background-color: #ffd0d0; font-weight: bold;")
            
            QMessageBox.warning(
                self, 
                "Unload Failed",
                f"Failed to unload plugin '{plugin_info.name}'. Check the logs for details."
            ) 

    def on_plugin_status_changed(self, plugin_info, status_message):
        """Handle plugin status changed signal"""
        # Add to plugin log
        if plugin_info.id not in self.plugin_logs:
            self.plugin_logs[plugin_info.id] = []
        
        # Add timestamp to the message
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {status_message}"
        self.plugin_logs[plugin_info.id].append(log_entry)
        
        # If this is the currently displayed plugin, update the log
        current_item = self.plugin_list.currentItem()
        if current_item and current_item.plugin_info.id == plugin_info.id:
            self.log_text.append(log_entry)
            # Scroll to the bottom
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    @Slot()
    def on_open_plugin_directory_clicked(self):
        """Handle open plugin directory button clicked"""
        import subprocess
        import platform
        
        # Get the external plugins directory from plugin manager
        plugin_dir = self.plugin_manager.external_plugins_dir
        
        # Ensure the directory exists
        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir, exist_ok=True)
        
        try:
            # Open the directory in the default file manager
            if platform.system() == "Windows":
                os.startfile(plugin_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", plugin_dir])
            else:  # Linux and other Unix-like systems
                subprocess.run(["xdg-open", plugin_dir])
                
            logger.info(f"Opened plugin directory: {plugin_dir}")
        except Exception as e:
            logger.error(f"Failed to open plugin directory: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open plugin directory:\n{plugin_dir}\n\nError: {str(e)}"
            )

    @Slot()
    def on_reload_all_plugins_clicked(self):
        """Handle reload all plugins button clicked"""
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Reload All Plugins",
            "This will reload all plugins and discover any new plugins in the plugin directories.\n\n"
            "Any unsaved changes will be lost. Do you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Clear any pending changes
            self.pending_plugin_changes.clear()
            
            # Use the plugin manager's reload_all_plugins method
            success = self.plugin_manager.reload_all_plugins()
            
            if success:
                # Refresh the plugin list
                self.load_plugins()
                
                # Update status bar
                self._update_status_bar()
                
                logger.info("Successfully reloaded all plugins")
                QMessageBox.information(
                    self,
                    "Plugins Reloaded",
                    "All plugins have been reloaded successfully.\n\n"
                    "New plugins have been discovered and existing plugins have been refreshed."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Reload Failed",
                    "Failed to reload all plugins. Check the logs for details."
                )
            
        except Exception as e:
            logger.error(f"Failed to reload all plugins: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to reload all plugins:\n\n{str(e)}"
            )