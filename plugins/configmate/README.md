# ConfigMate Plugin

**Configuration and template management tool for network engineers**

ConfigMate is a comprehensive plugin for the NetWORKS platform that provides powerful configuration and template management capabilities specifically designed for network engineers and administrators.

## 🚀 Features

### Core Functionality
- **Template Management**: Create, edit, and organize configuration templates with syntax highlighting
- **Smart Generation**: Generate device configurations using templates with automatic variable substitution
- **Intelligent Detection**: Automatically detect variables from existing device configurations
- **Configuration Comparison**: Side-by-side comparison of configurations with detailed diff highlighting
- **Batch Operations**: Apply templates and generate configurations for multiple devices simultaneously
- **Export Capabilities**: Export templates and configurations in various formats

### Platform Support
- **Cisco IOS/IOS-XE**: Full syntax highlighting and validation
- **Cisco NX-OS**: Native command set support
- **Juniper JunOS**: Configuration structure awareness
- **Generic**: Universal text-based configuration support

### Template Formats
- **Text**: Simple text templates with basic variable substitution
- **Jinja2**: Advanced templating with conditional logic and loops
- **Simple**: Basic variable replacement for quick templates
- **Python**: Execute Python code for complex generation logic

### Export Formats
- **Text**: Plain text output
- **HTML**: Formatted HTML with syntax highlighting
- **PDF**: Professional PDF documents
- **JSON**: Structured JSON data
- **YAML**: YAML formatted output

## 📋 Requirements

- **NetWORKS Platform**: Version 0.8.16 or higher
- **Python**: 3.8 or higher
- **Qt**: 6.5 or higher
- **Dependencies**: 
  - Jinja2 >= 3.0
  - difflib (standard library)

## 🔧 Installation

1. **Automatic Installation** (Recommended):
   - Place the `configmate` folder in your NetWORKS `plugins/` directory
   - Restart the NetWORKS application
   - The plugin will be automatically detected and loaded

2. **Manual Installation**:
   ```bash
   cd /path/to/networks/plugins/
   git clone https://github.com/networks/configmate.git
   ```

3. **Verify Installation**:
   - Open NetWORKS
   - Go to **Tools > Plugin Manager**
   - Confirm ConfigMate is listed and enabled

## 🎯 Quick Start

### Creating Your First Template

1. **From Toolbar**: Click the **Template Manager** button
2. **From Menu**: Go to **Tools > ConfigMate > Template Manager**
3. **From Context Menu**: Right-click a device and select **Create Template from Device**

### Generating Configurations

1. Select one or more devices in the device table
2. Click **Quick Generate** from the toolbar, or
3. Right-click selected devices and choose **Generate Configuration**

### Comparing Configurations

1. Select two or more devices
2. Click **Compare Configs** from the toolbar
3. Choose configurations to compare in the dialog

## ⚙️ Configuration

### Plugin Settings

ConfigMate provides extensive configuration options organized in categories:

#### Core Settings
- **Default Platform**: Choose default device platform for new templates
- **Auto-Detect Variables**: Automatically detect variables when creating templates
- **Template Format**: Default format for saved templates

#### UI Settings
- **Syntax Highlighting**: Enable/disable syntax highlighting in editor
- **Max Preview Lines**: Limit lines shown in configuration preview
- **Comparison Context Lines**: Context lines around differences
- **Diff Algorithm**: Algorithm for configuration comparison

#### Safety Settings
- **Confirm Apply**: Always confirm before applying configurations
- **Backup Before Apply**: Create backup before applying changes
- **Validate Syntax**: Validate configuration syntax before applying
- **Apply Timeout**: Timeout for configuration apply operations

#### Export Settings
- **Export Format**: Default format for exported configurations
- **Include Metadata**: Include timestamps and device info in exports
- **Export Directory**: Default directory for exported files

#### Advanced Settings
- **Variable Detection Sensitivity**: Sensitivity for automatic variable detection
- **Template Cache Size**: Number of templates to cache in memory
- **Parallel Generation**: Enable parallel configuration generation
- **Max Parallel Jobs**: Maximum number of parallel jobs

#### Debug Settings
- **Debug Mode**: Enable detailed logging for troubleshooting
- **Log Level**: Set logging verbosity level

### Accessing Settings

1. **Plugin Manager**: Go to **Tools > Plugin Manager > ConfigMate > Settings**
2. **Settings Dialog**: Go to **Edit > Preferences > Plugins > ConfigMate**

## 🔍 Usage Guide

### Template Creation

#### From Device Configuration
1. Right-click a device with configuration data
2. Select **Create Template from Device**
3. Choose configuration source (running config, startup config, etc.)
4. Review detected variables and adjust as needed
5. Name and save the template

#### Manual Creation
1. Open **Template Manager**
2. Click **New Template**
3. Enter template content with variables (e.g., `{{hostname}}`, `{{ip_address}}`)
4. Set platform and format options
5. Save the template

### Variable System

ConfigMate supports multiple variable formats:

- **Simple**: `{hostname}`, `{ip_address}`
- **Jinja2**: `{{hostname}}`, `{{ip_address}}`, `{% if condition %}`
- **Python**: Custom Python expressions and functions

### Configuration Generation

