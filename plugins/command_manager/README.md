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

### Device Groups and Subnets

You can now run commands on device groups and subnets as well:

1. Use the "Groups" or "Subnets" tab in the Command Dialog
2. Select the groups or subnets you want to target
3. Choose the commands to run
4. Click "Run Selected" or "Run All"

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