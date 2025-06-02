# ConfigMate Plugin API

The ConfigMate Plugin provides configuration and template management capabilities for network engineers. This document describes the public API and integration points for the plugin.

## Plugin Interface

### Initialization

```python
def initialize(self, app, plugin_info)
```
Initializes the plugin with application context and plugin information.

**Parameters:**
- `app`: Main application instance
- `plugin_info`: Plugin metadata and configuration

**Returns:** 
- `True` if initialization successful, `False` otherwise

### Cleanup

```python
def cleanup(self)
```
Performs cleanup operations when the plugin is unloaded, including saving templates and disconnecting signals.

## Core Components

### Template Manager

The template manager handles creation, storage, and retrieval of configuration templates.

#### Methods

```python
def create_template(self, name, content, platform="generic", description="", variables=None)
```
Creates a new configuration template.

```python
def get_template(self, name)
```
Retrieves a template by name.

```python
def get_template_list(self)
```
Returns a list of all available templates.

```python
def update_template(self, name, content=None, platform=None, description=None, variables=None)
```
Updates an existing template.

```python
def delete_template(self, name)
```
Deletes a template.

### Config Generator

Generates device configurations from templates using variable substitution.

#### Methods

```python
def generate_config(self, device, template_name, variables=None)
```
Generates configuration for a device using the specified template.

**Parameters:**
- `device`: Device object
- `template_name`: Name of template to use
- `variables`: Dictionary of variable values

**Returns:** Generated configuration string

```python
def get_template_variables_for_device(self, device, template_name)
```
Extracts appropriate variable values for a device from its properties.

### Variable Detector

Intelligently detects template variables from device configurations.

#### Methods

```python
def detect_variables_single_config(self, config_text, device_name="device")
```
Detects variables in a single device configuration.

```python
def detect_variables_multi_config(self, config_dict)
```
Detects variables by comparing multiple device configurations.

```python
def create_template_from_config(self, config_text, device, template_format="text")
```
Creates a template from device configuration with automatic variable detection.

```python
def detect_variables_in_template(self, template_content)
```
Detects variable placeholders in existing template content.

### Config Comparator

Provides configuration comparison capabilities.

#### Methods

```python
def compare_configurations(self, config1, config2, context_lines=3)
```
Compares two configurations and returns detailed differences.

## UI Components

### Template Editor Dialog

```python
class TemplateEditorDialog(QDialog)
```
Comprehensive dialog for creating and editing templates with syntax highlighting and variable management.

#### Methods

```python
def create_from_config(self, device, config_text)
```
Initializes the editor to create a template from device configuration.

### Config Preview Widget

```python
class ConfigPreviewWidget(QWidget)
```
Right panel widget for previewing generated configurations.

## Plugin Settings

The ConfigMate plugin provides the following configurable settings:

| Setting | Description | Type | Default |
|---------|-------------|------|---------|
| `default_platform` | Default device platform for templates | choice | `cisco_ios` |
| `auto_detect_variables` | Automatically detect variables | bool | `True` |
| `syntax_highlighting` | Enable syntax highlighting | bool | `True` |
| `template_format` | Default template format | choice | `text` |
| `confirm_apply` | Confirm before applying configurations | bool | `True` |
| `max_preview_lines` | Maximum lines in preview | int | `100` |
| `backup_before_apply` | Create backup before applying | bool | `True` |
| `comparison_context_lines` | Context lines in comparisons | int | `3` |

## Context Menu Actions

The plugin registers the following context menu actions for devices:

- **Generate Configuration**: Generate config from template for selected device(s)
- **Apply Template**: Apply template configuration to device(s)
- **Create Template from Device**: Create template from device configuration

## Toolbar Actions

- **Template Manager**: Open template management dialog
- **Quick Generate**: Quick configuration generation
- **Compare Configs**: Compare device configurations
- **Test Device Info**: Debug device information (development)

## Signals

The plugin emits the following signals:

```python
template_created = Signal(str)  # template_name
template_updated = Signal(str)  # template_name  
template_deleted = Signal(str)  # template_name
config_generated = Signal(str, str)  # device_id, template_name
comparison_completed = Signal(list)  # comparison_results
```

## Integration with Other Plugins

### Command Manager Integration

The ConfigMate plugin integrates with the Command Manager plugin to:
- Retrieve cached device configurations (show running-config)
- Execute commands for configuration retrieval
- Access device credentials for configuration operations

**Dependencies:**
- Command Manager plugin must be loaded and available
- Device must have cached configuration or be accessible for command execution

## Template Formats

### Text Format (Default)
Simple placeholder format using `<VARIABLE_NAME>` syntax:

```
hostname <HOSTNAME>
interface <MGMT_INTERFACE>
 ip address <IP_ADDRESS> <SUBNET_MASK>
```

### Jinja2 Format
Full Jinja2 template syntax with filters and defaults:

```
hostname {{ hostname | default('SW01') }}
interface {{ mgmt_interface | default('GigabitEthernet0/0') }}
 ip address {{ ip_address | default('192.168.1.100') }} {{ subnet_mask | default('255.255.255.0') }}
```

## Data Storage

- **Templates**: Stored in `<workspace>/configmate/templates/`
- **Generated Configs**: Cached in `<workspace>/configmate/data/`
- **Plugin Settings**: Integrated with main application settings

## Error Handling

The plugin implements comprehensive error handling:
- Safe action wrappers prevent crashes
- Graceful fallbacks for missing dependencies
- Detailed logging for troubleshooting
- User-friendly error messages

## Requirements

- **Python**: 3.8+
- **Dependencies**: Jinja2, loguru, PySide6
- **Optional**: Command Manager plugin for device integration

## Version Compatibility

- **Plugin Version**: 1.0.0
- **Minimum App Version**: 0.8.16
- **API Version**: 1.0

## Examples

### Creating a Template Programmatically

```python
# Get the ConfigMate plugin
configmate = app.plugin_manager.get_plugin("configmate").instance

# Create a simple template
configmate.template_manager.create_template(
    name="basic_switch",
    content="""hostname <HOSTNAME>
interface <MGMT_INTERFACE>
 ip address <IP_ADDRESS> <SUBNET_MASK>""",
    platform="cisco_ios",
    description="Basic switch configuration",
    variables={
        "hostname": "SW01",
        "mgmt_interface": "GigabitEthernet0/0",
        "ip_address": "192.168.1.100",
        "subnet_mask": "255.255.255.0"
    }
)
```

### Generating Configuration

```python
# Generate config for a device
device = device_manager.get_device_by_id("device_id")
config = configmate.config_generator.generate_config(
    device, 
    "basic_switch",
    {"hostname": "SW02", "ip_address": "192.168.1.101"}
)
```

## Support

For issues, feature requests, or contributions, refer to the main NetWORKS application documentation and issue tracking system. 