#### Single Device
1. Select a device
2. Choose **Generate Configuration** from context menu
3. Select template to use
4. Review generated configuration
5. Apply or export as needed

#### Batch Generation
1. Select multiple devices
2. Use **Quick Generate** for fast batch processing
3. Review results for each device
4. Apply to devices or export for later use

### Configuration Comparison

1. Select devices to compare
2. Open **Compare Configurations**
3. Choose configurations for each device
4. Review side-by-side diff with highlighting
5. Export comparison results if needed

## 🔌 Integration

### Command Manager Integration

ConfigMate integrates seamlessly with the Command Manager plugin:

- **Configuration Retrieval**: Automatically fetch device configurations
- **Command Execution**: Execute configuration commands on devices
- **Credential Management**: Use existing device credentials
- **Output Caching**: Leverage cached command outputs

### Device Integration

- **Device Properties**: Access all device properties as template variables
- **Group Variables**: Use device group properties in templates
- **Dynamic Variables**: Generate variables based on device state

### GUI Integration

- **Toolbar Actions**: Quick access to common operations
- **Context Menus**: Right-click actions for devices
- **Right Panel**: Live configuration preview
- **Status Updates**: Real-time operation status

## 📚 API Reference

### Plugin Interface

ConfigMate implements the complete NetWORKS plugin interface:

```python
# Core methods
def initialize(app, plugin_info)
def cleanup()
def get_settings()
def update_setting(setting_id, value)

# UI integration
def get_toolbar_actions()
def get_menu_actions() 
def get_device_panels()
def get_context_menu_actions()
def get_settings_pages()

# Information methods
def get_info()
def get_description()
def get_capabilities()
def get_documentation_url()
def get_support_info()

# Event handlers
def on_device_added(device)
def on_device_removed(device)
def on_device_changed(device)
def on_selection_changed(devices)
```

### Core Components

#### Template Manager
```python
template_manager.create_template(name, content, platform, description, variables)
template_manager.get_template(name)
template_manager.get_template_list()
template_manager.update_template(name, **kwargs)
template_manager.delete_template(name)
```

#### Config Generator
```python
config_generator.generate_config(device, template_name, variables)
config_generator.get_template_variables_for_device(device, template_name)
```

#### Variable Detector
```python
variable_detector.detect_variables_single_config(config_text, device_name)
variable_detector.detect_variables_multi_config(config_dict)
variable_detector.create_template_from_config(config_text, device, format)
```

#### Config Comparator
```python
config_comparator.compare_configurations(config1, config2, context_lines)
```

## 🛠️ Troubleshooting

### Common Issues

#### Templates Not Loading
- **Cause**: Permission issues or incorrect template format
- **Solution**: Check templates directory permissions and validate template syntax

#### Configuration Generation Fails
- **Cause**: Missing variables or device connectivity issues
- **Solution**: Verify device connectivity and ensure all template variables are defined

#### Syntax Highlighting Not Working
- **Cause**: Feature disabled or platform not supported
- **Solution**: Enable syntax highlighting in plugin settings and restart application

#### Export Failures
- **Cause**: Insufficient permissions or invalid export path
- **Solution**: Check write permissions and verify export directory exists

### Debug Mode

Enable debug mode for detailed troubleshooting:

1. Go to **Plugin Settings > Debug**
2. Enable **Debug Mode**
3. Set **Log Level** to **DEBUG**
4. Restart NetWORKS
5. Check logs in workspace directory

### Log Locations

- **Windows**: `%USERPROFILE%\Documents\NetWORKS\workspace\configmate\logs\`
- **macOS**: `~/Documents/NetWORKS/workspace/configmate/logs/`
- **Linux**: `~/Documents/NetWORKS/workspace/configmate/logs/`

### Performance Optimization

For large environments:

- Increase **Template Cache Size** for frequently used templates
- Enable **Parallel Generation** for batch operations
- Adjust **Max Parallel Jobs** based on system capabilities
- Use **Variable Detection Sensitivity: Low** for faster processing

## 🤝 Support

### Documentation
- **Online Docs**: https://docs.networks.com/plugins/configmate
- **API Reference**: https://docs.networks.com/plugins/configmate/api
- **Examples**: https://docs.networks.com/plugins/configmate/examples

### Community
- **GitHub**: https://github.com/networks/configmate
- **Issues**: https://github.com/networks/configmate/issues
- **Discussions**: https://github.com/networks/configmate/discussions
- **Forum**: https://community.networks.com/plugins/configmate

### Professional Support
- **Email**: support@networks.com
- **Enterprise**: enterprise@networks.com
- **Training**: training@networks.com

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔄 Changelog

### Version 1.0.0 (2025-05-30)
- Initial release of ConfigMate plugin
- Template creation and management with syntax highlighting
- Intelligent template generation from device configurations
- Configuration generation and preview functionality
- Side-by-side configuration comparison with diff highlighting
- Integration with command_manager plugin for device operations
- GUI integration with toolbar, context menus, and right panel widget
- Variable detection and substitution system
- Batch operations support for multiple devices
- Export capabilities for templates and comparison results

## 🙏 Acknowledgments

- NetWORKS development team
- Jinja2 template engine
- Qt framework
- Python community
- Network engineering community for feedback and testing

---

**Made with ❤️ by the NetWORKS Team** 