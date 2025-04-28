# Base Network Scanner

A core plugin for netWORKS that provides basic network scanning functionality for device discovery.

## Features

- Multiple scan types: ping sweep, port scan, and deep scan
- Comprehensive device discovery
- Network interface detection
- Customizable scan templates
- User-friendly UI integration
- Database integration for persistent storage
- Workspace support for saving and loading scan results

## Scan Types

### Quick Scan (Ping Sweep)

Fast ping sweep of the network to identify live hosts. Uses ICMP echo requests (ping) to determine if devices are online. This is the most basic scan type and is useful for quickly mapping your network.

### Port Scan

Performs a quick ping sweep followed by port scanning on discovered devices. Checks common ports to identify services running on devices. This scan provides more detailed information about devices.

### Deep Scan

Comprehensive network scan that includes:
- Ping sweep to identify live hosts
- Port scanning to identify services
- OS fingerprinting attempts
- Hostname resolution
- Additional metadata collection

### Stealth Scan

Like a quick scan but with slower timing and lower impact on the network. Useful in sensitive environments where network load should be minimized.

## Usage

1. Select a network interface from the dropdown list
2. Enter an IP range to scan (e.g., "192.168.1.0/24", "10.0.0.1-10.0.0.254")
3. Choose a scan type
4. Click "Start Scan"

The scan results will be displayed in the device table and stored in the database for persistence.

## Database Integration

The Base Network Scanner plugin integrates with the netWORKS database system for persistent storage:

- All discovered devices are automatically stored in the database
- Scan history is recorded for future reference
- Device information is updated when devices are rediscovered
- All data is automatically available across application sessions

## Workspace Support

The plugin fully supports the netWORKS workspace system:

- When you save a workspace, all scan results and discovered devices are saved
- When you load a workspace, previously discovered devices and scan history are restored
- Create new workspaces to separate different scanning projects
- All data is properly persisted in the workspace database

## Requirements

This plugin requires the following Python packages:
- scapy (optional, used for advanced scanning if available)
- netifaces (optional, used for better interface detection if available)

## API

The plugin provides an API for other plugins to use. See the [API.md](API.md) file for details.

## License

This plugin is part of netWORKS and follows the same license terms. 