# Command Manager Plugin for NetWORKS

## Overview

The Command Manager plugin provides a powerful interface for running commands on network devices. It supports SSH and Telnet connections, command templates, credential management, and output storage.

## Features

- Run pre-defined or custom commands on network devices
- Store and manage command outputs for later reference
- Secure credential management for device access
- Command templates with variable substitution
- Export command outputs to files
- Command sets for different device types and firmware versions

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

1. Select one or more devices in the device table
2. Right-click and select "Run Commands" or use the toolbar button
3. Select commands from the available command sets
4. Click "Run" to execute the commands on the selected devices

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