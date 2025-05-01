#!/usr/bin/env python3
# Network Scanner - Scan Engine

import os
import subprocess
import socket
import ipaddress
import threading
import time
import platform
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
import uuid
import copy
import re

class NetworkScanner:
    """Core network scanning engine for the plugin."""
    
    def __init__(self, plugin_api, config=None):
        """Initialize scanner with plugin API and optional config.
        
        Args:
            plugin_api: Reference to the plugin API
            config: Optional scanner configuration
        """
        self.plugin_api = plugin_api
        self.config = config or {}
        self.active_scans = {}
        self.scan_threads = {}
        self.scan_stop_events = {}
        self.results_cache = {}
        self.logger = logging.getLogger("plugin.base_network_scanner.scan_engine")
        self.logger.debug("NetworkScanner initialized")
        self.lock = threading.RLock()  # Thread safety lock
    
    @property
    def is_scanning(self):
        """Check if any scans are currently active.
        
        Returns:
            bool: True if any scans are running, False otherwise
        """
        with self.lock:
            # Check if there are any active scans with status 'running' or 'starting'
            return any(scan.get('status') in ['running', 'starting'] 
                      for scan in self.active_scans.values())
    
    def _generate_scan_id(self):
        """Generate a unique scan ID.
        
        Returns:
            str: A unique scan identifier
        """
        with self.lock:
            return f"scan_{uuid.uuid4().hex[:8]}"
    
    def run_scan(self, scan_config):
        """Run a network scan based on the provided configuration.
        
        This method is called from the UI and serves as a bridge between
        the plugin UI and the scanner engine.
        
        Args:
            scan_config: Dictionary containing scan configuration
            
        Returns:
            str: Scan ID
        """
        try:
            self.logger.debug(f"Running scan with config: {scan_config}")
            
            # Extract required parameters from scan_config
            scan_id = scan_config.get("id")
            interface = scan_config.get("interface")
            ip_range = scan_config.get("range")
            scan_type = scan_config.get("scan_type")
            
            if not scan_id or not interface or not ip_range or not scan_type:
                self.logger.error(f"Missing required scan parameters: id={scan_id}, interface={interface}, ip_range={ip_range}, scan_type={scan_type}")
                raise ValueError("Missing required scan parameters")
            
            # Create a stop event for this scan
            stop_event = threading.Event()
            
            # Add additional fields to scan_config
            scan_config['start_time'] = datetime.now()
            scan_config['status'] = 'starting'
            scan_config['stop_event'] = stop_event  # Store the stop event in the config
            
            # Store scan in active scans
            with self.lock:
                self.active_scans[scan_id] = scan_config
                self.scan_stop_events[scan_id] = stop_event
                self.results_cache[scan_id] = []
            
            # Parse scan type to match internal method names
            if scan_type == 'quick_scan':
                internal_scan_type = 'ping_sweep'
            elif scan_type in ['ping_sweep', 'port_scan', 'deep_scan', 'stealth_scan']:
                internal_scan_type = scan_type
            else:
                internal_scan_type = 'ping_sweep'  # Default to ping sweep
                
            scan_config['scan_type'] = internal_scan_type
            
            # Create and start scan thread
            scan_thread = threading.Thread(
                target=self._run_scan_thread,
                args=(scan_id, stop_event),
                name=f"ScanThread-{scan_id}"
            )
            scan_thread.daemon = True  # Thread will exit when main thread exits
            
            with self.lock:
                self.scan_threads[scan_id] = scan_thread
            
            scan_thread.start()
            
            self.logger.debug(f"Scan thread started with ID: {scan_id}")
            return scan_id
            
        except Exception as e:
            self.logger.error(f"Error running scan: {str(e)}", exc_info=True)
            raise
    
    def _run_scan_thread(self, scan_id, stop_event):
        """Run the scan in a background thread.
        
        Args:
            scan_id: The unique scan identifier
            stop_event: Threading event to signal scan termination
        """
        current_thread = threading.current_thread()
        self.logger.debug(f"Scan thread {scan_id} starting in thread: {current_thread.name}")
        
        try:
            # Update scan status
            with self.lock:
                if scan_id not in self.active_scans:
                    self.logger.error(f"Scan {scan_id} not found in active scans")
                    return
                    
                self.active_scans[scan_id]['status'] = 'running'
            
            # Get scan configuration - use shallow copy to avoid thread lock issues
            scan_config = None
            with self.lock:
                # Create a copy of the configuration without the stop_event (which can't be copied)
                config_copy = dict(self.active_scans[scan_id])
                if 'stop_event' in config_copy:
                    del config_copy['stop_event']
                scan_config = config_copy
            
            if not scan_config:
                self.logger.error(f"Cannot retrieve configuration for scan {scan_id}")
                return
            
            # Add stop_event reference without copying it
            scan_config['stop_event'] = stop_event
            
            # Parse IP range
            try:
                # Use our parsing method which handles different formats
                ip_addresses = self._parse_ip_range(scan_config.get('range', ''))
                if not ip_addresses:
                    self.logger.error(f"No valid IP addresses in range: {scan_config.get('range', '')}")
                    with self.lock:
                        self.active_scans[scan_id]['status'] = 'error'
                        self.active_scans[scan_id]['error'] = f"No valid IP addresses in range"
                    return
                    
                total_ips = len(ip_addresses)
                self.logger.debug(f"Scan {scan_id} will process {total_ips} IP addresses")
                
                # Store total IP count
                scan_config['total_devices'] = total_ips
                with self.lock:
                    self.active_scans[scan_id]['total_devices'] = total_ips
            except Exception as e:
                self.logger.error(f"Invalid IP range format: {scan_config.get('range', '')}: {str(e)}")
                with self.lock:
                    self.active_scans[scan_id]['status'] = 'error'
                    self.active_scans[scan_id]['error'] = f"Invalid IP range: {str(e)}"
                return
            
            # Get scan options
            options = scan_config.get('options', {})
            
            # Get scan type
            scan_type = scan_config.get('scan_type', 'ping_sweep')
            
            # Check if we should use nmap for advanced scanning
            use_nmap = (
                options.get('os_detection', False) or 
                options.get('service_detection', False) or
                options.get('script_scan', False) or
                (options.get('port_scan_type', 'connect') in ['syn', 'fin', 'udp', 'all']) or
                (options.get('discovery_method', 'ping') in ['syn', 'ack', 'udp', 'all'])
            )
            
            if use_nmap:
                self._run_nmap_scan(scan_config, ip_addresses)
            else:
                # Use the standard scan methods
                if scan_type == 'ping_sweep':
                    self._run_ping_sweep(scan_config, ip_addresses)
                elif scan_type == 'port_scan':
                    self._run_ping_sweep(scan_config, ip_addresses)  # Start with ping sweep
                    if not stop_event.is_set():
                        # Only continue if not stopped
                        self._run_port_scan(scan_config, ip_addresses)
                elif scan_type == 'deep_scan':
                    self._run_deep_scan(scan_config, ip_addresses)
                elif scan_type == 'stealth_scan':
                    self._run_stealth_scan(scan_config, ip_addresses)
            
            # If the scan wasn't stopped, mark it as completed
            if not stop_event.is_set():
                with self.lock:
                    if scan_id in self.active_scans:
                        self.active_scans[scan_id]['status'] = 'completed'
                        self.active_scans[scan_id]['end_time'] = datetime.now()
                        
                        # Calculate duration
                        start_time = self.active_scans[scan_id].get('start_time')
                        end_time = self.active_scans[scan_id].get('end_time')
                        if start_time and end_time:
                            duration = (end_time - start_time).total_seconds()
                            self.active_scans[scan_id]['duration'] = duration
                        
                        # Ensure device count is correct
                        devices_found = len(self.results_cache.get(scan_id, []))
                        self.active_scans[scan_id]['devices_found'] = devices_found
                        
                        # Log scan completion
                        self.logger.info(f"Scan {scan_id} completed successfully with {devices_found} devices found")
                        
                        # Emit scan finished signal
                        self.plugin_api.scan_finished.emit(self.active_scans[scan_id])
                
        except Exception as e:
            self.logger.error(f"Error in scan thread: {str(e)}", exc_info=True)
            # Update scan status to error
            with self.lock:
                if scan_id in self.active_scans:
                    self.active_scans[scan_id]['status'] = 'error'
                    self.active_scans[scan_id]['error'] = str(e)
                    self.active_scans[scan_id]['end_time'] = datetime.now()
                    
                    # Log scan error
                    self.logger.error(f"Scan {scan_id} failed with error: {str(e)}")
                    
                    # Emit scan finished signal with error
                    self.plugin_api.scan_finished.emit(self.active_scans[scan_id])
        
        self.logger.debug(f"Scan thread {scan_id} completed in thread: {current_thread.name}")
    
    def _run_nmap_scan(self, scan_config, ip_addresses):
        """Run an advanced scan using nmap.
        
        Args:
            scan_config: The scan configuration dictionary
            ip_addresses: List of IP addresses to scan
        """
        stop_event = scan_config.get('stop_event')
        scan_id = scan_config.get('id')
        options = scan_config.get('options', {})
        
        try:
            # Check if nmap is available
            try:
                # Try to execute nmap to check if it's available
                subprocess.run(["nmap", "--version"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               timeout=2)
            except (subprocess.SubprocessError, FileNotFoundError):
                self.logger.error("Nmap is not available on this system")
                with self.lock:
                    if scan_id in self.active_scans:
                        self.active_scans[scan_id]['status'] = 'error'
                        self.active_scans[scan_id]['error'] = "Nmap is not available on this system"
                return
            
            total_devices = scan_config.get('total_devices', len(ip_addresses))
            progress_increment = 100 / total_devices if total_devices > 0 else 0
            
            # Build the target list string - join IPs with spaces for nmap
            target_list = " ".join(ip_addresses)
            
            # Build nmap command with all options
            nmap_args = ["nmap"]
            
            # Add timing template
            timing = options.get('timing', 3)  # Default to normal
            nmap_args.append(f"-T{timing}")
            
            # Set basic discovery options based on discovery_method
            discovery_method = options.get('discovery_method', 'ping')
            if discovery_method == 'ping':
                nmap_args.append("-PE")  # ICMP Echo
            elif discovery_method == 'arp':
                nmap_args.append("-PR")  # ARP scan
            elif discovery_method == 'syn':
                nmap_args.append("-PS")  # TCP SYN
            elif discovery_method == 'ack':
                nmap_args.append("-PA")  # TCP ACK
            elif discovery_method == 'udp':
                nmap_args.append("-PU")  # UDP scan
            elif discovery_method == 'all':
                nmap_args.extend(["-PE", "-PS", "-PA", "-PU", "-PR"])  # All methods
            
            # Port scanning options
            if options.get('use_common_ports', True):
                port_group = options.get('port_group', 'common')
                if port_group == 'top10':
                    nmap_args.append("--top-ports 10")
                elif port_group == 'top100':
                    nmap_args.append("--top-ports 100")
                elif port_group == 'top1000':
                    nmap_args.append("--top-ports 1000")
                elif port_group == 'all':
                    nmap_args.append("-p-")  # All ports
                # 'common' is the default
            
            # Add custom ports if specified
            if options.get('use_custom_ports', False) and 'ports' in options:
                port_list = options['ports']
                port_str = ",".join(map(str, port_list))
                nmap_args.append(f"-p {port_str}")
            
            # Port scan type
            port_scan_type = options.get('port_scan_type', 'connect')
            if port_scan_type == 'syn':
                nmap_args.append("-sS")
            elif port_scan_type == 'fin':
                nmap_args.append("-sF")
            elif port_scan_type == 'udp':
                nmap_args.append("-sU")
            elif port_scan_type == 'all':
                nmap_args.append("-sS -sU -sV")
            # 'connect' is the default scan type so no args needed
            
            # Advanced options
            if options.get('os_detection', False):
                nmap_args.append("-O")
            
            if options.get('service_detection', False):
                nmap_args.append("-sV")
            
            if options.get('script_scan', False):
                script_category = options.get('script_category', 'safe')
                if script_category == 'default':
                    nmap_args.append("-sC")
                elif script_category == 'discovery':
                    nmap_args.append("--script=discovery")
                elif script_category == 'safe':
                    nmap_args.append("--script=safe")
                elif script_category == 'all':
                    nmap_args.append("--script=all")
            
            # Add XML output for parsing
            import tempfile
            xml_output = tempfile.mktemp(suffix=".xml")
            nmap_args.append(f"-oX {xml_output}")
            
            # Verbose output
            nmap_args.append("-v")
            
            # Add target list
            nmap_args.append(target_list)
            
            # Join all args into a command string
            nmap_cmd = " ".join(nmap_args)
            self.logger.debug(f"Running nmap command: {nmap_cmd}")
            
            # Run nmap and capture output
            process = subprocess.Popen(
                nmap_cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Variables to track progress
            current_ip_index = 0
            current_progress = 0
            
            # Regular expressions to parse nmap output
            ip_pattern = re.compile(r'Discovered open port \d+/[a-z]+ on (\d+\.\d+\.\d+\.\d+)')
            completion_pattern = re.compile(r'Completed (\d+)%')
            
            # Process output line by line to track progress
            while process.poll() is None:
                if stop_event.is_set():
                    # Stop scan if requested
                    process.terminate()
                    process.wait()
                    self.logger.info(f"Nmap scan {scan_id} terminated by user")
                    with self.lock:
                        if scan_id in self.active_scans:
                            self.active_scans[scan_id]['status'] = 'stopped'
                    return
                
                # Read a line from stdout
                line = process.stdout.readline()
                if not line:
                    continue
                
                # Check for IP addresses in output
                ip_match = ip_pattern.search(line)
                if ip_match:
                    ip = ip_match.group(1)
                    self.logger.debug(f"Found device at IP: {ip}")
                    
                    # Create a basic device record - will be enhanced with XML parsing
                    device = {
                        'ip': ip,
                        'status': 'up',
                        'scan_id': scan_id,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Emit device found
                    self._emit_device_found(device)
                
                # Check for completion percentage
                completion_match = completion_pattern.search(line)
                if completion_match:
                    new_progress = int(completion_match.group(1))
                    if new_progress > current_progress:
                        current_progress = new_progress
                        # Update scan progress
                        with self.lock:
                            if scan_id in self.active_scans:
                                self.active_scans[scan_id]['progress'] = current_progress
                        
                        # Log progress
                        self.logger.debug(f"Scan {scan_id} progress: {current_progress}%")
            
            # Process completed - check return code
            return_code = process.returncode
            if return_code != 0 and not stop_event.is_set():
                # Read error output
                error_output = process.stderr.read()
                self.logger.error(f"Nmap scan failed with return code {return_code}: {error_output}")
                with self.lock:
                    if scan_id in self.active_scans:
                        self.active_scans[scan_id]['status'] = 'error'
                        self.active_scans[scan_id]['error'] = f"Nmap scan failed: {error_output}"
                return
            
            # Parse the XML output file if it exists and wasn't stopped
            if not stop_event.is_set() and os.path.exists(xml_output):
                try:
                    self._parse_nmap_xml(xml_output, scan_id)
                except Exception as e:
                    self.logger.error(f"Error parsing nmap XML output: {str(e)}")
                finally:
                    # Clean up temp file
                    try:
                        os.remove(xml_output)
                    except Exception:
                        pass
        
        except Exception as e:
            self.logger.error(f"Error running nmap scan: {str(e)}", exc_info=True)
            with self.lock:
                if scan_id in self.active_scans:
                    self.active_scans[scan_id]['status'] = 'error'
                    self.active_scans[scan_id]['error'] = f"Nmap scan error: {str(e)}"
    
    def _parse_nmap_xml(self, xml_file, scan_id):
        """Parse the nmap XML output file to extract detailed host information.
        
        Args:
            xml_file: Path to the nmap XML output file
            scan_id: The scan ID this data belongs to
        """
        try:
            import xml.etree.ElementTree as ET
            
            # Parse the XML
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Process each host
            for host in root.findall('./host'):
                # Get IP address
                ip = None
                for addr in host.findall('./address'):
                    if addr.get('addrtype') == 'ipv4':
                        ip = addr.get('addr')
                        break
                
                if not ip:
                    continue
                
                # Get status
                status = 'unknown'
                status_elem = host.find('./status')
                if status_elem is not None:
                    status = status_elem.get('state', 'unknown')
                
                # Get hostnames
                hostnames = []
                for hostname in host.findall('./hostnames/hostname'):
                    hostnames.append(hostname.get('name', ''))
                
                # Get OS detection data
                os_info = {}
                os_elem = host.find('./os')
                if os_elem is not None:
                    os_matches = os_elem.findall('./osmatch')
                    if os_matches:
                        best_match = os_matches[0]  # First match has highest accuracy
                        os_info = {
                            'name': best_match.get('name', 'Unknown'),
                            'accuracy': best_match.get('accuracy', '0'),
                            'family': ''
                        }
                        
                        # Try to get OS family from class
                        os_classes = best_match.findall('./osclass')
                        if os_classes:
                            os_info['family'] = os_classes[0].get('osfamily', '')
                
                # Get open ports and services
                ports = []
                for port in host.findall('./ports/port'):
                    port_state = port.find('./state')
                    if port_state is not None and port_state.get('state') == 'open':
                        port_id = port.get('portid', '')
                        protocol = port.get('protocol', '')
                        
                        service_info = {}
                        service_elem = port.find('./service')
                        if service_elem is not None:
                            service_info = {
                                'name': service_elem.get('name', 'unknown'),
                                'product': service_elem.get('product', ''),
                                'version': service_elem.get('version', ''),
                                'extrainfo': service_elem.get('extrainfo', '')
                            }
                        
                        ports.append({
                            'port': port_id,
                            'protocol': protocol,
                            'service': service_info
                        })
                
                # Create comprehensive device record
                device = {
                    'ip': ip,
                    'status': status,
                    'scan_id': scan_id,
                    'timestamp': datetime.now().isoformat(),
                    'hostnames': hostnames,
                    'os': os_info,
                    'ports': ports
                }
                
                # Emit device found or update existing device
                self._emit_device_found(device)
        
        except Exception as e:
            self.logger.error(f"Error parsing nmap XML file: {str(e)}", exc_info=True)
    
    def _run_ping_sweep(self, scan_config: Dict, ip_addresses: List[str]):
        """Run a ping sweep on the specified IP addresses.
        
        Args:
            scan_config: Scan configuration
            ip_addresses: List of IP addresses to scan
        """
        self.logger.info(f"Running ping sweep on {len(ip_addresses)} addresses")
        
        timeout = scan_config.get("timeout", 1)
        retries = scan_config.get("retries", 1)
        parallel = scan_config.get("parallel", 50)
        scan_id = scan_config.get("id")
        
        devices_found = 0
        stop_event = scan_config.get("stop_event")
        if not stop_event:
            self.logger.error("No stop event in scan configuration")
            return
        
        # Function to ping a single IP address
        def ping_host(ip):
            if stop_event.is_set():
                return None
            
            try:
                # Determine OS-specific ping command
                if platform.system().lower() == "windows":
                    cmd = ["ping", "-n", str(retries), "-w", str(timeout * 1000), ip]
                else:
                    cmd = ["ping", "-c", str(retries), "-W", str(timeout), ip]
                
                self.logger.debug(f"Pinging {ip} with command: {' '.join(cmd)}")
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                if result.returncode == 0:
                    # Host is up
                    hostname = ""
                    mac = ""
                    os_hint = ""
                    
                    # Try to get hostname
                    try:
                        hostname = socket.getfqdn(ip)
                        if hostname == ip:
                            # Try harder with a direct gethostbyaddr call
                            try:
                                hostname = socket.gethostbyaddr(ip)[0]
                            except:
                                hostname = ""
                    except Exception as e:
                        self.logger.debug(f"Error getting hostname for {ip}: {str(e)}")
                    
                    # Try to guess OS from ping results (TTL values)
                    try:
                        output = result.stdout.lower()
                        if "ttl=" in output or "time to live=" in output:
                            # Extract TTL value
                            ttl_match = None
                            if "ttl=" in output:
                                ttl_match = re.search(r"ttl=(\d+)", output)
                            elif "time to live=" in output:
                                ttl_match = re.search(r"time to live=(\d+)", output)
                                
                            if ttl_match:
                                ttl = int(ttl_match.group(1))
                                if ttl <= 64:
                                    os_hint = "Linux/Unix"
                                elif ttl <= 128:
                                    os_hint = "Windows"
                                elif ttl <= 255:
                                    os_hint = "Cisco/Network"
                    except Exception as e:
                        self.logger.debug(f"Error guessing OS from TTL for {ip}: {str(e)}")
                    
                    # Try to get MAC address (platform specific)
                    try:
                        if platform.system().lower() == "windows":
                            # Use ARP to get MAC
                            arp_cmd = ["arp", "-a", ip]
                            arp_result = subprocess.run(arp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            if arp_result.returncode == 0:
                                # Parse MAC from ARP output
                                mac_matches = re.findall(r"([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})", arp_result.stdout)
                                if mac_matches:
                                    mac = mac_matches[0]
                        else:
                            # For Linux/macOS
                            arp_cmd = ["arp", "-n", ip]
                            arp_result = subprocess.run(arp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            if arp_result.returncode == 0:
                                # Parse MAC from ARP output
                                mac_matches = re.findall(r"([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})", arp_result.stdout)
                                if mac_matches:
                                    mac = mac_matches[0]
                    except Exception as e:
                        self.logger.debug(f"Error getting MAC address for {ip}: {str(e)}")
                    
                    # Create device info with comprehensive metadata
                    device = {
                        "ip": ip,
                        "hostname": hostname or f"Device-{ip.split('.')[-1]}",
                        "mac": mac,
                        "os": os_hint,
                        "status": "active",
                        "scan_method": "ping",
                        "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "scan_id": scan_id,
                        "metadata": {
                            "ping_response": "ok",
                            "discovery_method": "ping_sweep",
                            "ttl": ttl_match.group(1) if 'ttl_match' in locals() and ttl_match else "",
                            "rtt": re.search(r"time[=<]([\d.]+)", output).group(1) if re.search(r"time[=<]([\d.]+)", output) else "",
                            "scan_id": scan_id
                        }
                    }
                    
                    self.logger.info(f"Device found: {ip} ({hostname or 'Unknown'})")
                    return device
                else:
                    self.logger.debug(f"No response from {ip}")
                return None
            except Exception as e:
                self.logger.error(f"Error pinging {ip}: {str(e)}")
                return None
        
        # Use ThreadPoolExecutor to run ping scans in parallel
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {executor.submit(ping_host, ip): ip for ip in ip_addresses}
            
            for future in futures:
                try:
                    device = future.result()
                    if device:
                        devices_found += 1
                        scan_config["devices_found"] = devices_found
                        
                        # Update the active scan record
                        with self.lock:
                            if scan_id in self.active_scans:
                                self.active_scans[scan_id]["devices_found"] = devices_found
                        
                        # Emit device found signal
                        self._emit_device_found(device)
                except Exception as e:
                    self.logger.error(f"Error processing scan result: {str(e)}", exc_info=True)
                
                if stop_event.is_set():
                    self.logger.info(f"Scan {scan_id} was stopped")
                    scan_config["status"] = "stopped"
                    
                    # Update active scan status
                    with self.lock:
                        if scan_id in self.active_scans:
                            self.active_scans[scan_id]["status"] = "stopped"
                    break
    
    def _emit_device_found(self, device):
        """Helper method to emit device_found events properly."""
        try:
            # Ensure the device has required fields
            if not device.get('ip'):
                self.logger.warning("Cannot emit device_found for device with no IP")
                return
            
            # Add timestamp if missing
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not device.get('last_seen'):
                device['last_seen'] = current_time
            if not device.get('first_seen'):
                device['first_seen'] = current_time
            
            # Add hostname if missing
            if not device.get('hostname'):
                device['hostname'] = f"Device-{device['ip'].split('.')[-1]}"
            
            # Ensure we have metadata
            if 'metadata' not in device:
                device['metadata'] = {}
            
            # Track how this device was discovered
            device['metadata']['discovery_source'] = 'network_scan'
            device['metadata']['discovery_timestamp'] = current_time
            
            success = False
            
            # First try the device_found signal
            if hasattr(self.plugin_api, 'device_found'):
                self.logger.debug(f"Emitting device_found signal for {device['ip']}")
                self.plugin_api.device_found.emit(device)
                success = True
            
            # Try the emit_event method next
            elif hasattr(self.plugin_api, 'emit_event'):
                self.logger.debug(f"Using emit_event for device {device['ip']}")
                self.plugin_api.emit_event('device_found', device)
                success = True
            
            # Try directly adding to the main window's device table
            if not success or self.logger.level <= logging.DEBUG:  # Always try direct access in debug mode
                try:
                    # Try direct access to main_window
                    if hasattr(self.plugin_api, 'api') and self.plugin_api.api:
                        api = self.plugin_api.api
                        if hasattr(api, 'main_window') and api.main_window:
                            if hasattr(api.main_window, 'device_table'):
                                self.logger.debug(f"Adding device {device['ip']} directly to main device table")
                                api.main_window.device_table.add_device(device)
                                success = True
                
                    # Try access via plugin_api.main_window
                    elif hasattr(self.plugin_api, 'main_window') and self.plugin_api.main_window:
                        if hasattr(self.plugin_api.main_window, 'device_table'):
                            self.logger.debug(f"Adding device {device['ip']} directly to device table")
                            self.plugin_api.main_window.device_table.add_device(device)
                            success = True
                except Exception as e:
                    self.logger.error(f"Error adding device directly to table: {str(e)}", exc_info=True)
            
            # If all else fails, log the issue
            if not success:
                self.logger.warning(f"No method available to emit device_found event for {device['ip']}")
            
        except Exception as e:
            self.logger.error(f"Error emitting device_found event: {str(e)}", exc_info=True)
    
    def _run_deep_scan(self, scan_config: Dict, ip_addresses: List[str]):
        """Run a deep scan on the specified IP addresses.
        
        Args:
            scan_config: Scan configuration
            ip_addresses: List of IP addresses to scan
        """
        self.logger.info(f"Running deep scan on {len(ip_addresses)} addresses")
        
        # First, perform a ping sweep
        self._run_ping_sweep(scan_config, ip_addresses)
        
        # If scan was stopped, don't continue
        if scan_config["status"] in ["stopped", "error"]:
            return
        
        # Implement additional scanning functionality like port scanning
        scan_id = scan_config.get("id")
        ports = scan_config.get("ports", [80, 443, 22, 21, 25, 53, 3389])
        parallel = scan_config.get("parallel", 25)
        timeout = scan_config.get("timeout", 2)
        stop_event = self.active_scans[scan_id]["stop_event"]
        
        # Get devices already found
        devices = {}
        for i, scan in enumerate(self.plugin_api.scan_history):
            if scan.get("id") == scan_id:
                for ip, device in scan.get("devices", {}).items():
                    devices[ip] = device
                break
        
        # Function to scan ports on a single IP
        def scan_ports(ip):
            if stop_event.is_set():
                return None
            
            device = devices.get(ip, {})
            if not device:
                return None
            
            try:
                open_ports = []
                
                for port in ports:
                    if stop_event.is_set():
                        break
                    
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(timeout)
                        result = sock.connect_ex((ip, port))
                        if result == 0:
                            open_ports.append(port)
                        sock.close()
                    except:
                        pass
                
                if open_ports:
                    device["ports"] = open_ports
                    device["scan_method"] = "deep_scan"
                    
                    return device
                return None
            except Exception as e:
                self.logger.error(f"Error scanning ports on {ip}: {str(e)}")
                return None
        
        # Only scan devices that were found during ping sweep
        active_ips = list(devices.keys())
        
        # Use ThreadPoolExecutor to run port scans in parallel
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {executor.submit(scan_ports, ip): ip for ip in active_ips}
            
            for future in futures:
                try:
                    device = future.result()
                    if device:
                        # Emit device updated signal
                        self.plugin_api.emit_event('device_found', device)
                except Exception as e:
                    self.logger.error(f"Error processing port scan result: {str(e)}")
                
                if stop_event.is_set():
                    self.logger.info(f"Scan {scan_id} was stopped")
                    scan_config["status"] = "stopped"
                    break
    
    def _run_stealth_scan(self, scan_config: Dict, ip_addresses: List[str]):
        """Run a stealth scan on the specified IP addresses.
        
        Args:
            scan_config: Scan configuration
            ip_addresses: List of IP addresses to scan
        """
        # Modify parameters for a more stealthy scan
        scan_config["parallel"] = min(scan_config.get("parallel", 5), 5)
        scan_config["timeout"] = max(scan_config.get("timeout", 3), 3)
        
        # Run a standard ping sweep but with slower parameters
        self._run_ping_sweep(scan_config, ip_addresses)
    
    def stop_all_scans(self):
        """Stop all active scans."""
        self.logger.info(f"Stopping all active scans ({len(self.active_scans)})")
        for scan_id in list(self.active_scans.keys()):
            self.stop_scan(scan_id)
        
        # Wait for scans to stop
        max_wait = 5  # seconds
        start_time = time.time()
        while self.active_scans and time.time() - start_time < max_wait:
            time.sleep(0.1)
        
        if self.active_scans:
            self.logger.warning(f"{len(self.active_scans)} scans did not stop gracefully within timeout")

    def start_scan(self, interface, ip_range, scan_type, options=None):
        """Start a new network scan in a background thread.
        
        Args:
            interface: Network interface to use
            ip_range: IP range to scan (CIDR notation)
            scan_type: Type of scan to perform
            options: Additional scan options
            
        Returns:
            str: Scan ID for tracking the scan
        """
        try:
            self.logger.debug(f"Starting scan on interface {interface} with range {ip_range}, type {scan_type}")
            
            # Generate a unique scan ID
            scan_id = self._generate_scan_id()
            
            # Create scan configuration
            scan_config = {
                'id': scan_id,
                'interface': interface,
                'range': ip_range,
                'scan_type': scan_type,
                'options': options or {},
            }
            
            # Run the scan using our run_scan method
            return self.run_scan(scan_config)
            
        except Exception as e:
            self.logger.error(f"Error starting scan: {str(e)}", exc_info=True)
            raise
    
    def _parse_ip_range(self, ip_range: str) -> List[str]:
        """Parse an IP range string into a list of IP addresses.
        
        Supports:
        - Single IP: 192.168.1.1
        - CIDR notation: 192.168.1.0/24
        - Range notation: 192.168.1.1-254
        - Multiple ranges: 192.168.1.1-10,192.168.2.1-10
        
        Args:
            ip_range: String representing an IP range
            
        Returns:
            List of IP address strings
        """
        if not ip_range:
            return []
        
        ip_addresses = []
        
        # Split multiple ranges
        for range_part in ip_range.split(','):
            range_part = range_part.strip()
            
            if '-' in range_part and '/' not in range_part:
                # Handle range notation (e.g., 192.168.1.1-254)
                try:
                    start, end = range_part.rsplit('-', 1)
                    
                    # If only the last octet is provided in the end part
                    if '.' not in end:
                        base_ip = start.rsplit('.', 1)[0]
                        end = f"{base_ip}.{end}"
                    
                    # Convert to integer values for comparison
                    start_ip = int(ipaddress.IPv4Address(start))
                    end_ip = int(ipaddress.IPv4Address(end))
                    
                    # Generate IP addresses in the range
                    for ip_int in range(start_ip, end_ip + 1):
                        ip = str(ipaddress.IPv4Address(ip_int))
                        ip_addresses.append(ip)
                except Exception as e:
                    self.logger.error(f"Error parsing IP range {range_part}: {str(e)}")
            else:
                try:
                    # Handle CIDR notation or single IP
                    network = ipaddress.ip_network(range_part, strict=False)
                    for ip in network.hosts():
                        ip_addresses.append(str(ip))
                    
                    # If it's a single IP (no hosts), add it
                    if not ip_addresses and range_part.find('/') == -1:
                        ip_addresses.append(range_part)
                except Exception as e:
                    self.logger.error(f"Error parsing IP range {range_part}: {str(e)}")
        
        return ip_addresses
    
    def stop_scan(self, scan_id):
        """Stop a running scan.
        
        Args:
            scan_id: ID of the scan to stop
            
        Returns:
            bool: True if scan was stopped, False otherwise
        """
        self.logger.debug(f"Request to stop scan {scan_id}")
        
        with self.lock:
            if scan_id not in self.active_scans:
                self.logger.warning(f"Cannot stop scan {scan_id}: not found in active scans")
                return False
                
            if scan_id not in self.scan_stop_events:
                self.logger.warning(f"Cannot stop scan {scan_id}: stop event not found")
                return False
                
            # Set the stop event to signal the scan thread to terminate
            self.scan_stop_events[scan_id].set()
            
            # Update scan status
            self.active_scans[scan_id]['status'] = 'stopping'
            
        self.logger.info(f"Scan {scan_id} is being stopped")
        return True 