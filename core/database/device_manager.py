#!/usr/bin/env python3
# netWORKS - Device Database Manager

import os
import json
import uuid
import sqlite3
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Union, Optional

class DeviceDatabaseManager:
    """Manages device database operations for netWORKS."""
    
    def __init__(self, main_window=None):
        """Initialize the device database manager.
        
        Args:
            main_window: Reference to the main window (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.main_window = main_window
        
        # Initialize database path
        self.db_path = Path("data/device_database.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        self.logger.info("Device database manager initialized")
    
    def _init_database(self) -> bool:
        """Initialize the SQLite database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create workspace settings table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            ''')
            
            # Create devices table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                ip TEXT,
                mac TEXT,
                hostname TEXT,
                vendor TEXT,
                os TEXT,
                first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                metadata TEXT,
                tags TEXT,
                notes TEXT
            )
            ''')
            
            # Create device_history table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                ip TEXT,
                event_type TEXT,
                event_data TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
            ''')
            
            # Create plugin_data table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_data (
                plugin_id TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY (plugin_id, key)
            )
            ''')
            
            conn.commit()
            conn.close()
            return True
        
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            return False
    
    def add_device(self, device: Dict[str, Any]) -> bool:
        """Add or update a device in the database.
        
        Args:
            device: Device data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not device.get('ip'):
            self.logger.error("Cannot add device without IP address")
            return False
            
        try:
            # Ensure device has an ID
            if 'id' not in device:
                device['id'] = str(uuid.uuid4())
            
            # Set timestamps if missing
            now = datetime.datetime.now().isoformat()
            if 'first_seen' not in device:
                device['first_seen'] = now
            if 'last_seen' not in device:
                device['last_seen'] = now
            
            # Ensure metadata is a dictionary
            if 'metadata' not in device or not isinstance(device['metadata'], dict):
                device['metadata'] = {}
            
            # Prepare for storage
            metadata = json.dumps(device.get('metadata', {}))
            tags = json.dumps(device.get('tags', []))
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if device already exists
            cursor.execute("SELECT id FROM devices WHERE ip = ?", (device['ip'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing device
                cursor.execute('''
                UPDATE devices SET
                    mac = ?,
                    hostname = ?,
                    vendor = ?,
                    os = ?,
                    last_seen = ?,
                    status = ?,
                    metadata = ?,
                    tags = ?,
                    notes = ?
                WHERE ip = ?
                ''', (
                    device.get('mac'),
                    device.get('hostname'),
                    device.get('vendor'),
                    device.get('os'),
                    device.get('last_seen', now),
                    device.get('status', 'active'),
                    metadata,
                    tags,
                    device.get('notes'),
                    device['ip']
                ))
                
                # Log update event
                cursor.execute('''
                INSERT INTO device_history (device_id, ip, event_type, event_data)
                VALUES (?, ?, ?, ?)
                ''', (
                    existing[0], 
                    device['ip'], 
                    'update', 
                    json.dumps({
                        'timestamp': now,
                        'source': device.get('metadata', {}).get('update_source', 'unknown')
                    })
                ))
                
            else:
                # Insert new device
                cursor.execute('''
                INSERT INTO devices (
                    id, ip, mac, hostname, vendor, os,
                    first_seen, last_seen, status, metadata, tags, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    device['id'],
                    device['ip'],
                    device.get('mac'),
                    device.get('hostname'),
                    device.get('vendor'),
                    device.get('os'),
                    device.get('first_seen', now),
                    device.get('last_seen', now),
                    device.get('status', 'active'),
                    metadata,
                    tags,
                    device.get('notes')
                ))
                
                # Log discovery event
                cursor.execute('''
                INSERT INTO device_history (device_id, ip, event_type, event_data)
                VALUES (?, ?, ?, ?)
                ''', (
                    device['id'], 
                    device['ip'], 
                    'discovery', 
                    json.dumps({
                        'timestamp': now,
                        'source': device.get('metadata', {}).get('discovery_source', 'unknown')
                    })
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding device to database: {str(e)}")
            return False
    
    def remove_device(self, device_id: str) -> bool:
        """Remove a device from the database.
        
        Args:
            device_id: Device ID to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get device IP before deletion for history
            cursor.execute("SELECT ip FROM devices WHERE id = ?", (device_id,))
            result = cursor.fetchone()
            
            if not result:
                self.logger.warning(f"Device not found: {device_id}")
                return False
                
            device_ip = result[0]
            now = datetime.datetime.now().isoformat()
            
            # Log removal event in history
            cursor.execute('''
            INSERT INTO device_history (device_id, ip, event_type, event_data)
            VALUES (?, ?, ?, ?)
            ''', (
                device_id, 
                device_ip, 
                'removal', 
                json.dumps({
                    'timestamp': now
                })
            ))
            
            # Delete the device
            cursor.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing device: {str(e)}")
            return False
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices in the database.
        
        Returns:
            List[Dict]: List of devices
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM devices')
            devices = []
            
            for row in cursor.fetchall():
                device = dict(row)
                
                # Convert JSON strings back to Python objects
                device['metadata'] = json.loads(device['metadata'])
                device['tags'] = json.loads(device['tags'])
                devices.append(device)
            
            conn.close()
            return devices
            
        except Exception as e:
            self.logger.error(f"Error getting devices from database: {str(e)}")
            return []
    
    def get_device(self, device_ip: str) -> Optional[Dict[str, Any]]:
        """Get a device by IP address.
        
        Args:
            device_ip: IP address of the device
            
        Returns:
            Dict or None: Device data or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM devices WHERE ip = ?', (device_ip,))
            row = cursor.fetchone()
            
            if row:
                device = dict(row)
                
                # Convert JSON strings back to Python objects
                device['metadata'] = json.loads(device['metadata'])
                device['tags'] = json.loads(device['tags'])
                
                conn.close()
                return device
            
            conn.close()
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting device from database: {str(e)}")
            return None
    
    def get_device_history(self, device_ip: str) -> List[Dict[str, Any]]:
        """Get history for a device.
        
        Args:
            device_ip: IP address of the device
            
        Returns:
            List[Dict]: List of history events
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM device_history 
            WHERE ip = ? 
            ORDER BY timestamp DESC
            ''', (device_ip,))
            
            history = []
            for row in cursor.fetchall():
                event = dict(row)
                
                # Convert JSON strings back to Python objects
                event['event_data'] = json.loads(event['event_data'])
                history.append(event)
            
            conn.close()
            return history
            
        except Exception as e:
            self.logger.error(f"Error getting device history: {str(e)}")
            return []
    
    def search_devices(self, query: str) -> List[Dict[str, Any]]:
        """Search for devices matching a query.
        
        Args:
            query: Search query
            
        Returns:
            List[Dict]: List of matching devices
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Search in multiple fields
            search = f"%{query}%"
            cursor.execute('''
            SELECT * FROM devices 
            WHERE ip LIKE ? 
            OR hostname LIKE ? 
            OR mac LIKE ? 
            OR vendor LIKE ? 
            OR os LIKE ? 
            OR notes LIKE ?
            ''', (search, search, search, search, search, search))
            
            devices = []
            for row in cursor.fetchall():
                device = dict(row)
                
                # Convert JSON strings back to Python objects
                device['metadata'] = json.loads(device['metadata'])
                device['tags'] = json.loads(device['tags'])
                devices.append(device)
            
            conn.close()
            return devices
            
        except Exception as e:
            self.logger.error(f"Error searching devices: {str(e)}")
            return []
    
    def store_plugin_data(self, plugin_id: str, key: str, value: Any) -> bool:
        """Store plugin-specific data in the database.
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            value: Data value (will be JSON encoded)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert value to JSON string
            value_json = json.dumps(value)
            
            # Check if key already exists
            cursor.execute(
                "SELECT COUNT(*) FROM plugin_data WHERE plugin_id = ? AND key = ?", 
                (plugin_id, key)
            )
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                # Update existing data
                cursor.execute(
                    "UPDATE plugin_data SET value = ? WHERE plugin_id = ? AND key = ?",
                    (value_json, plugin_id, key)
                )
            else:
                # Insert new data
                cursor.execute(
                    "INSERT INTO plugin_data (plugin_id, key, value) VALUES (?, ?, ?)",
                    (plugin_id, key, value_json)
                )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing plugin data: {str(e)}")
            return False
    
    def get_plugin_data(self, plugin_id: str, key: str, default: Any = None) -> Any:
        """Get plugin-specific data from the database.
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            default: Default value if not found
            
        Returns:
            Any: The stored data or default value
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT value FROM plugin_data WHERE plugin_id = ? AND key = ?", 
                (plugin_id, key)
            )
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return json.loads(result[0])
            else:
                return default
                
        except Exception as e:
            self.logger.error(f"Error getting plugin data: {str(e)}")
            return default
    
    def clear_plugin_data(self, plugin_id: str) -> bool:
        """Clear all data for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM plugin_data WHERE plugin_id = ?", 
                (plugin_id,)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing plugin data: {str(e)}")
            return False
    
    def save_device(self, device: Dict[str, Any]) -> bool:
        """Save a device to the database (alias for add_device).
        
        Args:
            device: Device data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.add_device(device)
    
    def execute_query(self, query, params=None):
        """Execute a SQL query and return results as a list of dicts."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if params is None:
                params = []
            cursor.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
            else:
                conn.commit()
                result = cursor.rowcount
            conn.close()
            return result
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            return [] 