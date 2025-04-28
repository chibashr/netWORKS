#!/usr/bin/env python3
# Network Scanner - Right Panel UI

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QSpinBox,
    QGroupBox, QCheckBox, QTextEdit, QListWidget, QListWidgetItem,
    QSizePolicy, QSpacerItem, QTabWidget, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, Slot

class ScanSettingsPanel(QWidget):
    """Right panel UI component for configuring custom scan settings."""
    
    def __init__(self, plugin):
        """Initialize the scan settings panel.
        
        Args:
            plugin: The parent plugin instance
        """
        super().__init__()
        self.plugin = plugin
        self.logger = logging.getLogger(__name__)
        
        self.init_ui()
        self.connect_signals()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the UI elements."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Custom Scan Settings")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Basic settings (no tabs needed since we're removing Templates tab)
        basic_widget = QWidget()
        basic_layout = QVBoxLayout(basic_widget)
        
        # Timeout settings
        timeout_group = QGroupBox("Scan Timing")
        timeout_layout = QFormLayout(timeout_group)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(1)
        self.timeout_spin.setMaximum(30)
        self.timeout_spin.setValue(1)
        timeout_layout.addRow("Timeout (seconds):", self.timeout_spin)
        
        self.retries_spin = QSpinBox()
        self.retries_spin.setMinimum(1)
        self.retries_spin.setMaximum(10)
        self.retries_spin.setValue(1)
        timeout_layout.addRow("Retries:", self.retries_spin)
        
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setMinimum(1)
        self.parallel_spin.setMaximum(100)
        self.parallel_spin.setValue(50)
        timeout_layout.addRow("Parallel hosts:", self.parallel_spin)
        
        basic_layout.addWidget(timeout_group)
        
        # Port settings
        port_group = QGroupBox("Port Settings")
        port_layout = QVBoxLayout(port_group)
        
        self.port_check = QCheckBox("Scan ports")
        port_layout.addWidget(self.port_check)
        
        port_form = QFormLayout()
        self.ports_input = QLineEdit()
        self.ports_input.setPlaceholderText("80,443,22,3389")
        self.ports_input.setEnabled(False)  # Disabled by default
        port_form.addRow("Ports to scan:", self.ports_input)
        port_layout.addLayout(port_form)
        
        basic_layout.addWidget(port_group)
        
        # Add a spacer
        basic_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Add basic widget to layout
        layout.addWidget(basic_widget)
        
        # Add apply button at the bottom with improved styling
        self.apply_btn = QPushButton("Apply Settings")
        self.apply_btn.setMinimumHeight(36)
        self.apply_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.apply_btn)
    
    def connect_signals(self):
        """Connect UI signals to handlers."""
        # Checkboxes
        self.port_check.toggled.connect(self.ports_input.setEnabled)
        
        # Buttons
        self.apply_btn.clicked.connect(self.apply_settings)
    
    def load_settings(self):
        """Load settings from plugin configuration."""
        # Load basic scan settings
        timeout = self.plugin.config.get("timeout", 1)
        retries = self.plugin.config.get("retries", 1)
        parallel = self.plugin.config.get("parallel", 50)
        
        self.timeout_spin.setValue(timeout)
        self.retries_spin.setValue(retries)
        self.parallel_spin.setValue(parallel)
        
        # Load port settings
        ports = self.plugin.config.get("ports", [])
        if ports:
            self.port_check.setChecked(True)
            self.ports_input.setEnabled(True)
            self.ports_input.setText(",".join(map(str, ports)))
    
    def apply_settings(self):
        """Apply the current settings to the plugin configuration."""
        try:
            # Save basic scan settings
            self.plugin.config["timeout"] = self.timeout_spin.value()
            self.plugin.config["retries"] = self.retries_spin.value()
            self.plugin.config["parallel"] = self.parallel_spin.value()
            
            # Save port settings
            if self.port_check.isChecked() and self.ports_input.text():
                try:
                    ports = [int(p.strip()) for p in self.ports_input.text().split(",") if p.strip()]
                    self.plugin.config["ports"] = ports
                except ValueError:
                    self.plugin.api.log("Invalid port format. Use comma-separated numbers.", level="ERROR")
            else:
                if "ports" in self.plugin.config:
                    del self.plugin.config["ports"]
            
            # Save configuration
            self.plugin._save_config()
            
            self.plugin.api.log("Scan settings saved successfully")
        except Exception as e:
            self.plugin.api.log(f"Error saving settings: {str(e)}", level="ERROR")
    
    def show_device(self, device):
        """Show device details in the panel.
        
        Args:
            device: Device information dictionary
        """
        # This is needed for compatibility with the main panel
        # In the current implementation, this panel doesn't show device details,
        # but the method is called from the main panel when a device is selected
        self.logger.debug(f"Device selected: {device.get('ip', 'Unknown')}")
        
        # Could be implemented in the future to show device-specific settings
        pass
    
    def refresh(self):
        """Refresh the panel data."""
        try:
            self.load_settings()
        except Exception as e:
            self.logger.error(f"Error refreshing settings panel: {str(e)}") 