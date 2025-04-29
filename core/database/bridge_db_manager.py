#!/usr/bin/env python3
# netWORKS - Database Bridge Manager

import os
import json
import logging
from typing import Dict, List, Any, Union, Optional

from .object_db_manager import ObjectDatabaseManager
from .models import Device, DeviceHistory, PluginData


class BridgeDatabaseManager:
    """Bridge between legacy database API and new object-based database.
    
    This class provides backward compatibility for plugins that use the
    old database API, while internally using the new object-based database.
    """
    
    def __init__(self, main_window=None, db_path=None):
        """Initialize the bridge database manager.
        
        Args:
            main_window: Reference to the main window (optional)
            db_path: Custom database path (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.main_window = main_window
        
        # Initialize the object-based database manager
        self.object_db = ObjectDatabaseManager(main_window, db_path)
        self.db_path = self.object_db.db_path
        
        self.logger.info("Bridge database manager initialized")
    
    # Compatibility methods for legacy API
    
    def _init_database(self) -> bool:
        """Initialize the database (delegates to object_db)."""
        return self.object_db._init_database()
    
    def add_device(self, device: Dict[str, Any]) -> bool:
        """Add or update a device (legacy API).
        
        Args:
            device: Device data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.object_db.add_device(device)
    
    def get_device(self, device_ip: str) -> Optional[Dict[str, Any]]:
        """Get a device by IP address (legacy API).
        
        Args:
            device_ip: Device IP address
            
        Returns:
            Device data dictionary or None if not found
        """
        device = self.object_db.get_device(device_ip)
        return device.to_dict() if device else None
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices (legacy API).
        
        Returns:
            List of device data dictionaries
        """
        devices = self.object_db.get_devices()
        return [device.to_dict() for device in devices]
    
    def remove_device(self, device_id: str) -> bool:
        """Remove a device (legacy API).
        
        Args:
            device_id: Device ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.object_db.remove_device(device_id)
    
    def get_device_history(self, device_ip: str) -> List[Dict[str, Any]]:
        """Get history for a device (legacy API).
        
        Args:
            device_ip: Device IP address
            
        Returns:
            List of history event dictionaries
        """
        history_items = self.object_db.get_device_history(device_ip)
        return [item.to_dict() for item in history_items]
    
    def search_devices(self, query: str) -> List[Dict[str, Any]]:
        """Search for devices (legacy API).
        
        Args:
            query: Search query
            
        Returns:
            List of matching device dictionaries
        """
        devices = self.object_db.search_devices(query)
        return [device.to_dict() for device in devices]
    
    def store_plugin_data(self, plugin_id: str, key: str, value: Any) -> bool:
        """Store plugin data (legacy API).
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            value: Data value
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.object_db.store_plugin_data(plugin_id, key, value)
    
    def get_plugin_data(self, plugin_id: str, key: str, default: Any = None) -> Any:
        """Get plugin data (legacy API).
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            default: Default value if not found
            
        Returns:
            Stored value or default
        """
        return self.object_db.get_plugin_data(plugin_id, key, default)
    
    def get_device_groups(self) -> Dict[str, List[str]]:
        """Get all device groups (legacy API).
        
        Returns:
            Dictionary with group names as keys and lists of device IDs as values
        """
        try:
            # Device groups are stored as plugin data with plugin_id 'core' and key 'device_groups'
            groups = self.object_db.get_plugin_data('core', 'device_groups', {})
            
            # Ensure it's a dictionary
            if not isinstance(groups, dict):
                self.logger.warning("Device groups data is not a dictionary, returning empty dictionary")
                return {}
                
            return groups
        except Exception as e:
            self.logger.error(f"Error getting device groups: {str(e)}")
            return {}
    
    def clear_plugin_data(self, plugin_id: str) -> bool:
        """Clear plugin data (legacy API).
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.object_db.clear_plugin_data(plugin_id)
    
    def execute_query(self, query: str, params=None):
        """Execute a raw SQL query (legacy API).
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Query results
        """
        return self.object_db.execute_query(query, params)
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table (legacy API).
        
        Args:
            table_name: Table name
            
        Returns:
            List of column names
        """
        return self.object_db.get_table_columns(table_name)
    
    def save_device(self, device: Dict[str, Any]) -> bool:
        """Save a device to the database (alias for add_device).
        
        Args:
            device: Device data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.add_device(device)
    
    # New object-based API methods
    
    def get_device_object(self, device_ip: str) -> Optional[Device]:
        """Get a device as a Device object.
        
        Args:
            device_ip: Device IP address
            
        Returns:
            Device object or None if not found
        """
        return self.object_db.get_device(device_ip)
    
    def get_device_objects(self) -> List[Device]:
        """Get all devices as Device objects.
        
        Returns:
            List of Device objects
        """
        return self.object_db.get_devices()
    
    def add_device_object(self, device: Device) -> bool:
        """Add or update a Device object.
        
        Args:
            device: Device object
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.object_db.add_device(device)
    
    def search_device_objects(self, query: str) -> List[Device]:
        """Search for devices and return Device objects.
        
        Args:
            query: Search query
            
        Returns:
            List of matching Device objects
        """
        return self.object_db.search_devices(query)
    
    def get_plugin_data_object(self, plugin_id: str, key: str) -> Optional[PluginData]:
        """Get plugin data as a PluginData object.
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            
        Returns:
            PluginData object or None if not found
        """
        value = self.get_plugin_data(plugin_id, key)
        if value is not None:
            return PluginData(plugin_id=plugin_id, key=key, value=value)
        return None
    
    # Backup and restore methods
    
    def backup_database(self, backup_dir=None) -> bool:
        """Create a backup of the database.
        
        Args:
            backup_dir: Directory to store backups (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.object_db.backup_database(backup_dir)
    
    def restore_database(self, backup_path) -> bool:
        """Restore the database from a backup.
        
        Args:
            backup_path: Path to backup directory
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.object_db.restore_database(backup_path)
    
    # Migration method
    
    @classmethod
    def migrate_from_legacy_db(cls, legacy_db_path: str, new_db_path: str = None) -> 'BridgeDatabaseManager':
        """Migrate from legacy database to new object-based database.
        
        Args:
            legacy_db_path: Path to legacy database
            new_db_path: Path to new database (optional)
            
        Returns:
            New BridgeDatabaseManager instance
        """
        # Use the migration method from ObjectDatabaseManager
        object_db = ObjectDatabaseManager.migrate_from_sql_db(legacy_db_path, new_db_path)
        
        # Create and return a new bridge manager
        bridge = cls(db_path=new_db_path)
        bridge.object_db = object_db
        bridge.db_path = object_db.db_path
        
        return bridge 