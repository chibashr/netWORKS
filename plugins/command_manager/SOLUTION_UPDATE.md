# Command Manager Plugin Updates

## Overview

Enhanced the Command Manager plugin to support running commands on device groups and subnets in addition to individual devices. This update improves the plugin's flexibility and makes it more efficient for network administrators to manage multiple devices with similar characteristics.

## Key Changes

### UI Enhancements

1. **Tabbed Interface in Command Dialog**:
   - Added tabs to separate Devices, Groups, and Subnets
   - Each tab has its own selection list and maintains its own state

2. **Group and Subnet Selection**:
   - Added UI components to display available device groups
   - Implemented automatic subnet detection based on device IP addresses
   - Provided selection capabilities for both groups and subnets

### Credential Management

1. **Hierarchical Credential Strategy**:
   - Implemented a hierarchy for credential resolution: device > group > subnet
   - When running commands, credentials are fetched in order of specificity
   - Each level can have its own credential set

2. **Enhanced Credential Manager**:
   - Updated to support viewing, editing, and saving credentials for groups and subnets
   - Added ability to select groups and subnets in the credential manager
   - Improved UI to better indicate which entities have credentials defined

### Command Execution

1. **CommandWorker Improvements**:
   - Modified to recognize group and subnet credentials
   - Enhanced credential retrieval logic to follow the hierarchy
   - Improved logging to show which credential source is being used

2. **Context Menu Integration**:
   - Added context menu items for device groups and subnets
   - Implemented handlers for new menu items
   - Ensured proper selection state is maintained when launching from context menus

### Documentation

1. **README Updates**:
   - Added documentation for the new group and subnet features
   - Updated usage instructions to cover new functionality

2. **API Documentation**:
   - Documented new methods and parameters for working with groups and subnets
   - Clarified credential hierarchy and resolution strategy

## Implementation Details

### Command Dialog

The Command Dialog was extended with a tabbed interface allowing users to select targets by device, group, or subnet. Each tab maintains its own selection state, and when commands are executed, the appropriate devices are gathered based on the active tab.

### Context Menu Handling

The plugin now registers additional context menu actions with the device group and subnet tables (if available). These actions allow for running commands on all devices within a group or subnet and managing credentials for these collections.

### Credential Resolution

When running commands, the CommandWorker first attempts to use device-specific credentials. If none are found, it checks for credentials associated with any groups the device belongs to. If still unsuccessful, it falls back to subnet-based credentials.

## Benefits

1. **Simplified Operations**: Run the same command set on logical groups of devices with one action
2. **Consistent Credentials**: Define credentials once for a group or subnet rather than per device
3. **Flexible Targeting**: Choose the most appropriate level (device, group, subnet) for your task
4. **Improved Efficiency**: Manage large networks more effectively by operating on collections

## Backward Compatibility

All existing functionality is preserved. The plugin continues to work with individual devices as before, with the group and subnet features providing additional capabilities rather than replacing existing ones.

# Command Manager Plugin Bugfixes and Enhancements

## 1. Fixed DeviceGroup Check Error

Fixed the error with `'DeviceGroup' object has no attribute 'get_devices'` by enhancing the device group detection logic to handle different possible implementations of device groups:

- Added try/except blocks to gracefully handle errors
- Added checks for different possible methods to retrieve devices from a group:
  - `get_devices()`
  - `devices` property
  - `get_device_ids()`

## 2. Updated UI to Use Row Selection

Replaced checkboxes with row selection in the command dialog:
- Removed checkbox columns from device and command tables
- Updated UI to use multi-row selection
- Modified device and command selection logic to work with row selection
- Improved visual clarity and better aligned with the application's standard UI patterns

## 3. Implemented Comprehensive Credential Manager

Added a full-featured credential manager UI with support for:
- Device-specific credentials
- Group-based credentials
- Subnet-based credentials

Made the credential manager accessible from:
- Main toolbar
- Device context menu

## 4. Added Commands Tab to Device Properties

Implemented a Commands tab in the device properties panel that shows:
- Command history for the selected device
- Command text, timestamp, and success status
- Button to view the full command output
- Export and delete functionality

## 5. Added Report Generation

Implemented a report generation feature that:
- Supports Text, HTML, Excel, and Word formats
- Allows filtering by date range and success status
- Includes device information
- Provides formatted output for easy readability

## 6. Fixed Application Integration

Improved plugin integration with the main application:
- Added proper toolbar creation and registration
- Fixed device tab provider implementation
- Made sure all UI components are properly connected
- Improved command set and credential management

## 7. Enhanced Error Handling

Added better error handling throughout the plugin:
- Graceful handling of missing device group methods
- Improved credential store error handling
- Better error reporting for command failures
- Friendly error messages for UI operations

# Command Manager Plugin Update Notes

## Credential Storage Improvements

### Changes Made

1. **Device-Property-Based Credential Storage**:
   - Credentials are now stored directly in device properties using the `credentials` property
   - This ensures credentials are properly associated with their devices
   - Credentials are saved and loaded with the device configuration

2. **Backward Compatibility**:
   - Legacy file-based credentials are automatically migrated to device properties
   - Fallback to file-based credentials if device manager is not available
   - Group and subnet credentials still use the file-based approach

3. **Improved Security**:
   - Credentials are encrypted before storage in device properties
   - Decryption happens only when credentials are needed

4. **Migration Process**:
   - When the plugin loads, it checks for existing credential files
   - If a file exists for a device, the credentials are migrated to the device properties
   - The original file is removed after successful migration

### Benefits

1. **Data Integrity**: 
   - Credentials are now directly attached to their associated devices
   - No risk of orphaned credential files when devices are deleted
   - Credentials move with devices when exported/imported

2. **Simplified Code**:
   - No need to maintain separate file paths and IDs
   - Direct access to credentials through device properties

3. **Better User Experience**:
   - More intuitive credential management
   - Credentials are maintained with the devices they belong to

## Implementation Details

The core changes were made in the following files:

1. `utils/credential_store.py`: 
   - Modified to store/retrieve credentials from device properties
   - Added migration logic for legacy credentials

2. `core/command_manager.py`: 
   - Updated to pass the device_manager to the credential store
   - Ensures proper access to device objects

3. `API.md` and `README.md`: 
   - Updated documentation to reflect the new storage mechanism

## Future Considerations

1. Group and subnet credentials could also benefit from being stored in the main application's configuration, but this would require changes to the core application structure.

2. Consider adding a migration utility for batch conversion of file-based credentials to device properties. 