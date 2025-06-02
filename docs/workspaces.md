# NetWORKS Workspaces

Workspaces in NetWORKS allow you to organize your devices, groups, and settings into separate logical environments. Each workspace maintains its own set of devices, configuration templates, and plugin settings.

## Overview

A workspace is a collection of:
- **Devices**: Network devices and their properties
- **Groups**: Device groupings and hierarchies  
- **Settings**: Workspace-specific configuration
- **Plugin Data**: Plugin-specific data and configurations
- **Templates**: Configuration templates and scripts

## Directory Structure

Workspaces are stored in the `workspaces/` directory in the root of your NetWORKS installation:

```
workspaces/
├── default/                  # Default workspace
│   ├── devices/             # Device storage
│   ├── settings/            # Workspace settings
│   ├── command_manager/     # Command manager plugin data
│   ├── configmate/          # ConfigMate plugin data
│   └── workspace.json       # Workspace metadata
├── production/              # Production workspace example
│   ├── devices/
│   ├── settings/
│   ├── plugins/            # Workspace-specific plugins
│   └── workspace.json
└── staging/                 # Staging workspace example
    └── ...
```

Each workspace is stored in the `workspaces` directory with the following structure:

```
workspaces/
├── default/                   # Workspace name
│   ├── devices/              # Device definitions and data
│   ├── groups.json           # Device groups
│   ├── workspace.json        # Workspace metadata
│   ├── settings/             # UI layouts and preferences
│   └── plugins/              # Plugin-specific data
└── production/               # Another workspace
    └── ...
```

## Workspace Structure

### Core Files

- `workspace.json`: Contains workspace metadata including name, description, enabled plugins, and settings
- `groups.json`: Defines device groups and their relationships
- `recycle_bin.json`: Stores deleted devices for potential recovery

### Directories

- `devices/`: Individual device folders, each containing `device.json` and any associated files
- `settings/`: UI preferences like window layouts (`window_layout.ini`)
- Plugin directories: Each plugin can store workspace-specific data (e.g., `command_manager/`, `configmate/`)

## Creating Workspaces

### Using the UI

1. Go to **File → Workspaces → Create Workspace**
2. Enter a name and description
3. Click **Create**

### Programmatically

```python
# Create a new workspace
device_manager.create_workspace("production", "Production environment")

# Switch to the workspace
device_manager.load_workspace("production")
```

## Switching Workspaces

### Using the UI

1. Go to **File → Workspaces → Switch Workspace**
2. Select the desired workspace from the list
3. Click **Switch**

### Programmatically

```python
# List available workspaces
workspaces = device_manager.list_workspaces()

# Switch to a workspace
success = device_manager.load_workspace("production")
```

## Workspace Management

### Backing Up Workspaces

Workspaces can be backed up by copying their entire directory:

```bash
# Backup a workspace
cp -r workspaces/production workspaces/production-backup

# Or backup all workspaces
cp -r workspaces/ workspaces-backup/
```

### Deleting Workspaces

```python
# Delete a workspace (moves to recycle bin first)
device_manager.delete_workspace("old-workspace")
```

### Importing/Exporting

Workspaces can be shared by copying their directories between NetWORKS installations.

## Plugin Integration

Plugins can store workspace-specific data in their own subdirectories within each workspace:

```
workspaces/production/
├── command_manager/
│   ├── credentials/
│   └── command_sets.json
├── configmate/
│   └── templates/
└── my_plugin/
    └── plugin_data.json
```

## Best Practices

1. **Naming**: Use descriptive names that reflect the environment (e.g., "production", "staging", "lab")
2. **Organization**: Keep related devices in the same workspace
3. **Backups**: Regularly backup important workspaces
4. **Plugin Data**: Be aware that switching workspaces changes plugin data context
5. **Templates**: Store environment-specific templates in the appropriate workspace

## Migration

When upgrading NetWORKS, workspace data is automatically migrated to maintain compatibility. The workspace structure is designed to be forward-compatible with future versions.

## Troubleshooting

### Workspace Won't Load

1. Check that the workspace directory exists in `workspaces/`
2. Verify `workspace.json` is valid JSON
3. Check the NetWORKS log files for specific errors

### Missing Devices

1. Ensure the workspace's `devices/` directory contains device folders
2. Check that each device folder has a valid `device.json` file
3. Verify workspace permissions

### Plugin Data Missing

1. Confirm the plugin is enabled for the workspace (check `workspace.json`)
2. Verify plugin-specific directories exist in the workspace
3. Check plugin logs for initialization errors 