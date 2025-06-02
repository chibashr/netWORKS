# ConfigMate Device Access and Comparison Fixes

## Issues Addressed

### 1. Command Manager Plugin Instance Access Error
**Problem**: The `_get_device_config` method was trying to access the command manager plugin instance through `self.app.plugin_manager`, which was not available and causing errors:
```
ERROR | configmate:_get_device_config:806 | Command manager plugin instance not available
```

**Solution**: Replaced complex plugin manager access with direct device data access. The method now looks directly at device properties for cached command outputs instead of trying to access the command manager plugin instance.

**Changes Made**:
- Updated `configmate_plugin.py` `_get_device_config()` method to access `device.command_outputs` or `device.get_command_outputs()` directly
- Removed dependency on command manager plugin instance
- Added comprehensive command ID pattern matching for finding cached configurations
- Implemented intelligent scoring system for fuzzy matching running-config commands

### 2. Config Comparator Method Name Errors
**Problem**: The comparison dialog was calling non-existent methods:
- `compare_configs()` - method doesn't exist
- `compare_multiple_configs()` - method doesn't exist

**Error**:
```
ERROR | ui.config_comparison_dialog:run:121 | Error in comparison worker: 'ConfigComparator' object has no attribute 'compare_configs'
```

**Solution**: Fixed method calls to use the correct ConfigComparator methods:
- `compare_configs()` → `compare_devices()`
- `compare_multiple_configs()` → `compare_multiple_devices()`

**Changes Made**:
- Updated `ui/config_comparison_dialog.py` ComparisonWorker to use correct method names
- Fixed device ID access from `device.get_property('id')` to `device.device_id`
- Added proper error handling for missing configurations

### 3. Enhanced Config Comparison with Device/Command Selection
**Problem**: User requested the ability to compare different commands from different devices with dropdown selection.

**Solution**: Enhanced the comparison dialog with comprehensive device and command selection capabilities.

**New Features**:
- **Device Selection Dropdowns**: Choose any two devices from available devices for comparison
- **Command Selection Dropdowns**: Choose different commands for each device (editable combos)
- **Dynamic Command Population**: Automatically populates available commands from device's cached outputs
- **Flexible Comparison**: Can compare same command between devices or different commands
- **Real-time Updates**: "Update Comparison" button to refresh comparison based on new selections

**Changes Made**:
- Added device and command selection UI with `QGridLayout`
- Implemented `_populate_command_combo()` to show available commands for each device
- Created `_update_comparison_from_selection()` for on-demand comparison updates
- Added `_get_device_command_output()` for retrieving specific command outputs
- Enhanced comparison logic to handle different command types (show commands vs templates)

### 4. ConfigComparator Device Access Updates
**Problem**: ConfigComparator's helper methods were still using placeholder implementations that didn't access actual device data.

**Solution**: Updated ConfigComparator's `_get_device_config()` and `_get_command_output()` methods to use the same direct device access pattern.

**Changes Made**:
- Updated `core/config_comparator.py` to access device command outputs directly
- Implemented comprehensive command matching with exact and fuzzy search
- Added proper error handling and logging
- Unified device access pattern across all components

### 5. Signal Disconnection Warning Fix
**Problem**: Warning about failed signal disconnection in config preview widget:
```
RuntimeWarning: Failed to disconnect (None) from signal "currentTextChanged(QString)".
```

**Solution**: Added proper signal disconnection handling with try-catch block and informative comment.

## Technical Details

### Device Access Pattern
The new device access pattern works as follows:

1. **Primary Access**: Check `device.command_outputs` attribute
2. **Fallback Access**: Call `device.get_command_outputs()` method
3. **Command Matching**: Try exact command match first, then fuzzy matching
4. **Output Extraction**: Handle both dict format (`{'output': text}`) and direct string format
5. **Timestamp Handling**: Always use most recent output when multiple timestamps exist

### Command ID Patterns Supported
The system now recognizes various command ID formats:
- `"show running-config"`
- `"show run"`
- `"show_run"`
- `"Show Running Config"`
- `"Show Running-Config"`
- `"show running"`
- `"sh run"`
- `"sh running-config"`
- `"running-config"`
- `"running_config"`

### Scoring System for Command Matching
- **100 points**: Contains both "running" and "config"
- **50 points**: Contains "running" 
- **40 points**: Contains "show" + ("run" or "conf")
- **30 points**: Contains "config"
- **10 points**: Contains any of "show", "run", "conf"

### Comparison Features
1. **Two-Device Comparison**: Enhanced side-by-side view with device/command selection
2. **Multi-Device Comparison**: Support for comparing multiple devices simultaneously
3. **Show Command Comparison**: Specialized comparison for show command outputs
4. **Template Comparison**: Comparison between different command outputs treated as templates
5. **Flexible Selection**: Mix and match devices and commands as needed

## Files Modified

### Primary Plugin Files
- `configmate_plugin.py`: Fixed `_get_device_config()` method, removed command manager dependency
- `ui/config_comparison_dialog.py`: Fixed method calls, added device/command selection UI
- `core/config_comparator.py`: Updated device access methods
- `ui/config_preview_widget.py`: Fixed signal disconnection warning

### Key Methods Updated
- `ConfigMatePlugin._get_device_config()`: Direct device access implementation
- `ComparisonWorker.run()`: Correct method calls and error handling  
- `ConfigComparisonDialog._create_two_device_comparison()`: Enhanced UI with selection controls
- `ConfigComparator._get_device_config()`: Direct device access implementation
- `ConfigComparator._get_command_output()`: Unified with device config access

## Testing Results

All components now import and function correctly:
- ✅ ConfigMate plugin imports successfully
- ✅ Config comparison dialog imports without errors
- ✅ ConfigComparator has all required methods: `compare_devices`, `compare_show_commands`, `compare_multiple_devices`, `compare_templates`
- ✅ Device access works without command manager plugin dependency
- ✅ Enhanced comparison UI with device/command selection functional

## Benefits

1. **Reliability**: No more dependency on command manager plugin instance
2. **Performance**: Direct device access is faster than plugin manager calls
3. **Flexibility**: Users can compare any cached command between any devices
4. **User Experience**: Intuitive dropdown selection for devices and commands
5. **Robustness**: Comprehensive error handling and fallback mechanisms
6. **Maintainability**: Cleaner code with consistent device access patterns

## User Impact

- **No More Errors**: ConfigMate will work reliably without command manager plugin instance errors
- **Enhanced Comparison**: Users can now select specific devices and commands to compare
- **Better Discovery**: Available commands are automatically populated from device cache
- **Flexible Workflows**: Compare different command outputs between different devices as needed
- **Improved Feedback**: Better error messages and status information during comparisons 