# ConfigMate Multi-Device Selection and Running Config Detection Fix

## Issue Description

The ConfigMate plugin was not properly recognizing when multiple devices were selected with running configurations. This manifested as:

1. **Signal Reception Issues**: The `on_selection_changed` signal handler wasn't always receiving updated device selections
2. **Timing Problems**: Device selection changes occurred faster than ConfigMate could process them
3. **Incomplete Running Config Detection**: The plugin didn't check which selected devices actually had running configurations available

## Root Cause Analysis

From the logs, we identified several issues:

1. **Signal Disconnect/Timing**: The ConfigMate plugin's signal handling was not consistently receiving selection change events
2. **Asynchronous Updates**: Device selection updates in the UI were happening asynchronously, but ConfigMate was checking selection at the wrong time
3. **Missing Config Validation**: When multiple devices were selected, the plugin didn't verify which ones actually had running configurations

## Implemented Solutions

### 1. Enhanced Device Selection Synchronization

**Added `_force_selection_refresh()` method:**
```python
def _force_selection_refresh(self):
    """Force a refresh of the device selection state"""
    # Tries multiple methods to get current selection:
    # - device_manager.get_selected_devices()
    # - main_window.get_selected_devices()  
    # - device_table.get_selected_devices()
    
    # Logs detailed information about selection changes
    # Automatically checks for running configs on newly selected devices
```

**Updated key action handlers:**
- `open_template_manager()` - Now calls `_force_selection_refresh()` before opening
- `quick_generate_config()` - Ensures latest selection before generating configs
- `compare_configurations()` - Refreshes selection and validates running configs

### 2. Running Configuration Detection

**Added `_check_devices_for_running_configs()` method:**
```python
def _check_devices_for_running_configs(self, devices):
    """Check which devices have running configurations available"""
    # Loops through each device
    # Calls _get_device_config() to verify config availability
    # Returns only devices with substantial configs (>100 chars)
    # Logs detailed information about each device's config status
```

**Enhanced `on_selection_changed()` signal handler:**
- Now logs detailed device selection information
- Automatically checks for running configs when multiple devices are selected
- Provides informative logging about config availability

### 3. Template Editor Improvements

**Enhanced `create_from_config()` method:**
- Proactively calls `_update_selection_if_needed()` to get latest selection
- Validates running config availability for each selected device
- Only uses multi-device detection when ≥2 devices have actual running configs
- Falls back to single-device mode when insufficient configs are available

**Improved config retrieval:**
- Uses `_get_device_config_for_template()` for more comprehensive config detection
- Better error handling and logging for config retrieval failures

### 4. Comparison Dialog Enhancements

**Updated `compare_configurations()` method:**
- Validates that selected devices actually have running configurations
- Shows detailed error messages when insufficient configs are available
- Lists which devices have configs and which don't
- Only opens comparison dialog with devices that have actual configurations

## Logging Improvements

Added comprehensive logging at multiple levels:

1. **Selection Changes**: Detailed logs when device selection changes
2. **Config Detection**: Information about which devices have running configs
3. **Method Calls**: Debug information about which selection methods work
4. **Error Handling**: Better error messages and troubleshooting information

## Expected Behavior After Fix

### Multiple Device Selection
- ConfigMate will immediately recognize when multiple devices are selected
- It will check which devices have running configurations available
- Only devices with substantial running configs will be used for multi-device operations

### Template Creation
- When creating templates from device configs, the plugin will:
  1. Refresh device selection to ensure it's current
  2. Check each selected device for running config availability
  3. Use multi-device detection only when ≥2 devices have configs
  4. Provide clear feedback about which devices are being used

### Configuration Comparison
- The comparison feature will:
  1. Validate that selected devices have running configurations
  2. Show informative error messages when configs are missing
  3. Only compare devices that actually have configurations available

### Logging Output
You should now see logs like:
```
ConfigMate: Device selection changed - 2 devices selected
ConfigMate: Selected devices: Device1, Device2
ConfigMate: 2 of 2 selected devices have running configurations
ConfigMate: Using multi-device variable detection with 2 devices
```

## Testing the Fix

1. **Select Multiple Devices**: Choose 2+ devices in the device table
2. **Check Logs**: Look for "ConfigMate: Device selection changed" messages
3. **Create Template**: Right-click → "Create Template from Config" should detect multiple devices
4. **Compare Configs**: Tools → Compare Configurations should validate running configs

## Backward Compatibility

All changes are backward compatible:
- Single device operations work exactly as before
- Existing templates and configurations are unaffected
- No changes to the plugin's public API or settings 