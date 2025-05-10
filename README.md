# NetWORKS

An extensible device management application.

## Features

- Device management with customizable properties
- Workspace support for managing different device configurations
- Plugin system for extending functionality
- Context menu support for device interactions
- Multi-device selection and bulk operations
- Device grouping with automatic name conflict resolution
- Bulk import of devices from files or pasted text
- Manifest and changelog tracking for the application and plugins
- Windows launcher for easy setup and execution

## Installation

### Windows

1. Clone the repository or download the source code
2. Run `Start_NetWORKS.bat` to automatically set up the environment and launch the application

### Manual Setup

1. Clone the repository or download the source code
2. Create a Python virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the application: `python networks.py`

## Workspaces

NetWORKS supports multiple workspaces for managing different device configurations. Each workspace maintains its own set of devices, groups, and enabled plugins.

### Creating a New Workspace

1. Go to **File → Workspaces → New Workspace**
2. Enter a name and optional description for the workspace
3. Choose whether to switch to the new workspace immediately

### Switching Workspaces

1. Go to **File → Workspaces → Open Workspace**
2. Select a workspace from the list

### Managing Workspaces

1. Go to **File → Workspaces → Manage Workspaces**
2. From here you can:
   - Switch to a different workspace
   - Delete workspaces (except the default workspace)

## Device Storage

Devices are stored in individual directories under the `config/devices` directory. Each device has its own directory named with its UUID, containing:

- `device.json` - Device properties and metadata
- Associated files - Configuration files, logs, or other files associated with the device

## Plugins

NetWORKS can be extended with plugins. Plugins are stored in the `plugins` directory.

### Plugin Manifest

Each plugin must include a `manifest.json` file that provides information about the plugin. See the [Plugin Manifest](docs/plugins/manifest.md) documentation for details.

### Sample Plugin

A sample plugin is included in the `plugins/sample` directory to demonstrate the plugin architecture.

## Development

### Project Structure

```
NetWORKS/
├── config/              # Configuration files
│   ├── devices/         # Device storage
│   └── workspaces/      # Workspace configurations
├── docs/                # Documentation
│   ├── api/             # API documentation
│   └── plugins/         # Plugin development guides
├── logs/                # Application logs
├── plugins/             # Plugin directory
│   └── sample/          # Sample plugin
├── src/                 # Source code
│   ├── core/            # Core functionality
│   ├── plugins/         # Internal plugins
│   └── ui/              # User interface
├── manifest.json        # Application manifest
├── networks.py          # Main entry point
├── README.md            # This file
├── requirements.txt     # Python dependencies
├── setup.bat            # Setup script for Windows
└── Start_NetWORKS.bat   # Launcher for Windows
```

### Adding a New Device Type

To add a new device type, you can either:

1. Extend the base `Device` class in a plugin
2. Register a custom device factory with the `DeviceManager`

### Creating a Plugin

See the [Plugin Development Guide](docs/plugins/README.md) for details on creating plugins.

## Documentation

NetWORKS includes comprehensive documentation to help you get started:

- [Getting Started Guide](docs/GETTING_STARTED.md): First steps with NetWORKS
- [Device Management Guide](docs/DEVICE_MANAGEMENT.md): Guide to managing devices and groups
- [Multi-Device Operations](docs/MULTI_DEVICE_OPERATIONS.md): Guide to working with multiple devices
- [Development Guide](docs/DEVELOPMENT.md): Information for developers
- [API Documentation](docs/API.md): Overview of the API
- [Signals Documentation](docs/api/signals.md): Working with signals and events
- [Plugin Development Guide](docs/plugins/README.md): How to extend NetWORKS with plugins

### Detailed Documentation

For more detailed documentation, see the [docs](docs) directory, which includes:

- [Plugin Development Guide](docs/plugins/README.md)
- [API Documentation Guidelines](docs/api/README.md)
- [Core API Reference](docs/api/core.md)
- [UI API Reference](docs/api/ui.md)
- [Context Menu API](docs/api/context_menu.md): How to use and extend the context menu
- [Signals Documentation](docs/api/signals.md): Working with signals and events
- [Multi-Device Operations](docs/api/context_menu.md#multi-device-selection-support): Support for working with multiple devices

## Architecture

NetWORKS is built with a modular architecture:

- **Core**: Provides base functionality for device and plugin management
- **UI**: Handles the user interface components
- **Plugins**: Extend the application with additional features

### Core Components

- **Device Manager**: Manages devices, their properties, and grouping
- **Plugin Manager**: Handles plugin discovery, loading, and lifecycle
- **Configuration Manager**: Manages application and plugin configuration

### Plugin System

Plugins can extend the application in the following ways:

- Add toolbar actions and menu items
- Register device types and properties
- Add columns to the device table
- Add panels to the device details view
- Add dock widgets to the main window
- Define custom device operations
- Connect to and emit signals for event-driven functionality

## License

This project is licensed under the MIT License. 