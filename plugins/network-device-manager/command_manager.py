#!/usr/bin/env python3
# Network Device Manager - Command Manager

import os
import json
import glob
from pathlib import Path

class CommandManager:
    """
    Manages device command definitions.
    Loads command sets from JSON files and provides access to them.
    """
    
    def __init__(self, commands_dir):
        self.commands_dir = Path(commands_dir)
        self.commands_by_type = {}
        
        # Load all command sets
        self._load_command_sets()
    
    def _load_command_sets(self):
        """Load all command sets from the commands directory."""
        if not self.commands_dir.exists():
            return
            
        # Find all JSON files in the commands directory
        for cmd_file in self.commands_dir.glob('*.json'):
            try:
                with open(cmd_file, 'r') as f:
                    command_set = json.load(f)
                
                # Extract device type from filename
                device_type = cmd_file.stem
                
                # Store command set
                self.commands_by_type[device_type] = command_set
            except Exception as e:
                print(f"Error loading command set {cmd_file.name}: {str(e)}")
    
    def get_device_types(self):
        """Get list of available device types."""
        return list(self.commands_by_type.keys())
    
    def get_device_type_display_names(self):
        """Get list of available device types with display names."""
        return {
            device_type: command_set.get('name', device_type) 
            for device_type, command_set in self.commands_by_type.items()
        }
    
    def get_commands_for_device_type(self, device_type):
        """Get commands for a specific device type."""
        if device_type not in self.commands_by_type:
            return {}
            
        return self.commands_by_type[device_type].get('commands', {})
    
    def get_command_details(self, device_type, command_id):
        """Get details for a specific command."""
        commands = self.get_commands_for_device_type(device_type)
        return commands.get(command_id, None)
    
    def add_command_set(self, device_type, name, description, commands):
        """Add or update a command set."""
        command_set = {
            'name': name,
            'description': description,
            'commands': commands
        }
        
        # Update in-memory data
        self.commands_by_type[device_type] = command_set
        
        # Ensure the commands directory exists
        self.commands_dir.mkdir(exist_ok=True)
        
        # Save to file
        cmd_file = self.commands_dir / f"{device_type}.json"
        
        try:
            with open(cmd_file, 'w') as f:
                json.dump(command_set, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving command set {device_type}: {str(e)}")
            return False
    
    def add_command(self, device_type, command_id, command, description, output_type="text"):
        """Add or update a command in a command set."""
        if device_type not in self.commands_by_type:
            return False
            
        # Get command set
        command_set = self.commands_by_type[device_type]
        
        # Make sure commands dictionary exists
        if 'commands' not in command_set:
            command_set['commands'] = {}
            
        # Add command
        command_set['commands'][command_id] = {
            'command': command,
            'description': description,
            'output_type': output_type
        }
        
        # Save command set
        return self.add_command_set(
            device_type, 
            command_set.get('name', device_type),
            command_set.get('description', ''),
            command_set['commands']
        )
    
    def remove_command(self, device_type, command_id):
        """Remove a command from a command set."""
        if device_type not in self.commands_by_type:
            return False
            
        # Get command set
        command_set = self.commands_by_type[device_type]
        
        # Check if command exists
        if 'commands' not in command_set or command_id not in command_set['commands']:
            return False
            
        # Remove command
        del command_set['commands'][command_id]
        
        # Save command set
        return self.add_command_set(
            device_type, 
            command_set.get('name', device_type),
            command_set.get('description', ''),
            command_set['commands']
        )
    
    def remove_command_set(self, device_type):
        """Remove a command set."""
        if device_type not in self.commands_by_type:
            return False
            
        # Remove from memory
        del self.commands_by_type[device_type]
        
        # Remove file
        cmd_file = self.commands_dir / f"{device_type}.json"
        try:
            cmd_file.unlink()
            return True
        except Exception as e:
            print(f"Error removing command set {device_type}: {str(e)}")
            return False
    
    def import_command_set(self, json_file_path):
        """Import a command set from a JSON file."""
        try:
            with open(json_file_path, 'r') as f:
                command_set = json.load(f)
                
            # Validate command set structure
            if not isinstance(command_set, dict) or 'name' not in command_set or 'commands' not in command_set:
                return False, "Invalid command set format"
                
            # Extract device type from filename if not specified
            device_type = command_set.get('id', Path(json_file_path).stem)
            
            # Add command set
            self.add_command_set(
                device_type,
                command_set.get('name', device_type),
                command_set.get('description', ''),
                command_set.get('commands', {})
            )
            
            return True, f"Imported command set: {command_set.get('name', device_type)}"
        except Exception as e:
            return False, f"Error importing command set: {str(e)}"
    
    def export_command_set(self, device_type, export_path):
        """Export a command set to a JSON file."""
        if device_type not in self.commands_by_type:
            return False, f"Device type {device_type} not found"
            
        try:
            # Get command set
            command_set = self.commands_by_type[device_type]
            
            # Add device type ID if not present
            if 'id' not in command_set:
                command_set['id'] = device_type
                
            # Write to file
            with open(export_path, 'w') as f:
                json.dump(command_set, f, indent=4)
                
            return True, f"Exported command set to {export_path}"
        except Exception as e:
            return False, f"Error exporting command set: {str(e)}" 