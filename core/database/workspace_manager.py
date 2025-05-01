#!/usr/bin/env python3
# netWORKS - Workspace Database Manager

import os
import json
import uuid
import logging
import datetime
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

class WorkspaceDBManager:
    """Database manager for workspace operations.
    
    This class provides an interface for storing and retrieving devices,
    scan results, and other workspace data from the database.
    """
    
    def __init__(self, workspace_id=None, main_window=None):
        """Initialize the workspace database manager.
        
        Args:
            workspace_id (str, optional): ID of the workspace to manage
            main_window: Reference to the main window (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.main_window = main_window
        
        # Set workspace ID
        self.workspace_id = workspace_id
        
        # Database directory setup
        self.db_dir = Path("data/workspaces")
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database connection
        self.db_conn = None
        self.db_path = None
        
        if workspace_id:
            self.set_workspace(workspace_id)
        
        self.logger.debug("Workspace database manager initialized")
    
    def set_workspace(self, workspace_id: str) -> bool:
        """Set the current workspace.
        
        Args:
            workspace_id: ID of the workspace to manage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Close previous connection if exists
            if self.db_conn:
                self.db_conn.close()
                self.db_conn = None
            
            # Set new workspace ID
            self.workspace_id = workspace_id
            
            # Set database path
            workspace_dir = self.db_dir / workspace_id
            workspace_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = workspace_dir / "database.db"
            
            # Initialize database
            self._init_database()
            
            self.logger.info(f"Set workspace ID to {workspace_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting workspace: {str(e)}")
            return False
    
    def _init_database(self) -> bool:
        """Initialize the SQLite database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db_conn = sqlite3.connect(self.db_path)
            cursor = self.db_conn.cursor()
            
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
            
            # Create device_groups table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_groups (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                created TEXT DEFAULT CURRENT_TIMESTAMP,
                devices TEXT,
                metadata TEXT
            )
            ''')
            
            # Create scan_history table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id TEXT PRIMARY KEY,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                end_time TEXT,
                interface TEXT,
                ip_range TEXT,
                scan_type TEXT,
                duration REAL,
                devices_found INTEGER,
                status TEXT,
                metadata TEXT
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
            
            self.db_conn.commit()
            self.logger.debug(f"Initialized database at {self.db_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            return False
    
    def add_device(self, device: Dict) -> bool:
        """Add or update a device.
        
        Args:
            device: Device data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return False
        
        try:
            cursor = self.db_conn.cursor()
            
            # Ensure device has an ID
            if 'id' not in device or not device['id']:
                device['id'] = str(uuid.uuid4())
            
            # Convert metadata, tags to JSON if they exist
            metadata = json.dumps(device.get('metadata', {})) if device.get('metadata') else '{}'
            tags = json.dumps(device.get('tags', [])) if device.get('tags') else '[]'
            
            # Add or update the device
            cursor.execute('''
            INSERT OR REPLACE INTO devices (
                id, ip, mac, hostname, vendor, os, 
                first_seen, last_seen, status, metadata, tags, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device.get('id'),
                device.get('ip'),
                device.get('mac'),
                device.get('hostname'),
                device.get('vendor'),
                device.get('os'),
                device.get('first_seen', datetime.datetime.now().isoformat()),
                device.get('last_seen', datetime.datetime.now().isoformat()),
                device.get('status', 'active'),
                metadata,
                tags,
                device.get('notes', '')
            ))
            
            self.db_conn.commit()
            self.logger.debug(f"Added/updated device {device.get('ip')} ({device.get('id')})")
            return True
        except Exception as e:
            self.logger.error(f"Error adding device: {str(e)}")
            return False
    
    def get_device(self, device_id: str) -> Optional[Dict]:
        """Get a device by ID.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device data dictionary or None if not found
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return None
        
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute('''
            SELECT id, ip, mac, hostname, vendor, os, 
                  first_seen, last_seen, status, metadata, tags, notes 
            FROM devices 
            WHERE id = ?
            ''', (device_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Convert to dictionary
            device = {
                'id': row[0],
                'ip': row[1],
                'mac': row[2],
                'hostname': row[3],
                'vendor': row[4],
                'os': row[5],
                'first_seen': row[6],
                'last_seen': row[7],
                'status': row[8],
                'metadata': json.loads(row[9]) if row[9] else {},
                'tags': json.loads(row[10]) if row[10] else [],
                'notes': row[11]
            }
            
            return device
        except Exception as e:
            self.logger.error(f"Error getting device {device_id}: {str(e)}")
            return None
    
    def get_devices(self) -> List[Dict]:
        """Get all devices.
        
        Returns:
            List of device data dictionaries
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return []
        
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute('''
            SELECT id, ip, mac, hostname, vendor, os, 
                  first_seen, last_seen, status, metadata, tags, notes 
            FROM devices
            ''')
            
            devices = []
            for row in cursor.fetchall():
                device = {
                    'id': row[0],
                    'ip': row[1],
                    'mac': row[2],
                    'hostname': row[3],
                    'vendor': row[4],
                    'os': row[5],
                    'first_seen': row[6],
                    'last_seen': row[7],
                    'status': row[8],
                    'metadata': json.loads(row[9]) if row[9] else {},
                    'tags': json.loads(row[10]) if row[10] else [],
                    'notes': row[11]
                }
                devices.append(device)
            
            self.logger.debug(f"Retrieved {len(devices)} devices")
            return devices
        except Exception as e:
            self.logger.error(f"Error getting devices: {str(e)}")
            return []
    
    def delete_device(self, device_id: str) -> bool:
        """Delete a device.
        
        Args:
            device_id: Device ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return False
        
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute('DELETE FROM devices WHERE id = ?', (device_id,))
            
            self.db_conn.commit()
            self.logger.debug(f"Deleted device {device_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting device {device_id}: {str(e)}")
            return False
    
    def add_device_group(self, group: Dict) -> bool:
        """Add or update a device group.
        
        Args:
            group: Device group data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return False
        
        try:
            cursor = self.db_conn.cursor()
            
            # Ensure group has an ID
            if 'id' not in group or not group['id']:
                group['id'] = str(uuid.uuid4())
            
            # Convert devices, metadata to JSON if they exist
            devices = json.dumps(group.get('devices', [])) if group.get('devices') else '[]'
            metadata = json.dumps(group.get('metadata', {})) if group.get('metadata') else '{}'
            
            # Add or update the group
            cursor.execute('''
            INSERT OR REPLACE INTO device_groups (
                id, name, description, created, devices, metadata
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                group.get('id'),
                group.get('name'),
                group.get('description', ''),
                group.get('created', datetime.datetime.now().isoformat()),
                devices,
                metadata
            ))
            
            self.db_conn.commit()
            self.logger.debug(f"Added/updated device group {group.get('name')} ({group.get('id')})")
            return True
        except Exception as e:
            self.logger.error(f"Error adding device group: {str(e)}")
            return False
    
    def get_device_groups(self) -> Dict[str, Dict]:
        """Get all device groups.
        
        Returns:
            Dictionary of device group data dictionaries (id -> group)
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return {}
        
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute('''
            SELECT id, name, description, created, devices, metadata 
            FROM device_groups
            ''')
            
            groups = {}
            for row in cursor.fetchall():
                group = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'created': row[3],
                    'devices': json.loads(row[4]) if row[4] else [],
                    'metadata': json.loads(row[5]) if row[5] else {}
                }
                groups[row[0]] = group
            
            self.logger.debug(f"Retrieved {len(groups)} device groups")
            return groups
        except Exception as e:
            self.logger.error(f"Error getting device groups: {str(e)}")
            return {}
    
    def delete_device_group(self, group_id: str) -> bool:
        """Delete a device group.
        
        Args:
            group_id: Device group ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return False
        
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute('DELETE FROM device_groups WHERE id = ?', (group_id,))
            
            self.db_conn.commit()
            self.logger.debug(f"Deleted device group {group_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting device group {group_id}: {str(e)}")
            return False
    
    def add_scan_result(self, scan: Dict) -> bool:
        """Add a scan result.
        
        Args:
            scan: Scan result data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return False
        
        try:
            cursor = self.db_conn.cursor()
            
            # Ensure scan has an ID
            if 'id' not in scan or not scan['id']:
                scan['id'] = str(uuid.uuid4())
            
            # Convert metadata to JSON if it exists
            metadata = json.dumps(scan.get('metadata', {})) if scan.get('metadata') else '{}'
            
            # Add the scan result
            cursor.execute('''
            INSERT OR REPLACE INTO scan_history (
                id, timestamp, end_time, interface, ip_range, scan_type,
                duration, devices_found, status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                scan.get('id'),
                scan.get('timestamp', datetime.datetime.now().isoformat()),
                scan.get('end_time'),
                scan.get('interface'),
                scan.get('ip_range'),
                scan.get('scan_type'),
                scan.get('duration', 0.0),
                scan.get('devices_found', 0),
                scan.get('status', 'completed'),
                metadata
            ))
            
            self.db_conn.commit()
            self.logger.debug(f"Added scan result {scan.get('id')}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding scan result: {str(e)}")
            return False
    
    def get_scan_history(self) -> List[Dict]:
        """Get all scan results.
        
        Returns:
            List of scan result data dictionaries
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return []
        
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute('''
            SELECT id, timestamp, end_time, interface, ip_range, scan_type,
                  duration, devices_found, status, metadata
            FROM scan_history
            ''')
            
            scans = []
            for row in cursor.fetchall():
                scan = {
                    'id': row[0],
                    'timestamp': row[1],
                    'end_time': row[2],
                    'interface': row[3],
                    'ip_range': row[4],
                    'scan_type': row[5],
                    'duration': row[6],
                    'devices_found': row[7],
                    'status': row[8],
                    'metadata': json.loads(row[9]) if row[9] else {}
                }
                scans.append(scan)
            
            self.logger.debug(f"Retrieved {len(scans)} scan results")
            return scans
        except Exception as e:
            self.logger.error(f"Error getting scan history: {str(e)}")
            return []
    
    def get_plugin_data(self, plugin_id: str, key: str = None) -> Any:
        """Get plugin data.
        
        Args:
            plugin_id: Plugin ID
            key: Data key (optional). If None, returns all data for the plugin.
            
        Returns:
            Plugin data value or dictionary of values
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return None if key else {}
        
        try:
            cursor = self.db_conn.cursor()
            
            if key:
                # Get specific key
                cursor.execute('''
                SELECT value FROM plugin_data 
                WHERE plugin_id = ? AND key = ?
                ''', (plugin_id, key))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return json.loads(row[0]) if row[0] else None
            else:
                # Get all keys for plugin
                cursor.execute('''
                SELECT key, value FROM plugin_data 
                WHERE plugin_id = ?
                ''', (plugin_id,))
                
                data = {}
                for row in cursor.fetchall():
                    data[row[0]] = json.loads(row[1]) if row[1] else None
                
                return data
        except Exception as e:
            self.logger.error(f"Error getting plugin data for {plugin_id}: {str(e)}")
            return None if key else {}
    
    def store_plugin_data(self, plugin_id: str, key: str, value: Any) -> bool:
        """Store plugin data.
        
        Args:
            plugin_id: Plugin ID
            key: Data key
            value: Data value (will be JSON serialized)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_conn:
            self.logger.error("Database not initialized")
            return False
        
        try:
            cursor = self.db_conn.cursor()
            
            # JSON serialize the value
            value_json = json.dumps(value)
            
            # Store the data
            cursor.execute('''
            INSERT OR REPLACE INTO plugin_data (
                plugin_id, key, value
            ) VALUES (?, ?, ?)
            ''', (plugin_id, key, value_json))
            
            self.db_conn.commit()
            self.logger.debug(f"Stored plugin data {plugin_id}.{key}")
            return True
        except Exception as e:
            self.logger.error(f"Error storing plugin data {plugin_id}.{key}: {str(e)}")
            return False
    
    def close(self):
        """Close the database connection."""
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None
            self.logger.debug("Closed database connection")
    
    def __del__(self):
        """Ensure database connection is closed on deletion."""
        self.close() 