#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Encryption utilities for Command Manager plugin
"""

import os
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


# Generate a static key based on machine-specific information
# This is not perfect security, but better than storing in plaintext
def _get_encryption_key():
    """Get a static encryption key"""
    # Machine-specific values
    machine_id = os.getenv('COMPUTERNAME', '') or os.getenv('HOSTNAME', '')
    user_id = os.getenv('USERNAME', '') or os.getenv('USER', '')
    
    # Additional static salt
    salt = "NetWORKS_Command_Manager_Plugin"
    
    # Combine and hash
    key_material = f"{machine_id}:{user_id}:{salt}"
    key = hashlib.sha256(key_material.encode()).digest()
    
    return key


def encrypt_password(password):
    """Encrypt a password"""
    if not password:
        return ""
        
    try:
        # Get encryption key
        key = _get_encryption_key()
        
        # Create cipher
        cipher = AES.new(key, AES.MODE_CBC)
        
        # Pad the password and encrypt
        ct_bytes = cipher.encrypt(pad(password.encode('utf-8'), AES.block_size))
        
        # Combine IV and ciphertext
        iv = base64.b64encode(cipher.iv).decode('utf-8')
        ct = base64.b64encode(ct_bytes).decode('utf-8')
        
        # Return as single string
        return f"{iv}:{ct}"
    except Exception as e:
        # If encryption fails, return original password
        # This is not ideal, but prevents data loss
        return password


def decrypt_password(encrypted_password):
    """Decrypt a password"""
    if not encrypted_password:
        return ""
        
    try:
        # Check if password is encrypted (contains IV and ciphertext)
        if ":" not in encrypted_password:
            return encrypted_password
            
        # Split IV and ciphertext
        iv, ct = encrypted_password.split(":", 1)
        
        # Decode from base64
        iv = base64.b64decode(iv)
        ct = base64.b64decode(ct)
        
        # Get encryption key
        key = _get_encryption_key()
        
        # Create cipher
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # Decrypt and unpad
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        
        # Return as string
        return pt.decode('utf-8')
    except Exception as e:
        # If decryption fails, return original password
        # This is not ideal, but prevents data loss
        return encrypted_password 