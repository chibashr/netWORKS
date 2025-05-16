# Command Manager Plugin - Patch 1.0.1

## Fixed Issues

### Device Groups Display and Management

The Command Manager now properly displays and manages device groups, fixing issues where groups were not showing up correctly in the Command Dialog. This update ensures that:

1. Device groups are now correctly displayed in the groups tab of the Command Dialog
2. Running commands on groups works more reliably with improved error handling
3. Group credentials are properly detected and applied when running commands

## Technical Changes

### Added Core Functionality

- Added `get_device_groups_for_device()` method to the DeviceManager class to properly identify which groups a device belongs to
- Updated credential fallback logic to better handle various group structures
- Improved error handling and logging for group-related operations

### API Documentation

- Updated API.md with documentation for the new device groups method
- Added examples for using device groups in plugins

## Compatibility

This patch requires NetWORKS core version 0.8.16 or higher. No configuration changes are needed; the update will automatically apply when the plugin is loaded. 