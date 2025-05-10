# Sample Plugin API Documentation

## Overview

The Sample Plugin demonstrates how to extend NetWORKS functionality while providing comprehensive testing capabilities for the application. It serves as both a reference implementation for plugin developers and a testing utility for core application features.

Key features include:
- UI extensions (toolbar actions, menu items, device panels, dock widgets)
- Device property extensions
- Device table column extensions
- Comprehensive signal monitoring and testing
- Core application feature testing dashboard
- Plugin lifecycle management examples

## Public API

### Methods

```python
def test_core_features(self):
    """
    Run a comprehensive test of core application features
    
    Returns:
        dict: Dictionary containing test results with success/failure status
    """

def test_signal(self, signal_name):
    """
    Test a specific application signal
    
    Args:
        signal_name (str): Name of the signal to test
        
    Returns:
        bool: True if signal test was successful, False otherwise
    """
    
def monitor_signal(self, signal_name, enable=True):
    """
    Enable or disable monitoring for a specific signal
    
    Args:
        signal_name (str): Name of the signal to monitor
        enable (bool): True to enable monitoring, False to disable
        
    Returns:
        bool: True if the operation was successful
    """
    
def update_device_details(self, device):
    """
    Update device details in the panel
    
    Args:
        device: Device to update details for
    """
    
def log_message(self, message):
    """
    Add a message to the plugin's log widget
    
    Args:
        message (str): Message to log
    """
```

### Device Dialog Usage

The plugin demonstrates how to use the device dialog methods provided by the PluginInterface:

```python
def show_properties_dialog(self, device):
    """
    Show properties dialog for an existing device
    
    Args:
        device: Device to edit
        
    Returns:
        Device or None: Updated device if successful, None if cancelled
    """
    updated_device = self.show_device_properties_dialog(device)
    return updated_device
    
def create_new_device(self):
    """
    Create a new device using the add device dialog
    
    Returns:
        Device or None: New device if created, None if cancelled
    """
    new_device = self.add_device_dialog()
    return new_device
```

### Device Properties

The plugin adds and manages the following device properties:

| Property | Type   | Description                           |
|----------|--------|---------------------------------------|
| sample   | string | A sample property for demonstration   |
| test_result | string | Last test result for this device   |
| test_timestamp | string | Timestamp of the last test      |

Example usage:
```python
# Set sample property
device.set_property("sample", "My Sample Value")

# Get sample property
value = device.get_property("sample", "Default")

# Get test results
test_result = device.get_property("test_result", "Not tested")
```

### Testing API

The plugin provides a comprehensive testing API for the application:

```python
# Get the sample plugin instance
sample_plugin = plugin_manager.get_plugin("sample").instance

# Run comprehensive tests
test_results = sample_plugin.test_core_features()
for feature, result in test_results.items():
    print(f"{feature}: {'SUCCESS' if result['success'] else 'FAILED'}")
    
# Test a specific signal
signal_test_result = sample_plugin.test_signal("device_added")
print(f"Signal test result: {signal_test_result}")

# Enable signal monitoring
sample_plugin.monitor_signal("plugin_loaded", True)
```

## Signals

### Emitted Signals

The plugin emits the following signals:

| Signal | Parameters | Description |
|--------|------------|-------------|
| test_started | (str) | Emitted when a test begins, with test name |
| test_completed | (str, bool) | Emitted when a test completes, with test name and result |
| test_all_completed | (dict) | Emitted with complete test results dictionary |

### Monitored Signals

The plugin can monitor and log the following application signals:

- `device_manager.device_added`
- `device_manager.device_removed`
- `device_manager.device_changed`
- `device_manager.selection_changed`
- `device_manager.group_added`
- `device_manager.group_removed`
- `plugin_manager.plugin_loaded`
- `plugin_manager.plugin_unloaded`
- `plugin_manager.plugin_enabled`
- `plugin_manager.plugin_disabled`

## Plugin Settings

The plugin demonstrates how to implement configurable settings:

| Setting ID | Type | Description | Default |
|------------|------|-------------|---------|
| log_level | choice | The log level for plugin messages | INFO |
| auto_sample | bool | Automatically add sample property to devices | true |
| default_value | string | Default value for the sample property | Sample Value |
| testing_mode | choice | Testing mode (manual, automatic, or disabled) | manual |
| test_signal_timeout | int | Timeout in seconds for signal tests | 10 |
| signal_monitoring | bool | Enable signal monitoring by default | false |

## UI Components

The plugin provides the following UI components:

- Toolbar actions:
  - "Sample Action": Add sample property to selected devices
  - "Test Application": Launch application testing dashboard

- Menu items (under "Sample" menu):
  - "Sample Menu Action"
  - "Add New Device"
  - "Edit Selected Device"
  - "Run Tests"
  - "Signal Monitor"

- Device panels:
  - "Sample" tab: Shows device details and test results

- Dock widgets:
  - "Sample Plugin Log": Shows plugin operation log
  - "Test Dashboard": Shows test results and monitoring data

## Integration Examples

Other plugins can integrate with the Sample Plugin as follows:

```python
def initialize(self, app, plugin_info):
    # Get the sample plugin instance
    sample_plugin_info = app.plugin_manager.get_plugin("sample")
    
    if sample_plugin_info and sample_plugin_info.loaded:
        sample_plugin = sample_plugin_info.instance
        
        # Connect to test signals
        sample_plugin.test_completed.connect(self.on_test_completed)
        
        # Add to log
        sample_plugin.log_message("Integration from my plugin")
        
        # Use the testing API
        test_results = sample_plugin.test_core_features()
        
    return True
    
def on_test_completed(self, test_name, success):
    logger.info(f"Test {test_name} completed: {'SUCCESS' if success else 'FAILED'}")
```

## Changelog

### Version 1.0.0 (2025-05-19)
- Added comprehensive application testing capabilities
- Updated to comply with new documentation standards
- Enhanced UI with testing dashboard
- Added signal testing and monitoring functionality

### Version 0.1.0 (2023-11-14)
- Initial sample plugin
- Demonstrates basic plugin functionality
- Shows how to register with the application 