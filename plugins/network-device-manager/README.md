# Network Device Manager Plugin

A netWORKS plugin for connecting to and managing network devices via SSH and telnet. This plugin allows network administrators to run commands, collect information, and store outputs from various types of network devices.

## Features

- Connect to network devices using SSH or telnet
- Run commands and collect output from devices
- Store command outputs in text or CSV format
- Secure credential management with encryption
- Support for multiple device types
- Extensible command sets via JSON files
- Credential management by device, subnet, or group
- Command output viewer and export options

## Installation

1. Copy the `network-device-manager` directory to the `plugins` directory of your netWORKS installation
2. Install required dependencies:
   ```
   pip install -r plugins/network-device-manager/requirements.txt
   ```
3. Restart netWORKS

## Getting Started

1. Select a device in the device table
2. In the right panel, set the device type (e.g., Cisco IOS, Juniper)
3. Click "Connect (SSH)" or "Connect (Telnet)" to establish a connection
4. Use the bottom panel to run commands on the connected device
5. View and download command outputs

## Credential Management

Credentials are stored securely in an encrypted format. You can set credentials for:

- Individual devices
- Subnets (e.g., 192.168.1.0/24)
- Device groups
- Default fallback credentials

To manage credentials:
1. Go to Tools > Network Device Manager > Manage Credentials
2. Use the Credentials tab to add, edit, or remove credential entries

## Command Sets

Commands are organized into sets based on device type. Each command has:
- A unique ID
- The actual command string to execute
- A description
- Output type (text or tabular)

The plugin comes with built-in command sets for:
- Cisco IOS
- Juniper JunOS

You can import additional command sets or create your own:
1. Go to the Commands tab in the bottom panel
2. Click "Import Commands" to import a JSON command set
3. Future versions will include a command set editor

## Custom Command Sets

You can create custom command sets in JSON format:

```json
{
    "name": "Custom Device Type",
    "description": "Commands for My Custom Device",
    "commands": {
        "show_version": {
            "command": "show version",
            "description": "Display version information",
            "output_type": "text"
        },
        "show_interfaces": {
            "command": "show interfaces",
            "description": "Display interfaces",
            "output_type": "tabular"
        }
    }
}
```

## UI Integration

The plugin integrates with the netWORKS UI in several ways:

- Right panel: Device information and connection controls
- Bottom panel: Command execution and output viewing
- Context menu: Right-click options on devices in the device table
- Tools menu: Network Device Manager submenu with plugin options

## License

This plugin is distributed under the same license as netWORKS.

## Author

chibashr 