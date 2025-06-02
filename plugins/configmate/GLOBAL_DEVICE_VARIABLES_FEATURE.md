# Global vs Device Variables & Multi-Device Preview

## Overview

The ConfigMate plugin now supports **Global Variables** and **Device Variables** to provide more flexible and efficient template management for network engineers.

## Features Implemented

### 1. Global vs Device Variables

#### Global Variables
- **Purpose**: Variables that apply to **all devices** using the template
- **Examples**: Passwords, SNMP communities, NTP servers, DNS servers, domain names, banners
- **UI**: Blue-bordered fields in the "Global Variables" section
- **Behavior**: Set once, applied to all devices

#### Device Variables  
- **Purpose**: Variables that are **specific to each device**
- **Examples**: Hostnames, IP addresses, interface names, VLANs, MAC addresses
- **UI**: Green-bordered fields in the "Device Variables" section
- **Behavior**: Can be different for each device, auto-filled from device properties

### 2. Multi-Device Preview

#### Preview Options
- **All Devices**: Shows configuration preview for all selected devices
- **Individual Device**: Shows preview for a specific selected device
- **Device Selector**: Dropdown to choose which device(s) to preview

#### Auto-Fill Functionality
- Device variables automatically populated from device properties
- Smart mapping: hostname → device name, ip_address → device IP, etc.
- Manual override: Users can still manually enter values

## Technical Implementation

### Template Manager Updates

```python
class Template:
    def __init__(self, ..., global_variables=None, device_variables=None):
        self.global_variables = global_variables or {}
        self.device_variables = device_variables or {}
        
    def render(self, global_variables=None, device_variables=None):
        # Combines variables with precedence: device > global > template defaults
```

### Variable Detection

```python
class VariableCandidate:
    def __init__(self, ..., variable_type="device"):
        self.variable_type = variable_type  # "global" or "device"
```

**Automatic Categorization Patterns:**
- **Global**: password, secret, community, domain, ntp_server, dns_server, timezone, contact
- **Device**: hostname, ip_address, interface, vlan_id, mac_address, location

### Config Preview Widget

#### UI Structure
```
ConfigMate
├── Template Selection
├── Device Selection (Multi-device support)
├── Variables
│   ├── Global Variables (blue border)
│   │   ├── SNMP_COMMUNITY
│   │   ├── NTP_SERVER
│   │   └── DOMAIN_NAME
│   ├── ─────────────────
│   └── Device Variables (green border)
│       ├── HOSTNAME
│       ├── IP_ADDRESS
│       └── MGMT_INTERFACE
├── Configuration Preview
│   ├── Preview for: [All Devices ▼]
│   └── [Preview Text Area]
└── [Generate] [Apply]
```

#### Multi-Device Preview Logic
```python
def _update_preview(self):
    if selected_preview_device == "All Devices":
        # Show preview for all devices with device-specific variables
        for device in selected_devices:
            device_vars = get_device_specific_variables(device)
            combined_vars = {**global_variables, **device_vars}
            config = generate_config(device, template, combined_vars)
    else:
        # Show preview for specific device
```

## Usage Workflow

### 1. Template Creation
1. Create template with variables (e.g., `{{ hostname }}`, `{{ snmp_community }}`)
2. Variables automatically categorized as global or device-specific
3. Template stores both types separately

### 2. Configuration Generation
1. Select template from dropdown
2. Select multiple devices from device table
3. Fill global variables (apply to all devices)
4. Fill device variables (per device, with auto-fill option)
5. Preview configurations for all devices or individual devices
6. Generate and apply configurations

### 3. Variable Auto-Fill
- Device variables automatically populated from device properties
- Smart mapping based on variable names
- Manual override capability

## Benefits

### For Network Engineers
- **Efficiency**: Set global settings once for all devices
- **Consistency**: Ensure uniform global settings across infrastructure
- **Flexibility**: Customize device-specific settings per device
- **Preview**: See exactly what will be generated before applying

### For Template Management
- **Organization**: Clear separation of global vs device-specific settings
- **Reusability**: Templates work across different device sets
- **Maintenance**: Easy to update global settings for all devices

## Example Use Case

### Scenario: Configuring 10 Switches

**Global Variables (set once):**
- SNMP_COMMUNITY: "readonly123"
- NTP_SERVER: "10.1.1.100"
- DNS_SERVER: "8.8.8.8"
- DOMAIN_NAME: "company.local"

**Device Variables (per device):**
- HOSTNAME: SW01, SW02, SW03, etc.
- IP_ADDRESS: 10.1.1.10, 10.1.1.11, 10.1.1.12, etc.
- MGMT_INTERFACE: GigabitEthernet0/0

**Result:**
- All 10 switches get the same SNMP, NTP, DNS, and domain settings
- Each switch gets its unique hostname and IP address
- Preview shows all 10 configurations before applying

## File Changes

### Core Files Modified
- `plugins/configmate/core/template_manager.py` - Global/device variable support
- `plugins/configmate/core/variable_detector.py` - Variable categorization
- `plugins/configmate/ui/config_preview_widget.py` - Multi-device UI

### New Features Added
- Variable type classification (global vs device)
- Multi-device preview with device selector
- Auto-fill device variables from device properties
- Visual distinction (blue/green borders) for variable types
- Template backward compatibility

## Future Enhancements

### Potential Improvements
- **Group Variables**: Variables that apply to device groups
- **Variable Templates**: Predefined variable sets for common scenarios
- **Bulk Import**: Import device variables from CSV/Excel
- **Variable Validation**: Ensure required variables are filled
- **Configuration Diff**: Compare generated configs before applying

This implementation provides a solid foundation for efficient network device configuration management while maintaining the flexibility needed for diverse network environments. 