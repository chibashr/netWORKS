# Table Functions Module

This module contains functions related to table management in the netWORKS application.

## Functions

### `customize_table_columns(main_window)`

Shows a dialog for customizing which columns are displayed in the device table.

Parameters:
- `main_window`: Reference to the main window instance

Returns:
- `bool`: True if changes were applied, False otherwise

### `manage_device_aliases(main_window)`

Shows a dialog for setting custom aliases for network devices.

Parameters:
- `main_window`: Reference to the main window instance

Returns:
- `bool`: True if changes were applied, False otherwise

## Usage

```python
from core.ui.table import customize_table_columns, manage_device_aliases

# Show the column customization dialog
customize_table_columns(main_window)

# Show the device aliases management dialog
manage_device_aliases(main_window)
``` 