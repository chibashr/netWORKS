#!/usr/bin/env python3
# netWORKS - Workspace Manager

import json
import os
import uuid
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class WorkspaceManager:
    """Manages workspaces for netWORKS.
    
    This class handles the creation, loading, and management of workspaces.
    Each workspace is a collection of devices, settings, and plugin data.
    """
    
    def __init__(self, main_window=None):
        """Initialize the workspace manager.
        
        Args:
            main_window: Reference to the main window (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.main_window = main_window
        
        # Workspace directory setup
        self.workspaces_dir = Path("data/workspaces")
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        
        # Workspace data
        self.workspaces = {}  # id -> workspace data
        self.current_workspace_id = None
        
        # Load available workspaces
        self._load_available_workspaces()
        
        # Create default workspace if none exist and not in a dialog context
        # Note: We'll let the dialog handle workspace creation
        # if not self.workspaces:
        #     self._create_default_workspace()
            
        self.logger.info("Workspace manager initialized")
    
    def _load_available_workspaces(self):
        """Load metadata for all available workspaces."""
        try:
            # Load workspace metadata files
            for meta_file in self.workspaces_dir.glob("*/metadata.json"):
                try:
                    with open(meta_file, 'r') as f:
                        workspace_meta = json.load(f)
                    
                    workspace_id = workspace_meta.get('id')
                    if workspace_id:
                        self.workspaces[workspace_id] = workspace_meta
                except Exception as e:
                    self.logger.error(f"Error loading workspace metadata {meta_file}: {str(e)}")
            
            self.logger.info(f"Loaded {len(self.workspaces)} available workspaces")
        except Exception as e:
            self.logger.error(f"Error loading available workspaces: {str(e)}")
    
    def _create_default_workspace(self):
        """Create a default workspace if none exists."""
        try:
            workspace_id = str(uuid.uuid4())
            workspace_name = "Default Workspace"
            workspace_dir = self.workspaces_dir / workspace_id
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            # Create metadata file
            metadata = {
                'id': workspace_id,
                'name': workspace_name,
                'created': datetime.datetime.now().isoformat(),
                'last_modified': datetime.datetime.now().isoformat(),
                'description': "Default workspace created automatically.",
                'devices_count': 0,
                'device_groups_count': 0
            }
            
            with open(workspace_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create data file
            data = {
                'devices': [],
                'device_groups': {},
                'settings': {},
                'plugins': {}
            }
            
            with open(workspace_dir / "data.json", 'w') as f:
                json.dump(data, f, indent=2)
            
            # Add to workspaces dict
            self.workspaces[workspace_id] = metadata
            
            # Set as current workspace
            self.current_workspace_id = workspace_id
            
            self.logger.info(f"Created default workspace: {workspace_name} ({workspace_id})")
            return workspace_id
        except Exception as e:
            self.logger.error(f"Error creating default workspace: {str(e)}")
            return None
    
    def create_workspace(self, name: str, description: str = "") -> Optional[str]:
        """Create a new workspace.
        
        Args:
            name: Name of the workspace
            description: Description of the workspace
            
        Returns:
            Workspace ID or None if failed
        """
        try:
            workspace_id = str(uuid.uuid4())
            workspace_dir = self.workspaces_dir / workspace_id
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            # Create metadata file
            metadata = {
                'id': workspace_id,
                'name': name,
                'created': datetime.datetime.now().isoformat(),
                'last_modified': datetime.datetime.now().isoformat(),
                'description': description,
                'devices_count': 0,
                'device_groups_count': 0
            }
            
            with open(workspace_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create data file with existing data if available
            data = {
                'devices': [],
                'device_groups': {},
                'settings': {},
                'plugins': {}
            }
            
            # Keep existing data if main window is available
            if self.main_window:
                if hasattr(self.main_window, 'device_table') and self.main_window.device_table:
                    # Get current devices
                    data['devices'] = self.main_window.device_table.get_all_devices()
                    
                    # Get device groups
                    if hasattr(self.main_window.device_table, 'device_groups'):
                        data['device_groups'] = self.main_window.device_table.device_groups
                    
                    # Update metadata count
                    metadata['devices_count'] = len(data['devices'])
                    metadata['device_groups_count'] = len(data['device_groups'])
                
                # Get settings
                if hasattr(self.main_window, 'config'):
                    data['settings'] = self.main_window.config
                
                # Get plugin data
                if hasattr(self.main_window, 'plugin_manager'):
                    for plugin_id, plugin_info in self.main_window.plugin_manager.plugins.items():
                        data['plugins'][plugin_id] = {
                            'enabled': plugin_info.get('enabled', False),
                            'version': plugin_info.get('version', 'Unknown'),
                            'config': {},
                            'stored_data': {}
                        }
                        
                        # Get plugin config
                        plugin_api = self.main_window.plugin_manager.plugin_apis.get(plugin_id)
                        if plugin_api and hasattr(plugin_api, 'get_config'):
                            try:
                                plugin_config = plugin_api.get_config()
                                if plugin_config:
                                    data['plugins'][plugin_id]['config'] = plugin_config
                            except Exception as e:
                                self.logger.warning(f"Error getting config from plugin {plugin_id}: {str(e)}")
                        
                        # Get plugin stored data
                        if hasattr(self.main_window, 'database_manager'):
                            try:
                                # Check the get_plugin_data method signature
                                if hasattr(self.main_window.database_manager, 'get_plugin_data'):
                                    import inspect
                                    sig = inspect.signature(self.main_window.database_manager.get_plugin_data)
                                    
                                    # If get_plugin_data accepts only plugin_id (without key parameter)
                                    if len(sig.parameters) == 1:
                                        plugin_data = self.main_window.database_manager.get_plugin_data(plugin_id)
                                        if plugin_data:
                                            data['plugins'][plugin_id]['stored_data'] = plugin_data
                                    # If get_plugin_data requires both plugin_id and key
                                    elif len(sig.parameters) > 1:
                                        # Try to get all keys for this plugin
                                        if hasattr(self.main_window.database_manager, 'get_plugin_keys'):
                                            keys = self.main_window.database_manager.get_plugin_keys(plugin_id)
                                            for key in keys:
                                                value = self.main_window.database_manager.get_plugin_data(plugin_id, key)
                                                if value is not None:
                                                    if 'stored_data' not in data['plugins'][plugin_id]:
                                                        data['plugins'][plugin_id]['stored_data'] = {}
                                                    data['plugins'][plugin_id]['stored_data'][key] = value
                                        else:
                                            self.logger.warning(f"Cannot get plugin data keys for plugin {plugin_id}")
                            except Exception as e:
                                self.logger.warning(f"Error getting stored data for plugin {plugin_id}: {str(e)}")
            
            with open(workspace_dir / "data.json", 'w') as f:
                json.dump(data, f, indent=2)
            
            # Add to workspaces dict
            self.workspaces[workspace_id] = metadata
            
            self.logger.info(f"Created workspace: {name} ({workspace_id})")
            return workspace_id
        except Exception as e:
            self.logger.error(f"Error creating workspace: {str(e)}")
            return None
    
    def open_workspace(self, workspace_id: str) -> bool:
        """Open a workspace.
        
        Args:
            workspace_id: ID of the workspace to open
            
        Returns:
            True if successful, False otherwise
        """
        if workspace_id not in self.workspaces:
            self.logger.error(f"Workspace {workspace_id} not found")
            return False
        
        try:
            # Load workspace data
            workspace_dir = self.workspaces_dir / workspace_id
            data_file = workspace_dir / "data.json"
            
            if not data_file.exists():
                self.logger.error(f"Workspace data file not found: {data_file}")
                return False
            
            with open(data_file, 'r') as f:
                workspace_data = json.load(f)
            
            # Set current workspace
            self.current_workspace_id = workspace_id
            
            # Update main window if available
            if self.main_window:
                # Load devices into device table
                if hasattr(self.main_window, 'device_table') and self.main_window.device_table:
                    self.main_window.device_table.clear_devices()
                    if 'devices' in workspace_data:
                        self.main_window.device_table.add_devices(workspace_data['devices'])
                
                # Load device groups
                if hasattr(self.main_window, 'device_table') and self.main_window.device_table:
                    if 'device_groups' in workspace_data:
                        self.main_window.device_table.set_device_groups(workspace_data['device_groups'])
                
                # Load settings
                if hasattr(self.main_window, 'config') and 'settings' in workspace_data:
                    self.main_window.config.update(workspace_data['settings'])
                
                # Load plugin data
                if hasattr(self.main_window, 'plugin_manager') and 'plugins' in workspace_data:
                    for plugin_id, plugin_data in workspace_data['plugins'].items():
                        # Only load plugin data if plugin exists
                        if plugin_id in self.main_window.plugin_manager.plugins:
                            plugin_api = self.main_window.plugin_manager.plugin_apis.get(plugin_id)
                            
                            # Set plugin configuration if available
                            if plugin_api and 'config' in plugin_data and hasattr(plugin_api, 'set_config'):
                                try:
                                    plugin_api.set_config(plugin_data['config'])
                                except Exception as e:
                                    self.logger.warning(f"Error setting plugin config for {plugin_id}: {str(e)}")
                            
                            # Load plugin data into database if available
                            if 'stored_data' in plugin_data and hasattr(self.main_window, 'database_manager'):
                                for key, value in plugin_data['stored_data'].items():
                                    self.main_window.database_manager.store_plugin_data(plugin_id, key, value)
                
                # Refresh UI
                if hasattr(self.main_window, 'device_table') and self.main_window.device_table:
                    self.main_window.device_table.update_data()
                
                # Update status bar
                if hasattr(self.main_window, 'statusBar'):
                    devices_count = len(workspace_data.get('devices', []))
                    plugins_count = len(workspace_data.get('plugins', {}))
                    workspace_name = self.workspaces[workspace_id]['name']
                    
                    # Check if statusBar is a method or attribute
                    try:
                        status_bar = self.main_window.statusBar()
                        # Check if it's an object with showMessage
                        if hasattr(status_bar, 'showMessage'):
                            status_bar.showMessage(
                                f"Opened workspace '{workspace_name}' with {devices_count} devices and {plugins_count} plugins", 
                                5000
                            )
                    except Exception as e:
                        self.logger.warning(f"Could not update status bar: {str(e)}")
                        # Fallback - try direct access if statusBar is an attribute not a method
                        if hasattr(self.main_window, 'statusBar') and hasattr(self.main_window.statusBar, 'showMessage'):
                            self.main_window.statusBar.showMessage(
                                f"Opened workspace '{workspace_name}' with {devices_count} devices and {plugins_count} plugins", 
                                5000
                            )
            
            # Update metadata
            self.workspaces[workspace_id]['last_modified'] = datetime.datetime.now().isoformat()
            self.workspaces[workspace_id]['devices_count'] = len(workspace_data.get('devices', []))
            self.workspaces[workspace_id]['device_groups_count'] = len(workspace_data.get('device_groups', {}))
            
            with open(workspace_dir / "metadata.json", 'w') as f:
                json.dump(self.workspaces[workspace_id], f, indent=2)
            
            self.logger.info(f"Opened workspace: {self.workspaces[workspace_id]['name']} ({workspace_id})")
            return True
        except Exception as e:
            self.logger.error(f"Error opening workspace {workspace_id}: {str(e)}")
            return False
    
    def save_workspace(self, workspace_id: Optional[str] = None) -> bool:
        """Save the current workspace.
        
        Args:
            workspace_id: ID of the workspace to save (defaults to current)
            
        Returns:
            True if successful, False otherwise
        """
        # Use current workspace if none specified
        if workspace_id is None:
            workspace_id = self.current_workspace_id
        
        if not workspace_id or workspace_id not in self.workspaces:
            self.logger.error(f"Invalid workspace ID: {workspace_id}")
            return False
        
        try:
            # Get workspace directory
            workspace_dir = self.workspaces_dir / workspace_id
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare workspace data
            workspace_data = {
                'devices': [],
                'device_groups': {},
                'settings': {},
                'plugins': {}
            }
            
            # Gather data from main window if available
            if self.main_window:
                # Get devices from device table
                if hasattr(self.main_window, 'device_table') and self.main_window.device_table:
                    workspace_data['devices'] = self.main_window.device_table.get_all_devices()
                    
                    # Get device groups
                    if hasattr(self.main_window.device_table, 'device_groups'):
                        workspace_data['device_groups'] = self.main_window.device_table.device_groups
                
                # Get settings
                if hasattr(self.main_window, 'config'):
                    workspace_data['settings'] = self.main_window.config
                
                # Get plugin data
                if hasattr(self.main_window, 'plugin_manager'):
                    for plugin_id, plugin_info in self.main_window.plugin_manager.plugins.items():
                        workspace_data['plugins'][plugin_id] = {
                            'enabled': plugin_info.get('enabled', False),
                            'version': plugin_info.get('version', 'Unknown'),
                            'config': {},
                            'stored_data': {}
                        }
                        
                        # Get plugin config
                        plugin_api = self.main_window.plugin_manager.plugin_apis.get(plugin_id)
                        if plugin_api and hasattr(plugin_api, 'get_config'):
                            try:
                                plugin_config = plugin_api.get_config()
                                if plugin_config:
                                    workspace_data['plugins'][plugin_id]['config'] = plugin_config
                            except Exception as e:
                                self.logger.warning(f"Error getting config from plugin {plugin_id}: {str(e)}")
                        
                        # Get plugin stored data
                        if hasattr(self.main_window, 'database_manager'):
                            try:
                                plugin_data = self.main_window.database_manager.get_plugin_data(plugin_id)
                                if plugin_data:
                                    workspace_data['plugins'][plugin_id]['stored_data'] = plugin_data
                            except Exception as e:
                                self.logger.warning(f"Error getting stored data for plugin {plugin_id}: {str(e)}")
            
            # Save data file
            with open(workspace_dir / "data.json", 'w') as f:
                json.dump(workspace_data, f, indent=2)
            
            # Update metadata
            self.workspaces[workspace_id]['last_modified'] = datetime.datetime.now().isoformat()
            self.workspaces[workspace_id]['devices_count'] = len(workspace_data['devices'])
            self.workspaces[workspace_id]['device_groups_count'] = len(workspace_data['device_groups'])
            
            with open(workspace_dir / "metadata.json", 'w') as f:
                json.dump(self.workspaces[workspace_id], f, indent=2)
            
            self.logger.info(f"Saved workspace: {self.workspaces[workspace_id]['name']} ({workspace_id})")
            return True
        except Exception as e:
            self.logger.error(f"Error saving workspace {workspace_id}: {str(e)}")
            return False
    
    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace.
        
        Args:
            workspace_id: ID of the workspace to delete
            
        Returns:
            True if successful, False otherwise
        """
        if workspace_id not in self.workspaces:
            self.logger.error(f"Workspace {workspace_id} not found")
            return False
        
        try:
            # Cannot delete current workspace
            if workspace_id == self.current_workspace_id:
                self.logger.error("Cannot delete current workspace")
                return False
            
            # Delete workspace directory
            workspace_dir = self.workspaces_dir / workspace_id
            if workspace_dir.exists():
                import shutil
                shutil.rmtree(workspace_dir)
            
            # Remove from workspaces dict
            workspace_name = self.workspaces[workspace_id]['name']
            del self.workspaces[workspace_id]
            
            self.logger.info(f"Deleted workspace: {workspace_name} ({workspace_id})")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting workspace {workspace_id}: {str(e)}")
            return False
    
    def rename_workspace(self, workspace_id: str, new_name: str) -> bool:
        """Rename a workspace.
        
        Args:
            workspace_id: ID of the workspace to rename
            new_name: New name for the workspace
            
        Returns:
            True if successful, False otherwise
        """
        if workspace_id not in self.workspaces:
            self.logger.error(f"Workspace {workspace_id} not found")
            return False
        
        try:
            # Get workspace directory
            workspace_dir = self.workspaces_dir / workspace_id
            
            # Update metadata
            old_name = self.workspaces[workspace_id]['name']
            self.workspaces[workspace_id]['name'] = new_name
            self.workspaces[workspace_id]['last_modified'] = datetime.datetime.now().isoformat()
            
            with open(workspace_dir / "metadata.json", 'w') as f:
                json.dump(self.workspaces[workspace_id], f, indent=2)
            
            self.logger.info(f"Renamed workspace: {old_name} -> {new_name} ({workspace_id})")
            return True
        except Exception as e:
            self.logger.error(f"Error renaming workspace {workspace_id}: {str(e)}")
            return False
    
    def get_workspaces(self) -> Dict[str, Dict]:
        """Get all available workspaces.
        
        Returns:
            Dictionary of workspaces (id -> metadata)
        """
        return self.workspaces
    
    def get_current_workspace(self) -> Optional[Dict]:
        """Get the current workspace metadata.
        
        Returns:
            Current workspace metadata or None if no current workspace
        """
        if not self.current_workspace_id:
            return None
        return self.workspaces.get(self.current_workspace_id)
    
    def import_workspace(self, file_path: str) -> Optional[str]:
        """Import a workspace from a file.
        
        Args:
            file_path: Path to the workspace file
            
        Returns:
            Imported workspace ID or None if failed
        """
        try:
            with open(file_path, 'r') as f:
                import_data = json.load(f)
            
            # Create new workspace
            description = "Imported workspace"
            if "application" in import_data:
                description += f" from {import_data['application'].get('name', 'unknown')} {import_data['application'].get('version', '')}"
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            workspace_name = f"Imported Workspace {timestamp}"
            
            workspace_id = self.create_workspace(workspace_name, description)
            if not workspace_id:
                self.logger.error("Failed to create workspace for import")
                return None
            
            # Get workspace directory
            workspace_dir = self.workspaces_dir / workspace_id
            
            # Prepare workspace data
            workspace_data = {
                'devices': import_data.get('devices', []),
                'device_groups': import_data.get('device_groups', {}),
                'settings': import_data.get('settings', {}),
                'plugins': {}
            }
            
            # Process plugin data
            if "plugins" in import_data:
                workspace_data['plugins'] = import_data['plugins']
            
            # Save data file
            with open(workspace_dir / "data.json", 'w') as f:
                json.dump(workspace_data, f, indent=2)
            
            # Update metadata
            self.workspaces[workspace_id]['devices_count'] = len(workspace_data['devices'])
            self.workspaces[workspace_id]['device_groups_count'] = len(workspace_data['device_groups'])
            
            with open(workspace_dir / "metadata.json", 'w') as f:
                json.dump(self.workspaces[workspace_id], f, indent=2)
            
            self.logger.info(f"Imported workspace from {file_path} as {workspace_name} ({workspace_id})")
            return workspace_id
        except Exception as e:
            self.logger.error(f"Error importing workspace from {file_path}: {str(e)}")
            return None
    
    def export_workspace(self, workspace_id: str, file_path: str) -> bool:
        """Export a workspace to a file.
        
        Args:
            workspace_id: ID of the workspace to export
            file_path: Path to save the workspace file
            
        Returns:
            True if successful, False otherwise
        """
        if workspace_id not in self.workspaces:
            self.logger.error(f"Workspace {workspace_id} not found")
            return False
        
        try:
            # Get workspace directory
            workspace_dir = self.workspaces_dir / workspace_id
            data_file = workspace_dir / "data.json"
            
            if not data_file.exists():
                self.logger.error(f"Workspace data file not found: {data_file}")
                return False
            
            with open(data_file, 'r') as f:
                workspace_data = json.load(f)
            
            # Prepare export data
            export_data = {
                "export_version": "2.0",
                "timestamp": datetime.datetime.now().isoformat(),
                "application": {
                    "name": "netWORKS",
                    "version": "Unknown"
                },
                "workspace": {
                    "id": workspace_id,
                    "name": self.workspaces[workspace_id]['name'],
                    "created": self.workspaces[workspace_id]['created'],
                    "description": self.workspaces[workspace_id]['description']
                },
                "devices": workspace_data.get('devices', []),
                "device_groups": workspace_data.get('device_groups', {}),
                "settings": workspace_data.get('settings', {}),
                "plugins": workspace_data.get('plugins', {})
            }
            
            # Add app version from plugin manager if available
            if self.main_window and hasattr(self.main_window, 'plugin_manager'):
                if hasattr(self.main_window.plugin_manager, 'get_app_version'):
                    export_data['application']['version'] = self.main_window.plugin_manager.get_app_version()
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Exported workspace {self.workspaces[workspace_id]['name']} ({workspace_id}) to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting workspace {workspace_id} to {file_path}: {str(e)}")
            return False 