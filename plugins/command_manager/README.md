# Command Manager Plugin for NetWORKS

## Overview

The Command Manager plugin provides a powerful interface for running commands on network devices. It supports SSH and Telnet connections, command templates, credential management, and output storage.

## Features

- Run commands on multiple devices in parallel
- Save command output for later analysis
- Organize commands into reusable sets
- Syntax highlighting for command output
- Credential management for device access
- Export command outputs to files
- Support for running commands on device groups and subnets
- Command search functionality to quickly find commands
- Custom command execution with safety checks

## Credential Management

The plugin provides a secure way to manage network device credentials:

- **Device-specific credentials**: Stored directly in device properties
- **Group-based credentials**: Credentials for groups of devices
- **Subnet-based credentials**: Credentials for IP subnets

> **Security Note**: All credentials are encrypted before storage. Device credentials are saved directly to the device properties to ensure they are properly associated with devices.

## Command Sets

Command sets are collections of pre-defined commands organized by device type and firmware version. The plugin includes default command sets for common network devices, but you can also create and customize your own.

Each command in a command set can include:
- Name and description
- Command text (with variable substitution)
- Expected output format
- Error detection patterns

## Usage

### Running Commands

1. Select one or more devices in the main application
2. Right-click and select "Run Commands"
3. Choose the command set appropriate for your devices
4. Select commands to run
5. Click "Run Selected" or "Run All"

### Searching Commands

You can quickly find commands in the command table:

1. Type any part of the command name, syntax, or description in the search box
2. The command table will filter in real-time, showing only matching commands
3. Clear the search box to show all commands again

### Running Custom Commands

You can also run custom commands without creating a command set:

1. Enter your command in the custom command field at the bottom of the dialog
2. Select the devices to run the command on
3. Click "Run Custom Command"

By default, a safety check is enabled that will warn you when attempting to run non-"show" commands that might modify device configuration.

### Device Groups and Subnets

You can now run commands on device groups and subnets:

1. Use the "Groups" or "Subnets" tab in the Command Dialog
2. Select the groups or subnets you want to target
3. Choose the command set and commands to run
4. Click "Run Selected" or "Run All"

The Command Manager now uses the DeviceManager's `get_device_groups_for_device()` method to determine which groups a device belongs to, providing more reliable detection of group membership. This enables more accurate credential fallback from device to group to subnet.

### Managing Credentials

1. Select a device in the device table
2. Right-click and select "Manage Credentials"
3. Enter credentials for the selected device

### Viewing Command Output

1. Select a device in the device table
2. Open the "Command Output" panel
3. View past command outputs for the selected device

## Integration

The Command Manager plugin integrates with the main NetWORKS application:

- Adds toolbar buttons for quick access
- Adds context menu items for devices
- Provides panels for device details
- Registers custom settings 