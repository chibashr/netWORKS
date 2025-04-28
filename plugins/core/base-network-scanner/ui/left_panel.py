#!/usr/bin/env python3
# Network Scanner - Left Panel UI

import logging
import threading
import ipaddress
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox, QLineEdit,
    QGroupBox, QRadioButton, QButtonGroup, QSpacerItem,
    QSizePolicy, QProgressBar, QGridLayout
)
from PySide6.QtCore import Qt, Signal, Slot, QThread

class ScanControlPanel(QWidget):
    """Left panel UI component for controlling network scans."""
    
    def __init__(self, plugin):
        """Initialize the scan control panel.
        
        Args:
            plugin: The parent plugin instance
        """
        super().__init__()
        self.plugin = plugin
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Creating ScanControlPanel in thread: {QThread.currentThread()}")
        
        self.init_ui()
        self.connect_signals()
        self.refresh_interfaces()
        self.refresh_templates()
        
        # Disable scan button if a scan is already in progress
        try:
            if hasattr(self.plugin, 'scanner') and self.plugin.scanner is not None:
                # Check is_scanning property safely - this approach works with both PyQt5 and PySide6
                scanning = self.plugin.scanner.is_scanning
                if scanning:
                    self.start_scan_btn.setEnabled(False)
                    self.stop_scan_btn.setEnabled(True)
                    self.logger.debug("Scan in progress detected, disabling start button")
        except Exception as e:
            self.logger.warning(f"Error checking scan status: {str(e)}")
    
    def init_ui(self):
        """Initialize the UI elements."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Network Scanner")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Interface selection
        interface_group = QGroupBox("Network Interface")
        interface_layout = QVBoxLayout(interface_group)
        interface_layout.setContentsMargins(5, 10, 5, 10)
        interface_layout.setSpacing(5)
        
        self.interface_combo = QComboBox()
        self.interface_combo.setMinimumWidth(200)
        interface_layout.addWidget(self.interface_combo)
        
        self.refresh_interfaces_btn = QPushButton("Refresh Interfaces")
        interface_layout.addWidget(self.refresh_interfaces_btn)
        
        layout.addWidget(interface_group)
        
        # IP Range - with range type selector
        range_group = QGroupBox("IP Range")
        range_layout = QVBoxLayout(range_group)
        range_layout.setContentsMargins(5, 10, 5, 10)
        range_layout.setSpacing(5)
        
        # Add radio buttons for range type selection
        range_type_layout = QHBoxLayout()
        
        self.range_type_group = QButtonGroup(self)
        
        self.interface_range_radio = QRadioButton("Interface Range")
        self.custom_range_radio = QRadioButton("Custom Range")
        
        self.range_type_group.addButton(self.interface_range_radio)
        self.range_type_group.addButton(self.custom_range_radio)
        
        # Select interface range by default
        self.interface_range_radio.setChecked(True)
        
        range_type_layout.addWidget(self.interface_range_radio)
        range_type_layout.addWidget(self.custom_range_radio)
        range_type_layout.addStretch()
        
        range_layout.addLayout(range_type_layout)
        
        # Range input with help button
        range_input_layout = QHBoxLayout()
        
        self.range_input = QLineEdit()
        self.range_input.setPlaceholderText("192.168.1.1-254 or 10.0.0.0/24")
        range_input_layout.addWidget(self.range_input)
        
        tooltip = ("Examples:<br>"
                  "• 192.168.1.1-254<br>"
                  "• 10.0.0.0/24<br>"
                  "• 172.16.1.1,172.16.1.5-10")
        
        help_btn = QPushButton("?")
        help_btn.setMaximumWidth(16)  # Make the button smaller
        help_btn.setMaximumHeight(16)
        help_btn.setStyleSheet("font-size: 8pt; padding: 0px;")  # Reduce padding and font size
        help_btn.setToolTip(tooltip)
        range_input_layout.addWidget(help_btn)
        
        range_layout.addLayout(range_input_layout)
        
        layout.addWidget(range_group)
        
        # Scan type
        scan_type_group = QGroupBox("Scan Type")
        scan_type_layout = QVBoxLayout(scan_type_group)
        scan_type_layout.setContentsMargins(5, 10, 5, 10)
        scan_type_layout.setSpacing(5)
        
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.setMinimumWidth(200)
        scan_type_layout.addWidget(self.scan_type_combo)
        
        layout.addWidget(scan_type_group)
        
        # Progress indicator
        progress_group = QGroupBox("Scan Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(5, 10, 5, 10)
        progress_layout.setSpacing(5)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.start_scan_btn = QPushButton("Start Scan")
        self.start_scan_btn.setMinimumHeight(40)
        self.start_scan_btn.setStyleSheet("font-weight: bold;")
        button_layout.addWidget(self.start_scan_btn)
        
        self.stop_scan_btn = QPushButton("Stop Scan")
        self.stop_scan_btn.setMinimumHeight(40)
        self.stop_scan_btn.setEnabled(False)
        button_layout.addWidget(self.stop_scan_btn)
        
        layout.addLayout(button_layout)
        
        # Add spacer at the bottom
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Initialize with default values
        self.range_input.setText(self.plugin.config.get("default_range", "192.168.1.1-254"))
    
    def connect_signals(self):
        """Connect the UI signals to handlers"""
        self.logger.debug(f"Connecting ScanControlPanel signals in thread: {QThread.currentThread()}")
        
        try:
            # Button signals
            self.refresh_interfaces_btn.clicked.connect(self.refresh_interfaces)
            self.start_scan_btn.clicked.connect(self.scan)
            self.stop_scan_btn.clicked.connect(self.stop_scan)
            
            # Plugin signals
            self.plugin.scan_started.connect(self.on_scan_started)
            self.plugin.scan_finished.connect(self.on_scan_finished)
            self.plugin.device_found.connect(self.on_device_found)
            
            # Range type radio buttons
            self.interface_range_radio.toggled.connect(self.on_range_type_changed)
            self.custom_range_radio.toggled.connect(self.on_range_type_changed)
            
            self.logger.debug("ScanControlPanel signals connected successfully")
        except Exception as e:
            self.logger.error(f"Error connecting signals: {str(e)}", exc_info=True)
    
    def on_range_type_changed(self, checked):
        """Handle change of range type selection."""
        if checked:
            if self.sender() == self.interface_range_radio:
                # Interface range selected - update from current interface
                # Force update regardless of current state
                self.force_update_range_from_interface()
                # Disable manual editing
                self.range_input.setReadOnly(True)
                self.range_input.setStyleSheet("background-color: #f0f0f0;")
            else:
                # Custom range selected - enable manual editing
                self.range_input.setReadOnly(False)
                self.range_input.setStyleSheet("")
    
    def force_update_range_from_interface(self):
        """Force update the IP range based on the selected interface, ignoring the current range type."""
        try:
            index = self.interface_combo.currentIndex()
            if index < 0:
                return
            
            # Get interface data (name, ip)
            interface_data = self.interface_combo.itemData(index)
            if not interface_data or not isinstance(interface_data, tuple):
                return
                
            # Data structure is (name, ip, alias)
            if len(interface_data) >= 2:
                name, ip = interface_data[0], interface_data[1]
            else:
                self.logger.warning(f"Interface data format unexpected: {interface_data}")
                return
            
            if not ip or ip == "127.0.0.1":
                # Use default range for loopback or no IP
                default_range = self.plugin.config.get("default_range", "192.168.1.1-254")
                self.range_input.setText(default_range)
                return
            
            # Calculate subnet based on IP
            try:
                # Try to determine subnet mask by checking if it's a private network
                # Most common private networks
                if ip.startswith("192.168."):
                    # 192.168.x.y - Class C private (255.255.255.0)
                    prefix_len = 24
                    ip_obj = ipaddress.IPv4Address(ip)
                    network = ipaddress.IPv4Network(f"{ip}/{prefix_len}", strict=False)
                    subnet_range = f"{network.network_address + 1}-{network.broadcast_address - 1}"
                elif ip.startswith("10."):
                    # 10.x.y.z - Class A private (255.0.0.0)
                    # Use smaller range for scanning efficiency
                    ip_parts = ip.split('.')
                    subnet_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1-254"
                elif ip.startswith("172."):
                    # 172.16-31.x.y - Class B private (255.240.0.0)
                    # Use smaller range for scanning efficiency
                    ip_parts = ip.split('.')
                    subnet_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1-254"
                else:
                    # For other IPs, just scan the /24 subnet
                    ip_parts = ip.split('.')
                    subnet_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1-254"
                
                self.range_input.setText(subnet_range)
                self.logger.debug(f"Updated range to {subnet_range} based on interface IP {ip}")
            except Exception as e:
                self.logger.error(f"Error calculating subnet: {str(e)}")
                # Fall back to default range
                default_range = self.plugin.config.get("default_range", "192.168.1.1-254")
                self.range_input.setText(default_range)
                
        except Exception as e:
            self.logger.error(f"Error forcing update range from interface: {str(e)}", exc_info=True)
    
    def refresh_interfaces(self):
        """Refresh the list of network interfaces."""
        try:
            # Remember the previously selected interface
            prev_index = self.interface_combo.currentIndex()
            prev_data = self.interface_combo.itemData(prev_index) if prev_index >= 0 else None
            
            self.interface_combo.clear()
            
            interfaces = self.plugin.get_network_interfaces()
            
            for interface in interfaces:
                name = interface.get("name", "")
                ip = interface.get("ip", "")
                alias = interface.get("alias", name)
                
                # Format display name to always show status
                if ip:
                    display_name = f"{alias} ({ip})"
                else:
                    display_name = f"{alias} (disconnected)"
                
                # Store interface info in the item data
                self.interface_combo.addItem(display_name, (name, ip, alias))
            
            # Try to select the previously selected interface if it exists
            found_previous = False
            if prev_data and isinstance(prev_data, tuple) and len(prev_data) >= 1:
                for i in range(self.interface_combo.count()):
                    curr_data = self.interface_combo.itemData(i)
                    if curr_data and isinstance(curr_data, tuple) and len(curr_data) >= 1 and curr_data[0] == prev_data[0]:
                        self.interface_combo.setCurrentIndex(i)
                        found_previous = True
                        break
            
            # If no interface is selected, select the first one
            if not found_previous and self.interface_combo.currentIndex() < 0 and self.interface_combo.count() > 0:
                self.interface_combo.setCurrentIndex(0)
            
            # Update range input with subnet of selected interface if interface range is selected
            if hasattr(self, 'interface_range_radio') and self.interface_range_radio.isChecked():
                self.force_update_range_from_interface()
            
            # Connect change signal (after populating to avoid triggering on each item)
            try:
                self.interface_combo.currentIndexChanged.disconnect(self.update_range_from_interface)
            except Exception:
                # It's fine if it fails because the signal wasn't connected yet
                pass
                
            self.interface_combo.currentIndexChanged.connect(self.update_range_from_interface)
            
        except Exception as e:
            self.logger.error(f"Error refreshing interfaces: {str(e)}", exc_info=True)
    
    def update_range_from_interface(self):
        """Update the IP range based on the selected interface."""
        try:
            # Only update range if interface range is selected
            if hasattr(self, 'custom_range_radio') and self.custom_range_radio.isChecked():
                return
                
            index = self.interface_combo.currentIndex()
            if index < 0:
                return
            
            # Get interface data (name, ip)
            interface_data = self.interface_combo.itemData(index)
            if not interface_data or not isinstance(interface_data, tuple):
                return
            
            # Data structure is (name, ip, alias)
            if len(interface_data) >= 2:
                name, ip = interface_data[0], interface_data[1]
            else:
                self.logger.warning(f"Interface data format unexpected: {interface_data}")
                return
            
            if not ip or ip == "127.0.0.1":
                # Use default range for loopback or no IP
                default_range = self.plugin.config.get("default_range", "192.168.1.1-254")
                self.range_input.setText(default_range)
                return
            
            # Calculate subnet based on IP
            try:
                # Try to determine subnet mask by checking if it's a private network
                # Most common private networks
                if ip.startswith("192.168."):
                    # 192.168.x.y - Class C private (255.255.255.0)
                    prefix_len = 24
                    ip_obj = ipaddress.IPv4Address(ip)
                    network = ipaddress.IPv4Network(f"{ip}/{prefix_len}", strict=False)
                    subnet_range = f"{network.network_address + 1}-{network.broadcast_address - 1}"
                elif ip.startswith("10."):
                    # 10.x.y.z - Class A private (255.0.0.0)
                    # Use smaller range for scanning efficiency
                    ip_parts = ip.split('.')
                    subnet_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1-254"
                elif ip.startswith("172."):
                    # 172.16-31.x.y - Class B private (255.240.0.0)
                    # Use smaller range for scanning efficiency
                    ip_parts = ip.split('.')
                    subnet_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1-254"
                else:
                    # For other IPs, just scan the /24 subnet
                    ip_parts = ip.split('.')
                    subnet_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1-254"
                
                self.range_input.setText(subnet_range)
                self.logger.debug(f"Updated range to {subnet_range} based on interface IP {ip}")
            except Exception as e:
                self.logger.error(f"Error calculating subnet: {str(e)}")
                # Fall back to default range
                default_range = self.plugin.config.get("default_range", "192.168.1.1-254")
                self.range_input.setText(default_range)
                
        except Exception as e:
            self.logger.error(f"Error updating range from interface: {str(e)}", exc_info=True)
    
    def refresh_templates(self):
        """Refresh the list of scan templates."""
        try:
            self.scan_type_combo.clear()
            
            templates = self.plugin.get_scan_templates()
            
            for template_id, template in templates.items():
                name = template.get("name", template_id)
                description = template.get("description", "")
                display_name = f"{name} - {description}" if description else name
                self.scan_type_combo.addItem(display_name, template_id)
        except Exception as e:
            self.logger.error(f"Error refreshing templates: {str(e)}")
    
    def on_scan_type_changed(self, index):
        """Handle scan type selection change."""
        template_id = self.scan_type_combo.itemData(index)
        if not template_id:
            return
        
        template = self.plugin.config.get("scan_templates", {}).get(template_id)
        if not template:
            return
    
    def on_start_scan(self):
        """Handle start scan button click."""
        # Get selected interface
        interface_index = self.interface_combo.currentIndex()
        if interface_index < 0:
            self.plugin.api.log("No interface selected", level="ERROR")
            return
        
        interface = self.interface_combo.itemData(interface_index)
        
        # Get IP range
        ip_range = self.range_input.text().strip()
        if not ip_range:
            self.plugin.api.log("No IP range specified", level="ERROR")
            return
        
        # Get scan type
        template_index = self.scan_type_combo.currentIndex()
        if template_index < 0:
            self.plugin.api.log("No scan type selected", level="ERROR")
            return
        
        scan_type = self.scan_type_combo.itemData(template_index)
        
        # Start the scan
        try:
            scan_id = self.plugin.start_scan(interface, ip_range, scan_type)
            self.plugin.api.log(f"Started scan {scan_id}")
        except Exception as e:
            self.plugin.api.log(f"Error starting scan: {str(e)}", level="ERROR")
    
    def on_stop_scan(self):
        """Handle stop scan button click."""
        # Get current scan ID from progress
        current_scan_id = getattr(self, "current_scan_id", None)
        if not current_scan_id:
            return
        
        # Stop the scan
        try:
            if self.plugin.scanner.stop_scan(current_scan_id):
                self.plugin.api.log(f"Stopped scan {current_scan_id}")
        except Exception as e:
            self.plugin.api.log(f"Error stopping scan: {str(e)}", level="ERROR")
    
    @Slot(dict)
    def on_scan_started(self, scan_config):
        """Handle scan started signal."""
        scan_id = scan_config.get("id")
        self.current_scan_id = scan_id
        
        # Update UI
        self.progress_bar.setValue(0)
        self.status_label.setText("Scanning...")
        
        # Enable/disable buttons
        self.start_scan_btn.setEnabled(False)
        self.stop_scan_btn.setEnabled(True)
    
    @Slot(dict)
    def on_scan_finished(self, scan_result):
        """Handle scan finished signal."""
        # Update UI
        status = scan_result.get("status", "unknown")
        devices_found = scan_result.get("devices_found", 0)
        
        if status == "completed":
            self.progress_bar.setValue(100)
            self.status_label.setText(f"Completed: Found {devices_found} devices")
        elif status == "stopped":
            self.status_label.setText(f"Stopped: Found {devices_found} devices")
        elif status == "error":
            error = scan_result.get("error", "Unknown error")
            self.status_label.setText(f"Error: {error}")
        
        # Enable/disable buttons
        self.start_scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.interface_combo.setEnabled(True)
        self.range_input.setEnabled(True)
        self.scan_type_combo.setEnabled(True)
        
        # Also re-enable range type selection
        if hasattr(self, 'interface_range_radio'):
            self.interface_range_radio.setEnabled(True)
            self.custom_range_radio.setEnabled(True)
            
            # Ensure range input state is consistent with selection
            if self.interface_range_radio.isChecked():
                self.range_input.setReadOnly(True)
                self.range_input.setStyleSheet("background-color: #f0f0f0;")
            else:
                self.range_input.setReadOnly(False)
                self.range_input.setStyleSheet("")
        
        # Clear current scan ID
        self.current_scan_id = None
    
    @Slot(dict)
    def on_device_found(self, device):
        """Handle device found signal."""
        # Update progress if we have a total count
        scan_id = device.get("scan_id")
        if scan_id != self.current_scan_id:
            return
        
        # Get current scan
        scan = self.plugin.get_scan_by_id(scan_id)
        if not scan:
            return
        
        devices_found = scan.get("devices_found", 0)
        total_devices = scan.get("total_devices", 0)
        
        if total_devices > 0:
            progress = min(int((devices_found / total_devices) * 100), 100)
            self.progress_bar.setValue(progress)
            self.status_label.setText(f"Scanning: Found {devices_found} devices")

    def scan(self, ip_range=None):
        """Start a scan with the current configuration.
        
        Args:
            ip_range: Optional IP range to scan (defaults to input field value)
        """
        self.logger.debug(f"Scan method called in thread: {QThread.currentThread()}")
        
        try:
            # Get selected interface
            interface_index = self.interface_combo.currentIndex()
            if interface_index < 0:
                self.logger.error("No interface selected")
                self.status_label.setText("Error: No interface selected")
                return
            
            # Get interface data (name, ip)
            interface_data = self.interface_combo.itemData(interface_index)
            if not interface_data or not isinstance(interface_data, tuple) or len(interface_data) < 1:
                self.logger.error("Invalid interface data")
                self.status_label.setText("Error: Invalid interface data")
                return
                
            # Extract interface name from the tuple
            interface = interface_data[0]
            
            # Get IP range from the input field
            if ip_range is None or ip_range == "":
                ip_range = self.range_input.text().strip()
            
            # If range is empty, update it based on selection
            if not ip_range:
                # Update based on range type
                if hasattr(self, 'interface_range_radio') and self.interface_range_radio.isChecked():
                    self.force_update_range_from_interface()
                    ip_range = self.range_input.text().strip()
                
                # Still no range? Use default
                if not ip_range:
                    ip_range = self.plugin.config.get("default_range", "192.168.1.1-254")
                    self.range_input.setText(ip_range)
                
                self.logger.info(f"No IP range specified, using: {ip_range}")
            
            # Get scan type
            template_index = self.scan_type_combo.currentIndex()
            if template_index < 0:
                self.logger.error("No scan type selected")
                self.status_label.setText("Error: No scan type selected")
                return
            
            scan_type = self.scan_type_combo.itemData(template_index)
            
            # Start the scan
            self.logger.info(f"Starting scan on interface {interface} with range {ip_range}, type {scan_type}")
            
            # Update UI before starting scan
            self.progress_bar.setValue(0)
            self.status_label.setText("Starting scan...")
            
            # Disable UI elements
            self.start_scan_btn.setEnabled(False)
            self.interface_combo.setEnabled(False)
            self.range_input.setEnabled(False)
            self.scan_type_combo.setEnabled(False)
            self.stop_scan_btn.setEnabled(True)
            
            # Also disable range type selection
            if hasattr(self, 'interface_range_radio'):
                self.interface_range_radio.setEnabled(False)
                self.custom_range_radio.setEnabled(False)
            
            # Start the scan (this will create a background thread)
            scan_id = self.plugin.start_scan(interface, ip_range, scan_type)
            self.logger.debug(f"Scan started with ID: {scan_id}")
            self.current_scan_id = scan_id
            
        except Exception as e:
            self.logger.error(f"Error starting scan: {str(e)}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            # Re-enable UI elements
            self.start_scan_btn.setEnabled(True)
            self.interface_combo.setEnabled(True)
            self.range_input.setEnabled(True)
            self.scan_type_combo.setEnabled(True)
            self.stop_scan_btn.setEnabled(False)
            
            # Also re-enable range type selection
            if hasattr(self, 'interface_range_radio'):
                self.interface_range_radio.setEnabled(True)
                self.custom_range_radio.setEnabled(True)

    def stop_scan(self):
        """Stop the current network scan."""
        self.logger.debug(f"Stop scan button clicked in thread: {QThread.currentThread()}")
        
        try:
            # Get current scan ID
            if not hasattr(self, 'current_scan_id') or not self.current_scan_id:
                self.logger.error("No current scan to stop")
                self.status_label.setText("No current scan to stop")
                return
            
            # Use the scanner's stop_scan method with the current scan ID
            if hasattr(self.plugin, 'scanner') and self.plugin.scanner:
                self.plugin.scanner.stop_scan(self.current_scan_id)
                self.logger.info(f"Scan {self.current_scan_id} stopped by user")
            else:
                self.logger.error("Scanner not available")
                self.status_label.setText("Error: Scanner not available")
                return
            
            # Re-enable UI elements
            self.start_scan_btn.setEnabled(True)
            self.stop_scan_btn.setEnabled(False)
            self.interface_combo.setEnabled(True)
            self.range_input.setEnabled(True)
            self.scan_type_combo.setEnabled(True)
            
            # Also re-enable range type selection
            if hasattr(self, 'interface_range_radio'):
                self.interface_range_radio.setEnabled(True)
                self.custom_range_radio.setEnabled(True)
                
                # Ensure range input state is consistent with selection
                if self.interface_range_radio.isChecked():
                    self.range_input.setReadOnly(True)
                    self.range_input.setStyleSheet("background-color: #f0f0f0;")
                else:
                    self.range_input.setReadOnly(False)
                    self.range_input.setStyleSheet("")
            
            # Update status
            self.status_label.setText("Scan stopped")
            
            # Clear current scan ID
            self.current_scan_id = None
        except Exception as e:
            self.logger.error(f"Error stopping scan: {str(e)}", exc_info=True)
            self.status_label.setText(f"Error stopping scan: {str(e)}")
            
            # Re-enable UI elements in case of error
            self.start_scan_btn.setEnabled(True)
            self.stop_scan_btn.setEnabled(False)
            self.interface_combo.setEnabled(True)
            self.range_input.setEnabled(True)
            self.scan_type_combo.setEnabled(True)
            
            # Also re-enable range type selection
            if hasattr(self, 'interface_range_radio'):
                self.interface_range_radio.setEnabled(True)
                self.custom_range_radio.setEnabled(True)

    def update_scan_progress(self, current, total, status_text=None):
        """Update the scan progress UI
        
        Args:
            current: Current progress value
            total: Maximum progress value
            status_text: Optional text to display in status label
        """
        self.logger.debug(f"Updating scan progress in thread: {QThread.currentThread()}, progress: {current}/{total}")
        
        # Calculate percentage
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        else:
            self.progress_bar.setValue(0)
            
        # Update status text if provided
        if status_text:
            self.status_label.setText(status_text)
            
    def scan_completed(self, result_data=None):
        """Handle scan completion
        
        Args:
            result_data: Optional data from scan results
        """
        self.logger.debug(f"Scan completed signal received in thread: {QThread.currentThread()}")
        
        # Re-enable UI elements
        self.start_scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.interface_combo.setEnabled(True)
        self.range_input.setEnabled(True)
        self.scan_type_combo.setEnabled(True)
        
        # Also re-enable range type selection
        if hasattr(self, 'interface_range_radio'):
            self.interface_range_radio.setEnabled(True)
            self.custom_range_radio.setEnabled(True)
            
            # Ensure range input state is consistent with selection
            if self.interface_range_radio.isChecked():
                self.range_input.setReadOnly(True)
                self.range_input.setStyleSheet("background-color: #f0f0f0;")
            else:
                self.range_input.setReadOnly(False)
                self.range_input.setStyleSheet("")
        
        # Update progress and status
        self.progress_bar.setValue(100)
        self.status_label.setText("Scan completed")
        
        # Handle result data if provided
        if result_data:
            if "error" in result_data:
                self.progress_bar.setValue(0)
                self.status_label.setText(f"Error: {result_data['error']}")
        
    def scan_error(self, error_message):
        """Handle scan error
        
        Args:
            error_message: Error message to display
        """
        self.logger.debug(f"Scan error received in thread: {QThread.currentThread()}, error: {error_message}")
        
        # Re-enable UI elements
        self.start_scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.interface_combo.setEnabled(True)
        self.range_input.setEnabled(True)
        self.scan_type_combo.setEnabled(True)
        
        # Also re-enable range type selection
        if hasattr(self, 'interface_range_radio'):
            self.interface_range_radio.setEnabled(True)
            self.custom_range_radio.setEnabled(True)
            
            # Ensure range input state is consistent with selection
            if self.interface_range_radio.isChecked():
                self.range_input.setReadOnly(True)
                self.range_input.setStyleSheet("background-color: #f0f0f0;")
            else:
                self.range_input.setReadOnly(False)
                self.range_input.setStyleSheet("")
        
        # Update progress and status
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Error: {error_message}")

    def add_device(self, device):
        """Add a device to the network map.
        
        Args:
            device: Dictionary containing device information
        """
        # Update the status to show new device found
        try:
            device_ip = device.get('ip', 'Unknown')
            self.status_label.setText(f"Device found: {device_ip}")
            
            # If this method is called, it means a device was found during scanning
            # We don't need to display it in this panel, but we'll update the status
            self.logger.debug(f"Device found during scan: {device_ip}")
        except Exception as e:
            self.logger.error(f"Error handling new device: {str(e)}") 