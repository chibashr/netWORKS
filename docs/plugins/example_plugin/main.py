#!/usr/bin/env python3
# netWORKS - Example Plugin

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from PySide6.QtCore import Qt

class ExamplePlugin:
    """Example plugin showcasing basic netWORKS plugin functionality."""
    
    def __init__(self, plugin_api):
        self.api = plugin_api
        self.api.log("Example plugin initializing...")
        
        # Register with main window when ready
        self.api.on_main_window_ready(self.create_ui)
        
        # Register hooks
        self.register_hooks()
        
        # Device info
        self.current_device = None
        
        self.api.log("Example plugin initialized")
    
    def register_hooks(self):
        """Register event hooks."""
        @self.api.hook("device_select")
        def on_device_select(device):
            self.current_device = device
            self.api.log(f"Device selected: {device['ip'] if device else 'None'}")
            
            # Update UI if it exists
            if hasattr(self, 'device_info') and self.device_info:
                if device:
                    self.device_info.setText(f"Selected Device: {device['ip']}\n"
                                            f"MAC: {device.get('mac', 'Unknown')}\n"
                                            f"Hostname: {device.get('hostname', 'Unknown')}")
                else:
                    self.device_info.setText("No device selected")
        
        @self.api.hook("scan_complete")
        def on_scan_complete(results):
            self.api.log(f"Scan complete: {len(results)} devices found")
            
            # Update UI if it exists
            if hasattr(self, 'scan_log') and self.scan_log:
                self.scan_log.append(f"Scan completed with {len(results)} devices found")
    
    def create_ui(self):
        """Create UI components."""
        self.api.log("Creating UI components...")
        
        # Create left panel
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        
        title = QLabel("Example Plugin")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(title)
        
        # Device info display
        self.device_info = QTextEdit()
        self.device_info.setReadOnly(True)
        self.device_info.setText("No device selected")
        self.device_info.setMaximumHeight(100)
        left_layout.addWidget(self.device_info)
        
        # Action buttons
        ping_button = QPushButton("Ping Device")
        ping_button.clicked.connect(self.ping_device)
        left_layout.addWidget(ping_button)
        
        get_info_button = QPushButton("Get Device Info")
        get_info_button.clicked.connect(self.get_device_info)
        left_layout.addWidget(get_info_button)
        
        left_layout.addStretch()
        
        # Register panel with application
        self.api.register_panel(self.left_panel, "left", "Example Plugin")
        
        # Create bottom panel tab
        self.bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_panel)
        
        bottom_title = QLabel("Example Plugin Log")
        bottom_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(bottom_title)
        
        self.scan_log = QTextEdit()
        self.scan_log.setReadOnly(True)
        bottom_layout.addWidget(self.scan_log)
        
        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(lambda: self.scan_log.clear())
        bottom_layout.addWidget(clear_button)
        
        # Add tab to bottom panel
        self.api.add_tab(self.bottom_panel, "Example Plugin")
        
        # Register menu items
        self.register_menu_items()
        
        self.api.log("UI components created")
    
    def register_menu_items(self):
        """Register menu items for the plugin."""
        # Add to Tools menu
        self.api.register_menu_item(
            label="Ping Selected Device",
            callback=self.ping_device,
            enabled_callback=lambda: self.current_device is not None,
            parent_menu="Tools"
        )
        
        self.api.register_menu_item(
            label="Get Device Info",
            callback=self.get_device_info,
            enabled_callback=lambda: self.current_device is not None,
            parent_menu="Tools"
        )
    
    def ping_device(self):
        """Ping the selected device."""
        if not self.current_device:
            self.api.log("No device selected", level="WARNING")
            return
        
        try:
            ip = self.current_device.get('ip')
            if not ip:
                self.api.log("Device has no IP address", level="WARNING")
                return
                
            self.api.log(f"Pinging device: {ip}")
            self.scan_log.append(f"Pinging device: {ip}")
            
            # In a real plugin, we would perform an actual ping here
            # For this example, we'll just simulate it
            import time
            import random
            
            # Show progress
            self.api.show_progress(True)
            
            # Simulate ping process
            total_pings = 4
            for i in range(total_pings):
                self.api.update_progress(i+1, total_pings)
                time.sleep(0.5)  # Simulate delay
                
                # Simulate response time
                response_time = random.randint(1, 100)
                self.scan_log.append(f"Reply from {ip}: time={response_time}ms")
            
            self.api.show_progress(False)
            self.scan_log.append(f"Ping to {ip} completed")
            
        except Exception as e:
            self.api.log(f"Error pinging device: {str(e)}", level="ERROR")
            self.scan_log.append(f"Error: {str(e)}")
            self.api.show_progress(False)
    
    def get_device_info(self):
        """Get information about the selected device."""
        if not self.current_device:
            self.api.log("No device selected", level="WARNING")
            return
        
        try:
            self.api.log(f"Getting info for device: {self.current_device.get('ip')}")
            self.scan_log.append(f"Device Information:")
            
            # Log all device properties
            for key, value in self.current_device.items():
                self.scan_log.append(f"  {key}: {value}")
                
        except Exception as e:
            self.api.log(f"Error getting device info: {str(e)}", level="ERROR")
            self.scan_log.append(f"Error: {str(e)}")
    
    def cleanup(self):
        """Clean up plugin resources."""
        try:
            # Remove UI components
            if hasattr(self, 'bottom_panel'):
                self.api.remove_tab("Example Plugin")
            
            self.api.log("Example plugin cleanup complete")
        except Exception as e:
            self.api.log(f"Error during cleanup: {str(e)}", level="ERROR")

def init_plugin(plugin_api):
    """Initialize the plugin."""
    return ExamplePlugin(plugin_api) 