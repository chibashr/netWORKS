# netWORKS Main Window API

This document outlines the API provided by the main window for plugin integration. It describes how plugins can interact with the main window, access core functionality, and integrate with the application's UI.

## Main Window

The main window is the primary interface for the application. Plugins can access it through the plugin API.

### Key Components

- **Main Window**: Central application window
- **Device Table**: Table showing all discovered devices
- **Left Panel**: Navigation and filtering panel
- **Right Panel**: Detail and property panel
- **Bottom Panel**: Log and output panel
- **Status Bar**: Information and progress display
- **Toolbar**: Quick access actions

## Accessing the Main Window

When your plugin is loaded, the main window reference is automatically provided through the `set_main_window` method in your plugin API:

```python
def set_main_window(self, main_window):
    self.main_window = main_window
    # Now you can access main window methods and properties
```

## API Version Compatibility

The netWORKS API may have different implementations and feature sets across versions. Always implement robust error handling and check for the existence of methods before using them:

```python
# Check if a method exists before calling it
if hasattr(self.api, 'register_menu'):
    # Use the method if available
    self.api.register_menu(...)
else:
    # Use an alternative approach or log a warning
    self.api.log("Using simplified menu registration", level="WARNING")
    # Implement fallback behavior
```

## Device Selection

### Device Selection Signals and Hooks

The application provides two mechanisms for receiving device selection events:

1. **Hook System**: Register a hook callback through the API
2. **Qt Signals**: Connect directly to device_selected signals

For maximum compatibility and reliability, use both approaches:

```python
# Register for device selection via the hook system
self.api.register_hook('device_select', self.on_device_selected)

# Also try to connect directly to the device selection signal
try:
    if hasattr(self.api, 'main_window') and hasattr(self.api.main_window, 'device_table'):
        if hasattr(self.api.main_window.device_table, 'device_selected'):
            # Connect directly to the signal
            self.api.main_window.device_table.device_selected.connect(self.on_device_selected)
except Exception as e:
    self.api.log(f"Error connecting to device selection signal: {str(e)}", level="ERROR")
```

### Handling Device Selection Events

Device selection events may provide different data types (dict or list):

```python
@Slot(object)
def on_device_selected(self, device):
    """Handle device selection events."""
    try:
        # Handle different data types
        if device is None:
            # No device selected
            self.current_device = None
        elif isinstance(device, dict):
            # Single device dictionary
            self.current_device = device
        elif isinstance(device, list) and len(device) > 0:
            # List of devices (take the first one)
            self.current_device = device[0] if isinstance(device[0], dict) else None
            
        # Update UI based on selected device
        self.update_ui_with_current_device()
    except Exception as e:
        self.api.log(f"Error handling device selection: {str(e)}", level="ERROR")
```

## Main Window Methods

### UI Integration

```python
# Register a panel in the specified location
main_window.register_panel(panel, location, name=None)
# location can be: "left", "right", "bottom", "central", "toolbar"

# Remove a panel from the UI
main_window.remove_panel(panel)

# Add a widget to the toolbar tab
main_window.add_toolbar_widget(widget, category="Tools")
# category determines which tab the widget is added to (e.g., "Home", "Tools", "View")

# Create a new tab in the ribbon-style toolbar
main_window.create_toolbar_tab(name)

# Toggle visibility of panels
main_window.toggle_left_panel(checked)
main_window.toggle_right_panel(checked)
main_window.toggle_bottom_panel(checked)
```

### Toolbar Integration (Ribbon Interface)

The application uses a Microsoft Office-style ribbon interface as its primary navigation system. The traditional dropdown menus have been replaced by this ribbon interface to provide better organization and visual access to functions.

#### Ribbon Structure

The ribbon toolbar consists of the following tabs by default:
- **Home**: Contains file operations and common actions
- **View**: Controls for panel visibility and display options
- **Tools**: Application utilities and tools
- **Plugins**: Plugin-specific functions
- **Help**: Documentation and support options

#### Adding Widgets to the Ribbon

To add a widget to the ribbon toolbar:

```python
# Create a button
from PySide6.QtWidgets import QPushButton
button = QPushButton("My Button")
button.clicked.connect(my_callback_function)

# Add the button to a specific tab and group
main_window.add_toolbar_widget(button, tab_name="Home", group_name="My Group")
```

If the specified tab or group doesn't exist, it will be created automatically.

#### Creating Organized Groups

For more organized toolbar layouts, you can create groups within tabs:

```python
# Create a group in a tab
group = main_window.create_toolbar_group("My Category", main_window.home_tab)

# Create a tool button for an action
from PySide6.QtWidgets import QToolButton
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt

action = QAction("My Action", main_window)
action.setIcon(QIcon("path/to/icon.png"))
action.triggered.connect(my_action_callback)

button = QToolButton()
button.setDefaultAction(action)
button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

# Add the button to the group
group.layout().addWidget(button)
```

