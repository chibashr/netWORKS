# netWORKS Plugin Development Guide

This comprehensive guide explains how to create plugins for the netWORKS application. It provides detailed information about plugin structure, registration methods, and best practices.

## Table of Contents

1. [Plugin Structure](#plugin-structure)
2. [Plugin Lifecycle](#plugin-lifecycle)
3. [Registration Methods](#registration-methods)
4. [Complete Plugin Example](#complete-plugin-example)
5. [Common Patterns and Best Practices](#common-patterns-and-best-practices)
6. [Common Mistakes to Avoid](#common-mistakes-to-avoid)
7. [Plugin API Reference](#plugin-api-reference)

## Plugin Structure

### Required Files and Structure

A basic plugin requires the following structure:

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

### The Manifest File

Every plugin must have a `manifest.json` file that defines its metadata and dependencies. Here's a template:

```json
{
    "name": "your-plugin-name",           // Required: Unique identifier (use kebab-case)
    "displayName": "Your Plugin Name",     // Required: User-friendly name
    "version": "1.0.0",                   // Required: Semantic versioning
    "description": "Description of your plugin",  // Required: Brief description
    "author": "Your Name",                // Required: Author information
    "main": "main.py",                    // Required: Entry point file (must contain init_plugin function)
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

### The Main Plugin Module

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

## Plugin Lifecycle

### Loading Process

1. **Discovery**: The plugin manager scans the `plugins/` directory for folders with `manifest.json` files
2. **Registration**: Each discovered plugin is registered with the plugin manager
3. **Dependency Checking**: Plugin dependencies are verified
4. **Installation**: Plugin-specific requirements are installed
5. **Initialization**: The plugin's `init_plugin` function is called with a PluginAPI instance
6. **UI Integration**: The plugin registers UI components using the API

### Implementation Details

The plugin loading process follows these steps:

1. The `PluginManager` discovers plugins by scanning the plugins directory
2. It creates a `PluginAPI` instance for each plugin
3. It loads the main module using Python's `importlib`
4. It calls the `init_plugin` function with the PluginAPI instance
5. The plugin instance is stored in the plugin manager
6. When the main window is ready, UI components are created and registered

## Registration Methods

### How to Register UI Components

Plugins can register UI components using these PluginAPI methods:

```python
# Register a panel (left, right, or bottom)
self.api.register_panel(panel_widget, "left", "Panel Name")

# Add a tab to the bottom panel
self.api.add_tab(tab_widget, "Tab Name", "path/to/icon.png")

# Register a menu item
self.api.register_menu_item(
    label="Menu Item",
    callback=self.do_action,
    enabled_callback=lambda: True,  # Function that determines if item is enabled
    parent_menu="Tools"  # Parent menu name
)

# Register a toolbar
self.api.register_toolbar(toolbar_widget, category="Tools")
```

### How to Register Event Hooks

Plugins can register for application events using hooks:

```python
# Using decorator syntax
@self.api.hook("device_select")
def on_device_select(device):
    self.api.log(f"Device selected: {device['ip']}")

# Using function syntax
def on_scan_complete(results):
    self.api.log(f"Scan complete: {len(results)} devices found")
self.api.register_hook("scan_complete", on_scan_complete)
```

Available hooks include:
- `device_select`: Called when a device is selected
- `before_scan`: Called before a network scan starts
- `after_scan`: Called after a network scan completes
- `device_found`: Called when a new device is discovered

### How to Register Plugin Functionality

Plugins can register new functionality with the application:

```python
# Register a new scan type
self.api.register_scan_type(
    name="Port Scan",
    handler=self.perform_port_scan,
    description="Scan for open ports on a device",
    default_options={"ports": "1-1024", "timeout": 1.0}
)

# Register a new device action
self.api.register_device_action(
    name="Ping",
    handler=self.ping_device,
    description="Send ICMP ping to device",
    icon_path="path/to/icon.png"
)
```

## Complete Plugin Example

Here's a complete example of a simple plugin:

```python
# main.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt

class SimplePlugin:
    """A simple example plugin for netWORKS."""
    
    def __init__(self, plugin_api):
        self.api = plugin_api
        self.api.log("Simple plugin initializing...")
        
        # Register with main window when ready
        self.api.on_main_window_ready(self.create_ui)
        
        # Register hooks
        self.register_hooks()
        
        self.api.log("Simple plugin initialized")
    
    def register_hooks(self):
        """Register event hooks."""
        @self.api.hook("device_select")
        def on_device_select(device):
            if device:
                self.api.log(f"Device selected: {device['ip']}")
    
    def create_ui(self):
        """Create UI components."""
        # Create left panel
        self.left_panel = QWidget()
        layout = QVBoxLayout(self.left_panel)
        
        title = QLabel("Simple Plugin")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        button = QPushButton("Hello World")
        button.clicked.connect(self.say_hello)
        layout.addWidget(button)
        
        # Register panel with application
        self.api.register_panel(self.left_panel, "left", "Simple Plugin")
        
        # Create bottom panel tab
        self.bottom_panel = QWidget()
        tab_layout = QVBoxLayout(self.bottom_panel)
        
        tab_label = QLabel("This is a simple plugin tab")
        tab_layout.addWidget(tab_label)
        
        # Add tab to bottom panel
        self.api.add_tab(self.bottom_panel, "Simple Plugin")
        
        # Register menu item
        self.api.register_menu_item(
            label="Say Hello",
            callback=self.say_hello,
            enabled_callback=lambda: True,
            parent_menu="Tools"
        )
    
    def say_hello(self):
        """Say hello to the user."""
        self.api.log("Hello, World!")
        
        # Show in UI if main window is available
        if hasattr(self.api, 'main_window') and self.api.main_window:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self.api.main_window, "Hello", "Hello, World!")
    
    def cleanup(self):
        """Clean up plugin resources."""
        # Remove UI components
        if hasattr(self, 'bottom_panel'):
            self.api.remove_tab("Simple Plugin")
        
        self.api.log("Simple plugin cleanup complete")

def init_plugin(plugin_api):
    """Initialize the plugin."""
    return SimplePlugin(plugin_api)
```

And the corresponding `manifest.json`:

```json
{
    "name": "simple-plugin",
    "displayName": "Simple Plugin",
    "version": "1.0.0",
    "description": "A simple example plugin for netWORKS",
    "author": "netWORKS Team",
    "main": "main.py",
    "dependencies": [],
    "ui": {
        "panels": ["left", "bottom"]
    }
}
```

## Common Patterns and Best Practices

### Deferred UI Initialization

Wait for the main window to be ready before initializing UI components:

```python
def __init__(self, plugin_api):
    self.api = plugin_api
    
    # Register for main window ready notification
    self.api.on_main_window_ready(self.init_ui)
    
def init_ui(self):
    """Initialize UI components when main window is ready."""
    # Create and register UI components
    self.left_panel = self.create_left_panel()
    self.results_tab = self.create_results_tab()
```

### Error Handling

Always handle exceptions to prevent plugin errors from affecting the main application:

```python
def perform_action(self):
    try:
        # Perform action
        result = self.do_something_risky()
        return result
    except Exception as e:
        self.api.log(f"Error performing action: {str(e)}", level="ERROR")
        return None
```

### Resource Cleanup

Implement proper cleanup to release resources when the plugin is disabled:

```python
def cleanup(self):
    """Clean up plugin resources when disabled."""
    # Remove UI components
    if hasattr(self, 'left_panel'):
        self.api.remove_panel(self.left_panel)
        
    # Stop background tasks
    if hasattr(self, 'scanner') and self.scanner:
        self.scanner.stop()
```

### Long-Running Operations

Perform time-consuming operations in background threads:

```python
def start_scan(self):
    """Start a network scan in the background."""
    # Show progress
    self.api.show_progress(True)
    
    # Start scan in background thread
    import threading
    self.scan_thread = threading.Thread(target=self._run_scan)
    self.scan_thread.daemon = True
    self.scan_thread.start()
```

## Common Mistakes to Avoid

1. **Missing init_plugin function**: Every plugin must have an `init_plugin` function that returns an instance of your plugin class.
2. **Not handling exceptions**: Always catch exceptions to prevent your plugin from crashing the main application.
3. **Direct UI manipulation**: Always use the PluginAPI to register UI components and interact with the application.
4. **Missing cleanup method**: Implement a cleanup method to release resources when your plugin is disabled.
5. **Blocking the UI thread**: Perform long-running operations in background threads to keep the UI responsive.
6. **Hardcoded paths**: Use relative paths and the plugin's directory for resources.
7. **Not checking if main window is ready**: Always check if the main window is ready before registering UI components.

## Plugin API Reference

Here's a summary of the available PluginAPI methods:

### UI Registration
- `register_panel(panel, location, name)`: Register a panel in the specified location (left, right, bottom)
- `add_tab(widget, title, icon_path=None)`: Add a tab to the bottom panel
- `remove_tab(title)`: Remove a tab from the bottom panel
- `register_menu_item(label, callback, enabled_callback=None, parent_menu="Tools")`: Register a menu item
- `register_toolbar(toolbar, category="Tools")`: Register a toolbar

### Events and Hooks
- `hook(hook_name)`: Decorator to register a hook callback
- `register_hook(hook_name, callback)`: Register a hook callback
- `emit_event(event_name, data=None)`: Emit an event to other plugins
- `on_main_window_ready(callback)`: Register a callback for when the main window is ready

### Logging and Progress
- `log(message, level="INFO")`: Log a message to the application log
- `show_progress(show)`: Show or hide the progress bar
- `update_progress(value, maximum)`: Update the progress bar value

### Settings and Data
```python
# Get plugin configuration
config = api.get_config()

# Save plugin configuration
api.save_config(config)

# Get application configuration
app_config = api.get_app_config()

# Accessing device data
selected_device = api.get_selected_devices()
all_devices = api.get_all_devices()
api.add_device(device_data)
api.update_device(device_data)
api.remove_device(device_id)
results = api.search_devices("query")

# Managing device groups
groups = api.get_device_groups()
api.create_device_group("Servers")
api.add_device_to_group(device_id, "Servers")
devices_in_group = api.get_devices_in_group("Servers")
```

### Application Information
- `get_network_interfaces()`: Get list of network interfaces
- `get_current_device()`: Get the currently selected device

### Inter-Plugin Communication
- `call_plugin_function(plugin_id, function_name, *args, **kwargs)`: Call a function in another plugin
- `has_plugin(plugin_id)`: Check if a plugin is available
- `send_message(target_plugin_id, message)`: Send a message to another plugin
- `broadcast_message(message)`: Broadcast a message to all plugins
- `register_message_handler(handler)`: Register a handler for messages from other plugins

By following this guide, you can create powerful plugins that extend the netWORKS application while maintaining compatibility and stability. 