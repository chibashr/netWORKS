# Log Viewer Plugin

This plugin adds a log viewer tool to netWORKS, allowing users to view, filter, and download application logs.

## Features

- View all application logs in a centralized location
- Filter logs by:
  - Log level (INFO, WARNING, ERROR, DEBUG, CRITICAL)
  - Timestamp/date range
  - Source (logger name)
  - Message content
- View detailed information for each log entry, including exception tracebacks
- Download all logs or filtered logs as text or JSON files
- Access via Help toolbar button or Help menu

## Usage

1. Click the "Log Viewer" button in the Help toolbar or select "Log Viewer" from the Help menu
2. The log viewer dialog will open, displaying all available logs
3. Use the filter controls at the top to narrow down the log entries
4. Click on any log entry to view its details in the panel below
5. Use the buttons at the bottom to refresh the view or download logs

## Filter Options

- **Log Level**: Filter by severity (INFO, WARNING, ERROR, etc.)
- **Date Range**: Filter logs within a specific time period
- **Source**: Filter by logger name (supports regex patterns)
- **Message**: Filter by message content (supports regex patterns)

## Technical Details

The plugin parses log files from the `logs/` directory and displays them in a sortable, filterable table. It handles standard Python logging format with timestamps, logger names, levels, and messages. 