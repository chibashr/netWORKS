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
        
        # Keep these directories for backward compatibility and group/subnet credentials
        self.group_creds_dir = data_dir / "credentials" / "groups"
        self.group_creds_dir.mkdir(parents=True, exist_ok=True)
        
        self.subnet_creds_dir = data_dir / "credentials" / "subnets"
        self.subnet_creds_dir.mkdir(parents=True, exist_ok=True)
        
        # The device_creds_dir is maintained only for backward compatibility
        self.device_creds_dir = data_dir / "credentials" / "devices"
        self.device_creds_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache
        self.device_credentials = {}  # Only used for backward compatibility now
        self.group_credentials = {}
        self.subnet_credentials = {}
        
        # Device manager reference (will be set by the plugin)
        self.device_manager = None
        
        # Load group and subnet credentials
        self._load_credentials()
        
    def set_device_manager(self, device_manager):
        """Set the device manager reference"""
        self.device_manager = device_manager
        logger.debug(f"CredentialStore: Device manager reference set")
        
    def _load_credentials(self):
        """Load all credentials from disk"""
        self._load_device_credentials()  # For backward compatibility
        self._load_group_credentials()
        self._load_subnet_credentials()
        
    def _load_device_credentials(self):
        """
        Load device credentials from disk for backward compatibility
        Note: These will be migrated to device properties when accessed
        """
        self.device_credentials = {}
        
        # Check if the credentials directory exists
        if not self.device_creds_dir.exists():
            return
        
        # Iterate through credential files
        for file_path in self.device_creds_dir.glob("*.json"):
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
                        # Delete the file after migration
                        try:
                            file_path.unlink()
                            logger.debug(f"Migrated and deleted credential file for device {device_id}")
                        except Exception as e:
                            logger.error(f"Error deleting credential file for device {device_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error loading device credentials from {file_path}: {e}")
    
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
        self.group_credentials = {}
        
        # Check if the credentials directory exists
        if not self.group_creds_dir.exists():
            return
        
        # Iterate through credential files
        for file_path in self.group_creds_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Extract group name from filename
                group_name = file_path.stem
                
                # Store credentials
                self.group_credentials[group_name] = data
                
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
    
    def _load_subnet_credentials(self):
        """Load subnet credentials from disk"""
        self.subnet_credentials = {}
        
        # Check if the credentials directory exists
        if not self.subnet_creds_dir.exists():
            return
        
        # Iterate through credential files
        for file_path in self.subnet_creds_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Extract subnet from filename
                subnet = file_path.stem
                
                # Store credentials
                self.subnet_credentials[subnet] = data
                
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
        # Check if the credentials directory exists
        if not self.group_creds_dir.exists():
            self.group_creds_dir.mkdir(parents=True, exist_ok=True)
        
        # Iterate through credentials
        for group_name, creds in self.group_credentials.items():
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
                file_path = self.group_creds_dir / f"{group_name}.json"
                with open(file_path, "w") as f:
                    json.dump(creds_copy, f, indent=2)
            
            except Exception as e:
                logger.error(f"Error saving credentials for group {group_name}: {e}")
    
    def _save_subnet_credentials(self):
        """Save subnet credentials to disk"""
        # Check if the credentials directory exists
        if not self.subnet_creds_dir.exists():
            self.subnet_creds_dir.mkdir(parents=True, exist_ok=True)
        
        # Iterate through credentials
        for subnet, creds in self.subnet_credentials.items():
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
                file_path = self.subnet_creds_dir / f"{subnet}.json"
                with open(file_path, "w") as f:
                    json.dump(creds_copy, f, indent=2)
            
            except Exception as e:
                logger.error(f"Error saving credentials for subnet {subnet}: {e}")
    
    def get_device_credentials(self, device_id, device_ip=None, groups=None):
        """
        Get credentials for a device with fallback to group or subnet credentials
        
        Args:
            device_id: The device ID
            device_ip: The device IP address (for subnet matching)
            groups: List of groups the device belongs to
            
        Returns:
            dict: Credentials dictionary or empty dict if no credentials found
        """
        # First check if we have a device manager reference
        if self.device_manager:
            device = self.device_manager.get_device(device_id)
            if device:
                # Check for credentials in device properties
                device_creds = self._get_credentials_from_device(device)
                if device_creds:
                    return device_creds
        
        # Fall back to legacy file-based credentials for backward compatibility
        if device_id in self.device_credentials:
            return self.device_credentials[device_id]
        
        # Next, check if device belongs to any groups with credentials
        if groups:
            for group in groups:
                if group in self.group_credentials:
                    return self.group_credentials[group]
        
        # Finally, check if device IP falls within any subnets with credentials
        if device_ip:
            try:
                device_ip_obj = ipaddress.ip_address(device_ip)
                for subnet, creds in self.subnet_credentials.items():
                    try:
                        subnet_obj = ipaddress.ip_network(subnet, strict=False)
                        if device_ip_obj in subnet_obj:
                            return creds
                    except ValueError:
                        # Invalid subnet
                        continue
            except ValueError:
                # Invalid IP address
                pass
        
        # No credentials found
        return {}
    
    def set_device_credentials(self, device_id, credentials):
        """Set credentials for a device"""
        # Check if we have a device manager reference
        if self.device_manager:
            device = self.device_manager.get_device(device_id)
            if device:
                # Create a copy of the credentials
                creds_copy = credentials.copy()
                
                # Encrypt password before saving
                if "password" in creds_copy and creds_copy["password"]:
                    creds_copy["password"] = encrypt_password(creds_copy["password"])
                
                # Encrypt enable password before saving
                if "enable_password" in creds_copy and creds_copy["enable_password"]:
                    creds_copy["enable_password"] = encrypt_password(creds_copy["enable_password"])
                
                # Save to device property
                device.set_property("credentials", creds_copy)
                logger.debug(f"Saved credentials to device properties for device {device_id}")
                return True
        
        # Fall back to legacy file-based storage
        logger.warning(f"Falling back to legacy credential storage for device {device_id}")
        self.device_credentials[device_id] = credentials
        
        # Save to file for backward compatibility
        try:
            # Create a copy of the credentials
            creds_copy = credentials.copy()
            
            # Encrypt password before saving
            if "password" in creds_copy and creds_copy["password"]:
                creds_copy["password"] = encrypt_password(creds_copy["password"])
            
            # Encrypt enable password before saving
            if "enable_password" in creds_copy and creds_copy["enable_password"]:
                creds_copy["enable_password"] = encrypt_password(creds_copy["enable_password"])
            
            # Save to file
            file_path = self.device_creds_dir / f"{device_id}.json"
            with open(file_path, "w") as f:
                json.dump(creds_copy, f, indent=2)
                
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
        
        # Also delete from legacy storage if it exists
        if device_id in self.device_credentials:
            del self.device_credentials[device_id]
            success = True
            
            # Remove file if it exists
            file_path = self.device_creds_dir / f"{device_id}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.debug(f"Deleted credential file for device {device_id}")
                except Exception as e:
                    logger.error(f"Error deleting credential file for device {device_id}: {e}")
        
        return success
    
    def set_group_credentials(self, group_name, credentials):
        """Set credentials for a group"""
        self.group_credentials[group_name] = credentials
        self._save_group_credentials()
        return True
    
    def delete_group_credentials(self, group_name):
        """Delete credentials for a group"""
        if group_name in self.group_credentials:
            del self.group_credentials[group_name]
            
            # Remove file if it exists
            file_path = self.group_creds_dir / f"{group_name}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
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
            
        self.subnet_credentials[subnet] = credentials
        self._save_subnet_credentials()
        return True
    
    def delete_subnet_credentials(self, subnet):
        """Delete credentials for a subnet"""
        if subnet in self.subnet_credentials:
            del self.subnet_credentials[subnet]
            
            # Remove file if it exists
            file_path = self.subnet_creds_dir / f"{subnet}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
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
        return self.group_credentials
    
    def get_all_subnet_credentials(self):
        """Get all subnet credentials"""
        return self.subnet_credentials 