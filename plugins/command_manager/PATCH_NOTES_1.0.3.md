# Command Manager Plugin - Patch 1.0.3

## New Features

### Command Search Functionality

The Command Manager now includes a search box above the command table, allowing you to quickly find commands by typing any part of their name, command text, or description:

- **Real-time filtering**: Commands are filtered as you type
- **Case-insensitive**: Search is not case-sensitive
- **Multi-field search**: Searches across the alias, command text, and description columns

### Custom Command Support

You can now run custom commands directly from the Command Manager interface without needing to create a command set:

- **Custom command input field**: Enter any command to run it on selected devices
- **Custom command safety**: Option to restrict commands to read-only "show" commands
- **Safety confirmation**: Warning prompt when attempting to run non-show commands

## Safety Features

### Show Command Validation

To prevent accidental configuration changes, the Custom Command feature includes safety measures:

- **"Show-only" checkbox**: When enabled, only allows commands starting with "show"
- **Confirmation dialog**: If a non-show command is entered, displays a warning with details about potential risks
- **Default protection**: The show-only mode is enabled by default

## Technical Implementation

### Command Search

```python
def _on_search_commands(self, text):
    search_text = text.lower().strip()
    
    # Show all rows if search is empty
    if not search_text:
        for row in range(self.command_table.rowCount()):
            self.command_table.setRowHidden(row, False)
        return
    
    # Hide rows that don't match the search
    for row in range(self.command_table.rowCount()):
        match_found = False
        
        # Check all columns
        for col in range(self.command_table.columnCount()):
            item = self.command_table.item(row, col)
            if item and search_text in item.text().lower():
                match_found = True
                break
        
        # Show or hide the row
        self.command_table.setRowHidden(row, not match_found)
```

### Custom Command Implementation

```python
# Check if it's a show command if the checkbox is checked
if self.show_only_check.isChecked() and not command_text.lower().startswith("show "):
    # Ask for confirmation
    result = QMessageBox.warning(
        self,
        "Non-Show Command",
        f"The command '{command_text}' does not start with 'show'. "
        f"Non-show commands may modify device configuration.\n\n"
        f"Are you sure you want to run this command?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    
    if result != QMessageBox.Yes:
        return
```

## Compatibility

This patch requires NetWORKS core version 0.8.16 or higher. No configuration changes are needed; the update will automatically apply when the plugin is loaded. 