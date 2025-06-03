# ConfigMate Plugin - Usage Guide

This comprehensive guide covers all aspects of using the ConfigMate plugin for configuration and template management in NetWORKS.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Template Management](#template-management)
3. [Configuration Generation](#configuration-generation)
4. [Configuration Comparison](#configuration-comparison)
5. [Variable System](#variable-system)
6. [Batch Operations](#batch-operations)
7. [Export Capabilities](#export-capabilities)
8. [Settings Configuration](#settings-configuration)
9. [Integration Features](#integration-features)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

Before using ConfigMate, ensure:

- NetWORKS version 0.8.16 or higher is installed
- ConfigMate plugin is enabled in the Plugin Manager
- Command Manager plugin is available (for device integration)
- Devices are added to your NetWORKS workspace

### First Launch

1. **Access ConfigMate**: Look for ConfigMate actions in:
   - **Toolbar**: Template Manager, Quick Generate, Compare Configs buttons
   - **Menu**: Tools > ConfigMate submenu
   - **Context Menu**: Right-click on devices for ConfigMate options

2. **Initial Setup**: The plugin will automatically:
   - Create necessary directories in your workspace
   - Initialize template storage
   - Create a sample template if none exist

### Interface Overview

ConfigMate integrates into NetWORKS through:

- **Toolbar Actions**: Quick access to main functions
- **Device Context Menus**: Right-click actions for selected devices
- **Right Panel**: Configuration preview widget
- **Settings Pages**: Comprehensive configuration options

## Template Management

### Understanding Templates

Templates are configuration blueprints that use variables to generate device-specific configurations. ConfigMate supports multiple template formats:

- **Text**: Simple text with basic variable substitution
- **Jinja2**: Advanced templating with conditional logic and loops
- **Simple**: Basic variable replacement for quick templates
- **Python**: Execute Python code for complex generation logic

### Creating Templates

#### Method 1: From Device Configuration

This is the recommended approach for creating templates from existing device configurations.

1. **Select Source Device**:
   - Right-click a device with configuration data
   - Choose **"Create Template from Device"**

2. **Choose Configuration Source**:
   - Running configuration (most common)
   - Startup configuration
   - Cached command outputs
   - Manual text input

3. **Variable Detection**:
   - ConfigMate automatically detects potential variables
   - Review suggested variables (hostname, IP addresses, interface names, etc.)
   - Add, remove, or modify variables as needed
   - Set variable types and default values

4. **Template Configuration**:
   - **Name**: Descriptive template name
   - **Platform**: Target device platform (Cisco IOS, NX-OS, Juniper, Generic)
   - **Format**: Template format (text, Jinja2, simple, Python)
   - **Description**: Optional description and usage notes

5. **Save Template**:
   - Review the generated template
   - Test with sample variables
   - Save to template library

#### Method 2: Manual Template Creation

For creating templates from scratch or when you have specific requirements.

1. **Open Template Manager**:
   - Click **Template Manager** in toolbar
   - Or go to **Tools > ConfigMate > Template Manager**

2. **Create New Template**:
   - Click **"New Template"** button
   - Choose template format

3. **Enter Template Content**:
   ```text
   # Example Text Template
   hostname {hostname}
   !
   interface GigabitEthernet0/1
    ip address {mgmt_ip} {subnet_mask}
    no shutdown
   !
   ip route 0.0.0.0 0.0.0.0 {default_gateway}
   ```

4. **Define Variables**:
   - Use the Variables panel to define:
     - Variable names
     - Data types (string, IP address, integer, etc.)
     - Default values
     - Validation rules

5. **Test Template**:
   - Use the Preview panel to test with sample values
   - Verify generated configuration is correct

### Advanced Template Features

#### Jinja2 Templates

Jinja2 templates support advanced features:

```jinja2
{# Jinja2 Template Example #}
hostname {{ hostname }}
!
{% for interface in interfaces %}
interface {{ interface.name }}
 description {{ interface.description }}
 ip address {{ interface.ip }} {{ interface.mask }}
 {% if interface.shutdown %}
 shutdown
 {% else %}
 no shutdown
 {% endif %}
!
{% endfor %}

{# Conditional configuration based on device type #}
{% if device_type == 'router' %}
ip routing
{% elif device_type == 'switch' %}
spanning-tree mode rapid-pvst
{% endif %}
```

#### Python Templates

For complex logic and calculations:

```python
# Python Template Example
def generate_config(device, variables):
    config = []
    config.append(f"hostname {variables['hostname']}")
    config.append("!")
    
    # Dynamic VLAN configuration
    for vlan_id in range(variables['start_vlan'], variables['end_vlan'] + 1):
        config.append(f"vlan {vlan_id}")
        config.append(f" name VLAN_{vlan_id:04d}")
    
    # Calculate subnet based on device ID
    device_id = int(variables['device_id'])
    subnet = f"192.168.{device_id}.0/24"
    config.append(f"ip route 0.0.0.0 0.0.0.0 192.168.{device_id}.1")
    
    return "\n".join(config)
```

### Template Management Operations

#### Organizing Templates

- **Categories**: Organize templates by device type, function, or location
- **Tags**: Add tags for easy searching and filtering
- **Versioning**: Keep multiple versions of templates
- **Sharing**: Export/import templates between workspaces

#### Template Editing

1. **Open Existing Template**:
   - Double-click template in Template Manager
   - Or select and click **"Edit"**

2. **Make Changes**:
   - Modify template content
   - Update variables
   - Change settings

3. **Version Control**:
   - ConfigMate automatically creates backups
   - Track changes with version notes
   - Revert to previous versions if needed

## Configuration Generation

### Single Device Generation

Generate configuration for a single device:

1. **Select Device**: Click on device in device table

2. **Choose Method**:
   - **Context Menu**: Right-click > "Generate Configuration"
   - **Quick Generate**: Use toolbar button for fast generation
   - **Template Manager**: Select template and target device

3. **Template Selection**:
   - Choose from available templates
   - Filter by platform compatibility
   - Preview template content

4. **Variable Configuration**:
   - Review auto-populated variables from device properties
   - Override default values as needed
   - Add custom variables

5. **Generation Options**:
   - **Preview Only**: Generate and display without applying
   - **Save to File**: Export generated configuration
   - **Apply to Device**: Deploy configuration (with safety checks)

6. **Review Output**:
   - Check generated configuration for accuracy
   - Validate syntax if platform supports it
   - Make manual adjustments if necessary

### Batch Generation

Generate configurations for multiple devices simultaneously:

1. **Select Multiple Devices**:
   - Use Ctrl+click to select multiple devices
   - Or select device group

2. **Launch Batch Generation**:
   - Use **"Quick Generate"** from toolbar
   - Or right-click selection > "Generate Configuration"

3. **Template and Variables**:
   - Choose template for all devices
   - Configure variables that apply to all devices
   - Set device-specific variable overrides

4. **Generation Settings**:
   - **Parallel Processing**: Enable for faster generation
   - **Error Handling**: Choose how to handle failures
   - **Output Format**: Select format for generated configs

5. **Monitor Progress**:
   - Progress bar shows generation status
   - Error log displays any issues
   - Success/failure summary

6. **Review Results**:
   - Individual device configurations
   - Success/failure status for each device
   - Export or apply configurations as needed

## Configuration Comparison

### Setting Up Comparisons

1. **Select Devices**: Choose 2 or more devices to compare

2. **Launch Comparison**:
   - Click **"Compare Configs"** in toolbar
   - Or Tools > ConfigMate > Compare Configurations

3. **Choose Configurations**:
   - **Source Options**:
     - Running configuration
     - Startup configuration
     - Generated configurations
     - Custom text input
     - Saved configuration files

4. **Comparison Settings**:
   - **Algorithm**: Unified, context, or side-by-side diff
   - **Context Lines**: Number of lines around differences
   - **Ignore Options**: Whitespace, comments, specific patterns

### Understanding Comparison Results

#### Visual Indicators

- **Green**: Lines added in second configuration
- **Red**: Lines removed from first configuration
- **Yellow**: Lines modified between configurations
- **White**: Unchanged lines (context)

#### Navigation Features

- **Jump to Differences**: Navigate between changes
- **Expand/Collapse**: Show/hide context sections
- **Search**: Find specific text in configurations
- **Line Numbers**: Reference original line numbers

#### Filtering Options

- **Show Only Differences**: Hide unchanged sections
- **Filter by Pattern**: Show only changes matching pattern
- **Ignore Patterns**: Exclude specific types of changes

### Comparison Actions

1. **Export Comparison**:
   - Save as HTML report with highlighting
   - Export as PDF for documentation
   - Save as text file for scripts

2. **Apply Changes**:
   - Select specific differences to apply
   - Generate configuration patches
   - Queue changes for deployment

3. **Create Template**:
   - Convert common sections to template
   - Extract variables from differences
   - Save as new template

## Variable System

### Variable Types

ConfigMate supports various variable types:

- **String**: Text values (hostnames, descriptions)
- **IP Address**: IPv4/IPv6 addresses with validation
- **Integer**: Numeric values (VLAN IDs, port numbers)
- **Boolean**: True/false values for conditional logic
- **List**: Multiple values (interface lists, VLAN ranges)
- **Object**: Complex structured data

### Variable Sources

Variables can be populated from:

1. **Device Properties**: Automatic mapping from device attributes
2. **User Input**: Manual entry during generation
3. **Calculated Values**: Derived from other variables or device state
4. **External Sources**: APIs, databases, CSV files
5. **Default Values**: Fallback values defined in template

### Variable Detection

ConfigMate automatically detects variables when creating templates:

#### Automatic Detection Rules

- **IP Addresses**: Identifies and suggests IP variables
- **Hostnames**: Detects hostname patterns
- **Interface Names**: Recognizes interface naming patterns
- **Numeric Values**: Identifies potential numeric variables
- **Repeated Patterns**: Finds recurring text patterns

#### Manual Variable Definition

1. **Select Text**: Highlight text in template editor
2. **Create Variable**: Right-click > "Create Variable"
3. **Configure Variable**:
   - Name and description
   - Data type and validation
   - Default value
   - Required/optional status

### Advanced Variable Features

#### Variable Relationships

- **Dependencies**: Variables that depend on other variables
- **Calculated Fields**: Variables computed from formulas
- **Conditional Variables**: Variables that appear based on conditions

#### Variable Validation

- **Format Validation**: Ensure correct format (IP, hostname, etc.)
- **Range Validation**: Check numeric ranges
- **Pattern Validation**: Regular expression matching
- **Custom Validation**: Python validation functions

## Batch Operations

### Planning Batch Operations

1. **Define Scope**:
   - Select target devices
   - Choose templates to apply
   - Plan variable assignments

2. **Pre-flight Checks**:
   - Verify device connectivity
   - Check template compatibility
   - Validate variable values

3. **Safety Measures**:
   - Enable backup creation
   - Set confirmation requirements
   - Configure rollback procedures

### Execution Options

#### Parallel Processing

- **Enable**: For faster processing of large device sets
- **Thread Limit**: Control resource usage
- **Error Handling**: Continue or stop on errors

#### Sequential Processing

- **Ordered Execution**: Process devices in specific order
- **Dependency Management**: Handle device dependencies
- **Progressive Validation**: Validate each step before continuing

### Monitoring and Control

1. **Progress Tracking**:
   - Real-time progress updates
   - Individual device status
   - Estimated completion time

2. **Error Management**:
   - Detailed error logging
   - Retry failed operations
   - Skip problematic devices

3. **Intervention Options**:
   - Pause/resume operations
   - Cancel remaining operations
   - Modify settings mid-process

## Export Capabilities

### Export Formats

#### Text Export
- Plain text configurations
- Command-line friendly format
- Script integration support

#### HTML Export
- Formatted output with syntax highlighting
- Embedded CSS styling
- Print-friendly layout

#### PDF Export
- Professional document format
- Headers and footers with metadata
- Table of contents for large exports

#### JSON Export
- Structured data format
- API integration friendly
- Programmatic processing support

#### YAML Export
- Human-readable structured format
- Configuration management tools
- Infrastructure as Code support

### Export Options

1. **Content Selection**:
   - Full configurations
   - Differences only
   - Specific sections
   - Template definitions

2. **Metadata Inclusion**:
   - Generation timestamps
   - Device information
   - Template details
   - Variable values used

3. **Formatting Options**:
   - Syntax highlighting
   - Line numbers
   - Comments and annotations
   - Custom headers/footers

### Automated Export

- **Scheduled Exports**: Regular automated exports
- **Event-Driven**: Export on configuration changes
- **Integration**: Connect to external systems
- **Notifications**: Email or webhook notifications

## Settings Configuration

### Settings Categories

#### Core Settings
- **Default Platform**: Primary device platform
- **Auto-Detect Variables**: Automatic variable detection
- **Template Format**: Default template format

#### UI Settings
- **Syntax Highlighting**: Code highlighting in editors
- **Max Preview Lines**: Limit for configuration previews
- **Comparison Context**: Lines of context in diffs
- **Diff Algorithm**: Comparison algorithm selection

#### Safety Settings
- **Confirm Apply**: Require confirmation for deployments
- **Backup Before Apply**: Create backups automatically
- **Validate Syntax**: Syntax validation before apply
- **Apply Timeout**: Timeout for configuration operations

#### Export Settings
- **Export Format**: Default export format
- **Include Metadata**: Add metadata to exports
- **Export Directory**: Default export location

#### Advanced Settings
- **Variable Detection Sensitivity**: Detection accuracy level
- **Template Cache Size**: Number of cached templates
- **Parallel Generation**: Enable parallel processing
- **Max Parallel Jobs**: Concurrent job limit

#### Debug Settings
- **Debug Mode**: Enable detailed logging
- **Log Level**: Logging verbosity level

### Configuring Settings

1. **Access Settings**:
   - Tools > Plugin Manager > ConfigMate > Settings
   - Edit > Preferences > Plugins > ConfigMate

2. **Modify Settings**:
   - Browse categories
   - Adjust values using appropriate controls
   - Use tooltips for setting descriptions

3. **Apply Changes**:
   - Changes take effect immediately
   - Some settings may require restart
   - Settings are automatically saved

## Integration Features

### Command Manager Integration

ConfigMate works closely with the Command Manager plugin:

- **Configuration Retrieval**: Automatically fetch device configs
- **Command Execution**: Deploy generated configurations
- **Credential Management**: Use existing device credentials
- **Output Caching**: Leverage cached command results

### Device Integration

- **Property Mapping**: Use device properties as template variables
- **Group Variables**: Apply group-wide settings
- **Status Monitoring**: Track device status during operations
- **Capability Detection**: Adapt to device capabilities

### Workflow Integration

- **Event Handling**: Respond to device and configuration events
- **State Management**: Track configuration states
- **Change Detection**: Monitor configuration changes
- **Audit Trail**: Maintain operation history

## Best Practices

### Template Design

1. **Modularity**: Create focused, single-purpose templates
2. **Documentation**: Include clear descriptions and comments
3. **Variable Naming**: Use descriptive, consistent variable names
4. **Validation**: Include appropriate variable validation
5. **Testing**: Test templates with various device types

### Variable Management

1. **Standardization**: Use consistent variable naming conventions
2. **Documentation**: Document variable purposes and formats
3. **Defaults**: Provide sensible default values
4. **Validation**: Implement appropriate validation rules
5. **Organization**: Group related variables logically

### Configuration Management

1. **Version Control**: Track template and configuration versions
2. **Testing**: Test configurations in lab environment first
3. **Gradual Deployment**: Roll out changes incrementally
4. **Monitoring**: Monitor devices after configuration changes
5. **Documentation**: Document all configuration changes

### Security Considerations

1. **Access Control**: Limit template modification access
2. **Credential Security**: Protect device credentials
3. **Audit Logging**: Maintain detailed operation logs
4. **Change Approval**: Implement change approval processes
5. **Backup Strategy**: Maintain configuration backups

## Troubleshooting

### Common Issues

#### Template Problems

**Issue**: Template fails to load
- Check template syntax and format
- Verify file permissions
- Review error logs for details

**Issue**: Variables not substituting correctly
- Verify variable names match exactly
- Check variable data types
- Ensure device properties are available

**Issue**: Generated configuration is incorrect
- Review template logic
- Check variable values
- Test with simple template first

#### Generation Problems

**Issue**: Configuration generation fails
- Verify device connectivity
- Check template compatibility
- Review variable requirements

**Issue**: Slow generation performance
- Enable parallel processing
- Increase cache size
- Optimize template complexity

**Issue**: Generation produces errors
- Check device platform compatibility
- Verify template syntax
- Review variable validation rules

#### Comparison Issues

**Issue**: Comparison shows unexpected differences
- Check comparison algorithm settings
- Verify input configurations
- Review ignore patterns

**Issue**: Comparison is too slow
- Reduce context lines
- Use simpler diff algorithm
- Compare smaller sections

### Debug Mode

Enable debug mode for detailed troubleshooting:

1. **Enable Debug Mode**:
   - Go to Settings > Debug
   - Enable "Debug Mode"
   - Set log level to "DEBUG"

2. **Review Logs**:
   - Check workspace/configmate/logs/
   - Look for error messages
   - Review operation traces

3. **Report Issues**:
   - Include log files
   - Describe reproduction steps
   - Provide sample templates/configurations

### Getting Help

1. **Documentation**: Check online documentation
2. **Community**: Post in forums or discussions
3. **Support**: Contact support team
4. **GitHub**: Report bugs or request features

---

This usage guide covers the comprehensive functionality of the ConfigMate plugin. For additional information, refer to the API documentation and plugin settings help text. 