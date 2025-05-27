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
        
        # Install missing requirements
        for req in requirements:
            try:
                __import__(req.split('>=')[0].split('==')[0])
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

def get_network_interfaces() -> list:
    """
    Get list of network interfaces with their details.
    
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
                        interfaces.append({
                            'name': iface,
                            'ip': addr['addr'],
                            'netmask': addr.get('netmask', '255.255.255.0')
                        })
            except Exception as e:
                logger.warning(f"Error getting interface {iface} details: {e}")
        return interfaces
    except Exception as e:
        logger.error(f"Error getting network interfaces: {e}")
        return [] 