#!/usr/bin/env python3
# netWORKS - Object-Based Database Manager

import os
import json
import uuid
import logging
import datetime
import time
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Type, TypeVar

from .models import BaseModel, Device, DeviceHistory, PluginData
from .object_store import ObjectStore

T = TypeVar('T', bound=BaseModel)

class ObjectDatabaseManager:
    """Object-based database manager for netWORKS.
    
    This class wraps the ObjectStore to provide a compatible interface
    for existing code that uses the ObjectDatabaseManager.
    """
    
    def __init__(self, main_window=None, db_path=None):
        """Initialize the object database manager.
        
        Args:
            main_window: Reference to the main window (optional)
            db_path: Custom database path (optional) - Not used for actual database,
                     but retained for API compatibility. Used as the base directory for JSON storage.
        """
        self.logger = logging.getLogger(__name__)
        self.main_window = main_window
        
        # Calculate data directory from db_path if provided
        data_dir = None
        if db_path:
            path = Path(db_path)
            data_dir = path.parent / "objects"
        
        # Initialize object store
        self.store = ObjectStore(main_window, data_dir)
        
        # For compatibility with existing code
        self.db_path = Path(db_path) if db_path else Path("data/device_database.db")
        
        self.logger.info("Object database manager initialized")
    
    def _init_database(self) -> bool:
        """Initialize the database (now just returns True since ObjectStore handles initialization).
        
        Returns:
            bool: True if successful, False otherwise
        """
        return True
    
    # Device operations
    
    def add_device(self, device: Union[Device, Dict[str, Any]]) -> bool:
        """Add or update a device in the database.
        
        Args:
            device: Device object or dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.store.add_device(device)
    
    def get_device(self, device_ip: str) -> Optional[Device]:
        """Get a device by IP address.
        
        Args:
            device_ip: Device IP address
            
        Returns:
            Device object or None if not found
        """
        return self.store.get_device(device_ip)
    
    def get_devices(self) -> List[Device]:
        """Get all devices.
        
        Returns:
            List of Device objects
        """
        return self.store.get_devices()
    
    def remove_device(self, device_id: str) -> bool:
        """Remove a device from the database.
        
        Args:
            device_id: Device ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.store.remove_device(device_id)
    
    def get_device_history(self, device_ip: str) -> List[DeviceHistory]:
        """Get history for a device.
        
        Args:
            device_ip: Device IP address
            
        Returns:
            List of DeviceHistory objects
        """
        return self.store.get_device_history(device_ip)
    
    def search_devices(self, query: str) -> List[Device]:
        """Search for devices by various criteria.
        
        Args:
            query: Search query (IP, hostname, tag, etc.)
            
        Returns:
            List of matching Device objects
        """
        return self.store.search_devices(query)
    
    # Plugin data operations
    
    def store_plugin_data(self, plugin_id: str, key: str, value: Any) -> bool:
        """Store plugin-specific data in the database.
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            value: Data value (will be JSON encoded)
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.store.store_plugin_data(plugin_id, key, value)
    
    def get_plugin_data(self, plugin_id: str, key: str, default: Any = None) -> Any:
        """Get plugin-specific data from the database.
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            default: Default value if not found
            
        Returns:
            Any: The stored data or default value
        """
        return self.store.get_plugin_data(plugin_id, key, default)
    
    def get_all_plugin_data(self, plugin_id: str) -> Dict[str, Any]:
        """Get all data for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Dict of key-value pairs
        """
        return self.store.get_all_plugin_data(plugin_id)
    
    def clear_plugin_data(self, plugin_id: str) -> bool:
        """Clear all data for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.store.clear_plugin_data(plugin_id)
    
    # Legacy compatibility methods
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table (compatibility method).
        
        This method returns predefined columns for known tables to maintain compatibility.
        
        Args:
            table_name: Table name
            
        Returns:
            List of column names
        """
        # Return predefined columns for known tables
        if table_name == 'devices':
            return ['id', 'ip', 'mac', 'hostname', 'vendor', 'os', 'first_seen', 
                    'last_seen', 'status', 'metadata', 'tags', 'notes', 'device_type']
        elif table_name == 'device_history':
            return ['id', 'device_id', 'ip', 'event_type', 'event_data', 'timestamp']
        elif table_name == 'plugin_data':
            return ['plugin_id', 'key', 'value']
        elif table_name == 'app_settings':
            return ['key', 'value']
        else:
            self.logger.warning(f"Unknown table requested: {table_name}")
            return []
    
    def add_column(self, table_name: str, column_name: str, column_type: str, default_value: Any = None) -> bool:
        """Add a column to a table (compatibility method).
        
        This method now does nothing but return success to maintain compatibility.
        
        Args:
            table_name: Table name
            column_name: Column name
            column_type: Column type
            default_value: Default value for the column
            
        Returns:
            bool: Always True
        """
        # This operation is not needed in the object model
        self.logger.info(f"Ignoring add_column request for {table_name}.{column_name} (not needed in object model)")
        return True
    
    def execute_query(self, query: str, params=None):
        """Execute a SQL query (compatibility method).
        
        This method provides limited SQL-like query capability by parsing the query
        and routing to appropriate ObjectStore methods.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Query results
        """
        self.logger.debug(f"SQL compatibility: {query}")
        
        # Handle SELECT queries
        if query.strip().upper().startswith("SELECT"):
            # Very basic query parsing - only handles simple queries
            if "FROM devices" in query:
                # Return all devices
                devices = self.store.get_devices()
                return [device.to_dict() for device in devices]
            elif "FROM plugin_data" in query:
                # Extract plugin_id and key if specified
                if "WHERE plugin_id = ? AND key = ?" in query and params and len(params) >= 2:
                    plugin_id, key = params[0], params[1]
                    value = self.store.get_plugin_data(plugin_id, key)
                    if value is not None:
                        return [{'value': json.dumps(value)}]
                    return []
                # This is a limited implementation
                self.logger.warning(f"Unsupported plugin_data query: {query}")
                return []
            else:
                self.logger.warning(f"Unsupported SELECT query: {query}")
                return []
                
        # Handle INSERT and UPDATE queries (simplified)
        elif query.strip().upper().startswith("INSERT") or query.strip().upper().startswith("UPDATE"):
            # For plugin_data operations
            if "plugin_data" in query and params and len(params) >= 3:
                # Extract parameters differently based on query type
                if query.strip().upper().startswith("INSERT"):
                    # INSERT INTO plugin_data (plugin_id, key, value) VALUES (?, ?, ?)
                    plugin_id, key, value = params
                elif "UPDATE plugin_data SET value = ? WHERE plugin_id = ? AND key = ?" in query:
                    # UPDATE plugin_data SET value = ? WHERE plugin_id = ? AND key = ?
                    value, plugin_id, key = params
                else:
                    self.logger.warning(f"Unsupported plugin_data update query: {query}")
                    return False
                
                # Parse the JSON value
                try:
                    parsed_value = json.loads(value)
                    return self.store.store_plugin_data(plugin_id, key, parsed_value)
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON value in plugin_data query: {value}")
                    return False
            
            self.logger.warning(f"Unsupported INSERT/UPDATE query: {query}")
            return False
            
        # Handle DELETE queries
        elif query.strip().upper().startswith("DELETE"):
            if "FROM plugin_data WHERE plugin_id = ?" in query and params and len(params) >= 1:
                plugin_id = params[0]
                return self.store.clear_plugin_data(plugin_id)
            
            self.logger.warning(f"Unsupported DELETE query: {query}")
            return False
            
        # Handle other queries
        else:
            self.logger.warning(f"Unsupported query type: {query}")
            return False
    
    # Backup and restore methods
    
    def backup_database(self, backup_dir=None) -> bool:
        """Create a backup of the database.
        
        Args:
            backup_dir: Directory to store backups (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.store.backup(backup_dir)
    
    def restore_database(self, backup_path) -> bool:
        """Restore the database from a backup.
        
        Args:
            backup_path: Path to backup directory
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.store.restore(backup_path)
    
    # Migration methods - not needed for the new object model
    
    @classmethod
    def migrate_from_old_db(cls, old_db_path: str, new_db_path: str = None) -> 'ObjectDatabaseManager':
        """Migrate data from old database to new object-based database.
        
        This method is retained for API compatibility but delegates to migrate_from_sql_db.
        
        Args:
            old_db_path: Path to old database
            new_db_path: Path to new database (optional)
            
        Returns:
            New ObjectDatabaseManager instance
        """
        return cls.migrate_from_sql_db(old_db_path, new_db_path)
    
    @classmethod
    def migrate_from_sql_db(cls, sql_db_path: str, new_db_path: str = None) -> 'ObjectDatabaseManager':
        """Migrate data from a SQLite database to the new object-based database.
        
        Args:
            sql_db_path: Path to SQLite database
            new_db_path: Path to new database directory (optional)
            
        Returns:
            New ObjectDatabaseManager instance
        """
        import sqlite3
        
        # Create new database instance
        new_db = cls(db_path=new_db_path)
        
        # Connect to old database
        try:
            old_conn = sqlite3.connect(sql_db_path)
            old_conn.row_factory = sqlite3.Row
            old_cursor = old_conn.cursor()
            
            # Migrate devices
            old_cursor.execute("SELECT * FROM devices")
            device_records = [dict(row) for row in old_cursor.fetchall()]
            
            for device_record in device_records:
                # Process JSON fields
                if 'metadata' in device_record and device_record['metadata']:
                    try:
                        device_record['metadata'] = json.loads(device_record['metadata'])
                    except:
                        device_record['metadata'] = {}
                
                if 'tags' in device_record and device_record['tags']:
                    try:
                        device_record['tags'] = json.loads(device_record['tags'])
                    except:
                        device_record['tags'] = []
                
                # Create Device object and add to new database
                device = Device.from_dict(device_record)
                new_db.add_device(device)
            
            # Migrate device history
            old_cursor.execute("SELECT * FROM device_history")
            history_records = [dict(row) for row in old_cursor.fetchall()]
            
            for history_record in history_records:
                # Process JSON fields
                if 'event_data' in history_record and history_record['event_data']:
                    try:
                        history_record['event_data'] = json.loads(history_record['event_data'])
                    except:
                        history_record['event_data'] = {}
                
                # Create DeviceHistory object
                history = DeviceHistory.from_dict(history_record)
                
                # Add to new database
                key = f"{history.ip}_{history.timestamp}"
                new_db.store.device_history.add(key, history)
            
            # Migrate plugin data
            old_cursor.execute("SELECT * FROM plugin_data")
            plugin_data_records = [dict(row) for row in old_cursor.fetchall()]
            
            for plugin_data_record in plugin_data_records:
                # Process JSON fields
                if 'value' in plugin_data_record and plugin_data_record['value']:
                    try:
                        value = json.loads(plugin_data_record['value'])
                    except:
                        value = plugin_data_record['value']
                else:
                    value = None
                
                # Store plugin data in new database
                new_db.store_plugin_data(
                    plugin_data_record['plugin_id'],
                    plugin_data_record['key'],
                    value
                )
            
            old_conn.close()
            
            # Save all collections to make sure everything is persisted
            new_db.store.devices.save()
            new_db.store.device_history.save()
            new_db.store.plugin_data.save()
            
            logging.info(f"Successfully migrated database from {sql_db_path} to object store")
            return new_db
            
        except Exception as e:
            logging.error(f"Error migrating database: {str(e)}")
            return new_db 