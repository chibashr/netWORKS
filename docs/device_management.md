# Device Management in netWORKS

This document provides information about managing devices in netWORKS, including discovery, manual addition, and editing.

## Table of Contents
1. [Device Discovery](#device-discovery)
2. [Manual Device Addition](#manual-device-addition)
3. [Device Editing](#device-editing)
4. [Custom Fields](#custom-fields)
5. [Multi-Selection](#multi-selection)
6. [Device Groups](#device-groups)
7. [Device Management](#device-management)
8. [Device Details](#device-details)
9. [Plugin Integration](#plugin-integration)
10. [Database Storage](#database-storage)

## Device Discovery

netWORKS provides several methods for discovering devices on your network:

- **Network Scanner**: The built-in network scanner automatically discovers devices on your network through various scan types:
  - Quick Scan: Fast ping sweep of the network
  - Deep Scan: Comprehensive scan with port enumeration
  - Stealth Scan: Low-impact scan for sensitive environments

- **Plugin-based Discovery**: Additional plugins can provide specialized device discovery methods.

## Manual Device Addition

You can manually add devices that may not be automatically discovered:

### Adding a Device Manually

1. Right-click anywhere in the device table (even if it already contains devices)
2. Select "Add Device Manually" from the context menu
3. In the dialog that appears, enter the device information:
   - **IP Address** (required): The IP address of the device
   - **Hostname**: A name for the device (generated automatically if not provided)
   - **MAC Address**: The device's MAC address
   - **Status**: Set the device status (active, inactive, unknown)
   - **Alias**: A friendly name to identify the device easily

4. In the Additional Details section, you can also provide:
   - **OS**: Operating system information
   - **Notes**: Any additional information about the device

5. In the Custom Fields section, you can add any number of custom fields:
   - Click "Add Custom Field" to add a new field
   - Enter a field name and value
   - These fields will be stored in the device metadata

6. Click "Save" to add the device

Manually added devices are tracked with metadata that indicates they were added manually and when they were added.

## Device Editing

You can edit device properties to update information or correct errors:

### Editing Device Properties

1. Right-click on a device in the table
2. Select "Edit Device Properties" from the context menu
3. In the dialog that appears, modify any of the device properties:
   - **IP Address** (read-only): Cannot be modified as it's the primary identifier
   - **Hostname**: Update the hostname
   - **MAC Address**: Correct or update the MAC address
   - **Status**: Change the device status
   - **Alias**: Update the friendly name
   - **OS**: Update operating system information
   - **Notes**: Add or update additional notes

4. In the Custom Fields section, you can:
   - Edit existing custom fields
   - Add new custom fields by clicking "Add Custom Field"
   - These fields are stored in the device metadata

5. In the All Fields (Advanced) section, you can:
   - View and edit all raw device fields
   - Add new top-level fields to the device
   - This is an advanced feature and should be used with caution

6. Click "Save" to apply the changes

When a device is edited, a 'last_edited' timestamp is added to its metadata to track when changes were made.

## Custom Fields

netWORKS supports adding custom fields to devices for maximum flexibility:

### About Custom Fields

- Custom fields allow you to store any additional information about devices
- They are stored in the device's metadata
- They can be added during manual device addition or when editing devices
- Custom fields are preserved in the device database

### Uses for Custom Fields

- **Asset Management**: Track asset tags, purchase dates, warranty information
- **Location Data**: Building, floor, room, or rack location
- **Contact Information**: Department, owner, or responsible person
- **Technical Details**: Hardware specifications, software versions
- **Classification**: Security levels, network zones, or business criticality

### Adding Custom Fields to Multiple Devices

To efficiently add the same custom field to multiple devices:
1. Select each device individually
2. Edit its properties and add the custom field
3. Save the changes for each device

Plugins can also be developed to automate the process of adding custom fields to multiple devices.

## Multi-Selection

netWORKS supports multi-selection of devices in the device table, allowing you to perform operations on multiple devices at once:

### Using Multi-Selection

1. To select multiple devices, use the following methods:
   - Hold Ctrl (or Cmd on Mac) and click on devices to select/deselect individual devices
   - Hold Shift and click to select a range of devices
   - Click and drag to select multiple devices at once

2. Once multiple devices are selected, you can:
   - Remove all selected devices at once
   - Add all selected devices to a group
   - Perform plugin actions that support multi-device operations

### Multi-Device Operations

When multiple devices are selected, the context menu will show operations that can be performed on all selected devices. Individual device operations (like editing properties) will be disabled if more than one device is selected.

Plugins can register multi-device operations that appear in the context menu when multiple devices are selected. These operations receive the list of all selected device objects.

## Device Groups

netWORKS allows you to organize devices into logical groups for easier management and categorization:

### Creating and Managing Device Groups

1. To manage device groups, right-click anywhere in the device table and select "Manage Device Groups..."
2. In the dialog that appears, you can:
   - Create new groups using the "Add Group" button
   - Rename existing groups using the "Rename" button
   - Delete groups using the "Delete" button
   - Assign devices to groups by selecting a group and checking the devices to include

### Adding Devices to Groups

You can add devices to groups in several ways:

1. Through the Manage Device Groups dialog:
   - Select a group on the left
   - Check the devices you want to include in that group on the right

2. Through the context menu when devices are selected:
   - Select one or more devices in the table
   - Right-click and navigate to "Add to Group" submenu
   - Choose an existing group or create a new one

### Using Groups for Filtering and Organization

Device groups provide a way to:
- Organize devices by function, location, or any other category
- Perform operations on logical sets of devices
- Filter and view subsets of your network inventory

Groups are stored in the database and are preserved between sessions.

## Device Management

Once devices are added to netWORKS, you can manage them in several ways:

- **View Details**: Select a device to view its details in the bottom panel
- **Edit Properties**: Right-click a device and select "Edit Device Properties"
- **Remove Devices**: Right-click on a device and select "Remove Device"
- **Manage Aliases**: Set custom aliases for easier identification
- **Sort and Filter**: Sort the device table by any column, and filter for specific devices

## Device Details

The device details panel provides comprehensive information about selected devices:

- **Basic Information**: IP, hostname, MAC, status
- **Network Information**: Open ports, protocols, services
- **Activity Information**: First seen, last seen
- **Metadata**: OS, device type, vendor information
- **Notes**: Custom notes about the device

## Plugin Integration

Device information is accessible to plugins, allowing for extended functionality such as vulnerability scanning, monitoring, and more.

### Context Menu Integration for Plugins

Plugins can add their own device-specific actions to the context menu of the device table. When a device is right-clicked, the plugin's menu items will be displayed.

To register a plugin menu item:

```python
self.api.register_menu_item(
    label="My Plugin Action",
    callback=self.my_action_function,
    enabled_callback=lambda device: self.is_action_available(device),
    parent_menu="My Plugin"  # Optional group
)

def my_action_function(self, device):
    # Access device properties
    ip = device.get('ip')
    hostname = device.get('hostname')
    # Perform action with device
```

### Multi-Device Plugin Integration

Plugins can also register actions that operate on multiple selected devices:

```python
self.api.register_multi_device_menu_item(
    label="Process Selected Devices",
    callback=self.process_multiple_devices,
    parent_menu="My Plugin"  # Optional group
)

def process_multiple_devices(self, devices):
    # Devices is a list of all selected device dictionaries
    for device in devices:
        # Process each device
        ip = device.get('ip')
        # Perform batch operations
```

### Device Data Structure

Plugins working with devices should follow this standard data structure:

```python
device = {
    'id': str(uuid.uuid4()),  # Unique identifier
    'ip': '192.168.1.100',    # IP address (primary identifier)
    'hostname': 'device-100', # Hostname
    'mac': '00:11:22:33:44:55', # MAC address
    'first_seen': '2023-07-15 14:30:22', # First discovery timestamp
    'last_seen': '2023-07-15 14:30:22',  # Last discovery timestamp
    'status': 'active',       # Device status
    'metadata': {             # Extensible metadata
        'os': 'Windows 10',
        'notes': 'Custom notes',
        'discovery_source': 'plugin_name',
        'last_edited': '2023-07-16 09:45:12',
        'custom_field1': 'Custom value 1',  # Custom fields appear here
        'custom_field2': 'Custom value 2'   # Any number of custom fields can be added
    },
    'tags': ['server', 'production']  # Optional tags
}
```

Plugins can add their own custom fields to the metadata dictionary. When displaying devices, the UI will automatically show relevant metadata fields in the appropriate sections.

## Database Storage

netWORKS stores all device information in a SQLite database for persistence and efficient querying:

### Device Database Structure

The device database includes the following tables:

1. **devices**: Stores the core device information
   - **id**: Unique identifier for the device (UUID)
   - **ip**: IP address (primary identifier for user interaction)
   - **mac**: MAC address 
   - **hostname**: Device hostname
   - **vendor**: Device vendor/manufacturer
   - **os**: Operating system information
   - **first_seen**: Timestamp when the device was first discovered
   - **last_seen**: Timestamp when the device was last seen
   - **status**: Current status (active, inactive, etc.)
   - **metadata**: JSON-encoded metadata dictionary
   - **tags**: JSON-encoded array of device tags
   - **notes**: User notes about the device

2. **device_history**: Tracks historical events for devices
   - **id**: Unique event ID
   - **device_id**: Reference to the device ID
   - **ip**: IP address of the device
   - **event_type**: Type of event (discovery, update, deletion, etc.)
   - **event_data**: JSON-encoded event data
   - **timestamp**: When the event occurred

### Benefits of Database Storage

The database-based device management provides several benefits:

- **Persistence**: All device information is automatically stored and preserved
- **History Tracking**: Keep track of when devices were first discovered and last seen
- **Event History**: Full history of events related to each device
- **Efficient Searching**: Fast lookups and filtering based on any device property
- **Data Integrity**: Ensures all device data is properly stored and related

### Programmatic Access

Plugins can access the device database through the provided APIs:

```python
# Add or update a device in the database
device_manager.save_device({
    'ip': '192.168.1.100',
    'hostname': 'device-100',
    'mac': '00:11:22:33:44:55',
    'metadata': {'os': 'Windows 10'}
})

# Get a device by IP
device = device_manager.get_device('192.168.1.100')

# Get all devices
devices = device_manager.get_all_devices()

# Search for devices
search_results = device_manager.search_devices('windows')

# Get device history
history = device_manager.get_device_history('192.168.1.100')
``` 