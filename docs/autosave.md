# Autosave Feature

NetWORKS includes a comprehensive autosave system to ensure your work is never lost. This document explains how to configure and use this feature.

## Overview

The autosave feature periodically saves your current workspace, ensuring that your device data and configuration changes are preserved even in the event of an unexpected shutdown or crash. The system can be fully customized through the Settings dialog.

## Configuration

To configure autosave, go to **Tools → Settings** and select the **Autosave** tab. The following options are available:

### Autosave Options

- **Enable Autosave**: Turn the autosave feature on or off.
- **Autosave Interval**: Set how frequently to save your work (1-60 minutes).
- **Smart Autosave**: Only save if changes have been made since the last save.
- **Notifications**: Show a notification in the status bar when an autosave occurs.

### Backup Options

- **Create Backups**: Create a backup ZIP file of your workspace each time an autosave occurs.
- **Maximum Backups**: The maximum number of backup files to keep per workspace (1-100).
- **Backup Directory**: The directory where backup files are stored.

## How It Works

When autosave is enabled:

1. A timer runs in the background, checking if a save is needed based on your settings.
2. If "Smart Autosave" is enabled, it only saves when changes are detected in your workspace.
3. If backup creation is enabled, a ZIP file is created containing the complete workspace.
4. Old backups are automatically removed when the number exceeds your "Maximum Backups" setting.

## Backup Files

Backup files are stored in the format:

```
workspace_name_YYYYMMDD_HHMMSS.zip
```

For example: `production_20250518_143022.zip`

By default, backups are stored in the `config/backups` directory unless you specify a custom location.

## Restoring from Backup

To restore a workspace from a backup:

1. Locate the appropriate backup ZIP file in your backup directory.
2. Extract the contents to a temporary location.
3. Create a new workspace in NetWORKS.
4. Copy the extracted files to the new workspace directory.

## Best Practices

- Set an appropriate autosave interval based on how frequently you make changes.
- Enable "Smart Autosave" to reduce unnecessary disk writes.
- Keep backup creation enabled for important workspaces.
- Periodically check your backup directory to ensure backups are being created correctly.
- Consider using a cloud-synchronized folder for your backup directory for additional safety.

## Technical Details

Autosave functionality is implemented in the `MainWindow` class and respects all configuration settings specified in the autosave tab. The system uses the following configuration keys:

- `autosave.enabled`
- `autosave.interval`
- `autosave.only_on_changes`
- `autosave.show_notification`
- `autosave.create_backups`
- `autosave.max_backups`
- `autosave.backup_directory` 