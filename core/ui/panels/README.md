# Panel Functions Module

This module contains functions related to panel management in the netWORKS application.

## Functions

### `register_panel(main_window, panel, location, name=None)`

Registers a panel widget in the specified location.

Parameters:
- `main_window`: Reference to the main window instance
- `panel`: QWidget - The panel to register
- `location`: str - Where to register the panel ("left", "right", "bottom")
- `name`: str - Optional name for the panel

Returns:
- `bool`: True if registration was successful

### `remove_panel(main_window, panel)`

Removes a panel from the UI.

Parameters:
- `main_window`: Reference to the main window instance
- `panel`: QWidget - The panel to remove

Returns:
- `bool`: True if removal was successful

### `toggle_left_panel(main_window, checked)`

Toggles the visibility of the left panel.

Parameters:
- `main_window`: Reference to the main window instance
- `checked`: bool - Whether the panel should be visible

### `toggle_right_panel(main_window, checked)`

Toggles the visibility of the right panel.

Parameters:
- `main_window`: Reference to the main window instance
- `checked`: bool - Whether the panel should be visible

### `toggle_bottom_panel(main_window, checked)`

Toggles the visibility of the bottom panel.

Parameters:
- `main_window`: Reference to the main window instance
- `checked`: bool - Whether the panel should be visible

### `refresh_plugin_panels(main_window)`

Refreshes all plugin panels in the UI.

Parameters:
- `main_window`: Reference to the main window instance

Returns:
- `bool`: True if refresh was successful

## Usage

```python
from core.ui.panels import (
    register_panel, remove_panel, toggle_left_panel,
    toggle_right_panel, toggle_bottom_panel, refresh_plugin_panels
)

# Register a new panel in the right sidebar
register_panel(main_window, my_panel, "right", "My Custom Panel")

# Toggle panel visibility
toggle_left_panel(main_window, True)  # Show left panel
toggle_bottom_panel(main_window, False)  # Hide bottom panel

# Refresh all plugin panels
refresh_plugin_panels(main_window)
``` 