#!/usr/bin/env python3
# Network Scanner Plugin

import os
import json
import logging
import threading
import time
import subprocess
import socket
import ipaddress
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import uuid

from PySide6.QtCore import Qt, Signal, QObject, QThread, Slot
from PySide6.QtGui import QIcon, QAction

from scan_engine import NetworkScanner

# Try to import netifaces but provide fallback if not available
try:
    import netifaces
    HAS_NETIFACES = True
except ImportError:
    HAS_NETIFACES = False
    logging.getLogger(__name__).warning("netifaces module not available, using fallback method for interface discovery")

class NetworkScannerPlugin(QObject):
    """Main plugin class for the Network Scanner plugin."""
    
    scan_started = Signal(dict)
    scan_finished = Signal(dict)
    device_found = Signal(dict)
    
    def __init__(self, plugin_api):
        """Initialize the plugin.
        
        Args:
            plugin_api: The plugin API provided by the main application
        """
        super().__init__()
        self.api = plugin_api
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Network Scanner plugin")
        
        # Initialize default configuration
        self.config = self._load_config()
        
        # Initialize scan engine
        self.scanner = NetworkScanner(self)
        
        # Initialize scan history
        self.scan_history = self._load_scan_history()
        
        # UI panels will be created when main window is ready
        self.left_panel = None
        self.right_panel = None
        self.bottom_panel = None
        
        # Register main window ready callback
        self.api.on_main_window_ready(self.init_ui)
        
        # Connect scan signals
        self.scan_started.connect(self._on_scan_started)
        self.scan_finished.connect(self._on_scan_finished)
        self.device_found.connect(self._on_device_found)
        
        self.logger.info("Network Scanner plugin initialized")
        self.logger.debug(f"Plugin initialized in thread: {QThread.currentThread()}")
    
    def init_ui(self):
        """Initialize UI components once main window is available."""
        try:
            self.logger.debug(f"Creating UI components in thread: {QThread.currentThread()}")
            
            # Import UI components here to ensure they're loaded in the main thread
            from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication, QMessageBox, QMenu, QToolButton
            from PySide6.QtGui import QIcon, QAction
            from PySide6.QtCore import QPoint
            
            # Use direct imports from the plugin directory
            import os
            import sys
            import importlib.util
            
            # Get the path to the UI modules
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            ui_dir = os.path.join(plugin_dir, 'ui')
            
            # Add both the plugin directory and ui directory to sys.path
            if plugin_dir not in sys.path:
                sys.path.insert(0, plugin_dir)
            if ui_dir not in sys.path:
                sys.path.insert(0, ui_dir)
                
            # Import directly from ui directory with proper path resolution
            import importlib.util
            
            # Define helper function to safely import modules by path
            def import_module_from_path(module_name, file_path):
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None:
                    self.logger.error(f"Could not find module: {module_name} at {file_path}")
                    return None
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
            
            # Import UI modules
            left_panel_path = os.path.join(ui_dir, 'left_panel.py')
            right_panel_path = os.path.join(ui_dir, 'right_panel.py')
            bottom_panel_path = os.path.join(ui_dir, 'bottom_panel.py')
            
            left_panel = import_module_from_path('left_panel', left_panel_path)
            right_panel = import_module_from_path('right_panel', right_panel_path)
            bottom_panel = import_module_from_path('bottom_panel', bottom_panel_path)
            
            # Get classes from modules
            ScanControlPanel = left_panel.ScanControlPanel
            ScanSettingsPanel = right_panel.ScanSettingsPanel
            ScanHistoryPanel = bottom_panel.ScanHistoryPanel
            
            # Create UI components - this is already in the main thread thanks to on_main_window_ready
            self.left_panel = ScanControlPanel(self)
            self.right_panel = ScanSettingsPanel(self)
            self.bottom_panel = ScanHistoryPanel(self)
            
            # Set plugin_id property on all panels for identification
            for panel in [self.left_panel, self.right_panel, self.bottom_panel]:
                panel.setProperty("plugin_id", "base-network-scanner")
            
            # Register UI components with the main window
            self.logger.debug("Registering left panel")
            result = self.api.register_panel(self.left_panel, "left", "Scanner")
            self.logger.debug(f"Left panel registration result: {result}")
            
            self.logger.debug("Registering right panel")
            result = self.api.register_panel(self.right_panel, "right", "Scan Settings")
            self.logger.debug(f"Right panel registration result: {result}")
            
            self.logger.debug("Registering bottom panel")
            result = self.api.add_tab(self.bottom_panel, "Scan History")
            self.logger.debug(f"Bottom panel registration result: {result}")
            
            # Register plugin menu items
            self.api.register_menu_item(
                label="Quick Scan",
                callback=self.quick_scan,
                parent_menu="Tools"
            )
            self.api.register_menu_item(
                label="Scan Manager",
                callback=self.show_scan_manager,
                parent_menu="Tools"
            )
            
            # Add templates to toolbar instead of right panel
            self.setup_toolbar_templates()
            
            self.logger.debug("UI components created and registered successfully")
        except Exception as e:
            self.logger.error(f"Error creating UI components: {str(e)}", exc_info=True)
            # Attempt to show an error message to the user
            try:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None,
                    "Network Scanner Plugin Error",
                    f"Failed to initialize Network Scanner UI components:\n{str(e)}"
                )
            except Exception as msg_error:
                self.logger.error(f"Could not show error message: {str(msg_error)}")
    
    def setup_toolbar_templates(self):
        """Setup template buttons in the toolbar."""
        try:
            if not hasattr(self.api, 'main_window') or not self.api.main_window:
                self.logger.warning("Main window not available for toolbar registration")
                return
                
            from PySide6.QtWidgets import QToolButton, QMenu
            from PySide6.QtGui import QIcon, QAction
            from PySide6.QtCore import Qt
            
            main_window = self.api.main_window
            
            # Create a toolbar group for scanner templates
            # Check if network group exists in tools tab 
            if hasattr(main_window, 'network_group'):
                templates_group = main_window.network_group
            else:
                # Create it if it doesn't exist
                templates_group = main_window.create_toolbar_group("Network", main_window.tools_tab)
            
            # Create dropdown button for templates
            templates_button = QToolButton()
            templates_button.setText("Templates")
            templates_button.setToolTip("Select scan template")
            templates_button.setPopupMode(QToolButton.InstantPopup)
            templates_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            
            # Set a network icon if available
            templates_button.setIcon(QIcon.fromTheme("network-workgroup"))
            
            # Create menu for templates
            templates_menu = QMenu(templates_button)
            
            # Add all templates to the menu
            templates = self.get_scan_templates()
            for template_id, template in templates.items():
                name = template.get("name", template_id)
                desc = template.get("description", "")
                
                action = QAction(name, templates_menu)
                action.setToolTip(desc)
                action.setData(template_id)
                action.triggered.connect(lambda checked, tid=template_id: self.select_scan_template(tid))
                templates_menu.addAction(action)
            
            # Add separator and management options
            templates_menu.addSeparator()
            
            # Add template management options
            manage_action = QAction("Manage Templates...", templates_menu)
            manage_action.triggered.connect(self.show_template_manager)
            templates_menu.addAction(manage_action)
            
            new_action = QAction("New Template...", templates_menu)
            new_action.triggered.connect(self.create_new_template)
            templates_menu.addAction(new_action)
            
            # Set the menu on the button
            templates_button.setMenu(templates_menu)
            
            # Add the button to the group
            templates_group.layout().addWidget(templates_button)
            
            # Create a dedicated New Template button in the toolbar
            new_template_button = QToolButton()
            new_template_button.setText("New Template")
            new_template_button.setToolTip("Create a new scan template")
            new_template_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            new_template_button.clicked.connect(self.create_new_template)
            
            # Set an appropriate icon if available
            new_template_button.setIcon(QIcon.fromTheme("document-new"))
            
            # Add the new template button to the group
            templates_group.layout().addWidget(new_template_button)
            
            # Store for future reference
            self.templates_button = templates_button
            
            # Update the templates when they change
            self.update_templates_menu()
            
            self.logger.debug("Added templates button to toolbar")
            
        except Exception as e:
            self.logger.error(f"Error setting up toolbar templates: {str(e)}")
    
    def update_templates_menu(self):
        """Update the templates menu with current templates."""
        try:
            if hasattr(self, 'templates_button') and self.templates_button:
                menu = self.templates_button.menu()
                if menu:
                    # Import necessary classes
                    from PySide6.QtGui import QAction
                    
                    # Clear existing template actions (but keep management actions)
                    actions = menu.actions()
                    for action in actions:
                        if action.isSeparator():
                            break  # Stop at the separator
                        menu.removeAction(action)
                    
                    # Add all templates to the menu
                    templates = self.get_scan_templates()
                    for template_id, template in templates.items():
                        name = template.get("name", template_id)
                        desc = template.get("description", "")
                        
                        action = QAction(name, menu)
                        action.setToolTip(desc)
                        action.setData(template_id)
                        action.triggered.connect(lambda checked, tid=template_id: self.select_scan_template(tid))
                        menu.insertAction(actions[0], action)  # Insert before separator
        except Exception as e:
            self.logger.error(f"Error updating templates menu: {str(e)}")
    
    def select_scan_template(self, template_id):
        """Select a scan template from the popup menu.
        
        Args:
            template_id: The ID of the template to select
        """
        try:
            # Tell the left panel to select this template
            if hasattr(self, 'left_panel') and self.left_panel:
                # Find the template in the combo box
                combo = self.left_panel.scan_type_combo
                for i in range(combo.count()):
                    if combo.itemData(i) == template_id:
                        combo.setCurrentIndex(i)
                        self.logger.debug(f"Selected template: {template_id}")
                        return
            
            self.logger.warning(f"Could not select template: {template_id}")
        except Exception as e:
            self.logger.error(f"Error selecting template: {str(e)}")
    
    def show_template_manager(self):
        """Show the template management interface."""
        try:
            # Create a dialog for template management
            from PySide6.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
                QPushButton, QFormLayout, QLineEdit, QTextEdit, QSpinBox,
                QDialogButtonBox, QGroupBox, QLabel, QMessageBox
            )
            from PySide6.QtCore import Qt
            
            dialog = QDialog(self.api.main_window)
            dialog.setWindowTitle("Manage Scan Templates")
            dialog.setMinimumSize(600, 500)
            
            # Create layout
            layout = QVBoxLayout(dialog)
            
            # Title
            title = QLabel("Scan Template Manager")
            title.setStyleSheet("font-size: 16px; font-weight: bold;")
            layout.addWidget(title)
            
            main_layout = QHBoxLayout()
            layout.addLayout(main_layout)
            
            # Left side - template list
            list_group = QGroupBox("Available Templates")
            list_layout = QVBoxLayout(list_group)
            
            template_list = QListWidget()
            list_layout.addWidget(template_list)
            
            # Load templates into list
            templates = self.get_scan_templates()
            for template_id, template in templates.items():
                name = template.get("name", template_id)
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, template_id)
                template_list.addItem(item)
            
            # Buttons for list management
            button_layout = QHBoxLayout()
            
            new_btn = QPushButton("New")
            edit_btn = QPushButton("Edit")
            delete_btn = QPushButton("Delete")
            
            button_layout.addWidget(new_btn)
            button_layout.addWidget(edit_btn)
            button_layout.addWidget(delete_btn)
            button_layout.addStretch()
            
            list_layout.addLayout(button_layout)
            
            main_layout.addWidget(list_group)
            
            # Right side - template editor
            editor_group = QGroupBox("Template Editor")
            editor_layout = QFormLayout(editor_group)
            
            name_input = QLineEdit()
            editor_layout.addRow("Name:", name_input)
            
            id_input = QLineEdit()
            editor_layout.addRow("ID:", id_input)
            
            description_input = QTextEdit()
            description_input.setMaximumHeight(80)
            editor_layout.addRow("Description:", description_input)
            
            timeout_spin = QSpinBox()
            timeout_spin.setMinimum(1)
            timeout_spin.setMaximum(30)
            timeout_spin.setValue(1)
            editor_layout.addRow("Timeout:", timeout_spin)
            
            retries_spin = QSpinBox()
            retries_spin.setMinimum(1)
            retries_spin.setMaximum(10)
            retries_spin.setValue(1)
            editor_layout.addRow("Retries:", retries_spin)
            
            parallel_spin = QSpinBox()
            parallel_spin.setMinimum(1)
            parallel_spin.setMaximum(100)
            parallel_spin.setValue(50)
            editor_layout.addRow("Parallel hosts:", parallel_spin)
            
            ports_input = QLineEdit()
            ports_input.setPlaceholderText("80,443,22,3389")
            editor_layout.addRow("Ports:", ports_input)
            
            editor_buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
            editor_layout.addRow(editor_buttons)
            
            main_layout.addWidget(editor_group)
            
            # Dialog buttons
            dialog_buttons = QDialogButtonBox(QDialogButtonBox.Close)
            layout.addWidget(dialog_buttons)
            
            # Connect signals
            def on_new():
                # Clear editor fields
                name_input.setText("")
                id_input.setText("")
                id_input.setEnabled(True)
                description_input.setText("")
                timeout_spin.setValue(1)
                retries_spin.setValue(1)
                parallel_spin.setValue(50)
                ports_input.setText("")
            
            def on_edit():
                selected_items = template_list.selectedItems()
                if not selected_items:
                    return
                
                item = selected_items[0]
                template_id = item.data(Qt.UserRole)
                
                template = self.config.get("scan_templates", {}).get(template_id)
                if not template:
                    return
                
                # Fill editor fields
                name_input.setText(template.get("name", ""))
                id_input.setText(template_id)
                id_input.setEnabled(False)  # Don't allow changing ID when editing
                description_input.setText(template.get("description", ""))
                timeout_spin.setValue(template.get("timeout", 1))
                retries_spin.setValue(template.get("retries", 1))
                parallel_spin.setValue(template.get("parallel", 50))
                
                ports = template.get("ports", [])
                ports_input.setText(",".join(map(str, ports)) if ports else "")
            
            def on_delete():
                selected_items = template_list.selectedItems()
                if not selected_items:
                    return
                
                item = selected_items[0]
                template_id = item.data(Qt.UserRole)
                
                # Don't allow deleting built-in templates
                if template_id in ["quick_scan", "deep_scan", "stealth_scan"]:
                    QMessageBox.warning(dialog, "Warning", "Cannot delete built-in templates")
                    return
                
                # Ask for confirmation
                confirm = QMessageBox.question(
                    dialog, 
                    "Confirm Deletion",
                    f"Are you sure you want to delete template '{item.text()}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if confirm == QMessageBox.Yes:
                    # Delete template
                    if self.remove_scan_template(template_id):
                        # Refresh list
                        template_list.clear()
                        templates = self.get_scan_templates()
                        for tid, template in templates.items():
                            name = template.get("name", tid)
                            new_item = QListWidgetItem(name)
                            new_item.setData(Qt.UserRole, tid)
                            template_list.addItem(new_item)
                        
                        self.logger.info(f"Template '{template_id}' deleted")
            
            def on_save():
                name = name_input.text().strip()
                template_id = id_input.text().strip()
                description = description_input.toPlainText().strip()
                
                if not name or not template_id:
                    QMessageBox.warning(dialog, "Warning", "Template name and ID are required")
                    return
                
                # Create template data
                template = {
                    "name": name,
                    "description": description,
                    "timeout": timeout_spin.value(),
                    "retries": retries_spin.value(),
                    "parallel": parallel_spin.value()
                }
                
                # Add ports if provided
                if ports_input.text():
                    try:
                        port_list = [int(p.strip()) for p in ports_input.text().split(",") if p.strip()]
                        if port_list:
                            template["ports"] = port_list
                    except ValueError:
                        QMessageBox.warning(dialog, "Warning", "Invalid port format. Use comma-separated numbers.")
                        return
                
                # Save template
                is_edit = not id_input.isEnabled()
                
                if is_edit:
                    success = self.update_scan_template(template_id, template)
                    message = f"Template '{template_id}' updated"
                else:
                    success = self.add_scan_template(template_id, template)
                    message = f"Template '{template_id}' created"
                
                if success:
                    # Refresh list
                    template_list.clear()
                    templates = self.get_scan_templates()
                    for tid, template in templates.items():
                        name = template.get("name", tid)
                        new_item = QListWidgetItem(name)
                        new_item.setData(Qt.UserRole, tid)
                        template_list.addItem(new_item)
                    
                    # Reset editor
                    id_input.setEnabled(True)
                    name_input.setText("")
                    id_input.setText("")
                    description_input.setText("")
                    timeout_spin.setValue(1)
                    retries_spin.setValue(1)
                    parallel_spin.setValue(50)
                    ports_input.setText("")
                    
                    self.logger.info(message)
                else:
                    QMessageBox.warning(dialog, "Warning", f"Failed to save template '{template_id}'")
            
            def on_cancel():
                # Reset editor
                id_input.setEnabled(True)
                name_input.setText("")
                id_input.setText("")
                description_input.setText("")
                timeout_spin.setValue(1)
                retries_spin.setValue(1)
                parallel_spin.setValue(50)
                ports_input.setText("")
            
            # Connect signals
            new_btn.clicked.connect(on_new)
            edit_btn.clicked.connect(on_edit)
            delete_btn.clicked.connect(on_delete)
            
            editor_buttons.accepted.connect(on_save)
            editor_buttons.rejected.connect(on_cancel)
            
            dialog_buttons.accepted.connect(dialog.accept)
            dialog_buttons.rejected.connect(dialog.reject)
            
            # Selection change
            def on_selection_changed():
                has_selection = len(template_list.selectedItems()) > 0
                edit_btn.setEnabled(has_selection)
                delete_btn.setEnabled(has_selection)
            
            template_list.itemSelectionChanged.connect(on_selection_changed)
            on_selection_changed()  # Initialize button states
            
            # Show dialog
            dialog.exec()
            
        except Exception as e:
            self.logger.error(f"Error showing template manager: {str(e)}", exc_info=True)
    
    def create_new_template(self):
        """Create a new scan template."""
        try:
            # Show the template manager dialog and pre-select the "New" action
            self.show_template_manager()
            
            # Note: This is now handled by the dialog's on_new method
            # which is automatically called when showing the dialog
        except Exception as e:
            self.logger.error(f"Error creating new template: {str(e)}", exc_info=True)
    
    def update_scan_template(self, template_id: str, template: Dict) -> bool:
        """Update an existing scan template."""
        if template_id not in self.config.get("scan_templates", {}):
            return False
        
        self.config["scan_templates"][template_id] = template
        self._save_config()
        
        # Update the templates menu after updating a template
        if hasattr(self, 'update_templates_menu'):
            self.update_templates_menu()
            
        return True
    
    def add_scan_template(self, template_id: str, template: Dict) -> bool:
        """Add a new scan template."""
        if template_id in self.config.get("scan_templates", {}):
            return False
        
        self.config.setdefault("scan_templates", {})[template_id] = template
        self._save_config()
        
        # Update the templates menu after adding a template
        if hasattr(self, 'update_templates_menu'):
            self.update_templates_menu()
            
        return True
    
    def remove_scan_template(self, template_id: str) -> bool:
        """Remove a scan template."""
        if template_id not in self.config.get("scan_templates", {}):
            return False
        
        del self.config["scan_templates"][template_id]
        self._save_config()
        
        # Update the templates menu after removing a template
        if hasattr(self, 'update_templates_menu'):
            self.update_templates_menu()
            
        return True
    
    def _load_config(self) -> Dict:
        """Load the plugin configuration from the config file.
        
        Returns:
            Dict: The configuration dictionary
        """
        default_config = {
            "scan_templates": {
                "quick_scan": {
                    "name": "Quick Scan",
                    "description": "Fast ping sweep of network",
                    "timeout": 1,
                    "retries": 1,
                    "parallel": 50
                },
                "deep_scan": {
                    "name": "Deep Scan",
                    "description": "Comprehensive scan with port checks",
                    "timeout": 2,
                    "retries": 2,
                    "parallel": 25,
                    "ports": [21, 22, 23, 25, 53, 80, 443, 445, 3389]
                },
                "stealth_scan": {
                    "name": "Stealth Scan",
                    "description": "Slow, stealthy scan with minimal impact",
                    "timeout": 3,
                    "retries": 1,
                    "parallel": 5
                }
            },
            "default_interface": "",
            "default_range": "192.168.1.1-254",
            "max_scan_history": 50
        }
        
        # Get plugin config from API, if available
        config = self.api.get_setting("config", default_config)
        
        # Merge with default config to ensure all fields exist
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        
        return config
    
    def _save_config(self):
        """Save plugin configuration."""
        self.api.set_setting("config", self.config)
    
    def _load_scan_history(self) -> List[Dict]:
        """Load scan history from storage."""
        history = self.api.get_setting("scan_history", [])
        
        # Limit history size
        max_history = self.config.get("max_scan_history", 50)
        if len(history) > max_history:
            history = history[-max_history:]
            self.api.set_setting("scan_history", history)
        
        return history
    
    def _save_scan_history(self):
        """Save scan history to storage."""
        max_history = self.config.get("max_scan_history", 50)
        if len(self.scan_history) > max_history:
            self.scan_history = self.scan_history[-max_history:]
        
        self.api.set_setting("scan_history", self.scan_history)
    
    def safe_trigger_hook(self, hook_name, data=None):
        """Safely trigger a hook if the method exists.
        
        Args:
            hook_name: Name of the hook to trigger
            data: Data to pass to hook handlers
        """
        try:
            if hasattr(self.api, 'trigger_hook'):
                self.api.trigger_hook(hook_name, data)
            else:
                self.logger.debug(f"Hook {hook_name} not triggered (method not available)")
        except Exception as e:
            self.logger.error(f"Error triggering hook {hook_name}: {str(e)}")
    
    def get_network_interfaces(self) -> List[Dict]:
        """Get available network interfaces."""
        try:
            interfaces = []
            
            if HAS_NETIFACES:
                # Use netifaces if available
                for iface in netifaces.interfaces():
                    # Skip loopback interfaces
                    if iface.startswith('lo'):
                        continue
                    
                    iface_info = {"name": iface, "ip": "", "alias": iface}
                    
                    # Get IPv4 address if available
                    addrs = netifaces.ifaddresses(iface)
                    if netifaces.AF_INET in addrs:
                        iface_info["ip"] = addrs[netifaces.AF_INET][0].get('addr', '')
                    
                    # Try to get a more user-friendly alias for the interface
                    try:
                        # On Windows, try to get the adapter description
                        import platform
                        if platform.system().lower() == 'windows':
                            try:
                                import winreg

                                # Get adapter information from registry
                                conn = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
                                key_path = r'SYSTEM\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002BE10318}'
                                
                                # First try the Connection registry key
                                try:
                                    parent_key = winreg.OpenKey(conn, key_path)
                                    
                                    # Try to extract UUID from interface name (common format on Windows)
                                    if '{' in iface and '}' in iface:
                                        interface_uuid = iface
                                        if not interface_uuid.startswith('{'):
                                            # Extract the UUID part
                                            interface_uuid = iface[iface.find('{'):]
                                        
                                        # Look up the interface in registry
                                        adapter_key = winreg.OpenKey(parent_key, f"{interface_uuid}\\Connection")
                                        name, _ = winreg.QueryValueEx(adapter_key, "Name")
                                        if name:
                                            iface_info["alias"] = name
                                            
                                except (WindowsError, OSError):
                                    pass
                                    
                                # If we couldn't get a name, try the network adapter registry
                                if iface_info["alias"] == iface:
                                    try:
                                        key_path = r'SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}'
                                        adapters_key = winreg.OpenKey(conn, key_path)
                                        
                                        # Iterate through adapters
                                        for i in range(50):  # Assume max 50 adapters
                                            try:
                                                adapter_key_name = winreg.EnumKey(adapters_key, i)
                                                adapter_key = winreg.OpenKey(adapters_key, adapter_key_name)
                                                
                                                # Check the adapter ID
                                                try:
                                                    adapter_id, _ = winreg.QueryValueEx(adapter_key, "NetCfgInstanceId")
                                                    if adapter_id.lower() == iface.replace('{', '').replace('}', '').lower():
                                                        desc, _ = winreg.QueryValueEx(adapter_key, "DriverDesc")
                                                        iface_info["alias"] = desc
                                                        break
                                                except (WindowsError, OSError):
                                                    pass
                                                    
                                            except (WindowsError, OSError):
                                                break  # No more adapters
                                                
                                    except (WindowsError, OSError):
                                        pass
                                
                            except Exception as e:
                                self.logger.debug(f"Error getting interface description from registry: {e}")
                        
                        # If still using raw interface name, try socket method
                        if iface_info["alias"] == iface:
                            if hasattr(socket, 'if_nameindex'):  # Available in Python 3.3+
                                for idx, name in socket.if_nameindex():
                                    if name == iface:
                                        iface_info["alias"] = f"Network Adapter {idx}"
                                        break
                        
                        # Add simple prefixes based on common interface naming patterns
                        if iface_info["alias"] == iface:
                            # Use some common naming patterns
                            if iface.startswith('eth'):
                                iface_info["alias"] = f"Ethernet {iface[3:]}"
                            elif iface.startswith('wlan'):
                                iface_info["alias"] = f"WiFi {iface[4:]}"
                            elif iface.startswith('en'):
                                iface_info["alias"] = f"Ethernet {iface[2:]}"
                            elif iface.startswith('wl'):
                                iface_info["alias"] = f"WiFi {iface[2:]}"
                            
                    except Exception as e:
                        self.logger.debug(f"Error getting interface alias: {e}")
                    
                    interfaces.append(iface_info)
            else:
                # Fallback to using socket and platform-specific commands
                self.logger.debug("Using fallback method to get network interfaces")
                
                import platform
                system = platform.system().lower()
                
                if system == 'windows':
                    # Try multiple methods on Windows to ensure we capture all interfaces
                    
                    # Method 1: Use ipconfig
                    try:
                        self.logger.debug("Trying ipconfig to detect network interfaces")
                        output = subprocess.check_output('ipconfig /all', shell=True).decode('utf-8', errors='ignore')
                        current_iface = None
                        current_ip = None
                        current_alias = None
                        
                        for line in output.split('\r\n'):
                            line = line.strip()
                            
                            # New adapter section
                            if line and not line.startswith(' ') and ':' in line:
                                # Save previous interface if we have one
                                if current_iface and current_ip:
                                    # Skip Microsoft and virtual adapters
                                    skip_keywords = ['Microsoft', 'Virtual', 'VirtualBox', 'VMware', 'Loopback', 'Pseudo']
                                    if not any(keyword in current_iface for keyword in skip_keywords):
                                        interfaces.append({"name": current_iface, "ip": current_ip, "alias": current_alias or current_iface})
                                
                                # Start new adapter
                                current_iface = line.split(':')[0].strip()
                                current_alias = line.split(':')[0].strip()  # Use the display name as alias
                                current_ip = None
                            
                            # IPv4 address line - multiple formats possible
                            elif 'IPv4' in line and ('Address' in line or 'IP' in line) and ':' in line:
                                parts = line.split(':')
                                if len(parts) > 1:
                                    current_ip = parts[1].strip().split('(')[0].strip()
                            
                            # Description line might contain a better name
                            elif 'Description' in line and ':' in line:
                                parts = line.split(':')
                                if len(parts) > 1:
                                    current_alias = parts[1].strip()
                        
                        # Don't forget the last adapter
                        if current_iface and current_ip:
                            skip_keywords = ['Microsoft', 'Virtual', 'VirtualBox', 'VMware', 'Loopback', 'Pseudo']
                            if not any(keyword in current_iface for keyword in skip_keywords):
                                interfaces.append({"name": current_iface, "ip": current_ip, "alias": current_alias or current_iface})
                    
                    except Exception as e:
                        self.logger.error(f"Error using ipconfig: {str(e)}")
                    
                    # Method 2: Use netsh (if no interfaces were found)
                    if not interfaces:
                        try:
                            self.logger.debug("Trying netsh to detect network interfaces")
                            output = subprocess.check_output('netsh interface ip show addresses', shell=True).decode('utf-8', errors='ignore')
                            current_iface = None
                            current_ip = None
                            
                            for line in output.split('\r\n'):
                                line = line.strip()
                                
                                # Interface name line
                                if line.startswith('Interface'):
                                    # Save previous interface if we have one
                                    if current_iface and current_ip:
                                        interfaces.append({"name": current_iface, "ip": current_ip, "alias": current_iface})
                                    
                                    # Start new adapter - extract name in quotes
                                    import re
                                    match = re.search(r'"([^"]+)"', line)
                                    if match:
                                        current_iface = match.group(1)
                                        current_ip = None
                                
                                # IP address line
                                elif 'IP Address' in line and ':' in line:
                                    parts = line.split(':')
                                    if len(parts) > 1:
                                        current_ip = parts[1].strip()
                            
                            # Don't forget the last adapter
                            if current_iface and current_ip:
                                interfaces.append({"name": current_iface, "ip": current_ip, "alias": current_iface})
                                
                        except Exception as e:
                            self.logger.error(f"Error using netsh: {str(e)}")
                    
                    # Method 3: Simple fallback - always add default network interface
                    if not interfaces:
                        try:
                            hostname = socket.gethostname()
                            local_ip = socket.gethostbyname(hostname)
                            interfaces.append({"name": "Default", "ip": local_ip, "alias": "Default Interface"})
                            
                            # Try to get adapter name from registry (Advanced method)
                            try:
                                import winreg
                                reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
                                key = winreg.OpenKey(reg, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkCards')
                                
                                # Enumerate all network cards
                                for i in range(32):  # Loop through possible indices
                                    try:
                                        subkey_name = winreg.EnumKey(key, i)
                                        subkey = winreg.OpenKey(key, subkey_name)
                                        description = winreg.QueryValueEx(subkey, 'Description')[0]
                                        interfaces.append({"name": description, "ip": "", "alias": description})
                                        winreg.CloseKey(subkey)
                                    except OSError:
                                        break  # No more keys
                                winreg.CloseKey(key)
                                winreg.CloseKey(reg)
                            except Exception as e:
                                self.logger.error(f"Error accessing registry: {str(e)}")
                                
                        except Exception as e:
                            self.logger.error(f"Error getting local hostname/IP: {str(e)}")
                
                elif system in ('linux', 'darwin'):
                    # Use ifconfig on Linux/macOS
                    try:
                        output = subprocess.check_output('ifconfig', shell=True).decode('utf-8', errors='ignore')
                    except (subprocess.SubprocessError, FileNotFoundError):
                        # Try ip command if ifconfig is not available
                        try:
                            output = subprocess.check_output('ip addr', shell=True).decode('utf-8', errors='ignore')
                        except (subprocess.SubprocessError, FileNotFoundError):
                            output = ""
                    
                    if output:
                        import re
                        # Process output to extract interfaces and IPs
                        current_iface = None
                        
                        for line in output.split('\n'):
                            line = line.strip()
                            
                            # New interface line
                            if line and not line.startswith(' ') and (':' in line or line.endswith(':')):
                                iface_match = re.match(r'^(\w+)[:\s]', line)
                                if iface_match:
                                    current_iface = iface_match.group(1)
                                    if current_iface.startswith('lo'):
                                        current_iface = None  # Skip loopback
                            
                            # IP address line
                            elif current_iface and ('inet ' in line or 'inet addr:' in line):
                                ip_match = re.search(r'inet (?:addr:)?(\d+\.\d+\.\d+\.\d+)', line)
                                if ip_match:
                                    ip = ip_match.group(1)
                                    if not ip.startswith('127.'):  # Skip loopback addresses
                                        # Try to get a friendly name from ip -o link for Linux
                                        alias = current_iface
                                        try:
                                            link_output = subprocess.check_output(f'ip -o link show {current_iface}', shell=True).decode('utf-8', errors='ignore')
                                            alias_match = re.search(r'alias\s+([^\\]+)', link_output)
                                            if alias_match:
                                                alias = alias_match.group(1).strip()
                                            else:
                                                # Use some common naming patterns
                                                if current_iface.startswith('eth'):
                                                    alias = f"Ethernet {current_iface[3:]}"
                                                elif current_iface.startswith('wlan'):
                                                    alias = f"WiFi {current_iface[4:]}"
                                                elif current_iface.startswith('en'):
                                                    alias = f"Ethernet {current_iface[2:]}"
                                                elif current_iface.startswith('wl'):
                                                    alias = f"WiFi {current_iface[2:]}"
                                                else:
                                                    alias = f"Network Adapter {current_iface}"
                                        except Exception:
                                            pass
                                            
                                        interfaces.append({"name": current_iface, "ip": ip, "alias": alias})
                                        current_iface = None  # Reset to avoid duplicates
                
                # Add backup interface if no interfaces were found
                if not interfaces:
                    try:
                        hostname = socket.gethostname()
                        local_ip = socket.gethostbyname(hostname)
                        interfaces.append({"name": "Default", "ip": local_ip, "alias": "Default Interface"})
                    except Exception as e:
                        self.logger.error(f"Error getting local hostname/IP: {str(e)}")
                        # Last resort - loopback interface
                        interfaces.append({"name": "Loopback", "ip": "127.0.0.1", "alias": "Loopback Interface"})
            
            # Log found interfaces for debugging
            self.logger.debug(f"Found {len(interfaces)} network interfaces:")
            for iface in interfaces:
                self.logger.debug(f"  - {iface['alias']} ({iface['name']}): {iface['ip']}")
                
            return interfaces
        except Exception as e:
            self.logger.error(f"Error getting network interfaces: {str(e)}")
            # Return a fallback interface as last resort
            return [{"name": "Default", "ip": "127.0.0.1", "alias": "Default Interface"}]
    
    def get_scan_templates(self) -> Dict:
        """Get available scan templates."""
        return self.config.get("scan_templates", {})
    
    def start_scan(self, interface: str, ip_range: str, scan_type: str = "quick_scan", **kwargs) -> str:
        """Start a network scan with the specified parameters."""
        # Generate scan ID
        scan_id = f"scan_{int(time.time())}"
        
        # Create scan configuration
        scan_config = {
            "id": scan_id,
            "interface": interface,
            "range": ip_range,
            "scan_type": scan_type,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "starting",
            "devices_found": 0,
            "total_devices": 0,
            "end_time": None
        }
        
        # Get template settings
        template = self.config.get("scan_templates", {}).get(scan_type)
        if template:
            scan_config.update(template)
        
        # Update with custom parameters
        scan_config.update(kwargs)
        
        # Add to scan history
        self.scan_history.append(scan_config)
        self._save_scan_history()
        
        # Trigger hook
        self.safe_trigger_hook("base-network-scanner:before_scan", scan_config)
        
        # Emit signal
        self.scan_started.emit(scan_config)
        
        # Start scan in background thread
        threading.Thread(
            target=self.scanner.run_scan,
            args=(scan_config,),
            daemon=True
        ).start()
        
        return scan_id
    
    def quick_scan(self):
        """Start a quick scan using default settings."""
        interface = self.config.get("default_interface", "")
        ip_range = self.config.get("default_range", "192.168.1.1-254")
        
        if not interface:
            interfaces = self.get_network_interfaces()
            if interfaces:
                interface = interfaces[0].get("name", "")
        
        return self.start_scan(interface, ip_range, "quick_scan")
    
    def show_scan_manager(self):
        """Show the scan manager dialog."""
        # This will be implemented in a future update
        self.api.log("Scan Manager dialog not yet implemented")
    
    def get_scan_history(self) -> List[Dict]:
        """Get the scan history."""
        return self.scan_history
    
    def get_scan_by_id(self, scan_id: str) -> Optional[Dict]:
        """Get a scan by its ID."""
        for scan in self.scan_history:
            if scan.get("id") == scan_id:
                return scan
        return None
    
    def get_scan_devices(self, scan_id: str) -> List[Dict]:
        """Get devices associated with a scan.
        
        Args:
            scan_id: The ID of the scan
            
        Returns:
            List of device dictionaries
        """
        # Check in-memory history
        for scan in self.scan_history:
            if scan.get('id') == scan_id and 'devices' in scan:
                return list(scan['devices'].values())
        
        return []
    
    def _on_scan_started(self, scan_config: Dict):
        """Handle scan started event."""
        self.logger.info(f"Scan started: {scan_config['id']}")
        self.api.log(f"Started {scan_config.get('name', 'scan')} on {scan_config['range']}")
        
        # Update UI
        self.bottom_panel.update_scan_history()
    
    def _on_scan_finished(self, scan_result: Dict):
        """Handle scan finished event."""
        scan_id = scan_result.get("id")
        self.logger.info(f"Scan finished: {scan_id}")
        
        # Update scan in history
        for i, scan in enumerate(self.scan_history):
            if scan.get("id") == scan_id:
                self.scan_history[i].update(scan_result)
                break
        
        self._save_scan_history()
        
        # Trigger hook
        self.safe_trigger_hook("base-network-scanner:after_scan", scan_result)
        
        # Update UI
        self.bottom_panel.update_scan_history()
        self.api.log(f"Scan completed: Found {scan_result.get('devices_found', 0)} devices")
    
    def _on_device_found(self, device: Dict):
        """Handle device found event."""
        self.logger.debug(f"Device found: {device.get('ip')}")
        
        try:
            # Log detailed device info at debug level
            self.logger.debug(f"Full device details: {device}")
            
            # Ensure device has required fields
            if not device.get('ip'):
                self.logger.warning("Received device with no IP address")
                return
                
            # Add timestamp if missing
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not device.get('last_seen'):
                device['last_seen'] = current_time
            if not device.get('first_seen'):
                device['first_seen'] = current_time
            
            # Add hostname if missing
            if not device.get('hostname'):
                device['hostname'] = f"Device-{device['ip'].split('.')[-1]}"
            
            # Ensure metadata exists
            if 'metadata' not in device:
                device['metadata'] = {}
            
            # Add OS info if available
            if device.get('os'):
                device['metadata']['os'] = device['os']
            
            # Track how this device was added
            device['metadata']['discovery_source'] = 'network_scan'
            device['metadata']['discovery_timestamp'] = current_time
            
            # Make sure the device has an ID
            if 'id' not in device:
                device['id'] = str(uuid.uuid4())
                
            # Create a success counter
            success_methods = []
            
            # Try to add directly to the main device table
            try:
                if hasattr(self.api, 'main_window') and self.api.main_window:
                    if hasattr(self.api.main_window, 'device_table'):
                        self.logger.info(f"Adding device {device['ip']} directly to main device table")
                        main_window = self.api.main_window
                        device_table = main_window.device_table
                        
                        # Debug the structure
                        self.logger.debug(f"Device table type: {type(device_table)}")
                        self.logger.debug(f"Device table methods: {dir(device_table)}")
                        
                        # Add the device
                        device_table.add_device(device)
                        success_methods.append("direct_device_table")
                    else:
                        self.logger.warning("Main window has no device_table attribute")
                else:
                    self.logger.warning("API has no main_window attribute or it's None")
            except Exception as e:
                self.logger.error(f"Error adding device directly to table: {str(e)}", exc_info=True)
            
            # Try to save via plugin API
            if "direct_device_table" not in success_methods:
                try:
                    self.logger.debug(f"Calling core plugin to add device: {device['ip']}")
                    result = self.api.call_plugin_function("core", "add_device", device)
                    if result is False:
                        self.logger.warning("Core plugin returned False when adding device")
                    else:
                        success_methods.append("core_plugin")
                except Exception as e:
                    self.logger.error(f"Error calling core plugin to add device: {str(e)}", exc_info=True)
                
            # Update the scan information in scan history
            scan_id = device.get('scan_id')
            if scan_id:
                for scan in self.scan_history:
                    if scan.get('id') == scan_id:
                        # Update the devices found count
                        devices_found = scan.get('devices_found', 0) + 1
                        scan['devices_found'] = devices_found
                        # Add device to scan's devices
                        if 'devices' not in scan:
                            scan['devices'] = {}
                        scan['devices'][device.get('ip', str(uuid.uuid4()))] = device
                        # Save to storage
                        self._save_scan_history()
                        break
            
            # Trigger hook for other plugins to use the found device
            self.safe_trigger_hook("base-network-scanner:device_found", device)
            
            # Log success or failure
            if success_methods:
                self.logger.info(f"Successfully added device {device.get('ip')} using methods: {', '.join(success_methods)}")
            else:
                self.logger.error(f"FAILED TO ADD DEVICE {device.get('ip')} - No successful methods found")
            
        except Exception as e:
            self.logger.error(f"Error processing device found event: {str(e)}", exc_info=True)
    
    def cleanup(self):
        """Clean up resources before plugin is unloaded."""
        self.logger.info("Cleaning up Network Scanner plugin")
        
        # Save any pending changes
        self._save_config()
        self._save_scan_history()
        
        # Clean up scanner
        self.scanner.stop_all_scans()


def init_plugin(plugin_api):
    """Initialize the plugin."""
    try:
        plugin_api.log("Initializing Network Scanner plugin", level="INFO")
        plugin_api.log(f"Plugin initializing in thread: {QThread.currentThread()}", level="DEBUG")
        return NetworkScannerPlugin(plugin_api)
    except Exception as e:
        import traceback
        error_msg = f"Failed to initialize Network Scanner plugin: {str(e)}\n{traceback.format_exc()}"
        plugin_api.log(error_msg, level="ERROR")
        # This will ensure the error is captured by the plugin manager
        raise RuntimeError(error_msg) from e 