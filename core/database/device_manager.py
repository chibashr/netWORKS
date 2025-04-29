#!/usr/bin/env python3
# netWORKS - Device Database Manager

import os
import json
import uuid
import sqlite3
import logging
import datetime
import time
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
    
    def _initialize_database(self) -> bool:
        """Initialize the SQLite database. Alias for _init_database for backward compatibility.
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self._init_database()
    
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
            # Use the retry mechanism for database operations
            return self._execute_with_retry(self._add_device_internal, device)
        except Exception as e:
            self.logger.error(f"Error adding device to database: {str(e)}")
            return False
    
    def _add_device_internal(self, device: Dict[str, Any]) -> bool:
        """Internal method to add or update a device with transaction handling.
        
        Args:
            device: Device data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
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
        
        # Connect to database with transaction
        conn = sqlite3.connect(self.db_path)
        try:
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
            return True
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
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
            # Use the retry mechanism for database operations
            return self._execute_with_retry(self._store_plugin_data_internal, plugin_id, key, value)
        except Exception as e:
            self.logger.error(f"Error storing plugin data: {str(e)}")
            return False
    
    def _store_plugin_data_internal(self, plugin_id: str, key: str, value: Any) -> bool:
        """Internal method to store plugin-specific data with transaction handling.
        
        Args:
            plugin_id: Plugin identifier
            key: Data key
            value: Data value (will be JSON encoded)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Convert value to JSON string
        value_json = json.dumps(value)
        
        # Connect to database with transaction
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
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
            return True
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
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
    
    def save_device_groups(self, device_groups: Dict[str, List[str]]) -> bool:
        """Save device groups to the database.
        
        Args:
            device_groups: Dictionary of group names to lists of device IDs
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Store as plugin data for the core app
            return self.store_plugin_data('core', 'device_groups', device_groups)
        except Exception as e:
            self.logger.error(f"Error saving device groups: {str(e)}")
            return False
    
    def get_device_groups(self) -> Dict[str, List[str]]:
        """Get device groups from the database.
        
        Returns:
            Dict[str, List[str]]: Dictionary of group names to lists of device IDs
        """
        try:
            return self.get_plugin_data('core', 'device_groups', {})
        except Exception as e:
            self.logger.error(f"Error getting device groups: {str(e)}")
            return {}
    
    def _execute_with_retry(self, func, *args, max_retries=3, **kwargs):
        """Execute a database function with retry logic.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            max_retries: Maximum number of retries
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Any: Result of the function call
        """
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except sqlite3.DatabaseError as e:
                if "database disk image is malformed" in str(e) and attempt < max_retries - 1:
                    self.logger.warning(f"Database error on attempt {attempt+1}, trying to recover: {str(e)}")
                    self._repair_database()
                else:
                    raise
    
    def _repair_database(self):
        """Attempt to repair a corrupted database."""
        try:
            self.logger.info("Attempting to repair database...")
            # Create a backup first
            import shutil
            backup_path = f"{self.db_path}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"Created database backup at {backup_path}")
            
            # Try to repair with integrity check
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchall()
                conn.close()
                
                if result[0][0] != "ok":
                    self.logger.warning(f"Integrity check failed: {result}")
                    # If integrity check fails, try to dump and reload
                    self._dump_and_reload_database()
                else:
                    self.logger.info("Database integrity check passed")
                    
            except sqlite3.DatabaseError:
                # If we can't even run the integrity check, try more aggressive recovery
                self.logger.warning("Cannot perform integrity check, trying dump and reload")
                self._dump_and_reload_database()
                
        except Exception as e:
            self.logger.error(f"Error repairing database: {str(e)}")
            # As a last resort, completely reset the database
            self._create_new_database()
    
    def _check_and_repair_database(self):
        """
        Perform SQLite integrity checks and attempt repair.
        
        Returns:
            bool: True if repair successful, False otherwise
        """
        try:
            # Close any existing connection
            try:
                if hasattr(self, 'conn') and self.conn:
                    self.conn.close()
            except Exception:
                pass
                
            # Backup the database before attempting repair
            backup_path = f"{self.db_path}.integrity_check.{int(time.time())}"
            import shutil
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"Created backup before integrity check at {backup_path}")
            
            # Connect and run integrity check
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchall()
            
            if result[0][0] == "ok":
                self.logger.info("Database integrity check passed")
                
                # Run vacuum to optimize
                cursor.execute("VACUUM")
                conn.commit()
                
                # Run integrity_check again to verify
                cursor.execute("PRAGMA integrity_check")
                final_check = cursor.fetchall()
                
                if final_check[0][0] == "ok":
                    self.logger.info("Database optimized successfully")
                    conn.close()
                    return True
                else:
                    self.logger.warning("Database failed integrity check after optimization")
                    conn.close()
                    return False
            else:
                self.logger.warning(f"Database integrity check failed: {result}")
                conn.close()
                return False
                
        except Exception as e:
            self.logger.error(f"Error during database integrity check: {str(e)}")
            return False
    
    def _create_new_database(self):
        """Create a completely new database when repair attempts fail."""
        try:
            self.logger.warning("Creating a new database as a last resort")
            
            # Backup current database if it exists
            import os
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}.corrupted_{int(time.time())}"
                try:
                    os.rename(self.db_path, backup_path)
                    self.logger.info(f"Backed up corrupted database to {backup_path}")
                except Exception as e:
                    self.logger.error(f"Failed to back up corrupted database: {str(e)}")
                    # Try to remove it if we can't rename
                    try:
                        os.remove(self.db_path)
                        self.logger.info("Removed corrupted database")
                    except Exception as e2:
                        self.logger.error(f"Failed to remove corrupted database: {str(e2)}")
            
            # Connect to a fresh database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create all tables
            cursor.execute('''CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS devices (
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
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS device_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                ip TEXT,
                event_type TEXT,
                event_data TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS plugin_data (
                plugin_id TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY (plugin_id, key)
            )''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("New database created successfully")
            
            # Re-initialize the connection
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            
        except Exception as e:
            self.logger.critical(f"Failed to create new database: {str(e)}")
            raise RuntimeError("Database repair failed completely. Application may be unstable.")
    
    def _dump_and_reload_database(self):
        """
        Attempt to recover database by dumping to SQL and reloading.
        This can sometimes recover from corruption that integrity_check cannot fix.
        
        Returns:
            bool: True if successful, False otherwise
        """
        import subprocess
        import os
        import tempfile
        
        try:
            self.logger.info("Attempting database recovery via dump and reload")
            
            # Create backup first
            backup_path = f"{self.db_path}.dump_recovery.{int(time.time())}"
            import shutil
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"Created backup before dump recovery at {backup_path}")
            
            # Close any current connection
            try:
                if hasattr(self, 'conn') and self.conn:
                    self.conn.close()
            except Exception:
                pass
            
            # Create temporary directory for dump
            temp_dir = tempfile.mkdtemp()
            dump_file = os.path.join(temp_dir, "dump.sql")
            new_db = os.path.join(temp_dir, "new.db")
            
            try:
                # Dump the database to SQL
                self.logger.info(f"Dumping database to {dump_file}")
                
                try:
                    # Try using the sqlite3 command-line tool if available
                    subprocess.run(["sqlite3", self.db_path, f".output {dump_file}", ".dump"], 
                                  check=True, capture_output=True, text=True, timeout=60)
                except (subprocess.SubprocessError, FileNotFoundError):
                    # Fall back to Python implementation if sqlite3 command not available
                    conn = sqlite3.connect(self.db_path)
                    with open(dump_file, 'w') as f:
                        for line in conn.iterdump():
                            f.write(f"{line}\n")
                    conn.close()
                
                # Check if the dump contains anything
                if os.path.getsize(dump_file) < 100:  # If dump is too small, it failed
                    self.logger.error("Database dump failed or produced minimal output")
                    return False
                
                # Create a new database from the dump
                self.logger.info(f"Creating new database from dump")
                conn = sqlite3.connect(new_db)
                
                with open(dump_file, 'r') as f:
                    conn.executescript(f.read())
                conn.commit()
                conn.close()
                
                # Verify the new database
                conn = sqlite3.connect(new_db)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchall()
                conn.close()
                
                if result[0][0] != "ok":
                    self.logger.error(f"New database failed integrity check: {result}")
                    return False
                
                # Replace the old database with the new one
                try:
                    if hasattr(self, 'conn') and self.conn:
                        self.conn.close()
                except Exception:
                    pass
                
                shutil.copy2(new_db, self.db_path)
                self.logger.info("Successfully restored database from dump")
                
                # Re-initialize the connection
                self._initialize_database()
                return True
                
            finally:
                # Clean up temporary files
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    self.logger.warning(f"Error cleaning up temp files: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Error during database dump and reload: {str(e)}")
            return False
    
    def execute_query(self, query, params=None):
        """Execute a SQL query and return results as a list of dicts."""
        try:
            # Use the retry mechanism for database operations
            return self._execute_with_retry(self._execute_query_internal, query, params)
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            return []
            
    def _execute_query_internal(self, query, params=None):
        """Internal method to execute SQL query with transaction handling."""
        conn = sqlite3.connect(self.db_path)
        try:
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
                
            return result
        except Exception as e:
            if not query.strip().upper().startswith("SELECT"):
                conn.rollback()
            raise
        finally:
            conn.close()
    
    def _handle_database_error(self, error):
        """
        Handle database errors by attempting to repair the database.
        This will be called when a database error is detected.
        """
        self.logger.error(f"Database error detected: {str(error)}")
        
        error_str = str(error).lower()
        
        # Try to recover from common SQLite errors
        if "database disk image is malformed" in error_str or "database is locked" in error_str or "no such table" in error_str:
            self.logger.warning("Attempting to repair database...")
            
            try:
                # Try to close current connection if it exists
                try:
                    if self.conn:
                        self.conn.close()
                except Exception as close_err:
                    self.logger.warning(f"Error closing connection: {str(close_err)}")
                
                # Check database integrity first
                if "database disk image is malformed" in error_str:
                    try:
                        self.logger.info("Checking database integrity...")
                        repair_result = self._check_and_repair_database()
                        if repair_result:
                            self.logger.info("Database integrity check and repair completed successfully")
                            return True
                    except Exception as integrity_err:
                        self.logger.error(f"Failed to check/repair database integrity: {str(integrity_err)}")
                
                # Try to dump and reload the database
                try:
                    self.logger.info("Attempting to dump and reload database...")
                    if self._dump_and_reload_database():
                        self.logger.info("Database successfully dumped and reloaded")
                        return True
                except Exception as dump_err:
                    self.logger.error(f"Failed to dump and reload database: {str(dump_err)}")
                
                # If all else fails, create a new database
                self._create_new_database()
                return True
                
            except Exception as repair_err:
                self.logger.critical(f"All database repair attempts failed: {str(repair_err)}")
                return False
        else:
            self.logger.error(f"Unhandled database error: {str(error)}")
            return False 