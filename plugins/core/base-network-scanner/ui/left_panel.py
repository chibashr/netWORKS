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
    QSizePolicy, QProgressBar, QGridLayout, QDialog, QDialogButtonBox,
    QSpinBox, QCheckBox
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
        
        # Set tooltip on the range input itself instead of using a separate button
        self.range_input.setToolTip(tooltip)
        
        range_layout.addLayout(range_input_layout)
        
        layout.addWidget(range_group)
        
        # Scan type
        scan_type_group = QGroupBox("Scan Type")
        scan_type_layout = QVBoxLayout(scan_type_group)
        scan_type_layout.setContentsMargins(5, 10, 5, 10)
        scan_type_layout.setSpacing(5)
        
        # Create a horizontal layout for scan type selection
        scan_type_selector_layout = QHBoxLayout()
        scan_type_selector_layout.setSpacing(10)  # Add spacing between elements
        
        # Add scan type combo box
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.setMinimumWidth(200)
        scan_type_selector_layout.addWidget(self.scan_type_combo)
        
        # Add configure button for manual scan
        self.configure_manual_btn = QPushButton("Configure")
        self.configure_manual_btn.setToolTip("Configure manual scan settings")
        self.configure_manual_btn.setVisible(False)  # Hidden by default
        self.configure_manual_btn.clicked.connect(self.configure_manual_scan)
        self.configure_manual_btn.setMaximumWidth(100)  # Limit width to prevent layout issues
        scan_type_selector_layout.addWidget(self.configure_manual_btn)
        
        # Add stretch to push elements to the left
        scan_type_selector_layout.addStretch(1)
        
        # Add the selector layout to the main layout
        scan_type_layout.addLayout(scan_type_selector_layout)
        
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
            
            # Scan type combo
            self.scan_type_combo.currentIndexChanged.connect(self.on_scan_type_changed)
            
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
        """Refresh the list of available network interfaces."""
        try:
            self.interface_combo.clear()
            
            # Get interfaces from plugin
            interfaces = self.plugin.get_network_interfaces()
            
            # Filter to only show connected interfaces (with valid IP)
            connected_interfaces = []
            for iface in interfaces:
                ip = iface.get('ip', '')
                
                # Skip interfaces without IP or with loopback IP
                if not ip or ip.startswith('127.'):
                    continue
                
                connected_interfaces.append(iface)
            
            # If no connected interfaces were found, add all interfaces as fallback
            if not connected_interfaces:
                connected_interfaces = interfaces
            
            # Add interfaces to combo box
            for iface in connected_interfaces:
                name = iface.get('name', '')
                ip = iface.get('ip', '')
                alias = iface.get('alias', name)
                
                # Format display text with IP address
                if ip:
                    display_text = f"{alias} ({ip})"
                else:
                    display_text = alias
                
                # Store name and IP as item data
                self.interface_combo.addItem(display_text, (name, ip, alias))
            
            # Add automatic option as the first item
            self.interface_combo.insertItem(0, "Automatic (Best Interface)", ("auto", "", "Automatic"))
            self.interface_combo.setCurrentIndex(0)
            
            # Update IP range based on selection if using interface range
            if hasattr(self, 'interface_range_radio') and self.interface_range_radio.isChecked():
                self.update_range_from_interface()
                
        except Exception as e:
            self.logger.error(f"Error refreshing interfaces: {str(e)}")
    
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
            
        # Enable or disable controls based on selected template
        if template_id == "manual_scan":
            self.logger.debug("Manual scan selected")
            # Show the configure button for manual scan
            self.configure_manual_btn.setVisible(True)
        else:
            # Hide the configure button for other scan types
            self.configure_manual_btn.setVisible(False)

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
        
        # Check if we need to show the Configure button for manual scan
        template_id = self.scan_type_combo.itemData(self.scan_type_combo.currentIndex())
        if template_id == "manual_scan":
            self.configure_manual_btn.setVisible(True)
        
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
            
            # Check if it's a manual scan
            template = self.plugin.config.get("scan_templates", {}).get(scan_type)
            if not template:
                self.logger.error(f"Template not found: {scan_type}")
                self.status_label.setText(f"Error: Template not found: {scan_type}")
                return
                
            kwargs = {}
            
            if template.get("manual", False):
                # For manual scan, use the pre-configured settings
                # If user hasn't configured yet, show the dialog
                if not self.configure_manual_btn.isVisible() or template.get("first_use", True):
                    # First time use or button not visible yet - show dialog
                    scan_params = self.show_manual_scan_dialog(template, interface, ip_range)
                    if not scan_params:
                        # User cancelled
                        return
                    
                    # Use the manually configured settings
                    interface = scan_params.get("interface", interface)
                    ip_range = scan_params.get("range", ip_range)
                    scan_type = scan_params.get("scan_type", scan_type)
                    kwargs = scan_params.get("options", {})
                    
                    # Update template to remove first_use flag
                    template = self.plugin.config.get("scan_templates", {}).get(scan_type, {})
                    template["first_use"] = False
                    self.plugin.update_scan_template(scan_type, template)
                else:
                    # Use existing saved settings
                    for key, value in template.items():
                        if key not in ["name", "description", "manual", "first_use"]:
                            kwargs[key] = value
            
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
            self.configure_manual_btn.setVisible(False)  # Hide config button during scan
            
            # Disable range type radio buttons if present
            if hasattr(self, 'interface_range_radio'):
                self.interface_range_radio.setEnabled(False)
                self.custom_range_radio.setEnabled(False)
            
            # Enable stop button
            self.stop_scan_btn.setEnabled(True)
            
            # Start the scan
            try:
                scan_id = self.plugin.start_scan(interface, ip_range, scan_type, **kwargs)
                self.current_scan_id = scan_id
            except Exception as e:
                self.logger.error(f"Error starting scan: {str(e)}")
                self.scan_error(f"Error starting scan: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error in scan method: {str(e)}")
            self.scan_error(f"Error: {str(e)}")

    def show_manual_scan_dialog(self, template, default_interface, default_range):
        """Show dialog to configure manual scan settings.
        
        Args:
            template: The template with default settings
            default_interface: The default selected interface
            default_range: The default IP range
            
        Returns:
            Dict with scan parameters or None if cancelled
        """
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Manual Scan Configuration")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Interface selection
        interface_group = QGroupBox("Network Interface")
        interface_layout = QVBoxLayout(interface_group)
        
        interface_combo = QComboBox()
        
        # Add the current interfaces
        for i in range(self.interface_combo.count()):
            interface_combo.addItem(self.interface_combo.itemText(i), self.interface_combo.itemData(i))
        
        # Select the current interface
        for i in range(interface_combo.count()):
            item_data = interface_combo.itemData(i)
            if item_data and isinstance(item_data, tuple) and len(item_data) > 0:
                if item_data[0] == default_interface:
                    interface_combo.setCurrentIndex(i)
                    break
        
        interface_layout.addWidget(interface_combo)
        layout.addWidget(interface_group)
        
        # IP Range
        range_group = QGroupBox("IP Range")
        range_layout = QVBoxLayout(range_group)
        
        range_input = QLineEdit(default_range)
        range_layout.addWidget(range_input)
        
        layout.addWidget(range_group)
        
        # Scan settings
        settings_group = QGroupBox("Scan Settings")
        settings_layout = QFormLayout(settings_group)
        
        # Timeout (seconds)
        timeout_spin = QSpinBox()
        timeout_spin.setMinimum(1)
        timeout_spin.setMaximum(30)
        timeout_spin.setValue(template.get("timeout", 2))
        settings_layout.addRow("Timeout (seconds):", timeout_spin)
        
        # Retries
        retries_spin = QSpinBox()
        retries_spin.setMinimum(1)
        retries_spin.setMaximum(10)
        retries_spin.setValue(template.get("retries", 2))
        settings_layout.addRow("Retries:", retries_spin)
        
        # Parallel hosts
        parallel_spin = QSpinBox()
        parallel_spin.setMinimum(1)
        parallel_spin.setMaximum(100)
        parallel_spin.setValue(template.get("parallel", 25))
        settings_layout.addRow("Parallel hosts:", parallel_spin)
        
        # Port scanning
        port_check = QCheckBox("Scan common ports")
        port_check.setChecked("ports" in template)
        settings_layout.addRow("", port_check)
        
        # Port list
        ports_input = QLineEdit()
        default_ports = template.get("ports", [21, 22, 23, 25, 53, 80, 443, 445, 3389])
        if default_ports:
            ports_input.setText(",".join(map(str, default_ports)))
        ports_input.setEnabled(port_check.isChecked())
        settings_layout.addRow("Ports to scan:", ports_input)
        
        # Connect port check to ports input
        port_check.toggled.connect(ports_input.setEnabled)
        
        layout.addWidget(settings_group)
        
        # Add note about scan time
        note_label = QLabel(
            "Note: High parallelism can speed up scans but may cause network congestion or false negatives.\n"
            "For reliable results, keep parallel hosts between 25-50."
        )
        note_label.setWordWrap(True)
        layout.addWidget(note_label)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # Get selected interface
            interface_idx = interface_combo.currentIndex()
            interface_data = interface_combo.itemData(interface_idx)
            interface = interface_data[0] if interface_data else default_interface
            
            # Get entered IP range
            ip_range = range_input.text().strip()
            if not ip_range:
                ip_range = default_range
            
            # Get scan options
            options = {
                "timeout": timeout_spin.value(),
                "retries": retries_spin.value(),
                "parallel": parallel_spin.value()
            }
            
            # Add ports if enabled
            if port_check.isChecked() and ports_input.text().strip():
                try:
                    port_list = [int(p.strip()) for p in ports_input.text().split(",") if p.strip()]
                    if port_list:
                        options["ports"] = port_list
                except ValueError:
                    self.plugin.api.log("Invalid port format. Using default ports.", level="WARNING")
                    options["ports"] = default_ports
            
            return {
                "interface": interface,
                "range": ip_range,
                "scan_type": "manual_scan",
                "options": options
            }
        
        return None

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

    def configure_manual_scan(self):
        """Open the manual scan configuration dialog."""
        # Get current interface
        interface_index = self.interface_combo.currentIndex()
        if interface_index < 0:
            self.plugin.api.log("No interface selected", level="ERROR")
            return
            
        interface_data = self.interface_combo.itemData(interface_index)
        if not interface_data or not isinstance(interface_data, tuple) or len(interface_data) < 1:
            self.logger.error("Invalid interface data")
            return
            
        interface = interface_data[0]
        
        # Get current IP range
        ip_range = self.range_input.text().strip()
        
        # Get manual scan template
        template = self.plugin.config.get("scan_templates", {}).get("manual_scan", {})
        
        # Show the dialog
        scan_params = self.show_manual_scan_dialog(template, interface, ip_range)
        
        # Store the configuration for later use when the scan starts
        if scan_params:
            # Save the configuration in the template for manual_scan
            options = scan_params.get("options", {})
            template.update(options)
            self.plugin.update_scan_template("manual_scan", template)
            
            # Show confirmation to user
            self.plugin.api.log("Manual scan settings saved")
            self.status_label.setText("Manual scan configured")
            
            # If the interface or range changed, update UI
            if scan_params["interface"] != interface:
                # Find and select the interface in the combo box
                for i in range(self.interface_combo.count()):
                    item_data = self.interface_combo.itemData(i)
                    if item_data and isinstance(item_data, tuple) and item_data[0] == scan_params["interface"]:
                        self.interface_combo.setCurrentIndex(i)
                        break
            
            # Update the range input if it changed
            if scan_params["range"] != ip_range:
                # Switch to custom range mode if using interface range
                if self.interface_range_radio.isChecked():
                    self.custom_range_radio.setChecked(True)
                self.range_input.setText(scan_params["range"]) 