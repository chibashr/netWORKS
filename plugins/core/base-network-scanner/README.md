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
- Advanced nmap integration for detailed scanning
- OS detection and service identification

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

### Manual Scan (Advanced)

Highly configurable scan with customizable parameters:

- Discovery methods (ICMP Echo, ARP, TCP SYN/ACK, UDP)
- Port scanning types (Connect, SYN, FIN, UDP)
- Pre-defined port groups (Top 10/100/1000, Common services, All ports)
- Custom port range specification with range syntax (e.g., 80,443,8080-8090)
- OS detection
- Service version detection
- Script scanning with different security levels
- Scan timing templates (from paranoid to aggressive)

## Usage

1. Select a network interface from the dropdown list
2. Choose range type (interface range or custom range)
3. Enter an IP range for custom range (e.g., "192.168.1.0/24", "10.0.0.1-10.0.0.254")
4. Choose a scan type or template
5. For manual scans, click "Configure" to set advanced options
6. Click "Start Scan"

The scan results will be displayed in the device table and stored in the database for persistence.

## Template Management

The plugin provides a template system for saving and reusing scan configurations:

- Create new templates with customized settings
- Manage existing templates
- Apply templates for quick scanning with preferred settings
- Templates are accessible from the "Scan Type" area

## Automatic Interface Range

The plugin now supports automatic range detection from selected interfaces:

- Choose "Interface Range" to automatically use the subnet of the selected interface
- The range updates automatically when switching interfaces
- Custom ranges are saved for future scans

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

## Advanced Scanning with Nmap

For advanced scanning features, the plugin can utilize Nmap if available on the system:

- Service version detection
- Operating system detection
- Script scanning (safe, discovery, or all scripts)
- Multiple port scanning types (SYN, FIN, UDP)
- Multiple discovery methods
- Comprehensive XML output parsing for detailed results

## Requirements

This plugin requires the following Python packages:
- scapy (optional, used for advanced scanning if available)
- netifaces (optional, used for better interface detection if available)
- nmap (optional, must be installed on the system for advanced scanning features)

## API

The plugin provides an API for other plugins to use. See the [API.md](API.md) file for details.

## License

This plugin is part of netWORKS and follows the same license terms. 