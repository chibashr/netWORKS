# Log Viewer Plugin API

This document describes the API provided by the Log Viewer plugin for integration with other plugins or components.

## Exported Functions

### open_log_viewer()

Opens the log viewer dialog to display and filter logs.

**Parameters:** None

**Returns:** None

**Example:**
```python
# Get the Log Viewer plugin
log_viewer_plugin = plugin_api.get_plugin("log-viewer")

# Open the log viewer dialog
log_viewer_plugin.open_log_viewer()
```

### get_logs(filter_criteria=None)

Retrieves log entries from the system, optionally filtered by the provided criteria.

**Parameters:**
- `filter_criteria` (dict, optional): A dictionary containing filter criteria with the following optional keys:
  - `level` (str): Filter by log level (e.g., "INFO", "ERROR")
  - `source` (str): Filter by log source/logger name (regex pattern supported)
  - `date_from` (datetime): Include logs from this date/time forward
  - `date_to` (datetime): Include logs up to this date/time
  - `message` (str): Filter by message content (regex pattern supported)

**Returns:**
- List of dictionaries, each representing a log entry with the following structure:
  ```python
  {
      "timestamp": "YYYY-MM-DD HH:MM:SS,SSS",
      "level": "INFO|WARNING|ERROR|DEBUG|CRITICAL",
      "source": "logger_name",
      "message": "Log message content",
      "file": "source_log_file_name",
      "exception": "Full exception traceback if available"
  }
  ```

**Example:**
```python
# Get the Log Viewer plugin
log_viewer_plugin = plugin_api.get_plugin("log-viewer")

# Get logs with basic filtering
import datetime
logs = log_viewer_plugin.get_logs({
    "level": "ERROR",
    "date_from": datetime.datetime.now() - datetime.timedelta(days=1),
    "source": "netWORKS"
})

# Process the logs
for log in logs:
    print(f"{log['timestamp']} - {log['level']} - {log['message']}")
```

### download_logs(log_entries, file_path)

Saves the provided log entries to a file in either text or JSON format.

**Parameters:**
- `log_entries` (list): List of log entry dictionaries (as returned by `get_logs()`)
- `file_path` (str): Path where to save the log file. If the path ends with `.json`, the logs will be saved in JSON format; otherwise, they will be saved in text format.

**Returns:**
- `bool`: True if the logs were successfully saved, False otherwise.

**Example:**
```python
# Get the Log Viewer plugin
log_viewer_plugin = plugin_api.get_plugin("log-viewer")

# Get error logs
logs = log_viewer_plugin.get_logs({"level": "ERROR"})

# Save logs to a file
success = log_viewer_plugin.download_logs(logs, "error_logs.log")
if success:
    print("Logs saved successfully")
else:
    print("Failed to save logs")
```

## Integration with Other Plugins

Other plugins can use the Log Viewer API to programmatically access logs and perform advanced operations:

### Example: Generating Error Reports

```python
def generate_error_report(self):
    # Get the Log Viewer plugin
    log_viewer_plugin = self.api.get_plugin("log-viewer")
    
    # Get error logs from the last 24 hours
    import datetime
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    
    error_logs = log_viewer_plugin.get_logs({
        "level": "ERROR",
        "date_from": yesterday
    })
    
    # Generate and save the report
    report_path = "error_report.json"
    log_viewer_plugin.download_logs(error_logs, report_path)
    
    # Open the log viewer to show the errors
    log_viewer_plugin.open_log_viewer()
    
    return report_path
``` 