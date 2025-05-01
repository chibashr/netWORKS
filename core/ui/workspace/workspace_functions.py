"""
Workspace management functions for the netWORKS application.
These functions were extracted from main_window.py to improve modularity.
"""

import os
import json
import logging
import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QMessageBox, QInputDialog, QFileDialog,
    QGroupBox, QCheckBox, QListWidget, QListWidgetItem,
    QTextEdit, QSplitter
)
from PySide6.QtCore import Signal, Qt, QTimer

# Setup logger
logger = logging.getLogger(__name__)

def show_workspace_dialog(main_window):
    """Show the workspace selection dialog at startup."""
    try:
        # Import required modules
        from core.ui.dialogs import WorkspaceSelectionDialog
        
        # Create and show the dialog
        dialog = WorkspaceSelectionDialog(main_window.workspace_manager, main_window)
        
        # Connect the workspace selection signal
        dialog.workspace_selected.connect(main_window.on_workspace_selected)
        
        # Show the dialog and wait for it to close
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            main_window.logger.info("Workspace selected successfully")
        else:
            main_window.logger.info("Workspace dialog closed with reject")
            # Default to first workspace if none selected
            workspaces = main_window.workspace_manager.get_workspaces()
            if workspaces:
                first_workspace_id = next(iter(workspaces))
                main_window.on_workspace_selected(first_workspace_id)
    except ImportError as e:
        main_window.logger.error(f"Error importing workspace dialog: {str(e)}", exc_info=True)
        # Fall back to default workspace
        main_window.logger.info("Falling back to default workspace due to import error")
        default_id = main_window.workspace_manager._create_default_workspace()
        if default_id:
            main_window.workspace_manager.open_workspace(default_id)
        main_window.show_error_dialog(
            "Workspace Dialog Error",
            "Could not load the workspace selection dialog. A default workspace has been created."
        )
    except Exception as e:
        main_window.logger.error(f"Error showing workspace dialog: {str(e)}", exc_info=True)
        # Fall back to default workspace
        main_window.logger.info("Falling back to default workspace due to unexpected error")
        default_id = main_window.workspace_manager._create_default_workspace()
        if default_id:
            main_window.workspace_manager.open_workspace(default_id)
        main_window.show_error_dialog(
            "Workspace Dialog Error",
            f"An error occurred while showing the workspace selection dialog: {str(e)}\n\n"
            "A default workspace has been created."
        )

def on_workspace_selected(main_window, workspace_id):
    """Handle workspace selection from dialog.
    
    Args:
        main_window: Reference to the main window
        workspace_id: ID of the selected workspace
    """
    try:
        main_window.logger.info(f"Selected workspace: {workspace_id}")
        
        # Open the selected workspace
        success = main_window.workspace_manager.open_workspace(workspace_id)
        
        if success:
            # Update window title
            workspace_meta = main_window.workspace_manager.get_current_workspace()
            if workspace_meta:
                main_window.setWindowTitle(f"netWORKS - {workspace_meta['name']}")
            main_window.logger.info(f"Opened workspace: {workspace_id}")
        else:
            main_window.logger.error(f"Failed to open workspace: {workspace_id}")
            main_window.show_error_dialog(
                "Workspace Error",
                f"Failed to open the selected workspace. A new workspace will be created."
            )
            
            # Create a new default workspace
            default_id = main_window.workspace_manager._create_default_workspace()
            if default_id:
                main_window.workspace_manager.open_workspace(default_id)
    except Exception as e:
        main_window.logger.error(f"Error opening workspace: {str(e)}", exc_info=True)
        main_window.show_error_dialog(
            "Workspace Error",
            f"An error occurred while opening the workspace: {str(e)}"
        )

def create_new_workspace(main_window):
    """Show dialog to create a new workspace."""
    try:
        name, ok = QInputDialog.getText(
            main_window, 
            "Create New Workspace",
            "Enter name for new workspace:"
        )
        
        if ok and name:
            # First save the current workspace if needed
            current_workspace = main_window.workspace_manager.get_current_workspace()
            if current_workspace:
                main_window.workspace_manager.save_workspace()
            
            # Create a new workspace
            workspace_id = main_window.workspace_manager.create_workspace(name)
            
            if workspace_id:
                # Open the new workspace
                success = main_window.workspace_manager.open_workspace(workspace_id)
                
                if success:
                    main_window.logger.info(f"Created new workspace: {name} ({workspace_id})")
                    main_window.setWindowTitle(f"netWORKS - {name}")
                    
                    # Show success message
                    QMessageBox.information(
                        main_window,
                        "Workspace Created",
                        f"New workspace '{name}' created successfully."
                    )
                else:
                    main_window.logger.error(f"Failed to open new workspace: {workspace_id}")
                    main_window.show_error_dialog(
                        "Workspace Error",
                        "Failed to open the new workspace."
                    )
            else:
                main_window.logger.error("Failed to create new workspace")
                main_window.show_error_dialog(
                    "Workspace Error",
                    "Failed to create new workspace."
                )
    except Exception as e:
        main_window.logger.error(f"Error creating new workspace: {str(e)}", exc_info=True)
        main_window.show_error_dialog(
            "Workspace Error",
            f"An error occurred while creating the workspace: {str(e)}"
        )

