# Multi-Device Operations in NetWORKS

This document provides guidance on working with multiple devices simultaneously in NetWORKS, a feature available since version 0.5.4.

## Table of Contents

- [Selection Mechanisms](#selection-mechanisms)
- [Device Manager Selection API](#device-manager-selection-api)
- [Handling Multiple Selections in UI](#handling-multiple-selections-in-ui)
- [Group Management with Multiple Devices](#group-management-with-multiple-devices)
- [Context Menu with Multiple Selection](#context-menu-with-multiple-selection)
- [Plugin Development for Multi-Device Support](#plugin-development-for-multi-device-support)

## Selection Mechanisms

NetWORKS supports the following mechanisms for selecting multiple devices:

- **Ctrl+Click**: Toggles selection of a single device
- **Shift+Click**: Selects a range of devices between the last selected and the current
- **Select All**: Selects all devices in the current view
- **Deselect All**: Clears the current selection

## Device Manager Selection API

The Device Manager provides the following methods for working with device selection:

```python
# Select a device (exclusive=True clears previous selection)
device_manager.select_device(device, exclusive=False)

# Deselect a device
device_manager.deselect_device(device)

# Clear all selections
device_manager.clear_selection()

# Get currently selected devices (returns a list)
selected_devices = device_manager.get_selected_devices()
```

The `selection_changed` signal is emitted whenever the selection changes:

```python
# Connect to the selection_changed signal
device_manager.selection_changed.connect(self.on_selection_changed)

def on_selection_changed(self, devices):
    """Handle selection change
    
    Args:
        devices: List of selected devices
    """
    # Handle the selection change
    num_selected = len(devices)
    if num_selected == 0:
        print("No devices selected")
    elif num_selected == 1:
        print(f"Single device selected: {devices[0].get_property('alias')}")
    else:
        print(f"Multiple devices selected: {num_selected}")
```

## Handling Multiple Selections in UI

When multiple devices are selected, UI components should adapt their behavior:

- **Properties Panel**: Show common properties or multi-select mode
- **Device Details**: Show summary information or multi-device view
- **Actions**: Enable/disable based on whether they support multiple devices

Example of adapting a UI component to handle multiple selection:

```python
def update_properties_panel(self, devices):
    """Update the properties panel based on selection
    
    Args:
        devices: List of selected devices
    """
    self.properties_panel.clear()
    
    if not devices:
        self.properties_panel.show_empty_state()
        return
        
    if len(devices) == 1:
        # Single device selected - show all properties
        device = devices[0]
        self.properties_panel.show_device_properties(device)
    else:
        # Multiple devices selected - show common properties
        self.properties_panel.show_common_properties(devices)
```

## Group Management with Multiple Devices

NetWORKS supports adding and removing multiple devices to/from groups:

### Adding Multiple Devices to a Group

```python
def add_devices_to_group(self, devices, group):
    """Add multiple devices to a group
    
    Args:
        devices: List of devices to add
        group: Target group
    
    Returns:
        int: Number of devices successfully added
    """
    success_count = 0
    
    for device in devices:
        if self.device_manager.add_device_to_group(device, group):
            success_count += 1
            
    return success_count
```

### Removing Multiple Devices from a Group

```python
def remove_devices_from_group(self, devices, group):
    """Remove multiple devices from a group
    
    Args:
        devices: List of devices to remove
        group: Source group
    
    Returns:
        int: Number of devices successfully removed
    """
    success_count = 0
    
    for device in devices:
        if self.device_manager.remove_device_from_group(device, group):
            success_count += 1
            
    return success_count
```

## Context Menu with Multiple Selection

When implementing context menu actions, always handle both single and multiple device selections:

```python
def on_context_menu_requested(self, devices, menu):
    """Handle context menu request
    
    Args:
        devices: List of selected devices
        menu: QMenu instance
    """
    if not devices:
        return
        
    # Add action based on selection count
    if len(devices) == 1:
        device = devices[0]
        action = menu.addAction(f"Configure {device.get_property('alias')}")
        action.triggered.connect(lambda: self.configure_device(device))
    else:
        action = menu.addAction(f"Configure {len(devices)} devices")
        action.triggered.connect(lambda: self.configure_devices(devices))
```

For lambda functions in menu actions with multiple device selections, always use proper variable capture:

```python
# INCORRECT - 'group' will be the last value from the loop for all actions
for group in groups:
    action = menu.addAction(f"Add to {group.name}")
    action.triggered.connect(lambda: self.add_to_group(devices, group))

# CORRECT - Use default arguments to properly capture the current value
for group in groups:
    action = menu.addAction(f"Add to {group.name}")
    action.triggered.connect(lambda g=group: self.add_to_group(devices, g))
```

## Plugin Development for Multi-Device Support

When developing plugins that interact with devices, consider these guidelines:

### 1. Always Check for Multiple Devices

```python
def handle_devices(self, device_or_devices):
    """Handle one or more devices
    
    Args:
        device_or_devices: Single device or list of devices
    """
    # Normalize to a list
    devices = []
    
    if isinstance(device_or_devices, list):
        devices = device_or_devices
    elif device_or_devices:
        devices = [device_or_devices]
    
    # Process each device
    for device in devices:
        self.process_device(device)
```

### 2. Provide Feedback for Multi-Device Operations

Always provide appropriate feedback when operations complete:

```python
def configure_devices(self, devices):
    """Configure multiple devices
    
    Args:
        devices: List of devices to configure
    """
    success_count = 0
    failed_count = 0
    
    for device in devices:
        try:
            if self.configure_single_device(device):
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"Error configuring device {device.id}: {e}")
            failed_count += 1
    
    # Provide feedback
    if failed_count == 0:
        QMessageBox.information(
            self.main_window,
            "Configuration Complete",
            f"Successfully configured all {success_count} devices."
        )
    else:
        QMessageBox.warning(
            self.main_window,
            "Configuration Partial",
            f"Configured {success_count} devices. Failed to configure {failed_count} devices."
        )
```

### 3. Connect to Appropriate Signals

Make sure to connect to the `selection_changed` signal to respond to user selection changes:

```python
def initialize(self):
    # Connect to selection_changed signal
    self.device_manager.selection_changed.connect(self.on_selection_changed)
    
    return True

def on_selection_changed(self, devices):
    """Handle selection change
    
    Args:
        devices: List of selected devices
    """
    # Update UI based on selection
    self.update_actions_enabled_state(devices)
```

### 4. Batch Operations for Performance

When working with many devices, consider batching operations for better performance:

```python
def scan_devices(self, devices):
    """Scan multiple devices
    
    Args:
        devices: List of devices to scan
    """
    # Process in batches to avoid UI locking
    batch_size = 10
    total_devices = len(devices)
    processed = 0
    
    # Show progress dialog
    progress = QProgressDialog("Scanning devices...", "Cancel", 0, total_devices, self.main_window)
    progress.setWindowModality(Qt.WindowModal)
    
    for i in range(0, total_devices, batch_size):
        # Process a batch
        batch = devices[i:min(i+batch_size, total_devices)]
        self.scan_batch(batch)
        
        # Update progress
        processed += len(batch)
        progress.setValue(processed)
        
        # Check for cancellation
        if progress.wasCanceled():
            break
    
    progress.close()
```

### 5. Proper Error Handling

Handle errors gracefully to prevent one device failure from affecting others:

```python
def process_devices(self, devices):
    """Process multiple devices with error isolation
    
    Args:
        devices: List of devices to process
    """
    results = {"success": [], "failed": []}
    
    for device in devices:
        try:
            self.process_device(device)
            results["success"].append(device)
        except Exception as e:
            logger.error(f"Error processing device {device.id}: {e}")
            results["failed"].append((device, str(e)))
    
    return results
``` 