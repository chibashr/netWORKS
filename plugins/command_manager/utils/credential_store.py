#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Credential Store for Command Manager plugin
"""

import os
import json
import ipaddress
from pathlib import Path
from loguru import logger

from .encryption import encrypt_password, decrypt_password


class CredentialStore:
    """Secure storage for network device credentials"""
    
    def __init__(self, data_dir):
        """Initialize the credential store"""
        self.data_dir = data_dir
        
        # Define legacy paths for migration purposes only (don't create them)
        self.plugin_creds_dir = data_dir / "credentials"
        self.legacy_group_creds_dir = self.plugin_creds_dir / "groups"
        self.legacy_subnet_creds_dir = self.plugin_creds_dir / "subnets"
        self.device_creds_dir = self.plugin_creds_dir / "devices"
        
        # Main app workspace directory (will be set when device_manager is provided)
        self.app_workspace_dir = None
        self.workspace_name = "default"
        self.previous_workspace_name = None
        
        # Device manager reference (will be set by the plugin)
        self.device_manager = None
        
        # Cache - make workspace-specific by using dictionaries with workspace as key
        self.device_credentials = {}  # Only used for backward compatibility
        self.workspace_credentials = {
            "default": {
                "groups": {},
                "subnets": {}
            }
        }
        
        # Load device credentials initially
        self._load_device_credentials()
        
    def set_device_manager(self, device_manager):
        """Set the device manager reference"""
        old_workspace_name = self.workspace_name
        workspace_found = False
        
        self.device_manager = device_manager
        logger.debug(f"CredentialStore: Device manager set: {device_manager is not None}")
        
        # Update workspace name and directory if device_manager is available
        if self.device_manager:
            # Get workspace name
            if hasattr(self.device_manager, 'get_current_workspace_name'):
                try:
                    self.workspace_name = self.device_manager.get_current_workspace_name()
                    if old_workspace_name != self.workspace_name:
                        logger.debug(f"CredentialStore: Workspace changed from {old_workspace_name} to {self.workspace_name}")
                        self.previous_workspace_name = old_workspace_name
                    logger.debug(f"CredentialStore: Current workspace set to {self.workspace_name}")
                except Exception as e:
                    logger.warning(f"Error getting current workspace name: {e}")
            else:
                logger.warning("Device manager does not have get_current_workspace_name method")
            
            # Get workspace directory
            if hasattr(self.device_manager, 'get_workspace_dir'):
                try:
                    workspace_dir = self.device_manager.get_workspace_dir()
                    logger.debug(f"CredentialStore: Device manager returned workspace_dir: {workspace_dir}")
                    if workspace_dir:
                        self.app_workspace_dir = Path(workspace_dir)
                        workspace_found = True
                        logger.debug(f"CredentialStore: Using workspace directory: {self.app_workspace_dir}")
                        logger.debug(f"CredentialStore: Workspace directory exists: {self.app_workspace_dir.exists()}")
                        
                        # Check if the command_manager subdirectory exists
                        cmd_mgr_dir = self.app_workspace_dir / "command_manager"
                        logger.debug(f"CredentialStore: Command manager directory exists: {cmd_mgr_dir.exists()}")
                        
                        # Check if credentials subdirectory exists
                        creds_dir = cmd_mgr_dir / "credentials"
                        logger.debug(f"CredentialStore: Credentials directory exists: {creds_dir.exists()}")
                    else:
                        logger.warning("Device manager returned None for workspace directory")
                except Exception as e:
                    logger.warning(f"Error getting workspace directory: {e}")
            else:
                logger.warning("Device manager does not have get_workspace_dir method")
        else:
            logger.warning("No device manager provided to credential store")
        
        # If we couldn't get workspace directory from device manager, try to construct it
        if not workspace_found and self.workspace_name:
            logger.debug(f"CredentialStore: Attempting to construct workspace directory for workspace: {self.workspace_name}")
            
            # Try to find the workspace directory in various possible locations
            possible_paths = [
                # Current directory workspace
                Path.cwd() / "workspaces" / self.workspace_name,
                # Data directory workspace  
                self.data_dir.parent.parent / "workspaces" / self.workspace_name
            ]
            
            for path in possible_paths:
                logger.debug(f"CredentialStore: Checking possible workspace path: {path}")
                if path.exists():
                    self.app_workspace_dir = path
                    workspace_found = True
                    logger.info(f"CredentialStore: Found workspace directory at: {self.app_workspace_dir}")
                    break
            
            if not workspace_found:
                logger.warning(f"CredentialStore: Could not find workspace directory for workspace: {self.workspace_name}")
        
        # Load credentials after setting device manager
        self._load_credentials()
        
    def _get_workspace_device_dir(self):
        """Get the directory for the current workspace's device credentials"""
        try:
            # First try using the app_workspace_dir if it exists
            if self.app_workspace_dir and self.app_workspace_dir.exists():
                workspace_dir = self.app_workspace_dir / "command_manager" / "credentials" / "devices"
                workspace_dir.mkdir(parents=True, exist_ok=True)
                return workspace_dir
                
            # If not, try getting workspace from device_manager
            if self.device_manager:
                if hasattr(self.device_manager, 'get_workspace_dir'):
                    try:
                        workspace_path = Path(self.device_manager.get_workspace_dir())
                        if workspace_path and workspace_path.exists():
                            # Create credential directory structure
                            workspace_dir = workspace_path / "command_manager" / "credentials" / "devices"
                            workspace_dir.mkdir(parents=True, exist_ok=True)
                            # Update our reference for future use
                            self.app_workspace_dir = workspace_path
                            return workspace_dir
                    except Exception as e:
                        logger.debug(f"Could not get workspace directory from device_manager: {e}")
                
            # Last resort: use fallback in data directory
            fallback_dir = self.data_dir / "workspace_fallback" / self.workspace_name / "credentials" / "devices"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback workspace directory: {fallback_dir}")
            return fallback_dir
            
        except Exception as e:
            logger.error(f"Error creating workspace device directory: {e}")
            # Ultimate fallback - use plugin data directory
            try:
                fallback = self.data_dir / "credentials" / "devices"
                fallback.mkdir(parents=True, exist_ok=True)
                return fallback
            except:
                logger.error("Cannot get workspace device directory: app_workspace_dir is not set or doesn't exist")
                return None
        
    def _get_workspace_group_dir(self):
        """Get the directory for the current workspace's group credentials"""
        try:
            # First try using the app_workspace_dir if it exists
            if self.app_workspace_dir and self.app_workspace_dir.exists():
                workspace_dir = self.app_workspace_dir / "command_manager" / "credentials" / "groups"
                workspace_dir.mkdir(parents=True, exist_ok=True)
                return workspace_dir
                
            # If not, try getting workspace from device_manager
            if self.device_manager:
                if hasattr(self.device_manager, 'get_workspace_dir'):
                    try:
                        workspace_path = Path(self.device_manager.get_workspace_dir())
                        if workspace_path and workspace_path.exists():
                            # Create credential directory structure
                            workspace_dir = workspace_path / "command_manager" / "credentials" / "groups"
                            workspace_dir.mkdir(parents=True, exist_ok=True)
                            # Update our reference for future use
                            self.app_workspace_dir = workspace_path
                            return workspace_dir
                    except Exception as e:
                        logger.debug(f"Could not get workspace directory from device_manager: {e}")
                
            # Last resort: use fallback in data directory
            fallback_dir = self.data_dir / "workspace_fallback" / self.workspace_name / "credentials" / "groups"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback workspace group directory: {fallback_dir}")
            return fallback_dir
            
        except Exception as e:
            logger.error(f"Error creating workspace group directory: {e}")
            # Ultimate fallback - use plugin data directory
            try:
                fallback = self.data_dir / "credentials" / "groups"
                fallback.mkdir(parents=True, exist_ok=True)
                return fallback
            except:
                logger.error("Cannot create workspace group directory: all fallback options failed")
                return None
        
    def _get_workspace_subnet_dir(self):
        """Get the directory for the current workspace's subnet credentials"""
        try:
            # First try using the app_workspace_dir if it exists
            if self.app_workspace_dir and self.app_workspace_dir.exists():
                workspace_dir = self.app_workspace_dir / "command_manager" / "credentials" / "subnets"
                workspace_dir.mkdir(parents=True, exist_ok=True)
                return workspace_dir
                
            # If not, try getting workspace from device_manager
            if self.device_manager:
                if hasattr(self.device_manager, 'get_workspace_dir'):
                    try:
                        workspace_path = Path(self.device_manager.get_workspace_dir())
                        if workspace_path and workspace_path.exists():
                            # Create credential directory structure
                            workspace_dir = workspace_path / "command_manager" / "credentials" / "subnets"
                            workspace_dir.mkdir(parents=True, exist_ok=True)
                            # Update our reference for future use
                            self.app_workspace_dir = workspace_path
                            return workspace_dir
                    except Exception as e:
                        logger.debug(f"Could not get workspace directory from device_manager: {e}")
                
            # Last resort: use fallback in data directory
            fallback_dir = self.data_dir / "workspace_fallback" / self.workspace_name / "credentials" / "subnets"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback workspace subnet directory: {fallback_dir}")
            return fallback_dir
            
        except Exception as e:
            logger.error(f"Error creating workspace subnet directory: {e}")
            # Ultimate fallback - use plugin data directory
            try:
                fallback = self.data_dir / "credentials" / "subnets"
                fallback.mkdir(parents=True, exist_ok=True)
                return fallback
            except:
                logger.error("Cannot create workspace subnet directory: all fallback options failed")
                return None

    def _cleanup_legacy_credentials(self):
        """Delete all credential files from the legacy plugin directories"""
        # Check if the plugin_creds_dir exists before trying to access it
        if not self.plugin_creds_dir.exists():
            logger.debug(f"Legacy credentials directory doesn't exist: {self.plugin_creds_dir}")
            return
            
        # Remove legacy device credentials
        if self.device_creds_dir.exists():
            try:
                for file_path in self.device_creds_dir.glob("*.json"):
                    try:
                        file_path.unlink()
                        logger.debug(f"Deleted legacy credential file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting legacy credential file {file_path}: {e}")
                
                # Try to remove the directory
                if not any(self.device_creds_dir.iterdir()):
                    self.device_creds_dir.rmdir()
                    logger.info("Removed empty legacy device credentials directory")
            except Exception as e:
                logger.error(f"Error cleaning up legacy device credentials: {e}")
        
        # Remove legacy group credentials
        if self.legacy_group_creds_dir.exists():
            try:
                for file_path in self.legacy_group_creds_dir.glob("*.json"):
                    try:
                        file_path.unlink()
                        logger.debug(f"Deleted legacy group credential file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting legacy group credential file {file_path}: {e}")
                
                # Try to remove the directory
                if not any(self.legacy_group_creds_dir.iterdir()):
                    self.legacy_group_creds_dir.rmdir()
                    logger.info("Removed empty legacy group credentials directory")
            except Exception as e:
                logger.error(f"Error cleaning up legacy group credentials: {e}")
        
        # Remove legacy subnet credentials
        if self.legacy_subnet_creds_dir.exists():
            try:
                for file_path in self.legacy_subnet_creds_dir.glob("*.json"):
                    try:
                        file_path.unlink()
                        logger.debug(f"Deleted legacy subnet credential file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting legacy subnet credential file {file_path}: {e}")
                
                # Try to remove the directory
                if not any(self.legacy_subnet_creds_dir.iterdir()):
                    self.legacy_subnet_creds_dir.rmdir()
                    logger.info("Removed empty legacy subnet credentials directory")
            except Exception as e:
                logger.error(f"Error cleaning up legacy subnet credentials: {e}")
                
        # Clean up any workspaces directory in plugin
        workspaces_dir = self.plugin_creds_dir / "workspaces"
        if workspaces_dir.exists():
            try:
                import shutil
                shutil.rmtree(workspaces_dir)
                logger.info("Removed legacy workspaces directory from plugin")
            except Exception as e:
                logger.error(f"Error removing legacy workspaces directory: {e}")
                
        # Try to remove the main credentials directory if empty
        try:
            if self.plugin_creds_dir.exists() and not any(self.plugin_creds_dir.iterdir()):
                self.plugin_creds_dir.rmdir()
                logger.info("Removed empty plugin credentials directory")
        except Exception as e:
            logger.error(f"Error removing plugin credentials directory: {e}")

    def _migrate_legacy_credentials(self):
        """Migrate any legacy credentials to workspace-specific directories"""
        logger.debug("Checking for legacy credentials to migrate")
        
        # First migrate any legacy plugin-specific workspace credentials
        legacy_plugin_workspace_dir = self.plugin_creds_dir / "workspaces"
        if legacy_plugin_workspace_dir.exists():
            for workspace_dir in legacy_plugin_workspace_dir.glob("*"):
                if workspace_dir.is_dir():
                    ws_name = workspace_dir.name
                    logger.info(f"Migrating legacy workspace credentials: {ws_name}")
                    
                    # Migrate group credentials
                    legacy_group_dir = workspace_dir / "groups"
                    if legacy_group_dir.exists() and legacy_group_dir.is_dir():
                        # Get target directory
                        if ws_name == self.workspace_name:
                            # Current workspace - use current methods
                            target_group_dir = self._get_workspace_group_dir()
                        else:
                            # Other workspace - create target directory
                            if self.app_workspace_dir and self.app_workspace_dir.parent:
                                # Use parent of current workspace dir to get to workspaces
                                target_group_dir = self.app_workspace_dir.parent / ws_name / "command_manager" / "credentials" / "groups"
                            else:
                                # Fallback
                                continue
                                
                        target_group_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Migrate files
                        for file_path in legacy_group_dir.glob("*.json"):
                            try:
                                with open(file_path, "r") as f:
                                    creds = json.load(f)
                                
                                target_path = target_group_dir / file_path.name
                                with open(target_path, "w") as f:
                                    json.dump(creds, f, indent=2)
                                
                                logger.debug(f"Migrated group credentials from workspace {ws_name}: {file_path.name}")
                                
                                # Delete legacy file
                                try:
                                    file_path.unlink()
                                except Exception as e:
                                    logger.error(f"Error deleting legacy group credential file: {e}")
                            except Exception as e:
                                logger.error(f"Error migrating group credentials from {file_path}: {e}")
                    
                    # Migrate subnet credentials
                    legacy_subnet_dir = workspace_dir / "subnets"
                    if legacy_subnet_dir.exists() and legacy_subnet_dir.is_dir():
                        # Get target directory
                        if ws_name == self.workspace_name:
                            # Current workspace - use current methods
                            target_subnet_dir = self._get_workspace_subnet_dir()
                        else:
                            # Other workspace - create target directory
                            if self.app_workspace_dir and self.app_workspace_dir.parent:
                                # Use parent of current workspace dir to get to workspaces
                                target_subnet_dir = self.app_workspace_dir.parent / ws_name / "command_manager" / "credentials" / "subnets"
                            else:
                                # Fallback
                                continue
                                
                        target_subnet_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Migrate files
                        for file_path in legacy_subnet_dir.glob("*.json"):
                            try:
                                with open(file_path, "r") as f:
                                    creds = json.load(f)
                                
                                target_path = target_subnet_dir / file_path.name
                                with open(target_path, "w") as f:
                                    json.dump(creds, f, indent=2)
                                
                                logger.debug(f"Migrated subnet credentials from workspace {ws_name}: {file_path.name}")
                                
                                # Delete legacy file
                                try:
                                    file_path.unlink()
                                except Exception as e:
                                    logger.error(f"Error deleting legacy subnet credential file: {e}")
                            except Exception as e:
                                logger.error(f"Error migrating subnet credentials from {file_path}: {e}")
                
                # Try to clean up if directories are empty
                try:
                    if legacy_group_dir.exists() and not any(legacy_group_dir.iterdir()):
                        legacy_group_dir.rmdir()
                except Exception as e:
                    logger.error(f"Error removing legacy group directory: {e}")
                
                try:
                    if legacy_subnet_dir.exists() and not any(legacy_subnet_dir.iterdir()):
                        legacy_subnet_dir.rmdir()
                except Exception as e:
                    logger.error(f"Error removing legacy subnet directory: {e}")
                    
                try:
                    if workspace_dir.exists() and not any(workspace_dir.iterdir()):
                        workspace_dir.rmdir()
                except Exception as e:
                    logger.error(f"Error removing legacy workspace directory: {e}")
        
        # Migrate legacy group credentials
        if self.legacy_group_creds_dir.exists():
            logger.info(f"Migrating legacy group credentials to workspace '{self.workspace_name}'")
            workspace_group_dir = self._get_workspace_group_dir()
            
            # Iterate through credential files
            for file_path in self.legacy_group_creds_dir.glob("*.json"):
                try:
                    # Read credentials
                    with open(file_path, "r") as f:
                        creds = json.load(f)
                    
                    # Extract group name from filename
                    group_name = file_path.stem
                    
                    # Save to workspace directory
                    target_path = workspace_group_dir / file_path.name
                    with open(target_path, "w") as f:
                        json.dump(creds, f, indent=2)
                    
                    logger.debug(f"Migrated group credentials for '{group_name}' to workspace")
                    
                    # Delete legacy file
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.error(f"Error deleting legacy group credential file: {e}")
                        
                except Exception as e:
                    logger.error(f"Error migrating group credentials from {file_path}: {e}")
            
            # Try to remove legacy directory if empty
            try:
                if not any(self.legacy_group_creds_dir.iterdir()):
                    self.legacy_group_creds_dir.rmdir()
                    logger.info("Removed empty legacy group credentials directory")
            except Exception as e:
                logger.error(f"Error removing legacy group credentials directory: {e}")
        
        # Migrate legacy subnet credentials
        if self.legacy_subnet_creds_dir.exists():
            logger.info(f"Migrating legacy subnet credentials to workspace '{self.workspace_name}'")
            workspace_subnet_dir = self._get_workspace_subnet_dir()
            
            # Iterate through credential files
            for file_path in self.legacy_subnet_creds_dir.glob("*.json"):
                try:
                    # Read credentials
                    with open(file_path, "r") as f:
                        creds = json.load(f)
                    
                    # Extract subnet from filename
                    subnet = file_path.stem
                    
                    # Save to workspace directory
                    target_path = workspace_subnet_dir / file_path.name
                    with open(target_path, "w") as f:
                        json.dump(creds, f, indent=2)
                    
                    logger.debug(f"Migrated subnet credentials for '{subnet}' to workspace")
                    
                    # Delete legacy file
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.error(f"Error deleting legacy subnet credential file: {e}")
                        
                except Exception as e:
                    logger.error(f"Error migrating subnet credentials from {file_path}: {e}")
            
            # Try to remove legacy directory if empty
            try:
                if not any(self.legacy_subnet_creds_dir.iterdir()):
                    self.legacy_subnet_creds_dir.rmdir()
                    logger.info("Removed empty legacy subnet credentials directory")
            except Exception as e:
                logger.error(f"Error removing legacy subnet credentials directory: {e}")
                
        # Try cleaning up the workspaces directory if empty
        try:
            if legacy_plugin_workspace_dir.exists() and not any(legacy_plugin_workspace_dir.iterdir()):
                legacy_plugin_workspace_dir.rmdir()
                logger.info("Removed empty legacy workspaces directory")
        except Exception as e:
            logger.error(f"Error removing legacy workspaces directory: {e}")
            
        # Try cleaning up the plugin credentials directory if empty
        try:
            plugin_workspaces_dir = self.plugin_creds_dir / "workspaces"
            if plugin_workspaces_dir.exists() and not any(plugin_workspaces_dir.iterdir()):
                plugin_workspaces_dir.rmdir()
                logger.info("Removed empty plugin workspaces directory")
                
            # Check if the main plugin credentials directory is empty except for device credentials
            non_device_dirs = [d for d in self.plugin_creds_dir.iterdir() if d != self.device_creds_dir]
            if not non_device_dirs:
                logger.info("Plugin credentials directory contains only device credentials")
        except Exception as e:
            logger.error(f"Error cleaning up plugin workspaces directory: {e}")
        
    def _load_credentials(self):
        """Load all credentials from disk"""
        if not self.app_workspace_dir:
            logger.error("Cannot load credentials: No workspace directory available")
            logger.error("Current workspace name: " + self.workspace_name)
            logger.error("Device manager available: " + str(self.device_manager is not None))
            if self.device_manager:
                logger.error("Device manager type: " + str(type(self.device_manager)))
                logger.error("Has get_workspace_dir: " + str(hasattr(self.device_manager, 'get_workspace_dir')))
                if hasattr(self.device_manager, 'get_workspace_dir'):
                    logger.error("get_workspace_dir returns: " + str(self.device_manager.get_workspace_dir()))
                logger.error("Has get_current_workspace_name: " + str(hasattr(self.device_manager, 'get_current_workspace_name')))
                if hasattr(self.device_manager, 'get_current_workspace_name'):
                    logger.error("get_current_workspace_name returns: " + str(self.device_manager.get_current_workspace_name()))
            return
            
        logger.debug(f"Loading credentials from workspace: {self.app_workspace_dir}")
        
        self._load_device_credentials()
        self._load_group_credentials()
        self._load_subnet_credentials()
        
        # Ensure no credentials remain in plugin directory
        self._cleanup_legacy_credentials()
        
    def _load_device_credentials(self):
        """
        Load device credentials from disk
        Note: Legacy credentials will be migrated to device properties or workspace
        """
        self.device_credentials = {}
        
        # Get workspace directory
        workspace_device_dir = self._get_workspace_device_dir()
        if not workspace_device_dir:
            logger.error("Cannot load device credentials: No workspace directory available")
            return
        
        # Load from workspace directory
        if workspace_device_dir.exists():
            logger.debug(f"Loading device credentials from workspace directory: {workspace_device_dir}")
            # Iterate through credential files in workspace directory
            for file_path in workspace_device_dir.glob("*.json"):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        
                    # Extract device ID from filename
                    device_id = file_path.stem
                    
                    # Store credentials
                    self.device_credentials[device_id] = data
                    
                    # Decrypt password (if needed)
                    if "password" in data and data["password"]:
                        try:
                            data["password"] = decrypt_password(data["password"])
                        except:
                            # If decryption fails, keep encrypted
                            pass
                    
                    # Decrypt enable password (if needed)
                    if "enable_password" in data and data["enable_password"]:
                        try:
                            data["enable_password"] = decrypt_password(data["enable_password"])
                        except:
                            # If decryption fails, keep encrypted
                            pass
                    
                    # Migrate to device properties if device manager is available
                    if self.device_manager:
                        device = self.device_manager.get_device(device_id)
                        if device:
                            self._migrate_credentials_to_device(device, data)
                            # Delete the file after migration to device properties
                            try:
                                file_path.unlink()
                                logger.debug(f"Migrated workspace credentials to device properties for {device_id}")
                            except Exception as e:
                                logger.error(f"Error deleting workspace credential file after migration: {e}")
                    
                except Exception as e:
                    logger.error(f"Error loading device credentials from workspace {file_path}: {e}")
        
        # Migrate any legacy credentials to workspace
        self._migrate_legacy_device_credentials()
        
    def _migrate_legacy_device_credentials(self):
        """Migrate device credentials from legacy location to workspace"""
        # Get workspace directory
        workspace_device_dir = self._get_workspace_device_dir()
        if not workspace_device_dir:
            logger.error("Cannot migrate legacy device credentials: No workspace directory available")
            return
        
        # Check if legacy directory exists
        if not self.device_creds_dir.exists():
            return
            
        logger.info("Migrating legacy device credentials to workspace")
        
        # Iterate through legacy credential files
        for file_path in self.device_creds_dir.glob("*.json"):
            try:
                # Read legacy credentials
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Extract device ID from filename
                device_id = file_path.stem
                
                # First try to migrate to device properties
                if self.device_manager:
                    device = self.device_manager.get_device(device_id)
                    if device:
                        # Create a copy with decrypted values
                        decrypted_data = data.copy()
                        
                        # Decrypt password (if needed)
                        if "password" in decrypted_data and decrypted_data["password"]:
                            try:
                                decrypted_data["password"] = decrypt_password(decrypted_data["password"])
                            except:
                                # If decryption fails, keep encrypted
                                pass
                        
                        # Decrypt enable password (if needed)
                        if "enable_password" in decrypted_data and decrypted_data["enable_password"]:
                            try:
                                decrypted_data["enable_password"] = decrypt_password(decrypted_data["enable_password"])
                            except:
                                # If decryption fails, keep encrypted
                                pass
                                
                        # Migrate to device properties
                        self._migrate_credentials_to_device(device, decrypted_data)
                        
                        # Add to in-memory cache (decrypted)
                        self.device_credentials[device_id] = decrypted_data
                        
                        logger.debug(f"Migrated legacy credentials to device properties for {device_id}")
                        
                        # Delete legacy file
                        try:
                            file_path.unlink()
                            logger.debug(f"Deleted legacy credential file after migration: {file_path}")
                        except Exception as e:
                            logger.error(f"Error deleting legacy credential file {file_path}: {e}")
                            
                        # Continue to next file
                        continue
                
                # If device not found or no device manager, save to workspace
                # Save to workspace directory
                target_path = workspace_device_dir / file_path.name
                with open(target_path, "w") as f:
                    json.dump(data, f, indent=2)
                
                logger.debug(f"Migrated legacy device credentials to workspace for {device_id}")
                
                # Add to in-memory cache (encrypted, will be decrypted when accessed)
                self.device_credentials[device_id] = data
                
                # Delete legacy file
                try:
                    file_path.unlink()
                    logger.debug(f"Deleted legacy credential file after migration: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting legacy credential file {file_path}: {e}")
                
            except Exception as e:
                logger.error(f"Error migrating legacy device credentials from {file_path}: {e}")
        
        # Try to remove the legacy directory if empty
        try:
            if not any(self.device_creds_dir.iterdir()):
                self.device_creds_dir.rmdir()
                logger.info("Removed empty legacy device credentials directory")
        except Exception as e:
            logger.error(f"Error removing legacy device credentials directory: {e}")
    
    def _migrate_credentials_to_device(self, device, credentials):
        """Migrate credentials from file to device properties"""
        encrypted_creds = credentials.copy()
        
        # Encrypt the password fields for storage
        if "password" in encrypted_creds and encrypted_creds["password"]:
            encrypted_creds["password"] = encrypt_password(encrypted_creds["password"])
        
        if "enable_password" in encrypted_creds and encrypted_creds["enable_password"]:
            encrypted_creds["enable_password"] = encrypt_password(encrypted_creds["enable_password"])
        
        # Store the encrypted credentials as a property on the device
        device.set_property("credentials", encrypted_creds)
        logger.debug(f"Migrated credentials to device property for device {device.id}")
    
    def _load_group_credentials(self):
        """Load group credentials from disk"""
        # Clear current workspace's group credentials
        self.workspace_credentials[self.workspace_name]["groups"] = {}
        
        # Get workspace directory
        workspace_group_dir = self._get_workspace_group_dir()
        if not workspace_group_dir:
            logger.error("Cannot load group credentials: No workspace directory available")
            return
        
        # Check if the credentials directory exists
        if not workspace_group_dir.exists():
            return
        
        # Iterate through credential files
        for file_path in workspace_group_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Extract group name from filename
                group_name = file_path.stem
                
                # Store credentials in workspace-specific cache
                self.workspace_credentials[self.workspace_name]["groups"][group_name] = data
                
                # Decrypt password (if needed)
                if "password" in data and data["password"]:
                    try:
                        data["password"] = decrypt_password(data["password"])
                    except:
                        # If decryption fails, keep encrypted
                        pass
                
                # Decrypt enable password (if needed)
                if "enable_password" in data and data["enable_password"]:
                    try:
                        data["enable_password"] = decrypt_password(data["enable_password"])
                    except:
                        # If decryption fails, keep encrypted
                        pass
                
            except Exception as e:
                logger.error(f"Error loading group credentials from {file_path}: {e}")
        
        # If any legacy group credentials exist, migrate them
        self._migrate_legacy_group_credentials()
    
    def _load_subnet_credentials(self):
        """Load subnet credentials from disk"""
        # Clear current workspace's subnet credentials
        self.workspace_credentials[self.workspace_name]["subnets"] = {}
        
        # Get workspace directory
        workspace_subnet_dir = self._get_workspace_subnet_dir()
        if not workspace_subnet_dir:
            logger.error("Cannot load subnet credentials: No workspace directory available")
            return
        
        # Check if the credentials directory exists
        if not workspace_subnet_dir.exists():
            return
        
        # Iterate through credential files
        for file_path in workspace_subnet_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Extract subnet from filename
                subnet = file_path.stem
                
                # Store credentials in workspace-specific cache
                self.workspace_credentials[self.workspace_name]["subnets"][subnet] = data
                
                # Decrypt password (if needed)
                if "password" in data and data["password"]:
                    try:
                        data["password"] = decrypt_password(data["password"])
                    except:
                        # If decryption fails, keep encrypted
                        pass
                
                # Decrypt enable password (if needed)
                if "enable_password" in data and data["enable_password"]:
                    try:
                        data["enable_password"] = decrypt_password(data["enable_password"])
                    except:
                        # If decryption fails, keep encrypted
                        pass
                
            except Exception as e:
                logger.error(f"Error loading subnet credentials from {file_path}: {e}")
        
        # If any legacy subnet credentials exist, migrate them
        self._migrate_legacy_subnet_credentials()
        
    def _migrate_legacy_group_credentials(self):
        """Migrate group credentials from legacy location to workspace"""
        # Check if legacy directory exists
        if not self.legacy_group_creds_dir.exists():
            return
            
        # Get workspace directory
        workspace_group_dir = self._get_workspace_group_dir()
        if not workspace_group_dir:
            logger.error("Cannot migrate legacy group credentials: No workspace directory available")
            return
            
        logger.info("Migrating legacy group credentials to workspace")
        
        # Iterate through credential files
        for file_path in self.legacy_group_creds_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Extract group name from filename
                group_name = file_path.stem
                
                # Save to workspace directory
                target_path = workspace_group_dir / file_path.name
                with open(target_path, "w") as f:
                    json.dump(data, f, indent=2)
                
                # Store in memory
                if group_name not in self.workspace_credentials[self.workspace_name]["groups"]:
                    # Decrypt passwords for in-memory use
                    data_copy = data.copy()
                    
                    if "password" in data_copy and data_copy["password"]:
                        try:
                            data_copy["password"] = decrypt_password(data_copy["password"])
                        except:
                            pass
                            
                    if "enable_password" in data_copy and data_copy["enable_password"]:
                        try:
                            data_copy["enable_password"] = decrypt_password(data_copy["enable_password"])
                        except:
                            pass
                            
                    self.workspace_credentials[self.workspace_name]["groups"][group_name] = data_copy
                
                logger.debug(f"Migrated group credentials for '{group_name}' to workspace")
                
                # Delete legacy file
                try:
                    file_path.unlink()
                    logger.debug(f"Deleted legacy group credential file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting legacy group credential file: {e}")
                    
            except Exception as e:
                logger.error(f"Error migrating group credentials from {file_path}: {e}")
        
        # Try to remove the legacy directory if empty
        try:
            if not any(self.legacy_group_creds_dir.iterdir()):
                self.legacy_group_creds_dir.rmdir()
                logger.info("Removed empty legacy group credentials directory")
        except Exception as e:
            logger.error(f"Error removing legacy group credentials directory: {e}")
            
    def _migrate_legacy_subnet_credentials(self):
        """Migrate subnet credentials from legacy location to workspace"""
        # Check if legacy directory exists
        if not self.legacy_subnet_creds_dir.exists():
            return
            
        # Get workspace directory
        workspace_subnet_dir = self._get_workspace_subnet_dir()
        if not workspace_subnet_dir:
            logger.error("Cannot migrate legacy subnet credentials: No workspace directory available")
            return
            
        logger.info("Migrating legacy subnet credentials to workspace")
        
        # Iterate through credential files
        for file_path in self.legacy_subnet_creds_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Extract subnet from filename
                subnet = file_path.stem
                
                # Save to workspace directory
                target_path = workspace_subnet_dir / file_path.name
                with open(target_path, "w") as f:
                    json.dump(data, f, indent=2)
                
                # Store in memory
                if subnet not in self.workspace_credentials[self.workspace_name]["subnets"]:
                    # Decrypt passwords for in-memory use
                    data_copy = data.copy()
                    
                    if "password" in data_copy and data_copy["password"]:
                        try:
                            data_copy["password"] = decrypt_password(data_copy["password"])
                        except:
                            pass
                            
                    if "enable_password" in data_copy and data_copy["enable_password"]:
                        try:
                            data_copy["enable_password"] = decrypt_password(data_copy["enable_password"])
                        except:
                            pass
                            
                    self.workspace_credentials[self.workspace_name]["subnets"][subnet] = data_copy
                
                logger.debug(f"Migrated subnet credentials for '{subnet}' to workspace")
                
                # Delete legacy file
                try:
                    file_path.unlink()
                    logger.debug(f"Deleted legacy subnet credential file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting legacy subnet credential file: {e}")
                    
            except Exception as e:
                logger.error(f"Error migrating subnet credentials from {file_path}: {e}")
        
        # Try to remove the legacy directory if empty
        try:
            if not any(self.legacy_subnet_creds_dir.iterdir()):
                self.legacy_subnet_creds_dir.rmdir()
                logger.info("Removed empty legacy subnet credentials directory")
        except Exception as e:
            logger.error(f"Error removing legacy subnet credentials directory: {e}")
    
    def save_credentials(self):
        """Save all credentials to disk"""
        # We don't need to save device credentials to files anymore
        # as they are now stored in device properties
        self._save_group_credentials()
        self._save_subnet_credentials()
    
    def _get_credentials_from_device(self, device):
        """Get credentials from device properties"""
        if not device:
            return {}
            
        # Get the credentials property
        encrypted_creds = device.get_property("credentials", {})
        if not encrypted_creds:
            return {}
            
        # Make a copy of the credentials to avoid modifying the original
        creds = encrypted_creds.copy()
        
        # Decrypt password
        if "password" in creds and creds["password"]:
            try:
                creds["password"] = decrypt_password(creds["password"])
            except Exception as e:
                logger.error(f"Error decrypting password for device {device.id}: {e}")
                creds["password"] = ""
        
        # Decrypt enable password
        if "enable_password" in creds and creds["enable_password"]:
            try:
                creds["enable_password"] = decrypt_password(creds["enable_password"])
            except Exception as e:
                logger.error(f"Error decrypting enable password for device {device.id}: {e}")
                creds["enable_password"] = ""
        
        return creds

    def _save_group_credentials(self):
        """Save group credentials to disk"""
        # Get workspace directory
        workspace_group_dir = self._get_workspace_group_dir()
        if not workspace_group_dir:
            logger.error("Cannot save group credentials: No workspace directory available")
            return False
        
        # Get credentials for current workspace
        ws_groups = self.workspace_credentials.get(self.workspace_name, {}).get("groups", {})
        
        # Iterate through credentials
        for group_name, creds in ws_groups.items():
            try:
                # Create a copy of the credentials
                creds_copy = creds.copy()
                
                # Encrypt password before saving
                if "password" in creds_copy and creds_copy["password"]:
                    creds_copy["password"] = encrypt_password(creds_copy["password"])
                
                # Encrypt enable password before saving
                if "enable_password" in creds_copy and creds_copy["enable_password"]:
                    creds_copy["enable_password"] = encrypt_password(creds_copy["enable_password"])
                
                # Save to file
                file_path = workspace_group_dir / f"{group_name}.json"
                with open(file_path, "w") as f:
                    json.dump(creds_copy, f, indent=2)
                
                logger.debug(f"Saved credentials for group {group_name} to workspace {self.workspace_name}")
            except Exception as e:
                logger.error(f"Error saving credentials for group {group_name}: {e}")
        
        return True
    
    def _save_subnet_credentials(self):
        """Save subnet credentials to disk"""
        # Get workspace directory
        workspace_subnet_dir = self._get_workspace_subnet_dir()
        if not workspace_subnet_dir:
            logger.error("Cannot save subnet credentials: No workspace directory available")
            return False
        
        # Get credentials for current workspace
        ws_subnets = self.workspace_credentials.get(self.workspace_name, {}).get("subnets", {})
        
        # Iterate through credentials
        for subnet, creds in ws_subnets.items():
            try:
                # Create a copy of the credentials
                creds_copy = creds.copy()
                
                # Encrypt password before saving
                if "password" in creds_copy and creds_copy["password"]:
                    creds_copy["password"] = encrypt_password(creds_copy["password"])
                
                # Encrypt enable password before saving
                if "enable_password" in creds_copy and creds_copy["enable_password"]:
                    creds_copy["enable_password"] = encrypt_password(creds_copy["enable_password"])
                
                # Save to file
                file_path = workspace_subnet_dir / f"{subnet}.json"
                with open(file_path, "w") as f:
                    json.dump(creds_copy, f, indent=2)
                
                logger.debug(f"Saved credentials for subnet {subnet} to workspace {self.workspace_name}")
            except Exception as e:
                logger.error(f"Error saving credentials for subnet {subnet}: {e}")
        
        return True
    
    def get_device_credentials(self, device_id, device_ip=None, groups=None):
        """Get credentials for a device
        
        Note: This method no longer falls back to group or subnet credentials.
        This allows the plugin to control the credential hierarchy itself.
        
        Args:
            device_id: The device ID
            device_ip: The device IP (not used for direct device credentials)
            groups: Device group names (not used for direct device credentials)
            
        Returns:
            dict: Credentials or None if not found
        """
        logger.debug(f"Getting credentials for device {device_id}")
        
        # First, check if the device exists and has credentials in its properties
        if self.device_manager:
            device = self.device_manager.get_device(device_id)
            if device:
                creds = self._get_credentials_from_device(device)
                if creds:
                    logger.debug(f"Found credentials in device properties for {device_id}")
                    return creds
        
        # For backward compatibility, check the legacy storage
        # but migrate to device properties if found
        if device_id in self.device_credentials:
            logger.debug(f"Found credentials in legacy storage for {device_id}")
            creds = self.device_credentials[device_id]
            
            # Try to migrate to device properties
            if self.device_manager:
                device = self.device_manager.get_device(device_id)
                if device:
                    self._migrate_credentials_to_device(device, creds)
                    # Remove from legacy storage after migration
                    del self.device_credentials[device_id]
                    # Delete legacy file
                    file_path = self.device_creds_dir / f"{device_id}.json"
                    if file_path.exists():
                        try:
                            file_path.unlink()
                            logger.debug(f"Migrated and deleted legacy credential file for device {device_id}")
                        except Exception as e:
                            logger.error(f"Error deleting legacy credential file for device {device_id}: {e}")
                
            return creds
        
        # No credentials found for this device
        return None
    
    def get_group_credentials(self, group_name):
        """Get credentials for a device group
        
        Args:
            group_name: The group name
            
        Returns:
            dict: Credentials or None if not found
        """
        logger.debug(f"Getting credentials for group {group_name} in workspace {self.workspace_name}")
        
        # Ensure group credentials are loaded from workspace
        if not self.workspace_credentials.get(self.workspace_name, {}).get("groups"):
            self._load_group_credentials()
            
        # Get from workspace-specific cache
        ws_groups = self.workspace_credentials.get(self.workspace_name, {}).get("groups", {})
        if group_name in ws_groups:
            return ws_groups[group_name]
        
        return None
    
    def get_subnet_credentials(self, subnet):
        """Get credentials for a subnet
        
        Args:
            subnet: The subnet in CIDR notation
            
        Returns:
            dict: Credentials or None if not found
        """
        logger.debug(f"Getting credentials for subnet {subnet} in workspace {self.workspace_name}")
        
        # Ensure subnet credentials are loaded from workspace
        if not self.workspace_credentials.get(self.workspace_name, {}).get("subnets"):
            self._load_subnet_credentials()
            
        # First, try exact match
        ws_subnets = self.workspace_credentials.get(self.workspace_name, {}).get("subnets", {})
        if subnet in ws_subnets:
            return ws_subnets[subnet]
        
        # Try to match by IP network
        try:
            target_network = ipaddress.ip_network(subnet, strict=False)
            
            for network_str, creds in ws_subnets.items():
                try:
                    network = ipaddress.ip_network(network_str, strict=False)
                    # Check if networks match (same network address and prefix)
                    if (network.network_address == target_network.network_address and 
                        network.prefixlen == target_network.prefixlen):
                        return creds
                except ValueError:
                    continue
        except ValueError:
            # Invalid subnet format
            pass
        
        return None
    
    def set_device_credentials(self, device_id, credentials):
        """Set credentials for a device"""
        # Check if we have a device manager reference
        if self.device_manager:
            logger.debug(f"Device manager exists, attempting to get device {device_id}")
            
            # Add detailed logging for debugging
            try:
                all_devices = self.device_manager.get_devices()
                device_count = len(all_devices)
                logger.debug(f"Device manager has {device_count} devices loaded")
                
                # Log some device IDs for comparison
                if device_count > 0:
                    device_ids = [d.id for d in all_devices[:5]]  # First 5 device IDs
                    logger.debug(f"Sample device IDs: {device_ids}")
                    
                    # Check if the requested device ID exists in the list
                    matching_devices = [d for d in all_devices if d.id == device_id]
                    logger.debug(f"Found {len(matching_devices)} devices with ID {device_id}")
                else:
                    logger.warning("No devices loaded in device manager")
            except Exception as e:
                logger.error(f"Error querying device manager state: {e}")
            
            device = self.device_manager.get_device(device_id)
            if device:
                logger.debug(f"Found device {device_id}, attempting to save credentials to device properties")
                # Create a copy of the credentials
                creds_copy = credentials.copy()
                
                # Encrypt password before saving
                if "password" in creds_copy and creds_copy["password"]:
                    creds_copy["password"] = encrypt_password(creds_copy["password"])
                
                # Encrypt enable password before saving
                if "enable_password" in creds_copy and creds_copy["enable_password"]:
                    creds_copy["enable_password"] = encrypt_password(creds_copy["enable_password"])
                
                try:
                    # Save to device property
                    device.set_property("credentials", creds_copy)
                    logger.debug(f"Saved credentials to device properties for device {device_id}")
                    
                    # Update in-memory cache
                    self.device_credentials[device_id] = credentials
                    
                    return True
                except Exception as e:
                    logger.error(f"Error saving to device properties for {device_id}: {e}")
            else:
                logger.warning(f"Device {device_id} not found via device manager")
        else:
            logger.warning(f"Device manager not available in credential store")
        
        # Get workspace directory
        workspace_device_dir = self._get_workspace_device_dir()
        if not workspace_device_dir:
            logger.error(f"Cannot save credentials for device {device_id}: No workspace directory available")
            return False
            
        # Fall back to workspace file-based storage
        logger.warning(f"Falling back to workspace file-based storage for device {device_id}")
        
        # Update in-memory cache
        self.device_credentials[device_id] = credentials
        
        # Save to file for backup
        try:
            # Create a copy of the credentials
            creds_copy = credentials.copy()
            
            # Encrypt password before saving
            if "password" in creds_copy and creds_copy["password"]:
                creds_copy["password"] = encrypt_password(creds_copy["password"])
            
            # Encrypt enable password before saving
            if "enable_password" in creds_copy and creds_copy["enable_password"]:
                creds_copy["enable_password"] = encrypt_password(creds_copy["enable_password"])
            
            # Save to workspace file
            file_path = workspace_device_dir / f"{device_id}.json"
            with open(file_path, "w") as f:
                json.dump(creds_copy, f, indent=2)
                
            logger.debug(f"Saved credentials to workspace file for device {device_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving credentials for device {device_id}: {e}")
            return False
    
    def delete_device_credentials(self, device_id):
        """Delete credentials for a device"""
        success = False
        
        # Delete from device property if available
        if self.device_manager:
            device = self.device_manager.get_device(device_id)
            if device and device.get_property("credentials", None) is not None:
                device.set_property("credentials", None)
                logger.debug(f"Deleted credentials from device properties for device {device_id}")
                success = True
        
        # Delete from workspace directory if exists
        workspace_device_dir = self._get_workspace_device_dir()
        if workspace_device_dir:
            workspace_file_path = workspace_device_dir / f"{device_id}.json"
            if workspace_file_path.exists():
                try:
                    workspace_file_path.unlink()
                    logger.debug(f"Deleted credential file from workspace for device {device_id}")
                    success = True
                except Exception as e:
                    logger.error(f"Error deleting workspace credential file for device {device_id}: {e}")
        
        # Remove from memory cache if exists
        if device_id in self.device_credentials:
            del self.device_credentials[device_id]
            success = True
        
        return success
    
    def set_group_credentials(self, group_name, credentials):
        """Set credentials for a group"""
        # Ensure workspace exists in cache
        if self.workspace_name not in self.workspace_credentials:
            self.workspace_credentials[self.workspace_name] = {
                "groups": {},
                "subnets": {}
            }
            
        # Store credentials in workspace-specific memory cache
        self.workspace_credentials[self.workspace_name]["groups"][group_name] = credentials
        logger.debug(f"Setting credentials for group {group_name} in workspace {self.workspace_name}")
        
        # Save to workspace
        self._save_group_credentials()
        
        return True
    
    def delete_group_credentials(self, group_name):
        """Delete credentials for a group"""
        # Check if group exists in current workspace
        ws_data = self.workspace_credentials.get(self.workspace_name, {})
        ws_groups = ws_data.get("groups", {})
        
        if group_name in ws_groups:
            # Remove from memory
            del self.workspace_credentials[self.workspace_name]["groups"][group_name]
            
            # Remove file from workspace if it exists
            workspace_group_dir = self._get_workspace_group_dir()
            if workspace_group_dir:
                file_path = workspace_group_dir / f"{group_name}.json"
                if file_path.exists():
                    try:
                        file_path.unlink()
                        logger.debug(f"Deleted credential file for group {group_name}")
                    except Exception as e:
                        logger.error(f"Error deleting credential file for group {group_name}: {e}")
            
            return True
        
        return False
    
    def set_subnet_credentials(self, subnet, credentials):
        """Set credentials for a subnet"""
        # Validate subnet
        try:
            ipaddress.ip_network(subnet, strict=False)
        except ValueError:
            logger.error(f"Invalid subnet: {subnet}")
            return False
        
        # Ensure workspace exists in cache
        if self.workspace_name not in self.workspace_credentials:
            self.workspace_credentials[self.workspace_name] = {
                "groups": {},
                "subnets": {}
            }
            
        # Store credentials in workspace-specific memory cache
        self.workspace_credentials[self.workspace_name]["subnets"][subnet] = credentials
        logger.debug(f"Setting credentials for subnet {subnet} in workspace {self.workspace_name}")
        
        # Save to workspace
        self._save_subnet_credentials()
        
        return True
    
    def delete_subnet_credentials(self, subnet):
        """Delete credentials for a subnet"""
        # Check if subnet exists in current workspace
        ws_data = self.workspace_credentials.get(self.workspace_name, {})
        ws_subnets = ws_data.get("subnets", {})
        
        if subnet in ws_subnets:
            # Remove from memory
            del self.workspace_credentials[self.workspace_name]["subnets"][subnet]
            
            # Remove file from workspace if it exists
            workspace_subnet_dir = self._get_workspace_subnet_dir()
            if workspace_subnet_dir:
                file_path = workspace_subnet_dir / f"{subnet}.json"
                if file_path.exists():
                    try:
                        file_path.unlink()
                        logger.debug(f"Deleted credential file for subnet {subnet}")
                    except Exception as e:
                        logger.error(f"Error deleting credential file for subnet {subnet}: {e}")
            
            return True
        
        return False
    
    def get_all_device_credentials(self):
        """Get all device credentials"""
        # Combine legacy stored credentials with device property-based credentials
        result = self.device_credentials.copy()
        
        # Add credentials from device properties if device manager is available
        if self.device_manager:
            for device in self.device_manager.get_devices():
                creds = self._get_credentials_from_device(device)
                if creds:
                    result[device.id] = creds
        
        return result
    
    def get_all_group_credentials(self):
        """Get all group credentials"""
        # Ensure credentials are loaded for current workspace
        if not self.workspace_credentials.get(self.workspace_name, {}).get("groups"):
            self._load_group_credentials()
            
        # Return group credentials for current workspace
        return self.workspace_credentials.get(self.workspace_name, {}).get("groups", {})
    
    def get_all_subnet_credentials(self):
        """Get all subnet credentials"""
        # Ensure credentials are loaded for current workspace
        if not self.workspace_credentials.get(self.workspace_name, {}).get("subnets"):
            self._load_subnet_credentials()
            
        # Return subnet credentials for current workspace
        return self.workspace_credentials.get(self.workspace_name, {}).get("subnets", {}) 