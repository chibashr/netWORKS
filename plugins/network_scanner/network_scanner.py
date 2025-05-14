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

# Try to import nmap with error handling
try:
    import nmap
    HAS_NMAP = True
except ImportError as e:
    logger.error(f"Could not import python-nmap: {e}")
    HAS_NMAP = False

# Try to import netifaces for interface detection
try:
    import netifaces
    HAS_NETIFACES = True
except ImportError as e:
    logger.error(f"Could not import netifaces: {e}")
    HAS_NETIFACES = False

from PySide6.QtWidgets import (
    QLabel, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QDockWidget,
    QPushButton, QTabWidget, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QGridLayout, QFormLayout, QGroupBox, QCheckBox, QComboBox,
    QSplitter, QProgressBar, QMessageBox, QLineEdit, QTableWidget, 
    QTableWidgetItem, QDialog, QDialogButtonBox, QMenu, QFileDialog,
    QRadioButton, QInputDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer, QThread, QObject
from PySide6.QtGui import QIcon, QAction, QFont, QColor, QIntValidator

# Import the plugin interface
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.core.plugin_interface import PluginInterface


# Safe action wrapper from sample plugin
def safe_action_wrapper(func):
    """Decorator to safely handle actions without crashing the application"""
    import functools
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            # Log the action start
            action_name = func.__name__
            logger.debug(f"Starting action: {action_name}")
            
            # Execute the action
            result = func(self, *args, **kwargs)
            logger.debug(f"Successfully completed action: {action_name}")
            return result
        except Exception as e:
            # Log the error
            logger.error(f"Error in action {func.__name__}: {e}", exc_info=True)
            
            # Try to log to the UI if possible
            try:
                if hasattr(self, 'log_message'):
                    self.log_message(f"Error performing action: {e}")
                
                # Try to show a status message
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage(f"Error: {e}", 3000)
            except Exception as inner_e:
                # Absolute fallback to console logging
                logger.critical(f"Failed to handle error in UI: {inner_e}")
                
            # Return a safe value (None)
            return None
    return wrapper


class ScannerWorker(QObject):
    """Worker thread for network scanning"""
    
    # Signals
    progress = Signal(int, int)  # current, total
    device_found = Signal(dict)  # device data
    scan_complete = Signal(dict)  # scan results
    scan_error = Signal(str)  # error message
    
    def __init__(self, network_range, scan_type="quick", timeout=300, 
                 os_detection=True, port_scan=True, use_sudo=False,
                 custom_scan_args=""):
        """Initialize the scanner worker"""
        super().__init__()
        self.network_range = network_range
        self.scan_type = scan_type
        self.timeout = timeout
        self.os_detection = os_detection
        self.port_scan = port_scan
        self.use_sudo = use_sudo
        self.custom_scan_args = custom_scan_args
        self.is_running = False
        self.should_stop = False
        
        # Create scanner in the worker thread when run is called
        self.scanner = None
        
    def stop(self):
        """Stop the scan"""
        logger.debug("Request to stop scanner received")
        self.should_stop = True
        
    def run(self):
        """Run the network scan"""
        self.is_running = True
        self.should_stop = False
        
        try:
            # Create the scanner here rather than in __init__ to ensure it's in the worker thread
            self.scanner = nmap.PortScanner()
            
            scan_start_time = time.time()
            devices_found = 0
            
            # If custom arguments are provided, use them directly
            if self.custom_scan_args:
                arguments = self.custom_scan_args
            else:
                # Determine scan arguments based on scan type
                if self.scan_type == "quick":
                    # Just ping scan
                    arguments = "-sn"
                elif self.scan_type == "standard":
                    # Ping scan with some port scanning and OS detection if enabled
                    arguments = "-sn"
                    if self.port_scan:
                        arguments += " -F"  # Fast port scan
                    if self.os_detection:
                        arguments += " -O"
                else:  # comprehensive
                    # Full scan with port scanning and OS detection
                    arguments = "-sS"
                    if self.port_scan:
                        arguments += " -p 1-1000"
                    if self.os_detection:
                        arguments += " -O -A"
            
            # Add sudo if requested and not already in arguments
            if self.use_sudo and not arguments.startswith("sudo"):
                command_prefix = "sudo "
            else:
                command_prefix = ""
                
            logger.info(f"Starting network scan of {self.network_range} with arguments: {arguments}")
            logger.debug(f"Using command prefix: {command_prefix}")
            
            # Check if we should stop before even starting
            if self.should_stop:
                logger.info("Scan stopped before starting")
                self.is_running = False
                return
                
            # Start the scan within a try/except block
            try:
                # Use a reasonable timeout value
                timeout_val = max(30, min(self.timeout, 600))  # Between 30 and 600 seconds
                self.scanner.scan(hosts=self.network_range, arguments=arguments, 
                                 timeout=timeout_val, sudo=self.use_sudo)
            except Exception as scan_error:
                logger.error(f"Error during nmap scan: {scan_error}")
                self.scan_error.emit(f"Scan error: {scan_error}")
                self.is_running = False
                return
                
            # Check for stop request after scan
            if self.should_stop:
                logger.info("Scan stopped after initial scan")
                self.is_running = False
                return
                
            # Process results
            try:
                all_hosts = self.scanner.all_hosts()
                total_hosts = len(all_hosts)
                
                # Emit initial progress
                self.progress.emit(0, total_hosts)
                
                for i, host in enumerate(all_hosts):
                    # Check if we should stop
                    if self.should_stop:
                        logger.info("Scan stopped during host processing")
                        break
                    
                    # Emit progress
                    self.progress.emit(i+1, total_hosts)
                    
                    # Get host data
                    host_data = {}
                    host_data["ip_address"] = host
                    
                    try:
                        # Get hostname if available
                        try:
                            if "hostname" in self.scanner[host]:
                                host_data["hostname"] = self.scanner[host]["hostname"]
                        except (KeyError, TypeError) as e:
                            logger.debug(f"Error getting hostname for {host}: {e}")
                        
                        # Get MAC address if available
                        try:
                            if "addresses" in self.scanner[host] and "mac" in self.scanner[host]["addresses"]:
                                host_data["mac_address"] = self.scanner[host]["addresses"]["mac"]
                                
                                # Get vendor if available
                                if "vendor" in self.scanner[host] and self.scanner[host]["addresses"]["mac"] in self.scanner[host]["vendor"]:
                                    host_data["mac_vendor"] = self.scanner[host]["vendor"][self.scanner[host]["addresses"]["mac"]]
                        except (KeyError, TypeError) as e:
                            logger.debug(f"Error getting MAC for {host}: {e}")
                        
                        # Get status
                        try:
                            if "status" in self.scanner[host]:
                                host_data["status"] = self.scanner[host]["status"]["state"]
                        except (KeyError, TypeError) as e:
                            logger.debug(f"Error getting status for {host}: {e}")
                            host_data["status"] = "unknown"
                        
                        # Get OS information if available
                        try:
                            if "osmatch" in self.scanner[host] and len(self.scanner[host]["osmatch"]) > 0:
                                best_match = self.scanner[host]["osmatch"][0]
                                host_data["os_fingerprint"] = best_match["name"]
                        except (KeyError, TypeError, IndexError) as e:
                            logger.debug(f"Error getting OS info for {host}: {e}")
                        
                        # Get open ports if available
                        open_ports = []
                        try:
                            for proto in self.scanner[host].all_protocols():
                                ports = self.scanner[host][proto].keys()
                                for port in ports:
                                    if self.scanner[host][proto][port]["state"] == "open":
                                        service = self.scanner[host][proto][port].get("name", "unknown")
                                        open_ports.append(f"{port}/{proto} ({service})")
                        except (KeyError, TypeError, AttributeError) as e:
                            logger.debug(f"Error getting ports for {host}: {e}")
                            
                        if open_ports:
                            host_data["open_ports"] = open_ports
                        
                        # Add scan timestamp
                        host_data["scan_timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Add scan source
                        host_data["scan_source"] = "nmap"
                        
                        # Tag as "scanned"
                        host_data["tags"] = ["scanned"]
                        
                        # Generate an alias if none exists
                        if "hostname" in host_data and host_data["hostname"]:
                            host_data["alias"] = host_data["hostname"]
                        elif "mac_vendor" in host_data:
                            host_data["alias"] = f"{host_data['mac_vendor']} Device"
                        else:
                            host_data["alias"] = f"Device at {host}"
                        
                        # Emit the device found signal
                        self.device_found.emit(host_data)
                        devices_found += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing host {host}: {e}")
                
                # Calculate scan time
                scan_time = time.time() - scan_start_time
                
                # Emit scan complete signal with results
                scan_results = {
                    "network_range": self.network_range,
                    "scan_type": self.scan_type,
                    "total_hosts": total_hosts,
                    "devices_found": devices_found,
                    "scan_time": scan_time,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                self.scan_complete.emit(scan_results)
                
            except Exception as e:
                logger.error(f"Error processing scan results: {e}", exc_info=True)
                self.scan_error.emit(f"Error processing results: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unhandled scan error: {e}", exc_info=True)
            self.scan_error.emit(str(e))
            
        finally:
            # Clear the scanner reference
            self.scanner = None
            self.is_running = False
            logger.debug("Scanner worker finished")


class NetworkScannerPlugin(PluginInterface):
    """
    Network Scanner Plugin for NetWORKS
    
    This plugin provides network scanning capabilities for discovering
    and adding devices to the NetWORKS inventory.
    """
    
    # Custom signals
    scan_started = Signal(str)  # network_range
    scan_progress = Signal(int, int)  # current, total
    scan_device_found = Signal(object)  # device
    scan_completed = Signal(dict)  # results_dict
    scan_error = Signal(str)  # error_message
    
    def __init__(self):
        """Initialize the plugin"""
        super().__init__()
        self.name = "Network Scanner"
        self.version = "1.1.9"
        self.description = "Scan network segments for devices and add them to NetWORKS"
        self.author = "NetWORKS Team"
        
        # Internal state
        self._connected_signals = set()  # Track connected signals for safe disconnection
        self._scanner_thread = None
        self._scanner_worker = None
        self._is_scanning = False
        self._scan_results = {}
        self._scan_log = []
        
        # Plugin settings
        self.settings = {
            "scan_profiles": {
                "name": "Scan Profiles",
                "description": "Customizable scan profiles with predefined settings",
                "type": "json",
                "default": {
                    "quick": {
                        "name": "Quick Scan",
                        "description": "Fast ping scan to discover hosts (minimal network impact)",
                        "arguments": "-sn",
                        "os_detection": False,
                        "port_scan": False,
                        "timeout": 60
                    },
                    "standard": {
                        "name": "Standard Scan",
                        "description": "Balanced scan with basic port scanning and OS detection",
                        "arguments": "-sn -F -O",
                        "os_detection": True,
                        "port_scan": True,
                        "timeout": 180
                    },
                    "comprehensive": {
                        "name": "Comprehensive Scan",
                        "description": "In-depth scan with full port scanning and OS fingerprinting",
                        "arguments": "-sS -p 1-1000 -O -A",
                        "os_detection": True,
                        "port_scan": True,
                        "timeout": 300
                    },
                    "stealth": {
                        "name": "Stealth Scan",
                        "description": "Quiet TCP SYN scan with minimal footprint",
                        "arguments": "-sS -T2",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 240
                    },
                    "service": {
                        "name": "Service Detection",
                        "description": "Focused on detecting services on common ports",
                        "arguments": "-sV -p 21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5900,8080",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 240
                    }
                },
                "value": {
                    "quick": {
                        "name": "Quick Scan",
                        "description": "Fast ping scan to discover hosts (minimal network impact)",
                        "arguments": "-sn",
                        "os_detection": False,
                        "port_scan": False,
                        "timeout": 60
                    },
                    "standard": {
                        "name": "Standard Scan",
                        "description": "Balanced scan with basic port scanning and OS detection",
                        "arguments": "-sn -F -O",
                        "os_detection": True,
                        "port_scan": True,
                        "timeout": 180
                    },
                    "comprehensive": {
                        "name": "Comprehensive Scan",
                        "description": "In-depth scan with full port scanning and OS fingerprinting",
                        "arguments": "-sS -p 1-1000 -O -A",
                        "os_detection": True,
                        "port_scan": True,
                        "timeout": 300
                    },
                    "stealth": {
                        "name": "Stealth Scan",
                        "description": "Quiet TCP SYN scan with minimal footprint",
                        "arguments": "-sS -T2",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 240
                    },
                    "service": {
                        "name": "Service Detection",
                        "description": "Focused on detecting services on common ports",
                        "arguments": "-sV -p 21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5900,8080",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 240
                    }
                }
            },
            "scan_type": {
                "name": "Default Scan Type",
                "description": "The default scan type to use",
                "type": "choice",
                "default": "quick",
                "value": "quick",
                "choices": ["quick", "standard", "comprehensive", "stealth", "service"]
            },
            "preferred_interface": {
                "name": "Preferred Interface",
                "description": "The preferred network interface to use for scanning",
                "type": "choice",
                "default": "",
                "value": "",
                "choices": []  # Will be populated during initialization
            },
            "scan_timeout": {
                "name": "Default Scan Timeout",
                "description": "Default timeout in seconds for scan operations",
                "type": "int",
                "default": 300,
                "value": 300
            },
            "os_detection": {
                "name": "OS Detection",
                "description": "Enable OS detection by default",
                "type": "bool",
                "default": True,
                "value": True
            },
            "port_scan": {
                "name": "Port Scanning",
                "description": "Enable port scanning by default",
                "type": "bool",
                "default": True,
                "value": True
            },
            "use_sudo": {
                "name": "Use Elevated Permissions",
                "description": "Run scans with elevated permissions (improves accuracy but requires admin/sudo)",
                "type": "bool",
                "default": False,
                "value": False
            },
            "custom_scan_args": {
                "name": "Custom Scan Arguments",
                "description": "Advanced: Custom nmap arguments (use with caution)",
                "type": "string",
                "default": "",
                "value": ""
            },
            "auto_tag": {
                "name": "Auto Tag",
                "description": "Automatically tag discovered devices",
                "type": "bool",
                "default": True,
                "value": True
            }
        }
        
        # Create UI components
        self._create_actions()
        self._create_widgets()
        
    def initialize(self, app, plugin_info):
        """Initialize the plugin"""
        try:
            logger.info(f"Initializing {self.name} v{self.version}")
            
            # Store app reference and set up plugin interface
            self.app = app
            self.device_manager = app.device_manager
            self.main_window = app.main_window
            self.config = app.config
            self.plugin_info = plugin_info
            
            # Check if nmap module was successfully imported
            if not HAS_NMAP:
                error_msg = "The python-nmap module is not available. Please install it using 'pip install python-nmap'"
                logger.error(error_msg)
                if hasattr(self, "main_window") and self.main_window:
                    QMessageBox.critical(
                        self.main_window,
                        "Network Scanner Error",
                        error_msg
                    )
                raise ImportError(error_msg)
                
            # Check if nmap is available
            try:
                # Try to create a scanner to verify nmap is installed
                test_scanner = nmap.PortScanner()
                logger.debug("Nmap Python module initialized successfully")
                
                # Check if the nmap executable is available
                if not self._check_nmap_executable():
                    error_msg = "The nmap executable was not found in the system PATH. Please install nmap and make sure it's in your PATH."
                    logger.error(error_msg)
                    if hasattr(self, "main_window") and self.main_window:
                        QMessageBox.critical(
                            self.main_window,
                            "Network Scanner Error",
                            error_msg
                        )
                    raise RuntimeError(error_msg)
                    
                logger.info("Nmap is available and ready to use")
                
            except ImportError as e:
                error_msg = f"Error importing nmap module: {e}"
                logger.error(error_msg)
                # Show an error message
                if hasattr(self, "main_window") and self.main_window:
                    QMessageBox.critical(
                        self.main_window,
                        "Network Scanner Error",
                        f"Failed to import nmap module. Make sure python-nmap is installed.\n\nError: {e}"
                    )
                raise ImportError(error_msg)
            except Exception as e:
                error_msg = f"Error initializing nmap: {e}"
                logger.error(error_msg)
                # Show an error message
                if hasattr(self, "main_window") and self.main_window:
                    QMessageBox.critical(
                        self.main_window,
                        "Network Scanner Error",
                        f"Failed to initialize nmap. Make sure nmap is installed.\n\nError: {e}"
                    )
                raise RuntimeError(error_msg)
            
            # Check for netifaces
            if not HAS_NETIFACES:
                logger.warning("Netifaces module not available. Interface detection will be limited.")
                # Show a warning but don't fail initialization
                if hasattr(self, "main_window") and self.main_window:
                    QMessageBox.warning(
                        self.main_window,
                        "Network Scanner Warning",
                        "The netifaces module is not available. Interface detection will be limited.\n\n"
                        "For better network interface detection, install netifaces using:\n"
                        "pip install netifaces"
                    )
            
            # Update network interfaces
            self._update_interface_choices()
            
            # Initialize threading system
            self._initialize_scanner()
            
            # We're going to defer UI setup a bit to allow the main window to fully initialize
            QTimer.singleShot(300, self._setup_device_context_menu)
            
            # Connect to application signals
            QTimer.singleShot(500, self._connect_signals)
            
            logger.info(f"{self.name} initialization complete")
            return True
        except Exception as e:
            error_msg = f"Plugin initialization failed: {e}"
            logger.error(error_msg, exc_info=True)
            # Try to show a message box if we have a main window
            try:
                if hasattr(self, "main_window") and self.main_window:
                    QMessageBox.critical(
                        self.main_window,
                        f"{self.name} Initialization Failed",
                        f"The plugin could not be initialized.\n\nError: {str(e)}"
                    )
            except Exception:
                pass  # If we can't show a message box, just continue
                
            # Re-raise the exception to signal failure
            raise
        
    def _connect_to_signal(self, signal, slot, signal_name):
        """Connect to a signal and track the connection"""
        if signal and slot:
            try:
                signal.connect(slot)
                self._connected_signals.add((signal, slot, signal_name))
                logger.debug(f"Connected to signal: {signal_name}")
                return True
            except Exception as e:
                logger.error(f"Error connecting to signal {signal_name}: {e}")
                return False
        return False
    
    def _connect_signals(self):
        """Connect to application signals"""
        # Connect to device manager signals
        self._connect_to_signal(
            self.device_manager.device_added, 
            self.on_device_added,
            "device_added"
        )
        
        self._connect_to_signal(
            self.device_manager.device_removed,
            self.on_device_removed,
            "device_removed"
        )
        
        self._connect_to_signal(
            self.device_manager.device_changed,
            self.on_device_changed,
            "device_changed"
        )
        
    def cleanup(self):
        """Clean up the plugin"""
        logger.info(f"Cleaning up {self.name}")
        
        # Stop any running scan first
        self.stop_scan()
        
        # Safe disconnection function
        def safe_disconnect(signal, handler=None, signal_name=""):
            """Safely disconnect a signal handler"""
            if not signal:
                logger.debug(f"Signal object is None for {signal_name}, skipping disconnect")
                return False
                
            try:
                if handler:
                    # Try with handler
                    signal.disconnect(handler)
                else:
                    # Try to disconnect all connections
                    try:
                        signal.disconnect()
                    except TypeError:
                        # If disconnect() fails, the signal might require a handler
                        pass
                return True
            except Exception as e:
                # This is expected sometimes due to how Qt handles signals
                logger.debug(f"Non-critical: Failed to disconnect {signal_name}: {e}")
                return False
        
        # Disconnect all tracked signals
        for signal, slot, signal_name in list(self._connected_signals):
            safe_disconnect(signal, slot, signal_name)
            
        # Clear the tracked signals
        self._connected_signals.clear()
        
        # Clean up any running scan threads
        self._cleanup_previous_scan()
        
        # Null out references that might cause reference cycles
        self.app = None
        self.device_manager = None
        self.main_window = None
        self.config = None
                
        logger.info(f"{self.name} cleanup complete")
        
    def _create_actions(self):
        """Create plugin actions"""
        self.scan_action = QAction("Scan Network")
        self.scan_action.triggered.connect(self.on_scan_action)
        
        self.scan_selected_action = QAction("Scan from Selected Device")
        self.scan_selected_action.triggered.connect(self.on_scan_selected_action)
        
    def _create_widgets(self):
        """Create plugin widgets"""
        # Main widget
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        
        # Input and controls
        self.control_group = QGroupBox("Network Scan Controls")
        self.control_layout = QFormLayout(self.control_group)
        
        # Network range input
        self.network_range_layout = QHBoxLayout()
        self.network_range_edit = QLineEdit()
        self.network_range_edit.setPlaceholderText("e.g., 192.168.1.0/24 or 10.0.0.1-10.0.0.254")
        self.network_range_layout.addWidget(self.network_range_edit)
        
        # Scan button
        self.scan_button = QPushButton("Start Scan")
        self.scan_button.clicked.connect(self.on_scan_button_clicked)
        self.network_range_layout.addWidget(self.scan_button)
        
        # Stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.on_stop_button_clicked)
        self.stop_button.setEnabled(False)
        self.network_range_layout.addWidget(self.stop_button)
        
        self.control_layout.addRow("Network Range:", self.network_range_layout)
        
        # Scan type
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.addItems(["quick", "standard", "comprehensive", "stealth", "service"])
        self.scan_type_combo.setCurrentText(self.settings["scan_type"]["value"])
        self.control_layout.addRow("Scan Type:", self.scan_type_combo)
        
        # OS Detection
        self.os_detection_check = QCheckBox()
        self.os_detection_check.setChecked(self.settings["os_detection"]["value"])
        self.control_layout.addRow("OS Detection:", self.os_detection_check)
        
        # Port Scanning
        self.port_scan_check = QCheckBox()
        self.port_scan_check.setChecked(self.settings["port_scan"]["value"])
        self.control_layout.addRow("Port Scanning:", self.port_scan_check)
        
        # Progress section
        self.progress_layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.progress_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_layout.addWidget(self.progress_bar)
        
        # Results section
        self.results_group = QGroupBox("Scan Results")
        self.results_layout = QVBoxLayout(self.results_group)
        
        # Results list
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_layout.addWidget(self.results_text)
        
        # Add all sections to main layout
        self.main_layout.addWidget(self.control_group)
        self.main_layout.addLayout(self.progress_layout)
        self.main_layout.addWidget(self.results_group)
        
    def _initialize_scanner(self):
        """Initialize the scanner thread and worker"""
        # We don't create the worker or thread here
        # These will be created on-demand when a scan is started
        self._scanner_thread = None
        self._scanner_worker = None
        
        # Just note that we're ready for scanning
        logger.debug("Scanner thread system initialized")
        
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
            
    def log_message(self, message):
        """Add a message to the scan log"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self._scan_log.append(log_entry)
        
        if hasattr(self, "results_text"):
            self.results_text.append(log_entry)
            
        logger.info(message)
        
    def get_dock_widgets(self):
        """Get plugin dock widgets"""
        # Avoid duplicate header by using a different name for the dock widget
        dock = QDockWidget("Scanner")
        dock.setWidget(self.main_widget)
        dock.setObjectName("NetworkScannerDock")
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Return a list of tuples: (widget_name, widget, area)
        return [("Network Scanner", dock, Qt.RightDockWidgetArea)]
        
    def get_menu_actions(self):
        """Get plugin menu actions"""
        return {"Network": [self.scan_action, self.scan_selected_action]}

    def scan_network(self, network_range, scan_type="quick"):
        """
        Start a network scan of the specified range
        
        Args:
            network_range: The network range to scan (e.g., 192.168.1.0/24)
            scan_type: The type of scan to perform (quick, standard, comprehensive, etc.)
            
        Returns:
            bool: True if scan started successfully, False otherwise
        """
        # Check if already scanning
        if self._is_scanning:
            logger.warning("Scan already in progress")
            return False
            
        # Clean up any previous scan
        self._cleanup_previous_scan()
        
        # Update scan type in settings
        self.settings["scan_type"]["value"] = scan_type
        
        # Get scan profile settings if available
        scan_profiles = self.settings["scan_profiles"]["value"]
        custom_args = self.settings["custom_scan_args"]["value"]
        use_sudo = self.settings["use_sudo"]["value"]
        os_detection = self.settings["os_detection"]["value"]
        port_scan = self.settings["port_scan"]["value"]
        timeout = self.settings["scan_timeout"]["value"]
        
        # If the scan type has a profile, use those settings unless overridden
        if scan_type in scan_profiles:
            profile = scan_profiles[scan_type]
            
            # Only use profile settings if not explicitly set by the user
            if not custom_args:
                custom_args = profile.get("arguments", "")
            
            # Use profile values for other settings if not explicitly overridden
            if os_detection == self.settings["os_detection"]["default"]:
                os_detection = profile.get("os_detection", os_detection)
                
            if port_scan == self.settings["port_scan"]["default"]:
                port_scan = profile.get("port_scan", port_scan)
                
            if timeout == self.settings["scan_timeout"]["default"]:
                timeout = profile.get("timeout", timeout)
        
        # Create a new worker thread
        try:
            # Log start of scan
            logger.info(f"Starting {scan_type} scan of {network_range}")
            
            # Create a new thread
            self._scanner_thread = QThread()
            
            # Create a worker and move it to the thread
            self._scanner_worker = ScannerWorker(
                network_range=network_range,
                scan_type=scan_type,
                timeout=timeout,
                os_detection=os_detection,
                port_scan=port_scan,
                use_sudo=use_sudo,
                custom_scan_args=custom_args
            )
            self._scanner_worker.moveToThread(self._scanner_thread)
            
            # Connect signals
            self._scanner_thread.started.connect(self._scanner_worker.run)
            self._scanner_worker.progress.connect(self._on_scan_progress)
            self._scanner_worker.device_found.connect(self._on_device_found)
            self._scanner_worker.scan_complete.connect(self._on_scan_complete)
            self._scanner_worker.scan_error.connect(self._on_scan_error)
            self._scanner_thread.finished.connect(self._thread_finished)
            
            # Set scanning flag
            self._is_scanning = True
            
            # Start the thread
            self._scanner_thread.start()
            
            # Update UI
            self.scan_started.emit(network_range)
            
            # Clear the scan log and reset progress
            self._scan_log = []
            self.log_message(f"Starting {scan_type} scan of {network_range}")
            self._scan_results = {}
            
            # Update scanner widget status if available
            if hasattr(self, "scan_button") and self.scan_button:
                self.scan_button.setEnabled(False)
            if hasattr(self, "stop_button") and self.stop_button:
                self.stop_button.setEnabled(True)
            if hasattr(self, "progress_bar") and self.progress_bar:
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(True)
                
            return True
        except Exception as e:
            logger.error(f"Error starting scan: {e}", exc_info=True)
            self._is_scanning = False
            self._cleanup_previous_scan()
            self.scan_error.emit(f"Error starting scan: {e}")
            return False
        
    def _cleanup_previous_scan(self):
        """Clean up any previous scan thread and worker"""
        # Stop thread if running
        if self._scanner_thread and self._scanner_thread.isRunning():
            logger.debug("Cleaning up previous thread")
            try:
                # Try to stop the worker if it exists
                if self._scanner_worker:
                    self._scanner_worker.stop()
                
                # Quit and wait for the thread
                self._scanner_thread.quit()
                success = self._scanner_thread.wait(1000)  # 1 second timeout
                
                if not success:
                    logger.warning("Thread did not exit cleanly, forcing termination")
                    self._scanner_thread.terminate()
                    self._scanner_thread.wait(1000)
            except Exception as e:
                logger.error(f"Error cleaning up previous scan: {e}")
                
        # Reset references
        self._scanner_thread = None
        self._scanner_worker = None
        self._is_scanning = False
        
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
            if hasattr(self, "scan_button"):
                self.scan_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                self.status_label.setText("Scan interrupted unexpectedly")
                
            self.log_message("Scan interrupted unexpectedly")
        
    def is_scanning(self):
        """
        Check if a scan is currently in progress
        
        Returns:
            bool: True if a scan is in progress, False otherwise
        """
        return self._is_scanning
        
    def stop_scan(self):
        """
        Stop any currently running scan
        
        Returns:
            bool: True if scan was stopped, False if no scan was running
        """
        if not self.is_scanning():
            logger.debug("No scan running to stop")
            return False
            
        logger.info("Stopping scan...")
        
        # Update UI first to give immediate feedback
        if hasattr(self, "scan_button"):
            self.scan_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.status_label.setText("Stopping scan...")
            
        # Signal the worker to stop
        try:
            if self._scanner_worker:
                self._scanner_worker.stop()
                logger.debug("Worker stop signal sent")
        except Exception as e:
            logger.error(f"Error signaling worker to stop: {e}")
        
        # Wait a bit before trying to terminate the thread
        try:
            if self._scanner_thread and self._scanner_thread.isRunning():
                # Try to quit gracefully first
                self._scanner_thread.quit()
                logger.debug("Thread quit signal sent")
                
                # Wait for the thread to finish with timeout
                if not self._scanner_thread.wait(3000):  # 3 second timeout
                    logger.warning("Thread did not exit within timeout, forcing termination")
                    try:
                        self._scanner_thread.terminate()
                        logger.debug("Thread terminate signal sent")
                        # Short wait for termination to take effect
                        self._scanner_thread.wait(1000)
                    except Exception as term_error:
                        logger.error(f"Error terminating thread: {term_error}")
        except Exception as e:
            logger.error(f"Error stopping thread: {e}")
                
        # Mark as not scanning
        self._is_scanning = False
        
        # Update UI
        if hasattr(self, "scan_button"):
            self.scan_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.status_label.setText("Scan stopped by user")
            
        self.log_message("Scan stopped by user")
        
        return True
        
    def get_scan_results(self):
        """
        Get the results of the most recent scan
        
        Returns:
            dict: Dictionary containing scan results with statistics
        """
        return self._scan_results
        
    def _on_scan_progress(self, current, total):
        """Handle scan progress updates"""
        # Calculate percentage
        if total > 0:
            percentage = int((current / total) * 100)
        else:
            percentage = 0
            
        # Update progress bar
        if hasattr(self, "progress_bar"):
            self.progress_bar.setValue(percentage)
            
        # Update status label
        if hasattr(self, "status_label"):
            self.status_label.setText(f"Scanning: {current}/{total} hosts processed ({percentage}%)")
            
        # Emit the scan progress signal
        self.scan_progress.emit(current, total)
        
    def _on_device_found(self, host_data):
        """
        Handle a device found during scanning
        
        This method is called when the scanner worker finds a device.
        It creates a new device or updates an existing one.
        """
        try:
            # Check if this device already exists based on IP or MAC
            existing_device = None
            if "ip_address" in host_data and host_data["ip_address"]:
                # Try to find by IP address
                for device in self.device_manager.get_devices():
                    if device.get_property("ip_address") == host_data["ip_address"]:
                        existing_device = device
                        break
                        
            if not existing_device and "mac_address" in host_data and host_data["mac_address"]:
                # Try to find by MAC address
                for device in self.device_manager.get_devices():
                    if device.get_property("mac_address") == host_data["mac_address"]:
                        existing_device = device
                        break
            
            if existing_device:
                # Update existing device
                for key, value in host_data.items():
                    if key == "tags":
                        # Merge tags rather than replace
                        current_tags = existing_device.get_property("tags", [])
                        for tag in value:
                            if tag not in current_tags:
                                current_tags.append(tag)
                        existing_device.set_property("tags", current_tags)
                    else:
                        existing_device.set_property(key, value)
                
                # Log the update
                self.log_message(f"Updated existing device: {existing_device.get_property('alias')}")
                
                # Emit the device found signal
                self.scan_device_found.emit(existing_device)
                
                return existing_device
            else:
                # Create a new device
                new_device = self.device_manager.create_device(
                    device_type="scanned",
                    **host_data
                )
                
                # Add it to the device manager
                self.device_manager.add_device(new_device)
                
                # Log the addition
                self.log_message(f"Added new device: {new_device.get_property('alias')}")
                
                # Emit the device found signal
                self.scan_device_found.emit(new_device)
                
                return new_device
                
        except Exception as e:
            logger.error(f"Error adding/updating device: {e}", exc_info=True)
            self.log_message(f"Error adding/updating device: {e}")
            return None
            
    def _on_scan_complete(self, results):
        """Handle scan completion"""
        # Store the results
        self._scan_results = results
        
        # Update UI
        if hasattr(self, "scan_button"):
            self.scan_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
        # Update status
        if hasattr(self, "status_label"):
            self.status_label.setText("Scan complete")
            
        # Set progress to 100%
        if hasattr(self, "progress_bar"):
            self.progress_bar.setValue(100)
            
        # Log results
        scan_time = round(results["scan_time"], 1)
        self.log_message(f"Scan complete: Found {results['devices_found']} devices in {scan_time} seconds")
        
        # Clean up
        self._is_scanning = False
        
        # Stop the thread
        if self._scanner_thread and self._scanner_thread.isRunning():
            self._scanner_thread.quit()
            self._scanner_thread.wait()
            
        # Emit the scan completed signal
        self.scan_completed.emit(results)
        
    def _on_scan_error(self, error_message):
        """Handle scan errors"""
        # Update UI
        if hasattr(self, "scan_button"):
            self.scan_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
        # Update status
        if hasattr(self, "status_label"):
            self.status_label.setText(f"Error: {error_message}")
            
        # Log the error
        self.log_message(f"Scan error: {error_message}")
        
        # Clean up
        self._is_scanning = False
        
        # Stop the thread
        if self._scanner_thread and self._scanner_thread.isRunning():
            self._scanner_thread.quit()
            self._scanner_thread.wait()
            
        # Emit the scan error signal
        self.scan_error.emit(error_message) 

    @safe_action_wrapper
    def on_scan_action(self):
        """Handle main scan action"""
        # Update network interfaces before showing dialog
        self._update_interface_choices()
        
        # Show scan dialog
        network_range = self._show_scan_dialog()
        
        if network_range:
            # Get scan type from settings
            scan_type = self.settings["scan_type"]["value"]
            
            # Start the scan
            self.scan_network(network_range, scan_type)
            
    @safe_action_wrapper
    def on_scan_selected_action(self):
        """Handle scanning selected devices"""
        # Find the device table
        from src.ui.device_table import DeviceTableView
        device_table = self.main_window.findChild(DeviceTableView)
        
        if not device_table:
            QMessageBox.warning(
                self.main_window,
                "Device Table Not Found",
                "Could not find the device table view."
            )
            return
            
        # Get selected devices
        selected_devices = device_table.get_selected_devices()
        
        if not selected_devices:
            QMessageBox.warning(
                self.main_window,
                "No Devices Selected",
                "Please select one or more devices to scan."
            )
            return
            
        # Call the rescan device action handler
        self._on_rescan_device_action(selected_devices)
        
    @safe_action_wrapper
    def on_scan_button_clicked(self):
        """Handle scan button click"""
        # Check if scan already in progress
        if self._is_scanning:
            QMessageBox.information(
                self.main_window,
                "Scan in Progress",
                "A scan is already in progress. Please wait for it to complete or click Stop to cancel it."
            )
            return
            
        # Update network interfaces before showing dialog
        self._update_interface_choices()
        
        # Show scan dialog
        network_range = self._show_scan_dialog()
        
        if network_range:
            # Get scan type from settings
            scan_type = self.settings["scan_type"]["value"]
            
            # Start the scan
            self.scan_network(network_range, scan_type)
        
    @safe_action_wrapper
    def on_stop_button_clicked(self):
        """Handle stop button click"""
        self.stop_scan()
        
    def _show_scan_dialog(self, selected_device=None):
        """Show a dialog to get scan parameters"""
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Network Scan")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # Create tabs for basic and advanced settings
        tab_widget = QTabWidget()
        basic_tab = QWidget()
        advanced_tab = QWidget()
        profiles_tab = QWidget()
        
        tab_widget.addTab(basic_tab, "Basic")
        tab_widget.addTab(advanced_tab, "Advanced")
        tab_widget.addTab(profiles_tab, "Scan Profiles")
        
        # ==== Basic Tab ====
        basic_layout = QVBoxLayout(basic_tab)
        
        # Network interface selection
        interface_group = QGroupBox("Network Interface")
        interface_layout = QVBoxLayout(interface_group)
        
        interface_combo = QComboBox()
        # Add interfaces from settings
        interface_combo.addItems(self.settings["preferred_interface"]["choices"])
        current_interface = self.settings["preferred_interface"]["value"]
        if current_interface and current_interface in self.settings["preferred_interface"]["choices"]:
            interface_combo.setCurrentText(current_interface)
            
        interface_layout.addWidget(interface_combo)
        basic_layout.addWidget(interface_group)
        
        # Scan target options
        target_group = QGroupBox("Scan Target")
        target_layout = QVBoxLayout(target_group)
        
        # Option to scan subnet of selected interface
        scan_subnet_radio = QRadioButton("Scan Interface Subnet")
        
        # Option for custom network range
        custom_range_radio = QRadioButton("Custom Network Range")
        custom_range_layout = QHBoxLayout()
        network_range_edit = QLineEdit()
        network_range_edit.setPlaceholderText("e.g., 192.168.1.0/24 or 10.0.0.1-10.0.0.254")
        custom_range_layout.addWidget(network_range_edit)
        
        # If a selected device was provided, add an option to rescan it
        rescan_device_radio = None
        if selected_device:
            rescan_device_radio = QRadioButton(f"Rescan Selected Device: {selected_device.get_property('alias', 'Device')}")
            target_layout.addWidget(rescan_device_radio)
            rescan_device_radio.setChecked(True)
        else:
            scan_subnet_radio.setChecked(True)
            
        target_layout.addWidget(scan_subnet_radio)
        target_layout.addWidget(custom_range_radio)
        target_layout.addLayout(custom_range_layout)
        
        # Connect radio buttons to enable/disable related widgets
        def update_ui_state():
            network_range_edit.setEnabled(custom_range_radio.isChecked())
            
        scan_subnet_radio.toggled.connect(update_ui_state)
        custom_range_radio.toggled.connect(update_ui_state)
        if rescan_device_radio:
            rescan_device_radio.toggled.connect(update_ui_state)
            
        # Initial UI state
        update_ui_state()
        
        target_group.setLayout(target_layout)
        basic_layout.addWidget(target_group)
        
        # Scan profile
        profile_group = QGroupBox("Scan Profile")
        profile_layout = QVBoxLayout(profile_group)
        
        # Scan type
        scan_type_combo = QComboBox()
        scan_type_combo.addItems(self.settings["scan_type"]["choices"])
        scan_type_combo.setCurrentText(self.settings["scan_type"]["value"])
        
        # Create a label to show scan description
        scan_description_label = QLabel()
        scan_description_label.setWordWrap(True)
        
        # Function to update description when scan type changes
        def update_scan_description(index):
            scan_type = scan_type_combo.currentText()
            profiles = self.settings["scan_profiles"]["value"]
            if scan_type in profiles:
                description = profiles[scan_type].get("description", "")
                scan_description_label.setText(description)
                # Update settings as well
                self.os_detection_check.setChecked(profiles[scan_type].get("os_detection", False))
                self.port_scan_check.setChecked(profiles[scan_type].get("port_scan", False))
                
        # Connect the signal
        scan_type_combo.currentIndexChanged.connect(update_scan_description)
        
        # Call initially to set the description
        update_scan_description(0)
        
        profile_layout.addWidget(QLabel("Scan Type:"))
        profile_layout.addWidget(scan_type_combo)
        profile_layout.addWidget(scan_description_label)
        
        basic_layout.addWidget(profile_group)
        
        # ==== Advanced Tab ====
        advanced_layout = QVBoxLayout(advanced_tab)
        
        # Scan options
        options_group = QGroupBox("Scan Options")
        options_layout = QFormLayout(options_group)
        
        # OS Detection
        os_detection_check = QCheckBox()
        os_detection_check.setChecked(self.settings["os_detection"]["value"])
        options_layout.addRow("OS Detection:", os_detection_check)
        
        # Port Scanning
        port_scan_check = QCheckBox()
        port_scan_check.setChecked(self.settings["port_scan"]["value"])
        options_layout.addRow("Port Scanning:", port_scan_check)
        
        # Elevated permissions
        elevated_check = QCheckBox()
        elevated_check.setChecked(self.settings["use_sudo"]["value"])
        options_layout.addRow("Use Elevated Permissions:", elevated_check)
        
        # Timeout
        timeout_edit = QLineEdit(str(self.settings["scan_timeout"]["value"]))
        timeout_edit.setValidator(QIntValidator(10, 1000))
        options_layout.addRow("Timeout (seconds):", timeout_edit)
        
        # Custom arguments
        custom_args_edit = QLineEdit(self.settings["custom_scan_args"]["value"])
        custom_args_edit.setPlaceholderText("e.g., -p 80,443 -sV")
        options_layout.addRow("Custom nmap arguments:", custom_args_edit)
        
        advanced_layout.addWidget(options_group)
        advanced_layout.addStretch()
        
        # ==== Profiles Tab ====
        profiles_layout = QVBoxLayout(profiles_tab)
        
        # Display the current scan profiles
        profiles_label = QLabel("Available Scan Profiles:")
        profiles_layout.addWidget(profiles_label)
        
        # Create a text display for the profiles
        profiles_text = QTextEdit()
        profiles_text.setReadOnly(True)
        
        # Format the profiles information
        profile_info = ""
        for scan_id, profile in self.settings["scan_profiles"]["value"].items():
            profile_info += f"<b>{profile.get('name', scan_id)}</b><br>"
            profile_info += f"Description: {profile.get('description', 'No description')}<br>"
            profile_info += f"Arguments: <code>{profile.get('arguments', '')}</code><br>"
            profile_info += f"OS Detection: {'Yes' if profile.get('os_detection', False) else 'No'}<br>"
            profile_info += f"Port Scan: {'Yes' if profile.get('port_scan', False) else 'No'}<br>"
            profile_info += f"Timeout: {profile.get('timeout', 300)} seconds<br><br>"
            
        profiles_text.setHtml(profile_info)
        profiles_layout.addWidget(profiles_text)
        
        # Help text
        help_label = QLabel("Note: Scan profiles can be edited in the plugin settings.")
        help_label.setWordWrap(True)
        profiles_layout.addWidget(help_label)
        
        # Try to get a default value for network range based on the local network
        try:
            if current_interface and current_interface != "Any (default)":
                selected_if = current_interface.split(":")[0].strip()
                subnet = self._get_interface_subnet(selected_if)
                if subnet:
                    network_range_edit.setText(subnet)
                    logger.debug(f"Using subnet {subnet} from interface {selected_if}")
            
            # If no subnet from interface, try to get one from local IP
            if not network_range_edit.text():
                import socket
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
                network = ipaddress.IPv4Network(f"{ip_address}/24", strict=False)
                network_range_edit.setText(str(network))
                logger.debug(f"Using subnet {network} from local IP {ip_address}")
        except Exception as e:
            logger.debug(f"Error determining default network range: {e}")
            # If we can't determine the local network, leave it blank
            
        # Connect interface combo to update network range when changed
        def update_network_range(index):
            if scan_subnet_radio.isChecked():
                selected_if_text = interface_combo.currentText()
                if selected_if_text and selected_if_text != "Any (default)":
                    selected_if = selected_if_text.split(":")[0].strip()
                    subnet = self._get_interface_subnet(selected_if)
                    if subnet:
                        network_range_edit.setText(subnet)
                
        interface_combo.currentIndexChanged.connect(update_network_range)
            
        # Add tabs to layout
        layout.addWidget(tab_widget)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.Accepted:
            # Get the selected scan type and its profile settings
            selected_scan_type = scan_type_combo.currentText()
            profiles = self.settings["scan_profiles"]["value"]
            
            # Update settings from dialog
            self.settings["scan_type"]["value"] = selected_scan_type
            
            # Use values from the profile as a base, but let user override with advanced settings
            if selected_scan_type in profiles:
                profile = profiles[selected_scan_type]
                self.settings["os_detection"]["value"] = os_detection_check.isChecked()
                self.settings["port_scan"]["value"] = port_scan_check.isChecked()
                self.settings["use_sudo"]["value"] = elevated_check.isChecked()
                self.settings["scan_timeout"]["value"] = int(timeout_edit.text())
                
                # Only use custom args if provided, otherwise use from profile
                custom_args = custom_args_edit.text().strip()
                if custom_args:
                    self.settings["custom_scan_args"]["value"] = custom_args
                else:
                    self.settings["custom_scan_args"]["value"] = profile.get("arguments", "")
            else:
                # If scan type is not in profiles (shouldn't happen), use form values
                self.settings["os_detection"]["value"] = os_detection_check.isChecked()
                self.settings["port_scan"]["value"] = port_scan_check.isChecked()
                self.settings["use_sudo"]["value"] = elevated_check.isChecked()
                self.settings["scan_timeout"]["value"] = int(timeout_edit.text())
                self.settings["custom_scan_args"]["value"] = custom_args_edit.text()
                
            self.settings["preferred_interface"]["value"] = interface_combo.currentText()
            
            # Determine the network range to scan
            if selected_device and rescan_device_radio and rescan_device_radio.isChecked():
                # Return the IP of the selected device
                return selected_device.get_property("ip_address", "")
            elif scan_subnet_radio.isChecked():
                # Get subnet from selected interface
                selected_if_text = interface_combo.currentText()
                if selected_if_text and selected_if_text != "Any (default)":
                    selected_if = selected_if_text.split(":")[0].strip()
                    subnet = self._get_interface_subnet(selected_if)
                    if subnet:
                        return subnet
                # Fallback to the network range edit
                return network_range_edit.text().strip()
            else:
                # Return the custom network range
                return network_range_edit.text().strip()
        
        return None

    @safe_action_wrapper
    def _on_scan_subnet_action(self, device_or_devices=None):
        """Handle Scan Interface Subnet action from context menu"""
        # Update the interface list
        self._update_interface_choices()
        
        selected_if_text = self.settings["preferred_interface"]["value"]
        
        # If no interface is selected or it's the "Any" option, show the dialog
        if not selected_if_text or selected_if_text == "Any (default)":
            network_range = self._show_scan_dialog()
        else:
            # Get the interface name
            selected_if = selected_if_text.split(":")[0].strip()
            subnet = self._get_interface_subnet(selected_if)
            
            if not subnet:
                # If we couldn't determine the subnet, show the dialog
                network_range = self._show_scan_dialog()
            else:
                # Show confirmation dialog
                result = QMessageBox.question(
                    self.main_window,
                    "Confirm Subnet Scan",
                    f"Do you want to scan the subnet {subnet} from interface {selected_if}?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if result == QMessageBox.Yes:
                    network_range = subnet
                else:
                    network_range = None
        
        if network_range:
            # Get scan type from settings
            scan_type = self.settings["scan_type"]["value"]
            
            # Start the scan
            self.scan_network(network_range, scan_type)
            
    @safe_action_wrapper
    def _on_rescan_device_action(self, device_or_devices):
        """Handle Rescan Selected Device action from context menu"""
        # Get the device(s)
        devices = []
        if isinstance(device_or_devices, list):
            devices = device_or_devices
        elif device_or_devices is not None:
            devices = [device_or_devices]
        else:
            # If no devices were passed, try to get selected devices from device manager
            devices = self.device_manager.get_selected_devices()
            
        # Check if we have any devices
        if not devices:
            QMessageBox.warning(
                self.main_window,
                "No Devices Selected",
                "Please select one or more devices to rescan."
            )
            return
            
        # If only one device, show scan dialog for that device
        if len(devices) == 1:
            network_range = self._show_scan_dialog(devices[0])
            
            if network_range:
                # Get scan type from settings
                scan_type = self.settings["scan_type"]["value"]
                
                # Start the scan
                self.scan_network(network_range, scan_type)
        else:
            # For multiple devices, ask for confirmation
            device_ips = []
            for device in devices:
                ip = device.get_property("ip_address", "")
                if ip:
                    device_ips.append(ip)
                    
            if not device_ips:
                QMessageBox.warning(
                    self.main_window,
                    "No Valid Devices",
                    "None of the selected devices have valid IP addresses."
                )
                return
                
            # Show confirmation dialog
            result = QMessageBox.question(
                self.main_window,
                "Confirm Device Rescan",
                f"Do you want to rescan {len(device_ips)} selected devices?\n\n"
                f"This will perform individual scans for each device.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Get scan type from settings
                scan_type = self.settings["scan_type"]["value"]
                
                # Scan each device
                for ip in device_ips:
                    self.scan_network(ip, scan_type)
                    # Sleep briefly between scans to avoid resource contention
                    time.sleep(0.5)
                    
    @safe_action_wrapper
    def _on_scan_network_action(self, device_or_devices):
        """Handle Scan Network action from context menu"""
        # This action doesn't need the selected device, just show the scan dialog
        network_range = self._show_scan_dialog()
        
        if network_range:
            # Get scan type from settings
            scan_type = self.settings["scan_type"]["value"]
            
            # Start the scan
            self.scan_network(network_range, scan_type)
            
    @safe_action_wrapper
    def _on_scan_from_device_action(self, device_or_devices):
        """Handle Scan from Selected Device action from context menu"""
        # Get the device(s)
        if isinstance(device_or_devices, list):
            if not device_or_devices:
                QMessageBox.warning(
                    self.main_window,
                    "No Device Selected",
                    "Please select a device to scan its network."
                )
                return
            device = device_or_devices[0]  # Use the first device
        else:
            device = device_or_devices
            
        if not device:
            QMessageBox.warning(
                self.main_window,
                "No Device Selected",
                "Please select a device to scan its network."
            )
            return
            
        # Get the IP address
        ip_address = device.get_property("ip_address", "")
        
        if not ip_address:
            QMessageBox.warning(
                self.main_window,
                "No IP Address",
                "The selected device does not have an IP address."
            )
            return
            
        try:
            # Parse the IP address to get the network
            ip = ipaddress.ip_address(ip_address)
            
            # For IPv4, assume /24 subnet
            if isinstance(ip, ipaddress.IPv4Address):
                network = ipaddress.IPv4Network(f"{ip_address}/24", strict=False)
                network_range = str(network)
            else:
                # For IPv6, assume /64 subnet
                network = ipaddress.IPv6Network(f"{ip_address}/64", strict=False)
                network_range = str(network)
                
            # Show the scan dialog with the device's network pre-filled
            dialog_result = self._show_scan_dialog()
            if dialog_result:
                network_range = dialog_result
                
                # Get scan type from settings
                scan_type = self.settings["scan_type"]["value"]
                
                # Start the scan
                self.scan_network(network_range, scan_type)
                
        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"Error determining network range: {e}"
            )

    def on_device_added(self, device):
        """Handle device added signal"""
        # Check if this device was added by this plugin
        if device.get_property("scan_source", "") == "nmap":
            logger.debug(f"Device added by this plugin: {device.get_property('alias')}")
            
    def on_device_removed(self, device):
        """Handle device removed signal"""
        # Nothing specific to do for removed devices
        pass
        
    def on_device_changed(self, device):
        """Handle device changed signal"""
        # Nothing specific to do for changed devices
        pass
        
    def get_settings(self):
        """Get plugin settings"""
        return self.settings
        
    def update_setting(self, setting_id, value):
        """Update a plugin setting"""
        if setting_id in self.settings:
            self.settings[setting_id]["value"] = value
            logger.debug(f"Updated setting {setting_id} to {value}")
            
            # Special handling for certain settings
            if setting_id == "scan_profiles":
                # Update the scan type choices if profiles changed
                scan_types = list(value.keys())
                self.settings["scan_type"]["choices"] = scan_types
                
            return True
        return False

    def _check_nmap_executable(self):
        """Check if the nmap executable is available in the system PATH"""
        import subprocess
        import shutil
        
        try:
            # First try using shutil which is more reliable
            nmap_path = shutil.which("nmap")
            
            if nmap_path:
                logger.info(f"Nmap executable found at: {nmap_path}")
                return True
            
            # Try running nmap --version as a fallback
            try:
                result = subprocess.run(
                    ["nmap", "--version"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    timeout=2,  # 2 second timeout
                    text=True
                )
                
                if result.returncode == 0:
                    version_info = result.stdout.strip().split('\n')[0] if result.stdout else "Unknown version"
                    logger.info(f"Nmap executable available: {version_info}")
                    return True
                else:
                    logger.warning(f"Nmap check failed with return code {result.returncode}")
                    return False
            except Exception as e:
                logger.warning(f"Error checking nmap version: {e}")
                return False
        except Exception as e:
            logger.error(f"Error checking for nmap executable: {e}")
            return False
            
    def _get_network_interfaces(self):
        """Get a list of available network interfaces with their details"""
        interfaces = []
        
        if not HAS_NETIFACES:
            logger.warning("Netifaces library not available, cannot enumerate interfaces")
            return interfaces
            
        try:
            # Get list of interfaces
            for iface in netifaces.interfaces():
                try:
                    # Skip loopback and non-active interfaces
                    if iface == 'lo' or iface.startswith('vbox') or iface.startswith('docker'):
                        continue
                        
                    addrs = netifaces.ifaddresses(iface)
                    
                    # Get IPv4 address if available
                    if netifaces.AF_INET in addrs:
                        for addr in addrs[netifaces.AF_INET]:
                            ip = addr.get('addr')
                            netmask = addr.get('netmask')
                            
                            if ip and not ip.startswith('127.'):
                                # Create interface info
                                interface_info = {
                                    'name': iface,
                                    'ip': ip,
                                    'netmask': netmask,
                                    'display': f"{iface}: {ip}"
                                }
                                
                                # Try to get subnet in CIDR format
                                try:
                                    network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                                    interface_info['network'] = str(network)
                                    interface_info['display'] = f"{iface}: {ip} ({network})"
                                except Exception as e:
                                    logger.debug(f"Error calculating network for {iface}: {e}")
                                
                                interfaces.append(interface_info)
                except Exception as e:
                    logger.debug(f"Error processing interface {iface}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error getting network interfaces: {e}")
            
        return interfaces
        
    def _update_interface_choices(self):
        """Update the interface choices in settings"""
        interfaces = self._get_network_interfaces()
        
        # Update the choices in settings
        if "preferred_interface" in self.settings:
            choices = [f"{iface['display']}" for iface in interfaces]
            self.settings["preferred_interface"]["choices"] = choices
            
            # Add a blank option for "any interface"
            self.settings["preferred_interface"]["choices"].insert(0, "Any (default)")
            
            # Store the interface data for later use
            self._network_interfaces = interfaces
            
        return interfaces
        
    def _get_interface_subnet(self, interface_name=None):
        """Get the subnet for the specified interface or the preferred interface"""
        # If no interface specified, use the preferred interface from settings
        if not interface_name:
            preferred = self.settings.get("preferred_interface", {}).get("value", "")
            if preferred and preferred != "Any (default)":
                # Extract interface name from the display string
                interface_name = preferred.split(":")[0].strip()
        
        # If we have an interface name, find its subnet
        if interface_name:
            for iface in getattr(self, "_network_interfaces", []):
                if iface['name'] == interface_name:
                    return iface.get('network', None)
        
        return None

    def get_settings_pages(self):
        """Get plugin settings pages"""
        # Create main settings page (General)
        main_settings = QWidget()
        main_layout = QVBoxLayout(main_settings)
        
        # General settings group
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout(general_group)
        
        # Refresh interfaces button
        refresh_interfaces_layout = QHBoxLayout()
        interface_combo = QComboBox()
        interface_combo.addItems(self.settings["preferred_interface"]["choices"])
        interface_combo.setCurrentText(self.settings["preferred_interface"]["value"])
        refresh_interfaces_button = QPushButton("Refresh")
        refresh_interfaces_button.clicked.connect(self._update_interface_choices_and_refresh_ui)
        refresh_interfaces_layout.addWidget(interface_combo)
        refresh_interfaces_layout.addWidget(refresh_interfaces_button)
        general_layout.addRow("Preferred Interface:", refresh_interfaces_layout)
        
        # Default scan type
        scan_type_combo = QComboBox()
        scan_type_combo.addItems(self.settings["scan_type"]["choices"])
        scan_type_combo.setCurrentText(self.settings["scan_type"]["value"])
        general_layout.addRow("Default Scan Type:", scan_type_combo)
        
        # Connect changes to update settings
        interface_combo.currentTextChanged.connect(
            lambda text: self.update_setting("preferred_interface", text)
        )
        scan_type_combo.currentTextChanged.connect(
            lambda text: self.update_setting("scan_type", text)
        )
        
        main_layout.addWidget(general_group)
        
        # Advanced settings group
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout(advanced_group)
        
        # OS Detection
        os_detection_check = QCheckBox()
        os_detection_check.setChecked(self.settings["os_detection"]["value"])
        os_detection_check.toggled.connect(
            lambda state: self.update_setting("os_detection", state)
        )
        advanced_layout.addRow("Default OS Detection:", os_detection_check)
        
        # Port Scanning
        port_scan_check = QCheckBox()
        port_scan_check.setChecked(self.settings["port_scan"]["value"])
        port_scan_check.toggled.connect(
            lambda state: self.update_setting("port_scan", state)
        )
        advanced_layout.addRow("Default Port Scanning:", port_scan_check)
        
        # Elevated Permissions
        elevated_check = QCheckBox()
        elevated_check.setChecked(self.settings["use_sudo"]["value"])
        elevated_check.toggled.connect(
            lambda state: self.update_setting("use_sudo", state)
        )
        advanced_layout.addRow("Use Elevated Permissions:", elevated_check)

        # Custom Scan Arguments
        custom_args_edit = QLineEdit(self.settings["custom_scan_args"]["value"])
        custom_args_edit.textChanged.connect(
            lambda text: self.update_setting("custom_scan_args", text)
        )
        advanced_layout.addRow("Custom Arguments:", custom_args_edit)
        
        # Auto Tag
        auto_tag_check = QCheckBox()
        auto_tag_check.setChecked(self.settings["auto_tag"]["value"])
        auto_tag_check.toggled.connect(
            lambda state: self.update_setting("auto_tag", state)
        )
        advanced_layout.addRow("Auto Tag Devices:", auto_tag_check)
        
        main_layout.addWidget(advanced_group)
        
        # Add a spacer at the bottom to push everything up
        main_layout.addStretch()
        
        # =======================================================
        # Create a separate profiles settings page
        # =======================================================
        profiles_page = QWidget()
        profiles_page_layout = QVBoxLayout(profiles_page)
        
        # Function to refresh UI with updated interfaces
        def _update_interface_choices_and_refresh_ui():
            self._update_interface_choices()
            interface_combo.clear()
            interface_combo.addItems(self.settings["preferred_interface"]["choices"])
            interface_combo.setCurrentText(self.settings["preferred_interface"]["value"])
        
        # Explanation label
        explanation_label = QLabel(
            "Scan profiles define different scanning configurations. "
            "Select a profile to view or edit its settings, or create a new profile."
        )
        explanation_label.setWordWrap(True)
        profiles_page_layout.addWidget(explanation_label)
        
        # Profiles management section
        profiles_section = QWidget()
        profiles_section_layout = QVBoxLayout(profiles_section)
        
        # Profiles list with Add New option
        profiles_list_layout = QHBoxLayout()
        profiles_list = QComboBox()
        
        # Add all profiles plus a special "Add New..." option
        profile_keys = list(self.settings["scan_profiles"]["value"].keys())
        profiles_list.addItems(profile_keys)
        profiles_list.addItem("--- Add New Profile ---")
        
        profiles_list_layout.addWidget(QLabel("Select Profile:"))
        profiles_list_layout.addWidget(profiles_list, 1)  # Give it stretch factor
        profiles_section_layout.addLayout(profiles_list_layout)
        
        # Profile details form
        profile_details_group = QGroupBox("Profile Details")
        profile_form = QFormLayout(profile_details_group)
        
        profile_name = QLineEdit()
        profile_form.addRow("Display Name:", profile_name)
        
        profile_desc = QLineEdit()
        profile_desc.setPlaceholderText("Description of the scan profile")
        profile_form.addRow("Description:", profile_desc)
        
        profile_args = QLineEdit()
        profile_args.setPlaceholderText("nmap arguments, e.g. -sn -F")
        profile_form.addRow("Arguments:", profile_args)
        
        profile_os = QCheckBox()
        profile_form.addRow("OS Detection:", profile_os)
        
        profile_port = QCheckBox()
        profile_form.addRow("Port Scanning:", profile_port)
        
        profile_timeout = QLineEdit()
        profile_timeout.setValidator(QIntValidator(30, 600))
        profile_form.addRow("Timeout (seconds):", profile_timeout)
        
        profiles_section_layout.addWidget(profile_details_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Save Profile")
        delete_button = QPushButton("Delete Profile")
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(delete_button)
        
        profiles_section_layout.addLayout(buttons_layout)
        
        # Add the profiles section to the profiles page
        profiles_page_layout.addWidget(profiles_section)
        profiles_page_layout.addStretch()
        
        # Function to load profile data
        def load_profile_data():
            profile_id = profiles_list.currentText()
            
            # Handle special "Add New Profile" option
            if profile_id == "--- Add New Profile ---":
                # Clear the form for a new profile
                profile_name.setText("")
                profile_desc.setText("")
                profile_args.setText("-sn")  # Default args for new profile
                profile_os.setChecked(False)
                profile_port.setChecked(False)
                profile_timeout.setText("300")
                
                # Disable delete button, enable other fields
                delete_button.setEnabled(False)
                profile_name.setEnabled(True)
                profile_desc.setEnabled(True)
                profile_args.setEnabled(True)
                profile_os.setEnabled(True)
                profile_port.setEnabled(True)
                profile_timeout.setEnabled(True)
                save_button.setText("Create Profile")
                profile_details_group.setTitle("New Profile Details")
                return
                
            # Regular profile selected    
            if profile_id in self.settings["scan_profiles"]["value"]:
                profile = self.settings["scan_profiles"]["value"][profile_id]
                
                profile_name.setText(profile.get("name", profile_id))
                profile_desc.setText(profile.get("description", ""))
                profile_args.setText(profile.get("arguments", ""))
                profile_os.setChecked(profile.get("os_detection", False))
                profile_port.setChecked(profile.get("port_scan", False))
                profile_timeout.setText(str(profile.get("timeout", 300)))
                
                # Disable delete for built-in profiles
                is_builtin = profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]
                delete_button.setEnabled(not is_builtin)
                
                # Enable all fields
                profile_name.setEnabled(True)
                profile_desc.setEnabled(True)
                profile_args.setEnabled(True)
                profile_os.setEnabled(True)
                profile_port.setEnabled(True)
                profile_timeout.setEnabled(True)
                save_button.setText("Update Profile")
                profile_details_group.setTitle("Edit Profile Details")
                
        # Connect profile selection to load data
        profiles_list.currentTextChanged.connect(load_profile_data)
        
        # Initial load
        load_profile_data()
        
        # Function to save profile (both update and create)
        def save_profile():
            profile_id = profiles_list.currentText()
            
            if profile_id == "--- Add New Profile ---":
                # This is a new profile, ask for an ID
                new_id, ok = QInputDialog.getText(
                    profiles_page,
                    "New Profile",
                    "Enter a unique profile ID (lowercase, no spaces):",
                    text="custom_scan"  # Default suggestion
                )
                
                if not ok or not new_id:
                    return
                
                # Validate ID (lowercase, no spaces, etc.)
                new_id = new_id.lower().strip().replace(" ", "_")
                
                # Check if ID already exists
                if new_id in self.settings["scan_profiles"]["value"]:
                    QMessageBox.warning(
                        profiles_page,
                        "Profile Exists",
                        f"A profile with ID '{new_id}' already exists. Please choose a different ID."
                    )
                    return
                
                profile_id = new_id
            
            # Get values from form
            name = profile_name.text()
            description = profile_desc.text()
            arguments = profile_args.text()
            os_detection = profile_os.isChecked()
            port_scan = profile_port.isChecked()
            
            # Validate timeout
            try:
                timeout = int(profile_timeout.text())
                if timeout < 30:
                    timeout = 30
                elif timeout > 600:
                    timeout = 600
            except ValueError:
                timeout = 300
            
            # Prepare updated/new profile
            updated_profile = {
                "name": name,
                "description": description,
                "arguments": arguments,
                "os_detection": os_detection,
                "port_scan": port_scan,
                "timeout": timeout
            }
            
            # Update or add the profile in settings
            profiles = self.settings["scan_profiles"]["value"].copy()
            profiles[profile_id] = updated_profile
            self.update_setting("scan_profiles", profiles)
            
            # Update scan type choices if needed
            if profile_id not in self.settings["scan_type"]["choices"]:
                choices = list(self.settings["scan_type"]["choices"])
                choices.append(profile_id)
                self.settings["scan_type"]["choices"] = choices
                scan_type_combo.clear()
                scan_type_combo.addItems(choices)
                
            # Update UI
            current_index = profiles_list.findText(profile_id)
            if current_index == -1:  # Not found
                # This was a new profile, refresh the list
                profiles_list.clear()
                all_profiles = list(self.settings["scan_profiles"]["value"].keys())
                profiles_list.addItems(all_profiles)
                profiles_list.addItem("--- Add New Profile ---")
                profiles_list.setCurrentText(profile_id)
            
            # Show confirmation
            action = "created" if profile_id != profiles_list.currentText() else "updated"
            QMessageBox.information(
                profiles_page,
                "Profile Saved",
                f"The profile '{profile_id}' has been {action}."
            )
            
        # Function to delete profile
        def delete_profile():
            profile_id = profiles_list.currentText()
            
            # Prevent deletion of built-in profiles
            if profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]:
                QMessageBox.warning(
                    profiles_page,
                    "Cannot Delete",
                    "Built-in profiles cannot be deleted."
                )
                return
                
            # Don't try to delete "Add New Profile" option
            if profile_id == "--- Add New Profile ---":
                return
                
            # Confirm deletion
            result = QMessageBox.question(
                profiles_page,
                "Confirm Deletion",
                f"Are you sure you want to delete the profile '{profile_id}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Remove from settings
                profiles = self.settings["scan_profiles"]["value"].copy()
                if profile_id in profiles:
                    del profiles[profile_id]
                    self.update_setting("scan_profiles", profiles)
                    
                    # Remove from choices if present
                    if profile_id in self.settings["scan_type"]["choices"]:
                        choices = list(self.settings["scan_type"]["choices"])
                        choices.remove(profile_id)
                        self.settings["scan_type"]["choices"] = choices
                        scan_type_combo.clear()
                        scan_type_combo.addItems(choices)
                    
                    # Update UI
                    profiles_list.clear()
                    all_profiles = list(self.settings["scan_profiles"]["value"].keys())
                    profiles_list.addItems(all_profiles)
                    profiles_list.addItem("--- Add New Profile ---")
                    
                    # Show confirmation
                    QMessageBox.information(
                        profiles_page,
                        "Profile Deleted",
                        f"The profile '{profile_id}' has been deleted."
                    )
        
        # Connect button actions
        save_button.clicked.connect(save_profile)
        delete_button.clicked.connect(delete_profile)
        
        # Return both settings pages
        return [("General", main_settings), ("Scan Profiles", profiles_page)]


# Create plugin instance (will be loaded by the plugin manager)
logger.info("Creating Network Scanner plugin instance")
plugin_instance = NetworkScannerPlugin()
logger.info("Network Scanner plugin instance created") 