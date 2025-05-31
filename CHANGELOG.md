# Changelog

All notable changes to this project will be documented in this file.

## [0.9.11] - 2025-05-29

### Added
- **Version-Specific Build Directories**: Build system now creates version-specific directories (e.g., `release/v0.9.11/`)
- **Directory Configuration System**: Added `directory_config.json` to define standardized directory structure
- **Configurable Directory Paths**: All directory paths can now be changed in application settings
- **Persistent Directory Management**: Directories are no longer recreated once established
- **Workspace Isolation**: Enhanced workspace-specific data storage and configuration

### Fixed
- **Redundant Directory Structure**: Eliminated duplicate and redundant folders in data organization
- **Directory Persistence**: Fixed issue where directories would disappear after first-time startup
- **Build Directory Management**: Builds now maintain separate version-specific folders
- **Configuration Consistency**: Standardized how directories are created and managed across the application

### Improved
- **Build System Architecture**: Enhanced build script with standardized directory structure definition
- **Directory Structure Documentation**: Added comprehensive directory configuration with descriptions
- **Settings Integration**: Directory paths are now fully configurable through the settings dialog
- **Workspace Management**: Improved isolation between different workspaces
- **First-Time Setup**: Enhanced setup process to use standardized directory configuration

### Technical Changes
- **Directory Structure Version 2.0**: New standardized structure with no redundancy
- **Build Configuration**: Added directory configuration file generation during build
- **Persistent Storage**: Implemented .gitkeep files to ensure directory persistence
- **Configuration Management**: Enhanced settings to include directory path configuration
- **Workspace Configuration**: Added workspace-specific configuration files

### Directory Structure Changes
```
Old Structure (redundant):          New Structure (standardized):
├── config/                         ├── config/
│   ├── workspaces/                 │   ├── settings/
│   │   └── default/                │   └── backups/
│   └── settings/                   ├── workspaces/
├── data/                           │   └── default/
│   ├── workspaces/                 ├── data/
│   ├── downloads/                  │   ├── downloads/
│   └── ...                         │   ├── backups/
└── ...                             │   ├── screenshots/
                                    │   └── issue_queue/
                                    ├── logs/
                                    │   └── crashes/
                                    ├── exports/
                                    ├── command_outputs/
                                    │   ├── history/
                                    │   └── outputs/
                                    └── plugins/
```

## [0.9.10] - 2025-05-29

### Fixed
- **Plugin Directory Configuration**: Fixed critical issue where plugin directories defaulted to temporary locations instead of the proper plugins directory created during setup
- **Application Directory Detection**: Improved detection of application base directory for both development and executable environments
- **Plugin Directory Path Resolution**: Plugin manager now correctly calculates external plugins directory relative to executable location

### Improved
- **Settings Dialog Enhancement**: Plugin directory changes in settings now take immediate effect without requiring application restart
- **Plugin Manager Logging**: Added detailed logging of plugin directory configuration for better troubleshooting
- **Configuration Management**: Enhanced config system to properly handle plugin directory paths across different deployment scenarios
- **Setup Integration**: First-time setup now includes explicit plugin directory configuration in default settings

## [0.9.9] - 2025-05-29

### Fixed
- **Unicode Character Encoding Error**: Fixed critical issue in first-time setup that prevented installation on Windows systems with charmap codec
- Replaced Unicode arrow character (→) with ASCII equivalent (->) in setup text to ensure compatibility across all Windows configurations
- Enhanced file encoding handling with explicit UTF-8 encoding for all configuration files

### Improved
- **Light Mode Styling**: Added comprehensive light mode styling to the first-time setup dialog
- Professional appearance with consistent color scheme and improved visual hierarchy
- Enhanced progress tracking with better visual feedback during setup process
- Improved error handling and user feedback during setup failures

## [0.9.8] - 2025-05-28

### Added
- **First-Time Setup System**: Executable builds now include an intelligent first-time setup process
- GUI setup dialog with progress tracking and options for sample data creation
- Automatic directory structure creation on first run
- Console fallback setup for headless environments
- Setup completion tracking to prevent repeated setup runs

### Fixed
- **Qt5Core.dll Decompression Error**: Fixed by excluding Qt libraries from UPX compression
- Enhanced executable startup with proper Python path handling
- Improved error reporting and graceful failure handling
- Better support for PyInstaller executable packaging

### Improved
- Streamlined executable initialization process
- Professional first-run user experience
- Automatic workspace and configuration initialization
- Clear setup progress feedback for users

## [0.9.7] - 2025-05-28

### Changed
- **Streamlined Build System**: Clean EXE builds now create ultra-minimal releases with only 3-4 files maximum
- Removed unnecessary launcher script from EXE builds - all functionality is wrapped in the standalone executable
- Updated build documentation to reflect the cleaner distribution process
- Enhanced installation options with standalone executable as the recommended method

### Improved
- Simplified distribution package for end users
- Reduced file count in releases for cleaner deployment
- Updated README.md with clear installation options including standalone executable
- Enhanced BUILD.md documentation with streamlined build process details

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

## [Build System Update] - 2025-01-09

### 🛠️ NetWORKS Interactive Build System - Major Update

#### Fixed
- **CRITICAL FIX**: Removed problematic `--specpath` option from PyInstaller command
  - Error: "option(s) not allowed: --specpath makespec options not valid when a .spec file is given"
  - PyInstaller now works correctly with custom spec files
- **CRITICAL FIX**: Fixed Python boolean syntax in generated spec files
  - Error: "NameError: name 'false' is not defined. Did you mean: 'False'?"
  - Spec files now use proper Python boolean values (True/False) instead of lowercase strings
- **Build Failures**: Resolved PyInstaller command-line argument conflicts
- **Error Handling**: Improved error reporting with detailed PyInstaller output

#### Added
- **🎨 Interactive PyInstaller Configuration**: Advanced customization options
  - Default mode with recommended settings for each build type
  - Custom mode with fine-grained control over build optimization
  - UPX compression options (with antivirus warnings)
  - Module exclusion choices (tkinter, matplotlib, etc.)
  - Plugin dependency inclusion control
  - Three optimization levels: Basic, Standard, Aggressive

- **🔧 Dynamic Spec Generation**: Intelligent PyInstaller spec creation
  - Optimization-level based hidden imports
  - Smart module exclusion based on user choices
  - Build-type specific configurations
  - Comprehensive module lists with size optimization

- **📊 Enhanced Configuration Summary**: 
  - Shows PyInstaller settings in build confirmation
  - Detailed spec configuration display during build
  - Module count and optimization level reporting

#### Improved
- **User Experience**: Clearer prompts and explanations for technical options
- **Error Reporting**: Better PyInstaller output parsing and display
- **Build Process**: More detailed progress reporting during executable creation
- **Documentation**: Updated README with PyInstaller configuration examples

#### Technical Details
- Fixed PyInstaller command syntax when using custom spec files
- Added comprehensive hidden imports management
- Implemented smart module exclusion based on user preferences
- Enhanced spec file generation with optimization-specific settings
- Added proper error handling for PyInstaller subprocess calls

#### User Benefits
- **Resolved Build Failures**: Builds now complete successfully without PyInstaller errors
- **Customizable Builds**: Users can optimize executable size and build time
- **Better Control**: Choose exactly which dependencies to include
- **Antivirus Friendly**: Option to disable UPX compression to avoid false positives
- **Size Optimization**: Exclude unnecessary modules for smaller executables

The build system now provides both simple one-click building and advanced customization for power users, while maintaining the exact same functionality as `Start_NetWORKS.bat`.

--- 