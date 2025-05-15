#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command Set utility class for Command Manager plugin
"""

class Command:
    """Represents a single command"""
    
    def __init__(self, command, alias, description):
        """Initialize a command"""
        self.command = command
        self.alias = alias
        self.description = description
        
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "command": self.command,
            "alias": self.alias,
            "description": self.description
        }
        
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            data.get("command", ""),
            data.get("alias", ""),
            data.get("description", "")
        )


class CommandSet:
    """Represents a set of commands for a device type and firmware version"""
    
    def __init__(self, device_type, firmware_version, commands=None):
        """Initialize a command set"""
        self.device_type = device_type
        self.firmware_version = firmware_version
        self.commands = commands or []
        
    def add_command(self, command):
        """Add a command to the set"""
        self.commands.append(command)
        
    def remove_command(self, index):
        """Remove a command from the set"""
        if 0 <= index < len(self.commands):
            del self.commands[index]
            
    def get_command(self, index):
        """Get a command by index"""
        if 0 <= index < len(self.commands):
            return self.commands[index]
        return None
        
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "device_type": self.device_type,
            "firmware_version": self.firmware_version,
            "commands": [cmd.to_dict() for cmd in self.commands]
        }
        
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        # Create command set
        command_set = cls(
            data.get("device_type", ""),
            data.get("firmware_version", "")
        )
        
        # Add commands
        commands_data = data.get("commands", [])
        for cmd_data in commands_data:
            command = Command.from_dict(cmd_data)
            command_set.add_command(command)
            
        return command_set 