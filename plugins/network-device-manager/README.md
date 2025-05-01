# Network Device Manager Plugin

This plugin allows you to manage and interact with network devices directly from within netWORKS.

## Features

- Connect to network devices via SSH and Telnet
- Execute commands and view output
- Store and manage command outputs
- Create and manage device credentials
- Group devices by type
- Execute common commands with a single click

## Installation

This plugin is included with netWORKS by default. No additional installation is required.

## Usage

1. Select a device in the main device table
2. The Network Device Manager panel will show available commands for this device
3. Click "Run Command" to execute a command on the device
4. View the output and save it if desired

## Command Sets

The plugin includes predefined command sets for common device types:

- Cisco IOS
- Juniper JunOS

You can customize these command sets or add new ones using the Command Set Manager.

## Data Storage

All device-related data is stored in the root `/data/` directory of the netWORKS application instead of plugin-specific folders. This ensures that:

1. All device data is exported together with the workspace
2. Data is properly associated with the devices they belong to
3. Data is preserved across application updates
4. Data from this plugin can be accessed by other plugins

The data directory structure is:

- `/data/commands/` - Contains command set definitions (JSON format)
- `/data/outputs/` - Stores command outputs organized by device IP
- `/data/logs/` - Stores session logs from device connections
- `/data/devices/` - Contains device-specific metadata
- `/data/indexes/` - Contains index files for cross-referencing data
- `/data/command_metadata/` - Stores structured metadata for command outputs

Plugin-specific configuration (like credentials) is still stored in:
- `plugins/network-device-manager/data/config/` - Contains plugin configuration including credentials

This structure ensures all device data is:
- Properly organized by device
- Included in workspace exports
- Accessible to other plugins
- Maintained during backup/restore operations

## Object-Based Database Integration

This plugin uses the netWORKS object-based database API instead of direct SQL queries, providing:

1. Better integration with the core application
2. Improved data consistency and reliability
3. Compatibility with future netWORKS versions
4. Local data storage backup for resilience

All device operations now use the object API methods:
- `get_device_object()` - For retrieving device data
- `add_device_object()` - For storing device data
- `get_device_objects()` - For querying multiple devices

Command outputs are stored both in structured JSON metadata and as text files, ensuring data integrity even if database access is temporarily unavailable.

## Database Resilience

The plugin now includes enhanced database resilience features to prevent data loss:

- Command outputs are always saved to files in the `/data/outputs/` directory
- Structured metadata is stored in the `/data/command_metadata/` directory
- A local CSV index is maintained as a failsafe backup
- The plugin operates fully on local data without SQL dependencies

This ensures that your command outputs are never lost, even if database issues occur.

## Troubleshooting

If you encounter issues with the plugin, check the following:

1. Ensure the device is reachable via SSH or Telnet
2. Verify that the credentials are correct
3. Check the netWORKS log for error messages
4. Try restarting the application if commands are not displaying properly

If command outputs are not displaying, check the `/data/outputs/` and `/data/command_metadata/` directories. The command outputs should be stored there even if database issues occur.

## License

This plugin is licensed under the same license as netWORKS. 