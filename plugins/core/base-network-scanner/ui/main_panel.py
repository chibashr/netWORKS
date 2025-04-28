import logging
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout, 
                             QLabel, QPushButton, QSplitter, QVBoxLayout, 
                             QWidget)

from .left_panel import ScanControlPanel
from .right_panel import ScanSettingsPanel
from .bottom_panel import ScanHistoryPanel

class NetworkScannerMainPanel(QWidget):
    """Main panel for the Network Scanner plugin."""
    
    def __init__(self, plugin):
        """Initialize the main panel.
        
        Args:
            plugin: Reference to the plugin instance
        """
        super().__init__()
        self.plugin = plugin
        self.logger = logging.getLogger("plugin.base_network_scanner.ui")
        self.active_scan_id = None
        
        self._init_ui()
        self._connect_signals()
        
        self.logger.debug("Network Scanner main panel initialized")
    
    def _init_ui(self):
        """Initialize the UI components."""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Control panel
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Main splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (Network map/topology)
        self.left_panel = ScanControlPanel(self.plugin)
        self.main_splitter.addWidget(self.left_panel)
        
        # Right panel (Device details)
        self.right_panel = ScanSettingsPanel(self.plugin)
        self.main_splitter.addWidget(self.right_panel)
        
        # Set splitter sizes
        self.main_splitter.setSizes([600, 400])
        main_layout.addWidget(self.main_splitter, 1)
        
        # Bottom panel (Scan results)
        self.bottom_panel = ScanHistoryPanel(self.plugin)
        
        # Vertical splitter for main area and bottom panel
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.vertical_splitter.addWidget(self.main_splitter)
        self.vertical_splitter.addWidget(self.bottom_panel)
        self.vertical_splitter.setSizes([700, 300])
        
        main_layout.addWidget(self.vertical_splitter, 3)
        
        # Status bar
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)
        
        self.setLayout(main_layout)
    
    def _create_control_panel(self):
        """Create the control panel with scanning options.
        
        Returns:
            QWidget: Control panel widget
        """
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.StyledPanel)
        control_panel.setFixedHeight(50)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Interface selection
        interface_label = QLabel("Interface:")
        self.interface_combo = QComboBox()
        self._populate_interfaces()
        
        # IP Range
        ip_range_label = QLabel("IP Range:")
        self.ip_range_combo = QComboBox()
        self.ip_range_combo.setEditable(True)
        self.ip_range_combo.addItems(["192.168.1.0/24", "10.0.0.0/24", "172.16.0.0/16"])
        
        # Scan type
        scan_type_label = QLabel("Scan Type:")
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.addItems(["Ping Sweep", "ARP Scan", "TCP Port Scan"])
        
        # Scan/Stop button
        self.scan_button = QPushButton("Start Scan")
        self.scan_button.clicked.connect(self._on_scan_button_clicked)
        
        # Add widgets to layout
        layout.addWidget(interface_label)
        layout.addWidget(self.interface_combo)
        layout.addWidget(ip_range_label)
        layout.addWidget(self.ip_range_combo)
        layout.addWidget(scan_type_label)
        layout.addWidget(self.scan_type_combo)
        layout.addStretch()
        layout.addWidget(self.scan_button)
        
        control_panel.setLayout(layout)
        return control_panel
    
    def _create_status_bar(self):
        """Create the status bar.
        
        Returns:
            QWidget: Status bar widget
        """
        status_bar = QFrame()
        status_bar.setFrameShape(QFrame.StyledPanel)
        status_bar.setFixedHeight(25)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        self.device_count_label = QLabel("Devices: 0")
        layout.addStretch()
        layout.addWidget(self.device_count_label)
        
        status_bar.setLayout(layout)
        return status_bar
    
    def _populate_interfaces(self):
        """Populate the interface combo box with available interfaces."""
        self.interface_combo.clear()
        
        interfaces = self.plugin.get_interfaces()
        for interface_id, interface_data in interfaces.items():
            display_name = f"{interface_data['name']} ({interface_data['ip']})"
            self.interface_combo.addItem(display_name, interface_id)
    
    def _connect_signals(self):
        """Connect signals from plugin to UI handlers."""
        self.plugin.device_found.connect(self._on_device_found)
        self.plugin.scan_started.connect(self._on_scan_started)
        self.plugin.scan_finished.connect(self._on_scan_finished)
        self.plugin.scan_progress.connect(self._on_scan_progress)
    
    @Slot()
    def _on_scan_button_clicked(self):
        """Handle scan/stop button click."""
        if self.active_scan_id:
            # Stop the current scan
            self.plugin.stop_scan(self.active_scan_id)
        else:
            # Start a new scan
            interface = self.interface_combo.currentData()
            ip_range = self.ip_range_combo.currentText()
            scan_type = self.scan_type_combo.currentText().lower().replace(" ", "_")
            
            try:
                self.active_scan_id = self.plugin.start_scan(interface, ip_range, scan_type)
                self.scan_button.setText("Stop Scan")
                self.status_label.setText(f"Scanning {ip_range}...")
            except Exception as e:
                self.logger.error(f"Error starting scan: {str(e)}")
                self.status_label.setText(f"Error: {str(e)}")
    
    @Slot(dict)
    def _on_device_found(self, device):
        """Handle device found event.
        
        Args:
            device: Device information dictionary
        """
        # Update device count
        self.device_count_label.setText(f"Devices: {len(self.plugin.devices)}")
        
        # Update UI panels
        self.left_panel.add_device(device)
        
        # If this is the first device selected, show its details
        if len(self.plugin.devices) == 1:
            self.right_panel.show_device(device)
    
    @Slot(dict)
    def _on_scan_started(self, scan_data):
        """Handle scan started event.
        
        Args:
            scan_data: Scan information dictionary
        """
        # Update UI
        self.scan_button.setText("Stop Scan")
        self.status_label.setText(f"Scanning {scan_data.get('ip_range')}...")
        
        # Notify other panels
        self.bottom_panel.on_scan_started(scan_data)
    
    @Slot(dict)
    def _on_scan_finished(self, scan_data):
        """Handle scan finished event.
        
        Args:
            scan_data: Scan information dictionary
        """
        scan_id = scan_data.get('scan_id')
        if scan_id == self.active_scan_id:
            self.active_scan_id = None
            self.scan_button.setText("Start Scan")
            
            # Update status
            status = scan_data.get('status', 'completed')
            if status == 'completed':
                self.status_label.setText("Scan completed")
            elif status == 'error':
                self.status_label.setText(f"Scan error: {scan_data.get('error', 'Unknown error')}")
            else:
                self.status_label.setText("Scan stopped")
        
        # Notify other panels
        self.bottom_panel.on_scan_finished(scan_data)
    
    @Slot(dict)
    def _on_scan_progress(self, progress_data):
        """Handle scan progress event.
        
        Args:
            progress_data: Progress information dictionary
        """
        scan_id = progress_data.get('scan_id')
        if scan_id == self.active_scan_id:
            devices_found = progress_data.get('devices_found', 0)
            total_devices = progress_data.get('total_devices', 0)
            
            if total_devices > 0:
                percentage = int((devices_found / total_devices) * 100)
                self.status_label.setText(f"Scanning... {percentage}% ({devices_found}/{total_devices})")
            else:
                self.status_label.setText(f"Scanning... {devices_found} devices found")
        
        # Notify other panels
        self.bottom_panel.on_scan_progress(progress_data)
    
    def refresh(self):
        """Refresh the panel data."""
        self._populate_interfaces()
        self.left_panel.refresh()
        self.right_panel.refresh()
        self.bottom_panel.refresh()
        
        # Update device count
        self.device_count_label.setText(f"Devices: {len(self.plugin.devices)}") 