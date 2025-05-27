#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Network Scanner Plugin for NetWORKS

This plugin adds network scanning capabilities to NetWORKS using Nmap.
It allows scanning network ranges and adding discovered devices to the
device inventory.
"""

from loguru import logger
import sys
import os
import time
import datetime
import ipaddress
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem, QGridLayout, 
    QFormLayout, QGroupBox, QCheckBox, QComboBox, QSplitter, QProgressBar, 
    QMessageBox, QRadioButton, QInputDialog, QHeaderView, QDialog, QDialogButtonBox
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QCoreApplication

# Import the plugin interface
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.core.plugin_interface import PluginInterface

# Import the UI utilities using absolute imports
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)
    
# Change relative imports to absolute imports
from plugins.network_scanner.ui import create_main_widget, create_dock_widget, show_error_message
from plugins.network_scanner.utils import (
    safe_action_wrapper, parse_ip_range, get_subnet_for_ip, 
    get_network_interfaces
)
from plugins.network_scanner.scanner import Scanner
from plugins.network_scanner.device_manager import (
    match_device, handle_duplicate_device, update_device_properties, 
    create_device_from_scan_data, suspend_notifications, resume_notifications
)
from plugins.network_scanner.handlers import (
    on_scan_button_clicked, on_stop_button_clicked,
    on_quick_ping_button_clicked, on_advanced_scan_button_clicked,
    on_scan_action, on_scan_selected_action, on_scan_type_manager_action,
    _on_scan_network_action, _on_scan_subnet_action, 
    _on_scan_from_device_action, _on_rescan_device_action
)

# Check for dependencies and log warnings
try:
    import nmap
    HAS_NMAP = True
except ImportError as e:
    logger.error(f"Could not import python-nmap: {e}")
    HAS_NMAP = False

try:
    import netifaces
    HAS_NETIFACES = True
except ImportError as e:
    logger.warning(f"Could not import netifaces: {e}")
    HAS_NETIFACES = False

# Define the NetworkScannerPlugin class directly in this file
class NetworkScannerPlugin(PluginInterface):
    """Network Scanner Plugin for NetWORKS
    
    This plugin adds network scanning capabilities to NetWORKS using Nmap.
    It allows scanning network ranges and adding discovered devices to the
    device inventory.
    """
    # Custom signals
    scan_started = Signal(str)  # network_range
    scan_progress_signal = Signal(int, int)  # current, total
    scan_device_found = Signal(object)  # device
    scan_completed = Signal(dict)  # results_dict
    scan_error = Signal(str)  # error_message
    
    def __init__(self):
        """Initialize the Network Scanner Plugin"""
        super().__init__()
        self.name = "Network Scanner"
        self.version = "1.2.6"
        self.description = "Scan networks and discover devices"
        self.author = "NetWORKS Team"
        self.website = "https://github.com/chibashr/netWORKS"
        self.plugin_id = "network_scanner"
        
        # UI components
        self.dock_widget = None
        self.menu_actions = {}
        self.toolbar_actions = {}
        self.context_menu_actions = {}
        self.main_window = None
        
        # Scanner properties
        self._scanner_thread = None
        self._scanner_worker = None
        self._is_scanning = False
        self.target_subnet = ""
        self.progress_value = 0  # Rename from scan_progress to avoid conflict with signal
        self.discovered_devices = []
        self._scan_log = []
        self._scan_results = {}
        self._connected_signals = set()
        
        # Initialize instance variables
        self._scanner = None
        self._scan_queue = []  # Queue for multiple device scans
        self._queue_scan_type = None  # Scan type for queued scans
        self._scan_queue_connected = False  # Whether scan queue signal is connected
        
        # Initialize settings
        self._initialize_settings()
        
        # Create UI components
        self._create_actions()
        self._create_widgets()
        
        logger.debug("NetworkScannerPlugin instance initialized")
    
    def _initialize_settings(self):
        """Initialize plugin settings with default values"""
        self.settings = {
            "scan_type": {
                "value": "quick",
                "default": "quick"
            },
            "scan_timeout": {
                "value": 300,  # 5 minutes
                "default": 300
            },
            "os_detection": {
                "value": False,
                "default": False
            },
            "port_scan": {
                "value": False,
                "default": False
            },
            "use_sudo": {
                "value": False,
                "default": False
            },
            "custom_scan_args": {
                "value": "",
                "default": ""
            },
            "scan_profiles": {
                "value": {
                    "quick": {
                        "name": "Quick Scan (ping only)",
                        "description": "Fast ping scan to discover hosts",
                        "arguments": "-sn",
                        "os_detection": False,
                        "port_scan": False,
                        "timeout": 60
                    },
                    "standard": {
                        "name": "Standard Scan",
                        "description": "Basic port scan of common ports",
                        "arguments": "-sS -T4 -F",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 300
                    },
                    "comprehensive": {
                        "name": "Comprehensive Scan",
                        "description": "Detailed scan with service detection",
                        "arguments": "-sS -T4 -A",
                        "os_detection": True,
                        "port_scan": True,
                        "timeout": 600
                    },
                    "stealth": {
                        "name": "Stealth Scan",
                        "description": "Low and slow scan to avoid detection",
                        "arguments": "-sS -T2",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 900
                    },
                    "service": {
                        "name": "Service Detection",
                        "description": "Detailed service and version detection",
                        "arguments": "-sV",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 450
                    }
                },
                "default": {}  # This will be populated in the constructor
            }
        }
        
        # Set default profiles
        self.settings["scan_profiles"]["default"] = self.settings["scan_profiles"]["value"].copy()
    
    def _create_actions(self):
        """Create plugin actions"""
        self.scan_action = QAction("Scan Network")
        self.scan_action.triggered.connect(self.on_scan_action)
        
        self.scan_selected_action = QAction("Scan from Selected Device")
        self.scan_selected_action.triggered.connect(self.on_scan_selected_action)
        
        # Add a scan type manager action for toolbar
        self.scan_type_manager_action = QAction("Scan Type Manager")
        self.scan_type_manager_action.setToolTip("Manage scan profiles and types")
        self.scan_type_manager_action.triggered.connect(self.on_scan_type_manager_action)
        
        # Register actions with the plugin
        self.menu_actions = {
            "Tools": [
                self.scan_action,
                self.scan_selected_action
            ]
        }
        
        self.toolbar_actions = {
            "Network": [
                self.scan_action,
                self.scan_selected_action,
                self.scan_type_manager_action
            ]
        }
    
    def _create_widgets(self):
        """Create plugin widgets"""
        # Use the UI utility function to create widgets
        self.ui_components = create_main_widget()
        
        # Extract components from the dictionary
        for key, value in self.ui_components.items():
            setattr(self, key, value)
        
        # Store the main widget for easy access
        self.main_widget = self.ui_components.get('main_widget')
        
        # Also store other important UI components
        self.interface_combo = self.ui_components.get('interface_combo')
        self.refresh_interfaces_button = self.ui_components.get('refresh_interfaces_button')
        self.network_range_edit = self.ui_components.get('network_range_edit')
        self.scan_type_combo = self.ui_components.get('scan_type_combo')
        self.scan_type_manager_button = self.ui_components.get('scan_type_manager_button')
        self.scan_button = self.ui_components.get('scan_button')
        self.stop_button = self.ui_components.get('stop_button')
        self.quick_ping_button = self.ui_components.get('quick_ping_button')
        self.advanced_scan_button = self.ui_components.get('advanced_scan_button')
        self.os_detection_check = self.ui_components.get('os_detection_check')
        self.port_scan_check = self.ui_components.get('port_scan_check')
        self.status_label = self.ui_components.get('status_label')
        self.progress_bar = self.ui_components.get('progress_bar')
        self.results_text = self.ui_components.get('results_text')
        
        # Connect signals to slots
        if self.scan_button:
            self.scan_button.clicked.connect(self.on_scan_button_clicked)
            
        if self.stop_button:
            self.stop_button.clicked.connect(self.on_stop_button_clicked)
        
        if self.quick_ping_button:
            self.quick_ping_button.clicked.connect(self.on_quick_ping_button_clicked)
        
        if self.advanced_scan_button:
            self.advanced_scan_button.clicked.connect(self.on_advanced_scan_button_clicked)
        
        if self.scan_type_manager_button:
            self.scan_type_manager_button.clicked.connect(self.on_scan_type_manager_action)
        
        if self.refresh_interfaces_button:
            self.refresh_interfaces_button.clicked.connect(self._update_interface_choices_and_refresh_ui)
        
        if self.interface_combo:
            self.interface_combo.currentIndexChanged.connect(self._update_network_range_from_interface)
    
    def initialize(self, app, plugin_info):
        """Initialize the plugin with the application instance"""
        logger.debug(f"Initializing Network Scanner Plugin: {plugin_info}")
        self.app = app
        self.plugin_info = plugin_info
        
        # Store references to important app components
        self.main_window = self.app.main_window
        self.device_manager = self.app.device_manager
        
        # Initialize scanner system
        self._initialize_scanner()
        
        # Connect to application signals
        self._connect_signals()
        
        # Setup device context menu
        QTimer.singleShot(1000, self._setup_device_context_menu)
        
        # Success!
        return True
        
    def cleanup(self):
        """Clean up resources used by this plugin"""
        logger.debug("Cleaning up Network Scanner Plugin")
        
        # Stop any running scan
        if hasattr(self, "_scanner") and self._scanner:
            try:
                self._scanner.stop_scan()
            except Exception as e:
                logger.error(f"Error stopping scanner: {e}")
        
        # Clean up scanner thread and worker
        try:
            self._cleanup_previous_scan()
        except Exception as e:
            logger.error(f"Error cleaning up scanner thread: {e}")
        
        # Disconnect from device manager signals if connected
        if hasattr(self, "_connected_signals") and "device_signals" in self._connected_signals:
            try:
                if hasattr(self.app, "device_manager") and self.app.device_manager:
                    # Disconnect device-related signals
                    self.app.device_manager.device_added.disconnect(self.on_device_added)
                    self.app.device_manager.device_removed.disconnect(self.on_device_removed)
                    self.app.device_manager.device_changed.disconnect(self.on_device_changed)
                    self.app.device_manager.group_added.disconnect(self.on_group_added)
                    self.app.device_manager.group_removed.disconnect(self.on_group_removed)
                    self.app.device_manager.selection_changed.disconnect(self.on_device_selected)
                    
                    # Log successful disconnection
                    logger.debug("Successfully disconnected from device manager signals")
            except Exception as e:
                logger.error(f"Error disconnecting from device manager signals: {e}")
        
        # Clean up scanner instance
        if hasattr(self, "_scanner"):
            self._scanner = None
        
        # Clean up thread and worker references
        self._scanner_thread = None
        self._scanner_worker = None
        
        # Disconnect scan queue signal if connected
        if self._scan_queue_connected:
            try:
                self.scan_completed.disconnect(self._process_scan_queue)
                self._scan_queue_connected = False
            except Exception as e:
                logger.debug(f"Error disconnecting scan queue signal: {e}")
        
        # Clear scan queue
        self._scan_queue = []
        self._queue_scan_type = None
        
        return True
        
    def _initialize_scanner(self):
        """Initialize the scanner instance"""
        try:
            # Import the scanner class
            from plugins.network_scanner.scanner import Scanner
            
            # Create a scanner instance with our settings
            self._scanner = Scanner(settings=self.settings)
            
            # Connect scanner signals to our handlers
            self._scanner.scan_started.connect(lambda network_range: self.scan_started.emit(network_range))
            self._scanner.scan_progress.connect(self._on_scan_progress)
            self._scanner.scan_device_found.connect(self._on_device_found)
            self._scanner.scan_completed.connect(self._on_scan_complete)
            self._scanner.scan_error.connect(self._on_scan_error)
            
            # Store the device manager reference in the scanner
            self._scanner.device_manager = self.device_manager
            
            # Initialize thread and worker references
            self._scanner_thread = None
            self._scanner_worker = None
            
            logger.debug("Scanner initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing scanner: {e}", exc_info=True)
            self._scanner = None
            self._scanner_thread = None
            self._scanner_worker = None
    
    def _connect_signals(self):
        """Connect to application signals"""
        # Connect to device manager signals if available
        if hasattr(self.app, "device_manager") and self.app.device_manager:
            try:
                # Connect device-related signals
                self.app.device_manager.device_added.connect(self.on_device_added)
                self.app.device_manager.device_removed.connect(self.on_device_removed)
                self.app.device_manager.device_changed.connect(self.on_device_changed)
                self.app.device_manager.group_added.connect(self.on_group_added)
                self.app.device_manager.group_removed.connect(self.on_group_removed)
                self.app.device_manager.selection_changed.connect(self.on_device_selected)
                
                # Log successful connection
                logger.debug("Successfully connected to device manager signals")
                
                # Add to our set of connected signals for cleanup
                self._connected_signals = {"device_signals"}
            except Exception as e:
                logger.error(f"Error connecting to device manager signals: {e}")
        
        # Schedule a delayed population of dropdowns
        QTimer.singleShot(100, self._populate_interface_dropdown)
        QTimer.singleShot(200, self._populate_scan_types_dropdown)

    def _populate_interface_dropdown(self):
        """Populate the interface dropdown with available network interfaces"""
        if not hasattr(self, "interface_combo") or not self.interface_combo:
            logger.warning("Interface combo box not available")
            return
            
        try:
            # Get available interfaces
            interfaces = get_network_interfaces()
            
            # Add interfaces to combo box
            for interface in interfaces:
                if_name = interface.get("name", "")
                if_ip = interface.get("ip", "")
                if_netmask = interface.get("netmask", "")
                
                if if_name and if_ip:
                    # Create a display string with name and IP
                    display = f"{if_name} ({if_ip})"
                    self.interface_combo.addItem(display)
            
            logger.debug(f"Populated interface dropdown with {len(interfaces)} interfaces")
            
            # Select first item if available
            if self.interface_combo.count() > 0:
                self.interface_combo.setCurrentIndex(0)
                
        except Exception as e:
            logger.error(f"Error populating interface dropdown: {e}", exc_info=True)
            # Add just the Any option as fallback
            self.interface_combo.clear()
            self.interface_combo.addItem("Any (default)")
    
    def _populate_scan_types_dropdown(self):
        """Populate the scan types dropdown with available scan profiles"""
        if not hasattr(self, "scan_type_combo") or not self.scan_type_combo:
            logger.warning("Scan type combo box not available")
            return
            
        try:
            # Clear the combo box
            self.scan_type_combo.clear()
            
            # Define default scan types
            default_scan_types = {
                "quick": "Quick Scan (ping only)",
                "standard": "Standard Scan",
                "comprehensive": "Comprehensive Scan",
                "stealth": "Stealth Scan",
                "service": "Service Detection"
            }
            
            # Create default scan profiles if not already defined
            if not hasattr(self, "settings"):
                self.settings = {}
                
            if "scan_profiles" not in self.settings:
                self.settings["scan_profiles"] = {
                    "value": default_scan_types,
                    "default": default_scan_types
                }
                
            # Get scan profiles from settings
            scan_profiles = self.settings["scan_profiles"]["value"]
            
            # Add scan types to combo box
            for profile_id, profile in scan_profiles.items():
                if isinstance(profile, dict):
                    display_name = profile.get("name", profile_id)
                else:
                    display_name = profile
                    
                self.scan_type_combo.addItem(display_name)
            
            logger.debug(f"Populated scan types dropdown with {len(scan_profiles)} profiles")
            
            # Select default scan type
            default_type = "quick"
            default_index = self.scan_type_combo.findText("Quick Scan (ping only)")
            if default_index >= 0:
                self.scan_type_combo.setCurrentIndex(default_index)
            elif self.scan_type_combo.count() > 0:
                self.scan_type_combo.setCurrentIndex(0)
                
        except Exception as e:
            logger.error(f"Error populating scan types dropdown: {e}", exc_info=True)
            # Add basic types as fallback
            self.scan_type_combo.clear()
            self.scan_type_combo.addItem("Quick Scan")
            self.scan_type_combo.addItem("Standard Scan")
    
    def _update_interface_choices_and_refresh_ui(self):
        """Update interface choices and refresh UI"""
        logger.debug("Refreshing interface choices")
        # Re-populate the interface dropdown
        self._populate_interface_dropdown()
        
    def _update_network_range_from_interface(self, index):
        """Update the network range based on the selected interface"""
        if not hasattr(self, "network_range_edit") or not self.network_range_edit:
            return
            
        if not hasattr(self, "interface_combo") or not self.interface_combo:
            return
            
        # Get the selected interface
        selected_if_text = self.interface_combo.currentText()
        
        # If "Any" is selected, don't change the network range
        if selected_if_text == "Any (default)":
            return
        
        try:
            # Try to extract IP from the combo box text
            # Format is typically "eth0 (192.168.1.100)"
            import re
            ip_match = re.search(r'\(([0-9\.]+)\)', selected_if_text)
            
            if ip_match:
                ip_address = ip_match.group(1)
                
                # Get subnet for this IP
                subnet = get_subnet_for_ip(ip_address)
                
                if subnet:
                    # Update the network range field
                    self.network_range_edit.setText(subnet)
                    logger.debug(f"Updated network range to {subnet} based on selected interface")
                    
        except Exception as e:
            logger.error(f"Error updating network range from interface: {e}", exc_info=True)
            
    def on_device_added(self, device):
        """Handle device added signal"""
        logger.debug(f"Device added: {device.get_property('ip_address', 'Unknown')}")
        
        # Update any UI components that display device information
        if hasattr(self, "results_text") and self.results_text:
            ip = device.get_property('ip_address', 'Unknown')
            hostname = device.get_property('hostname', 'Unknown')
            if hostname and hostname != 'Unknown':
                self.log_message(f"Device added to inventory: {hostname} ({ip})")
            else:
                self.log_message(f"Device added to inventory: {ip}")
        
    def on_device_removed(self, device):
        """Handle device removed signal"""
        logger.debug(f"Device removed: {device.get_property('ip_address', 'Unknown')}")
        
        # Update any UI components that display device information
        if hasattr(self, "results_text") and self.results_text:
            ip = device.get_property('ip_address', 'Unknown')
            hostname = device.get_property('hostname', 'Unknown')
            if hostname and hostname != 'Unknown':
                self.log_message(f"Device removed from inventory: {hostname} ({ip})")
            else:
                self.log_message(f"Device removed from inventory: {ip}")
        
    def on_device_changed(self, device):
        """Handle device changed signal"""
        logger.debug(f"Device changed: {device.get_property('ip_address', 'Unknown')}")
        
        # If the device is in our discovered devices list, update it
        if hasattr(self, "discovered_devices"):
            ip = device.get_property('ip_address', 'Unknown')
            # Find the device in our list
            for i, dev_data in enumerate(self.discovered_devices):
                if dev_data.get('ip_address') == ip:
                    # Update device properties that may have changed
                    self.discovered_devices[i]['hostname'] = device.get_property('hostname', 'Unknown')
                    self.discovered_devices[i]['mac_address'] = device.get_property('mac_address', 'Unknown')
                    self.discovered_devices[i]['os'] = device.get_property('os', 'Unknown')
                    break
        
    def on_group_added(self, group):
        """Handle group added signal"""
        logger.debug(f"Group added: {group.name if hasattr(group, 'name') else group}")
        
    def on_group_removed(self, group):
        """Handle group removed signal"""
        logger.debug(f"Group removed: {group.name if hasattr(group, 'name') else group}")
        
    def on_device_selected(self, devices):
        """Handle device selection changed signal"""
        # Update UI based on selection
        device_count = len(devices) if devices else 0
        logger.debug(f"Device selection changed: {device_count} devices selected")
        
        # Enable/disable scan actions based on selection
        if hasattr(self, "scan_selected_action"):
            self.scan_selected_action.setEnabled(device_count > 0)
    
    # Event handlers
    def on_scan_action(self):
        """Handle scan action from menu/toolbar"""
        logger.debug("Scan action triggered")
        on_scan_action(self)
    
    def on_scan_selected_action(self):
        """Handle scan from selected device action"""
        logger.debug("Scan from selected device action triggered")
        on_scan_selected_action(self)
    
    def on_scan_type_manager_action(self):
        """Handle scan type manager action"""
        logger.debug("Scan type manager action triggered")
        on_scan_type_manager_action(self)
    
    def on_scan_button_clicked(self):
        """Handle scan button click"""
        logger.debug("Scan button clicked")
        on_scan_button_clicked(self)
    
    def on_stop_button_clicked(self):
        """Handle stop button click"""
        logger.debug("Stop button clicked")
        on_stop_button_clicked(self)
    
    def on_quick_ping_button_clicked(self):
        """Handle quick ping button click"""
        logger.debug("Quick ping button clicked")
        on_quick_ping_button_clicked(self)
    
    def on_advanced_scan_button_clicked(self):
        """Handle advanced scan button click"""
        logger.debug("Advanced scan button clicked")
        on_advanced_scan_button_clicked(self)
    
    # Context menu actions
    def _on_scan_network_action(self, selected_items):
        """Handle scan network context menu action"""
        logger.debug("Scan network context menu action triggered")
        _on_scan_network_action(self, selected_items)
    
    def _on_scan_subnet_action(self, selected_items):
        """Handle scan subnet context menu action"""
        logger.debug("Scan subnet context menu action triggered")
        _on_scan_subnet_action(self, selected_items)
    
    def _on_scan_from_device_action(self, selected_items):
        """Handle scan from device context menu action"""
        logger.debug("Scan from device context menu action triggered")
        _on_scan_from_device_action(self, selected_items)
    
    @safe_action_wrapper
    def _on_rescan_device_action(self, devices):
        """Handle rescan device action from context menu"""
        # Ensure devices is a list
        if not isinstance(devices, list):
            devices = [devices]
            
        # Count devices with IP addresses
        devices_with_ip = []
        for device in devices:
            ip_address = device.get_property("ip_address")
            if ip_address:
                devices_with_ip.append((device, ip_address))
                
        if not devices_with_ip:
            show_error_message(
                self.main_window,
                "Error",
                "None of the selected devices have IP addresses"
            )
            return
            
        # Get scan type from user
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox
        
        # Create scan type selection dialog
        scan_dialog = QDialog(self.main_window)
        scan_dialog.setWindowTitle("Select Scan Type")
        scan_dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(scan_dialog)
        
        # Add instructions
        if len(devices_with_ip) == 1:
            label = QLabel(f"Select scan type for device at {devices_with_ip[0][1]}:")
        else:
            label = QLabel(f"Select scan type for {len(devices_with_ip)} devices:")
        layout.addWidget(label)
        
        # Create scan type combo box
        scan_type_combo = QComboBox()
        
        # Get scan profiles from settings
        scan_profiles = self.settings["scan_profiles"]["value"]
        
        # Add scan types to combo box
        for profile_id, profile in scan_profiles.items():
            if isinstance(profile, dict):
                display_name = profile.get("name", profile_id)
            else:
                display_name = profile
                
            scan_type_combo.addItem(display_name)
        
        # If no scan types found, add defaults
        if scan_type_combo.count() == 0:
            default_types = ["Quick Scan (ping only)", "Standard Scan", "Comprehensive Scan"]
            for scan_type in default_types:
                scan_type_combo.addItem(scan_type)
        
        # Set standard scan as default if available
        standard_index = scan_type_combo.findText("Standard Scan")
        if standard_index >= 0:
            scan_type_combo.setCurrentIndex(standard_index)
        
        layout.addWidget(scan_type_combo)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(scan_dialog.accept)
        button_box.rejected.connect(scan_dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog
        if not scan_dialog.exec():
            return  # User canceled
        
        # Get selected scan type
        scan_type = scan_type_combo.currentText()
                
        # Show the main window and dock
        if self.main_window:
            self.main_window.activateWindow()
            self.main_window.raise_()
            
        # Find the dock widget and show it
        for dock in self.main_window.findChildren(QDockWidget):
            if dock.objectName() == "NetworkScannerDock":
                dock.show()
                dock.raise_()
                break
        
        # Scan the first device immediately
        if devices_with_ip:
            first_device, first_ip = devices_with_ip[0]
            self.log_message(f"Rescanning device at {first_ip} with {scan_type}")
            self.scan_network(first_ip, scan_type)
            
            # Queue the remaining devices to be scanned sequentially
            if len(devices_with_ip) > 1:
                remaining_devices = devices_with_ip[1:]
                self._queue_device_scans(remaining_devices, scan_type)
        
    def get_menu_actions(self):
        """Return actions to be placed in the menus"""
        return self.menu_actions
        
    def get_toolbar_actions(self):
        """Return actions to be placed on toolbars"""
        return self.toolbar_actions
        
    def get_context_menu_actions(self):
        """Return actions to be placed in context menus"""
        return self.context_menu_actions
        
    def get_device_panels(self):
        """Return panels to be displayed in the device details view"""
        return []
    
    def get_dock_widgets(self):
        """Get plugin dock widgets"""
        # Create a dock widget with the main plugin widget
        dock = create_dock_widget(self.main_widget)
        
        # Return a list of tuples: (widget_name, widget, area)
        return [("Network Scanner", dock, Qt.RightDockWidgetArea)]
        
    def scan_network(self, target, scan_type=None, **kwargs):
        """Start a network scan with the given parameters"""
        logger.info(f"Scanning network: {target}")
        
        # If scan_type is not provided, use the current selection from UI
        if scan_type is None and hasattr(self, "scan_type_combo") and self.scan_type_combo:
            scan_type = self.scan_type_combo.currentText()
        
        # If we're already scanning, warn the user and make sure we clean up properly
        if hasattr(self, "_scanner") and self._scanner and self._scanner.is_scanning():
            logger.warning("A scan is already running, stopping it before starting a new one")
            self._scanner.stop_scan()
            
            # Wait briefly to ensure the scan has stopped
            import time
            start_time = time.time()
            while self._scanner.is_scanning() and time.time() - start_time < 3.0:
                QCoreApplication.processEvents()
                time.sleep(0.1)
        
        # Reset the discovered devices list for this scan
        self.discovered_devices = []
        
        # Get scan settings from UI
        if hasattr(self, "os_detection_check") and self.os_detection_check:
            kwargs.setdefault("os_detection", self.os_detection_check.isChecked())
        if hasattr(self, "port_scan_check") and self.port_scan_check:
            kwargs.setdefault("port_scan", self.port_scan_check.isChecked())
        
        # Initialize thread and worker attributes if not already set
        if not hasattr(self, "_scanner_thread"):
            self._scanner_thread = None
        if not hasattr(self, "_scanner_worker"):
            self._scanner_worker = None
            
        # Forward the scan request to the scanner module
        return self._scanner.scan_network(target, scan_type, **kwargs)
        
    def stop_scan(self):
        """Stop the current scan"""
        if hasattr(self, "_scanner") and self._scanner:
            result = self._scanner.stop_scan()
            if result:
                self.log_message("Scan stopped by user")
            return result
        return False
        
    def is_scanning(self):
        """Check if a scan is currently running"""
        if hasattr(self, "_scanner") and self._scanner:
            return self._scanner.is_scanning()
        return False
        
    def log_message(self, message):
        """Add a message to the scan log"""
        if not hasattr(self, "_scan_log"):
            self._scan_log = []
            
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Add to internal log
        self._scan_log.append(log_entry)
        
        # Update UI if available
        if hasattr(self, "results_text") and self.results_text:
            current_text = self.results_text.toPlainText()
            if current_text:
                new_text = current_text + "\n" + log_entry
            else:
                new_text = log_entry
                
            self.results_text.setPlainText(new_text)
            # Scroll to bottom
            self.results_text.verticalScrollBar().setValue(
                self.results_text.verticalScrollBar().maximum()
            )
        
    def _setup_device_context_menu(self):
        """Set up context menu integration with device table"""
        # Defer context menu setup to a point when UI components are fully initialized
        # Use a QTimer to schedule this after the UI is fully loaded
        QTimer.singleShot(500, self._register_context_menu_actions)
        
    def _register_context_menu_actions(self):
        """Register context menu actions for device table"""
        try:
            # First try to get the device table directly from the main window
            if not hasattr(self.main_window, 'device_table'):
                logger.warning("Device table not found, cannot register context menu actions")
                return
                
            device_table = self.main_window.device_table
            
            # Check if table has register_context_menu_action method
            if not hasattr(device_table, 'register_context_menu_action'):
                logger.warning("Device table does not support context menu action registration")
                return
                
            # Register our scan actions with the device table
            device_table.register_context_menu_action(
                "Scan Network...", 
                self._on_scan_network_action, 
                priority=151
            )
            
            device_table.register_context_menu_action(
                "Scan Interface Subnet...", 
                self._on_scan_subnet_action, 
                priority=152
            )
            
            device_table.register_context_menu_action(
                "Scan Device's Network...", 
                self._on_scan_from_device_action, 
                priority=153
            )
            
            device_table.register_context_menu_action(
                "Rescan Selected Device(s)...", 
                self._on_rescan_device_action, 
                priority=154
            )
            
            logger.debug("Successfully registered context menu actions")
            
        except Exception as e:
            logger.error(f"Error registering context menu actions: {e}", exc_info=True)
            
    # Add missing callback methods for scanner signals
    def _on_scan_progress(self, current, total):
        """Handle scan progress updates from the scanner worker"""
        logger.debug(f"Scan progress: {current}/{total}")
        
        # Update progress in the plugin
        self.progress_value = int((current / total) * 100) if total > 0 else 0
        
        # Update UI components if available
        if hasattr(self, "progress_bar") and self.progress_bar:
            self.progress_bar.setValue(self.progress_value)
            
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.setText(f"Scanning: {current}/{total} hosts")
            
        # Log progress milestones (every 25%)
        if self.progress_value % 25 == 0 and self.progress_value > 0:
            self.log_message(f"Scan progress: {self.progress_value}% complete ({current}/{total} hosts)")
            
        # Emit the progress signal
        self.scan_progress_signal.emit(current, total)
        
    def _on_device_found(self, host_data):
        """Handle device discovered by the scanner"""
        # Skip status updates which aren't actual devices
        if "status_update" in host_data:
            return
            
        logger.debug(f"Device found: {host_data.get('ip_address', 'Unknown')}")
        
        # Skip if no IP address - this is the key issue we're fixing
        if not host_data.get('ip_address'):
            logger.debug("Skipping device without IP address")
            return
        
        # Add to discovered devices list
        self.discovered_devices.append(host_data)
        
        # Format and display device info
        ip = host_data.get('ip_address', 'Unknown')
        hostname = host_data.get('hostname', 'Unknown')
        mac = host_data.get('mac_address', 'Unknown')
        os = host_data.get('os', 'Unknown')
        
        # Log the device
        if hostname and hostname != 'Unknown':
            self.log_message(f"Found device: {hostname} ({ip})")
        else:
            self.log_message(f"Found device: {ip}")
            
        # Process and add the device to device_manager
        try:
            if hasattr(self, "device_manager") and self.device_manager:
                # Suspend notifications to prevent excessive UI updates
                suspend_notifications(self.device_manager)
                
                # Find matching devices
                matches = match_device(self.device_manager, host_data)
                
                device = None
                if matches:
                    # Handle matching devices (update existing)
                    device, was_merged = handle_duplicate_device(self.device_manager, host_data, matches)
                    if device:
                        # Update the device with new scan data
                        update_device_properties(device, host_data)
                        logger.debug(f"Updated existing device: {ip}")
                else:
                    # Create a new device
                    device = create_device_from_scan_data(self.device_manager, host_data)
                    logger.debug(f"Created new device: {ip}")
                
                # Add to scan results group for better organization
                if device:
                    self._add_device_to_scan_group(device)
                
                # Resume notifications
                resume_notifications(self.device_manager)
                
                # Emit device_found signal with the device object if available
                if device:
                    # Use safe_emit to prevent UI freezing
                    safe_emit_device_found(self.scan_device_found, device)
                else:
                    # Just emit the raw data if we couldn't create a device
                    self.scan_device_found.emit(host_data)
            else:
                # Just emit the raw data if device manager isn't available
                self.scan_device_found.emit(host_data)
        except Exception as e:
            logger.error(f"Error processing discovered device: {e}", exc_info=True)
            # Still emit the raw data so UI can be updated
            self.scan_device_found.emit(host_data)
        
    def _on_scan_complete(self, results):
        """Handle scan completion
        
        Args:
            results: Dictionary with scan results
        """
        logger.debug("Scan completed")
        
        # Store the results
        self._scan_results = results
        
        # Format the time string
        scan_time = results.get("scan_time", 0)
        if scan_time < 0.1:
            time_str = "<0.1"
        else:
            time_str = f"{scan_time:.1f}"
            
        # Log the results
        scan_type = results.get("scan_type", "unknown")
        network_range = results.get("network_range", "unknown")
        devices_found = results.get("devices_found", 0)
        total_hosts = results.get("total_hosts", 0)
        
        self.log_message(f"Scan complete: {scan_type} scan of {network_range}")
        self.log_message(f"Scanned {total_hosts} hosts, found {devices_found} devices in {time_str} seconds")
        
        # Clean up the previous scan before processing queue
        self._cleanup_previous_scan()
        
        # Reset scanning state
        self._is_scanning = False
        
        # Update UI
        if hasattr(self, "scan_button") and self.scan_button:
            self.scan_button.setEnabled(True)
        if hasattr(self, "stop_button") and self.stop_button:
            self.stop_button.setEnabled(False)
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.setText("Ready")
            
        # Process the next device in the queue if any
        if self._scan_queue:
            self._process_scan_queue(results)
            
        # Emit completion signal
        self.scan_completed.emit(results)
        
    def _process_scan_queue(self, results=None):
        """Process the next device in the scan queue
        
        Args:
            results: Results from the previous scan (ignored)
        """
        # Check if we have a queue
        if not self._scan_queue:
            logger.debug("No devices in scan queue")
            return
            
        # Check if a scan is currently running
        if self._is_scanning:
            # Wait for the current scan to finish - don't start a new one yet
            logger.debug("Scan still in progress, waiting to process next device in queue")
            return
            
        # Use a QTimer to add a short delay before starting the next scan
        # This helps ensure any thread cleanup from the previous scan is complete
        def start_next_scan():
            # Double check we're not scanning and have items in queue
            if self._is_scanning or not self._scan_queue:
                return
                
            # Get the next device from the queue
            device, ip_address = self._scan_queue.pop(0)
            
            # Get the scan type (default to standard if not specified)
            scan_type = self._queue_scan_type or "standard"
            
            # Make sure we're cleaned up from previous scan
            self._cleanup_previous_scan()
            
            # Reset scanning state
            self._is_scanning = False
            
            # Start the scan
            self.log_message(f"Starting queued scan of device at {ip_address} with {scan_type}")
            self.scan_network(ip_address, scan_type)
            
            # If the queue is empty, disconnect the signal
            if not self._scan_queue:
                try:
                    self.scan_completed.disconnect(self._process_scan_queue)
                    self._scan_queue_connected = False
                except Exception as e:
                    logger.debug(f"Error disconnecting scan_completed signal: {e}")
        
        # Use a timer to delay the next scan start by 1000ms to ensure cleanup
        QTimer.singleShot(1000, start_next_scan)
        
    def _cleanup_previous_scan(self):
        """Clean up any previous scan thread and worker"""
        logger.debug("Cleaning up previous scan")
        
        try:
            # Stop thread if running
            if hasattr(self, "_scanner_thread") and self._scanner_thread and self._scanner_thread.isRunning():
                # Try to stop the worker if it exists
                if hasattr(self, "_scanner_worker") and self._scanner_worker:
                    self._scanner_worker.stop()
                    
                # Process events to allow the worker to respond to the stop signal
                QCoreApplication.processEvents()
                
                # Quit and wait for the thread
                self._scanner_thread.quit()
                success = self._scanner_thread.wait(2000)  # 2 second timeout
                
                if not success:
                    logger.warning("Thread did not exit cleanly, forcing termination")
                    self._scanner_thread.terminate()
                    self._scanner_thread.wait(1000)
                    
                # Process events one more time to ensure any pending signals are handled
                QCoreApplication.processEvents()
                
            # Reset references
            self._scanner_thread = None
            self._scanner_worker = None
            self._is_scanning = False
            
        except Exception as e:
            logger.error(f"Error cleaning up previous scan: {e}")
            # Reset references even if cleanup failed
            self._scanner_thread = None
            self._scanner_worker = None
            self._is_scanning = False
        
    def _ensure_scan_results_group(self):
        """Ensure that the Scan Results group exists
        
        Returns:
            Group: The Scan Results group object
        """
        if not hasattr(self, "device_manager") or not self.device_manager:
            logger.warning("Device manager not available to create Scan Results group")
            return None
            
        try:
            # Check if the group already exists
            if hasattr(self.device_manager, 'get_group_by_name'):
                scan_group = self.device_manager.get_group_by_name("Scan Results")
                if scan_group:
                    return scan_group
                    
            # Create the group if it doesn't exist
            if hasattr(self.device_manager, 'create_group'):
                scan_group = self.device_manager.create_group("Scan Results", "Devices found by network scanner")
                logger.debug("Created 'Scan Results' group for organizing scanned devices")
                return scan_group
        except Exception as e:
            logger.error(f"Error ensuring Scan Results group: {e}", exc_info=True)
            
        return None
        
    def _add_device_to_scan_group(self, device):
        """Add a device to the appropriate scan results group
        
        Args:
            device: The device to add to the group
            
        Returns:
            bool: True if the device was added to a group
        """
        if not device or not hasattr(self, "device_manager") or not self.device_manager:
            return False
            
        try:
            # Get the Scan Results group
            scan_group = self._ensure_scan_results_group()
            if not scan_group:
                return False
                
            # Add the device to the group
            if hasattr(self.device_manager, 'add_device_to_group'):
                self.device_manager.add_device_to_group(device, scan_group)
                logger.debug(f"Added device {device.get_property('ip_address', 'Unknown')} to Scan Results group")
                return True
        except Exception as e:
            logger.error(f"Error adding device to scan group: {e}", exc_info=True)
            
        return False

    def _queue_device_scans(self, devices_with_ip, scan_type):
        """Queue up device scans to be run one at a time
        
        Args:
            devices_with_ip: List of (device, ip_address) tuples
            scan_type: Type of scan to run
        """
        if not devices_with_ip:
            return
            
        # Store the scan type
        self._queue_scan_type = scan_type
            
        # Add devices to the queue
        self._scan_queue.extend(devices_with_ip)
        
        # Connect to scan_completed signal if not already connected
        if not self._scan_queue_connected:
            self.scan_completed.connect(self._process_scan_queue)
            self._scan_queue_connected = True
            
    def _on_scan_error(self, error_message):
        """Handle scan errors"""
        logger.error(f"Scan error: {error_message}")
        
        # Update state
        self._is_scanning = False
        
        # Update UI
        if hasattr(self, "scan_button") and self.scan_button:
            self.scan_button.setEnabled(True)
        
        if hasattr(self, "stop_button") and self.stop_button:
            self.stop_button.setEnabled(False)
        
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.setText(f"Error: {error_message}")
        
        # Log error
        self.log_message(f"ERROR: {error_message}")
        
        # Emit the error signal
        self.scan_error.emit(error_message)
        
    def _thread_finished(self):
        """Handle thread finished signal"""
        logger.debug("Scanner thread finished")
        
        # The actual scan results are handled by the _on_scan_complete or _on_scan_error callbacks
        # This is just an extra safeguard to ensure thread resources are cleaned up
        if self._is_scanning:
            # If we get here and still think we're scanning, something went wrong
            logger.warning("Thread finished while still scanning - cleanup needed")
            self._is_scanning = False
            
            # Update UI
            if hasattr(self, "scan_button") and self.scan_button:
                self.scan_button.setEnabled(True)
            if hasattr(self, "stop_button") and self.stop_button:
                self.stop_button.setEnabled(False)
            if hasattr(self, "status_label") and self.status_label:
                self.status_label.setText("Scan interrupted unexpectedly")
                
            self.log_message("Scan interrupted unexpectedly")
        
        # Clean up thread and worker references to prevent memory leaks
        # Use a timer to delay this cleanup to ensure all signals are processed
        def complete_cleanup():
            if hasattr(self, "_scanner_worker") and self._scanner_worker:
                # Disconnect any signals that might still be connected
                try:
                    if hasattr(self._scanner_worker, "scan_complete"):
                        try:
                            self._scanner_worker.scan_complete.disconnect()
                        except:
                            pass
                    if hasattr(self._scanner_worker, "scan_error"):
                        try:
                            self._scanner_worker.scan_error.disconnect()
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"Error disconnecting signals: {e}")
                    
                # Clear the worker reference
                self._scanner_worker = None
                
            # Thread reference is cleared here
            self._scanner_thread = None
        
        # Use a short timer to ensure all signals are processed before cleanup
        QTimer.singleShot(100, complete_cleanup)

# Define a get_plugin function for the plugin system to use
def get_plugin():
    """Return the NetworkScannerPlugin class for registration"""
    return NetworkScannerPlugin 