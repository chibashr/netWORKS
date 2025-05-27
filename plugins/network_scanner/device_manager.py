"""
Device Manager Module

This module handles device management operations for the network scanner plugin.
"""

from loguru import logger
from typing import List, Dict, Optional, Tuple, Any

def match_device(device_manager: Any, host_data: Dict) -> List[Any]:
    """
    Find matching devices in the device manager based on host data.
    
    Args:
        device_manager: The device manager instance
        host_data: Dictionary containing host information
        
    Returns:
        List of matching devices
    """
    matches = []
    ip_address = host_data.get('ip_address')
    mac_address = host_data.get('mac_address')
    
    if not ip_address:
        return matches
        
    # Search by IP address
    ip_matches = device_manager.find_devices(
        lambda d: d.get_property('ip_address') == ip_address
    )
    matches.extend(ip_matches)
    
    # If we have a MAC address, also search by that
    if mac_address:
        mac_matches = device_manager.find_devices(
            lambda d: d.get_property('mac_address') == mac_address
        )
        # Add any new matches not already found by IP
        for device in mac_matches:
            if device not in matches:
                matches.append(device)
                
    return matches

def handle_duplicate_device(device_manager: Any, host_data: Dict, matches: List[Any]) -> Tuple[Any, bool]:
    """
    Handle cases where a device might already exist.
    
    Args:
        device_manager: The device manager instance
        host_data: Dictionary containing host information
        matches: List of matching devices
        
    Returns:
        Tuple of (device, was_merged)
    """
    if not matches:
        return None, False
        
    # If we have exactly one match, use that
    if len(matches) == 1:
        return matches[0], False
        
    # If we have multiple matches, try to merge them
    primary_device = matches[0]
    was_merged = False
    
    try:
        # Merge additional matches into the primary device
        for other_device in matches[1:]:
            # Merge properties
            for prop_name in other_device.get_properties():
                if not primary_device.get_property(prop_name):
                    primary_device.set_property(
                        prop_name,
                        other_device.get_property(prop_name)
                    )
            # Remove the other device
            device_manager.remove_device(other_device)
            was_merged = True
            
    except Exception as e:
        logger.error(f"Error merging devices: {e}")
        
    return primary_device, was_merged

def update_device_properties(device: Any, host_data: Dict) -> None:
    """
    Update device properties with new scan data.
    
    Args:
        device: The device to update
        host_data: Dictionary containing host information
    """
    # Map of host_data keys to device property names
    property_map = {
        'ip_address': 'ip_address',
        'hostname': 'hostname',
        'mac_address': 'mac_address',
        'os': 'os',
        'vendor': 'vendor',
        'status': 'status',
        'last_seen': 'last_seen',
        'open_ports': 'open_ports'
    }
    
    # Update mapped properties
    for host_key, device_key in property_map.items():
        if host_key in host_data:
            device.set_property(device_key, host_data[host_key])
            
    # Update scan-specific properties
    device.set_property('last_scan_time', host_data.get('scan_time'))
    device.set_property('scan_type', host_data.get('scan_type'))
    
    # Add any additional properties from host_data
    for key, value in host_data.items():
        if key not in property_map and not key.startswith('_'):
            device.set_property(key, value)

def create_device_from_scan_data(device_manager: Any, host_data: Dict) -> Any:
    """
    Create a new device from scan data.
    
    Args:
        device_manager: The device manager instance
        host_data: Dictionary containing host information
        
    Returns:
        The created device
    """
    try:
        # Get required properties
        ip_address = host_data.get('ip_address')
        if not ip_address:
            logger.error("Cannot create device without IP address")
            return None
            
        # Create device name from hostname or IP
        device_name = host_data.get('hostname', ip_address)
        
        # Create the device
        device = device_manager.create_device(
            device_type="network_device",
            name=device_name,
            description=f"Device discovered by network scan at {ip_address}"
        )
        
        # Update device properties
        update_device_properties(device, host_data)
        
        # Add to device manager
        device_manager.add_device(device)
        
        return device
        
    except Exception as e:
        logger.error(f"Error creating device from scan data: {e}")
        return None

def suspend_notifications(device_manager: Any) -> None:
    """
    Suspend device manager notifications temporarily.
    
    Args:
        device_manager: The device manager instance
    """
    if hasattr(device_manager, 'suspend_notifications'):
        device_manager.suspend_notifications()

def resume_notifications(device_manager: Any) -> None:
    """
    Resume device manager notifications.
    
    Args:
        device_manager: The device manager instance
    """
    if hasattr(device_manager, 'resume_notifications'):
        device_manager.resume_notifications() 