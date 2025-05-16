# Command Manager Plugin API

The Command Manager plugin provides an interface for running commands on network devices and managing credentials.

## Plugin Interface

### Initialization

```python
def initialize(self, app, plugin_info)
```
Initializes the plugin with application context and plugin information.

### Start/Stop

```python
def start(self)
```
Starts the plugin and connects signals.

```python
def stop(self)
```
Stops the plugin and disconnects signals.

```python
def cleanup(self)
```
Saves data and cleans up resources before plugin unload.

## Command Sets API

### Command Set Operations

```python
def get_device_types(self)
```
Returns a list of available device types.

```python
def get_firmware_versions(self, device_type)
```
Returns a list of available firmware versions for a specific device type.

```python
def get_command_set(self, device_type, firmware)
```
Returns a `CommandSet` object for the specified device type and firmware.

```python
def add_command_set(self, command_set)
```
Adds or updates a command set in the plugin.

```python
def delete_command_set(self, device_type, firmware)
```
Deletes a command set.

## Credential Management

### Overview

The Command Manager plugin provides a secure way to store and manage device credentials. Credentials are stored using the following methods:

1. **Device Credentials**: Stored directly in device properties using the `credentials` property, which contains an encrypted credentials object
2. **Group Credentials**: Stored in JSON files in the plugin's data directory
3. **Subnet Credentials**: Stored in JSON files in the plugin's data directory

The plugin uses a fallback mechanism to find credentials:
1. First, it checks device-specific credentials
2. If not found, it checks credentials for any groups the device belongs to
3. Finally, it checks if the device's IP address falls within any subnets with credentials

### Credential Storage

Device credentials are stored directly in the device properties to ensure they are properly associated with the device and saved/loaded with the device configuration. The credentials are stored as an encrypted object in the `credentials` property of the device.

Group and subnet credentials are still stored in separate files within the plugin's data directory.

### Credential Methods

| Method | Description |
|--------|-------------|
| `get_device_credentials(device_id, device_ip=None, groups=None)` | Get credentials for a device with fallback to group/subnet |
| `set_device_credentials(device_id, credentials)` | Store credentials for a device in its properties |
| `delete_device_credentials(device_id)` | Remove credentials from a device |
| `set_group_credentials(group_name, credentials)` | Store credentials for a device group |
| `delete_group_credentials(group_name)` | Remove credentials for a device group |
| `set_subnet_credentials(subnet, credentials)` | Store credentials for a subnet |
| `delete_subnet_credentials(subnet)` | Remove credentials for a subnet |
| `get_all_device_credentials()` | Get all device credentials |
| `get_all_group_credentials()` | Get all group credentials |
| `get_all_subnet_credentials()` | Get all subnet credentials |

### Credentials Format

All credentials are stored in a standard dictionary format:

```json
{
  "connection_type": "ssh",
  "username": "admin",
  "password": "<encrypted>",
  "enable_password": "<encrypted>"
}
```

Passwords are encrypted before storage and decrypted when retrieved.

## Command Execution API

```python
def run_command(self, device, command_text, credentials=None)
```
Runs a command on a device. Returns a dictionary with:
- `success`: Boolean indicating if the command succeeded
- `output`: Command output text
- `error`: Error message if command failed

## Command Output Management API

```python
def add_command_output(self, device_id, command_id, output, command_text=None)
```
Adds a command output to the history for a device.

```python
def get_command_outputs(self, device_id, command_id=None)
```
Gets command outputs for a device, optionally filtered by command ID.

```python
def delete_command_output(self, device_id, command_id, timestamp=None)
```
Deletes command output(s) for a device.

## UI Components

The plugin provides the following UI components:

### CommandDialog
Dialog for running commands on devices.

### CredentialManager
Dialog for managing device credentials.

### CommandOutputPanel
Panel for viewing command outputs.

### CommandSetEditor
Dialog for editing command sets.

## Data Model Classes

### CommandSet
Represents a set of commands for a device type and firmware version.

### Command
Represents a single command within a command set.

## Integration

The plugin integrates with the NetWORKS application by:
1. Adding a toolbar action for opening the Command Manager
2. Adding context menu items to device entries
3. Adding a "Command Outputs" tab to device details

## Menu Integration

The Command Manager plugin provides a `find_existing_menu` method that helps plugins integrate with existing menus in the application. This approach prevents the creation of duplicate menus with similar names.

### Usage

```python
# Find the existing Tools menu (case-insensitive)
tools_menu = plugin.find_existing_menu("Tools")

# Create menu actions
return {
    tools_menu: [
        action1,
        action2
    ]
}
```

### Method Documentation

```python
def find_existing_menu(self, menu_name):
    """Find an existing menu by name (case-insensitive)
    
    This method helps plugins integrate with existing menus rather than creating
    duplicate menus. It performs a case-insensitive search for standard menus
    like File, Edit, View, Tools, etc.
    
    Args:
        menu_name (str): The name of the menu to find
        
    Returns:
        str: The exact name of the menu if found, otherwise the original name
    """
    # Implementation details...
```

### Benefits

- Prevents duplicate menus in the application
- Ensures consistent UI
- Allows plugins to integrate with standard application menus
- Case-insensitive matching to handle different capitalization

### Example

When registering plugin menus, use this pattern:

```python
def get_menu_actions(self):
    """Get actions to be added to the menu"""
    # Find the existing Tools menu
    tools_menu = self.find_existing_menu("Tools")
    
    return {
        tools_menu: [
            self.toolbar_action,
            self.credential_manager_action
        ]
    }
``` 