# Changelog

All notable changes to this project will be documented in this file.

## [0.9.4] - 2025-05-29

### Fixed
- Added signal connection tracking for plugins to improve cleanup
- Enhanced credential store with better fallback mechanisms
- Fixed remaining signal disconnection warnings

## [0.9.3] - 2025-05-29

### Fixed
- Fixed signal disconnection warnings when unloading plugins
- Added object names to UI components to properly save and restore window state
- Added workspace directory access methods for command manager plugin credentials

## [0.9.2] - 2025-05-29

### Fixed
- Fixed device signal connection error when loading workspaces
- Improved plugin loading to ensure enabled plugins are properly loaded when switching workspaces

## [0.9.1] - 2025-05-29

### Fixed
- Fixed workspace switching to properly unload and reload plugins, preventing plugins from being loaded multiple times

## [0.9.0] - 2025-05-29

### Added
- Enhanced property panel with separate sections for core, plugin, and custom properties
- Added property naming convention for plugins (using plugin_id: prefix)
- Updated documentation with property naming guidelines for plugin developers

### Changed
- Improved property value display formatting for complex data types
- Updated core UI components to use the latest PySide6 features

### Fixed
- Fixed issue with device property filter not working with complex property values

## [0.8.54] - 2025-05-15

### Added
- Enhanced property details viewer with multiple view modes
- Added tabular data representation for structured data
- New JSON syntax highlighting in property details 