Groups have a title and a contained set of buttons, similar to Microsoft Office's ribbon groups.

#### Plugin Integration with Ribbon

Plugins can register toolbar items through their initialization process:

```python
def initialize(self):
    # Get the main window reference
    main_window = self.api.get_main_window()
    
    # Check if required classes are available before using them
    try:
        from PySide6.QtWidgets import QToolButton
        from PySide6.QtGui import QAction, QIcon
        from PySide6.QtCore import Qt
        
        # Create a tool button
        action = QAction("Plugin Function", main_window)
        action.setIcon(QIcon("path/to/icon.png"))
        action.triggered.connect(self.my_function)
        
        button = QToolButton()
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        
        # Add the button to an existing or new tab/group
        main_window.add_toolbar_widget(button, "Plugins", "My Plugin")
    except Exception as e:
        self.api.log(f"Error creating toolbar button: {str(e)}", level="ERROR")
```

#### Best Practices for Ribbon Integration

1. **Use appropriate icons** for all buttons to improve visual recognition
2. **Group related functions** together in meaningful categories
3. **Use clear, concise labels** for buttons (verb-noun format works well)
4. **Follow the design language** of the application for consistency
5. **Organize by frequency of use** - most common functions should be in the Home tab

### Database Access

The main window provides access to the device database manager, but implementations may vary:

```python
# Get the database manager
db_manager = main_window.database_manager

# Verify database methods are available before using them
if hasattr(db_manager, 'execute_query'):
    # Use execute_query method for database operations
    db_manager.execute_query(
        "INSERT INTO devices (ip, mac, hostname) VALUES (?, ?, ?)",
        ['192.168.1.1', '00:11:22:33:44:55', 'router']
    )
elif hasattr(db_manager, 'add_device'):
    # Use add_device method as alternative
    db_manager.add_device({
        'ip': '192.168.1.1',
        'mac': '00:11:22:33:44:55',
        'hostname': 'router',
        'vendor': 'Cisco',
        'metadata': {
            'custom_field': 'value'
        }
    })
else:
    # Log warning that database operations are not available
    self.api.log("Database operations not supported in this version", level="WARNING")

# Access plugin-specific storage (if available)
try:
    # Store plugin-specific data
    db_manager.store_plugin_data('my-plugin-id', 'key', value)

    # Retrieve plugin-specific data
    data = db_manager.get_plugin_data('my-plugin-id', 'key', default=None)
except Exception as e:
    self.api.log(f"Plugin data storage not available: {str(e)}", level="ERROR")
```

### Progress Display

```python
# Show or hide the progress bar
main_window.show_progress(True)

# Update progress value
main_window.update_progress(value, maximum=None)
```

### Dialog and Notifications

```python
# Show an error dialog
main_window.show_error_dialog(title, message)
```

## Device Management

Plugins can interact with the device table through the main window's device_table property:

```python
try:
    # Access the device table (always check if it exists)
    if hasattr(main_window, 'device_table'):
        device_table = main_window.device_table
        
        # Add a device to the table
        device_table.add_device(device_data)
        
        # Refresh the device table
        device_table.refresh()
        
        # Get selected devices
        selected_devices = device_table.get_selected_devices()
    else:
        self.api.log("Device table not available", level="WARNING")
except Exception as e:
    self.api.log(f"Error accessing device table: {str(e)}", level="ERROR")
```

## Configuration Access

The main window provides access to application configuration:

```python
# Access the configuration
config = main_window.config

# Get a specific configuration value
theme = main_window.config["app"]["theme"]

# Save configuration changes
main_window.save_config()
```

## Adding Menu Items

Plugins can add items to the main menu:

```python
try:
    # Check if register_menu method is available
    if hasattr(self.api, 'register_menu'):
        # Create a submenu
        self.api.register_menu(
            label="My Plugin",
            parent_menu="Tools"
        )
        
        # Add items to the submenu
        self.api.register_menu_item(
            label="My Action",
            callback=self.my_action_handler,
            parent_menu="Tools/My Plugin"
        )
    else:
        # Fallback to direct menu access
        menu = main_window.menus.get("tools")
        if menu:
            # Add action to menu
            from PySide6.QtGui import QAction
            action = QAction("My Plugin Action", main_window)
            action.triggered.connect(self.my_action_handler)
            menu.addAction(action)
            
            # Store reference to action for later removal
            self.menu_actions["my_action"] = action
except Exception as e:
    self.api.log(f"Error registering menu items: {str(e)}", level="ERROR")
```

## Best Practices

1. **Always check if components exist before using them**:
   ```python
   if hasattr(main_window, 'device_table'):
       main_window.device_table.refresh()
   ```

2. **Implement robust error handling**:
   ```python
   try:
       # Attempt to use a feature that might not be available
       self.api.register_context_menu_item(...)
   except Exception as e:
       self.api.log(f"Error registering context menu: {str(e)}", level="ERROR")
       # Implement fallback behavior if needed
   ```

