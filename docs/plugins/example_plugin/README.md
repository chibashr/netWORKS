# Example Plugin

## Overview
The Example Plugin provides basic network device diagnostics and information collection tools for netWORKS. It demonstrates plugin development best practices and serves as a template for creating custom plugins.

## Features
- Device ping functionality
- Device information retrieval
- Integration with the main application UI
- Event handling for network operations

## Installation
1. Copy the `example_plugin` directory to the `plugins` directory in your netWORKS installation
2. Enable the plugin in netWORKS through Tools -> Plugin Manager
3. Restart netWORKS for full functionality

## Usage
After installation, the plugin provides several ways to interact with it:

### Left Panel
The left panel contains:
- Device information display
- Ping button for selected device
- Get Info button for selected device

### Bottom Panel
The plugin adds a tab to the bottom panel showing:
- Logs of plugin activity
- Results of device operations

### Menu Integration
The plugin adds menu items to the Tools menu:
- Ping Selected Device
- Get Device Info

## Configuration
The Example Plugin doesn't require specific configuration. All functionality works out of the box.

## Dependencies
- PySide6 (provided by netWORKS core)
- No additional external dependencies are required

## Data Storage
This plugin doesn't store any persistent data.

## Network Interactions
The plugin performs the following network operations:
- ICMP ping to target devices
- TCP connection attempts for device information gathering

## License
This plugin is part of the netWORKS documentation and is licensed under the same terms as the main application.

## Contributing
See the netWORKS documentation for information on contributing to plugins and the core application.

## Version History
- v1.0.0: Initial release with basic device information and ping functionality 