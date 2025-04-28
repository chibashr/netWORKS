#!/usr/bin/env python3
# Core Plugin Setup Script
# Sets up the core plugins required for netWORKS

import os
import sys
import shutil
from pathlib import Path
import subprocess
import json

def ensure_dir(path):
    """Ensure a directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)

def main():
    print("Setting up core plugins...")
    
    # Determine the base directory (project root)
    base_dir = Path(__file__).resolve().parent.parent
    plugins_dir = base_dir / "plugins" / "core"
    
    # Core plugins that should be installed
    core_plugins = [
        "base-network-scanner"
    ]
    
    # Create plugins directory structure if it doesn't exist
    ensure_dir(plugins_dir)
    
    # Check if example plugin exists in docs
    example_plugin_dir = base_dir / "docs" / "plugins" / "example_plugin"
    if example_plugin_dir.exists():
        # Copy example plugin structure for any missing core plugins
        for plugin_name in core_plugins:
            plugin_dir = plugins_dir / plugin_name
            
            # If plugin directory doesn't exist, create it with basic structure
            if not plugin_dir.exists():
                print(f"Creating core plugin: {plugin_name}")
                ensure_dir(plugin_dir)
                ensure_dir(plugin_dir / "assets")
                ensure_dir(plugin_dir / "ui")
                
                # Create __init__.py file
                with open(plugin_dir / "__init__.py", "w") as f:
                    f.write(f"""# {plugin_name} Core Plugin
from .plugin import Plugin

__all__ = ["Plugin"]
""")
                
                # Create plugin.py file
                with open(plugin_dir / "plugin.py", "w") as f:
                    f.write(f"""# {plugin_name} Core Plugin Implementation
class Plugin:
    def __init__(self, api):
        self.api = api
        self.name = "{plugin_name}"
        self.description = "Core network scanning plugin"
        self.version = "1.0.0"
        self.author = "netWORKS Team"
        
    def initialize(self):
        # Register with the application
        self.api.register_plugin(self)
        return True
        
    def cleanup(self):
        # Perform cleanup when plugin is disabled
        pass
""")
                
                # Create plugin.json manifest
                with open(plugin_dir / "plugin.json", "w") as f:
                    json.dump({
                        "name": plugin_name,
                        "description": "Core network scanning plugin",
                        "version": "1.0.0",
                        "author": "netWORKS Team",
                        "core": True,
                        "dependencies": []
                    }, f, indent=4)
            else:
                print(f"Core plugin already exists: {plugin_name}")
    else:
        print("Example plugin template not found in docs/plugins. Using basic structure instead.")
        # Create basic structure for core plugins
        for plugin_name in core_plugins:
            plugin_dir = plugins_dir / plugin_name
            if not plugin_dir.exists():
                print(f"Creating basic core plugin: {plugin_name}")
                ensure_dir(plugin_dir)
                
                # Create plugin.json manifest
                with open(plugin_dir / "plugin.json", "w") as f:
                    json.dump({
                        "name": plugin_name,
                        "description": "Core network scanning plugin",
                        "version": "1.0.0",
                        "author": "netWORKS Team",
                        "core": True,
                        "dependencies": []
                    }, f, indent=4)
    
    print("Core plugins setup complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 