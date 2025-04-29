# Storage Structure in netWORKS

This document explains the storage structure in netWORKS, including how core application data and plugin data are stored.

## Directory Structure

All netWORKS data is stored in the `@data` directory, with the following structure:

```
@data/
  ├── objects/             # Object-based database storage
  │   ├── devices.json     # Device objects 
  │   ├── device_history.json # Device history events
  │   ├── plugin_data.json # Plugin-specific data
  │   └── app_settings.json # Application settings
  │
  ├── autosave/            # Automatic workspace backups
  │   └── autosave_*.json  # Timestamped autosave files
  │
  ├── exports/             # User-exported workspaces
  │   └── workspace_*.json # Exported workspace files
  │
  └── <plugin_id>/         # Plugin-specific data directories
      └── ...              # Plugin-specific files and subdirectories
```

## Storage Principles

1. **All data in `@data`**: All persistent data must be stored within the `@data` directory to ensure consistent backups and portability.
2. **Autosave**: Workspaces are automatically saved with random names to prevent data loss.
3. **Plugin isolation**: Each plugin should store its data in its own subdirectory.

## Accessing Storage from Plugins

### Getting the Base Data Directory

```python
def init_plugin(plugin_api):
    # Get the plugin's data directory
    data_dir = plugin_api.get_data_directory()
    # data_dir will be "@data/<plugin_id>"
    return MyPlugin(plugin_api, data_dir)
```

### Storing Plugin-Specific Files

```python
class MyPlugin:
    def __init__(self, api, data_dir):
        self.api = api
        self.data_dir = data_dir
        
        # Create plugin data directory if it doesn't exist
        import os
        os.makedirs(self.data_dir, exist_ok=True)
    
    def save_custom_data(self, filename, data):
        """Save custom data to the plugin's data directory"""
        import json
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return filepath
```

### Using the Object Database

For structured data that relates to devices or application state, use the object database:

```python
# Store plugin data in the database
def store_settings(self, settings):
    self.api.get_database_manager().store_plugin_data(
        self.api.get_plugin_id(), 
        "settings", 
        settings
    )

# Retrieve plugin data from the database
def get_settings(self):
    return self.api.get_database_manager().get_plugin_data(
        self.api.get_plugin_id(),
        "settings",
        {}  # Default value if not found
    )
```

## Automatic Workspace Backup

The application automatically saves the current workspace at regular intervals to the `@data/autosave` directory. These files use the naming format `autosave_YYYYMMDD_HHMMSS_randomid.json`.

The autosave interval is configurable in the application settings:

```json
{
  "app": {
    "auto_save_interval": 300  // Seconds between autosaves (default: 5 minutes)
  }
}
```

## Exporting and Importing Workspaces

Users can manually export the workspace using File > Export Workspace. The default location is `@data/exports`.

When importing a workspace, the dialog will automatically look in the following locations (in order):
1. `@data/exports`
2. `@data/autosave`
3. `@data`

## Plugin Guidelines

1. **Always use the provided API**: Use `api.get_data_directory()` to get your plugin's data directory.
2. **Create subdirectories as needed**: Organize your plugin's data in subdirectories.
3. **Clean up after yourself**: When your plugin is disabled or uninstalled, clean up unnecessary files.
4. **Handle migration gracefully**: If your plugin previously stored data elsewhere, migrate it to the new location.
5. **Use unique filenames**: Include timestamps or UUIDs in filenames to prevent conflicts.
6. **Respect file size limits**: Avoid storing very large files that could impact performance or storage.

## Creating a Plugin with Proper Storage

```python
class MyPlugin:
    def __init__(self, api):
        self.api = api
        self.plugin_id = api.get_plugin_id()
        self.data_dir = api.get_data_directory()
        
        # Create our subdirectories
        import os
        self.config_dir = os.path.join(self.data_dir, "config")
        self.output_dir = os.path.join(self.data_dir, "output")
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load configuration
        self.config = self.load_config()
    
    def load_config(self):
        """Load plugin configuration from file"""
        import json
        import os
        
        config_file = os.path.join(self.config_dir, "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.api.log_error(f"Error loading config: {str(e)}")
        
        # Default configuration
        return {"setting1": "default", "setting2": 123}
    
    def save_config(self):
        """Save plugin configuration to file"""
        import json
        import os
        
        config_file = os.path.join(self.config_dir, "config.json")
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            self.api.log_error(f"Error saving config: {str(e)}")
            return False
```

## Core Application Internals

The core application uses the Object Database Manager and Object Store to manage persistent data. These components automatically use the `@data` directory structure.

For plugin developers, the database is accessible through the Plugin API, which provides methods to interact with devices, settings, and plugin-specific data. 