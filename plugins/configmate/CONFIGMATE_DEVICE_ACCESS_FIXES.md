# ConfigMate Device Access and Comparison Fixes

## Issues Addressed

### 1. Device ID Attribute Access Error  
**Problem**: The code was trying to access `device.device_id` which doesn't exist on Device objects:
```
ERROR | configmate:_get_device_config:884 | Failed to get device config: 'Device' object has no attribute 'device_id'
```

**Solution**: Fixed all references to use the correct `device.id` attribute instead of `device.device_id`.

**Changes Made**:
- Updated `configmate_plugin.py` to use `device.id`
- Updated `ui/config_comparison_dialog.py` to use `device.id`  
- Updated `ui/config_preview_widget.py` to use `device.id`
- Updated `core/config_comparator.py` to use `device.id`

### 2. Command Manager Plugin Instance Access Error
**Problem**: The `_get_device_config` method was trying to access the command manager plugin instance through `self.app.plugin_manager`, which was not available and causing errors:
```
ERROR | configmate:_get_device_config:806 | Command manager plugin instance not available
```

**Solution**: Replaced complex plugin manager access with direct device data access. The method now looks directly at device properties for cached command outputs instead of trying to access the command manager plugin instance.

**Changes Made**:
- Updated `configmate_plugin.py` `_get_device_config()` method to access `device.command_outputs` or `device.get_command_outputs()` directly
- Added fallback to load command outputs from file system when not available in memory
- Enhanced command ID pattern matching for better compatibility

### 3. Dropdown Shows Default Commands Instead of Actual Available Commands
**Problem**: The comparison dialog was showing default commands like "show startup-config", "show interfaces", etc. instead of only showing commands that actually exist in the device's cached outputs.

**Solution**: 
- **Enhanced file-based command loading**: ConfigMate now loads command outputs directly from the workspace file system (`workspaces/langlade_wi/devices/{device_id}/commands/command_outputs.json`)
- **Intelligent command mapping**: Maps descriptive command IDs (e.g., `"Cisco_IOS_XE_16.x_Show_Running_Config"`) to user-friendly names (e.g., `"show running-config"`)
- **Only shows actual commands**: Dropdowns now only display commands that actually exist in the device's cached outputs

**Changes Made**:
- Added `_load_device_command_outputs_from_file()` method to load commands from workspace files
- Added `_get_device_available_commands()` method to get actual available commands for dropdown population
- Enhanced `_populate_command_combo()` to use actual device commands instead of defaults
- Added comprehensive command ID mapping for Cisco IOS/IOS-XE commands
- Improved workspace path detection with fallback logic

### 4. Workspace Path Detection Issues
**Problem**: ConfigMate couldn't find the langlade_wi workspace when device manager wasn't available (e.g., during testing or standalone operation).

**Solution**: Added intelligent workspace path detection that tries multiple common locations:
- Current directory + workspaces/langlade_wi
- Parent directory + workspaces/langlade_wi  
- Plugin parent directory + workspaces/langlade_wi
- Falls back to default workspace if langlade_wi not found

**Changes Made**:
- Enhanced `_load_device_command_outputs_from_file()` with fallback workspace detection
- Added debug logging to track workspace path resolution
- Works both with and without device manager context

### 5. Enhanced Command ID Pattern Matching
**Problem**: The original code only looked for simple command names like "show running-config" but NetWORKS stores commands with descriptive IDs like "Cisco_IOS_XE_16.x_Show_Running_Config".

**Solution**: Added comprehensive command ID mapping and pattern matching:
- **Exact mapping**: Maps known descriptive IDs to user-friendly names
- **Pattern extraction**: Automatically extracts command names from descriptive IDs
- **Fuzzy matching**: Falls back to similarity matching when exact matches fail
- **Prioritized ordering**: Shows common commands first (show running-config, show version, etc.)

**Command Mapping Examples**:
- `"Cisco_IOS_XE_16.x_Show_Running_Config"` → `"show running-config"`
- `"Cisco_IOS_XE_16.x_Show_Interface_Status"` → `"show interface status"`
- `"Cisco_IOS_XE_16.x_Show_Version"` → `"show version"`

### 6. Signal Disconnection Warning Fix
**Problem**: Warning about failed signal disconnection in config preview widget:
```
RuntimeWarning: Failed to disconnect (None) from signal "currentTextChanged(QString)".
```

**Solution**: Added proper signal disconnection handling with try-catch block and specific exception handling.

### 7. ComparisonResult Attribute Mismatch
**Problem**: UI code was trying to access attributes that didn't exist on ComparisonResult:
- `result.config1` and `result.config2` (should be `device1_config` and `device2_config`)
- `result.stats` (should be `statistics`)
- `result.get_unified_diff()` method (should be `unified_diff` attribute)
- `result.to_html()` and `result.to_text()` methods (didn't exist)

**Error**:
```
ERROR | ui.config_comparison_dialog:_display_comparison_results:473 | Error displaying comparison results: 'ComparisonResult' object has no attribute 'config1'
```

**Solution**: 
- Fixed all attribute access to use correct ComparisonResult attribute names
- Added missing `to_html()` and `to_text()` methods to ComparisonResult class
- Updated UI code to use proper attribute names throughout

**Changes Made**:
- Updated `_display_two_device_results()` to use `device1_config`, `device2_config`, `statistics`
- Added `to_html()` and `to_text()` methods to ComparisonResult class
- Fixed export functionality to work with new methods

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

✅ **All functionality now working correctly**:
- ConfigMate plugin loads successfully without errors
- Command loading works from langlade_wi workspace  
- Found workspace at: `D:\SynologyDrive\Development\New folder (2)\workspaces\langlade_wi`
- Successfully loaded 2 command outputs from device `e9616b7a-4048-497e-8e33-929f86c287cd`
- Correctly mapped commands: `['show running-config', 'show interface status']`
- Retrieved configuration successfully (5445+ characters)
- Config comparison dialog shows only actual available commands
- All attribute access issues resolved
- Signal disconnection warnings eliminated

## Benefits

1. **Reliability**: No more dependency on command manager plugin instance
2. **Performance**: Direct device access is faster than plugin manager calls  
3. **Flexibility**: Users can compare any cached command between any devices
4. **Accuracy**: Only shows commands that actually exist, preventing confusion
5. **Workspace Independence**: Works with any workspace (langlade_wi, default, etc.)
6. **Better UX**: Dropdowns show meaningful command names instead of cryptic IDs
7. **Robust Error Handling**: Graceful fallbacks when data isn't available

## Summary

ConfigMate now properly:
- ✅ Loads command outputs directly from workspace files
- ✅ Maps descriptive command IDs to user-friendly names  
- ✅ Shows only actual available commands in dropdowns
- ✅ Works with langlade_wi workspace containing multiple devices
- ✅ Handles device ID access correctly (`device.id`)
- ✅ Provides robust workspace path detection
- ✅ Displays comparison results without attribute errors
- ✅ Exports comparison results successfully 