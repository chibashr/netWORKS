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
        
        # Credential directories
        self.device_creds_dir = data_dir / "credentials" / "devices"
        self.device_creds_dir.mkdir(parents=True, exist_ok=True)
        
        self.group_creds_dir = data_dir / "credentials" / "groups"
        self.group_creds_dir.mkdir(parents=True, exist_ok=True)
        
        self.subnet_creds_dir = data_dir / "credentials" / "subnets"
        self.subnet_creds_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache
        self.device_credentials = {}
        self.group_credentials = {}
        self.subnet_credentials = {}
        
        # Load credentials
        self._load_credentials()
        
    def _load_credentials(self):
        """Load all credentials from disk"""
        self._load_device_credentials()
        self._load_group_credentials()
        self._load_subnet_credentials()
        
    def _load_device_credentials(self):
        """Load device credentials from disk"""
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
                
            except Exception as e:
                logger.error(f"Error loading device credentials from {file_path}: {e}")
    
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
        self._save_device_credentials()
        self._save_group_credentials()
        self._save_subnet_credentials()
    
    def _save_device_credentials(self):
        """Save device credentials to disk"""
        # Check if the credentials directory exists
        if not self.device_creds_dir.exists():
            self.device_creds_dir.mkdir(parents=True, exist_ok=True)
        
        # Iterate through credentials
        for device_id, creds in self.device_credentials.items():
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
                file_path = self.device_creds_dir / f"{device_id}.json"
                with open(file_path, "w") as f:
                    json.dump(creds_copy, f, indent=2)
            
            except Exception as e:
                logger.error(f"Error saving credentials for device {device_id}: {e}")
    
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
        # First check device-specific credentials
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
        self.device_credentials[device_id] = credentials
        self._save_device_credentials()
        return True
    
    def delete_device_credentials(self, device_id):
        """Delete credentials for a device"""
        if device_id in self.device_credentials:
            del self.device_credentials[device_id]
            
            # Remove file if it exists
            file_path = self.device_creds_dir / f"{device_id}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.error(f"Error deleting credential file for device {device_id}: {e}")
            
            return True
        
        return False
    
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
        try:
            # Validate subnet
            subnet_obj = ipaddress.ip_network(subnet, strict=False)
            subnet_str = str(subnet_obj)
            
            self.subnet_credentials[subnet_str] = credentials
            self._save_subnet_credentials()
            return True
            
        except ValueError:
            # Invalid subnet
            logger.error(f"Invalid subnet format: {subnet}")
            return False
    
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
        return self.device_credentials
    
    def get_all_group_credentials(self):
        """Get all group credentials"""
        return self.group_credentials
    
    def get_all_subnet_credentials(self):
        """Get all subnet credentials"""
        return self.subnet_credentials 