# NetWORKS API Documentation Guidelines

This document provides guidelines for creating API documentation for NetWORKS and its plugins.

## Table of Contents

- [Overview](#overview)
- [API Documentation Structure](#api-documentation-structure)
- [API Documentation Files](#api-documentation-files)
- [Documentation Format](#documentation-format)
- [API Documentation Examples](#api-documentation-examples)
- [Plugin API Documentation](#plugin-api-documentation)
- [Best Practices](#best-practices)

## Overview

NetWORKS uses a comprehensive API documentation system to:

1. Help developers understand how to use and extend the platform
2. Ensure plugins can interact with each other consistently
3. Maintain a standard format for documentation
4. Make development easier with clear, accessible information

All API documentation is written in Markdown format and organized in specific locations in the codebase.

## API Documentation Structure

The API documentation is organized in a hierarchical structure:

```
docs/
├── api/                  # Main API documentation directory
│   ├── README.md         # This guide
│   ├── core.md           # Core API documentation (copied from src/core/API.md)
│   └── ui.md             # UI API documentation (copied from src/ui/API.md)
├── plugins/              # Plugin development documentation
│   └── README.md         # Plugin development guide
└── index.md              # Documentation index
```

Additionally, each component of the application has its own API.md file:

```
src/
├── core/
│   └── API.md            # Core API documentation
├── ui/
│   └── API.md            # UI API documentation
├── config.py             # Configuration module
└── app.py                # Application module

plugins/
└── plugin_name/
    └── API.md            # Plugin API documentation
```

## API Documentation Files

### Main API.md

The main `API.md` file at the root of the project provides an overview of all APIs available in NetWORKS. It includes:

1. Application interfaces
2. Device manager
3. Plugin manager
4. Configuration manager
5. UI components
6. Plugin interface

### Module-specific API.md

Each major module (core, ui) has its own `API.md` file that documents the specific APIs provided by that module in more detail.

### Plugin API.md

Each plugin must include an `API.md` file that documents the public API it exposes to other plugins.

## Documentation Format

All API documentation should follow these formatting guidelines:

### Headers

Use Markdown headers to structure the documentation:

```markdown
# Main Title (H1)
## Section (H2)
### Subsection (H3)
#### Minor section (H4)
```

### Code Blocks

Use triple backticks for code blocks, specifying the language:

````markdown
```python
def example_function():
    return "This is an example"
```
````

### API Method Documentation

Document methods in this format:

```markdown
### method_name(param1, param2=default)

Description of what the method does.

**Parameters:**
- `param1` (type): Description of parameter
- `param2` (type, optional): Description of parameter, defaults to `default`

**Returns:**
- (return_type): Description of return value

**Raises:**
- `ExceptionType`: When exception is raised

**Example:**
```python
result = method_name("example", param2=123)
```

### Class Documentation

Document classes in this format:

```markdown
## ClassName

Description of what the class represents and its purpose.

**Attributes:**
- `attribute_name` (type): Description of attribute

**Methods:**
- `method_name(params)`: Brief description
```

### Signal Documentation

Document signals in this format:

```markdown
### signal_name

Signal emitted when something happens.

**Arguments:**
- `argument` (type): Description of argument

**Example:**
```python
# Connect to the signal
object.signal_name.connect(handler_function)

# Handler function
def handler_function(argument):
    print(f"Signal received with {argument}")
```
```

## API Documentation Examples

### Class Example

```markdown
## DeviceManager

Manages devices and device groups.

**Attributes:**
- `devices` (dict): Dictionary of devices by ID
- `groups` (dict): Dictionary of groups by name
- `root_group` (DeviceGroup): Root device group

**Signals:**
- `device_added(device)`: Emitted when a device is added
- `device_removed(device)`: Emitted when a device is removed

**Methods:**
- `add_device(device)`: Add a device to the system
- `remove_device(device)`: Remove a device from the system
```

### Method Example

```markdown
### add_device(device)

Add a device to the system.

**Parameters:**
- `device` (Device): The device to add

**Returns:**
- (Device): The added device

**Raises:**
- `ValueError`: If a device with the same ID already exists

**Example:**
```python
device = Device(name="My Device")
added_device = device_manager.add_device(device)
```
```

## Plugin API Documentation

Every plugin must include an `API.md` file that documents its public API. The file should include:

### 1. Overview

A brief description of what the plugin does and its main features.

### 2. Public API

Document all public classes, methods, and properties that other plugins can use.

### 3. Device Properties

Document any device properties that the plugin adds or modifies, including:
- Property name
- Data type
- Description
- Example usage

### 4. Signals

Document any signals that the plugin emits or expects, including:
- Signal name
- Arguments
- When it's emitted
- Example of connecting to it

### 5. UI Components

Document UI components added by the plugin, including:
- Toolbar actions
- Menu items
- Panels
- Dock widgets

### 6. Integration Examples

Provide code examples of how other plugins can integrate with this plugin.

### Plugin API Documentation Template

Use this template for plugin API documentation:

```markdown
# Plugin Name API Documentation

## Overview

Brief description of what the plugin does.

## Public API

### Classes

```python
class MyPluginClass:
    """Description of the class"""
    # Class details
```

### Methods

```python
def my_plugin_method(param):
    """Description of what the method does"""
    # Method details
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| property_name | type | Description |

## Device Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| property_name | type | Description | `device.get_property("property_name")` |

## Signals

| Signal | Arguments | Description |
|--------|-----------|-------------|
| signal_name | (arg_type) | Description |

## UI Components

| Component | Type | Description |
|-----------|------|-------------|
| component_name | type | Description |

## Integration Examples

```python
# Example of how to use this plugin from another plugin
def integrate_with_plugin(self):
    plugin = self.plugin_manager.get_plugin("plugin_id").instance
    if plugin:
        plugin.some_method()
```
```

## Best Practices

1. **Keep Documentation Updated**: Update the API documentation whenever the API changes
2. **Be Comprehensive**: Document all public APIs that others might use
3. **Include Examples**: Provide usage examples for complex functionality
4. **Use Clear Language**: Write in simple, clear English
5. **Explain Why, Not Just How**: Explain the purpose of APIs, not just their mechanics
6. **Document Breaking Changes**: Clearly mark breaking changes in API documentation
7. **Provide Context**: Include context for how different APIs work together
8. **Document Limitations**: Be clear about any limitations or edge cases
9. **Include Version Information**: Note which version of the application the documentation applies to
10. **Follow the Format**: Adhere to the documentation format guidelines 