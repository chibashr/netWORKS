"""
Network Scanner Module

This module handles the actual network scanning functionality using nmap and netifaces.
"""

import os
import sys
import time
import ipaddress
from pathlib import Path
from typing import Dict, List, Optional, Union, Callable
from loguru import logger
from PySide6.QtCore import QThread, QObject, Signal

# Ensure plugin lib is in path
plugin_dir = Path(__file__).parent
lib_dir = plugin_dir / "lib"
if str(lib_dir.absolute()) not in sys.path:
    sys.path.insert(0, str(lib_dir.absolute()))

try:
    import nmap
    import netifaces
except ImportError as e:
    logger.error(f"Failed to import scanner dependencies: {e}")
    raise

class ScanWorker(QObject):
    """Worker class for performing network scans in a separate thread"""
    
    # Signals for communicating with the main thread
    scan_progress = Signal(int, int)  # current, total
    device_found = Signal(dict)  # device data
    scan_complete = Signal(dict)  # scan results
    scan_error = Signal(str)  # error message
    
    def __init__(self):
        super().__init__()
        self.nm = nmap.PortScanner()
        self._should_stop = False
        
    def stop(self):
        """Signal the worker to stop scanning"""
        self._should_stop = True
        
    def scan_network(self, target: str, scan_type: str = None, **kwargs):
        """
        Perform network scan with progress reporting
        
        Args:
            target: IP address, range, or CIDR notation to scan
            scan_type: Type of scan to perform (quick, standard, etc.)
            **kwargs: Additional scan options
        """
        start_time = time.time()
        devices_found = 0
        
        try:
            # Reset stop flag
            self._should_stop = False
            
            # Map scan types to nmap arguments
            scan_type_args = {
                "Quick Scan (ping only)": "-sn",
                "quick": "-sn",
                "Standard Scan": "-sS",
                "standard": "-sS", 
                "Comprehensive Scan": "-sS -sV -O",
                "comprehensive": "-sS -sV -O",
                "Stealth Scan": "-sS -T2",
                "stealth": "-sS -T2",
                "Service Detection": "-sV",
                "service": "-sV"
            }
            
            # Get scan arguments based on type
            if scan_type and scan_type in scan_type_args:
                arguments = scan_type_args[scan_type]
            else:
                arguments = "-sn"  # Default to ping scan
            
            # Add additional options from kwargs
            if kwargs.get('os_detection', False):
                arguments += " -O"
            if kwargs.get('port_scan', False):
                arguments += " -p-"
            
            # Add custom arguments if provided
            custom_args = kwargs.get('custom_args', '')
            if custom_args:
                arguments += f" {custom_args}"
            
            # Use sudo if requested and not on Windows
            use_sudo = kwargs.get('use_sudo', False)
            
            logger.info(f"Starting network scan: target={target}, args={arguments}, sudo={use_sudo}")
            
            # Calculate total hosts for progress tracking
            try:
                if '/' in target:
                    network = ipaddress.ip_network(target, strict=False)
                    total_hosts = network.num_addresses
                elif '-' in target:
                    start_ip, end_ip = target.split('-', 1)
                    start_ip = start_ip.strip()
                    end_ip = end_ip.strip()
                    if '.' not in end_ip:
                        base = start_ip.rsplit('.', 1)[0]
                        end_ip = f"{base}.{end_ip}"
                    start = int(ipaddress.ip_address(start_ip))
                    end = int(ipaddress.ip_address(end_ip))
                    total_hosts = max(0, end - start + 1)
                else:
                    total_hosts = 1
            except Exception as e:
                logger.warning(f"Could not calculate host count for {target}: {e}")
                total_hosts = 100  # Default fallback
            
            # Emit initial progress
            self.scan_progress.emit(0, total_hosts)
            
            # Perform the scan
            if use_sudo and os.name != 'nt':  # sudo only on non-Windows
                scan_result = self.nm.scan(target, arguments=arguments, sudo=True)
            else:
                scan_result = self.nm.scan(target, arguments=arguments)
            
            # Check if we should stop
            if self._should_stop:
                logger.info("Scan stopped by user request")
                return
            
            # Process scan results
            hosts_scanned = 0
            for host in self.nm.all_hosts():
                if self._should_stop:
                    break
                    
                hosts_scanned += 1
                self.scan_progress.emit(hosts_scanned, total_hosts)
                
                # Get host information
                host_info = self._extract_host_info(host)
                if host_info:
                    devices_found += 1
                    self.device_found.emit(host_info)
                    
            # Complete any remaining progress
            if hosts_scanned < total_hosts and not self._should_stop:
                self.scan_progress.emit(total_hosts, total_hosts)
            
            # Emit completion signal
            if not self._should_stop:
                scan_time = time.time() - start_time
                results = {
                    "scan_type": scan_type or "Unknown",
                    "network_range": target,
                    "devices_found": devices_found,
                    "total_hosts": total_hosts,
                    "scan_time": scan_time,
                    "arguments": arguments
                }
                self.scan_complete.emit(results)
                logger.info(f"Scan completed: {devices_found} devices found in {scan_time:.1f} seconds")
            
        except Exception as e:
            error_msg = f"Scan error: {str(e)}"
            logger.error(error_msg)
            self.scan_error.emit(error_msg)
    
    def _extract_host_info(self, host: str) -> Optional[Dict]:
        """
        Extract information about a discovered host
        
        Args:
            host: IP address of the host
            
        Returns:
            Dictionary with host information or None if host is not responsive
        """
        try:
            # Check if host is up
            if host not in self.nm.all_hosts():
                return None
                
            host_data = self.nm[host]
            
            # Skip hosts that are not up
            if host_data.state() != 'up':
                return None
            
            # Extract basic information
            info = {
                'ip_address': host,
                'hostname': 'Unknown',
                'mac_address': 'Unknown',
                'vendor': 'Unknown',
                'os': 'Unknown',
                'ports': [],
                'status': host_data.state()
            }
            
            # Try to get hostname
            try:
                hostnames = host_data.hostnames()
                if hostnames:
                    info['hostname'] = hostnames[0]['name']
            except:
                pass
            
            # Try to get MAC address and vendor
            try:
                if 'addresses' in host_data:
                    addresses = host_data['addresses']
                    if 'mac' in addresses:
                        info['mac_address'] = addresses['mac']
                        # Try to get vendor info
                        if 'vendor' in host_data and host_data['vendor']:
                            vendor_info = list(host_data['vendor'].values())
                            if vendor_info:
                                info['vendor'] = vendor_info[0]
            except:
                pass
            
            # Try to get OS information
            try:
                if 'osmatch' in host_data:
                    os_matches = host_data['osmatch']
                    if os_matches:
                        info['os'] = os_matches[0]['name']
            except:
                pass
            
            # Get port information
            try:
                for protocol in host_data.all_protocols():
                    ports = host_data[protocol].keys()
                    for port in ports:
                        port_info = host_data[protocol][port]
                        info['ports'].append({
                            'port': port,
                            'protocol': protocol,
                            'state': port_info['state'],
                            'service': port_info.get('name', 'unknown'),
                            'version': port_info.get('version', '')
                        })
            except:
                pass
            
            return info
            
        except Exception as e:
            logger.warning(f"Error extracting info for host {host}: {e}")
            return None

