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

## Database Resilience

The plugin now includes enhanced database resilience features to prevent data loss when database issues occur:

- Command outputs are always saved to files in the `data/outputs/` directory
- If the database is unavailable, the plugin maintains a local index of command outputs
- The plugin will automatically recover and display command outputs even if the database is temporarily unavailable
- When the database becomes available again, the plugin will continue to use it without any user intervention

This ensures that your command outputs are never lost, even if database corruption occurs.

## Troubleshooting

If you encounter issues with the plugin, check the following:

1. Ensure the device is reachable via SSH or Telnet
2. Verify that the credentials are correct
3. Check the netWORKS log for error messages
4. Try restarting the application if commands are not displaying properly

If command outputs are not displaying, check the `data/outputs/` directory in the plugin folder. The command outputs should be stored there even if database issues occur.

## License

This plugin is licensed under the same license as netWORKS. 