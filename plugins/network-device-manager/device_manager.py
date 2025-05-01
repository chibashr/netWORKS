#!/usr/bin/env python3
# Network Device Manager - Device Manager

import os
import json
from pathlib import Path
import csv
import datetime
from core.database.models import Device  # Import the Device model

class DeviceManager:
    """
    Manages device metadata, types, and properties.
    Interacts with the main netWORKS database.
    """
    
    def __init__(self, plugin_api, credential_manager):
        self.api = plugin_api
        self.credential_manager = credential_manager
        self.db_manager = None  # Will be initialized when main_window is ready
        
        # Get the workspace root path instead of the plugin-specific path
        app_root = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")))
        
        # Use the root data directory for all storage
        self.data_dir = app_root / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Create network-device-manager subdirectory in root data folder
        self.plugin_data_dir = self.data_dir / "network-device-manager"
        self.plugin_data_dir.mkdir(exist_ok=True)
        
        # Default output directory for command outputs - organized by device
        self.output_dir = self.data_dir / "outputs"
        self.output_dir.mkdir(exist_ok=True)
        
        # Directory for additional device data
        self.device_data_dir = self.data_dir / "devices"
        self.device_data_dir.mkdir(exist_ok=True)
        
        # Directory for indexes and metadata
        self.index_dir = self.data_dir / "indexes"
        self.index_dir.mkdir(exist_ok=True)
        
        # Directory for command output metadata
        self.command_metadata_dir = self.data_dir / "command_metadata"
        self.command_metadata_dir.mkdir(exist_ok=True)
        
        # Directory for plugin-specific configuration (kept in plugin data dir)
        self.config_dir = self.plugin_data_dir / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # Will initialize database when main window is ready
        if self.api.main_window is not None:
            self.initialize_db()
        else:
            self.api.on_main_window_ready(self.initialize_db)
    
    def initialize_db(self):
        """Initialize database manager."""
        try:
            self.db_manager = self.api.main_window.database_manager
            # No need to create tables or columns with object-based API
        except Exception as e:
            self.api.log(f"Error initializing database: {str(e)}", level="ERROR")
    
    def get_device(self, ip):
        """Get a device by IP address."""
        try:
            # Use the object API
            if hasattr(self.db_manager, 'get_device_object'):
                device_obj = self.db_manager.get_device_object(ip)
                if device_obj:
                    return device_obj.to_dict()
            return None
        except Exception as e:
            self.api.log(f"Error getting device: {str(e)}", level="ERROR")
            return None
    
    def update_device_type(self, ip, device_type):
        """Update a device's type."""
        try:
            # Use the object API
            if hasattr(self.db_manager, 'get_device_object'):
                device_obj = self.db_manager.get_device_object(ip)
                if device_obj:
                    device_obj.set_metadata('device_type', device_type)
                    return self.db_manager.add_device_object(device_obj)
            return False
        except Exception as e:
            self.api.log(f"Error updating device type: {str(e)}", level="ERROR")
            return False

    def get_devices_by_type(self, device_type):
        """Get devices by type using the object API."""
        try:
            if hasattr(self.db_manager, 'get_device_objects'):
                all_devices = self.db_manager.get_device_objects()
                matching_devices = []
                for device in all_devices:
                    if device.get_metadata('device_type') == device_type:
                        matching_devices.append(device.to_dict())
                return matching_devices
            return []
        except Exception as e:
            self.api.log(f"Error getting devices by type: {str(e)}", level="ERROR")
            return []

    def get_device_types(self):
        """Get all device types using the object API."""
        try:
            if hasattr(self.db_manager, 'get_device_objects'):
                all_devices = self.db_manager.get_device_objects()
                device_types = set()
                for device in all_devices:
                    device_type = device.get_metadata('device_type')
                    if device_type:
                        device_types.add(device_type)
                return list(device_types)
            return []
        except Exception as e:
            self.api.log(f"Error getting device types: {str(e)}", level="ERROR")
            return []
    
    def add_command_output(self, device_ip, command, output_path, output_type="text", comment=None):
        """Add a command output record to local storage and metadata."""
        # Validate input parameters
        if not device_ip or not command or not output_path:
            self.api.log("Missing required parameters for add_command_output", level="ERROR")
            return False
            
        # Always save to a local file as the primary storage method
        local_save_success = False
        try:
            # Create device-specific output directory
            device_output_dir = self.output_dir / device_ip.replace('.', '_')
            device_output_dir.mkdir(exist_ok=True)
            
            # Use the output directory's root to store the index
            index_file = self.output_dir / "command_output_index.csv"
            
            # Create or append to index file
            mode = 'a' if index_file.exists() else 'w'
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(index_file, mode, newline='') as f:
                writer = csv.writer(f)
                if mode == 'w':
                    writer.writerow(['device_ip', 'command', 'output_path', 'output_type', 'timestamp', 'comment'])
                writer.writerow([device_ip, command, output_path, output_type, timestamp, comment])
            
            # Additionally, store metadata in JSON format for better structure
            output_id = Path(output_path).stem  # Use filename as ID
            
            # Store metadata in device-specific folder
            device_metadata_dir = self.command_metadata_dir / device_ip.replace('.', '_')
            device_metadata_dir.mkdir(exist_ok=True)
            
            metadata_file = device_metadata_dir / f"{output_id}.json"
            
            metadata = {
                'id': output_id,
                'device_ip': device_ip,
                'command': command,
                'output_path': output_path,
                'output_type': output_type,
                'timestamp': timestamp,
                'comment': comment
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.api.log(f"Command output record saved to local index: {device_ip} - {command}", level="DEBUG")
            local_save_success = True
        except Exception as e:
            self.api.log(f"Error saving command output to local index: {str(e)}", level="ERROR")
        
        # No longer trying to save to database directly with SQL
        # Instead, we could use an object-based approach if available in the future
        
        return local_save_success
    
    def get_command_outputs(self, device_ip=None):
        """Get command outputs for a device from local storage."""
        outputs = []
        
        try:
            if device_ip:
                # Get metadata files for specific device
                device_metadata_dir = self.command_metadata_dir / device_ip.replace('.', '_')
                if device_metadata_dir.exists():
                    metadata_files = list(device_metadata_dir.glob("*.json"))
                else:
                    metadata_files = []
            else:
                # Get all metadata files from all device directories
                metadata_files = []
                for device_dir in self.command_metadata_dir.glob("*"):
                    if device_dir.is_dir():
                        metadata_files.extend(list(device_dir.glob("*.json")))
            
            for file_path in metadata_files:
                try:
                    with open(file_path, 'r') as f:
                        metadata = json.load(f)
                    
                    # Filter by device_ip if specified
                    if device_ip and metadata.get('device_ip') != device_ip:
                        continue
                        
                    outputs.append(metadata)
                except Exception as e:
                    self.api.log(f"Error reading metadata file {file_path}: {str(e)}", level="ERROR")
            
            # If no metadata files or as a fallback, try reading from CSV index
            if not outputs:
                index_file = self.output_dir / "command_output_index.csv"
                if index_file.exists():
                    with open(index_file, 'r', newline='') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Filter by device_ip if specified
                            if device_ip and row['device_ip'] != device_ip:
                                continue
                            # Convert row to match expected format
                            outputs.append({
                                'id': f"local_{len(outputs)}",
                                'device_ip': row['device_ip'],
                                'command': row['command'],
                                'output_path': row['output_path'],
                                'timestamp': row.get('timestamp', ''),
                                'output_type': row.get('output_type', 'text'),
                                'comment': row.get('comment', '')
                            })
            
            self.api.log(f"Retrieved {len(outputs)} command outputs from local index", level="DEBUG")
        except Exception as e:
            self.api.log(f"Error getting command outputs from local index: {str(e)}", level="ERROR")
        
        # Sort all outputs by timestamp descending (newest first)
        outputs = sorted(outputs, key=lambda x: x.get('timestamp', ''), reverse=True)
        return outputs
    
    def remove_command_output(self, output_id):
        """Remove a command output record."""
        try:
            # Search in all device directories for the metadata file
            for device_dir in self.command_metadata_dir.glob("*"):
                if not device_dir.is_dir():
                    continue
                    
                metadata_file = device_dir / f"{output_id}.json"
                if metadata_file.exists():
                    # Read the file to get the output path before deleting
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    output_path = metadata.get('output_path')
                    
                    # Delete the metadata file
                    metadata_file.unlink()
                    
                    return True, output_path
            
            # Fallback to searching in the CSV index
            index_file = self.output_dir / "command_output_index.csv"
            if index_file.exists():
                # Read all rows
                with open(index_file, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                
                # Find the matching row
                for i, row in enumerate(rows):
                    if row.get('id') == output_id or f"local_{i}" == output_id:
                        output_path = row.get('output_path')
                        
                        # Remove the row by writing all other rows back
                        with open(index_file, 'w', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
                            writer.writeheader()
                            writer.writerows([r for j, r in enumerate(rows) if j != i])
                        
                        return True, output_path
            
            return False, None
        except Exception as e:
            self.api.log(f"Error removing command output: {str(e)}", level="ERROR")
            return False, None
    
    def get_devices_by_subnet(self, subnet):
        """Get all devices in a subnet using the object API."""
        try:
            if hasattr(self.db_manager, 'get_device_objects'):
                all_devices = self.db_manager.get_device_objects()
                matching_devices = []
                
                # This is a simplified implementation and would need to be 
                # enhanced with proper subnet calculations
                subnet_prefix = subnet.split('/')[0].rsplit('.', 1)[0]
                
                for device in all_devices:
                    device_ip = device.get_ip()
                    if device_ip and device_ip.startswith(subnet_prefix):
                        matching_devices.append(device.to_dict())
                        
                return matching_devices
            return []
        except Exception as e:
            self.api.log(f"Error getting devices by subnet: {str(e)}", level="ERROR")
            return []
    
    def update_device(self, device):
        """Update a device's properties using the object API."""
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
                
            # Use the object API
            if hasattr(self.db_manager, 'get_device_object'):
                device_obj = self.db_manager.get_device_object(device.get('ip'))
                
                if not device_obj:
                    # Create a new device object
                    device_obj = Device(device.get('ip'))
                
                # Update device properties
                if 'hostname' in device and device['hostname']:
                    device_obj.set_hostname(device['hostname'])
                
                if 'mac' in device and device['mac']:
                    device_obj.set_mac(device['mac'])
                
                if 'vendor' in device and device['vendor']:
                    device_obj.set_metadata('vendor', device['vendor'])
                
                # Update device type if provided
                if 'device_type' in device:
                    device_obj.set_metadata('device_type', device['device_type'])
                
                # Update metadata if present
                if 'metadata' in device and isinstance(device['metadata'], dict):
                    for key, value in device['metadata'].items():
                        device_obj.set_metadata(key, value)
                
                # Save the updated device
                result = self.db_manager.add_device_object(device_obj)
                
                self.api.log(f"Device {device['ip']} updated successfully", level="DEBUG")
                return result
            
            return False
        except Exception as e:
            self.api.log(f"Error updating device: {str(e)}", level="ERROR")
            return False 