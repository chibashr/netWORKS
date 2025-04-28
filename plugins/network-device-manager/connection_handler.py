#!/usr/bin/env python3
# Network Device Manager - Connection Handler

import os
import re
import time
import socket
import threading
from datetime import datetime
from pathlib import Path

try:
    import paramiko
    import netmiko
    from netmiko import ConnectHandler
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False

class ConnectionHandler:
    """
    Handles connections to network devices using SSH or telnet.
    Uses netmiko for device connections and command execution.
    """
    
    def __init__(self, credential_manager):
        self.credential_manager = credential_manager
        self.active_connections = {}  # ip -> connection_object
        self.connection_lock = threading.Lock()
    
    def connect(self, device_info, connection_type="ssh", credentials=None):
        """
        Connect to a device using SSH or telnet.
        
        Args:
            device_info: Dictionary containing device information
            connection_type: 'ssh' or 'telnet'
            credentials: Optional dictionary with 'username', 'password', and 'enable_password'
                         If not provided, will try to get from credential manager
        
        Returns:
            Tuple: (success, message, connection_id)
        """
        if not NETMIKO_AVAILABLE:
            return False, "Netmiko library not available", None
            
        ip = device_info.get('ip')
        if not ip:
            return False, "Device has no IP address", None
            
        # Check if already connected
        connection_id = f"{ip}_{connection_type}"
        with self.connection_lock:
            if connection_id in self.active_connections:
                # Check if connection is still active
                try:
                    self.active_connections[connection_id].find_prompt()
                    return True, "Already connected", connection_id
                except Exception:
                    # Connection lost, remove it
                    del self.active_connections[connection_id]
        
        # Get credentials if not provided
        if not credentials:
            # Try device-specific credentials
            credentials = self.credential_manager.get_credentials(ip)
            
            # If no device-specific credentials, try by subnet
            if not credentials:
                for subnet in ['192.168.0.0/24', '10.0.0.0/8', '172.16.0.0/12']:  # Example subnets
                    if self._is_ip_in_subnet(ip, subnet):
                        credentials = self.credential_manager.get_credentials_by_subnet(subnet)
                        if credentials:
                            break
            
            # If still no credentials, use default
            if not credentials:
                credentials = self.credential_manager.get_default_credentials()
                
            # If still no credentials, return error
            if not credentials:
                return False, "No credentials available for this device", None
        
        # Prepare connection parameters
        device_type = device_info.get('device_type', 'cisco_ios')  # Default to Cisco IOS
        
        connection_params = {
            'device_type': device_type,
            'ip': ip,
            'username': credentials.get('username', ''),
            'password': credentials.get('password', ''),
            'secret': credentials.get('enable_password', ''),
            'port': 22 if connection_type == 'ssh' else 23,
            'verbose': True,
            'session_log': f"logs/{ip}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            'session_log_file_mode': 'write'
        }
        
        if connection_type == 'telnet':
            if device_type == 'cisco_ios':
                connection_params['device_type'] = 'cisco_ios_telnet'
            elif not device_type.endswith('_telnet'):
                connection_params['device_type'] = f"{device_type}_telnet"
        
        # Try to connect
        try:
            try:
                connection = ConnectHandler(**connection_params)
            except ValueError as e:
                if "Unsupported 'device_type'" in str(e):
                    # Fallback to cisco_ios if device_type not supported
                    connection_params['device_type'] = 'cisco_ios' if connection_type == 'ssh' else 'cisco_ios_telnet'
                    connection = ConnectHandler(**connection_params)
                else:
                    raise
            
            # Enter enable mode if available
            if credentials.get('enable_password'):
                connection.enable()
                
            # Store connection
            with self.connection_lock:
                self.active_connections[connection_id] = connection
                
            return True, "Connected successfully", connection_id
        except Exception as e:
            return False, f"Connection error: {str(e)}", None
    
    def disconnect(self, connection_id):
        """Disconnect from a device."""
        with self.connection_lock:
            if connection_id in self.active_connections:
                try:
                    self.active_connections[connection_id].disconnect()
                except Exception:
                    pass  # Ignore errors on disconnect
                    
                del self.active_connections[connection_id]
                return True, "Disconnected"
            else:
                return False, "Not connected"
    
    def close_all(self):
        """Close all active connections."""
        with self.connection_lock:
            for connection_id, connection in list(self.active_connections.items()):
                try:
                    connection.disconnect()
                except Exception:
                    pass  # Ignore errors on disconnect
                    
            self.active_connections.clear()
    
    def execute_command(self, connection_id, command):
        """
        Execute a command on a connected device.
        
        Args:
            connection_id: Connection identifier
            command: Command to execute
        
        Returns:
            Tuple: (success, output)
        """
        with self.connection_lock:
            if connection_id not in self.active_connections:
                return False, "Not connected"
                
            connection = self.active_connections[connection_id]
        
        try:
            output = connection.send_command(command)
            return True, output
        except Exception as e:
            return False, f"Command execution error: {str(e)}"
    
    def execute_config_commands(self, connection_id, commands):
        """
        Execute configuration commands on a connected device.
        
        Args:
            connection_id: Connection identifier
            commands: List of configuration commands
        
        Returns:
            Tuple: (success, output)
        """
        with self.connection_lock:
            if connection_id not in self.active_connections:
                return False, "Not connected"
                
            connection = self.active_connections[connection_id]
        
        try:
            output = connection.send_config_set(commands)
            return True, output
        except Exception as e:
            return False, f"Command execution error: {str(e)}"
    
    def get_connection_status(self, connection_id):
        """Get connection status."""
        with self.connection_lock:
            if connection_id not in self.active_connections:
                return False, "Not connected"
                
            connection = self.active_connections[connection_id]
        
        try:
            # Check if connection is still active
            connection.find_prompt()
            return True, "Connected"
        except Exception:
            # Connection lost, remove it
            with self.connection_lock:
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
            return False, "Connection lost"
    
    def get_all_connections(self):
        """Get list of all active connections."""
        with self.connection_lock:
            connections = []
            for connection_id in self.active_connections:
                parts = connection_id.split('_')
                ip = parts[0]
                conn_type = parts[1] if len(parts) > 1 else "ssh"
                
                connections.append({
                    'id': connection_id,
                    'ip': ip,
                    'type': conn_type,
                    'status': "Connected"  # We could check actual status here
                })
                
            return connections
    
    def _is_ip_in_subnet(self, ip, subnet):
        """Check if an IP address is in a subnet."""
        try:
            # This is a simplified version; in production, use ipaddress module
            ip_parts = ip.split('.')
            subnet_parts = subnet.split('/')
            subnet_ip = subnet_parts[0]
            subnet_mask = int(subnet_parts[1])
            
            subnet_ip_parts = subnet_ip.split('.')
            
            # Compare the first (subnet_mask // 8) octets
            octets_to_compare = subnet_mask // 8
            for i in range(octets_to_compare):
                if ip_parts[i] != subnet_ip_parts[i]:
                    return False
                    
            # For the partially masked octet, if any
            if subnet_mask % 8 != 0:
                octet_index = subnet_mask // 8
                mask_bits = subnet_mask % 8
                mask = 256 - (1 << (8 - mask_bits))
                
                if int(ip_parts[octet_index]) & mask != int(subnet_ip_parts[octet_index]) & mask:
                    return False
                    
            return True
        except Exception:
            return False 