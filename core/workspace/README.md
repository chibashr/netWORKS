# netWORKS Workspace System

## Overview

The workspace system in netWORKS allows users to maintain separate work environments (saved sessions), each containing:

- Network devices and their configurations
- Device groups and organization
- Application settings and preferences
- Plugin data and configuration
- Scan results and history

Workspaces function like projects or saved sessions that users can switch between.

## User Interface

### Workspace Selection Dialog

At application startup, users are presented with a workspace selection dialog that allows them to:

1. Choose an existing workspace to load
2. Create a new workspace 
3. Rename or delete existing workspaces

### Workspace Management

During application use, users can:

- Save the current workspace (Ctrl+S)
- Export a workspace to a file for backup or transfer
- Import a workspace from a file
- Create a new workspace
- Switch between workspaces
- Rename or delete workspaces

All workspace management functions are available in the toolbar's "File" group and in the File menu.

## Technical Implementation

### Core Components

- **WorkspaceManager**: Central class managing workspace creation, loading, saving, and switching
- **WorkspaceSelectionDialog**: UI for workspace selection at startup
- **WorkspaceToolbar**: UI component for workspace management during application use

### Data Structure

Each workspace is stored in its own directory under `data/workspaces/[workspace-id]/` and contains:

- `metadata.json`: Basic information about the workspace (name, creation date, etc.)
- `data.json`: The actual workspace data, including devices, settings, and plugin data

### API Reference

#### WorkspaceManager

```python
# Create a new workspace
workspace_id = workspace_manager.create_workspace(name, description="")

# Open an existing workspace
success = workspace_manager.open_workspace(workspace_id)

# Save the current workspace
success = workspace_manager.save_workspace(workspace_id=None)  # None = current

# Get all available workspaces
workspaces = workspace_manager.get_workspaces()  # Dict: id -> metadata

# Get current workspace metadata
metadata = workspace_manager.get_current_workspace()

# Export a workspace to file
success = workspace_manager.export_workspace(workspace_id, file_path)

# Import a workspace from file
workspace_id = workspace_manager.import_workspace(file_path)

# Delete a workspace
success = workspace_manager.delete_workspace(workspace_id)

# Rename a workspace
success = workspace_manager.rename_workspace(workspace_id, new_name)
```

## Integration with Plugins

Plugins can store their data in workspaces, making their state persist across application sessions and allowing different configurations per workspace.

To access workspace data from a plugin:

```python
# Store plugin data
self.main_window.database_manager.store_plugin_data(plugin_id, key, value)

# Retrieve plugin data
data = self.main_window.database_manager.get_plugin_data(plugin_id, key)
```

When a workspace is saved, all plugin data stored in the database will be included in the workspace file. 