3. **Use proper thread handling for UI operations**:
   - UI operations should always happen on the main thread
   - Use Qt signals and slots for cross-thread communication
   - See the threading documentation for more details

4. **Clean up resources when your plugin is disabled or unloaded**:
   - Remove UI components you've added
   - Disconnect signals
   - Release any resources your plugin has acquired

5. **Store plugin-specific data using the database manager**:
   - Use the plugin_data table for persistent storage
   - Don't modify application tables directly

6. **Connect to both hook system and direct signals** for critical events:
   ```python
   # Register hook
   self.api.register_hook('device_select', self.on_device_select)
   
   # Also connect to signal
   if hasattr(self.main_window, 'device_table'):
       if hasattr(self.main_window.device_table, 'device_selected'):
           self.main_window.device_table.device_selected.connect(self.on_device_select)
   ```

## Example Plugin Integration

```python
class MyPlugin:
    def __init__(self):
        self.api = None
        self.main_window = None
        self.panel = None
        self.menu_actions = {}
        self.current_device = None
        
    def initialize(self, plugin_api):
        self.api = plugin_api
        self.api.on_main_window_ready(self.set_main_window)
        self.register_hooks()
        
    def register_hooks(self):
        # Register for device selection events
        self.api.register_hook('device_select', self.on_device_select)
        
    def set_main_window(self, main_window):
        self.main_window = main_window
        self.setup_ui()
        
        # Connect to device table signals directly when available
        try:
            if hasattr(main_window, 'device_table'):
                if hasattr(main_window.device_table, 'device_selected'):
                    main_window.device_table.device_selected.connect(self.on_device_select)
        except Exception as e:
            self.api.log(f"Error connecting to device signals: {str(e)}", level="ERROR")
        
    def on_device_select(self, device):
        """Handle device selection events from both hooks and signals."""
        try:
            if device is None:
                self.current_device = None
            elif isinstance(device, dict):
                self.current_device = device
                self.api.log(f"Selected device: {device.get('ip')}")
            elif isinstance(device, list) and len(device) > 0:
                self.current_device = device[0]
                self.api.log(f"Selected first device from list: {device[0].get('ip')}")
            
            # Update UI based on device selection
            self.update_ui_with_device()
        except Exception as e:
            self.api.log(f"Error processing device selection: {str(e)}", level="ERROR")
    
    def update_ui_with_device(self):
        """Update UI elements with the current device information."""
        if self.panel:
            try:
                if self.current_device:
                    # Update UI with device information
                    device_info = f"Device: {self.current_device.get('hostname', 'Unknown')} ({self.current_device.get('ip', 'Unknown IP')})"
                    self.device_label.setText(device_info)
                    # Enable device-specific actions
                    self.connect_button.setEnabled(True)
                else:
                    # Clear UI when no device is selected
                    self.device_label.setText("No device selected")
                    # Disable device-specific actions
                    self.connect_button.setEnabled(False)
            except Exception as e:
                self.api.log(f"Error updating UI: {str(e)}", level="ERROR")
        
    def setup_ui(self):
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
        
        # Create and register a panel
        self.panel = QWidget()
        layout = QVBoxLayout(self.panel)
        
        # Create device info label
        self.device_label = QLabel("No device selected")
        layout.addWidget(self.device_label)
        
        # Add a button
        self.connect_button = QPushButton("Connect to Device")
        self.connect_button.clicked.connect(self.connect_to_device)
        self.connect_button.setEnabled(False)  # Disabled until device selected
        layout.addWidget(self.connect_button)
        
        # Register the panel
        try:
            self.main_window.register_panel(self.panel, "right", "My Plugin")
        except Exception as e:
            self.api.log(f"Error registering panel: {str(e)}", level="ERROR")
    
    def connect_to_device(self):
        """Connect to the selected device."""
        if self.current_device:
            self.api.log(f"Connecting to {self.current_device.get('ip')}")
            # Device connection logic here
    
    def cleanup(self):
        """Clean up resources when plugin is unloaded."""
        # Remove panel
        if self.panel and self.main_window:
            try:
                self.main_window.remove_panel(self.panel)
            except Exception:
                pass
            self.panel = None
        
        # Remove menu actions
        if self.main_window and hasattr(self.main_window, 'menus'):
            menu = self.main_window.menus.get("tools")
            if menu:
                for action in self.menu_actions.values():
                    try:
                        menu.removeAction(action)
                    except Exception:
                        pass
        self.menu_actions = {}
        
        # Disconnect signals
        if self.main_window and hasattr(self.main_window, 'device_table'):
            try:
                if hasattr(self.main_window.device_table, 'device_selected'):
                    self.main_window.device_table.device_selected.disconnect(self.on_device_select)
            except Exception:
                pass
``` 