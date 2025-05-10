# Workspaces

NetWORKS supports multiple workspaces for managing different device configurations. A workspace is a logical container for devices, groups, and enabled plugins, allowing users to switch between different network configurations without having to manually manage sets of devices.

## Workspace Structure

Each workspace is stored in the `config/workspaces` directory with the following structure:

```
config/workspaces/
├── default/                   # Default workspace
│   ├── workspace.json         # Workspace metadata
│   ├── groups.json            # Group structure
│   └── devices/               # Device references
│       ├── device1.ref        # Reference to device1
│       └── device2.ref        # Reference to device2
└── production/                # Another workspace
    ├── workspace.json
    ├── groups.json
    └── devices/
```

The actual device data is stored in the `config/devices` directory and shared across workspaces. Each workspace contains references to devices rather than duplicating device data.

## Workspace File Format

### workspace.json

```json
{
  "name": "production",
  "description": "Production network devices",
  "created": "2023-11-14 10:00:00",
  "last_saved": "2023-11-14 15:30:45",
  "devices": [
    "920a4f34-c1bc-4504-9283-e20738a88203",
    "b5c12e8f-945a-4f2a-9b27-f12d89a24c67"
  ],
  "groups": [
    "All Devices",
    "Core Routers",
    "Edge Switches"
  ],
  "enabled_plugins": [
    "sample",
    "network_scanner",
    "device_backup"
  ]
}
```

## Workspace Operations

### Creating a Workspace

```python
workspace_name = "production"
description = "Production network devices"
device_manager.create_workspace(workspace_name, description)
```

### Switching Workspaces

```python
workspace_name = "production"
device_manager.load_workspace(workspace_name)
```

### Saving Workspace State

```python
device_manager.save_workspace()
```

### Listing Available Workspaces

```python
workspaces = device_manager.list_workspaces()
for workspace in workspaces:
    print(f"{workspace['name']} - {workspace.get('description', '')}")
```

### Deleting a Workspace

```python
workspace_name = "test"
device_manager.delete_workspace(workspace_name)
```

## Default Workspace

The "default" workspace is created automatically when the application starts for the first time. This workspace cannot be deleted.

## Best Practices

1. **Use descriptive names**: Choose workspace names that clearly indicate their purpose.
2. **Save often**: Call `save_workspace()` after making significant changes.
3. **Create workspaces for different environments**: For example, create separate workspaces for development, testing, and production environments.
4. **Document workspaces**: Use the description field to document the purpose and contents of each workspace.
5. **Share workspaces**: Copy workspace directories between installations to share configurations. 