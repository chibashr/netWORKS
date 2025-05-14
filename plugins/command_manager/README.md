# Command Manager Plugin

A tool to run commands and store the retrieved information per network device, for quickly getting information on one, or a group, of devices.

## Features

- Run commands on network devices via SSH or Telnet
- Securely store credentials per device or group
- Create and edit command sets for different device types and firmware versions
- Import and export command sets via JSON
- View command output history per device
- Run multiple commands on a group of devices
- Generate and download reports from command outputs

## Usage

### Command Manager Dialog

1. Click on the "Command Manager" button in the toolbar to open the main dialog
2. Select devices and commands to run
3. View and manage command outputs

### Quick Run Commands

1. Right-click on a device in the device table
2. Select "Run Commands" from the context menu
3. Choose a command set to run on the selected devices

### Command Sets

Command sets are organized by device type and firmware version. Each command has:
- Command: The actual command to run (e.g., "sh ver")
- Alias: A friendly name for the command (e.g., "Show Version")
- Description: A detailed description of what the command does

### Credentials Management

The plugin provides secure storage for device credentials:
- Credentials can be set per device or inherited from groups
- Credentials are encrypted before being stored
- Mass modification of credentials for multiple devices

## Command Set Format (JSON)

Command sets can be imported and exported in JSON format:

```json
{
  "device_type": "cisco_ios",
  "firmware_version": "15.x",
  "commands": [
    {
      "command": "sh ver",
      "alias": "Show Version",
      "description": "Shows version of device"
    },
    {
      "command": "sh run",
      "alias": "Show Running Config",
      "description": "Shows running configuration"
    }
  ]
}
``` 