def save_workspace_data(main_window):
    """Save current workspace data."""
    try:
        # Set the status bar message
        main_window.statusBar.showMessage("Saving workspace data...", 2000)
        
        # Show progress indicator
        main_window.show_progress(True)
        main_window.update_progress(20, 100)
        
        # Save workspace data
        main_window.workspace_manager.save_workspace()
        
        # Update progress
        main_window.update_progress(80, 100)
        
        # Check for any plugins with special save handlers
        for plugin_id, plugin_info in main_window.plugin_manager.plugins.items():
            if plugin_info.get("enabled", False) and plugin_info.get("instance"):
                # Check if plugin has a save_workspace_data method
                plugin_api = main_window.plugin_manager.plugin_apis.get(plugin_id)
                if plugin_api and hasattr(plugin_api, "save_workspace_data") and callable(plugin_api.save_workspace_data):
                    try:
                        plugin_api.save_workspace_data()
                    except Exception as e:
                        main_window.logger.error(f"Error saving data for plugin {plugin_id}: {str(e)}", exc_info=True)
        
        # Hide progress indicator
        main_window.update_progress(100, 100)
        main_window.show_progress(False)
        
        # Set the status bar message
        main_window.statusBar.showMessage("Workspace data saved successfully", 2000)
        
    except Exception as e:
        main_window.logger.error(f"Error saving workspace data: {str(e)}", exc_info=True)
        main_window.show_progress(False)
        main_window.show_error_dialog(
            "Save Error",
            f"An error occurred while saving the workspace data: {str(e)}"
        )

def autosave_workspace(main_window):
    """Automatically save workspace data at regular intervals."""
    try:
        # Check if autosave is enabled in config
        if not main_window.config.get("app", {}).get("autosave_enabled", True):
            return
            
        # Don't save if there's no current workspace
        if not main_window.workspace_manager.get_current_workspace():
            return
            
        # Save workspace data
        main_window.workspace_manager.save_workspace()
        
        # Check for any plugins with special save handlers
        for plugin_id, plugin_info in main_window.plugin_manager.plugins.items():
            if plugin_info.get("enabled", False) and plugin_info.get("instance"):
                # Check if plugin has a save_workspace_data method
                plugin_api = main_window.plugin_manager.plugin_apis.get(plugin_id)
                if plugin_api and hasattr(plugin_api, "save_workspace_data") and callable(plugin_api.save_workspace_data):
                    try:
                        plugin_api.save_workspace_data()
                    except Exception as e:
                        main_window.logger.error(f"Error auto-saving data for plugin {plugin_id}: {str(e)}", exc_info=True)
        
    except Exception as e:
        main_window.logger.error(f"Error during autosave: {str(e)}", exc_info=True)

