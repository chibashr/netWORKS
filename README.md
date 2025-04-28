# netWORKS - Network Scanning & Documentation Suite

A modular network scanner and documentation tool designed for IT professionals.

## Quick Start

### Windows:
- Just double-click `start.py` to run the application
- Alternatively, run `run.bat` from the command line

### Linux/macOS:
```bash
python3 start.py
```

First-time setup will automatically create a virtual environment and install all dependencies.

### Troubleshooting Installation Issues:
If you encounter dependency installation problems during first-time setup:
- Run `repair_dependencies.bat` (Windows) or `python scripts/repair_dependencies.py` (Linux/macOS)
- This utility will diagnose and repair common installation issues
- For detailed logs, check the `logs` directory after running the repair tool

## Documentation

Complete documentation is available in the `docs/` folder, including:
- User Guide
- Plugin Development Guide
- API Reference

## Overview

netWORKS is a comprehensive network scanning application with a modular architecture. It provides a unified interface for discovering, scanning, and documenting network devices while supporting various protocols and scanning techniques. Its plugin system allows for easy extension with additional functionality.

## Key Features

- **Network Discovery**: Identify devices on the network using multiple discovery protocols
- **Device Scanning**: Collect detailed information from discovered devices
- **Asset Management**: Track and manage network devices with detailed information
- **Report Generation**: Create comprehensive reports about network assets
- **Vulnerability Assessment**: Basic security scanning and vulnerability checks
- **Plugin System**: Extend functionality through a simple plugin architecture

## Technical Stack

- Python 3.9+
- PyQt5/PySide6 for the UI
- SQLite for local data storage
- Multiple network libraries (scapy, nmap, etc.)

## Architecture

netWORKS follows a modular architecture with the following components:

- **Core**: The main application framework and services
- **UI**: User interface components
- **Plugins**: Modular extensions for specific functionality
- **Database**: Data storage and management components
- **Utils**: Utility functions and helpers

## Core Features

- Device Discovery (ARP, ICMP, mDNS, NetBIOS)
- Port Scanning
- Service Identification
- OS Detection
- Network Mapping
- Basic Vulnerability Scanning

## Optional Plugins

- Advanced Security Scanner
- Network Topology Visualization
- Automated Documentation Generator
- Configuration Management
- Compliance Checker

## Installation

If you're running from source:

1. Make sure Python 3.9+ is installed
2. Clone or download this repository
3. Run `start.py`
4. First-time setup will automatically:
   - Create a Python virtual environment
   - Install required dependencies
   - Set up core plugins

For binary distributions, just run the provided installer.

### Common Installation Issues:

If you encounter problems during installation:
1. Make sure Python 3.9+ is correctly installed and in your PATH
2. Check that you have proper permissions to create directories and files
3. Some dependencies may require additional system packages:
   - For network scanning: nmap, libpcap
   - For UI components: Qt libraries
4. Use the dependency repair tool if you have issues with the Python environment:
   - Windows: Run `repair_dependencies.bat`
   - Linux/macOS: Run `python scripts/repair_dependencies.py`

## Usage

1. **Start the Application**: Run `start.py`
2. **Configure Settings**: Set up your preferences in the Settings panel
3. **Run a Network Scan**: Use the Scan panel to start a network discovery
4. **View Results**: Examine discovered devices in the Results panel
5. **Generate Reports**: Create documentation from the Reports panel

See the `docs/` directory for detailed usage instructions.

## System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux (major distributions)
- **CPU**: Dual-core processor or better
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 500MB for installation, plus space for scan data
- **Python**: Version 3.9 or newer (if running from source)
- **Network**: Ethernet or WiFi connection

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

Special thanks to the open-source community for the various libraries that make this project possible. 