# Create a netWORKS Plugin

## Plugin Purpose
[Describe the purpose of your plugin. What problem does it solve? What functionality will it add to netWORKS?]

Example: "Create a network topology visualization plugin that can map discovered devices and their connections in a visual graph."

## Plugin Details

### Plugin Name
[Technical plugin ID, lowercase with hyphens]
Example: "network-topology-visualizer"

### Display Name
[User-friendly name displayed in the UI]
Example: "Network Topology Visualizer"

### Version
[Initial version, usually 1.0.0]

### Description
[One or two sentences describing what the plugin does]
Example: "Visualizes network devices and their connections in an interactive graph. Supports different layout algorithms and can export visualizations."

### Author
[Your name or organization]

## Required Features
[List the main features your plugin should have]
Example:
- Create visual graph of devices discovered by netWORKS
- Show connection types between devices
- Allow different layout algorithms (hierarchical, circular, etc.)
- Export visualizations as PNG/SVG
- Filter visualization by device type or subnet

## UI Requirements
[Describe how your plugin should integrate with the netWORKS UI. Which panels should it use?]

### Available UI Areas
netWORKS provides several UI areas that plugins can integrate with:

1. **Panels**:
   - **Left Panel**: Typically used for controls, filters, and navigation trees
   - **Right Panel**: Often used for device details, property editors, or supplementary views
   - **Bottom Panel**: Commonly used for logs, results, terminal output, or visualization

2. **Device Table**:
   - Plugins can add custom columns to the main device table
   - Custom renderers can be provided for specific data types

3. **Main Menu**:
   - Plugins can add items to existing menus (File, View, Tools, etc.)
   - Plugins can create new menu categories for specialized functions

4. **Toolbars**:
   - Plugins can add buttons and controls to the main toolbar
   - Custom toolbars can be created for specific plugin functionality

5. **Context Menus**:
   - Right-click menus on devices or other elements
   - Custom actions based on selection context

Example UI Integration:
- Left panel with visualization controls and filtering options
- Bottom panel showing the actual network topology graph
- Add custom device table column for "Network Role"
- Add "Export Topology" option to the File menu
- Add "Layout" submenu under Tools menu
- Context menu items for selected devices to show related connections

## Database Integration
[Describe how your plugin interacts with the database system]

### Database Access
Plugins can access the central database through the database manager API:
```python
# Get database manager instance
db_manager = self.api.get_database_manager()

# Execute queries
results = db_manager.execute_query("SELECT * FROM devices WHERE ip LIKE ?", ["192.168.1.%"])

# Transaction handling
with db_manager.transaction() as cursor:
    cursor.execute("INSERT INTO plugin_data (plugin_id, key, value) VALUES (?, ?, ?)", 
                  [self.id, "last_scan", json.dumps(scan_data)])
```

### Extending Device Schema
Plugins can add custom fields to the device schema by registering them during initialization:
```python
# Register custom device fields
self.api.register_device_field(
    field_name="open_ports",           # Field identifier
    display_name="Open Ports",         # User-friendly name
    field_type="list",                 # Data type (string, number, boolean, list, dict)
    default_value=[],                  # Default value when not set
    searchable=True,                   # Whether field can be used in searches
    visible_in_table=True,             # Whether to show in device table by default
    renderer="tags"                    # UI renderer to use for display
)
```

### Storing Plugin-Specific Data
Plugins should store their settings and data in the plugin_data table:
```python
# Store plugin settings
def save_settings(self, settings_dict):
    db_manager = self.api.get_database_manager()
    serialized = json.dumps(settings_dict)
    db_manager.execute_query(
        "INSERT OR REPLACE INTO plugin_data (plugin_id, key, value) VALUES (?, 'settings', ?)",
        [self.id, serialized]
    )
    
# Retrieve plugin settings
def load_settings(self):
    db_manager = self.api.get_database_manager()
    result = db_manager.execute_query(
        "SELECT value FROM plugin_data WHERE plugin_id = ? AND key = 'settings'",
        [self.id]
    )
    if result and len(result) > 0:
        return json.loads(result[0][0])
    return {}  # Default settings
```

### Device Metadata Management
Plugins can update device metadata through the API:
```python
# Update device metadata
def update_device_ports(self, device_id, ports):
    self.api.update_device_metadata(device_id, {"open_ports": ports})
    
# Retrieve device with metadata
device = self.api.get_device(device_id)
if device and "open_ports" in device["metadata"]:
    ports = device["metadata"]["open_ports"]
```

### Database Schema
The core database schema includes these main tables:
- `devices`: Core device information (id, ip, mac, hostname, etc.)
- `device_metadata`: Extended device properties 
- `scan_history`: Records of previous scans
- `plugin_data`: Plugin-specific data storage
- `notes`: User notes for devices

Example of adding a new table for custom plugin data:
```python
def initialize_database(self):
    db_manager = self.api.get_database_manager()
    db_manager.execute_query("""
        CREATE TABLE IF NOT EXISTS topology_connections (
            id TEXT PRIMARY KEY,
            source_device_id TEXT NOT NULL,
            target_device_id TEXT NOT NULL,
            connection_type TEXT NOT NULL,
            discovered_date TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY (source_device_id) REFERENCES devices(id),
            FOREIGN KEY (target_device_id) REFERENCES devices(id)
        )
    """)
```

## Exported Functions
[Optional: List any functions your plugin will expose to other plugins]
Example:
- generate_topology_graph(devices, layout_type)
- export_visualization(format, path)

## Events/Hooks
[Optional: List any events your plugin will emit or hooks it will subscribe to]
Example:
- Subscribe to: device_found, scan_complete
- Emit: topology_updated, visualization_exported

## Additional Requirements
[Any other specific requirements or constraints]
Example:
- Must use networkx and matplotlib for graph generation
- Should support light and dark themes
- Should store visualization preferences in the database

## Dependencies
[List any specific Python packages your plugin requires]
Example:
- networkx>=2.8.0
- matplotlib>=3.5.0
- pyvis>=0.3.0