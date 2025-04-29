#!/usr/bin/env python3
# Example Plugin - Object Database Usage

import json
from core.database.models import Device, PluginData

class DeviceStatsAnalyzer:
    """Example class showing how to use the object-based database."""
    
    def __init__(self, plugin_api):
        """Initialize with plugin API.
        
        Args:
            plugin_api: Plugin API instance
        """
        self.api = plugin_api
        self.db_manager = None
        
        # Initialize when main window is ready
        if self.api.main_window:
            self.initialize()
        else:
            self.api.on_main_window_ready(self.initialize)
    
    def initialize(self):
        """Initialize with database manager from main window."""
        if not self.api.main_window:
            self.api.log("Main window not available", level="ERROR")
            return
            
        self.db_manager = self.api.main_window.database_manager
        self.api.log("Device Stats Analyzer initialized", level="INFO")
    
    def analyze_online_status(self):
        """Analyze online status of devices."""
        if not self.db_manager:
            self.api.log("Database manager not available", level="ERROR")
            return
        
        # Check if object-based API is available
        if hasattr(self.db_manager, 'get_device_objects'):
            # Use the object-based API
            devices = self.db_manager.get_device_objects()
            
            online_count = len([d for d in devices if d.status == 'active'])
            offline_count = len([d for d in devices if d.status == 'inactive'])
            
            # Store the analysis results using PluginData
            stats = {
                'online_count': online_count,
                'offline_count': offline_count,
                'total_count': len(devices),
                'online_percentage': (online_count / len(devices) * 100) if devices else 0
            }
            
            self.db_manager.store_plugin_data('device-stats-analyzer', 'online_stats', stats)
            self.api.log(f"Analyzed device status: {online_count} online, {offline_count} offline", level="INFO")
            
            return stats
        else:
            # Fall back to legacy API
            self.api.log("Object-based database API not available, using legacy API", level="WARNING")
            
            devices = self.db_manager.get_devices()
            
            online_count = len([d for d in devices if d.get('status') == 'active'])
            offline_count = len([d for d in devices if d.get('status') == 'inactive'])
            
            stats = {
                'online_count': online_count,
                'offline_count': offline_count,
                'total_count': len(devices),
                'online_percentage': (online_count / len(devices) * 100) if devices else 0
            }
            
            self.db_manager.store_plugin_data('device-stats-analyzer', 'online_stats', stats)
            self.api.log(f"Analyzed device status: {online_count} online, {offline_count} offline", level="INFO")
            
            return stats
    
    def get_vendors_by_device_count(self):
        """Get a breakdown of devices by vendor."""
        if not self.db_manager:
            self.api.log("Database manager not available", level="ERROR")
            return {}
        
        # Check if object-based API is available
        if hasattr(self.db_manager, 'get_device_objects'):
            # Use the object-based API
            devices = self.db_manager.get_device_objects()
            
            vendor_counts = {}
            for device in devices:
                vendor = device.vendor or 'Unknown'
                vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
            
            # Store the analysis results
            self.db_manager.store_plugin_data('device-stats-analyzer', 'vendor_stats', vendor_counts)
            
            return vendor_counts
        else:
            # Fall back to legacy API
            devices = self.db_manager.get_devices()
            
            vendor_counts = {}
            for device in devices:
                vendor = device.get('vendor') or 'Unknown'
                vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
            
            # Store the analysis results
            self.db_manager.store_plugin_data('device-stats-analyzer', 'vendor_stats', vendor_counts)
            
            return vendor_counts
    
    def tag_devices_by_subnet(self):
        """Tag devices by their subnet."""
        if not self.db_manager:
            self.api.log("Database manager not available", level="ERROR")
            return
        
        # Check if object-based API is available
        if hasattr(self.db_manager, 'get_device_objects'):
            # Use the object-based API
            devices = self.db_manager.get_device_objects()
            
            modified_count = 0
            for device in devices:
                if device.ip:
                    # Extract subnet (first three octets)
                    subnet = '.'.join(device.ip.split('.')[:3])
                    subnet_tag = f"subnet-{subnet}"
                    
                    # Add subnet tag if not already present
                    if subnet_tag not in device.tags:
                        device.add_tag(subnet_tag)
                        self.db_manager.add_device_object(device)
                        modified_count += 1
            
            self.api.log(f"Tagged {modified_count} devices with subnet information", level="INFO")
        else:
            # Fall back to legacy API
            self.api.log("Object-based database API not available, using legacy API", level="WARNING")
            
            devices = self.db_manager.get_devices()
            
            modified_count = 0
            for device in devices:
                if 'ip' in device and device['ip']:
                    # Extract subnet (first three octets)
                    subnet = '.'.join(device['ip'].split('.')[:3])
                    subnet_tag = f"subnet-{subnet}"
                    
                    # Get current tags
                    tags = json.loads(device.get('tags', '[]')) if isinstance(device.get('tags'), str) else device.get('tags', [])
                    
                    # Add subnet tag if not already present
                    if subnet_tag not in tags:
                        tags.append(subnet_tag)
                        device['tags'] = tags
                        self.db_manager.add_device(device)
                        modified_count += 1
            
            self.api.log(f"Tagged {modified_count} devices with subnet information", level="INFO")


# Example plugin entry point
def init_plugin(plugin_api):
    """Initialize the plugin.
    
    Args:
        plugin_api: The plugin API
        
    Returns:
        Plugin instance
    """
    return DeviceStatsAnalyzer(plugin_api) 