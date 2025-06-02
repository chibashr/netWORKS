#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core Command Manager Plugin implementation
"""

import os
import datetime
from pathlib import Path
from loguru import logger
import json

from PySide6.QtCore import Qt, Signal, Slot, QObject
from PySide6.QtWidgets import QMessageBox, QMenu, QDialog, QToolBar
from PySide6.QtGui import QIcon, QAction

# Import interfaces from the main application
from src.core.plugin_interface import PluginInterface

# Local imports
from plugins.command_manager.ui.command_dialog import CommandDialog
from plugins.command_manager.ui.credential_manager import CredentialManager
from plugins.command_manager.ui.command_output_panel import CommandOutputPanel
from plugins.command_manager.ui.command_set_editor import CommandSetEditor
from plugins.command_manager.ui.settings_dialog import SettingsDialog

# Import from core components
from .plugin_setup import register_ui, register_context_menu
from .command_handler import CommandHandler
from .output_handler import OutputHandler

# Import utilities
from plugins.command_manager.utils.credential_store import CredentialStore

class CommandManagerPlugin(PluginInterface):
    """Command Manager Plugin for NetWORKS"""
    
    def __init__(self, app=None):
        """Initialize the plugin"""
        super().__init__()
        
        logger.debug("Initializing Command Manager Plugin")
        
        # Store app reference early if provided
        self.app = app
        
        # Initialize dynamic registries
        self._signals = {}
        self._ui_components = {}
        self._handlers = {}
        self._settings = {}
        self._connected_signals = set()
        
        # Initialize plugin data paths
        self._data_paths = {}
        
        # Initialize UI components
        self.command_dialog = None
        self.output_panel = None
        self.toolbar = None
        self.toolbar_action = None
        self.batch_export_action = None
        self.credential_manager_action = None
        
        # Initialize plugin settings
        self._initialize_settings()
        
        logger.debug("Command Manager Plugin instance initialized")
        
    def _initialize_settings(self):
        """Initialize plugin settings with default values"""
        settings_schema = {
            "export_filename_template": {
                "name": "Export Filename Template",
                "description": "Template for exported command filenames. Available variables: {hostname}, {ip}, {command}, {date}, and any device property.",
                "type": "string",
                "default": "{hostname}_{command}_{date}",
                "value": "{hostname}_{command}_{date}"
            },
            "export_date_format": {
                "name": "Export Date Format",
                "description": "Date format for exported filenames (using Python strftime format)",
                "type": "string",
                "default": "%Y%m%d",
                "value": "%Y%m%d"
            },
            "export_command_format": {
                "name": "Export Command Format",
                "description": "How to format command names in exported filenames",
                "type": "choice",
                "choices": ["truncated", "full", "sanitized"],
                "default": "truncated",
                "value": "truncated"
            },
            "credential_store": {
                "name": "Credential Store Settings",
                "description": "Settings for credential storage and encryption",
                "type": "dict",
                "default": {
                    "encryption_method": "bcrypt",
                    "key_derivation": "pbkdf2",
                    "iterations": 100000
                },
                "value": {
                    "encryption_method": "bcrypt",
                    "key_derivation": "pbkdf2",
                    "iterations": 100000
                }
            }
        }
        
        # Load settings from schema
        self._settings = settings_schema
        
    def register_signal(self, name, signal_type=None):
        """Dynamically register a new signal"""
        if signal_type is None:
            signal_type = Signal
        self._signals[name] = signal_type()
        return self._signals[name]
    
    def register_ui_component(self, name, component):
        """Dynamically register a UI component"""
        self._ui_components[name] = component
        return component
    
    def register_handler(self, name, handler):
        """Dynamically register a handler"""
        self._handlers[name] = handler
        return handler
    
    def register_data_path(self, name, path):
        """Dynamically register a data path"""
        self._data_paths[name] = path
        return path
    
    def get_signal(self, name):
        """Get a registered signal by name"""
        return self._signals.get(name)
    
    def get_ui_component(self, name):
        """Get a registered UI component by name"""
        return self._ui_components.get(name)
    
    def get_handler(self, name):
        """Get a registered handler by name"""
        return self._handlers.get(name)
    
    def get_data_path(self, name):
        """Get a registered data path by name"""
        return self._data_paths.get(name)
    
    def get_setting(self, name):
        """Get a setting value by name"""
        setting = self._settings.get(name)
        return setting.get("value") if setting else None
    
    def update_setting(self, name, value):
        """Update a setting value"""
        if name in self._settings:
            self._settings[name]["value"] = value
            return True
        return False
    
    def get_settings(self):
        """Get all plugin settings for the plugin manager UI"""
        return self._settings.copy()
    
    # Properties for backward compatibility
    @property
    def command_handler(self):
        """Get the command handler"""
        return self.get_handler("command_handler")
    
    @property
    def output_handler(self):
        """Get the output handler"""
        return self.get_handler("output_handler")
    
    @property
    def credential_store(self):
        """Get the credential store"""
        return self.get_handler("credential_store")
    
    @property
    def data_dir(self):
        """Get the data directory"""
        return self.get_data_path("data_dir")
    
    @property
    def commands_dir(self):
        """Get the commands directory"""
        return self.get_data_path("commands_dir")
    
    @property
    def output_dir(self):
        """Get the output directory"""
        return self.get_data_path("output_dir")
    
    def initialize(self, app, plugin_info):
        """Initialize the plugin"""
        # Store app reference and set up plugin interface (only if not already set)
        if not hasattr(self, 'app') or self.app is None:
            self.app = app
        self.plugin_info = plugin_info
        self.main_window = app.main_window
        self.device_manager = app.device_manager
        
        logger.debug(f"Command Manager initialization started. App: {app}, plugin_info: {plugin_info}")
        
        # Create and register data directories FIRST
        self._create_data_directories()
        
        # Create and register credential store
        try:
            data_dir = Path(self.plugin_info.path) / "data"
            credential_store = CredentialStore(data_dir)
            
            # Set the device manager reference in the credential store
            credential_store.set_device_manager(self.device_manager)
            
            # Register the credential store
            self.register_handler("credential_store", credential_store)
            
        except Exception as e:
            logger.error(f"Error initializing credential store: {e}")
            logger.exception("Exception details:")
        
        # Initialize and register handlers
        command_handler = CommandHandler(self)
        output_handler = OutputHandler(self)
        
        self.register_handler("command_handler", command_handler)
        self.register_handler("output_handler", output_handler)
        
        # Load command outputs and command sets
        output_handler.load_command_outputs()
        command_handler.load_default_command_sets()
        
        # Create UI components and toolbar
        register_ui(self)
        
        # Register context menu items
        register_context_menu(self)
        
        # Connect signals
        self._connect_signals()
        
        logger.info("Command Manager plugin initialized successfully")
        return True
        
    def start(self):
        """Start the plugin"""
        logger.info(f"Starting {self.plugin_info.name} plugin")
        
        try:
            # Add toolbar to main window
            if self.toolbar is None:
                logger.error("Toolbar is None! Creating it now...")
                register_ui(self)
            
            if self.main_window is None:
                logger.error("Main window is None! Cannot add toolbar.")
            else:
                try:
                    self.main_window.addToolBar(self.toolbar)
                    logger.debug("Toolbar added to main window")
                    
                    # Apply style to reduce vertical margins on main toolbar buttons
                    main_toolbar = self.main_window.findChild(QToolBar)
                    if main_toolbar:
                        main_toolbar.setStyleSheet("""
                            QToolButton {
                                padding-top: 2px;
                                padding-bottom: 2px;
                                margin-top: 1px;
                                margin-bottom: 1px;
                            }
                        """)
                        logger.debug("Applied style to main toolbar")
                except Exception as e:
                    logger.error(f"Error adding toolbar to main window: {e}")
                    logger.exception("Exception details:")
            
            # Legacy device context menu items via device_manager (keeping for compatibility)
            logger.debug("Adding device context menu items via device_manager")
            try:
                if hasattr(self.device_manager, 'add_context_menu_item'):
                    self.device_manager.add_context_menu_item(
                        "Run Commands",
                        self._on_device_context_run_commands
                    )
                    
                    self.device_manager.add_context_menu_item(
                        "Manage Credentials",
                        self._on_device_context_credentials
                    )
                    logger.debug("Context menu items added via device_manager")
                else:
                    logger.debug("add_context_menu_item not found in device_manager")
            except Exception as e:
                logger.error(f"Error adding context menu items via device_manager: {e}")
                logger.exception("Exception details:")
            
            # Add tabs to device details
            logger.debug("Adding tabs to device details")
            try:
                self.device_manager.add_device_tab_provider(self)
                logger.debug("Tab provider added")
            except Exception as e:
                logger.error(f"Error adding tab provider: {e}")
                logger.exception("Exception details:")
            
            logger.info(f"{self.plugin_info.name} plugin started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting {self.plugin_info.name} plugin: {e}")
            logger.exception("Exception details:")
            return False
        
    def stop(self):
        """Stop the plugin"""
        if not super().stop():
            return False
            
        # Disconnect signals
        self._disconnect_signals()
        
        logger.info("Command Manager Plugin stopped")
        return True
        
    def cleanup(self):
        """Clean up plugin resources"""
        logger.info(f"Command Manager Plugin cleaned up")
        
        try:
            # Save command sets
            command_handler = self.get_handler("command_handler")
            if command_handler:
                command_handler.save_command_sets()
            
            # Save command outputs
            output_handler = self.get_handler("output_handler")
            if output_handler:
                output_handler.save_command_outputs()
                    
            # Close command dialog if open
            if hasattr(self, 'command_dialog') and self.command_dialog:
                try:
                    self.command_dialog.close()
                    self.command_dialog = None
                except Exception as e:
                    logger.error(f"Error closing command dialog: {e}")
            
            # Clean up UI
            if hasattr(self, 'output_panel'):
                self.output_panel = None
            
            # Unregister context menu actions
            if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'device_table'):
                try:
                    # Unregister context menu actions
                    logger.debug("Unregistering context menu actions")
                    self.main_window.device_table.unregister_context_menu_action("Run Commands")
                    self.main_window.device_table.unregister_context_menu_action("Manage Credentials")
                    logger.debug("Context menu actions unregistered")
                except Exception as e:
                    logger.error(f"Error unregistering context menu actions: {e}")
                    logger.exception("Exception details:")
                    
            # Disconnect signals
            self._disconnect_signals()
            
            return True
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            logger.exception("Exception details:")
            return False
    
    def _create_data_directories(self):
        """Create data directories for the plugin"""
        # Main data directory
        data_dir = Path(self.plugin_info.path) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.register_data_path("data_dir", data_dir)
        
        # Command sets directory
        commands_dir = data_dir / "commands"
        commands_dir.mkdir(exist_ok=True)
        self.register_data_path("commands_dir", commands_dir)
        
        # Command outputs directory
        output_dir = data_dir / "outputs"
        output_dir.mkdir(exist_ok=True)
        self.register_data_path("output_dir", output_dir)
        
        # Legacy credentials directory - marked for migration
        legacy_creds_dir = data_dir / "credentials"
        if legacy_creds_dir.exists():
            logger.debug("Legacy credentials directory exists, will be migrated to workspace directory")
            self.register_data_path("legacy_creds_dir", legacy_creds_dir)
            
    def get_current_workspace_dir(self):
        """Get the current workspace directory
        
        Returns:
            Path: Current workspace directory path, or None if not available
        """
        try:
            # Get the current workspace from the app's device manager
            if not hasattr(self.app, 'device_manager') or not self.app.device_manager:
                logger.warning("Device manager not available")
                return None
                
            # Use the device manager's method to get workspace directory
            workspace_dir = self.app.device_manager.get_workspace_dir()
            if workspace_dir:
                return Path(workspace_dir)
            
            # Fallback: construct the path manually if the method doesn't work
            current_workspace = self.app.device_manager.current_workspace
            workspaces_dir = self.app.device_manager.workspaces_dir
            
            if current_workspace and workspaces_dir:
                workspace_dir = Path(workspaces_dir) / current_workspace
                return workspace_dir
            
            logger.warning("Could not determine workspace directory")
            return None
            
        except Exception as e:
            logger.error(f"Error getting current workspace directory: {e}")
            return None
    
    def _connect_signals(self):
        """Connect signals to slots"""
        logger.debug("Connecting signals")
        try:
            # Connect to device manager signals
            if hasattr(self.device_manager, 'device_added'):
                self.device_manager.device_added.connect(self._on_device_added)
            else:
                logger.warning("device_added signal not found")
                
            if hasattr(self.device_manager, 'device_removed'):
                self.device_manager.device_removed.connect(self._on_device_removed)
            else:
                logger.warning("device_removed signal not found")
                
            if hasattr(self.device_manager, 'device_changed'):
                self.device_manager.device_changed.connect(self._on_device_changed)
            else:
                logger.warning("device_changed signal not found")
                
            if hasattr(self.device_manager, 'selection_changed'):
                self.device_manager.selection_changed.connect(self._on_selection_changed)
            else:
                logger.warning("selection_changed signal not found")
                
            logger.debug("Signals connected successfully")
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            logger.exception("Exception details:")
    
    def _disconnect_signals(self):
        """Disconnect signals from slots"""
        logger.debug("Disconnecting signals")
        try:
            # Only disconnect if the signal exists and we're connected
            if hasattr(self.device_manager, 'device_added'):
                try:
                    self.device_manager.device_added.disconnect(self._on_device_added)
                    logger.debug("Disconnected device_added signal")
                except (RuntimeError, TypeError):
                    logger.debug("device_added signal was not connected")
                    
            if hasattr(self.device_manager, 'device_removed'):
                try:
                    self.device_manager.device_removed.disconnect(self._on_device_removed)
                    logger.debug("Disconnected device_removed signal")
                except (RuntimeError, TypeError):
                    logger.debug("device_removed signal was not connected")
                    
            if hasattr(self.device_manager, 'device_changed'):
                try:
                    self.device_manager.device_changed.disconnect(self._on_device_changed)
                    logger.debug("Disconnected device_changed signal")
                except (RuntimeError, TypeError):
                    logger.debug("device_changed signal was not connected")
                    
            if hasattr(self.device_manager, 'selection_changed'):
                try:
                    self.device_manager.selection_changed.disconnect(self._on_selection_changed)
                    logger.debug("Disconnected selection_changed signal")
                except (RuntimeError, TypeError):
                    logger.debug("selection_changed signal was not connected")
                    
            logger.debug("Signals disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting signals: {e}")
            logger.exception("Exception details:")
    
    # Event handlers for device manager signals
    
    def _on_device_added(self, device):
        """Handle device added event"""
        # Update UI if necessary
        if self.command_dialog:
            self.command_dialog.refresh_devices()
            
        if self.output_panel:
            self.output_panel.refresh()
    
    def _on_device_removed(self, device):
        """Handle device removed event"""
        # Update UI if necessary
        if self.command_dialog:
            self.command_dialog.refresh_devices()
            
        if self.output_panel:
            self.output_panel.refresh()
    
    def _on_device_changed(self, device):
        """Handle device changed event"""
        # Update UI if necessary
        if self.command_dialog:
            self.command_dialog.refresh_devices()
            
        if self.output_panel:
            self.output_panel.refresh()
    
    def _on_selection_changed(self, devices):
        """Handle device selection changed"""
        # Update commands and output panels if available
        try:
            # Update the output panel with the selected device
            if self.output_panel and devices:
                self.output_panel.set_device(devices[0])
            
            # Update the commands panel if it exists
            if hasattr(self, 'commands_panel_widget') and self.commands_panel_widget and devices:
                self.output_handler.update_commands_panel(devices[0])
        except Exception as e:
            logger.error(f"Error updating panels: {e}")
            logger.exception("Exception details:")
    
    # Plugin API methods - to be called by other components
    
    def get_toolbar_actions(self):
        """Get actions to be added to the toolbar"""
        # Ensure toolbar actions are created
        if not hasattr(self, 'toolbar_action'):
            return []
        
        actions = []
        if hasattr(self, 'toolbar_action') and self.toolbar_action:
            actions.append(self.toolbar_action)
        if hasattr(self, 'batch_export_action') and self.batch_export_action:
            actions.append(self.batch_export_action)
        if hasattr(self, 'credential_manager_action') and self.credential_manager_action:
            actions.append(self.credential_manager_action)
        
        return actions
        
    def find_existing_menu(self, menu_name):
        """Find an existing menu by name (case-insensitive)
        
        This method helps plugins integrate with existing menus rather than creating
        duplicate menus. It performs a case-insensitive search for standard menus
        like File, Edit, View, Tools, etc.
        
        Args:
            menu_name (str): The name of the menu to find
            
        Returns:
            str: The exact name of the menu if found, otherwise the original name
        """
        if not hasattr(self.main_window, 'menuBar') or not callable(self.main_window.menuBar):
            logger.warning("Main window does not have a menuBar() method")
            return menu_name
            
        menu_bar = self.main_window.menuBar()
        
        # Get all existing menu titles
        existing_menus = {}
        for menu in menu_bar.findChildren(QMenu):
            if menu.title():
                existing_menus[menu.title().lower()] = menu.title()
                
        logger.debug(f"Existing menus: {existing_menus}")
        
        # Look for a case-insensitive match
        menu_name_lower = menu_name.lower()
        if menu_name_lower in existing_menus:
            logger.debug(f"Found existing menu {existing_menus[menu_name_lower]} for {menu_name}")
            return existing_menus[menu_name_lower]
            
        return menu_name
        
    def get_menu_actions(self):
        """Get actions to be added to the main menu
        
        Returns:
            dict: Dictionary of menu name -> list of actions
        """
        logger.debug("Getting menu actions")
        
        # Create actions
        actions = {}
        
        # Tools menu
        tools_menu = []
        
        # Run Commands action
        run_commands_action = QAction("Run Commands", self.main_window)
        run_commands_action.triggered.connect(self._on_run_commands)
        tools_menu.append(run_commands_action)
        
        # Manage Credentials action
        credentials_action = QAction("Manage Credentials", self.main_window)
        credentials_action.triggered.connect(self._on_manage_credentials)
        tools_menu.append(credentials_action)
        
        # Edit Command Sets action
        edit_commands_action = QAction("Edit Command Sets", self.main_window)
        edit_commands_action.triggered.connect(self._on_edit_command_sets)
        tools_menu.append(edit_commands_action)
        
        # Batch Export action
        batch_export_action = QAction("Batch Command Export", self.main_window)
        batch_export_action.triggered.connect(self._on_batch_export)
        tools_menu.append(batch_export_action)
        
        # Settings action
        settings_action = QAction("Command Manager Settings", self.main_window)
        settings_action.triggered.connect(self._on_open_settings)
        tools_menu.append(settings_action)
        
        actions["Tools"] = tools_menu
        
        logger.debug(f"Returning {len(actions)} menu actions")
        return actions
        
    def get_device_context_menu_actions(self):
        """Get actions to be added to the device context menu"""
        return list(self.context_menu_actions.values())
        
    def get_device_tabs(self, device):
        """Get tabs to be added to the device details view
        
        Args:
            device: The device object
            
        Returns:
            list: List of (tab_name, tab_widget) tuples
        """
        # Create a commands tab for this device
        commands_tab = self.output_handler.create_device_command_tab(device)
        
        # Create a command output panel specifically for this device
        output_panel = CommandOutputPanel(self, device)
        
        # Return tabs with Commands tab first for better visibility
        return [
            ("Commands", commands_tab),
            ("Command Outputs", output_panel)
        ]
    
    def get_device_panels(self):
        """Get panels to be added to the device properties panel
        
        Returns:
            list: List of (panel_name, panel_widget) tuples
        """
        return self.output_handler.get_device_panels()
        
    # Event handlers for UI actions
    
    def _on_device_context_run_commands(self, devices):
        """Handle run commands context menu item"""
        # Fix: Check if devices is a single Device object or a list
        if not isinstance(devices, list):
            # Convert to a list with a single device
            devices = [devices]
        
        dialog = CommandDialog(self, devices, parent=self.main_window)
        dialog.exec()
        
    def _on_device_context_credentials(self, devices):
        """Handle credential manager context menu action
        
        Args:
            devices: List of selected devices
        """
        logger.debug(f"Opening credential manager for {len(devices)} devices")
        
        try:
            from plugins.command_manager.ui.credential_manager import CredentialManager
            dialog = CredentialManager(self, devices, self.main_window)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening credential manager: {e}")
            logger.exception("Exception details:")
            
            # Show error dialog
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"An error occurred while opening the credential manager: {str(e)}"
            )
    
    def _on_group_context_run_commands(self, groups):
        """Handle run commands on group context menu action
        
        Args:
            groups: List of selected device groups
        """
        logger.debug(f"Opening command dialog for {len(groups)} device groups")
        
        try:
            # Get all devices from the selected groups
            all_devices = []
            for group in groups:
                try:
                    # Get all devices in this group (more reliable now with DeviceGroup class)
                    if hasattr(group, 'get_all_devices'):
                        group_devices = group.get_all_devices()
                    elif hasattr(group, 'devices'):
                        group_devices = group.devices
                    else:
                        logger.warning(f"Unknown group structure, cannot get devices: {group}")
                        continue
                        
                    # Add to all devices list, avoiding duplicates
                    for device in group_devices:
                        if device not in all_devices:
                            all_devices.append(device)
                            
                except Exception as e:
                    logger.error(f"Error getting devices from group: {e}")
            
            if not all_devices:
                logger.warning("No devices found in selected groups")
                QMessageBox.warning(
                    self.main_window,
                    "No Devices",
                    "No devices found in the selected groups."
                )
                return
                
            logger.debug(f"Found {len(all_devices)} unique devices in selected groups")
            
            # Open command dialog with these devices
            from plugins.command_manager.ui.command_dialog import CommandDialog
            self.command_dialog = CommandDialog(self, devices=all_devices, parent=self.main_window)
            self.command_dialog.show()
        except Exception as e:
            logger.error(f"Error opening command dialog for group: {e}")
            logger.exception("Exception details:")
            
            # Show error dialog
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"An error occurred while opening the command dialog: {str(e)}"
            )
    
    def _on_group_context_credentials(self, groups):
        """Handle credential manager context menu action for groups
        
        Args:
            groups: List of selected device groups
        """
        logger.debug(f"Opening credential manager for {len(groups)} device groups")
        
        try:
            from plugins.command_manager.ui.credential_manager import CredentialManager
            dialog = CredentialManager(self, groups=groups, parent=self.main_window)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening credential manager for groups: {e}")
            logger.exception("Exception details:")
            
            # Show error dialog
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"An error occurred while opening the credential manager: {str(e)}"
            )
    
    def _on_subnet_context_run_commands(self, subnets):
        """Handle run commands on subnet context menu action
        
        Args:
            subnets: List of selected subnets
        """
        logger.debug(f"Opening command dialog for {len(subnets)} subnets")
        
        try:
            # Get all devices from the selected subnets
            all_devices = []
            for subnet in subnets:
                if 'devices' in subnet:
                    for device in subnet['devices']:
                        if device not in all_devices:
                            all_devices.append(device)
            
            if not all_devices:
                QMessageBox.warning(
                    self.main_window,
                    "No Devices",
                    "The selected subnets do not contain any devices."
                )
                return
            
            # Open command dialog with these devices
            from plugins.command_manager.ui.command_dialog import CommandDialog
            if not hasattr(self, 'command_dialog') or not self.command_dialog:
                self.command_dialog = CommandDialog(self, all_devices, self.main_window)
            else:
                self.command_dialog.set_selected_devices(all_devices)
                
            self.command_dialog.show()
            self.command_dialog.raise_()
            self.command_dialog.activateWindow()
            
            # Switch to the Subnets tab and select the subnets
            self.command_dialog.target_tabs.setCurrentIndex(2)
            
            # Select the subnets in the subnet table
            self.command_dialog.subnet_table.clearSelection()
            for row in range(self.command_dialog.subnet_table.rowCount()):
                subnet_item = self.command_dialog.subnet_table.item(row, 0)
                if subnet_item and subnet_item.data(Qt.UserRole)['subnet'] in [s['subnet'] for s in subnets]:
                    self.command_dialog.subnet_table.selectRow(row)
            
        except Exception as e:
            logger.error(f"Error opening command dialog for subnets: {e}")
            logger.exception("Exception details:")
            
            # Show error dialog
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"An error occurred while opening the command dialog: {str(e)}"
            )
    
    def _on_subnet_context_credentials(self, subnets):
        """Handle credential manager context menu action for subnets
        
        Args:
            subnets: List of selected subnets
        """
        logger.debug(f"Opening credential manager for {len(subnets)} subnets")
        
        try:
            from plugins.command_manager.ui.credential_manager import CredentialManager
            dialog = CredentialManager(self, subnets=subnets, parent=self.main_window)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening credential manager for subnets: {e}")
            logger.exception("Exception details:")
            
            # Show error dialog
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"An error occurred while opening the credential manager: {str(e)}"
            )
    
    # Methods for credential handling
    
    def get_all_device_credentials(self):
        """Get all device credentials"""
        return self.credential_store.get_all_device_credentials() if self.credential_store else {}
        
    def get_all_group_credentials(self):
        """Get all group credentials"""
        return self.credential_store.get_all_group_credentials() if self.credential_store else {}
        
    def get_all_subnet_credentials(self):
        """Get all subnet credentials"""
        return self.credential_store.get_all_subnet_credentials() if self.credential_store else {}
        
    def get_device_credentials(self, device_id, device_ip=None, groups=None):
        """Get credentials for a device
        
        Args:
            device_id: The device ID
            device_ip: The device IP address (for subnet matching)
            groups: Optional list of group names the device belongs to
            
        Returns:
            dict: Credentials dictionary or None if not found
        """
        logger.debug(f"Getting credentials for device {device_id}")
        
        if not self.credential_store:
            logger.error("Credential store is not available")
            return None
        
        # 1. First try device-specific credentials
        device_credentials = self.credential_store.get_device_credentials(device_id)
        if device_credentials:
            logger.debug(f"Found device-specific credentials for {device_id}")
            return device_credentials
            
        # 2. If no device credentials, try group credentials
        if self.device_manager:
            try:
                # Get all groups this device belongs to using new method
                device_groups = self.device_manager.get_device_groups_for_device(device_id)
                
                if device_groups:
                    logger.debug(f"Found {len(device_groups)} groups for device {device_id}")
                    
                    # Try each group's credentials
                    for group in device_groups:
                        group_name = group.name if hasattr(group, 'name') else str(group)
                        group_credentials = self.credential_store.get_group_credentials(group_name)
                        if group_credentials:
                            logger.debug(f"Using credentials from group '{group_name}' for device {device_id}")
                            return group_credentials
            except Exception as e:
                logger.error(f"Error getting group credentials for device {device_id}: {e}")
                
        # 3. If still no credentials, try subnet matching
        if device_ip:
            try:
                # Extract subnet from IP
                parts = device_ip.split('.')
                if len(parts) == 4:
                    subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
                    subnet_credentials = self.credential_store.get_subnet_credentials(subnet)
                    if subnet_credentials:
                        logger.debug(f"Using credentials from subnet {subnet} for device {device_id}")
                        return subnet_credentials
            except Exception as e:
                logger.error(f"Error getting subnet credentials: {e}")
                
        logger.debug(f"No credentials found for device {device_id}")
        return None
        
    def get_group_credentials(self, group_name):
        """Get credentials for a device group
        
        Args:
            group_name: Name of the device group
            
        Returns:
            dict: Credentials dictionary or None if not found
        """
        logger.debug(f"Getting credentials for group {group_name}")
        
        if not self.credential_store:
            logger.error("Credential store is not available")
            return None
            
        return self.credential_store.get_group_credentials(group_name)
    
    def get_subnet_credentials(self, subnet):
        """Get credentials for a subnet
        
        Args:
            subnet: Subnet in CIDR notation (e.g. 192.168.1.0/24)
            
        Returns:
            dict: Credentials dictionary or None if not found
        """
        logger.debug(f"Getting credentials for subnet {subnet}")
        
        if not self.credential_store:
            logger.error("Credential store is not available")
            return None
            
        return self.credential_store.get_subnet_credentials(subnet)
    
    def set_device_credentials(self, device_id, credentials):
        """Set credentials for a device"""
        if hasattr(self, 'credential_store') and self.credential_store:
            return self.credential_store.set_device_credentials(device_id, credentials)
            
    def set_group_credentials(self, group_name, credentials):
        """Set credentials for a group"""
        if hasattr(self, 'credential_store') and self.credential_store:
            return self.credential_store.set_group_credentials(group_name, credentials)
            
    def set_subnet_credentials(self, subnet, credentials):
        """Set credentials for a subnet"""
        if hasattr(self, 'credential_store') and self.credential_store:
            return self.credential_store.set_subnet_credentials(subnet, credentials)
            
    def delete_device_credentials(self, device_id):
        """Delete credentials for a device"""
        if hasattr(self, 'credential_store') and self.credential_store:
            return self.credential_store.delete_device_credentials(device_id)
            
    def delete_group_credentials(self, group_name):
        """Delete credentials for a group"""
        if hasattr(self, 'credential_store') and self.credential_store:
            return self.credential_store.delete_group_credentials(group_name)
            
    def delete_subnet_credentials(self, subnet):
        """Delete credentials for a subnet"""
        if hasattr(self, 'credential_store') and self.credential_store:
            return self.credential_store.delete_subnet_credentials(subnet)
            
    # Methods for command set handling
    
    def get_device_types(self):
        """Get all available device types"""
        if hasattr(self, 'command_handler') and self.command_handler:
            return self.command_handler.get_device_types()
        return []
        
    def get_firmware_versions(self, device_type):
        """Get firmware versions for a device type"""
        if hasattr(self, 'command_handler') and self.command_handler:
            return self.command_handler.get_firmware_versions(device_type)
        return []
        
    def get_commands(self, device_type, firmware_version):
        """Get commands for a device type and firmware version"""
        if hasattr(self, 'command_handler') and self.command_handler:
            return self.command_handler.get_commands(device_type, firmware_version)
        return []
        
    def get_command_set(self, device_type, firmware_version):
        """Get command set for a device type and firmware version"""
        if hasattr(self, 'command_handler') and self.command_handler:
            return self.command_handler.get_command_set(device_type, firmware_version)
        return None
    
    def get_saved_command_sets(self):
        """Get saved custom command sets
        
        Returns:
            dict: Dictionary of set name -> list of command indices
        """
        logger.debug("Getting saved command sets")
        
        # Try to get workspace directory
        workspace_dir = self.get_current_workspace_dir()
        
        if workspace_dir and workspace_dir.exists():
            # Path to saved command sets file in workspace
            workspace_cmd_dir = workspace_dir / "command_manager"
            workspace_cmd_dir.mkdir(parents=True, exist_ok=True)
            saved_sets_path = workspace_cmd_dir / "command_sets.json"
            
            # Check if file exists in workspace directory
            if saved_sets_path.exists():
                try:
                    with open(saved_sets_path, "r") as f:
                        command_sets = json.load(f)
                    logger.debug(f"Loaded command sets from workspace: {len(command_sets)} sets")
                    return command_sets
                except Exception as e:
                    logger.error(f"Error loading command sets from workspace: {e}")
                    # Fall back to plugin directory
            else:
                # Check if there's a file in the plugin directory to migrate
                plugin_sets_path = self.data_dir / "command_sets.json"
                if plugin_sets_path.exists():
                    try:
                        with open(plugin_sets_path, "r") as f:
                            command_sets = json.load(f)
                            
                        # Save to workspace directory
                        with open(saved_sets_path, "w") as f:
                            json.dump(command_sets, f, indent=2)
                        
                        logger.debug(f"Migrated command sets to workspace: {len(command_sets)} sets")
                        
                        # Try to delete the old file
                        try:
                            plugin_sets_path.unlink()
                            logger.debug("Deleted legacy command sets file")
                        except Exception as e:
                            logger.error(f"Error deleting legacy command sets file: {e}")
                            
                        return command_sets
                    except Exception as e:
                        logger.error(f"Error migrating command sets to workspace: {e}")
        
        # Legacy path (fallback)
        plugin_sets_path = self.data_dir / "command_sets.json"
        
        # Check if file exists
        if plugin_sets_path.exists():
            try:
                with open(plugin_sets_path, "r") as f:
                    command_sets = json.load(f)
                logger.debug(f"Loaded command sets from plugin directory: {len(command_sets)} sets")
                return command_sets
            except Exception as e:
                logger.error(f"Error loading command sets from plugin directory: {e}")
                return {}
        else:
            logger.debug("No saved command sets found")
            return {}
    
    def save_command_set(self, name, command_indices):
        """Save a command set
        
        Args:
            name (str): Name of the command set
            command_indices (list): List of command indices
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug(f"Saving command set '{name}' with {len(command_indices)} commands")
        
        try:
            # First try to get workspace directory
            workspace_dir = self.get_current_workspace_dir()
            
            if workspace_dir and workspace_dir.exists():
                # Path to saved command sets file in workspace
                workspace_cmd_dir = workspace_dir / "command_manager"
                workspace_cmd_dir.mkdir(parents=True, exist_ok=True)
                saved_sets_path = workspace_cmd_dir / "command_sets.json"
                
                # Load existing sets if file exists
                saved_sets = {}
                if saved_sets_path.exists():
                    try:
                        with open(saved_sets_path, "r") as f:
                            saved_sets = json.load(f)
                    except Exception as e:
                        logger.error(f"Error loading existing command sets from workspace: {e}")
                
                # Add or update the set
                saved_sets[name] = command_indices
                
                # Save to workspace file
                with open(saved_sets_path, "w") as f:
                    json.dump(saved_sets, f, indent=2)
                    
                logger.info(f"Command set '{name}' saved to workspace successfully")
                return True
            else:
                # No workspace directory, fall back to plugin directory
                logger.warning("No workspace directory found, falling back to plugin directory")
                
                # Ensure data directory exists
                self.data_dir.mkdir(parents=True, exist_ok=True)
                
                # Path to saved command sets file
                saved_sets_path = self.data_dir / "command_sets.json"
                
                # Load existing sets
                saved_sets = {}
                if saved_sets_path.exists():
                    try:
                        with open(saved_sets_path, "r") as f:
                            saved_sets = json.load(f)
                    except Exception as e:
                        logger.error(f"Error loading existing command sets: {e}")
                
                # Add or update the set
                saved_sets[name] = command_indices
                
                # Save to file
                with open(saved_sets_path, "w") as f:
                    json.dump(saved_sets, f, indent=2)
                    
                logger.info(f"Command set '{name}' saved to plugin directory successfully")
                return True
        except Exception as e:
            logger.error(f"Error saving command set '{name}': {e}")
            logger.exception("Exception details:")
            return False
    
    def get_command_outputs(self, device_id):
        """Get command outputs for a device
        
        Args:
            device_id (str): The device ID
            
        Returns:
            dict: Dictionary of command_id -> {timestamp: output}
        """
        logger.debug(f"Getting command outputs for device {device_id}")
        
        # First try using the output handler if available
        if hasattr(self, 'output_handler') and self.output_handler:
            try:
                # Use the correct method name in OutputHandler
                device_outputs = self.output_handler.get_command_outputs(device_id)
                if device_outputs:
                    return device_outputs
            except Exception as e:
                logger.debug(f"Error getting outputs through handler: {e}")
                # Continue with direct access if handler fails
        
        # Fall back to direct access
        if hasattr(self, 'outputs') and device_id in self.outputs:
            return self.outputs.get(device_id, {})
            
        # Return empty dict if no outputs found
        return {}
    
    def add_command_output(self, device_id, command_id, output, command_text=None):
        """Add command output to history
        
        Args:
            device_id (str): Device ID
            command_id (str): Command ID
            output (str): Command output
            command_text (str, optional): Command text
        """
        logger.debug(f"Adding command output for device: {device_id}, command: {command_id}")
        
        # Delegate to output handler if available
        if hasattr(self, 'output_handler') and self.output_handler:
            try:
                self.output_handler.add_command_output(device_id, command_id, output, command_text)
                return True
            except Exception as e:
                logger.error(f"Error adding command output via handler: {e}")
                return False
        else:
            logger.error("No output handler available")
            return False
    
    def run_command(self, device, command, credentials=None):
        """Run a command on a device
        
        Args:
            device: Device to run command on
            command (str): Command to run
            credentials (dict, optional): Credentials to use
            
        Returns:
            dict: Command result with keys 'success' and 'output'
        """
        logger.debug(f"Running command on device: {device.id if hasattr(device, 'id') else 'Unknown'}")
        
        # Delegate to command handler if available
        if hasattr(self, 'command_handler') and self.command_handler:
            try:
                return self.command_handler.run_command(device, command, credentials)
            except Exception as e:
                logger.error(f"Error running command via handler: {e}")
                # Fall back to a basic error response
                return {
                    "success": False,
                    "output": f"Command: {command}\n\nError: {str(e)}"
                }
        else:
            # No command handler available
            logger.error("No command handler available")
            return {
                "success": False,
                "output": f"Command: {command}\n\nNo command handler available"
            }
    
    def _on_run_commands(self):
        """Handle run commands menu item"""
        # Implement the logic to open the command dialog
        pass
    
    def _on_manage_credentials(self):
        """Handle manage credentials menu item"""
        # Implement the logic to open the credential manager
        pass
    
    def _on_edit_command_sets(self):
        """Handle edit command sets menu item"""
        # Implement the logic to open the command set editor
        pass
    
    def _on_batch_export(self):
        """Open batch export dialog"""
        try:
            # Ensure the import is done properly with explicit import
            from PySide6.QtWidgets import QWidget
            from plugins.command_manager.reports.command_batch_export import CommandBatchExport
            
            dialog = CommandBatchExport(self, self.main_window)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening Command Batch Export: {e}")
            logger.exception("Exception details:")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.main_window,
                "Error Opening Command Batch Export",
                f"An error occurred while opening the Command Batch Export: {str(e)}"
            )
    
    def _on_open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.main_window)
        result = dialog.exec()
        
        # If settings were changed, update UI components
        if result:
            logger.debug("Settings updated")
            # Refresh any UI components that depend on settings
    
    def get_dock_widgets(self):
        """
        Get dock widgets to be added to the main window
        
        Returns:
            list: List of (widget_name, widget, area) tuples where area is a Qt.DockWidgetArea
        """
        # Command Manager plugin doesn't add any dock widgets
        return [] 