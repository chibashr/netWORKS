"""
Network Scanner Plugin Utilities
"""

import os
import sys
import subprocess
import functools
import ipaddress
from pathlib import Path
from loguru import logger

def ensure_plugin_dependencies():
    """
    Ensures all plugin dependencies are installed in the plugin's lib directory.
    Returns True if successful, False otherwise.
    """
    plugin_dir = Path(__file__).parent.parent
    requirements_file = plugin_dir / "requirements.txt"
    lib_dir = plugin_dir / "lib"
    
    if not lib_dir.exists():
        lib_dir.mkdir(parents=True)
    
    # Add lib directory to Python path if not already there
    lib_path = str(lib_dir.absolute())
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)
    
    try:
        # Check if requirements are already installed
        with open(requirements_file) as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        # Map package names to their import names
        package_map = {
            'python-nmap': 'nmap',
            'netifaces': 'netifaces'
        }
        
        # Install missing requirements
        for req in requirements:
            package_name = req.split('>=')[0].split('==')[0]
            import_name = package_map.get(package_name, package_name)
            try:
                __import__(import_name)
            except ImportError:
                print(f"Installing plugin requirement: {req}")
                subprocess.check_call([
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--target",
                    str(lib_dir),
                    req
                ])
        return True
    except Exception as e:
        print(f"Error ensuring plugin dependencies: {e}")
        return False

