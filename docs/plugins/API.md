# Plugin API Documentation Template

This template provides a standardized format for documenting your plugin's API. Every plugin that exposes functionality to other plugins must include API documentation following this format to ensure consistency across all netWORKS plugins.

---

# [Your Plugin Name] API Documentation

## API Version
```
API Version: 1.0.0
Compatible with netWORKS version: 1.0.0+
```

## Overview

[Provide a brief description of your plugin's purpose and the functionality it exposes to other plugins. Explain when and why other plugins might want to use your API.]

## Exported Functions

### functionName(param1, param2)

**Description:** [Detailed description of what the function does]

**Parameters:**
- `param1` (type): [Description of parameter]
- `param2` (type): [Description of parameter]

**Returns:** [Description of return value and its structure]

**Errors:** [List of possible error codes/messages and their meaning]

**Example:**
```python
result = plugin_api.call_plugin_function("your-plugin-id", "functionName", param1, param2)
if result["success"]:
    print(f"Operation successful: {result['data']}")
else:
    print(f"Error: {result['error']}")
```

### anotherFunction(param)

[Document each exported function following the same pattern]

## Events/Hooks

### your-plugin:eventName

**Description:** [Description of when this event is emitted]

**Data Structure:**
```python
{
  "field1": "string value",  # Description of field1
  "field2": 123,             # Description of field2
  "nested": {                # Nested object example
    "subfield": true
  }
}
```

**Example Usage:**
```python
@plugin_api.hook("your-plugin:eventName")
def handle_event(data):
    # Handle event data
    print(f"Received event with field1: {data['field1']}")
```

### your-plugin:anotherEvent

[Document each event following the same pattern]

## Data Structures

### StructureName

**Description:** [Description of what this data structure represents]

**Fields:**
- `field1` (type): [Description of field]
- `field2` (type): [Description of field]
- `nested` (object): [Description of nested object]
  - `subfield` (type): [Description of nested field]

## Integration Examples

[Provide complete examples showing how to integrate with your plugin]

```python
# Example of using plugin functionality
from netWORKS import plugin_api

def use_your_plugin():
    # Check if plugin is available
    if plugin_api.has_plugin("your-plugin-id"):
        # Call plugin function
        result = plugin_api.call_plugin_function(
            "your-plugin-id", 
            "functionName", 
            "param1_value", 
            {"param2_key": "param2_value"}
        )
        
        # Handle result
        if result["success"]:
            data = result["data"]
            # Process data
        else:
            # Handle error
            error = result["error"]
            print(f"Error: {error}")
    
    # Register for plugin events
    @plugin_api.hook("your-plugin:eventName")
    def handle_your_event(data):
        # Process event data
        print(f"Received event data: {data}")
```

## Version History

[Document changes to your API across versions, highlighting any breaking changes]

- 1.0.0 (YYYY-MM-DD): Initial release
- 1.1.0 (YYYY-MM-DD): Added functionName2, deprecated oldFunction
- 2.0.0 (YYYY-MM-DD): Breaking change - restructured return values for functionName

---

## How to Use This Template

1. Copy this template to your plugin's directory as `API.md`
2. Replace all placeholders (text in brackets) with your plugin's information
3. Document all functions, events, and data structures your plugin exports
4. Add complete integration examples
5. Remove any sections that don't apply to your plugin
6. Update the version history as your API evolves

# Plugin API Reference

This document provides a reference for the API available to plugins in the netWORKS platform.

## Core API

The core API provides fundamental functionality for plugins to interact with the main application.

### API Methods

#### UI Integration

```python
# Register a panel in the specified location
api.register_panel(panel, location, name=None)

# Remove a panel from the UI
api.remove_panel(panel)

# Add a menu item
api.register_menu_item(label, callback, parent_menu=None, icon_path=None, shortcut=None, enabled_callback=None)

# Register a multi-device menu item (appears when multiple devices are selected)
api.register_multi_device_menu_item(label, callback, parent_menu=None, icon_path=None, shortcut=None)

# Add a toolbar widget
api.add_toolbar_widget(widget, category="Tools")

# Log a message to the application log panel
api.log(message, level="INFO")  # Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

#### Device Access

```python
# Get the currently selected device(s)
# Returns a single device dictionary if one device is selected
# Returns a list of device dictionaries if multiple devices are selected
selected = api.get_selected_devices()

# Get all devices
devices = api.get_all_devices()

# Add a device to the workspace
api.add_device(device_data)

# Update a device
api.update_device(device_data)

# Remove a device
api.remove_device(device_id)

# Search for devices
results = api.search_devices(query)
```

#### Device Groups

```python
# Get all device groups
groups = api.get_device_groups()

# Create a new device group
success = api.create_device_group(group_name)

# Delete a device group
success = api.delete_device_group(group_name)

# Add a device to a group
success = api.add_device_to_group(device_id, group_name)

# Remove a device from a group
success = api.remove_device_from_group(device_id, group_name)

# Get all devices in a group
devices = api.get_devices_in_group(group_name)

# Get all groups a device belongs to
device_groups = api.get_device_groups_for_device(device_id)
```

#### Configuration

```python
# Get plugin configuration
config = api.get_config()

# Save plugin configuration
api.save_config(config)

# Get application configuration
app_config = api.get_app_config()
```

#### Event Handling

```python
# Register a callback for an event
api.register_event_handler(event_name, callback)

# Unregister an event handler
api.unregister_event_handler(event_name, callback)

# Fire an event
api.fire_event(event_name, data=None)
```

## Core Events

Plugins can register handlers for various application events:

```python
# Device events
api.register_event_handler("device_added", my_callback)
api.register_event_handler("device_updated", my_callback)
api.register_event_handler("device_removed", my_callback)
api.register_event_handler("device_selected", my_callback)
api.register_event_handler("devices_selected", my_callback)  # For multi-selection

# Plugin events
api.register_event_handler("plugin_enabled", my_callback)
api.register_event_handler("plugin_disabled", my_callback)

# Group events
api.register_event_handler("group_created", my_callback)
api.register_event_handler("group_updated", my_callback)
api.register_event_handler("group_deleted", my_callback)
api.register_event_handler("device_added_to_group", my_callback)
api.register_event_handler("device_removed_from_group", my_callback)

# Application events
api.register_event_handler("app_started", my_callback)
api.register_event_handler("app_shutdown", my_callback)
```

## Plugin Dependencies

Plugins can depend on other plugins and access their APIs:

```python
# Specify dependencies in plugin manifest
dependencies = ["core-workspace", "network-scanner"]

# Access another plugin's API
workspace_api = api.get_plugin_api("core-workspace")
scanner_api = api.get_plugin_api("network-scanner")

# Call functions from another plugin's API
result = workspace_api.call_function("get_workspace_path")
```

## Event Callback Signatures

The callbacks for events have specific signatures:

```python
# Device event callbacks
def on_device_added(device):
    # device is a dictionary with device data
    pass

def on_device_updated(device):
    # device is a dictionary with updated device data
    pass

def on_device_removed(device_id):
    # device_id is a string ID of the removed device
    pass

def on_device_selected(device):
    # device is a dictionary with selected device data
    pass

def on_devices_selected(devices):
    # devices is a list of dictionaries with selected devices data
    pass

# Group event callbacks
def on_group_created(group_name):
    # group_name is a string
    pass

def on_group_updated(group_name):
    # group_name is a string
    pass

def on_group_deleted(group_name):
    # group_name is a string
    pass

def on_device_added_to_group(device_id, group_name):
    # device_id is a string, group_name is a string
    pass

def on_device_removed_from_group(device_id, group_name):
    # device_id is a string, group_name is a string
    pass
```

## Multi-Device Operations

Plugins can register actions that operate on multiple selected devices:

```python
# Register a multi-device menu item
api.register_multi_device_menu_item(
    label="Process Selected Devices",
    callback=self.process_multiple_devices,
    parent_menu="My Plugin"
)

# Callback receives a list of device dictionaries
def process_multiple_devices(self, devices):
    # Perform operations on multiple devices
    for device in devices:
        # Process each device
        self.api.log(f"Processing device: {device.get('ip')}")
        # Perform batch operations
```

## Plugin API Example

```python
class ExamplePlugin:
    def __init__(self, api):
        self.api = api
        
    def initialize(self):
        # Register a menu item
        self.api.register_menu_item(
            label="Example Action",
            callback=self.example_action,
            parent_menu="Tools"
        )
        
        # Register a multi-device menu item
        self.api.register_multi_device_menu_item(
            label="Process Selected Devices",
            callback=self.process_devices,
            parent_menu="Tools"
        )
        
        # Register event handlers
        self.api.register_event_handler("device_added", self.on_device_added)
        self.api.register_event_handler("devices_selected", self.on_devices_selected)
        
        # Create device groups
        self.api.create_device_group("Servers")
        self.api.create_device_group("Workstations")
        
        # Log initialization
        self.api.log("Example plugin initialized", level="INFO")
        
    def example_action(self):
        device = self.api.get_selected_devices()
        if device:
            self.api.log(f"Selected device: {device.get('ip')}")
        
    def process_devices(self, devices):
        self.api.log(f"Processing {len(devices)} devices")
        for device in devices:
            self.api.log(f"Processing {device.get('ip')}")
            
    def on_device_added(self, device):
        self.api.log(f"Device added: {device.get('ip')}")
        
    def on_devices_selected(self, devices):
        self.api.log(f"{len(devices)} devices selected")
```
