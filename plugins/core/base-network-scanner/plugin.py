import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from PySide6.QtCore import QObject, Signal, Slot

# Add the plugin directory to sys.path if not already there
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

# Import from core database if available
try:
    from core.database.workspace_manager import WorkspaceDBManager
    HAS_WORKSPACE_DB = True
except ImportError:
    HAS_WORKSPACE_DB = False
    logging.getLogger(__name__).warning("Workspace database manager not available, using local storage")

# Use direct imports from the plugin directory
from scan_engine import NetworkScanner
from ui.main_panel import NetworkScannerMainPanel

class BaseNetworkScannerPlugin(QObject):
    """Base network scanner plugin for netWORKS."""
    
    # Define signals
    device_found = Signal(dict)
    scan_started = Signal(dict)
    scan_finished = Signal(dict)
    scan_progress = Signal(dict)
    
    def __init__(self, api=None):
        """Initialize the plugin with optional API reference.
        
        Args:
            api: Reference to the netWORKS plugin API
        """
        super().__init__()
        self.api = api
        self.logger = logging.getLogger("plugin.base_network_scanner")
        self.scan_history = []
        self.active_scans = {}
        self.interfaces = {}
        self.devices = {}
        self.ui_initialized = False  # Flag to track UI initialization
        
        # Initialize scanner
        self.scanner = NetworkScanner(self)
        
        # Initialize workspace DB manager
        self.workspace_db = None
        if HAS_WORKSPACE_DB:
            try:
                self.workspace_db = WorkspaceDBManager()
                self.logger.info("Workspace database manager initialized")
            except Exception as e:
                self.logger.error(f"Error initializing workspace database manager: {str(e)}")
        
        # Connect signals
        self.device_found.connect(self._on_device_found)
        self.scan_finished.connect(self._on_scan_finished)
        
        # Register for workspace hooks if available
        if api and hasattr(api, 'hook'):
            try:
                @api.hook("workspace_loaded")
                def on_workspace_loaded(workspace_id):
                    self.logger.info(f"Workspace loaded: {workspace_id}")
                    self._load_from_workspace(workspace_id)
                
                @api.hook("workspace_saved")
                def on_workspace_saved(workspace_id):
                    self.logger.info(f"Workspace saved: {workspace_id}")
                    self._save_to_workspace(workspace_id)
            except Exception as e:
                self.logger.error(f"Error registering workspace hooks: {str(e)}")
        
        self.logger.info("Base Network Scanner plugin initialized")
    
    def emit_event(self, event_name, data=None):
        """Emit an event using the appropriate signal.
        
        Args:
            event_name: Name of the event to emit
            data: Data to include with the event
        """
        if event_name == 'device_found':
            self.device_found.emit(data)
        elif event_name == 'scan_started':
            self.scan_started.emit(data)
        elif event_name == 'scan_finished':
            self.scan_finished.emit(data)
        elif event_name == 'scan_progress':
            self.scan_progress.emit(data)
        else:
            self.logger.warning(f"Unknown event type: {event_name}")
    
    def get_main_panel(self):
        """Create and return the main panel for this plugin.
        
        Returns:
            NetworkScannerMainPanel: The main UI panel
        """
        return NetworkScannerMainPanel(self)
    
    def get_name(self):
        """Get the plugin name.
        
        Returns:
            str: Plugin name
        """
        return "Base Network Scanner"
    
    def get_description(self):
        """Get the plugin description.
        
        Returns:
            str: Plugin description
        """
        return "Basic network scanning functionality for discovering devices on the network."
    
    def get_interfaces(self):
        """Get available network interfaces.
        
        Returns:
            dict: Dictionary of network interfaces
        """
        try:
            # This would typically use a library like netifaces or scapy to get interfaces
            # For now, return some dummy interfaces for testing
            return {
                "eth0": {"name": "Ethernet 1", "mac": "00:11:22:33:44:55", "ip": "192.168.1.100"},
                "wlan0": {"name": "Wi-Fi", "mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.1.101"}
            }
        except Exception as e:
            self.logger.error(f"Error getting interfaces: {str(e)}")
            return {}
    
    def start_scan(self, interface, ip_range, scan_type, options=None):
        """Start a network scan.
        
        Args:
            interface: Network interface to use
            ip_range: IP range to scan (CIDR notation)
            scan_type: Type of scan to perform
            options: Additional options for the scan
            
        Returns:
            str: Scan ID for tracking the scan
        """
        try:
            self.logger.info(f"Starting {scan_type} scan on {interface} for range {ip_range}")
            
            # Start the scan using the scanner engine
            scan_id = self.scanner.start_scan(interface, ip_range, scan_type, options)
            
            # Create scan record
            scan_record = {
                'id': scan_id,
                'interface': interface,
                'ip_range': ip_range,
                'scan_type': scan_type,
                'options': options or {},
                'start_time': datetime.now(),
                'devices': {}
            }
            
            # Store in active scans
            self.active_scans[scan_id] = scan_record
            
            # Emit scan started signal
            self.scan_started.emit(scan_record)
            
            self.logger.debug(f"Scan started with ID: {scan_id}")
            return scan_id
            
        except Exception as e:
            self.logger.error(f"Error starting scan: {str(e)}", exc_info=True)
            raise
    
    def stop_scan(self, scan_id):
        """Stop a running scan.
        
        Args:
            scan_id: ID of the scan to stop
            
        Returns:
            bool: True if scan was stopped, False otherwise
        """
        try:
            self.logger.info(f"Stopping scan {scan_id}")
            
            # Stop the scan using the scanner engine
            result = self.scanner.stop_scan(scan_id)
            
            if result:
                self.logger.debug(f"Scan {scan_id} stop request sent")
            else:
                self.logger.warning(f"Failed to stop scan {scan_id}")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error stopping scan: {str(e)}", exc_info=True)
            return False
    
    def get_scan_status(self, scan_id):
        """Get the status of a scan.
        
        Args:
            scan_id: ID of the scan
            
        Returns:
            dict: Scan status information
        """
        if scan_id in self.active_scans:
            return self.active_scans[scan_id]
        
        # Check scan history
        for scan in self.scan_history:
            if scan.get('id') == scan_id:
                return scan
                
        return None
    
    def get_device_info(self, ip_address):
        """Get information about a device.
        
        Args:
            ip_address: IP address of the device
            
        Returns:
            dict: Device information
        """
        return self.devices.get(ip_address, {})
    
    @Slot(dict)
    def _on_device_found(self, device):
        """Handle device found event.
        
        Args:
            device: Device information dictionary
        """
        ip = device.get('ip')
        if not ip:
            self.logger.warning("Received device with no IP address")
            return
            
        # Log the device discovery
        self.logger.info(f"Device found: {ip} ({device.get('hostname', 'Unknown')})")
            
        # Update devices dictionary
        self.devices[ip] = device
        
        # Add timestamp if missing
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not device.get('last_seen'):
            device['last_seen'] = current_time
        if not device.get('first_seen'):
            device['first_seen'] = current_time
            
        # Update scan results if part of an active scan
        scan_id = device.get('scan_id')
        if scan_id and scan_id in self.active_scans:
            # Save device in the scan's devices dictionary - use IP as key
            self.active_scans[scan_id]['devices'][ip] = device
            
            # Update count
            devices_count = len(self.active_scans[scan_id]['devices'])
            self.active_scans[scan_id]['devices_found'] = devices_count
            
            # Emit progress update
            progress = {
                'scan_id': scan_id,
                'devices_found': devices_count,
                'total_devices': self.active_scans[scan_id].get('total_devices', 0),
                'percent': 0  # Will be calculated if total_devices > 0
            }
            
            if progress['total_devices'] > 0:
                progress['percent'] = min(100, int((progress['devices_found'] / progress['total_devices']) * 100))
                
            self.scan_progress.emit(progress)
            
        # Add metadata to indicate discovery source
        if 'metadata' not in device:
            device['metadata'] = {}
        device['metadata']['discovery_source'] = 'base-network-scanner'
        
        # Add to workspace database if available
        if self.workspace_db:
            try:
                self.logger.debug(f"Adding device {ip} to workspace database")
                self.workspace_db.add_device(device)
            except Exception as e:
                self.logger.error(f"Error adding device to workspace database: {str(e)}")
    
    @Slot(dict)
    def _on_scan_finished(self, scan_result):
        """Handle scan finished event.
        
        Args:
            scan_result: Scan result dictionary
        """
        scan_id = scan_result.get('id')
        if not scan_id:
            self.logger.warning("Received scan result with no ID")
            return
            
        # Get scan from active scans
        scan = self.active_scans.get(scan_id)
        if scan:
            # Add end time and calculate duration
            now = datetime.now()
            scan['end_time'] = now
            start_time = scan.get('start_time')
            if start_time:
                scan['duration'] = (now - start_time).total_seconds()
                
            # Move from active to history
            self.scan_history.append(scan)
            del self.active_scans[scan_id]
            
            # Add to database if available
            if self.workspace_db:
                try:
                    self.logger.debug(f"Adding scan result {scan_id} to workspace database")
                    scan_db_record = {
                        'id': scan_id,
                        'timestamp': scan.get('start_time').isoformat() if scan.get('start_time') else None,
                        'end_time': scan.get('end_time').isoformat() if scan.get('end_time') else None,
                        'interface': scan.get('interface'),
                        'ip_range': scan.get('ip_range'),
                        'scan_type': scan.get('scan_type'),
                        'duration': scan.get('duration', 0.0),
                        'devices_found': len(scan.get('devices', {})),
                        'status': 'completed',
                        'metadata': {
                            'plugin': 'base-network-scanner',
                            'options': scan.get('options', {})
                        }
                    }
                    self.workspace_db.add_scan_result(scan_db_record)
                except Exception as e:
                    self.logger.error(f"Error adding scan result to workspace database: {str(e)}")
                
        self.logger.info(f"Scan {scan_id} completed")
    
    def _load_from_workspace(self, workspace_id):
        """Load data from a workspace.
        
        Args:
            workspace_id: ID of the workspace
        """
        if not self.workspace_db:
            self.logger.warning("Workspace database manager not available")
            return
            
        try:
            # Clear current devices and scan history
            self.devices = {}
            self.scan_history = []
            
            # Load devices from workspace
            devices = self.workspace_db.get_devices()
            for device in devices:
                # Only add devices discovered by this plugin
                if device.get('metadata', {}).get('discovery_source') == 'base-network-scanner':
                    ip = device.get('ip')
                    if ip:
                        self.devices[ip] = device
            
            # Load scan history from workspace
            scan_history = self.workspace_db.get_scan_history()
            for scan in scan_history:
                # Only add scans from this plugin
                if scan.get('metadata', {}).get('plugin') == 'base-network-scanner':
                    self.scan_history.append(scan)
            
            self.logger.info(f"Loaded {len(self.devices)} devices and {len(self.scan_history)} scans from workspace {workspace_id}")
            
        except Exception as e:
            self.logger.error(f"Error loading from workspace: {str(e)}")
    
    def _save_to_workspace(self, workspace_id):
        """Save data to a workspace.
        
        Args:
            workspace_id: ID of the workspace
        """
        if not self.workspace_db:
            self.logger.warning("Workspace database manager not available")
            return
            
        try:
            # Save devices to workspace
            for device in self.devices.values():
                self.workspace_db.add_device(device)
            
            # Save scan history to workspace
            for scan in self.scan_history:
                scan_db_record = {
                    'id': scan.get('id'),
                    'timestamp': scan.get('start_time').isoformat() if scan.get('start_time') else None,
                    'end_time': scan.get('end_time').isoformat() if scan.get('end_time') else None,
                    'interface': scan.get('interface'),
                    'ip_range': scan.get('ip_range'),
                    'scan_type': scan.get('scan_type'),
                    'duration': scan.get('duration', 0.0),
                    'devices_found': len(scan.get('devices', {})),
                    'status': 'completed',
                    'metadata': {
                        'plugin': 'base-network-scanner',
                        'options': scan.get('options', {})
                    }
                }
                self.workspace_db.add_scan_result(scan_db_record)
            
            self.logger.info(f"Saved {len(self.devices)} devices and {len(self.scan_history)} scans to workspace {workspace_id}")
            
        except Exception as e:
            self.logger.error(f"Error saving to workspace: {str(e)}")
    
    def initialize(self):
        """Initialize the plugin.
        
        Called when plugin is first loaded.
        """
        self.logger.info("Initializing Base Network Scanner plugin")
        
        # Register hooks if API is available
        if self.api and hasattr(self.api, 'register_hook'):
            try:
                # Register hooks for device events
                self.api.register_hook('device_found', self._on_device_found)
            except Exception as e:
                self.logger.error(f"Error registering hooks: {str(e)}")
                
        return True
    
    def shutdown(self):
        """Shutdown the plugin.
        
        Called when plugin is being unloaded.
        """
        self.logger.info("Shutting down Base Network Scanner plugin")
        
        # Stop any active scans
        active_scan_ids = list(self.active_scans.keys())
        for scan_id in active_scan_ids:
            try:
                self.stop_scan(scan_id)
            except Exception as e:
                self.logger.error(f"Error stopping scan {scan_id} during shutdown: {str(e)}")
                
        return True 