def safe_action_wrapper(func):
    """
    Decorator to safely handle plugin actions and provide error handling.
    
    Args:
        func: The function to wrap
        
    Returns:
        wrapper: The wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            # If first arg is self and has main_window, show error dialog
            if args and hasattr(args[0], 'main_window') and args[0].main_window:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    args[0].main_window,
                    "Error",
                    f"An error occurred: {str(e)}"
                )
            return None
    return wrapper

def safe_emit_device_found(signal, device):
    """
    Safely emit a device found signal without blocking the UI.
    
    Args:
        signal: The signal to emit
        device: The device data to emit
    """
    try:
        from PySide6.QtCore import QTimer
        # Use a timer to emit the signal in the next event loop iteration
        # This prevents UI blocking during rapid device discovery
        QTimer.singleShot(0, lambda: signal.emit(device))
    except Exception as e:
        logger.error(f"Error emitting device found signal: {e}")

def parse_ip_range(ip_range: str) -> str:
    """
    Parse and validate an IP range string.
    
    Args:
        ip_range: IP range in various formats (single IP, CIDR, range)
        
    Returns:
        str: Validated IP range
    """
    try:
        # Try parsing as CIDR
        ipaddress.ip_network(ip_range, strict=False)
        return ip_range
    except ValueError:
        try:
            # Try parsing as single IP
            ipaddress.ip_address(ip_range)
            return ip_range
        except ValueError:
            # Try parsing as range (e.g. 192.168.1.1-10)
            if '-' in ip_range:
                start, end = ip_range.rsplit('-', 1)
                if '.' not in end:  # Short form like 192.168.1.1-10
                    base = start.rsplit('.', 1)[0]
                    end = f"{base}.{end}"
                try:
                    ipaddress.ip_address(start)
                    ipaddress.ip_address(end)
                    return ip_range
                except ValueError:
                    pass
            raise ValueError(f"Invalid IP range format: {ip_range}")

def get_subnet_for_ip(ip: str) -> str:
    """
    Get the subnet for an IP address.
    
    Args:
        ip: IP address
        
    Returns:
        str: Subnet in CIDR notation
    """
    try:
        # Import netifaces here to ensure it's available
        import netifaces
        
        # Find interface with this IP
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    if addr['addr'] == ip:
                        # Calculate network address using IP and netmask
                        ip_obj = ipaddress.ip_address(ip)
                        netmask = addr.get('netmask', '255.255.255.0')
                        netmask_obj = ipaddress.ip_address(netmask)
                        
                        # Calculate network bits
                        network_bits = bin(int(netmask_obj)).count('1')
                        
                        # Create network object
                        network = ipaddress.ip_network(f"{ip}/{network_bits}", strict=False)
                        return str(network)
                        
        # If we didn't find the interface, return a default /24 network
        network = ipaddress.ip_network(f"{ip}/24", strict=False)
        return str(network)
        
    except Exception as e:
        logger.error(f"Error getting subnet for IP {ip}: {e}")
        # Return a safe default
        return f"{ip}/24"

def get_friendly_interface_name(interface_id: str) -> str:
    """
    Get a friendly name for a network interface.
    
    Args:
        interface_id: The interface identifier (GUID on Windows, name on Unix)
        
    Returns:
        str: A friendly name for the interface
    """
    try:
        # On Windows, try to get friendly name using wmic
        if os.name == 'nt' and interface_id.startswith('{') and interface_id.endswith('}'):
            try:
                # Remove curly braces for wmic query
                guid = interface_id.strip('{}')
                
                # Try to get the friendly name using wmic
                result = subprocess.run([
                    'wmic', 'path', 'win32_networkadapter', 
                    'where', f'GUID="{{{guid}}}"', 
                    'get', 'NetConnectionID', '/value'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('NetConnectionID='):
                            friendly_name = line.split('=', 1)[1].strip()
                            if friendly_name:
                                return friendly_name
                
                # Fallback: try using powershell
                result = subprocess.run([
                    'powershell', '-Command',
                    f'Get-NetAdapter | Where-Object {{$_.InterfaceGuid -eq "{{{guid}}}"}} | Select-Object -ExpandProperty Name'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    friendly_name = result.stdout.strip()
                    if friendly_name:
                        return friendly_name
                        
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass
            
            # If we can't get a friendly name, create a generic one
            return f"Network Adapter {interface_id[-8:-1]}"
        
        # On Unix-like systems, the interface name is usually already friendly
        # But we can make some common ones more readable
        friendly_names = {
            'lo': 'Loopback',
            'lo0': 'Loopback',
            'eth0': 'Ethernet',
            'eth1': 'Ethernet 2',
            'wlan0': 'WiFi',
            'wlan1': 'WiFi 2',
            'en0': 'Ethernet',
            'en1': 'Ethernet 2',
            'wlp': 'WiFi',  # Common prefix for WiFi on some Linux systems
        }
        
        # Check for exact matches first
        if interface_id in friendly_names:
            return friendly_names[interface_id]
        
        # Check for prefix matches
        for prefix, name in friendly_names.items():
            if interface_id.startswith(prefix):
                return name
                
        # Return the original name if no friendly name found
        return interface_id
        
    except Exception as e:
        logger.debug(f"Error getting friendly name for interface {interface_id}: {e}")
        return interface_id

def get_network_interfaces() -> list:
    """
    Get list of network interfaces with their details and friendly names.
    
    Returns:
        list: List of dictionaries containing interface details
    """
    try:
        # Import netifaces here to ensure it's available
        import netifaces
        
        interfaces = []
        for iface in netifaces.interfaces():
            try:
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:  # Only include interfaces with IPv4
                    for addr in addrs[netifaces.AF_INET]:
                        # Get friendly name for the interface
                        friendly_name = get_friendly_interface_name(iface)
                        
                        interfaces.append({
                            'name': iface,  # Keep original name for internal use
                            'friendly_name': friendly_name,  # Human-readable name
                            'ip': addr['addr'],
                            'netmask': addr.get('netmask', '255.255.255.0')
                        })
            except Exception as e:
                logger.warning(f"Error getting interface {iface} details: {e}")
        return interfaces
    except Exception as e:
        logger.error(f"Error getting network interfaces: {e}")
        return []

def calculate_host_count(network_range: str) -> int:
    """
    Calculate the number of hosts in a network range.
    
    Args:
        network_range: Network range in CIDR notation or IP range
        
    Returns:
        int: Number of hosts in the range
    """
    try:
        # Handle CIDR notation
        if '/' in network_range:
            network = ipaddress.ip_network(network_range, strict=False)
            return network.num_addresses
        
        # Handle IP range (e.g., 192.168.1.1-192.168.1.10)
        elif '-' in network_range:
            start_ip, end_ip = network_range.split('-', 1)
            start_ip = start_ip.strip()
            end_ip = end_ip.strip()
            
            # Handle short form (e.g., 192.168.1.1-10)
            if '.' not in end_ip:
                base = start_ip.rsplit('.', 1)[0]
                end_ip = f"{base}.{end_ip}"
            
            start = int(ipaddress.ip_address(start_ip))
            end = int(ipaddress.ip_address(end_ip))
            return max(0, end - start + 1)
        
        # Single IP
        else:
            ipaddress.ip_address(network_range)
            return 1
            
    except Exception as e:
        logger.error(f"Error calculating host count for {network_range}: {e}")
        return 1  # Default to 1 host if we can't calculate 