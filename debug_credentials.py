#!/usr/bin/env python3
"""Debug script for credential storage issues"""

import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Add src to path for imports
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

# Import directly from file paths
sys.path.insert(0, str(current_dir / "plugins" / "command_manager" / "utils"))
sys.path.insert(0, str(current_dir / "src" / "core"))

from credential_store import CredentialStore
from device_manager import Device

def main():
    print("=== Credential Debug Script ===")
    
    # Create a simple test device
    test_device = Device(device_id="test-device-123")
    test_device.set_property("alias", "Test Device")
    test_device.set_property("ip_address", "192.168.1.100")
    
    print(f"Created test device: {test_device.id}")
    print(f"Device properties: {test_device.get_properties()}")
    
    # Create credential store
    data_dir = Path("plugins/command_manager/data")
    cred_store = CredentialStore(data_dir)
    
    print(f"Created credential store with data dir: {data_dir}")
    
    # Test credentials
    test_credentials = {
        "connection_type": "ssh",
        "username": "testuser",
        "password": "testpass",
        "enable_password": "enablepass"
    }
    
    print(f"Test credentials: {test_credentials}")
    
    # Test device lookup without device manager
    print("\n=== Testing without device manager ===")
    result = cred_store.set_device_credentials(test_device.id, test_credentials)
    print(f"Set credentials result: {result}")
    
    retrieved_creds = cred_store.get_device_credentials(test_device.id)
    print(f"Retrieved credentials: {retrieved_creds}")
    
    # Test with mock device manager
    print("\n=== Testing with mock device manager ===")
    
    class MockDeviceManager:
        def __init__(self):
            self.devices = {test_device.id: test_device}
            
        def get_devices(self):
            return list(self.devices.values())
            
        def get_device(self, device_id):
            return self.devices.get(device_id)
            
        def get_current_workspace_name(self):
            return "default test"
            
        def get_workspace_dir(self):
            return str(Path.cwd() / "config" / "workspaces" / "default test")
    
    mock_dm = MockDeviceManager()
    cred_store.set_device_manager(mock_dm)
    
    print(f"Set device manager with {len(mock_dm.get_devices())} devices")
    
    # Test device lookup with device manager
    result2 = cred_store.set_device_credentials(test_device.id, test_credentials)
    print(f"Set credentials result with device manager: {result2}")
    
    retrieved_creds2 = cred_store.get_device_credentials(test_device.id)
    print(f"Retrieved credentials with device manager: {retrieved_creds2}")
    
    # Test device property storage
    stored_creds = test_device.get_property("credentials")
    print(f"Credentials stored on device: {stored_creds}")
    
    print("\n=== Debug completed ===")

if __name__ == "__main__":
    main() 