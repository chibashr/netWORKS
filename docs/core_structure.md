# netWORKS Core Structure

This document provides an overview of the netWORKS application structure, including the core, config, and data folders. Understanding this structure is essential for plugin developers and contributors.

## Directory Structure

The application has the following main directories:

```
netWORKS/
├── core/           # Core application functionality
├── config/         # Configuration files
├── data/           # Database and application data
├── docs/           # Documentation
├── logs/           # Application logs
├── plugins/        # Plugin directory
└── venv/           # Virtual environment (dev only)
```

## Core Directory

The `core/` directory contains the core application functionality and is organized as follows:

```
core/
├── database/        # Database interaction components
│   └── device_manager.py  # Device database management
├── plugins/         # Plugin management system
├── ui/              # User interface components
│   ├── dialogs/     # Dialog windows
│   ├── menu/        # Menu components
│   ├── panels/      # Panel UI components
│   ├── table/       # Table UI components
│   ├── toolbar/     # Toolbar components
│   ├── main_window.py  # Main application window
│   └── splash_screen.py  # Application splash screen
├── version.py       # Version management utilities
└── workspace/       # Workspace management (deprecated)
```

### Core Components

#### Database Module

The `database` module provides database interaction classes, primarily:

- **DeviceDatabaseManager**: Manages device-related database operations
  - Handles device storage, retrieval, and updates
  - Provides plugin data storage
  - Manages device history tracking

#### UI Module

The `ui` module contains all user interface components:

- **MainWindow**: The primary application window
  - Panel management
  - Menu and toolbar configuration
  - Device table integration
  - Plugin UI integration point

- **Panels**: UI panel components
  - LeftPanel: Navigation and filtering
  - RightPanel: Detail and property display
  - BottomPanel: Logs and status information

- **DeviceTable**: Device information display and management

#### Version Module

The `version.py` module provides version information and utilities:

- Functions to retrieve application version
- Version compatibility checking

## Config Directory

The `config/` directory contains application configuration files:

```
config/
├── logging.py      # Logging configuration
├── plugins.json    # Plugin registry and configuration
└── settings.json   # Application settings
```

### Config Components

#### settings.json

Contains application settings including:

- UI configuration (panels, toolbars, themes)
- Default application behavior
- User preferences

Example `settings.json`:
```json
{
  "app": {
    "theme": "light",
    "auto_save_interval": 300
  },
  "ui": {
    "panels": {
      "left": {"visible": true, "width": 250},
      "right": {"visible": true, "width": 300},
      "bottom": {"visible": true, "height": 200}
    },
    "toolbar": {
      "visible": true,
      "pinned": false,
      "position": "top",
      "categories": {}
    }
  }
}
```

#### plugins.json

Stores plugin registry information:

- Installed plugins
- Plugin enabled/disabled status
- Plugin configuration
- Dependency information

#### logging.py

Configures application logging:

- Log formats
- Log rotation
- Log levels

## Data Directory

The `data/` directory contains application data:

```
data/
└── device_database.db  # SQLite database for device information
```

### Data Components

#### device_database.db

SQLite database with the following schema:

- **devices**: Main device information
  - id (primary key)
  - ip, mac, hostname, vendor, os
  - first_seen, last_seen
  - status, metadata, tags, notes

- **device_history**: Historical device events
  - device_id (foreign key to devices table)
  - event_type, event_data, timestamp

- **plugin_data**: Plugin-specific data storage
  - plugin_id, key, value
  - Used for persistent plugin storage

- **app_settings**: Application settings storage
  - key, value
  - Used for storing application state

## Documentation Directory

The `docs/` directory contains all application documentation:

```
docs/
├── API.md                    # Main window API documentation
├── core_structure.md         # This document
├── device_management.md      # Device management documentation
├── version_manifest.json     # Version information
├── versioning.md             # Versioning documentation
└── plugins/                  # Plugin-specific documentation
```

## Interacting with the Application Structure

### From Plugins

Plugins should interact with the application using the documented API:

- Main Window API (see `API.md`)
- Database interactions via DeviceDatabaseManager
- UI integration through panel registration

### For Developers

When developing the core application:

1. Maintain separation of concerns between modules
2. Document public APIs for plugin developers
3. Follow the established directory structure
4. Use the version management system for tracking changes 