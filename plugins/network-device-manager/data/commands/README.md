# Network Device Manager Command Lists

This directory contains command lists for different device types. Each command list is stored as a JSON file and can be loaded by the Network Device Manager plugin.

## Command List Structure

Each command list file should have the following structure:

```json
{
    "id": "device_type_id",
    "name": "Display Name",
    "description": "Description of the device type",
    "commands": {
        "command_id": {
            "command": "actual_command_to_execute",
            "description": "Description of what the command does",
            "output_type": "text" 
        },
        ...
    }
}
```

- `id`: Unique identifier for the device type (used for file naming and internal references)
- `name`: User-friendly display name shown in the UI
- `description`: Detailed description of the device type
- `commands`: Dictionary of command definitions
  - `command_id`: Unique identifier for the command
  - `command`: The actual command string to execute on the device
  - `description`: Description of what the command does
  - `output_type`: How to display the output, can be `text` or `tabular`

## Importing Command Lists

You can import command lists in two ways:

1. **Via the UI**: 
   - Open the Network Device Manager plugin
   - Click "Manage Commands" 
   - Use the "Import" button to select a JSON file

2. **Direct file placement**:
   - Place your JSON command list file in this directory
   - Restart the application or reload plugins

## Executing Commands Without Connecting First

The latest version supports executing commands without manually connecting first. When you:

1. Select a device in the device list
2. Open the command dialog 
3. Choose a command to execute

The plugin will now automatically:
1. Establish a connection (SSH or Telnet) using saved credentials if available
2. Execute the command
3. Display the results

This feature makes it faster to run common diagnostic commands on devices without requiring manual connection steps.

## Available Command Lists

The following command lists are included by default:

- `cisco_ios.json`: Basic commands for Cisco IOS devices
- `cisco_3650.json`: Enhanced command set for Cisco Catalyst 3650 switches
- `junos.json`: Commands for Juniper JunOS devices

## Creating Your Own Command Lists

1. Create a new JSON file following the structure above
2. Name it according to the device type (e.g., `arista_eos.json`)
3. Add your commands with proper descriptions
4. Place the file in this directory or import it via the UI

## Tips

- For tabular command outputs, use the proper output_type setting for better display formatting
- Group related commands with similar command_id prefixes for better organization
- Include both common (basic) and advanced command sets for each device type 