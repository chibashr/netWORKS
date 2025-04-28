# Network Device Manager API

This document describes the API exported by the Network Device Manager plugin, which can be used by other plugins.

## Overview

The Network Device Manager plugin provides functionality for connecting to network devices, running commands, and managing command outputs. Other plugins can leverage this functionality through the exported API.

## Accessing the API

To access the Network Device Manager API from another plugin, use the plugin API's `get_plugin_api` method:

```python
# In your plugin
def __init__(self, plugin_api):
    self.api = plugin_api
    
    # Get Network Device Manager API
    self.ndm_api = self.api.get_plugin_api("network-device-manager")
    
    # Now you can call methods on self.ndm_api
    # For example:
    success, message, connection_id = self.ndm_api.connect_to_device(device_info, "ssh")
```

## API Methods

### Device Connections

#### `connect_to_device(device_info, connection_type="ssh", credentials=None)`

Connect to a network device using SSH or telnet.

**Parameters:**
- `device_info`: Dictionary containing device information (must include 'ip' key)
- `connection_type`: Connection protocol - either "ssh" or "telnet"
- `credentials`: Optional dictionary with 'username', 'password', and 'enable_password'

**Returns:**
- Tuple: (success, message, connection_id)

**Example:**
```python
device_info = {'ip': '192.168.1.1', 'device_type': 'cisco_ios'}
success, message, conn_id = ndm_api.connect_to_device(device_info, "ssh")
```

#### `run_command(device_info, command, output_format="text")`

Run a command on a connected device.

**Parameters:**
- `device_info`: Dictionary containing device information (must include 'ip' key)
- `command`: Command string to execute
- `output_format`: Format for the output - "text" or "csv"

**Returns:**
- Tuple: (success, output)

**Example:**
```python
success, output = ndm_api.run_command(device_info, "show version")
```

### Command Management

#### `get_device_commands(device_type)`

Get available commands for a device type.

**Parameters:**
- `device_type`: Device type string (e.g., "cisco_ios")

**Returns:**
- Dictionary of commands for the specified device type

**Example:**
```python
commands = ndm_api.get_device_commands("cisco_ios")
```

#### `save_device_output(device_info, command_output, filename=None, format="text")`

Save command output to a file.

**Parameters:**
- `device_info`: Dictionary containing device information
- `command_output`: Output string from a command
- `filename`: Optional filename (if None, will generate a name)
- `format`: Output format - "text" or "csv"

**Returns:**
- Path to saved file

**Example:**
```python
output_path = ndm_api.save_device_output(device_info, output, format="csv")
```

### Events

The Network Device Manager plugin emits events that other plugins can listen for:

#### `network-device-manager:connection_established`

Triggered when connection to a device is established.

**Event Data:**
- `device_ip`: IP address of the device
- `connection_type`: Connection type (ssh/telnet)
- `connection_id`: Unique connection identifier

**Example:**
```python
@self.api.hook("network-device-manager:connection_established")
def on_connection_established(event_data):
    device_ip = event_data.get('device_ip')
    connection_id = event_data.get('connection_id')
    self.api.log(f"Connection established to {device_ip}")
```

#### `network-device-manager:command_executed`

Triggered when a command is executed on a device.

**Event Data:**
- `device_ip`: IP address of the device
- `command`: Command that was executed
- `success`: Boolean indicating success or failure

**Example:**
```python
@self.api.hook("network-device-manager:command_executed")
def on_command_executed(event_data):
    device_ip = event_data.get('device_ip')
    command = event_data.get('command')
    success = event_data.get('success')
    self.api.log(f"Command executed on {device_ip}: {command} (Success: {success})")
```

#### `network-device-manager:output_saved`

Triggered when command output is saved to a file.

**Event Data:**
- `device_ip`: IP address of the device
- `command`: Command that was executed
- `output_path`: Path to the saved output file

**Example:**
```python
@self.api.hook("network-device-manager:output_saved")
def on_output_saved(event_data):
    device_ip = event_data.get('device_ip')
    output_path = event_data.get('output_path')
    self.api.log(f"Output saved for {device_ip}: {output_path}")
```

## Error Handling

All API methods return a success indicator (boolean) as the first element of the return tuple, followed by additional data or an error message.

## Future API Extensions

Additional API methods will be added in future versions to support:

- Credential management
- Command set management
- Batch command execution
- Configuration management 