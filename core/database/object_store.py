#!/usr/bin/env python3
# netWORKS - Object Store

import os
import json
import uuid
import logging
import datetime
import time
import shutil
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Type, TypeVar, Generic

from .models import BaseModel, Device, DeviceHistory, PluginData

T = TypeVar('T', bound=BaseModel)

class ObjectCollection(Generic[T]):
    """A collection of objects of a specific type."""
    
    def __init__(self, store: 'ObjectStore', model_class: Type[T], collection_name: str):
        """Initialize the collection.
        
        Args:
            store: The parent ObjectStore instance
            model_class: The class of objects stored in the collection
            collection_name: The name of the collection
        """
        self.store = store
        self.model_class = model_class
        self.collection_name = collection_name
        self.data_path = store.data_dir / f"{collection_name}.json"
        self.objects = {}
        self.load()
        
    def load(self) -> None:
        """Load objects from disk."""
        if not self.data_path.exists():
            self.objects = {}
            return
            
        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)
                self.objects = {
                    key: self.model_class.from_dict(value) 
                    for key, value in data.items()
                }
        except Exception as e:
            self.store.logger.error(f"Error loading collection {self.collection_name}: {str(e)}")
            # Create a backup of the corrupted file
            if self.data_path.exists():
                backup_path = self.data_path.with_suffix(f".json.backup.{int(time.time())}")
                shutil.copy2(self.data_path, backup_path)
                self.store.logger.info(f"Created backup of corrupted file at {backup_path}")
            self.objects = {}
    
    def save(self) -> None:
        """Save objects to disk."""
        try:
            # Create parent directory if it doesn't exist
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert objects to dictionaries
            data = {
                key: obj.to_dict() if hasattr(obj, 'to_dict') else obj 
                for key, obj in self.objects.items()
            }
            
            # Save to file with atomic write pattern
            temp_path = self.data_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Rename the temporary file to the actual file
            temp_path.replace(self.data_path)
        except Exception as e:
            self.store.logger.error(f"Error saving collection {self.collection_name}: {str(e)}")
    
    def add(self, key: str, obj: T) -> None:
        """Add or update an object in the collection.
        
        Args:
            key: Object key
            obj: Object to add or update
        """
        self.objects[key] = obj
        self.save()
    
    def get(self, key: str) -> Optional[T]:
        """Get an object from the collection.
        
        Args:
            key: Object key
            
        Returns:
            The object or None if not found
        """
        return self.objects.get(key)
    
    def get_all(self) -> List[T]:
        """Get all objects in the collection.
        
        Returns:
            List of all objects
        """
        return list(self.objects.values())
    
    def remove(self, key: str) -> bool:
        """Remove an object from the collection.
        
        Args:
            key: Object key
            
        Returns:
            True if the object was removed, False otherwise
        """
        if key in self.objects:
            del self.objects[key]
            self.save()
            return True
        return False
    
    def clear(self) -> None:
        """Clear all objects from the collection."""
        self.objects = {}
        self.save()
    
    def filter(self, predicate) -> List[T]:
        """Filter objects based on a predicate function.
        
        Args:
            predicate: Function that takes an object and returns a boolean
            
        Returns:
            List of objects for which the predicate returns True
        """
        return [obj for obj in self.objects.values() if predicate(obj)]


