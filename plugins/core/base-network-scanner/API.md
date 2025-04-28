# Network Scanner Plugin API Documentation

This document outlines the public API exposed by the Network Scanner plugin for use by other plugins.

## API Version

- Version: 1.1.0
- Compatible with netWORKS plugin API: 1.0.0+

## Exported Functions

### `start_scan`

Start a network scan with the given parameters.

**Parameters:**
- `interface` (string): Name of the network interface to use
- `ip_range` (string): IP range to scan (e.g., "192.168.1.1-254", "10.0.0.0/24")
- `scan_type` (string, optional): Type of scan to perform (default: "quick_scan")
- `**kwargs` (optional): Additional scan parameters:
  - `timeout` (int): Connection timeout in seconds
  - `retries` (int): Number of retries for failed connections
  - `parallel` (int): Number of parallel scan threads
  - `ports` (list): List of ports to scan (only for scan types that support port scanning)

**Returns:**
- `string`: Scan ID that can be used to track the scan

**Example:**
```python
scan_id = plugin_api.call_plugin_function(
    "base-network-scanner", 
    "start_scan", 
    "eth0", 
    "192.168.1.1-254", 
    "deep_scan",
    timeout=2, 
    retries=2
)
```

### `get_scan_history`

Get the history of previous scans.

**Parameters:**
- None

**Returns:**
- `list`: List of dictionaries containing scan information:
  - `id` (string): Scan ID
  - `interface` (string): Network interface used
  - `ip_range` (string): IP range scanned
  - `scan_type` (string): Type of scan performed
  - `timestamp` (string): Start time of the scan
  - `end_time` (string): End time of the scan (null if scan is still running)
  - `status` (string): Scan status ("running", "completed", "stopped", "error")
  - `devices_found` (int): Number of devices found
  - `total_devices` (int): Total number of devices in the range
  - `duration` (float): Duration of the scan in seconds

**Example:**
```python
history = plugin_api.call_plugin_function("base-network-scanner", "get_scan_history")
for scan in history:
    print(f"Scan {scan['id']}: Found {scan['devices_found']} devices")
```

### `get_scan_devices`

Get devices discovered during a specific scan.

**Parameters:**
- `scan_id` (string): ID of the scan to retrieve devices from

**Returns:**
- `list`: List of dictionaries containing device information discovered during the scan:
  - `id` (string): Device ID
  - `ip` (string): IP address
  - `hostname` (string): Hostname (if resolved)
  - `mac` (string): MAC address (if available)
  - `status` (string): Device status (e.g., "active")
  - `first_seen` (string): Timestamp when the device was first seen
  - `last_seen` (string): Timestamp when the device was last seen
  - `scan_id` (string): ID of the scan that found the device
  - `ports` (list, optional): List of open ports (if port scanning was performed)
  - `metadata` (dict): Additional device metadata

**Example:**
```python
devices = plugin_api.call_plugin_function("base-network-scanner", "get_scan_devices", "scan_12345678")
for device in devices:
    print(f"Device {device['ip']} ({device['hostname']})")
```

### `get_scan_templates`

Get available scan templates.

**Parameters:**
- None

**Returns:**
- `dict`: Dictionary of scan templates, where keys are template IDs and values are dictionaries containing template configuration:
  - `name` (string): Template name
  - `description` (string): Template description
  - `timeout` (int): Connection timeout in seconds
  - `retries` (int): Number of retries for failed connections
  - `parallel` (int): Number of parallel scan threads
  - `ports` (list, optional): List of ports to scan

**Example:**
```python
templates = plugin_api.call_plugin_function("base-network-scanner", "get_scan_templates")
for template_id, template in templates.items():
    print(f"Template {template['name']}: {template['description']}")
```

## Hooks

### `before_scan`

Triggered before a network scan starts.

**Parameters:**
- `scan_config` (dict): Scan configuration

**Example:**
```python
@plugin_api.hook("base-network-scanner:before_scan")
def handle_before_scan(scan_config):
    print(f"Scan starting: {scan_config['id']} on {scan_config['range']}")
```

### `after_scan`

Triggered after a network scan completes.

**Parameters:**
- `scan_result` (dict): Scan result containing the same fields as the scan configuration plus additional result data

**Example:**
```python
@plugin_api.hook("base-network-scanner:after_scan")
def handle_after_scan(scan_result):
    print(f"Scan completed: {scan_result['id']} found {scan_result['devices_found']} devices")
```

### `device_found`

Triggered when a device is found during a scan.

**Parameters:**
- `device` (dict): Device information:
  - `ip` (string): IP address
  - `hostname` (string): Hostname (if resolved)
  - `mac` (string): MAC address (if available)
  - `status` (string): Device status (e.g., "active")
  - `scan_method` (string): Method used to discover the device
  - `last_seen` (string): Timestamp when the device was last seen
  - `scan_id` (string): ID of the scan that found the device
  - `ports` (list, optional): List of open ports (if port scanning was performed)

**Example:**
```python
@plugin_api.hook("base-network-scanner:device_found")
def handle_device_found(device):
    print(f"Device found: {device['ip']} with hostname {device['hostname']}")
```

## Database Integration

The base-network-scanner plugin integrates with the netWORKS database system for persistent storage of devices and scan results.

### Device Storage

All devices discovered during scans are automatically stored in the database with the following additional metadata:

- `discovery_source`: Set to "base-network-scanner" to indicate the plugin that discovered the device
- `scan_id`: The ID of the scan that discovered the device
- `scan_type`: The type of scan that discovered the device

### Scan History Storage

Scan history is stored in the database for persistence across sessions. Each scan record includes:

- Basic scan information (ID, timestamps, interface, IP range, etc.)
- Scan results (devices found, duration, status)
- Scan configuration (scan type, options)

### Automatic Database Operations

The plugin automatically:

1. Stores discovered devices in the database
2. Records scan history in the database
3. Updates device information when a device is rediscovered

## Workspace Integration

The base-network-scanner plugin integrates with the netWORKS workspace system. When a workspace is loaded or saved, the plugin automatically handles the appropriate database operations.

### Workspace Events

The plugin registers for the following workspace events:

- `workspace_loaded`: When a workspace is loaded, the plugin loads devices and scan history relevant to this plugin
- `workspace_saved`: When a workspace is saved, the plugin ensures all devices and scan history are saved to the database

### Data Persistence

The following data is persisted across workspace operations:

1. **Devices**: All devices discovered by the network scanner
2. **Scan History**: Records of all completed scans
3. **Scan Templates**: Custom scan templates (if any)

### Cross-Session Support

Thanks to database integration, scan results persist across application sessions:

- Devices discovered in previous scanning sessions can be viewed
- Scan history from previous sessions is available
- Comparisons can be made between scan results from different times

## Error Handling

All functions will raise appropriate exceptions on error, which should be caught by the calling plugin:

- `ValueError`: When invalid parameters are provided
- `RuntimeError`: When there's an error during the scan operation
- `KeyError`: When a requested scan or template does not exist

## Notes

- Scan operations are performed asynchronously in a background thread
- Progress can be tracked by listening to the hook events
- Device information is automatically added to the netWORKS device database 