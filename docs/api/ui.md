# NetWORKS UI API Documentation

This document provides detailed information about the UI components of NetWORKS that plugins can interact with.

## Table of Contents

- [Main Window](#main-window)
- [Device Table](#device-table)
- [Device Tree](#device-tree)
- [UI Extension Points](#ui-extension-points)

## Main Window

The `MainWindow` class is the primary window of the application. Plugins can access it through `self.main_window`.

```python
class MainWindow:
    # Properties
    app: Application                    # Application instance
    device_manager: DeviceManager       # Device manager instance
    plugin_manager: PluginManager       # Plugin manager instance
    config: Config                      # Configuration manager instance
    
    # UI Components
    toolbar: QToolBar                   # Main toolbar
    menu_bar: QMenuBar                  # Main menu bar
    status_bar: QStatusBar              # Status bar
    device_table: DeviceTableView       # Device table view
    device_tree: DeviceTreeView         # Device tree view
    central_widget: QWidget             # Central widget
    properties_widget: QTabWidget       # Properties panel
    
    # Dock Widgets
    dock_device_tree: QDockWidget       # Device tree dock widget
    dock_properties: QDockWidget        # Properties dock widget
    dock_log: QDockWidget               # Log dock widget
    
    # Methods
    def update_status_bar()             # Update status bar with current counts
    def add_plugin_ui_components(self, plugin_info)  # Add UI components from a plugin
    def remove_plugin_ui_components(self, plugin_info)  # Remove UI components from a plugin
```

## Device Table

The `DeviceTableModel` and `DeviceTableView` classes provide the device table functionality.

```python
class DeviceTableModel:
    # Methods
    def refresh_devices()               # Refresh the device list
    def add_column(self, header, key, callback=None): bool  # Add a column to the table
    def remove_column(self, header): bool  # Remove a column from the table
```

```python
class DeviceTableView:
    # Signals
    double_clicked: Signal(object)      # Emitted when a device is double-clicked
```

## Device Tree

The `DeviceTreeModel` and `DeviceTreeView` classes provide the device tree functionality.

```python
class DeviceTreeView:
    # Signals
    device_double_clicked: Signal(object)  # Emitted when a device is double-clicked
```

## UI Extension Points

Plugins can extend the UI in several ways by implementing methods in the `PluginInterface`:

### Toolbar Actions

```python
def get_toolbar_actions() -> list:
    """
    Get actions to be added to the toolbar
    
    Returns:
        list: List of QAction objects
    """
```

Example:
```python
def get_toolbar_actions(self):
    action = QAction("My Action", self)
    action.triggered.connect(self.on_my_action)
    return [action]
```

### Menu Actions

```python
def get_menu_actions() -> dict:
    """
    Get actions to be added to the menu
    
    Returns:
        dict: Dictionary mapping menu names to lists of QAction objects
    """
```

Example:
```python
def get_menu_actions(self):
    action = QAction("My Menu Action", self)
    action.triggered.connect(self.on_my_menu_action)
    return {"My Menu": [action]}
```

### Device Panels

```python
def get_device_panels() -> list:
    """
    Get panels to be added to the device properties view
    
    Returns:
        list: List of (panel_name, widget) tuples
    """
```

Example:
```python
def get_device_panels(self):
    panel = QWidget()
    # Configure panel...
    return [("My Panel", panel)]
```

### Device Table Columns

```python
def get_device_table_columns() -> list:
    """
    Get columns to be added to the device table
    
    Returns:
        list: List of (column_id, column_name, callback) tuples
              where callback is a function that takes a device and returns the value
    """
```

Example:
```python
def get_device_table_columns(self):
    def get_my_value(device):
        return device.get_property("my_property", "N/A")
    return [("my_column", "My Column", get_my_value)]
```

### Device Context Menu Actions

```python
def get_device_context_menu_actions() -> list:
    """
    Get actions to be added to the device context menu
    
    Returns:
        list: List of QAction objects
    """
```

### Device Tabs

```python
def get_device_tabs() -> list:
    """
    Get tabs to be added to the device details view
    
    Returns:
        list: List of (tab_name, widget) tuples
    """
```

### Dock Widgets

```python
def get_dock_widgets() -> list:
    """
    Get dock widgets to be added to the main window
    
    Returns:
        list: List of (widget_name, widget, area) tuples
              where area is one of Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea,
              Qt.TopDockWidgetArea, or Qt.BottomDockWidgetArea
    """
```

Example:
```python
def get_dock_widgets(self):
    dock_widget = QWidget()
    # Configure dock widget...
    return [("My Dock", dock_widget, Qt.RightDockWidgetArea)]
```

### Settings Pages

```python
def get_settings_pages() -> list:
    """
    Get settings pages to be added to the settings dialog
    
    Returns:
        list: List of (page_name, widget) tuples
    """
``` 