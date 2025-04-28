#!/usr/bin/env python3
# Network Device Manager - Credential Manager

import os
import json
import base64
import getpass
import platform
from pathlib import Path

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
    from Cryptodome.Random import get_random_bytes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

class CredentialManager:
    """
    Manages device credentials with secure storage.
    Encrypts sensitive information before storing on disk.
    """
    
    def __init__(self, config_dir):
        self.config_dir = Path(config_dir)
        self.credentials_file = self.config_dir / "credentials.enc"
        self.key_file = self.config_dir / "key.dat"
        
        # Initialize encryption key
        self._initialize_encryption()
        
        # Load credentials
        self.credentials = self._load_credentials()
    
    def _initialize_encryption(self):
        """Initialize encryption key."""
        if not CRYPTO_AVAILABLE:
            # If crypto libraries are not available, we'll use base64 encoding
            # (not secure, but better than plaintext)
            self.encryption_key = b'netWORKSdefaultkey'
            return
            
        if not self.key_file.exists():
            # Generate a random key
            try:
                # Try to use system-specific secure storage mechanisms
                self._generate_key()
            except Exception:
                # Fall back to file-based key
                self.encryption_key = get_random_bytes(32)
                with open(self.key_file, 'wb') as f:
                    f.write(self.encryption_key)
        else:
            # Load existing key
            with open(self.key_file, 'rb') as f:
                self.encryption_key = f.read()
    
    def _generate_key(self):
        """Generate a key based on machine-specific information."""
        # This is a simplified version; in production, use platform-specific secure storage
        machine_id = platform.node() + getpass.getuser()
        self.encryption_key = self._derive_key(machine_id.encode())
    
    def _derive_key(self, seed):
        """Derive an encryption key from a seed."""
        if CRYPTO_AVAILABLE:
            import hashlib
            return hashlib.sha256(seed).digest()
        else:
            # Simple fallback if crypto libraries are not available
            return seed[:32].ljust(32, b'0')
    
    def _encrypt(self, data):
        """Encrypt data."""
        if not CRYPTO_AVAILABLE:
            # Simple encoding if crypto is not available
            return base64.b64encode(data.encode()).decode()
            
        cipher = AES.new(self.encryption_key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(data.encode(), AES.block_size))
        iv = cipher.iv
        return base64.b64encode(iv + ct_bytes).decode()
    
    def _decrypt(self, encrypted_data):
        """Decrypt data."""
        if not CRYPTO_AVAILABLE:
            # Simple decoding if crypto is not available
            return base64.b64decode(encrypted_data.encode()).decode()
            
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            iv = encrypted_bytes[:16]
            ct = encrypted_bytes[16:]
            cipher = AES.new(self.encryption_key, AES.MODE_CBC, iv)
            pt = unpad(cipher.decrypt(ct), AES.block_size)
            return pt.decode()
        except Exception as e:
            print(f"Error decrypting data: {str(e)}")
            return ""
    
    def _load_credentials(self):
        """Load credentials from disk."""
        if not self.credentials_file.exists():
            return {}
            
        try:
            with open(self.credentials_file, 'r') as f:
                encrypted_data = f.read()
                
            if not encrypted_data:
                return {}
                
            decrypted_data = self._decrypt(encrypted_data)
            return json.loads(decrypted_data)
        except Exception as e:
            print(f"Error loading credentials: {str(e)}")
            return {}
    
    def save(self):
        """Save credentials to disk."""
        if not self.credentials:
            return
            
        try:
            encrypted_data = self._encrypt(json.dumps(self.credentials))
            
            with open(self.credentials_file, 'w') as f:
                f.write(encrypted_data)
        except Exception as e:
            print(f"Error saving credentials: {str(e)}")
    
    def get_credentials(self, device_id):
        """Get credentials for a device."""
        return self.credentials.get(device_id, None)
    
    def get_credentials_by_subnet(self, subnet):
        """Get credentials for a subnet."""
        return self.credentials.get(f"subnet:{subnet}", None)
    
    def get_credentials_by_group(self, group):
        """Get credentials for a device group."""
        return self.credentials.get(f"group:{group}", None)
    
    def get_default_credentials(self):
        """Get default credentials."""
        return self.credentials.get("default", None)
    
    def set_credentials(self, device_id, username, password, enable_password=None):
        """Set credentials for a device."""
        self.credentials[device_id] = {
            "username": username,
            "password": password,
            "enable_password": enable_password
        }
        self.save()
    
    def set_credentials_by_subnet(self, subnet, username, password, enable_password=None):
        """Set credentials for a subnet."""
        self.credentials[f"subnet:{subnet}"] = {
            "username": username,
            "password": password,
            "enable_password": enable_password
        }
        self.save()
    
    def set_credentials_by_group(self, group, username, password, enable_password=None):
        """Set credentials for a device group."""
        self.credentials[f"group:{group}"] = {
            "username": username,
            "password": password,
            "enable_password": enable_password
        }
        self.save()
    
    def set_default_credentials(self, username, password, enable_password=None):
        """Set default credentials."""
        self.credentials["default"] = {
            "username": username,
            "password": password,
            "enable_password": enable_password
        }
        self.save()
    
    def remove_credentials(self, device_id):
        """Remove credentials for a device."""
        if device_id in self.credentials:
            del self.credentials[device_id]
            self.save()
    
    def get_all_credential_entries(self):
        """Get all credential entries (without the actual credentials)."""
        entries = []
        for key in self.credentials.keys():
            credential_type = "Device"
            name = key
            
            if key == "default":
                credential_type = "Default"
                name = "Global Default"
            elif key.startswith("subnet:"):
                credential_type = "Subnet"
                name = key[7:]  # Remove "subnet:" prefix
            elif key.startswith("group:"):
                credential_type = "Group"
                name = key[6:]  # Remove "group:" prefix
                
            entries.append({
                "id": key,
                "type": credential_type,
                "name": name
            })
            
        return entries 