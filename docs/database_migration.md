# Database Migration Guide

## Overview

netWORKS has been updated to use a fully object-oriented file-based storage system. This guide explains the changes, benefits, and how to migrate your existing data and plugins.

## Why Object-Based Storage?

The new object-based storage system offers several benefits:

1. **Better Type Safety**: Objects provide proper type checking and validation
2. **Cleaner API**: More intuitive API for working with devices and other data types
3. **Encapsulation**: Business logic is encapsulated within models rather than scattered
4. **Extensibility**: Easier to extend with new data types and behaviors
5. **Backward Compatibility**: Legacy code continues to work through a compatibility layer
6. **No Database Dependencies**: No relational database dependencies, just simple JSON files
7. **Better Portability**: Simpler file-based storage makes backups and transfers easier
8. **Improved Performance**: Direct object access without SQL translation layer
9. **Centralized Storage**: All data is stored in the @data directory for consistency

## Data Models

The key data models in the new system are:

- `Device`: Represents a network device with properties like IP, hostname, MAC, etc.
- `DeviceHistory`: Represents a historical event for a device
- `PluginData`: Represents plugin-specific data storage

## Migration Process

### Automated Migration

A migration system is provided to automatically migrate your existing database:

```python
# Import the migration function
from core.database.object_db_manager import ObjectDatabaseManager

# Migrate from old SQLite database to the new object store
new_db = ObjectDatabaseManager.migrate_from_sql_db("data/device_database.db", "@data/objects")
```

Command-line migration is also available:

```bash
python scripts/migrate_database.py --backup --replace
```

Options:
- `--source PATH`: Source SQLite database path (default: data/device_database.db)
- `--dest PATH`: Destination objects directory (default: @data/device_database_new.db)
- `--backup`: Create a backup of the source database before migration
- `--replace`: Replace any existing object files in the destination

### Manual Migration

If you prefer to migrate manually:

1. Create a backup of your existing database
2. Run the main application with the new storage system
3. Your existing data will still be accessible through the compatibility layer

## Using the New API in Plugins

### Legacy API (Backward Compatible)

All existing plugins will continue to work without changes. The bridge manager provides compatibility with the old API:

```python
# This code will still work
device = db_manager.get_device(ip_address)
device['hostname'] = 'new-hostname'
db_manager.add_device(device)
```

### New Object API (Recommended)

For new plugins or updates to existing ones, we recommend using the new object-based API:

```python
# Get a device as an object
device = db_manager.get_device_object(ip_address)

# Use properties and methods
print(device.hostname)
device.hostname = "new-hostname"
device.set_metadata("location", "server-room")
device.add_tag("important")

# Save changes
db_manager.add_device_object(device)
```

### Example: Working with Device Objects

```python
# Get all devices as objects
devices = db_manager.get_device_objects()

# Filter devices by a property
active_devices = [d for d in devices if d.status == 'active']

# Update multiple devices
for device in active_devices:
    device.set_metadata('last_checked', datetime.datetime.now().isoformat())
    db_manager.add_device_object(device)
```

## Plugin Updates

To make the most of the new storage system, consider updating your plugins:

1. Import the model classes when needed:
   ```python
   from core.database.models import Device, PluginData
   ```

2. Check for and use the new object-based methods:
   ```python
   if hasattr(db_manager, 'get_device_object'):
       # Use new object API
       device = db_manager.get_device_object(ip)
   else:
       # Fall back to legacy API
       device_dict = db_manager.get_device(ip)
   ```

3. Update your plugin manifest to indicate compatibility with the new storage system:
   ```json
   {
       "name": "your-plugin",
       "version": "2.0.0",
       "features": ["object-storage"]
   }
   ```

4. Use the plugin's dedicated data directory for any plugin-specific files:
   ```python
   data_dir = plugin_api.get_data_directory()  # Returns @data/<plugin_id>
   ```

## Storage Location

All database files and plugin data are now stored in the `@data` directory:

- Device data: `@data/objects/devices.json`
- Device history: `@data/objects/device_history.json`
- Plugin data: `@data/objects/plugin_data.json`
- App settings: `@data/objects/app_settings.json`
- Plugin-specific files: `@data/<plugin_id>/...`

For more details on the storage structure, see [docs/storage_structure.md](storage_structure.md).

## Troubleshooting

If you encounter issues with the data migration:

1. Check the `migration.log` file for errors
2. Restore from the backup created during migration
3. Try running with the `--dest` option to create a new storage location without replacing the old one
4. Contact support if issues persist

## Backup and Restore

The new storage system includes built-in backup and restore capabilities:

```python
# Create a backup
db_manager.backup_database("@data/backups/my_backup")

# Restore from a backup
db_manager.restore_database("@data/backups/my_backup")
```

## Automatic Workspace Backup

Workspaces are automatically saved to `@data/autosave` with timestamped random filenames to prevent data loss in case of application crashes or unexpected shutdowns.

## Technical Details

For developers interested in the implementation details:

- `ObjectStore`: Core implementation of file-based object storage with collections
- `ObjectCollection`: Generic collection class for storing typed objects
- `ObjectDatabaseManager`: Object-database manager that wraps ObjectStore
- `BridgeDatabaseManager`: Compatibility layer for legacy code

The system uses JSON files for storage with one file per collection type. Each file contains a dictionary mapping object keys to their serialized representations. 