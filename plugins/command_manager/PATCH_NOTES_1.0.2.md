# Command Manager Plugin - Patch 1.0.2

## Fixed Issues

### Credential Manager Bugs

The Command Manager's credential management system now properly handles device groups and subnets, fixing several critical bugs:

1. Fixed an `UnboundLocalError` related to improper logger usage in the credential manager UI
2. Resolved a `TypeError: unhashable type: 'dict'` bug that occurred when selecting subnets in the credential manager
3. Improved handling of different group object structures throughout the credential manager

## Technical Changes

### Robust Subnet Object Handling

The credential manager now properly extracts subnet information from different data structures:

```python
subnet_data = current.data(Qt.UserRole)
subnet = subnet_data['subnet'] if isinstance(subnet_data, dict) and 'subnet' in subnet_data else subnet_data
```

### Improved Group Name Extraction

Added consistent group name extraction logic that handles all possible group structures:

```python
group_name = None
if isinstance(group, dict) and 'name' in group:
    group_name = group['name']
elif hasattr(group, 'name'):
    group_name = group.name
elif hasattr(group, 'get_name'):
    group_name = group.get_name()
else:
    group_name = str(group)
```

### Proper Logger Initialization

Fixed logger initialization by adding an explicit import at the top of the credential manager module:

```python
from loguru import logger
```

## Compatibility

This patch requires NetWORKS core version 0.8.16 or higher. No configuration changes are needed; the update will automatically apply when the plugin is loaded. 