def import_workspace_data(main_window):
    """Import devices and settings from a file."""
    try:
        # First check if the workspace manager is available
        if hasattr(main_window, 'workspace_manager') and main_window.workspace_manager:
            # Create data/imports directory if it doesn't exist
            imports_dir = Path("data/imports")
            imports_dir.mkdir(parents=True, exist_ok=True)
            
            # Ask user for import file location
            file_path, _ = QFileDialog.getOpenFileName(
                main_window,
                "Import Workspace Data",
                str(imports_dir),
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if not file_path:
                return False
            
            # Attempt to import
            result = main_window.workspace_manager.import_workspace(file_path)
            
            if result:
                main_window.statusBar.showMessage(f"Imported workspace data from {file_path}", 5000)
                main_window.logger.info(f"Imported workspace data from {file_path}")
                
                # Show success message
                QMessageBox.information(
                    main_window,
                    "Import Successful",
                    f"Workspace data was successfully imported from {file_path}."
                )
                return True
            else:
                main_window.statusBar.showMessage(f"Error importing workspace data", 5000)
                main_window.logger.warning(f"Error importing workspace data from {file_path}")
                
                # Show error message
                QMessageBox.critical(
                    main_window,
                    "Import Error",
                    f"There was an error importing workspace data from {file_path}.\n\nThe file may be invalid or corrupted."
                )
                return False
        
        # Fall back to a simple JSON import if no workspace manager
        main_window.logger.warning("No workspace manager available, using simple JSON import")
        
        # Ask user for import file location
        file_path, _ = QFileDialog.getOpenFileName(
            main_window,
            "Import Workspace Data",
            "data/imports",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return False
            
        # Load JSON data
        with open(file_path, 'r') as f:
            import_data = json.load(f)
        
        # Check if the import file has a valid structure
        if not isinstance(import_data, dict) or 'devices' not in import_data:
            main_window.show_error_dialog(
                "Invalid Import File",
                "The selected file does not contain valid workspace data."
            )
            return False
        
        # Import the devices into the device table
        if hasattr(main_window, 'device_table'):
            main_window.device_table.devices = import_data.get('devices', [])
            main_window.device_table.update_data(main_window.device_table.devices)
            
            # Save to database if available
            if hasattr(main_window, 'database_manager') and main_window.database_manager:
                for device in main_window.device_table.devices:
                    main_window.database_manager.save_device(device)
        
        # Show success message
        main_window.statusBar.showMessage(f"Imported {len(import_data.get('devices', []))} devices from {file_path}", 5000)
        QMessageBox.information(
            main_window,
            "Import Successful",
            f"Successfully imported {len(import_data.get('devices', []))} devices from {file_path}."
        )
        return True
            
    except Exception as e:
        main_window.logger.error(f"Error importing workspace data: {str(e)}", exc_info=True)
        main_window.show_error_dialog(
            "Import Error",
            f"An error occurred while importing workspace data: {str(e)}"
        )
        return False

def export_workspace_data(main_window):
    """Export devices and settings to a file."""
    try:
        # First try to export through workspace manager if available
        if hasattr(main_window, 'workspace_manager') and main_window.workspace_manager:
            current_workspace = main_window.workspace_manager.get_current_workspace()
            if current_workspace:
                # Create data/exports directory if it doesn't exist
                exports_dir = Path("data/exports")
                exports_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate default filename with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                default_filename = f"{current_workspace['name'].replace(' ', '_')}_{timestamp}.json"
                default_path = str(exports_dir / default_filename)
                
                # Ask user for export file location
                file_path, _ = QFileDialog.getSaveFileName(
                    main_window,
                    "Export Workspace Data",
                    default_path,
                    "JSON Files (*.json);;All Files (*.*)"
                )
                
                if not file_path:
                    return False
                    
                # Add .json extension if not present
                if not file_path.lower().endswith('.json'):
                    file_path += '.json'
                
                # Export workspace
                if main_window.workspace_manager.export_workspace(current_workspace['id'], file_path):
                    main_window.statusBar.showMessage(f"Exported workspace '{current_workspace['name']}' to {file_path}", 5000)
                    main_window.logger.info(f"Exported workspace '{current_workspace['name']}' to {file_path}")
                    
                    # Show success message
                    QMessageBox.information(
                        main_window,
                        "Export Successful",
                        f"Workspace '{current_workspace['name']}' was successfully exported to {file_path}."
                    )
                    return True
                else:
                    main_window.statusBar.showMessage(f"Error exporting workspace", 5000)
                    main_window.logger.warning(f"Error exporting workspace")
                    
                    # Show error message
                    QMessageBox.critical(
                        main_window,
                        "Export Error",
                        f"There was an error exporting the workspace to {file_path}."
                    )
                    return False
        
        # Fall back to legacy export if no workspace manager or no current workspace
        # Create data/exports directory if it doesn't exist
        exports_dir = Path("data/exports")
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate default filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"workspace_export_{timestamp}.json"
        default_path = str(exports_dir / default_filename)
        
        # Ask user for export file location
        file_path, _ = QFileDialog.getSaveFileName(
            main_window,
            "Export Workspace Data",
            default_path,
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return False
            
        # Add .json extension if not present
        if not file_path.lower().endswith('.json'):
            file_path += '.json'
            
        # Prepare export data structure with complete information
        export_data = {
            "app_info": {
                "version": "1.0.0",  # Use actual version if available
                "export_date": datetime.datetime.now().isoformat(),
                "platform": os.name
            },
            "devices": []
        }
        
        # Export devices if available
        if hasattr(main_window, 'device_table'):
            export_data["devices"] = main_window.device_table.devices
        
        # Write export data to file
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        main_window.statusBar.showMessage(f"Exported {len(export_data['devices'])} devices to {file_path}", 5000)
        main_window.logger.info(f"Exported {len(export_data['devices'])} devices to {file_path}")
        
        # Show success message
        QMessageBox.information(
            main_window,
            "Export Successful",
            f"Successfully exported {len(export_data['devices'])} devices to {file_path}."
        )
        return True
            
    except Exception as e:
        main_window.logger.error(f"Error exporting workspace data: {str(e)}", exc_info=True)
        main_window.show_error_dialog(
            "Export Error",
            f"An error occurred while exporting workspace data: {str(e)}"
        )
        return False 