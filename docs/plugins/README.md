# netWORKS Plugin Development Guide

This guide explains how to create plugins for netWORKS, including how to interact with the application and other plugins, expose functionality, and integrate with the UI.

## Table of Contents
1. [Plugin Structure](#plugin-structure)
2. [Plugin Manifest](#plugin-manifest)
3. [Plugin Entry Point](#plugin-entry-point)
4. [Plugin API](#plugin-api)
5. [UI Integration](#ui-integration)
6. [Inter-Plugin Communication](#inter-plugin-communication)
7. [Hooks and Events](#hooks-and-events)
8. [Documentation Requirements](#documentation-requirements)
9. [Example Plugin](#example-plugin)
10. [UI Framework](#ui-framework)

## Plugin Structure

### Directory Structure

Each plugin should have the following structure:

```
plugins/
└── your_plugin_name/
    ├── manifest.json   # Required: Plugin metadata and configuration
    ├── main.py         # Required: Main plugin code with init_plugin function
    ├── README.md       # Required: User documentation
    ├── API.md          # Required if plugin exposes APIs to other plugins
    ├── requirements.txt # Optional: Python dependencies for this plugin
    └── assets/         # Optional: Plugin resources like images
```

## Plugin Manifest

Every plugin requires a `manifest.json` file that defines its metadata, dependencies and APIs. Here's an example:

```json
{
    "name": "your-plugin-name",           // Required: Unique identifier (use kebab-case)
    "displayName": "Your Plugin Name",     // Required: User-friendly name
    "version": "1.0.0",                   // Required: Semantic versioning
    "description": "Description of your plugin",  // Required: Brief description
    "author": "Your Name",                // Required: Author information
    "main": "main.py",                    // Required: Entry point file
    "dependencies": [],                   // Optional: List of other plugin dependencies
    "ui": {                               // Optional: UI registration
        "panels": ["left", "right", "bottom"]  // UI panels used by the plugin
    },
    "hooks": {                            // Optional: Hook definitions
        "your_event": {
            "description": "Called when something happens"
        }
    },
    "exports": {                          // Optional: Exported API for other plugins
        "function_name": {
            "description": "What this function does",
            "parameters": ["param1", "param2"],
            "returns": "Description of return value"
        }
    }
}
```

## Plugin Entry Point

The main plugin module (`main.py` by default) must contain an `init_plugin` function that returns an instance of your plugin class:

```python
def init_plugin(plugin_api):
    """
    Required entry point for the plugin.
    
    Args:
        plugin_api: Instance of PluginAPI for interacting with the application
        
    Returns:
        An instance of your plugin class
    """
    return YourPluginClass(plugin_api)
```

## Plugin API

The PluginAPI provides methods for interacting with the netWORKS application:

### UI Registration
- Register panels, tabs, menu items, and toolbars
- Access to the main window and application UI
- Customizing the UI for your plugin

### Events and Hooks
- Register callbacks for application events
- Create custom events for other plugins
- React to user actions and application state changes

### Logging and Settings
- Log messages to the application log
- Store and retrieve plugin settings
- Persist data between sessions

### Inter-Plugin Communication
- Call functions in other plugins
- Send and receive messages
- Broadcast events to other plugins

## UI Integration

Plugins can integrate with the UI in several ways:

> **IMPORTANT**: For detailed information about the UI framework, including the migration from PyQt5 to PySide6, please refer to the [UI Framework Guide](UI_FRAMEWORK.md).

### Panels
Plugins can register panels in the left, right, or bottom areas:
```python
self.api.register_panel(panel_widget, "left", "Panel Name")
```

Important considerations when creating panels:
- Panels must be created in the main thread, or properly moved to the main thread before registration
- Do not set a parent for your panel widgets before registration; the main window will handle this
- Use Qt signals/slots for thread-safe communication between your plugin logic and UI components
- Never directly modify UI components from a background thread

#### Recommended Pattern: Delayed UI Initialization

The most reliable approach for creating UI components is to wait until the main window is fully initialized:

```python
class YourPlugin(QObject):
    def __init__(self, plugin_api):
        super().__init__()
        self.api = plugin_api
        self.logger = logging.getLogger(__name__)
        
        # UI components - initialized as None
        self.left_panel = None
        self.right_panel = None
        
        # Register main window ready callback
        self.api.on_main_window_ready(self.init_ui)
        
        # Other non-UI initialization can happen here
        # ...
    
    def init_ui(self):
        """Initialize UI components once main window is available."""
        try:
            # Import UI components here to ensure they're loaded in the main thread
            from ui.your_panel import YourLeftPanel, YourRightPanel
            
            # Create panels
            self.left_panel = YourLeftPanel(self)
            self.right_panel = YourRightPanel(self)
            
            # Set plugin_id property
            self.left_panel.setProperty("plugin_id", "your-plugin-id")
            self.right_panel.setProperty("plugin_id", "your-plugin-id")
            
            # Register panels with main window
            self.api.register_panel(self.left_panel, "left", "Your Panel")
            self.api.register_panel(self.right_panel, "right", "Settings")
        except Exception as e:
            self.logger.error(f"Error creating UI: {str(e)}")

### Tabs
Plugins can add tabs to the bottom panel:
```python
self.api.add_tab(tab_widget, "Tab Name")
```

### Menu Items
Plugins can add items to the application menus:
```python
self.api.register_menu_item(
    label="Menu Item",
    callback=self.do_action,
    enabled_callback=lambda: True,  # Function that determines if item is enabled
    parent_menu="Tools"  # Parent menu name
)
```

## Inter-Plugin Communication

Plugins can communicate with each other using:

### Direct Function Calls
```python
result = self.api.call_plugin_function("other-plugin", "function_name", arg1, arg2)
```

### Event System
```python
# Emit an event
self.api.emit_event("my-plugin:custom_event", {"data": "value"})

# Listen for events from other plugins
@self.api.hook("other-plugin:event_name")
def handle_event(data):
    # Process event data
    pass
```

## Hooks and Events

The application provides several core hooks that plugins can register for:

- `device_select`: Called when a device is selected
- `before_scan`: Called before a network scan starts
- `after_scan`: Called after a network scan completes
- `device_found`: Called when a new device is discovered

Example:
```python
@self.api.hook("device_select")
def on_device_select(device):
    if device:
        self.api.log(f"Device selected: {device['ip']}")
```

## Device Discovery and Integration

Plugins that discover network devices need to properly communicate with the main application to ensure devices are displayed in the device table and stored in the database. The following methods are available for device integration:

### Device Data Structure

Discovered devices should include at least the following fields:

```python
device = {
    'id': str(uuid.uuid4()),  # Optional - will be generated if missing
    'ip': '192.168.1.100',    # Required
    'hostname': 'device-100', # Should be provided if available
    'mac': '00:11:22:33:44:55', # Should be provided if available
    'first_seen': '2023-07-15 14:30:22', # Will use current time if missing
    'last_seen': '2023-07-15 14:30:22',  # Will use current time if missing
    'scan_method': 'ping',    # Should indicate how the device was found
    'status': 'active',       # Optional status information
    'metadata': {             # Optional metadata
        'discovery_source': 'plugin_name',
        'os': 'Windows 10'
    }
}
```

### Methods for Adding Devices

Plugins should attempt these methods in order:

1. **Direct Device Table Integration**
   ```python
   if hasattr(self.api.main_window, 'device_table'):
       self.api.main_window.device_table.add_device(device)
   ```

2. **Database Manager Integration**
   ```python
   if hasattr(self.api.main_window, 'database_manager'):
       self.api.main_window.database_manager.add_device(device)
   ```

3. **Core Plugin Function**
   ```python
   self.api.call_plugin_function("core", "add_device", device)
   ```

4. **Emit Device Found Signal**
   If your plugin provides a device_found Signal, ensure the main window can connect to it:
   ```python
   class YourPlugin(QObject):
       device_found = Signal(dict)
       
       def discover_device(self, device):
           # Process device
           self.device_found.emit(device)
   ```

### Debugging Device Integration

If devices are detected but not appearing in the main application:

1. Check that your device dictionary contains all required fields
2. Verify that signals are properly connected
3. Implement more detailed logging to diagnose the issue:
   ```python
   try:
       self.logger.debug(f"Adding device {device['ip']} to table")
       self.api.main_window.device_table.add_device(device)
   except Exception as e:
       self.logger.error(f"Error adding device: {str(e)}", exc_info=True)
   ```

4. Ensure your plugin properly initializes after the main window is ready:
   ```python
   def __init__(self, plugin_api):
       # ...
       self.api.on_main_window_ready(self.init_ui)
   ```

## Documentation Requirements

For detailed information on plugin documentation requirements, please refer to [documentation_requirements.md](documentation_requirements.md) which outlines the standards for both user documentation (README.md) and developer API documentation (API.md).

## Example Plugin

For a complete example of a functional plugin, refer to the [example_plugin](example_plugin/) directory, which demonstrates:

- Basic plugin structure
- UI integration
- Hook registration
- API documentation
- User documentation

This example serves as a template for developing your own plugins and showcases best practices for plugin development.

## UI Framework

netWORKS has migrated from PyQt5 to PySide6 as its primary UI framework. All new plugins should use PySide6 for UI components, while backward compatibility with PyQt5 is maintained for legacy plugins.

For detailed information about working with the UI framework, please refer to the [UI Framework Guide](UI_FRAMEWORK.md), which covers:

- Qt framework migration status 
- How to properly use PySide6 imports and signals/slots
- Thread safety with UI components
- Best practices for plugin UI development
- Common mistakes to avoid

Properly using the UI framework ensures your plugin will integrate smoothly with the main application and provide a consistent user experience.

## Best Practices

- Handle exceptions to prevent plugin errors from affecting the main application
- Implement proper cleanup to release resources when the plugin is disabled
- Perform long-running operations in background threads to keep the UI responsive
- Use relative paths and the plugin's directory for resources
- Check if the main window is ready before registering UI components