class ObjectStore:
    """File-based object store for netWORKS."""
    
    def __init__(self, main_window=None, data_dir=None):
        """Initialize the object store.
        
        Args:
            main_window: Reference to the main window (optional)
            data_dir: Custom data directory (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.main_window = main_window
        
        # Initialize data directory
        self.data_dir = Path(data_dir) if data_dir else Path("data/objects")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Collections
        self.devices = ObjectCollection(self, Device, "devices")
        self.device_history = ObjectCollection(self, DeviceHistory, "device_history")
        self.plugin_data = ObjectCollection(self, PluginData, "plugin_data")
        self.app_settings = ObjectCollection(self, BaseModel, "app_settings")
        
        self.logger.info("Object store initialized")
    
    # Device operations
    
    def add_device(self, device: Union[Device, Dict[str, Any]]) -> bool:
        """Add or update a device in the store.
        
        Args:
            device: Device object or dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert dictionary to Device object if needed
            if isinstance(device, dict):
                device_obj = Device.from_dict(device)
            else:
                device_obj = device
            
            # Validate required fields
            if not device_obj.ip:
                self.logger.error("Cannot add device without IP address")
                return False
            
            # Update timestamps
            now = datetime.datetime.now().isoformat()
            device_obj.last_seen = now
            
            # Check if device already exists
            existing_device = self.get_device(device_obj.ip)
            
            # Add or update device
            self.devices.add(device_obj.ip, device_obj)
            
            # Add history entry
            history_entry = DeviceHistory(
                device_id=device_obj.id,
                ip=device_obj.ip,
                event_type="update" if existing_device else "discovery",
                event_data={
                    "timestamp": now,
                    "source": device_obj.get_metadata('update_source' if existing_device else 'discovery_source', 'unknown')
                }
            )
            history_key = f"{device_obj.ip}_{now}"
            self.device_history.add(history_key, history_entry)
            
            return True
        except Exception as e:
            self.logger.error(f"Error adding device to store: {str(e)}")
            return False
    
    def get_device(self, device_ip: str) -> Optional[Device]:
        """Get a device by IP address.
        
        Args:
            device_ip: Device IP address
            
        Returns:
            Device object or None if not found
        """
        return self.devices.get(device_ip)
    
    def get_devices(self) -> List[Device]:
        """Get all devices.
        
        Returns:
            List of Device objects
        """
        return self.devices.get_all()
    
    def remove_device(self, device_id: str) -> bool:
        """Remove a device from the store.
        
        Args:
            device_id: Device ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Find the device by ID
        for device_ip, device in self.devices.objects.items():
            if device.id == device_id:
                return self.devices.remove(device_ip)
        return False
    
    def get_device_history(self, device_ip: str) -> List[DeviceHistory]:
        """Get history for a device.
        
        Args:
            device_ip: Device IP address
            
        Returns:
            List of DeviceHistory objects
        """
        return self.device_history.filter(lambda h: h.ip == device_ip)
    
    def search_devices(self, query: str) -> List[Device]:
        """Search for devices by various criteria.
        
        Args:
            query: Search query (IP, hostname, tag, etc.)
            
        Returns:
            List of matching Device objects
        """
        query = query.lower()
        
        def match_device(device):
            # Check basic fields
            if query in (device.ip or "").lower():
                return True
            if query in (device.hostname or "").lower():
                return True
            if query in (device.vendor or "").lower():
                return True
            if query in (device.mac or "").lower():
                return True
            if query in (device.os or "").lower():
                return True
                
            # Check tags
            for tag in device.tags:
                if query in tag.lower():
                    return True
                    
            # Check metadata
            for key, value in device.metadata.items():
                if query in str(key).lower() or query in str(value).lower():
                    return True
                    
            return False
        
        return self.devices.filter(match_device)
    
    # Plugin data operations
    
    def store_plugin_data(self, plugin_id: str, key: str, value: Any) -> bool:
        """Store plugin-specific data in the store.
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            value: Data value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            plugin_data = PluginData(plugin_id=plugin_id, key=key, value=value)
            self.plugin_data.add(f"{plugin_id}:{key}", plugin_data)
            return True
        except Exception as e:
            self.logger.error(f"Error storing plugin data: {str(e)}")
            return False
    
    def get_plugin_data(self, plugin_id: str, key: str, default: Any = None) -> Any:
        """Get plugin-specific data from the store.
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            default: Default value if not found
            
        Returns:
            Any: The stored data or default value
        """
        try:
            plugin_data = self.plugin_data.get(f"{plugin_id}:{key}")
            return plugin_data.value if plugin_data else default
        except Exception as e:
            self.logger.error(f"Error getting plugin data: {str(e)}")
            return default
    
    def get_all_plugin_data(self, plugin_id: str) -> Dict[str, Any]:
        """Get all data for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Dict of key-value pairs
        """
        try:
            data = {}
            for key, plugin_data in self.plugin_data.objects.items():
                if key.startswith(f"{plugin_id}:"):
                    data_key = key.split(':', 1)[1]
                    data[data_key] = plugin_data.value
            return data
        except Exception as e:
            self.logger.error(f"Error getting all plugin data: {str(e)}")
            return {}
    
    def clear_plugin_data(self, plugin_id: str) -> bool:
        """Clear all data for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all keys for this plugin
            keys_to_remove = [
                key for key in self.plugin_data.objects.keys()
                if key.startswith(f"{plugin_id}:")
            ]
            
            # Remove each key
            for key in keys_to_remove:
                self.plugin_data.remove(key)
                
            return True
        except Exception as e:
            self.logger.error(f"Error clearing plugin data: {str(e)}")
            return False
    
    # Application settings
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set an application setting.
        
        Args:
            key: Setting key
            value: Setting value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            setting = BaseModel(key=key, value=value)
            self.app_settings.add(key, setting)
            return True
        except Exception as e:
            self.logger.error(f"Error setting application setting: {str(e)}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get an application setting.
        
        Args:
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        try:
            setting = self.app_settings.get(key)
            return setting.get_attribute('value') if setting else default
        except Exception as e:
            self.logger.error(f"Error getting application setting: {str(e)}")
            return default
    
    # Maintenance operations
    
    def backup(self, backup_dir=None) -> bool:
        """Create a backup of all store data.
        
        Args:
            backup_dir: Directory to store backups (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Default to backup_db directory
            if backup_dir is None:
                backup_dir = Path("backup_db")
            else:
                backup_dir = Path(backup_dir)
                
            # Create backup directory
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped backup directory
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy all data files
            for item in self.data_dir.glob("*.json"):
                shutil.copy2(item, backup_path)
                
            self.logger.info(f"Created backup at {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            return False
    
    def restore(self, backup_path) -> bool:
        """Restore data from a backup.
        
        Args:
            backup_path: Path to backup directory
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_path)
            
            # Verify backup directory exists
            if not backup_path.exists() or not backup_path.is_dir():
                self.logger.error(f"Backup directory {backup_path} does not exist")
                return False
                
            # Create backup of current data
            self.backup()
            
            # Clear current data
            for item in self.data_dir.glob("*.json"):
                item.unlink()
                
            # Copy backup files
            for item in backup_path.glob("*.json"):
                shutil.copy2(item, self.data_dir)
                
            # Reload collections
            self.devices.load()
            self.device_history.load()
            self.plugin_data.load()
            self.app_settings.load()
            
            self.logger.info(f"Restored from backup at {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error restoring from backup: {str(e)}")
            return False 