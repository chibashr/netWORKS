#!/usr/bin/env python3
# Network Device Manager - Device Manager

import os
import json
from pathlib import Path

class DeviceManager:
    """
    Manages device metadata, types, and properties.
    Interacts with the main netWORKS database.
    """
    
    def __init__(self, plugin_api, credential_manager):
        self.api = plugin_api
        self.credential_manager = credential_manager
        self.db_manager = None  # Will be initialized when main_window is ready
        
        # Default output directory for command outputs
        plugin_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = plugin_dir / "data" / "outputs"
        self.output_dir.mkdir(exist_ok=True)
        
        # Will initialize database when main window is ready
        if self.api.main_window is not None:
            self.initialize_db()
        else:
            self.api.on_main_window_ready(self.initialize_db)
    
    def initialize_db(self):
        """Initialize database manager and setup tables."""
        try:
            self.db_manager = self.api.main_window.database_manager
            
            # Check if the database manager has the methods we need
            if hasattr(self.db_manager, 'get_table_columns'):
                # Ensure device_type column exists
                self._ensure_device_type_column()
            else:
                self.api.log("Database manager doesn't have get_table_columns method. Skipping column check.", level="WARNING")
                
            if hasattr(self.db_manager, 'execute_query'):
                # Ensure command_outputs table exists
                self._ensure_command_outputs_table()
            else:
                self.api.log("Database manager doesn't have execute_query method. Skipping table creation.", level="WARNING")
                
        except Exception as e:
            self.api.log(f"Error initializing database: {str(e)}", level="ERROR")
    
    def _ensure_device_type_column(self):
        """Ensure device_type column exists in devices table."""
        try:
            # Check if column exists
            columns = self.db_manager.get_table_columns('devices')
            if 'device_type' not in columns:
                # Add device_type column
                self.db_manager.execute_query(
                    "ALTER TABLE devices ADD COLUMN device_type TEXT DEFAULT 'unknown'"
                )
        except Exception as e:
            self.api.log(f"Error ensuring device_type column: {str(e)}", level="ERROR")
    
    def _ensure_command_outputs_table(self):
        """Ensure command_outputs table exists."""
        try:
            # Create table if it doesn't exist
            self.db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS command_outputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_ip TEXT NOT NULL,
                    command TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    output_type TEXT DEFAULT 'text',
                    comment TEXT,
                    FOREIGN KEY (device_ip) REFERENCES devices(ip) ON DELETE CASCADE
                )
            """)
        except Exception as e:
            self.api.log(f"Error ensuring command_outputs table: {str(e)}", level="ERROR")
    
    def get_device(self, ip):
        """Get a device by IP address."""
        try:
            result = self.db_manager.execute_query(
                "SELECT * FROM devices WHERE ip = ?",
                [ip]
            )
            if result and len(result) > 0:
                return result[0]
            return None
        except Exception as e:
            self.api.log(f"Error getting device: {str(e)}", level="ERROR")
            return None
    
    def ensure_device_type_column(self):
        """Ensure the 'device_type' column exists in the devices table. If missing, add it automatically."""
        try:
            # Check if the column exists
            columns = []
            if hasattr(self.db_manager, 'get_table_columns'):
                columns = self.db_manager.get_table_columns('devices')
            else:
                # Fallback: query PRAGMA table_info with robust error handling
                try:
                    result = self.db_manager.execute_query("PRAGMA table_info(devices)")
                    if not isinstance(result, list):
                        self.api.log(f"PRAGMA table_info(devices) did not return a list. Got: {type(result)}", level="ERROR")
                        # Force creation of column anyway as a fallback
                        self.db_manager.execute_query(
                            "ALTER TABLE devices ADD COLUMN device_type TEXT DEFAULT 'unknown'"
                        )
                        self.api.log("Attempted to add device_type column without checking if it exists.", level="WARNING")
                        return
                    columns = [row['name'] for row in result if isinstance(row, dict) and 'name' in row]
                except Exception as pragma_error:
                    self.api.log(f"Error checking table schema: {str(pragma_error)}", level="ERROR")
                    # Try to create the column regardless of the error
                    try:
                        self.db_manager.execute_query(
                            "ALTER TABLE devices ADD COLUMN device_type TEXT DEFAULT 'unknown'"
                        )
                        self.api.log("Attempted to add device_type column after schema check error.", level="WARNING")
                    except:
                        pass
                    return
                    
            if 'device_type' not in columns:
                self.api.log("'device_type' column missing in devices table. Adding it automatically...", level="WARNING")
                self.db_manager.execute_query(
                    "ALTER TABLE devices ADD COLUMN device_type TEXT DEFAULT 'unknown'"
                )
                self.api.log("'device_type' column added to devices table.", level="INFO")
        except Exception as e:
            self.api.log(f"Error ensuring device_type column: {str(e)}", level="ERROR")
            # Last resort - try to add the column in a separate try/except block
            try:
                self.db_manager.execute_query(
                    "ALTER TABLE devices ADD COLUMN device_type TEXT DEFAULT 'unknown'"
                )
                self.api.log("Attempted to add device_type column in exception handler.", level="WARNING")
            except Exception as alter_error:
                self.api.log(f"Final attempt to add device_type column failed: {str(alter_error)}", level="ERROR")

    # Call this function before any update/select involving device_type
    # Example: in update_device_type and get_devices_by_type
    def update_device_type(self, ip, device_type):
        self.ensure_device_type_column()
        try:
            self.db_manager.execute_query(
                "UPDATE devices SET device_type = ? WHERE ip = ?",
                [device_type, ip]
            )
            return True
        except Exception as e:
            self.api.log(f"Error updating device type: {str(e)}", level="ERROR")
            return False

    def get_devices_by_type(self, device_type):
        self.ensure_device_type_column()
        try:
            return self.db_manager.execute_query(
                "SELECT * FROM devices WHERE device_type = ?",
                [device_type]
            )
        except Exception as e:
            self.api.log(f"Error getting devices by type: {str(e)}", level="ERROR")
            return []

    def get_device_types(self):
        self.ensure_device_type_column()
        try:
            result = self.db_manager.execute_query(
                "SELECT DISTINCT device_type FROM devices"
            )
            return [row['device_type'] for row in result if row['device_type']]
        except Exception as e:
            self.api.log(f"Error getting device types: {str(e)}", level="ERROR")
            return []
    
    def add_command_output(self, device_ip, command, output_path, output_type="text", comment=None):
        """Add a command output record."""
        try:
            self.db_manager.execute_query(
                """
                INSERT INTO command_outputs 
                (device_ip, command, output_path, output_type, comment)
                VALUES (?, ?, ?, ?, ?)
                """,
                [device_ip, command, output_path, output_type, comment]
            )
            return True
        except Exception as e:
            self.api.log(f"Error adding command output: {str(e)}", level="ERROR")
            return False
    
    def get_command_outputs(self, device_ip=None):
        """Get command outputs for a device."""
        try:
            if device_ip:
                return self.db_manager.execute_query(
                    "SELECT * FROM command_outputs WHERE device_ip = ? ORDER BY timestamp DESC",
                    [device_ip]
                )
            else:
                return self.db_manager.execute_query(
                    "SELECT * FROM command_outputs ORDER BY timestamp DESC"
                )
        except Exception as e:
            self.api.log(f"Error getting command outputs: {str(e)}", level="ERROR")
            return []
    
    def remove_command_output(self, output_id):
        """Remove a command output record."""
        try:
            # Get the output path before deleting
            result = self.db_manager.execute_query(
                "SELECT output_path FROM command_outputs WHERE id = ?",
                [output_id]
            )
            
            if result and len(result) > 0:
                output_path = result[0]['output_path']
                
                # Delete from database
                self.db_manager.execute_query(
                    "DELETE FROM command_outputs WHERE id = ?",
                    [output_id]
                )
                
                # Return the path so the file can be deleted if needed
                return True, output_path
            
            return False, None
        except Exception as e:
            self.api.log(f"Error removing command output: {str(e)}", level="ERROR")
            return False, None
    
    def get_devices_by_subnet(self, subnet):
        """Get all devices in a subnet."""
        try:
            # This is a simplified implementation and would need to be 
            # enhanced with proper subnet calculations
            subnet_prefix = subnet.split('/')[0].rsplit('.', 1)[0]
            return self.db_manager.execute_query(
                "SELECT * FROM devices WHERE ip LIKE ?",
                [f"{subnet_prefix}.%"]
            )
        except Exception as e:
            self.api.log(f"Error getting devices by subnet: {str(e)}", level="ERROR")
            return []
    
    def update_device(self, device):
        """Update a device's properties in the database.
        
        Args:
            device: Dict containing the device data to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            if not device or not device.get('ip'):
                self.api.log("Cannot update device: missing IP address", level="ERROR")
                return False
                
            # Log the update operation
            self.api.log(f"Updating device in database: {device.get('ip')}", level="DEBUG")
            
            # Check if we have a database manager
            if not hasattr(self, 'db_manager') or not self.db_manager:
                self.api.log("Database manager not initialized yet", level="WARNING")
                return False
                
            # Update device type if provided
            if 'device_type' in device:
                self.update_device_type(device['ip'], device['device_type'])
                self.api.log(f"Updated device type to {device['device_type']}", level="DEBUG")
            
            # Update device in database
            result = self.db_manager.execute_query(
                """
                UPDATE devices SET 
                hostname = COALESCE(?, hostname),
                mac = COALESCE(?, mac),
                vendor = COALESCE(?, vendor)
                WHERE ip = ?
                """,
                [
                    device.get('hostname'), 
                    device.get('mac'), 
                    device.get('vendor'),
                    device.get('ip')
                ]
            )
            
            # Update metadata if present
            if 'metadata' in device and isinstance(device['metadata'], dict):
                # Get existing metadata
                existing_device = self.get_device(device['ip'])
                if existing_device and 'metadata' in existing_device:
                    # Merge metadata
                    existing_metadata = existing_device['metadata'] or {}
                    updated_metadata = {**existing_metadata, **device['metadata']}
                    
                    # Store updated metadata
                    self.db_manager.execute_query(
                        "UPDATE devices SET metadata = ? WHERE ip = ?",
                        [json.dumps(updated_metadata), device['ip']]
                    )
                    self.api.log(f"Updated device metadata for {device['ip']}", level="DEBUG")
            
            self.api.log(f"Device {device['ip']} updated successfully", level="DEBUG")
            return True
        except Exception as e:
            self.api.log(f"Error updating device: {str(e)}", level="ERROR")
            return False 