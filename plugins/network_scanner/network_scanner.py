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
    QRadioButton, QInputDialog, QHeaderView
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
    
    def __init__(self, network_range, scan_type="quick", timeout=600, 
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
        
        try:
            # Initialize the scanner instance
            try:
                import nmap
                self.scanner = nmap.PortScanner()
                logger.debug(f"Created nmap scanner instance for {self.network_range}")
            except ImportError:
                logger.error("Failed to import python-nmap. Make sure it's installed.")
                self.scan_error.emit("Failed to import python-nmap. Make sure it's installed.")
                self.is_running = False
                return
            except Exception as e:
                logger.error(f"Error initializing nmap scanner: {e}")
                self.scan_error.emit(f"Error initializing scanner: {str(e)}")
                self.is_running = False
                return
            
            # Build the arguments string
            arguments = ""
            
            # Use profile arguments if provided
            if self.scan_type and self.scan_type != "custom":
                if self.scan_type == "quick":
                    arguments = "-sn -T4"  # Ping scan (no port scan)
                elif self.scan_type == "standard":
                    arguments = "-sn -F -O -T4"  # Fast scan with OS detection
                elif self.scan_type == "comprehensive":
                    arguments = "-sS -p 1-1000 -O -A -T4"  # SYN scan with OS and service detection
                elif self.scan_type == "stealth":
                    arguments = "-sS -T2"  # SYN scan with timing template 2 (slower)
                elif self.scan_type == "service":
                    arguments = "-sV -p 21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5900,8080 -T4"
            
            # Only add OS detection if requested AND not already in arguments
            if self.os_detection and "-O" not in arguments:
                arguments += " -O"
                
            # Only add port scan if requested AND not already in arguments
            if self.port_scan and not any(x in arguments for x in ["-p", "-sS", "-sT", "-sV"]):
                arguments += " -p 22,23,80,443,8080"
                
            # Add custom arguments if provided
            if self.custom_scan_args:
                arguments += f" {self.custom_scan_args}"
                
            # Make sure we don't have duplicate arguments by splitting and rejoining
            # This prevents issues like having "-sn -T4 -sn -T4"
            arg_parts = arguments.split()
            unique_args = []
            seen_options = set()
            port_options = []  # Store all port options
            
            # First pass - collect all port options and other unique args
            for arg in arg_parts:
                if arg.startswith("-p"):
                    # Store port option separately
                    if len(arg) > 2:  # Format is "-pXXX"
                        port_options.append(arg[2:])  # Just the port numbers
                    elif arg == "-p" and len(arg_parts) > arg_parts.index(arg) + 1:
                        # Handle space-separated format like "-p 22,80"
                        next_idx = arg_parts.index(arg) + 1
                        next_arg = arg_parts[next_idx]
                        if not next_arg.startswith("-"):  # Ensure it's actually port numbers
                            port_options.append(next_arg)
                elif arg.startswith("-"):
                    # For other options, only add if we haven't seen them before
                    option_char = arg[1:].split(" ")[0]  # Extract the option character
                    if option_char not in seen_options:
                        seen_options.add(option_char)
                        unique_args.append(arg)
                else:
                    # For non-option arguments, always add
                    unique_args.append(arg)
            
            # Now add the consolidated port option if we collected any
            if port_options:
                # Merge all port specifications, removing duplicates
                all_ports = set()
                for ports in port_options:
                    # Split by commas, handle ranges like "1-1000"
                    for port_spec in ports.split(","):
                        all_ports.add(port_spec.strip())
                
                # Add consolidated port option
                unique_args.append(f"-p {','.join(sorted(all_ports))}")
                
            # Rebuild the arguments string
            arguments = " ".join(unique_args)
                
            # Log the scan command
            logger.info(f"Starting network scan of {self.network_range} with arguments: {arguments}")
            
            # Add verbose output if not already specified to provide more feedback
            if "-v" not in arguments:
                arguments += " -v"
                
            # Tracking variables
            scan_start_time = time.time()
            devices_found = 0
            last_progress_update = time.time()
            last_status_message = ""
            
            try:
                # Check if we should stop before even starting
                if self.should_stop:
                    logger.info("Scan stopped before starting")
                    self.is_running = False
                    return
                    
                # Provide initial progress feedback
                self.progress.emit(0, 100)  # We don't know total yet, use 100 as placeholder
                
                # Emit a message to show scan is starting
                self.device_found.emit({"status_update": "Initializing nmap scan..."})
                
                # Extract network range info to estimate host count
                host_count_estimate = 256
                try:
                    import ipaddress
                    if "/" in self.network_range:  # CIDR notation
                        try:
                            network = ipaddress.IPv4Network(self.network_range, strict=False)
                            host_count_estimate = network.num_addresses
                            self.device_found.emit({"status_update": f"Preparing to scan {host_count_estimate} potential addresses..."})
                        except Exception:
                            pass
                except Exception:
                    pass
                
                # Start the scan within a try/except block
                try:
                    # Use a reasonable timeout value
                    timeout_val = max(60, min(self.timeout, 900))  # Between 60 and 900 seconds
                    
                    # Only add a -T4 timing template if not already specified to speed up the scan
                    if not any(arg in arguments for arg in ["-T1", "-T2", "-T3", "-T4", "-T5"]):
                        arguments += " -T4"
                        
                    logger.debug(f"Starting nmap scan with timeout {timeout_val}s and arguments: {arguments}")
                    
                    # Let the user know we're starting
                    self.device_found.emit({"status_update": f"Starting nmap scan with timeout {timeout_val}s..."})
                    
                    # Create a timer to provide updates during the scan
                    import threading
                    update_timer = None
                    
                    def provide_status_update():
                        if not self.is_running or self.should_stop:
                            return
                            
                        # Calculate elapsed time
                        elapsed = time.time() - scan_start_time
                        # Generate a status message
                        status = f"Scanning in progress... ({int(elapsed)}s elapsed)"
                        
                        # Emit a progress update based on time
                        progress_percent = min(95, int((elapsed / timeout_val) * 100))
                        self.progress.emit(progress_percent, 100)
                        
                        # Only emit a new status message if it's different
                        nonlocal last_status_message
                        if status != last_status_message:
                            self.device_found.emit({"status_update": status})
                            last_status_message = status
                        
                        # Schedule the next update
                        nonlocal update_timer
                        if self.is_running and not self.should_stop:
                            update_timer = threading.Timer(1.0, provide_status_update)
                            update_timer.daemon = True
                            update_timer.start()
                    
                    # Start the timer for updates
                    update_timer = threading.Timer(1.0, provide_status_update)
                    update_timer.daemon = True
                    update_timer.start()
                    
                    # Execute nmap scan
                    self.scanner.scan(hosts=self.network_range, arguments=arguments, 
                                     timeout=timeout_val, sudo=self.use_sudo)
                    
                    # Stop the update timer
                    if update_timer:
                        update_timer.cancel()
                        
                except Exception as scan_error:
                    logger.error(f"Error during nmap scan: {scan_error}")
                    
                    # Check if the error is a timeout and provide a more helpful message
                    error_msg = str(scan_error).lower()
                    if "timed out" in error_msg or "timeout" in error_msg:
                        self.scan_error.emit("Scan timed out. Try using a smaller network range or increasing the timeout value in settings.")
                    else:
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
                    
                    if total_hosts == 0:
                        self.device_found.emit({"status_update": "Scan complete - no hosts found"})
                    else:
                        self.device_found.emit({"status_update": f"Scan complete - processing {total_hosts} discovered hosts..."})
                    
                    # Emit initial progress
                    self.progress.emit(0, total_hosts)
                    
                    for i, host in enumerate(all_hosts):
                        # Check if we should stop
                        if self.should_stop:
                            logger.info("Scan stopped during host processing")
                            break
                        
                        # Emit progress
                        self.progress.emit(i+1, total_hosts)
                        
                        # Update status message periodically
                        current_time = time.time()
                        if current_time - last_progress_update > 0.5:  # Update every half second
                            self.device_found.emit({"status_update": f"Processing host {i+1} of {total_hosts}: {host}"})
                            last_progress_update = current_time
                        
                        # Get host data (with proper error handling to avoid memory corruption)
                        try:
                            # Verify the host is actually up before processing
                            if 'status' not in self.scanner[host] or not self.scanner[host]['status'] or self.scanner[host]['status'].get('state') != 'up':
                                logger.debug(f"Host {host} is not up, skipping")
                                continue
                                
                            host_data = {}
                            host_data["ip_address"] = host
                            host_data["scan_source"] = "nmap"
                            
                            # Store the scan type used to find the device
                            host_data["scan_type"] = self.scan_type
                            
                            # Store the exact state of the host
                            if 'status' in self.scanner[host] and self.scanner[host]['status']:
                                host_data["status"] = self.scanner[host]['status'].get('state', 'unknown')
                                host_data["status_reason"] = self.scanner[host]['status'].get('reason', '')
                            
                            # Get all available hostnames (if available)
                            try:
                                if 'hostnames' in self.scanner[host] and self.scanner[host]['hostnames']:
                                    hostnames = self.scanner[host]['hostnames']
                                    if isinstance(hostnames, list) and hostnames:
                                        # Primary hostname
                                        for hostname_entry in hostnames:
                                            if 'name' in hostname_entry and hostname_entry['name']:
                                                host_data["hostname"] = hostname_entry['name']
                                                break
                                        
                                        # Store all hostnames as a list if there are multiple
                                        all_hostnames = []
                                        for hostname_entry in hostnames:
                                            if 'name' in hostname_entry and hostname_entry['name']:
                                                all_hostnames.append(hostname_entry['name'])
                                        
                                        if len(all_hostnames) > 1:
                                            host_data["all_hostnames"] = all_hostnames
                            except Exception as e:
                                logger.warning(f"Error getting hostname for {host}: {e}")
                            
                            # Get all address information (IPv4, IPv6, MAC)
                            try:
                                if 'addresses' in self.scanner[host]:
                                    addresses = self.scanner[host]['addresses']
                                    
                                    # IPv4 address (already captured in ip_address)
                                    if 'ipv4' in addresses:
                                        host_data["ipv4_address"] = addresses['ipv4']
                                    
                                    # IPv6 address if available
                                    if 'ipv6' in addresses:
                                        host_data["ipv6_address"] = addresses['ipv6']
                                    
                                    # MAC address
                                    if 'mac' in addresses:
                                        host_data["mac_address"] = addresses['mac']
                                
                                # Get vendor information
                                if 'vendor' in self.scanner[host] and self.scanner[host]['vendor']:
                                    vendors = self.scanner[host]['vendor']
                                    if isinstance(vendors, dict) and host_data.get("mac_address") in vendors:
                                        host_data["mac_vendor"] = vendors[host_data["mac_address"]]
                                        
                                        # Also store the raw vendor data
                                        host_data["vendor_info"] = vendors
                            except Exception as e:
                                logger.warning(f"Error getting address info for {host}: {e}")
                            
                            # Get detailed OS detection results
                            try:
                                if 'osmatch' in self.scanner[host] and self.scanner[host]['osmatch']:
                                    os_matches = self.scanner[host]['osmatch']
                                    if isinstance(os_matches, list) and os_matches:
                                        # Get the highest accuracy match for the primary OS field
                                        best_match = max(os_matches, key=lambda x: int(x.get('accuracy', 0)) if x.get('accuracy') else 0)
                                        if 'name' in best_match:
                                            host_data["os"] = best_match['name']
                                            host_data["os_accuracy"] = best_match.get('accuracy', '')
                                            
                                        # Store all OS matches with details
                                        all_os_matches = []
                                        for os_match in os_matches:
                                            if 'name' in os_match:
                                                os_info = {
                                                    'name': os_match['name'],
                                                    'accuracy': os_match.get('accuracy', ''),
                                                    'type': os_match.get('osclass', {}).get('type', '') if isinstance(os_match.get('osclass', {}), dict) else '',
                                                    'vendor': os_match.get('osclass', {}).get('vendor', '') if isinstance(os_match.get('osclass', {}), dict) else '',
                                                    'family': os_match.get('osclass', {}).get('osfamily', '') if isinstance(os_match.get('osclass', {}), dict) else ''
                                                }
                                                all_os_matches.append(os_info)
                                                
                                        if all_os_matches:
                                            host_data["os_matches"] = all_os_matches
                                            
                                # Also check for osclass data directly
                                if 'osclass' in self.scanner[host] and self.scanner[host]['osclass']:
                                    os_classes = self.scanner[host]['osclass']
                                    if isinstance(os_classes, list) and os_classes:
                                        # Store OS classification data
                                        os_classes_data = []
                                        for os_class in os_classes:
                                            if isinstance(os_class, dict):
                                                os_classes_data.append(os_class)
                                                
                                        if os_classes_data:
                                            host_data["os_classes"] = os_classes_data
                            except Exception as e:
                                logger.warning(f"Error getting OS info for {host}: {e}")
                            
                            # Get all port and service information
                            try:
                                # Process TCP ports
                                if 'tcp' in self.scanner[host]:
                                    tcp_ports = []
                                    tcp_services = {}
                                    tcp_details = {}
                                    
                                    for port, port_data in self.scanner[host]['tcp'].items():
                                        # Create a detailed port information dictionary
                                        port_details = {
                                            'port': port,
                                            'state': port_data.get('state', 'unknown'),
                                            'reason': port_data.get('reason', ''),
                                            'name': port_data.get('name', ''),
                                            'product': port_data.get('product', ''),
                                            'version': port_data.get('version', ''),
                                            'extrainfo': port_data.get('extrainfo', ''),
                                            'conf': port_data.get('conf', ''),
                                            'cpe': port_data.get('cpe', '')
                                        }
                                        
                                        # For simplicity in UI, also maintain simple lists of open ports and services
                                        if port_data['state'] == 'open':
                                            tcp_ports.append(int(port))
                                            
                                            if 'name' in port_data and port_data['name']:
                                                service_name = port_data['name']
                                                # Enhance with version if available
                                                if port_data.get('product'):
                                                    service_name += f" ({port_data['product']}"
                                                    if port_data.get('version'):
                                                        service_name += f" {port_data['version']}"
                                                    service_name += ")"
                                                tcp_services[int(port)] = service_name
                                                
                                        # Store all port details regardless of state
                                        tcp_details[int(port)] = port_details
                                        
                                    # Store all TCP port information
                                    if tcp_ports:
                                        host_data["open_tcp_ports"] = sorted(tcp_ports)
                                        
                                    if tcp_services:
                                        host_data["tcp_services"] = tcp_services
                                        
                                    if tcp_details:
                                        host_data["tcp_port_details"] = tcp_details
                                
                                # Process UDP ports
                                if 'udp' in self.scanner[host]:
                                    udp_ports = []
                                    udp_services = {}
                                    udp_details = {}
                                    
                                    for port, port_data in self.scanner[host]['udp'].items():
                                        # Create detailed port information
                                        port_details = {
                                            'port': port,
                                            'state': port_data.get('state', 'unknown'),
                                            'reason': port_data.get('reason', ''),
                                            'name': port_data.get('name', ''),
                                            'product': port_data.get('product', ''),
                                            'version': port_data.get('version', ''),
                                            'extrainfo': port_data.get('extrainfo', ''),
                                            'conf': port_data.get('conf', ''),
                                            'cpe': port_data.get('cpe', '')
                                        }
                                        
                                        # For UI, maintain simple lists
                                        if port_data['state'] == 'open':
                                            udp_ports.append(int(port))
                                            
                                            if 'name' in port_data and port_data['name']:
                                                service_name = port_data['name']
                                                # Enhance with version if available
                                                if port_data.get('product'):
                                                    service_name += f" ({port_data['product']}"
                                                    if port_data.get('version'):
                                                        service_name += f" {port_data['version']}"
                                                    service_name += ")"
                                                udp_services[int(port)] = service_name
                                                
                                        # Store details
                                        udp_details[int(port)] = port_details
                                        
                                    # Store UDP port information
                                    if udp_ports:
                                        host_data["open_udp_ports"] = sorted(udp_ports)
                                        
                                    if udp_services:
                                        host_data["udp_services"] = udp_services
                                        
                                    if udp_details:
                                        host_data["udp_port_details"] = udp_details
                                        
                                # For backward compatibility, maintain the original open_ports and services fields
                                open_ports = host_data.get("open_tcp_ports", []) + host_data.get("open_udp_ports", [])
                                if open_ports:
                                    host_data["open_ports"] = sorted(open_ports)
                                    
                                services = {}
                                # Combine TCP and UDP services
                                services.update(host_data.get("tcp_services", {}))
                                services.update(host_data.get("udp_services", {}))
                                if services:
                                    host_data["services"] = services
                                    
                            except Exception as e:
                                logger.warning(f"Error getting port/service info for {host}: {e}")
                                
                            # Get script output if available
                            try:
                                if 'scripts' in self.scanner[host]:
                                    host_data["script_output"] = self.scanner[host]['scripts']
                            except Exception as e:
                                logger.warning(f"Error getting script output for {host}: {e}")
                            
                            # Store raw scan data for debugging or advanced use
                            try:
                                # Create a simplified version of the raw data to avoid memory issues
                                raw_data = {}
                                for key, value in self.scanner[host].items():
                                    if key not in ['scripts', 'osmatch', 'osclass', 'tcp', 'udp']:
                                        raw_data[key] = value
                                host_data["nmap_raw_data"] = raw_data
                            except Exception as e:
                                logger.warning(f"Error storing raw scan data for {host}: {e}")
                            
                            # Store scan timestamp
                            host_data["last_scan_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Add tags
                            host_data["tags"] = ["scanned", "nmap"]
                            
                            # Generate an alias if none exists
                            if "hostname" in host_data and host_data["hostname"]:
                                host_data["alias"] = host_data["hostname"]
                            elif "mac_vendor" in host_data:
                                host_data["alias"] = f"{host_data['mac_vendor']} Device"
                            else:
                                host_data["alias"] = f"Device at {host}"
                            
                            # Only emit device found if we have the basic information
                            # This ensures we don't add empty or non-existent devices
                            if host_data.get("ip_address"):
                                # Emit the device found signal
                                self.device_found.emit(host_data)
                                devices_found += 1
                            else:
                                logger.debug(f"Host {host} has no IP address, skipping")
                        except Exception as e:
                            logger.error(f"Error processing host {host}: {e}", exc_info=True)
                    
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
            # Cleanup to prevent memory leaks
            try:
                logger.debug("Cleaning up scanner resources")
                # Clear the scanner reference and explicitly help garbage collection
                if hasattr(self, 'scanner') and self.scanner:
                    self.scanner = None
                
                # Force a garbage collection cycle to clean up any lingering objects
                import gc
                gc.collect()
            except Exception as cleanup_error:
                logger.error(f"Error during scanner cleanup: {cleanup_error}")
                
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
        self.version = "1.2.3"
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
                        "arguments": "-sn -T4",
                        "os_detection": False,
                        "port_scan": False,
                        "timeout": 120
                    },
                    "standard": {
                        "name": "Standard Scan",
                        "description": "Balanced scan with basic port scanning and OS detection",
                        "arguments": "-sn -F -O -T4",
                        "os_detection": True,
                        "port_scan": True,
                        "timeout": 300
                    },
                    "comprehensive": {
                        "name": "Comprehensive Scan",
                        "description": "In-depth scan with full port scanning and OS fingerprinting",
                        "arguments": "-sS -p 1-1000 -O -A -T4",
                        "os_detection": True,
                        "port_scan": True,
                        "timeout": 600
                    },
                    "stealth": {
                        "name": "Stealth Scan",
                        "description": "Quiet TCP SYN scan with minimal footprint",
                        "arguments": "-sS -T2",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 480
                    },
                    "service": {
                        "name": "Service Detection",
                        "description": "Focused on detecting services on common ports",
                        "arguments": "-sV -p 21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5900,8080 -T4",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 480
                    }
                },
                "value": {
                    "quick": {
                        "name": "Quick Scan",
                        "description": "Fast ping scan to discover hosts (minimal network impact)",
                        "arguments": "-sn -T4",
                        "os_detection": False,
                        "port_scan": False,
                        "timeout": 120
                    },
                    "standard": {
                        "name": "Standard Scan",
                        "description": "Balanced scan with basic port scanning and OS detection",
                        "arguments": "-sn -F -O -T4",
                        "os_detection": True,
                        "port_scan": True,
                        "timeout": 300
                    },
                    "comprehensive": {
                        "name": "Comprehensive Scan",
                        "description": "In-depth scan with full port scanning and OS fingerprinting",
                        "arguments": "-sS -p 1-1000 -O -A -T4",
                        "os_detection": True,
                        "port_scan": True,
                        "timeout": 600
                    },
                    "stealth": {
                        "name": "Stealth Scan",
                        "description": "Quiet TCP SYN scan with minimal footprint",
                        "arguments": "-sS -T2",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 480
                    },
                    "service": {
                        "name": "Service Detection",
                        "description": "Focused on detecting services on common ports",
                        "arguments": "-sV -p 21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5900,8080 -T4",
                        "os_detection": False,
                        "port_scan": True,
                        "timeout": 480
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
                "default": 600,
                "value": 600
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
            
            # Update the interface dropdown if it exists already
            if hasattr(self, "interface_combo") and self.interface_combo is not None:
                self.interface_combo.clear()
                self.interface_combo.addItems(self.settings["preferred_interface"]["choices"])
                if self.settings["preferred_interface"]["value"] in self.settings["preferred_interface"]["choices"]:
                    self.interface_combo.setCurrentText(self.settings["preferred_interface"]["value"])
                # Set a default network range based on the selected interface
                selected_if_text = self.interface_combo.currentText()
                if selected_if_text and selected_if_text != "Any (default)" and hasattr(self, "network_range_edit"):
                    self._update_network_range_from_interface(0)  # 0 is dummy index
            
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
        
        # Add a scan type manager action for toolbar
        self.scan_type_manager_action = QAction("Scan Type Manager")
        self.scan_type_manager_action.setToolTip("Manage scan profiles and types")
        self.scan_type_manager_action.triggered.connect(self.on_scan_type_manager_action)
        
    def _create_widgets(self):
        """Create plugin widgets"""
        # Main widget
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(8, 8, 8, 8)  # Add proper margins
        self.main_layout.setSpacing(10)  # Increase spacing between main sections
        
        # Create a top section for controls
        top_section = QWidget()
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)
        
        # Input and controls
        self.control_group = QGroupBox("Network Scan Controls")
        self.control_layout = QFormLayout(self.control_group)
        self.control_layout.setSpacing(8)  # Increase spacing between form rows
        self.control_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # Allow fields to expand
        
        # Interface selection
        self.interface_layout = QHBoxLayout()
        self.interface_layout.setSpacing(8)
        self.interface_combo = QComboBox()
        
        # First make sure we have interface choices
        if not self.settings["preferred_interface"]["choices"]:
            self._update_interface_choices()
            
        self.interface_combo.addItems(self.settings["preferred_interface"]["choices"])
        current_interface = self.settings["preferred_interface"]["value"]
        if current_interface and current_interface in self.settings["preferred_interface"]["choices"]:
            self.interface_combo.setCurrentText(current_interface)
            
        self.refresh_interfaces_button = QPushButton("Refresh")
        self.refresh_interfaces_button.setToolTip("Refresh network interface list")
        self.refresh_interfaces_button.clicked.connect(self._update_interface_choices_and_refresh_ui)
        self.interface_layout.addWidget(self.interface_combo, 1)
        self.interface_layout.addWidget(self.refresh_interfaces_button)
        self.control_layout.addRow("Network Interface:", self.interface_layout)
        
        # Network range input - now in its own section with more space
        self.network_range_label = QLabel("Network Range:")
        self.network_range_edit = QLineEdit()
        self.network_range_edit.setPlaceholderText("e.g., 192.168.1.0/24 or 10.0.0.1-10.0.0.254")
        self.control_layout.addRow(self.network_range_label, self.network_range_edit)
        
        # Connect interface change to update network range
        self.interface_combo.currentIndexChanged.connect(self._update_network_range_from_interface)
        
        # Initialize network range from currently selected interface
        self._update_network_range_from_interface(self.interface_combo.currentIndex())
        
        # Scan type with manager button
        scan_type_layout = QHBoxLayout()
        scan_type_layout.setSpacing(8)
        
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.addItems(self.settings["scan_type"]["choices"])
        self.scan_type_combo.setCurrentText(self.settings["scan_type"]["value"])
        
        self.scan_type_manager_button = QPushButton("Manage")
        self.scan_type_manager_button.setToolTip("Manage scan profiles and types")
        self.scan_type_manager_button.clicked.connect(self.on_scan_type_manager_action)
        
        scan_type_layout.addWidget(self.scan_type_combo, 1)
        scan_type_layout.addWidget(self.scan_type_manager_button)
        
        self.control_layout.addRow("Scan Type:", scan_type_layout)
        
        # Scan controls in separate section with buttons side by side
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)  # Increase spacing between buttons
        
        # Create a button grid with 2x2 layout for better organization
        button_grid = QGridLayout()
        button_grid.setSpacing(8)
        button_grid.setHorizontalSpacing(10)
        button_grid.setVerticalSpacing(8)
        
        # Set a fixed minimum width for all buttons to prevent overlapping
        button_width = 100
        
        # Scan button
        self.scan_button = QPushButton("Start Scan")
        self.scan_button.setMinimumWidth(button_width)
        self.scan_button.clicked.connect(self.on_scan_button_clicked)
        button_grid.addWidget(self.scan_button, 0, 0)
        
        # Quick Ping Scan button
        self.quick_ping_button = QPushButton("Quick Ping")
        self.quick_ping_button.setMinimumWidth(button_width)
        self.quick_ping_button.clicked.connect(self.on_quick_ping_button_clicked)
        self.quick_ping_button.setToolTip("Fast ping scan without using nmap")
        button_grid.addWidget(self.quick_ping_button, 0, 1)
        
        # Advanced Scan button
        self.advanced_scan_button = QPushButton("Advanced...")
        self.advanced_scan_button.setMinimumWidth(button_width)
        self.advanced_scan_button.clicked.connect(self.on_advanced_scan_button_clicked)
        self.advanced_scan_button.setToolTip("Open the advanced scan configuration dialog")
        button_grid.addWidget(self.advanced_scan_button, 1, 0)
        
        # Stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.setMinimumWidth(button_width)
        self.stop_button.clicked.connect(self.on_stop_button_clicked)
        self.stop_button.setEnabled(False)
        button_grid.addWidget(self.stop_button, 1, 1)
        
        # Add the grid to the layout
        button_layout.addLayout(button_grid)
        
        # Add stretch to push buttons to the left
        button_layout.addStretch(1)
        
        # Add button layout to form with empty label to align properly
        self.control_layout.addRow("", button_layout)
        
        # Create a horizontal layout for checkboxes to save space
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(20)  # Add spacing between checkboxes
        
        # OS Detection
        os_detection_widget = QWidget()
        os_detection_layout = QHBoxLayout(os_detection_widget)
        os_detection_layout.setContentsMargins(0, 0, 0, 0)
        os_detection_label = QLabel("OS Detection:")
        self.os_detection_check = QCheckBox()
        self.os_detection_check.setChecked(self.settings["os_detection"]["value"])
        os_detection_layout.addWidget(os_detection_label)
        os_detection_layout.addWidget(self.os_detection_check)
        checkbox_layout.addWidget(os_detection_widget)
        
        # Port Scanning
        port_scan_widget = QWidget()
        port_scan_layout = QHBoxLayout(port_scan_widget)
        port_scan_layout.setContentsMargins(0, 0, 0, 0)
        port_scan_label = QLabel("Port Scanning:")
        self.port_scan_check = QCheckBox()
        self.port_scan_check.setChecked(self.settings["port_scan"]["value"])
        port_scan_layout.addWidget(port_scan_label)
        port_scan_layout.addWidget(self.port_scan_check)
        checkbox_layout.addWidget(port_scan_widget)
        
        # Add spacer to push checkboxes to the left
        checkbox_layout.addStretch(1)
        
        # Add the checkbox layout to the control layout
        control_widget = QWidget()
        control_widget.setLayout(checkbox_layout)
        self.control_layout.addRow("", control_widget)
        
        # Add the control group to the top section
        top_layout.addWidget(self.control_group)
        
        # Progress section
        progress_widget = QWidget()
        self.progress_layout = QVBoxLayout(progress_widget)
        self.progress_layout.setContentsMargins(4, 4, 4, 4)
        self.progress_layout.setSpacing(4)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.progress_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_layout.addWidget(self.progress_bar)
        
        # Add progress widget to top section
        top_layout.addWidget(progress_widget)
        
        # Results section
        self.results_group = QGroupBox("Scan Results")
        self.results_layout = QVBoxLayout(self.results_group)
        self.results_layout.setContentsMargins(8, 12, 8, 8)  # Add internal margins for better readability
        
        # Results list
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_layout.addWidget(self.results_text)
        
        # Create a splitter to allow resizing between controls and results
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.addWidget(top_section)
        self.main_splitter.addWidget(self.results_group)
        self.main_splitter.setStretchFactor(0, 0)  # Don't stretch the top section
        self.main_splitter.setStretchFactor(1, 1)  # Let the results section take extra space
        self.main_splitter.setSizes([200, 400])  # Set initial sizes
        
        # Add the splitter to the main layout
        self.main_layout.addWidget(self.main_splitter)
        
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
        
        # Set minimum width to prevent controls from being too cramped
        self.main_widget.setMinimumWidth(300)
        
        # Return a list of tuples: (widget_name, widget, area)
        return [("Network Scanner", dock, Qt.RightDockWidgetArea)]
        
    def get_toolbar_actions(self):
        """Get actions for the toolbar"""
        return [self.scan_action, self.scan_type_manager_action]
        
    def get_menu_actions(self):
        """Get plugin menu actions"""
        return {"Network": [self.scan_action, self.scan_selected_action, self.scan_type_manager_action]}
        
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
            
        # Try to stop ping scan if it's running
        stopped_ping = self.stop_ping_scan()
        
        # Signal the worker to stop
        try:
            if self._scanner_worker:
                self._scanner_worker.stop()
                logger.debug("Worker stop signal sent")
                
                # Force nmap to terminate if possible
                try:
                    # The python-nmap library sometimes doesn't properly terminate the nmap process
                    # We attempt to directly terminate it by accessing the internal scanner object
                    if hasattr(self._scanner_worker, 'scanner') and self._scanner_worker.scanner:
                        # Try to terminate the nmap process directly
                        if hasattr(self._scanner_worker.scanner, '_nmap_last_proc') and self._scanner_worker.scanner._nmap_last_proc:
                            try:
                                process = self._scanner_worker.scanner._nmap_last_proc
                                if process.poll() is None:  # Check if still running
                                    logger.info("Forcibly terminating nmap process")
                                    process.terminate()
                                    # Wait briefly for termination
                                    import time
                                    time.sleep(0.5)
                                    # If still running, kill it
                                    if process.poll() is None:
                                        process.kill()
                                        logger.info("Killed nmap process")
                            except Exception as e:
                                logger.error(f"Error terminating nmap process: {e}")
                except Exception as e:
                    logger.error(f"Error accessing nmap process: {e}")
                
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
            # Check if this is a status update rather than a device
            if "status_update" in host_data:
                # Update the status label with the status message
                if hasattr(self, "status_label"):
                    self.status_label.setText(host_data["status_update"])
                
                # Log the status update
                self.log_message(host_data["status_update"])
                return None
                
            # Use a local copy of host_data to avoid memory corruption
            device_data = host_data.copy()
            
            # Verify we have an IP address at minimum - if not, this isn't a valid device
            if not device_data.get("ip_address"):
                logger.debug("Received device data without IP address, ignoring")
                return None
                
            # For non-ping scans, ensure the device has some meaningful data
            if device_data.get("scan_source") != "ping":
                # Check if this device has any meaningful properties to add
                has_meaningful_data = False
                # Look for properties that would make this device worth adding
                for key in ["hostname", "mac_address", "open_ports", "services", "os"]:
                    if key in device_data and device_data[key]:
                        has_meaningful_data = True
                        break
                        
                # If a device is up but has no additional data, it's still worth adding
                # But we should log this situation for debugging
                if not has_meaningful_data:
                    logger.debug(f"Device at {device_data['ip_address']} is up but has no additional data")
            
            # Check if this device already exists based on IP or MAC
            existing_device = None
            if "ip_address" in device_data and device_data["ip_address"]:
                # Try to find by IP address
                for device in self.device_manager.get_devices():
                    if device.get_property("ip_address") == device_data["ip_address"]:
                        existing_device = device
                        break
                        
            if not existing_device and "mac_address" in device_data and device_data["mac_address"]:
                # Try to find by MAC address
                for device in self.device_manager.get_devices():
                    if device.get_property("mac_address") == device_data["mac_address"]:
                        existing_device = device
                        break
            
            if existing_device:
                # Update existing device (one property at a time to prevent race conditions)
                for key, value in device_data.items():
                    if key == "tags":
                        # Merge tags rather than replace
                        current_tags = existing_device.get_property("tags", [])
                        new_tags = []
                        for tag in value:
                            if tag not in current_tags and tag not in new_tags:
                                new_tags.append(tag)
                        
                        # Only update if there are new tags to add
                        if new_tags:
                            updated_tags = current_tags.copy()  # Make a copy to avoid modifying original
                            updated_tags.extend(new_tags)
                            existing_device.set_property("tags", updated_tags)
                    else:
                        # Only update if value is different to minimize device_changed events
                        current_value = existing_device.get_property(key, None)
                        if current_value != value:
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
                    **device_data
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
        
        # Stop the thread and ensure proper cleanup
        if self._scanner_thread and self._scanner_thread.isRunning():
            self._scanner_thread.quit()
            success = self._scanner_thread.wait(1000)  # 1 second timeout
            
            if not success:
                logger.warning("Thread did not exit cleanly after scan completion, forcing termination")
                self._scanner_thread.terminate()
                self._scanner_thread.wait(1000)
            
            # Reset references to help garbage collection
            self._scanner_worker = None
            self._scanner_thread = None
        
        # Force a garbage collection cycle to clean up lingering objects
        try:
            import gc
            gc.collect()
        except Exception as e:
            logger.warning(f"Error during garbage collection: {e}")
        
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
            
        # Get network range from the UI
        network_range = self.network_range_edit.text()
        if not network_range:
            # If no network range is specified, get it from the selected interface
            network_range = self._get_interface_subnet(self.interface_combo.currentText())
            if not network_range:
                QMessageBox.warning(
                    self.main_window,
                    "Missing Network Range",
                    "Please enter a network range or select a valid interface."
                )
                return
        
        # Get scan type from UI
        scan_type = self.scan_type_combo.currentText()
        
        # Get options from UI
        os_detection = self.os_detection_check.isChecked()
        port_scan = self.port_scan_check.isChecked()
        
        # Start the scan directly with the current panel settings
        self.scan_network(network_range, scan_type)
        
    @safe_action_wrapper
    def on_advanced_scan_button_clicked(self):
        """Handle advanced scan button click - opens the full scan dialog"""
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
        dialog.setMinimumWidth(550)  # Slightly wider to accommodate content
        dialog.setMinimumHeight(450)  # Set minimum height
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)  # Add proper margins
        layout.setSpacing(12)  # Increase spacing
        
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
        basic_layout.setContentsMargins(10, 10, 10, 10)  # Add margins
        basic_layout.setSpacing(12)  # Increase spacing
        
        # Network interface selection
        interface_group = QGroupBox("Network Interface")
        interface_layout = QVBoxLayout(interface_group)
        interface_layout.setContentsMargins(10, 15, 10, 10)
        interface_layout.setSpacing(8)
        
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
        target_layout.setContentsMargins(10, 15, 10, 10)
        target_layout.setSpacing(10)
        
        # Option to scan subnet of selected interface
        scan_subnet_radio = QRadioButton("Scan Interface Subnet")
        
        # Option for custom network range
        custom_range_radio = QRadioButton("Custom Network Range")
        
        # Custom range input with proper layout
        custom_range_container = QWidget()
        custom_range_layout = QHBoxLayout(custom_range_container)
        custom_range_layout.setContentsMargins(20, 0, 0, 0)  # Indent for visual hierarchy
        custom_range_layout.setSpacing(8)
        
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
        target_layout.addWidget(custom_range_container)
        
        # Connect radio buttons to enable/disable related widgets
        def update_ui_state():
            network_range_edit.setEnabled(custom_range_radio.isChecked())
            custom_range_container.setVisible(custom_range_radio.isChecked())
            
        scan_subnet_radio.toggled.connect(update_ui_state)
        custom_range_radio.toggled.connect(update_ui_state)
        if rescan_device_radio:
            rescan_device_radio.toggled.connect(update_ui_state)
            
        # Initial UI state
        update_ui_state()
        
        basic_layout.addWidget(target_group)
        
        # Scan profile
        profile_group = QGroupBox("Scan Profile")
        profile_layout = QVBoxLayout(profile_group)
        profile_layout.setContentsMargins(10, 15, 10, 10)
        profile_layout.setSpacing(8)
        
        # Scan type with label in layout
        scan_type_layout = QHBoxLayout()
        scan_type_layout.addWidget(QLabel("Scan Type:"))
        scan_type_combo = QComboBox()
        scan_type_combo.addItems(self.settings["scan_type"]["choices"])
        scan_type_combo.setCurrentText(self.settings["scan_type"]["value"])
        scan_type_layout.addWidget(scan_type_combo, 1)  # Give combo box more space
        
        profile_layout.addLayout(scan_type_layout)
        
        # Create a label to show scan description with proper styling
        scan_description_label = QLabel()
        scan_description_label.setWordWrap(True)
        scan_description_label.setStyleSheet("padding: 5px; background-color: rgba(240, 240, 240, 100); border-radius: 4px;")
        scan_description_label.setMinimumHeight(60)  # Ensure enough height for multi-line descriptions
        
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
        
        profile_layout.addWidget(scan_description_label)
        
        basic_layout.addWidget(profile_group)
        basic_layout.addStretch(1)  # Add stretch to keep widgets at the top
        
        # ==== Advanced Tab ====
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.setContentsMargins(10, 10, 10, 10)
        advanced_layout.setSpacing(12)
        
        # Scan options
        options_group = QGroupBox("Scan Options")
        options_layout = QFormLayout(options_group)
        options_layout.setContentsMargins(10, 15, 10, 10)
        options_layout.setSpacing(10)
        options_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # Allow fields to grow
        
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
        advanced_layout.addStretch(1)  # Add stretch to keep widgets at the top
        
        # ==== Profiles Tab ====
        profiles_layout = QVBoxLayout(profiles_tab)
        profiles_layout.setContentsMargins(10, 10, 10, 10)
        profiles_layout.setSpacing(12)
        
        # Display the current scan profiles
        profiles_label = QLabel("Available Scan Profiles:")
        profiles_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        profiles_layout.addWidget(profiles_label)
        
        # Create a text display for the profiles
        profiles_text = QTextEdit()
        profiles_text.setReadOnly(True)
        profiles_text.setStyleSheet("line-height: 1.4;")  # Improve line spacing
        
        # Format the profiles information
        profile_info = ""
        for scan_id, profile in self.settings["scan_profiles"]["value"].items():
            profile_info += f"<div style='margin-bottom: 12px; padding: 8px; background-color: rgba(240, 240, 240, 100); border-radius: 4px;'>"
            profile_info += f"<div style='font-weight: bold; font-size: 14px; color: #444; margin-bottom: 5px;'>{profile.get('name', scan_id)}</div>"
            profile_info += f"<div style='margin: 3px 0;'><b>Description:</b> {profile.get('description', 'No description')}</div>"
            profile_info += f"<div style='margin: 3px 0;'><b>Arguments:</b> <code>{profile.get('arguments', '')}</code></div>"
            profile_info += f"<div style='margin: 3px 0;'><b>OS Detection:</b> {'Yes' if profile.get('os_detection', False) else 'No'}</div>"
            profile_info += f"<div style='margin: 3px 0;'><b>Port Scan:</b> {'Yes' if profile.get('port_scan', False) else 'No'}</div>"
            profile_info += f"<div style='margin: 3px 0;'><b>Timeout:</b> {profile.get('timeout', 300)} seconds</div>"
            profile_info += "</div>"
            
        profiles_text.setHtml(profile_info)
        profiles_layout.addWidget(profiles_text)
        
        # Help text
        help_label = QLabel("Note: Scan profiles can be edited in the plugin settings.")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("font-style: italic; color: #666; padding: 5px;")
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
                    # Get subnet directly from the interface text
                    subnet = self._get_interface_subnet(selected_if_text)
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
                                # Try to get a friendly name/alias for the interface
                                interface_alias = self._get_interface_friendly_name(iface)
                                
                                # Create interface info
                                interface_info = {
                                    'name': iface,
                                    'alias': interface_alias,
                                    'ip': ip,
                                    'netmask': netmask,
                                    'display': f"{interface_alias}: {ip}"
                                }
                                
                                # Try to get subnet in CIDR format
                                try:
                                    network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                                    interface_info['network'] = str(network)
                                    interface_info['display'] = f"{interface_alias}: {ip} ({network})"
                                except Exception as e:
                                    logger.debug(f"Error calculating network for {iface}: {e}")
                                
                                interfaces.append(interface_info)
                except Exception as e:
                    logger.debug(f"Error processing interface {iface}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error getting network interfaces: {e}")
            
        return interfaces

    def _get_interface_friendly_name(self, interface_name):
        """Get a friendly name for the interface"""
        # This is a platform-dependent function
        try:
            import platform
            
            if platform.system() == "Windows":
                # On Windows, try to get friendly name using WMI
                try:
                    import wmi
                    c = wmi.WMI()
                    for adapter in c.Win32_NetworkAdapter():
                        if adapter.NetConnectionID and interface_name.lower() in adapter.NetConnectionID.lower():
                            return adapter.NetConnectionID
                        # Sometimes we need to match on the GUID
                        elif adapter.GUID and interface_name.lower() in adapter.GUID.lower():
                            return adapter.NetConnectionID or adapter.Name
                except Exception as e:
                    logger.debug(f"Error getting Windows interface name: {e}")
                    
                # If we couldn't get it from WMI, try some heuristics
                if "Local Area Connection" in interface_name:
                    return "Ethernet"
                elif "Wireless" in interface_name:
                    return "Wi-Fi"
                
            elif platform.system() == "Linux":
                # On Linux, try to get interface type
                if interface_name.startswith("eth"):
                    return "Ethernet"
                elif interface_name.startswith("wlan") or interface_name.startswith("wifi"):
                    return "Wi-Fi"
                elif interface_name.startswith("en"):
                    return "Ethernet"  # Modern naming scheme
                elif interface_name.startswith("wl"):
                    return "Wi-Fi"  # Modern naming scheme
            
            # If we got here, use the interface name as the alias
            return interface_name
            
        except Exception as e:
            logger.debug(f"Error getting interface friendly name: {e}")
            return interface_name
        
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
                # Extract interface info from the display string format: "Alias: IP (Network)"
                try:
                    # First check if we have stored interface data
                    if hasattr(self, "_network_interfaces") and self._network_interfaces:
                        # Find the interface with matching display string
                        for iface in self._network_interfaces:
                            if iface["display"] == preferred:
                                interface_name = iface["name"]
                                # If we found a match, we can return the network directly
                                if "network" in iface:
                                    return iface["network"]
                                break
                    
                    # If we didn't find it, try to extract from the display string
                    if not interface_name:
                        # Parse the interface name from the display string
                        parts = preferred.split(": ")
                        if len(parts) >= 2:
                            # Extract IP address from second part
                            ip_part = parts[1].split(" ")[0]
                            # Look for interface with this IP
                            if hasattr(self, "_network_interfaces") and self._network_interfaces:
                                for iface in self._network_interfaces:
                                    if iface["ip"] == ip_part:
                                        interface_name = iface["name"]
                                        # If we found a match, we can return the network directly
                                        if "network" in iface:
                                            return iface["network"]
                                        break
                except Exception as e:
                    logger.error(f"Error extracting interface name from {preferred}: {e}")
                    return None
        
        # If we have an interface name, find its subnet
        if interface_name:
            try:
                # Make sure we have network interface data
                if not hasattr(self, "_network_interfaces") or not self._network_interfaces:
                    # Try to update interfaces
                    logger.debug("Network interfaces not loaded, attempting to load them now")
                    self._update_interface_choices()
                
                # Search for the interface in our stored data
                for iface in getattr(self, "_network_interfaces", []):
                    if iface['name'] == interface_name:
                        network = iface.get('network', None)
                        if network:
                            logger.debug(f"Found subnet {network} for interface {interface_name}")
                            return network
                        else:
                            logger.debug(f"Interface {interface_name} found but has no subnet information")
                            # Try to calculate it if we have IP and netmask
                            if 'ip' in iface and 'netmask' in iface:
                                try:
                                    network = ipaddress.IPv4Network(f"{iface['ip']}/{iface['netmask']}", strict=False)
                                    logger.debug(f"Calculated subnet {network} for interface {interface_name}")
                                    return str(network)
                                except Exception as e:
                                    logger.debug(f"Error calculating network for {interface_name}: {e}")
                
                logger.debug(f"No matching interface found for {interface_name}")
            except Exception as e:
                logger.error(f"Error getting subnet for interface {interface_name}: {e}")
        
        return None

    def get_settings_pages(self):
        """Get plugin settings pages"""
        # Create main settings page (General)
        main_settings = QWidget()
        main_layout = QVBoxLayout(main_settings)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)  # Increase spacing between widgets
        
        # General settings group
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout(general_group)
        general_layout.setContentsMargins(12, 15, 12, 12)
        general_layout.setSpacing(10)  # Increase spacing between form rows
        general_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # Allow fields to expand
        
        # Refresh interfaces button
        refresh_interfaces_layout = QHBoxLayout()
        refresh_interfaces_layout.setSpacing(8)  # Add spacing between elements
        interface_combo = QComboBox()
        interface_combo.addItems(self.settings["preferred_interface"]["choices"])
        interface_combo.setCurrentText(self.settings["preferred_interface"]["value"])
        refresh_interfaces_button = QPushButton("Refresh")
        refresh_interfaces_button.clicked.connect(self._update_interface_choices_and_refresh_ui)
        refresh_interfaces_layout.addWidget(interface_combo, 1)  # Give the combo box more space
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
        advanced_layout.setContentsMargins(12, 15, 12, 12)
        advanced_layout.setSpacing(10)  # Increase spacing between form rows
        advanced_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # Allow fields to expand
        
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
        main_layout.addStretch(1)
        
        # =======================================================
        # Create a separate profiles settings page
        # =======================================================
        profiles_page = QWidget()
        profiles_page_layout = QVBoxLayout(profiles_page)
        profiles_page_layout.setContentsMargins(10, 10, 10, 10)
        profiles_page_layout.setSpacing(15)  # Increase spacing between widgets
        
        # Function to refresh UI with updated interfaces
        def _update_interface_choices_and_refresh_ui():
            self._update_interface_choices()
            interface_combo.clear()
            interface_combo.addItems(self.settings["preferred_interface"]["choices"])
            interface_combo.setCurrentText(self.settings["preferred_interface"]["value"])
        
        # Explanation label with better styling
        explanation_label = QLabel(
            "Scan profiles define different scanning configurations. "
            "Select a profile to view or edit its settings, or create a new profile."
        )
        explanation_label.setWordWrap(True)
        explanation_label.setStyleSheet("padding: 8px; background-color: #f0f0f0; border-radius: 4px;")
        profiles_page_layout.addWidget(explanation_label)
        
        # Profiles management section
        profiles_section = QWidget()
        profiles_section_layout = QVBoxLayout(profiles_section)
        profiles_section_layout.setContentsMargins(0, 0, 0, 0)
        profiles_section_layout.setSpacing(12)
        
        # Profiles list with Add New option
        profiles_list_layout = QHBoxLayout()
        profiles_list_layout.setSpacing(10)
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
        profile_form.setContentsMargins(12, 15, 12, 12)
        profile_form.setSpacing(10)  # Increase spacing between form rows
        profile_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # Allow fields to expand
        
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

    def _update_interface_choices_and_refresh_ui(self):
        """Update interface choices and refresh the UI"""
        try:
            # Update the interface choices
            interfaces = self._update_interface_choices()
            
            # Update the UI combobox if it exists
            if hasattr(self, "interface_combo") and self.interface_combo is not None:
                # Remember current selection to restore it if possible
                current_selection = self.interface_combo.currentText()
                
                # Clear and repopulate
                self.interface_combo.clear()
                self.interface_combo.addItems(self.settings["preferred_interface"]["choices"])
                
                # Try to restore previous selection, otherwise use the default
                if current_selection and current_selection in self.settings["preferred_interface"]["choices"]:
                    self.interface_combo.setCurrentText(current_selection)
                elif self.settings["preferred_interface"]["value"] in self.settings["preferred_interface"]["choices"]:
                    self.interface_combo.setCurrentText(self.settings["preferred_interface"]["value"])
                
                # Log the update
                logger.debug(f"Updated interface list, found {len(interfaces)} interfaces")
                
                # Update network range based on selected interface
                self._update_network_range_from_interface(self.interface_combo.currentIndex())
                
            return True
        except Exception as e:
            logger.error(f"Error updating interface choices: {e}")
            return False

    def _update_network_range_from_interface(self, index):
        """Update network range based on selected interface"""
        try:
            # Check if the UI elements exist
            if not hasattr(self, "interface_combo") or not hasattr(self, "network_range_edit"):
                logger.debug("UI elements not yet created, skipping network range update")
                return
            
            selected_if_text = self.interface_combo.currentText()
            
            # Skip "Any (default)" option
            if not selected_if_text or selected_if_text == "Any (default)":
                logger.debug("No specific interface selected, not updating network range")
                return
            
            # Log the selected interface for debugging
            logger.debug(f"Updating network range from selected interface: {selected_if_text}")
                
            # Try to directly find the network from stored interface data
            if hasattr(self, "_network_interfaces") and self._network_interfaces:
                for iface in self._network_interfaces:
                    if iface["display"] == selected_if_text:
                        # Check if network information is available
                        if "network" in iface:
                            network = iface["network"]
                            self.network_range_edit.setText(network)
                            logger.debug(f"Updated network range to {network} from interface {iface['alias']}")
                            return True
                        # Try IP with netmask
                        elif "ip" in iface and "netmask" in iface:
                            try:
                                network = ipaddress.IPv4Network(f"{iface['ip']}/{iface['netmask']}", strict=False)
                                network_str = str(network)
                                self.network_range_edit.setText(network_str)
                                logger.debug(f"Updated network range to {network_str} from interface {iface['alias']}")
                                return True
                            except Exception as e:
                                logger.debug(f"Error calculating network for {iface['alias']}: {e}")

            # If we get here, try getting the subnet using the standard method as fallback
            subnet = self._get_interface_subnet(selected_if_text)
            
            if subnet:
                # Set the network range text field and log it
                self.network_range_edit.setText(subnet)
                logger.debug(f"Updated network range to {subnet} from interface")
                return True
            else:
                logger.warning(f"Could not determine subnet for interface {selected_if_text}")
        
            # If no subnet was found from interface, try to get one from local IP
            try:
                import socket
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
                network = ipaddress.IPv4Network(f"{ip_address}/24", strict=False)
                self.network_range_edit.setText(str(network))
                logger.debug(f"Used default network {network} from local IP {ip_address}")
                return True
            except Exception as e:
                logger.debug(f"Error determining default network range: {e}")
        except Exception as e:
            logger.error(f"Error updating network range from interface: {e}")
            
        return False

    @safe_action_wrapper
    def on_scan_type_manager_action(self):
        """Handle scan type manager action"""
        self._show_scan_type_manager_dialog()
        
    def _show_scan_type_manager_dialog(self):
        """Show the scan type manager dialog"""
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Scan Type Manager")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Add description
        description_label = QLabel(
            "Manage your scan profiles. You can create new profiles, edit existing ones, or delete custom profiles."
        )
        description_label.setWordWrap(True)
        description_label.setStyleSheet("padding: 8px; background-color: #f0f0f0; border-radius: 4px;")
        layout.addWidget(description_label)
        
        # Create a table to display profiles
        profile_table = QTableWidget()
        profile_table.setColumnCount(5)
        profile_table.setHorizontalHeaderLabels(["Name", "Description", "Arguments", "OS Detection", "Port Scan"])
        profile_table.horizontalHeader().setStretchLastSection(True)
        profile_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        profile_table.setSelectionBehavior(QTableWidget.SelectRows)
        profile_table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(profile_table)
        
        # Function to refresh the table
        def refresh_table():
            profile_table.setRowCount(0)
            profiles = self.settings["scan_profiles"]["value"]
            
            for i, (profile_id, profile) in enumerate(profiles.items()):
                is_builtin = profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]
                
                profile_table.insertRow(i)
                
                # Name column
                name_item = QTableWidgetItem(profile.get("name", profile_id))
                if is_builtin:
                    name_item.setToolTip("Built-in profile (can't be deleted)")
                    # Set a background color for built-in profiles
                    name_item.setBackground(QColor("#f0f0f0"))
                name_item.setData(Qt.UserRole, profile_id)  # Store profile ID
                profile_table.setItem(i, 0, name_item)
                
                # Description column
                profile_table.setItem(i, 1, QTableWidgetItem(profile.get("description", "")))
                
                # Arguments column
                profile_table.setItem(i, 2, QTableWidgetItem(profile.get("arguments", "")))
                
                # OS Detection column
                os_detection_item = QTableWidgetItem("Yes" if profile.get("os_detection", False) else "No")
                os_detection_item.setTextAlignment(Qt.AlignCenter)
                profile_table.setItem(i, 3, os_detection_item)
                
                # Port Scan column
                port_scan_item = QTableWidgetItem("Yes" if profile.get("port_scan", False) else "No")
                port_scan_item.setTextAlignment(Qt.AlignCenter)
                profile_table.setItem(i, 4, port_scan_item)
                
            profile_table.resizeColumnsToContents()
            # Ensure description column gets some minimum width
            if profile_table.columnWidth(1) < 150:
                profile_table.setColumnWidth(1, 150)
        
        # First populate the table
        refresh_table()
        
        # Button layout
        button_layout = QHBoxLayout()
        new_button = QPushButton("New Profile")
        edit_button = QPushButton("Edit Profile")
        delete_button = QPushButton("Delete Profile")
        # Initially disable edit/delete until a row is selected
        edit_button.setEnabled(False)
        delete_button.setEnabled(False)
        
        button_layout.addWidget(new_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addStretch(1)
        
        layout.addLayout(button_layout)
        
        # Add dialog buttons
        dialog_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        dialog_buttons.rejected.connect(dialog.reject)
        layout.addWidget(dialog_buttons)
        
        # Handle selection change
        def on_selection_changed():
            selected_indexes = profile_table.selectedIndexes()
            if selected_indexes:
                row = selected_indexes[0].row()
                profile_id = profile_table.item(row, 0).data(Qt.UserRole)
                is_builtin = profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]
                
                edit_button.setEnabled(True)
                delete_button.setEnabled(not is_builtin)
            else:
                edit_button.setEnabled(False)
                delete_button.setEnabled(False)
        
        profile_table.itemSelectionChanged.connect(on_selection_changed)
        
        # Show edit dialog for a profile
        def edit_profile_dialog(profile_id=None, is_new=False):
            edit_dialog = QDialog(dialog)
            edit_dialog.setWindowTitle("New Scan Profile" if is_new else "Edit Scan Profile")
            edit_dialog.setMinimumWidth(450)
            
            edit_layout = QVBoxLayout(edit_dialog)
            
            # Form layout
            form_layout = QFormLayout()
            form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
            
            # Profile ID (for new profiles only)
            profile_id_edit = QLineEdit()
            if is_new:
                form_layout.addRow("Profile ID:", profile_id_edit)
                profile_id_edit.setPlaceholderText("e.g., custom_scan (no spaces, lowercase)")
            
            # Name
            profile_name_edit = QLineEdit()
            form_layout.addRow("Display Name:", profile_name_edit)
            
            # Description
            profile_desc_edit = QLineEdit()
            form_layout.addRow("Description:", profile_desc_edit)
            
            # Arguments
            profile_args_edit = QLineEdit()
            form_layout.addRow("Arguments:", profile_args_edit)
            profile_args_edit.setPlaceholderText("e.g., -sn -F")
            
            # OS Detection
            profile_os_check = QCheckBox()
            form_layout.addRow("OS Detection:", profile_os_check)
            
            # Port Scanning
            profile_port_check = QCheckBox()
            form_layout.addRow("Port Scanning:", profile_port_check)
            
            # Timeout
            profile_timeout_edit = QLineEdit()
            profile_timeout_edit.setValidator(QIntValidator(30, 600))
            form_layout.addRow("Timeout (seconds):", profile_timeout_edit)
            
            # If editing, populate with existing values
            if not is_new and profile_id:
                profile = self.settings["scan_profiles"]["value"].get(profile_id, {})
                profile_name_edit.setText(profile.get("name", ""))
                profile_desc_edit.setText(profile.get("description", ""))
                profile_args_edit.setText(profile.get("arguments", ""))
                profile_os_check.setChecked(profile.get("os_detection", False))
                profile_port_check.setChecked(profile.get("port_scan", False))
                profile_timeout_edit.setText(str(profile.get("timeout", 300)))
            
            edit_layout.addLayout(form_layout)
            
            # Add dialog buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(edit_dialog.accept)
            button_box.rejected.connect(edit_dialog.reject)
            edit_layout.addWidget(button_box)
            
            # Show dialog and handle result
            if edit_dialog.exec() == QDialog.Accepted:
                # Get values from form
                if is_new:
                    new_id = profile_id_edit.text().strip().lower().replace(" ", "_")
                    if not new_id:
                        QMessageBox.warning(dialog, "Invalid ID", "Profile ID cannot be empty.")
                        return
                    
                    # Check if ID exists
                    if new_id in self.settings["scan_profiles"]["value"]:
                        QMessageBox.warning(dialog, "Profile Exists", f"A profile with ID '{new_id}' already exists.")
                        return
                    
                    profile_id = new_id
                
                # Create updated profile
                updated_profile = {
                    "name": profile_name_edit.text(),
                    "description": profile_desc_edit.text(),
                    "arguments": profile_args_edit.text(),
                    "os_detection": profile_os_check.isChecked(),
                    "port_scan": profile_port_check.isChecked(),
                    "timeout": int(profile_timeout_edit.text() or "300")
                }
                
                # Update settings
                profiles = self.settings["scan_profiles"]["value"].copy()
                profiles[profile_id] = updated_profile
                self.settings["scan_profiles"]["value"] = profiles
                
                # Update scan type choices if needed
                if profile_id not in self.settings["scan_type"]["choices"]:
                    choices = list(self.settings["scan_type"]["choices"])
                    choices.append(profile_id)
                    self.settings["scan_type"]["choices"] = choices
                    
                    # Update the scan type combo box
                    if hasattr(self, "scan_type_combo") and self.scan_type_combo is not None:
                        self.scan_type_combo.clear()
                        self.scan_type_combo.addItems(choices)
                
                # Refresh the table
                refresh_table()
                
                return True
            
            return False
            
        # Handle new profile button
        def on_new_profile():
            edit_profile_dialog(is_new=True)
            
        # Handle edit profile button
        def on_edit_profile():
            selected_indexes = profile_table.selectedIndexes()
            if not selected_indexes:
                return
                
            row = selected_indexes[0].row()
            profile_id = profile_table.item(row, 0).data(Qt.UserRole)
            
            edit_profile_dialog(profile_id, is_new=False)
            
        # Handle delete profile button
        def on_delete_profile():
            selected_indexes = profile_table.selectedIndexes()
            if not selected_indexes:
                return
                
            row = selected_indexes[0].row()
            profile_id = profile_table.item(row, 0).data(Qt.UserRole)
            
            # Check if built-in
            if profile_id in ["quick", "standard", "comprehensive", "stealth", "service"]:
                QMessageBox.warning(dialog, "Cannot Delete", "Built-in profiles cannot be deleted.")
                return
                
            # Confirm deletion
            result = QMessageBox.question(
                dialog, 
                "Confirm Deletion",
                f"Are you sure you want to delete the profile '{profile_id}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Delete the profile
                profiles = self.settings["scan_profiles"]["value"].copy()
                if profile_id in profiles:
                    del profiles[profile_id]
                
                # Update settings
                self.settings["scan_profiles"]["value"] = profiles
                
                # Remove from choices if present
                if profile_id in self.settings["scan_type"]["choices"]:
                    choices = list(self.settings["scan_type"]["choices"])
                    choices.remove(profile_id)
                    self.settings["scan_type"]["choices"] = choices
                    
                    # Update the scan type combo box
                    if hasattr(self, "scan_type_combo") and self.scan_type_combo is not None:
                        self.scan_type_combo.clear()
                        self.scan_type_combo.addItems(choices)
                
                # Refresh the table
                refresh_table()
        
        # Connect button signals
        new_button.clicked.connect(on_new_profile)
        edit_button.clicked.connect(on_edit_profile)
        delete_button.clicked.connect(on_delete_profile)
        
        # Allow double-click to edit
        def on_double_click(item):
            row = item.row()
            profile_id = profile_table.item(row, 0).data(Qt.UserRole)
            edit_profile_dialog(profile_id, is_new=False)
            
        profile_table.itemDoubleClicked.connect(on_double_click)
        
        # Show the dialog
        dialog.exec_()

    def quick_ping_scan(self, network_range):
        """
        Perform a quick ping scan using system commands
        
        This provides an alternative to nmap for fast scanning, especially
        when just checking if hosts are alive.
        
        Args:
            network_range: Network range to scan (e.g., 192.168.1.0/24)
            
        Returns:
            bool: True if scan started successfully, False otherwise
        """
        # Check if already scanning
        if self._is_scanning:
            logger.warning("Scan already in progress")
            return False
            
        # Clean up any previous scan
        self._cleanup_previous_scan()
        
        # Convert network range to list of IPs to ping
        try:
            import ipaddress
            import subprocess
            import threading
            import platform
            from PySide6.QtCore import QObject, Signal, QThread
            
            # Create a worker object with signals for thread-safe UI updates
            class PingScanWorker(QObject):
                progress_updated = Signal(int, int)  # current, total
                status_updated = Signal(str)  # status message
                device_found = Signal(dict)  # device data
                scan_complete = Signal(dict)  # scan results
                
                def __init__(self, ip_list, network_range):
                    super().__init__()
                    self.ip_list = ip_list
                    self.network_range = network_range
                    self.should_stop = False
                    
                def stop(self):
                    self.should_stop = True
                    
                def run(self):
                    self._run_scan()
                    
                def _ping_host(self, ip, index):
                    if self.should_stop:
                        return
                        
                    # Determine ping command based on OS
                    system = platform.system().lower()
                    if system == "windows":
                        ping_cmd = ["ping", "-n", "1", "-w", "500", str(ip)]
                        ping_success = lambda proc: proc.returncode == 0
                    else:  # Linux and macOS
                        ping_cmd = ["ping", "-c", "1", "-W", "1", str(ip)]
                        ping_success = lambda proc: proc.returncode == 0
                        
                    try:
                        # Execute ping command
                        proc = subprocess.run(
                            ping_cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                            timeout=1
                        )
                        
                        # Check result
                        if ping_success(proc):
                            # Log success
                            self.status_updated.emit(f"Host {ip} is up")
                            
                            # Create device data
                            host_data = {
                                "ip_address": str(ip),
                                "scan_source": "ping",
                                "alias": f"Device at {ip}",
                                "tags": ["scanned", "ping"]
                            }
                            
                            # Try to get hostname
                            try:
                                import socket
                                hostname = socket.getfqdn(str(ip))
                                if hostname and hostname != str(ip):
                                    host_data["hostname"] = hostname
                                    host_data["alias"] = hostname
                            except Exception:
                                pass
                                
                            # Emit device found signal
                            self.device_found.emit(host_data)
                        else:
                            # Host is not up, don't add it
                            logger.debug(f"Host {ip} did not respond to ping")
                            
                    except Exception as e:
                        logger.debug(f"Error pinging {ip}: {e}")
                        
                    finally:
                        # Update progress through signal
                        if not self.should_stop:
                            self.progress_updated.emit(index + 1, len(self.ip_list))
                            
                def _run_scan(self):
                    start_time = time.time()
                    alive_hosts = []
                    threads = []
                    max_concurrent = min(50, len(self.ip_list))  # Limit concurrent threads
                    
                    try:
                        for i, ip in enumerate(self.ip_list):
                            if self.should_stop:
                                break
                                
                            # Create and start thread
                            t = threading.Thread(target=self._ping_host, args=(ip, i))
                            t.daemon = True
                            threads.append(t)
                            t.start()
                            
                            # Limit concurrent threads
                            while len([t for t in threads if t.is_alive()]) >= max_concurrent:
                                time.sleep(0.01)
                                
                            # Update status periodically
                            if i % 10 == 0:
                                self.status_updated.emit(f"Scanned {i} of {len(self.ip_list)} addresses...")
                                
                        # Wait for all threads to complete
                        for t in threads:
                            if self.should_stop:
                                break
                            t.join(timeout=0.5)
                            
                        # Scan complete
                        scan_time = time.time() - start_time
                        self.status_updated.emit(f"Scan complete: Found {len(alive_hosts)} devices in {round(scan_time, 1)} seconds")
                        
                        # Store results
                        scan_results = {
                            "network_range": self.network_range,
                            "scan_type": "quick_ping",
                            "total_hosts": len(self.ip_list),
                            "devices_found": len(alive_hosts),
                            "scan_time": scan_time,
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Emit scan complete signal
                        self.scan_complete.emit(scan_results)
                        
                    except Exception as e:
                        logger.error(f"Error during ping scan: {e}")
                        self.status_updated.emit(f"Error during scan: {e}")
            
            # Set scanning flag
            self._is_scanning = True
            
            # Update scanner widget status if available
            if hasattr(self, "scan_button") and self.scan_button:
                self.scan_button.setEnabled(False)
            if hasattr(self, "stop_button") and self.stop_button:
                self.stop_button.setEnabled(True)
            if hasattr(self, "progress_bar") and self.progress_bar:
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(True)
            
            # Clear the scan log and reset progress
            self._scan_log = []
            self.log_message(f"Starting quick ping scan of {network_range}")
            self._scan_results = {}
            
            # Extract IP addresses from network range
            ip_list = []
            try:
                # For CIDR notation like 192.168.1.0/24
                if '/' in network_range:
                    net = ipaddress.ip_network(network_range, strict=False)
                    ip_list = list(net.hosts())
                    
                # For range notation like 192.168.1.1-10
                elif '-' in network_range:
                    parts = network_range.split('-')
                    if len(parts) == 2:
                        start_ip = parts[0].strip()
                        
                        # Check if the second part is a full IP or just the last octet
                        if '.' in parts[1]:
                            end_ip = parts[1].strip()
                        else:
                            # Assume it's just the last octet
                            start_parts = start_ip.split('.')
                            end_ip = f"{start_parts[0]}.{start_parts[1]}.{start_parts[2]}.{parts[1].strip()}"
                            
                        # Generate IP range
                        start = int(ipaddress.IPv4Address(start_ip))
                        end = int(ipaddress.IPv4Address(end_ip))
                        
                        for i in range(start, end + 1):
                            ip_list.append(ipaddress.IPv4Address(i))
                
                # Single IP address
                else:
                    ip_list = [ipaddress.ip_address(network_range)]
            except Exception as e:
                self.log_message(f"Error parsing network range: {e}")
                self._is_scanning = False
                return False
                
            if not ip_list:
                self.log_message("No valid IP addresses to scan")
                self._is_scanning = False
                return False
                
            self.log_message(f"Scanning {len(ip_list)} addresses...")
            
            # Update progress bar
            if hasattr(self, "progress_bar") and self.progress_bar:
                self.progress_bar.setRange(0, len(ip_list))
                self.progress_bar.setValue(0)
            
            # Create worker thread
            self._ping_scan_thread = QThread()
            self._ping_scan_worker = PingScanWorker(ip_list, network_range)
            self._ping_scan_worker.moveToThread(self._ping_scan_thread)
            
            # Connect worker signals
            self._ping_scan_worker.progress_updated.connect(self._on_ping_scan_progress)
            self._ping_scan_worker.status_updated.connect(self.log_message)
            self._ping_scan_worker.device_found.connect(self._on_device_found)
            self._ping_scan_worker.scan_complete.connect(self._on_ping_scan_complete)
            
            # Connect thread signals
            self._ping_scan_thread.started.connect(self._ping_scan_worker.run)
            
            # Start the worker thread
            self._ping_scan_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting ping scan: {e}")
            self._is_scanning = False
            self.log_message(f"Error starting scan: {e}")
            return False
            
    def _on_ping_scan_progress(self, current, total):
        """Handle ping scan progress updates in a thread-safe way"""
        if hasattr(self, "progress_bar") and self.progress_bar:
            self.progress_bar.setValue(current)
            
        if hasattr(self, "status_label") and self.status_label:
            percentage = int((current / total) * 100) if total > 0 else 0
            self.status_label.setText(f"Scanning: {current}/{total} ({percentage}%)")
            
    def _on_ping_scan_complete(self, results):
        """Handle ping scan completion in a thread-safe way"""
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
            self.progress_bar.setValue(self.progress_bar.maximum())
            
        # Clean up
        self._is_scanning = False
        
        # Clean up thread
        if hasattr(self, "_ping_scan_thread") and self._ping_scan_thread.isRunning():
            self._ping_scan_thread.quit()
            self._ping_scan_thread.wait(1000)
            
        # Emit the scan completed signal
        self.scan_completed.emit(results)
            
    def stop_ping_scan(self):
        """Stop the ping scan if it's running"""
        if hasattr(self, "_ping_scan_worker"):
            self._ping_scan_worker.stop()
            self.log_message("Stopping ping scan...")
            return True
        return False

    @safe_action_wrapper
    def on_quick_ping_button_clicked(self):
        """Handle quick ping button click"""
        # Check if scan already in progress
        if self._is_scanning:
            QMessageBox.information(
                self.main_window,
                "Scan in Progress",
                "A scan is already in progress. Please wait for it to complete or click Stop to cancel it."
            )
            return
            
        # Get network range from the UI
        network_range = self.network_range_edit.text()
        if not network_range:
            # If no network range is specified, get it from the selected interface
            network_range = self._get_interface_subnet(self.interface_combo.currentText())
            if not network_range:
                QMessageBox.warning(
                    self.main_window,
                    "Missing Network Range",
                    "Please enter a network range or select a valid interface."
                )
                return
        
        # Start the quick ping scan
        self.quick_ping_scan(network_range)


# Create plugin instance (will be loaded by the plugin manager)
logger.info("Creating Network Scanner plugin instance")
plugin_instance = NetworkScannerPlugin()
logger.info("Network Scanner plugin instance created") 