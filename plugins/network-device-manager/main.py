#!/usr/bin/env python3
# netWORKS - Network Device Manager Plugin

import os
import json
import base64
import logging
import importlib
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDialog, QFormLayout, QLineEdit, QCheckBox, QMessageBox,
    QFileDialog, QGroupBox, QSplitter, QMenu, QApplication,
    QToolButton
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QTimer
from PySide6.QtGui import QAction, QIcon, QFont

try:
    # Try to import optional dependencies
    import paramiko
    import netmiko
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
    import yaml
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

# Add the current directory to sys.path to make imports work
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import device manager and connection handler
from device_manager import DeviceManager
from connection_handler import ConnectionHandler
from credential_manager import CredentialManager
from command_manager import CommandManager
from ui.device_panel import DevicePanel
from ui.command_panel import CommandPanel
from ui.output_panel import OutputPanel
from ui.config_dialog import ConfigDialog

class NetworkDeviceManagerPlugin:
    """
    Plugin for connecting to and managing network devices via SSH/telnet.
    Allows running commands, storing outputs, and managing device configurations.
    """
    
    def __init__(self, plugin_api):
        self.api = plugin_api
        self.api.log("Network Device Manager plugin initializing...")
        
        # Check dependencies
        if not DEPENDENCIES_AVAILABLE:
            self.api.log("Warning: Some dependencies are missing.", level="WARNING")
            self.api.show_message(
                "Missing Dependencies",
                "Some dependencies required by Network Device Manager are missing. "
                "Please install them by running: pip install -r plugins/network-device-manager/requirements.txt",
                level="warning"
            )
        
        # Initialize data directories
        # Get the root application path
        app_root = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")))
        
        # Use root data directory for device-related data
        self.data_dir = app_root / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Create command directories in root data
        self.commands_dir = self.data_dir / "commands"
        self.commands_dir.mkdir(exist_ok=True)
        
        # Use root data for outputs
        self.output_dir = self.data_dir / "outputs"
        self.output_dir.mkdir(exist_ok=True)
        
        # Keep plugin-specific config in plugin directory
        plugin_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.plugin_data_dir = plugin_dir / "data"
        self.plugin_data_dir.mkdir(exist_ok=True)
        self.config_dir = self.plugin_data_dir / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # Load default commands if they don't exist
        self._initialize_default_commands()
        
        # Initialize credential manager (doesn't require main window)
        self.credential_manager = CredentialManager(self.config_dir)
        self.command_manager = CommandManager(self.commands_dir)
        
        # Initialize connection handler (doesn't require database)
        self.connection_handler = ConnectionHandler(self.credential_manager)
        
        # Device manager will be initialized when main window is ready
        self.device_manager = None
        
        # Device info
        self.current_device = None
        
        # Register with main window when ready
        self.api.on_main_window_ready(self.on_main_window_ready)
        
        # Register hooks
        self.register_hooks()
        
        self.api.log("Network Device Manager plugin initialized")
    
    def _initialize_default_commands(self):
        """Initialize default command sets if they don't exist."""
        default_commands = {
            "cisco_ios": {
                "name": "Cisco IOS",
                "description": "Commands for Cisco IOS devices",
                "commands": {
                    "show_version": {
                        "command": "show version",
                        "description": "Display version information",
                        "output_type": "text"
                    },
                    "show_interfaces": {
                        "command": "show ip interface brief",
                        "description": "Display interface status and IP addresses",
                        "output_type": "tabular"
                    },
                    "show_inventory": {
                        "command": "show inventory",
                        "description": "Display hardware inventory",
                        "output_type": "text"
                    },
                    "show_running_config": {
                        "command": "show running-config",
                        "description": "Display current configuration",
                        "output_type": "text"
                    }
                }
            },
            "junos": {
                "name": "Juniper JunOS",
                "description": "Commands for Juniper JunOS devices",
                "commands": {
                    "show_version": {
                        "command": "show version",
                        "description": "Display version information",
                        "output_type": "text"
                    },
                    "show_interfaces": {
                        "command": "show interfaces terse",
                        "description": "Display interface status",
                        "output_type": "tabular"
                    },
                    "show_chassis": {
                        "command": "show chassis hardware",
                        "description": "Display hardware information",
                        "output_type": "text"
                    },
                    "show_configuration": {
                        "command": "show configuration",
                        "description": "Display current configuration",
                        "output_type": "text"
                    }
                }
            }
        }
        
        for device_type, command_set in default_commands.items():
            command_file = self.commands_dir / f"{device_type}.json"
            if not command_file.exists():
                with open(command_file, 'w') as f:
                    json.dump(command_set, f, indent=4)
    
    def register_hooks(self):
        """Register hooks with the API.
        
        This method registers the plugin's hooks with the API. These hooks are used to
        receive events from the core application.
        """
        # Register the plugin's hooks
        self.api.log("Registering hooks for Network Device Manager Plugin", level="DEBUG")

        # Device selection hook - connect to both hook and direct signal if available
        self.api.register_hook('device_select', self.hook_device_select)
        
        # Try to connect directly to device selection signals if possible
        try:
            # Attempt to connect to the main window's device table if available
            if hasattr(self.api, 'main_window') and hasattr(self.api.main_window, 'device_table'):
                self.api.log("Connecting directly to main window's device table", level="DEBUG")
                if hasattr(self.api.main_window.device_table, 'device_selected'):
                    self.api.main_window.device_table.device_selected.connect(self.hook_device_select)
                    self.api.log("Successfully connected to device_table device_selected signal", level="DEBUG")
        except Exception as e:
            self.api.log(f"Error connecting to device selection signals: {str(e)}", level="ERROR")
        
        self.api.log("Hooks registered for Network Device Manager Plugin", level="DEBUG")
    
    def on_main_window_ready(self):
        """Called when the main window is ready."""
        try:
            # Now we can safely initialize device manager
            self.device_manager = DeviceManager(self.api, self.credential_manager)
            
            # Provide access to the command_manager
            self.device_manager.command_manager = self.command_manager
            
            # Create UI components
            self.create_ui()
            
            # Directly connect to the device table's selection signal
            # This ensures we'll get device selection events directly
            if hasattr(self.api.main_window, 'device_table'):
                self.api.log("Connecting directly to device_table's selection signal", level="DEBUG")
                self.api.main_window.device_table.device_selected.connect(self.hook_device_select)
        except Exception as e:
            self.api.log(f"Error initializing plugin: {str(e)}", level="ERROR")
    
    def create_ui(self):
        """Create UI components."""
        self.api.log("Creating UI components...")
        
        # If device_manager isn't available, don't try to create UI
        if self.device_manager is None:
            self.api.log("Cannot create UI: device manager not initialized", level="ERROR")
            return
        
        # Create device panel for right side
        self.device_panel = DevicePanel(self.api, self.device_manager)
        
        # Create command panel
        self.command_panel = CommandPanel(
            self.api, 
            self.command_manager,
            self.connection_handler
        )
        
        # Set references between components so they can access each other
        self.command_panel.set_device_manager(self.device_manager)
        self.command_panel.set_device_panel(self.device_panel)
        
        # Create output panel
        self.output_panel = OutputPanel(
            self.api,
            self.output_dir
        )
        
        # Create bottom panel with tabs
        self.bottom_panel = QTabWidget()
        
        # Register the Command Outputs tab (but don't add it to the main UI yet)
        self.bottom_panel.addTab(self.output_panel, "Command Output")
        
        # Get the all outputs widget from the output panel
        if hasattr(self.output_panel, 'output_tabs') and self.output_panel.output_tabs.count() > 0:
            # We're removing the All Outputs tab completely
            # The all outputs functionality will still be available within the Network Commands tab
            pass
        
        # Don't register bottom panel as a permanent tab - it will only be shown when viewing output
        # self.api.add_tab(self.bottom_panel, "Network Device Manager")
        
        # Store the bottom panel for later use, but don't display it yet
        self.api.log("Command Output panel created but not added to UI until needed", level="DEBUG")
        
        # Register panels
        self.api.register_panel(self.device_panel, "right", "Device Manager")
        
        # Register menu items
        self.register_menu_items()
        
        # Register context menu items
        self.register_context_menu()
        
        # Register toolbar buttons
        self.register_toolbar_buttons()
        
        self.api.log("UI components created")
    
    def register_menu_items(self):
        """Register menu items for the plugin."""
        try:
            # Try to use the register_menu method if available
            if hasattr(self.api, 'register_menu'):
                # Create Network Device Manager menu
                self.api.register_menu(
                    label="Network Device Manager",
                    parent_menu="Tools"
                )
                
                # Add items to the menu
                self.api.register_menu_item(
                    label="Connect to Device",
                    callback=self.connect_to_selected_device,
                    enabled_callback=lambda device: self.current_device is not None,
                    parent_menu="Tools/Network Device Manager"
                )
                
                self.api.register_menu_item(
                    label="Run Command",
                    callback=self.run_command_dialog,
                    enabled_callback=lambda device: self.current_device is not None,
                    parent_menu="Tools/Network Device Manager"
                )
                
                self.api.register_menu_item(
                    label="Manage Device Commands",
                    callback=self.manage_commands,
                    parent_menu="Tools/Network Device Manager"
                )
                
                self.api.register_menu_item(
                    label="Manage Credentials",
                    callback=self.manage_credentials,
                    parent_menu="Tools/Network Device Manager"
                )
                
                self.api.register_menu_item(
                    label="Settings",
                    callback=self.show_settings,
                    parent_menu="Tools/Network Device Manager"
                )
            else:
                # Fallback to simpler menu item registration if register_menu is not available
                self.api.log("Advanced menu registration not available, using simplified approach", level="WARNING")
                
                # Add items directly to Tools menu
                self.api.register_menu_item(
                    label="NDM: Connect to Device",
                    callback=self.connect_to_selected_device,
                    enabled_callback=lambda device: self.current_device is not None
                )
                
                self.api.register_menu_item(
                    label="NDM: Run Command",
                    callback=self.run_command_dialog,
                    enabled_callback=lambda device: self.current_device is not None
                )
                
                self.api.register_menu_item(
                    label="NDM: Manage Device Commands",
                    callback=self.manage_commands
                )
                
                self.api.register_menu_item(
                    label="NDM: Manage Credentials",
                    callback=self.manage_credentials
                )
                
                self.api.register_menu_item(
                    label="NDM: Settings",
                    callback=self.show_settings
                )
        except Exception as e:
            self.api.log(f"Error registering menu items: {str(e)}", level="ERROR")
    
    def register_context_menu(self):
        """Register context menu items for devices."""
        try:
            if not hasattr(self.api, 'register_context_menu_item'):
                self.api.log("Context menu registration not supported by this API", level="WARNING")
                return
                
            self.api.register_context_menu_item(
                "device_table",
                "Connect (SSH)",
                lambda device: self.connect_to_device(device, "ssh")
            )
            
            self.api.register_context_menu_item(
                "device_table",
                "Connect (Telnet)",
                lambda device: self.connect_to_device(device, "telnet")
            )
            
            self.api.register_context_menu_item(
                "device_table",
                "Run Command",
                lambda device: self.run_command_dialog(device)
            )
            
            self.api.register_context_menu_item(
                "device_table",
                "View Command Outputs",
                lambda device: self.view_device_outputs(device)
            )
        except Exception as e:
            self.api.log(f"Error registering context menu items: {str(e)}", level="ERROR")
    
    def register_toolbar_buttons(self):
        """Register buttons on the ribbon toolbar for the plugin."""
        try:
            if not hasattr(self.api, 'main_window') or not self.api.main_window:
                self.api.log("Main window not available for toolbar registration", level="WARNING")
                return

            main_window = self.api.main_window
            
            # Create network device action buttons with proper icons
            # Connect action
            connect_ssh_action = QAction("Connect SSH", main_window)
            connect_ssh_action.setIcon(QIcon.fromTheme("network-server"))
            connect_ssh_action.setEnabled(False)  # Initially disabled
            connect_ssh_action.triggered.connect(lambda: self.connect_to_selected_device("ssh"))
            
            # Telnet action
            connect_telnet_action = QAction("Connect Telnet", main_window)
            connect_telnet_action.setIcon(QIcon.fromTheme("network-transmit"))
            connect_telnet_action.setEnabled(False)  # Initially disabled
            connect_telnet_action.triggered.connect(lambda: self.connect_to_selected_device("telnet"))
            
            # Command execution action
            execute_command_action = QAction("Execute Command", main_window)
            execute_command_action.setIcon(QIcon.fromTheme("system-run"))
            execute_command_action.setEnabled(False)  # Initially disabled
            execute_command_action.triggered.connect(self.run_command_dialog)
            
            # Store actions for later enabling/disabling
            self.toolbar_actions = {
                "connect_ssh": connect_ssh_action,
                "connect_telnet": connect_telnet_action,
                "execute_command": execute_command_action
            }
            
            # Create tool buttons for each action
            connect_ssh_button = QToolButton()
            connect_ssh_button.setDefaultAction(connect_ssh_action)
            connect_ssh_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            
            connect_telnet_button = QToolButton()
            connect_telnet_button.setDefaultAction(connect_telnet_action)
            connect_telnet_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            
            execute_command_button = QToolButton()
            execute_command_button.setDefaultAction(execute_command_action)
            execute_command_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            
            # Find or create a group in the Tools tab for network device actions
            network_device_group = None
            
            # First check if the network group already exists in the tools tab
            if hasattr(main_window, 'network_group'):
                network_device_group = main_window.network_group
            else:
                # Create a new group in tools tab if needed
                self.api.log("Creating network device group in tools tab")
                network_device_group = main_window.create_toolbar_group("Network Devices", main_window.tools_tab)
            
            # Add buttons to the group
            network_device_group.layout().addWidget(connect_ssh_button)
            network_device_group.layout().addWidget(connect_telnet_button)
            network_device_group.layout().addWidget(execute_command_button)
            
            # Management actions (in the Plugins tab)
            # Command management action
            manage_commands_action = QAction("Manage Commands", main_window)
            manage_commands_action.setIcon(QIcon.fromTheme("edit-find-replace"))
            manage_commands_action.triggered.connect(self.manage_commands)
            
            # Credential management action
            manage_credentials_action = QAction("Manage Credentials", main_window)
            manage_credentials_action.setIcon(QIcon.fromTheme("dialog-password"))
            manage_credentials_action.triggered.connect(self.manage_credentials)
            
            # Settings action
            settings_action = QAction("Settings", main_window)
            settings_action.setIcon(QIcon.fromTheme("preferences-system"))
            settings_action.triggered.connect(self.show_settings)
            
            # Create tool buttons for management actions
            manage_commands_button = QToolButton()
            manage_commands_button.setDefaultAction(manage_commands_action)
            manage_commands_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            
            manage_credentials_button = QToolButton()
            manage_credentials_button.setDefaultAction(manage_credentials_action)
            manage_credentials_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            
            settings_button = QToolButton()
            settings_button.setDefaultAction(settings_action)
            settings_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            
            # Create a group in the Plugins tab for network device manager
            plugins_group = None
            plugins_tab = main_window.plugins_tab
            
            # Add a new group to the Plugins tab
            self.api.log("Adding Network Device Manager group to plugins tab")
            plugins_group = main_window.create_toolbar_group("Network Device Manager", plugins_tab)
            
            # Add management buttons to the plugins group
            plugins_group.layout().addWidget(manage_commands_button)
            plugins_group.layout().addWidget(manage_credentials_button)
            plugins_group.layout().addWidget(settings_button)
            
            # Update action enablement when device selection changes
            @self.api.hook("device_select")
            def on_toolbar_device_select(device):
                # Enable or disable actions based on device selection
                has_device = device is not None
                for action_name, action in self.toolbar_actions.items():
                    action.setEnabled(has_device)
            
            self.api.log("Ribbon toolbar buttons registered successfully")
        except Exception as e:
            self.api.log(f"Error registering ribbon toolbar buttons: {str(e)}", level="ERROR")
    
    def connect_to_selected_device(self, connection_type="ssh"):
        """Connect to the currently selected device."""
        if not self.current_device:
            self.api.log("No device selected", level="WARNING")
            return
        
        self.connect_to_device(self.current_device, connection_type)
    
    def connect_to_device(self, device, connection_type="ssh"):
        """Connect to a device using SSH or telnet."""
        pass  # Implemented in connection_handler.py
    
    def run_command_dialog(self, device=None):
        """Open dialog to run a command on a device."""
        target_device = device or self.current_device
        if not target_device:
            self.api.log("No device selected", level="WARNING")
            return
            
        # This will be implemented in the command panel
        self.command_panel.show_command_dialog(target_device)
    
    def manage_commands(self):
        """Open dialog to manage device commands."""
        try:
            # Import the dialog (to avoid circular imports)
            from ui.command_set_dialog import CommandSetDialog
            
            # Create and show the dialog
            dialog = CommandSetDialog(self.api.main_window, self.command_manager)
            dialog.exec()
            
            # Reload device types in device panel if it exists
            if hasattr(self, 'device_panel'):
                self.device_panel._load_device_types()
                
            self.api.log("Command set management complete")
        except Exception as e:
            self.api.log(f"Error managing commands: {str(e)}", level="ERROR")
    
    def manage_credentials(self):
        """Open dialog to manage device credentials."""
        try:
            # Import the dialog (to avoid circular imports)
            from ui.credential_dialog import CredentialDialog
            
            # Create and show the dialog with our credential_manager instance directly
            dialog = CredentialDialog(self.api.main_window, self.credential_manager)
            dialog.exec()
            
            self.api.log("Credential management complete")
        except Exception as e:
            self.api.log(f"Error managing credentials: {str(e)}", level="ERROR")
    
    def show_settings(self):
        """Open settings dialog."""
        # To be implemented
        self.api.log("Opening settings dialog")
    
    def view_device_outputs(self, device=None):
        """View command outputs for a device."""
        target_device = device or self.current_device
        if not target_device:
            self.api.log("No device selected", level="WARNING")
            return
            
        # This method is no longer needed with the simplified UI
        # Just log a message for debugging
        self.api.log(f"View outputs requested for device {target_device['ip']} - functionality removed in simplified UI", level="DEBUG")
    
    def cleanup(self):
        """Clean up plugin resources."""
        try:
            # Save any pending data
            self.credential_manager.save()
            
            # Close connections
            if hasattr(self, 'connection_handler'):
                self.connection_handler.close_all()
            
            # Remove UI components
            if hasattr(self, 'bottom_panel'):
                self.api.remove_tab("Network Device Manager")
            
            self.api.log("Network Device Manager plugin cleanup complete")
        except Exception as e:
            self.api.log(f"Error during cleanup: {str(e)}", level="ERROR")

    def hook_device_select(self, device):
        """Centralized handler for the device_select hook.
        
        This method serves as a central point for handling device selection events.
        The issue seems to be that the device selection from the bottom panel in the core
        isn't being properly received by our plugin.
        
        Args:
            device: The device object or list of devices that was selected
        """
        try:
            # Add debug logging to see what exactly is being received
            if isinstance(device, dict):
                self.api.log(f"Device select hook received device: IP={device.get('ip')}, ID={device.get('id', 'unknown')}", level="DEBUG")
            elif isinstance(device, list):
                device_ips = [d.get('ip', 'unknown') for d in device if isinstance(d, dict)]
                self.api.log(f"Device select hook received {len(device)} devices: {', '.join(device_ips)}", level="DEBUG")
            else:
                self.api.log(f"Device select hook received unexpected type: {type(device)}", level="WARNING")
            
            # Update current_device based on what's actually selected
            if device is None:
                self.current_device = None
                self.api.log("Device selection cleared", level="DEBUG")
            else:
                # Check the type of device being received
                if isinstance(device, dict):
                    # Direct use when a dict is passed (most likely from an API method)
                    self.current_device = device
                    self.api.log(f"Using direct device dict: {device.get('ip')}", level="DEBUG")
                elif isinstance(device, list) and len(device) > 0:
                    # If it's a list with items, take the first one
                    if isinstance(device[0], dict):
                        self.current_device = device[0]
                        self.api.log(f"Using first device from list: {device[0].get('ip')}", level="DEBUG")
                    else:
                        self.api.log(f"List item is not a dict: {type(device[0])}", level="WARNING")
                        # Try to get selected devices from API as fallback
                        self._try_get_selected_devices_from_api()
                else:
                    # As a fallback, try to use the API's method to get the selected device(s)
                    self._try_get_selected_devices_from_api()
            
            # Add verification check
            if self.current_device:
                self.api.log(f"Current device set to: IP={self.current_device.get('ip')}, ID={self.current_device.get('id', 'unknown')}", level="DEBUG")
            else:
                self.api.log("Current device is None", level="DEBUG")
            
            # Update UI components with the selected device
            self._update_ui_with_current_device()
        except Exception as e:
            self.api.log(f"Error in device selection hook: {str(e)}", level="ERROR")
            import traceback
            self.api.log(traceback.format_exc(), level="DEBUG")

    def _try_get_selected_devices_from_api(self):
        """Try to get selected devices from the API as a fallback."""
        try:
            selected_devices = self.api.get_selected_devices()
            
            # Handle different return types from get_selected_devices
            if isinstance(selected_devices, list):
                if selected_devices:
                    self.current_device = selected_devices[0]
                    self.api.log(f"Fetched device from API: {self.current_device.get('ip')}", level="DEBUG")
                else:
                    self.current_device = None
                    self.api.log("API returned empty device list", level="DEBUG")
            elif isinstance(selected_devices, dict):
                # Single device
                self.current_device = selected_devices
                self.api.log(f"Fetched single device from API: {self.current_device.get('ip')}", level="DEBUG")
            else:
                self.current_device = None
                self.api.log(f"API returned unexpected type: {type(selected_devices)}", level="WARNING")
        except Exception as e:
            self.api.log(f"Error getting selected devices from API: {str(e)}", level="ERROR")
            self.current_device = None

    def _update_ui_with_current_device(self):
        """Update UI components with the current device."""
        try:
            # Update UI if it exists, using try/except for each component for robustness
            if hasattr(self, 'device_panel'):
                try:
                    self.api.log(f"Updating device panel with device: {self.current_device['ip'] if self.current_device else 'None'}", level="DEBUG")
                    self.device_panel.update_device(self.current_device)
                except Exception as e:
                    self.api.log(f"Error updating device panel: {str(e)}", level="ERROR")
            
            if hasattr(self, 'command_panel'):
                try:
                    self.command_panel.update_device(self.current_device)
                except Exception as e:
                    self.api.log(f"Error updating command panel: {str(e)}", level="ERROR")
            
            if hasattr(self, 'output_panel'):
                try:
                    self.output_panel.update_device(self.current_device)
                except Exception as e:
                    self.api.log(f"Error updating output panel: {str(e)}", level="ERROR")
        except Exception as e:
            self.api.log(f"Error updating UI components: {str(e)}", level="ERROR")

    def on_tab_added(self, tab_info):
        """Called when a tab is added to the main window.
        
        This method handles the tab_added hook event, which is fired when
        a new tab is added to the tab widget.
        
        Args:
            tab_info: Dict containing information about the added tab
        """
        try:
            self.api.log(f"Tab added: {tab_info.get('name', 'Unknown')}", level="DEBUG")
            # Check if this is a device-related tab that we should monitor
            # This is just a placeholder - implement specific functionality as needed
        except Exception as e:
            self.api.log(f"Error in tab_added hook: {str(e)}", level="ERROR")

    def show_command_history(self):
        """Show command history for the current device."""
        if not self.current_device:
            self.api.log("No device selected", level="WARNING")
            return
            
        self.view_device_outputs(self.current_device)
        
    def show_credentials_manager(self):
        """Show credentials manager dialog."""
        self.manage_credentials()

def init_plugin(plugin_api):
    """Initialize the plugin."""
    return NetworkDeviceManagerPlugin(plugin_api) 