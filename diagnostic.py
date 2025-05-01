#!/usr/bin/env python3
"""
Diagnostic script to check package imports
"""

import sys
import traceback

def check_imports():
    """Check if all required packages can be imported."""
    print("Starting package import checks...")
    
    # List of packages to check
    packages = [
        'PySide6',
        'PyQt5',
        'netifaces',
        'scapy',
        'nmap',
        'psutil',
        'PyInstaller',
        'cryptography',
        'wmi',
        'pysnmp',
        'whois',
        'dns',
        'netaddr',
        'netmiko',
        'requests',
        'dotenv',
        'pytest',
        'black',
        'flake8',
        'shiboken6'
    ]
    
    failures = []
    
    for pkg in packages:
        try:
            print(f"Attempting to import {pkg}...")
            __import__(pkg)
            print(f"✓ Successfully imported {pkg}")
        except ImportError as e:
            print(f"✗ FAILED to import {pkg}: {str(e)}")
            traceback.print_exc()
            failures.append((pkg, str(e)))
    
    if failures:
        print("\nMissing or problematic packages:")
        for pkg, error in failures:
            print(f"  - {pkg}: {error}")
        return False
    else:
        print("\nAll packages successfully imported!")
        return True

if __name__ == "__main__":
    success = check_imports()
    if not success:
        print("\nSome packages failed to import. You may need to install or repair them.")
        sys.exit(1)
    else:
        print("\nAll dependencies are properly installed.")
        sys.exit(0) 