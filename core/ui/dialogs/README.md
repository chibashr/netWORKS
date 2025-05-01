# Dialog Functions Module

This module contains functions related to dialog management in the netWORKS application.

## Functions

### `show_error_dialog(main_window, title, message)`

Shows an error dialog with the specified title and message.

Parameters:
- `main_window`: Reference to the main window instance
- `title`: str - Title of the error dialog
- `message`: str - Error message to display

## Usage

```python
from core.ui.dialogs import show_error_dialog

# Show an error dialog
show_error_dialog(main_window, "Connection Error", "Failed to connect to the device.")
``` 