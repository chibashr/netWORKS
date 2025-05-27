"""
Network Scanner Module

This module handles the actual network scanning functionality using nmap and netifaces.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union
from loguru import logger

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

class Scanner:
    """Network scanner implementation using nmap"""
    
    def __init__(self):
        self.nm = nmap.PortScanner()
        self._current_scan = None
        self._is_scanning = False
    
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
    
    def scan(self, target: str, arguments: str = '-sn', sudo: bool = False) -> Dict:
        """
        Perform network scan
        
        Args:
            target: IP address, range, or CIDR notation
            arguments: nmap arguments
            sudo: whether to use sudo for the scan
        
        Returns:
            Dictionary containing scan results
        """
        try:
            self._is_scanning = True
            if sudo and os.name != 'nt':  # sudo only on non-Windows
                self._current_scan = self.nm.scan(target, arguments=arguments, sudo=True)
            else:
                self._current_scan = self.nm.scan(target, arguments=arguments)
            return self._current_scan
        except Exception as e:
            logger.error(f"Scan error: {e}")
            raise
        finally:
            self._is_scanning = False
            self._current_scan = None
    
    def stop_scan(self):
        """Stop any running scan"""
        if self._is_scanning and self._current_scan:
            try:
                # nmap-python doesn't have a direct stop method
                # but we can try to terminate the process
                self.nm._nm.terminate()
            except:
                pass
            finally:
                self._is_scanning = False
                self._current_scan = None
    
    def is_scanning(self) -> bool:
        """Check if a scan is currently running"""
        return self._is_scanning
    
    @property
    def last_scan(self) -> Optional[Dict]:
        """Get the results of the last scan"""
        return self._current_scan 