class Scanner:
    """Network scanner implementation using nmap with threading support"""
    
    def __init__(self):
        self.nm = nmap.PortScanner()
        self._current_scan = None
        self._is_scanning = False
        self._scan_thread = None
        self._scan_worker = None
        
        # Callback functions for progress and results
        self.progress_callback = None
        self.device_found_callback = None
        self.scan_complete_callback = None
        self.scan_error_callback = None
    
    def set_callbacks(self, progress_callback=None, device_found_callback=None, 
                     scan_complete_callback=None, scan_error_callback=None):
        """Set callback functions for scan events"""
        self.progress_callback = progress_callback
        self.device_found_callback = device_found_callback
        self.scan_complete_callback = scan_complete_callback
        self.scan_error_callback = scan_error_callback
    
    def get_network_interfaces(self) -> List[Dict[str, str]]:
        """Get list of network interfaces with their details"""
        interfaces = []
        for iface in netifaces.interfaces():
            try:
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:  # Only include interfaces with IPv4
                    for addr in addrs[netifaces.AF_INET]:
                        interfaces.append({
                            'name': iface,
                            'ip': addr['addr'],
                            'netmask': addr.get('netmask', '255.255.255.0')
                        })
            except Exception as e:
                logger.warning(f"Error getting interface {iface} details: {e}")
        return interfaces
    
    def scan_network(self, target: str, scan_type: str = None, **kwargs) -> bool:
        """
        Start a network scan with the given parameters
        
        Args:
            target: IP address, range, or CIDR notation to scan
            scan_type: Type of scan to perform (quick, standard, etc.)
            **kwargs: Additional scan options
        
        Returns:
            bool: True if scan started successfully, False otherwise
        """
        try:
            # Stop any existing scan
            if self._is_scanning:
                self.stop_scan()
                
            # Create worker and thread
            self._scan_worker = ScanWorker()
            self._scan_thread = QThread()
            
            # Move worker to thread
            self._scan_worker.moveToThread(self._scan_thread)
            
            # Connect signals
            if self.progress_callback:
                self._scan_worker.scan_progress.connect(self.progress_callback)
            if self.device_found_callback:
                self._scan_worker.device_found.connect(self.device_found_callback)
            if self.scan_complete_callback:
                self._scan_worker.scan_complete.connect(self.scan_complete_callback)
            if self.scan_error_callback:
                self._scan_worker.scan_error.connect(self.scan_error_callback)
            
            # Connect thread signals
            self._scan_thread.started.connect(
                lambda: self._scan_worker.scan_network(target, scan_type, **kwargs)
            )
            self._scan_worker.scan_complete.connect(self._scan_thread.quit)
            self._scan_worker.scan_error.connect(self._scan_thread.quit)
            self._scan_thread.finished.connect(self._on_thread_finished)
            
            # Start scanning
            self._is_scanning = True
            self._scan_thread.start()
            
            logger.info(f"Started threaded network scan: {target}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting network scan: {e}")
            self._is_scanning = False
            return False
    
    def _on_thread_finished(self):
        """Handle thread completion"""
        self._is_scanning = False
        if self._scan_thread:
            self._scan_thread.deleteLater()
            self._scan_thread = None
        if self._scan_worker:
            self._scan_worker.deleteLater()
            self._scan_worker = None
    
    def stop_scan(self):
        """Stop any running scan"""
        if self._is_scanning and self._scan_worker:
            try:
                self._scan_worker.stop()
                if self._scan_thread and self._scan_thread.isRunning():
                    self._scan_thread.quit()
                    self._scan_thread.wait(3000)  # Wait up to 3 seconds
                self._is_scanning = False
                logger.info("Scan stopped successfully")
                return True
            except Exception as e:
                logger.error(f"Error stopping scan: {e}")
                self._is_scanning = False
                return False
        return True
    
    def is_scanning(self) -> bool:
        """Check if a scan is currently running"""
        return self._is_scanning
    
    @property
    def last_scan(self) -> Optional[Dict]:
        """Get the results of the last scan"""
        return self._current_scan 