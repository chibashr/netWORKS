#!/usr/bin/env python3
# netWORKS - Version Management

import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Current application version
VERSION = {
    "major": 1,
    "minor": 0,
    "patch": 0,
    "build": 0,
    "stage": "alpha",  # alpha, beta, rc, release
    "date": datetime.now().strftime("%Y-%m-%d"),
}

# Version string representation
VERSION_STRING = f"{VERSION['major']}.{VERSION['minor']}.{VERSION['patch']}"
if VERSION['stage'] != "release":
    VERSION_STRING += f"-{VERSION['stage']}"
if VERSION['build'] > 0:
    VERSION_STRING += f".{VERSION['build']}"

# Update the path to point to docs folder
MANIFEST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "version_manifest.json")
CHANGELOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "CHANGELOG.md")

logger = logging.getLogger(__name__)

def get_version_string():
    """Get current version as a string."""
    return VERSION_STRING

def get_version():
    """Get current version information as a dictionary."""
    return VERSION.copy()

def load_manifest():
    """Load version manifest from file."""
    try:
        if os.path.exists(MANIFEST_FILE):
            with open(MANIFEST_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default manifest
            manifest = {
                "version": VERSION,
                "version_string": VERSION_STRING,
                "build_date": VERSION["date"],
                "release_notes": "Initial version",
                "release_type": VERSION["stage"],
                "compatibility": {
                    "min_plugin_api": "1.0.0",
                    "min_python_version": "3.9.0"
                },
                "history": [
                    {
                        "version": VERSION_STRING,
                        "date": VERSION["date"],
                        "changes": ["Initial release"]
                    }
                ]
            }
            save_manifest(manifest)
            return manifest
    except Exception as e:
        logger.error(f"Error loading version manifest: {str(e)}")
        return None

def save_manifest(manifest):
    """Save version manifest to file."""
    try:
        with open(MANIFEST_FILE, 'w') as f:
            json.dump(manifest, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving version manifest: {str(e)}")
        return False

def update_version(major=None, minor=None, patch=None, build=None, stage=None):
    """Update the version information."""
    manifest = load_manifest()
    if not manifest:
        logger.error("Failed to load manifest for version update")
        return False
    
    # Create a new version entry based on the current version
    new_version = manifest["version"].copy()
    
    # Update version components if provided
    if major is not None:
        new_version["major"] = major
    if minor is not None:
        new_version["minor"] = minor
    if patch is not None:
        new_version["patch"] = patch
    if build is not None:
        new_version["build"] = build
    if stage is not None:
        new_version["stage"] = stage
    
    # Update date
    new_version["date"] = datetime.now().strftime("%Y-%m-%d")
    
    # Create new version string
    version_string = f"{new_version['major']}.{new_version['minor']}.{new_version['patch']}"
    if new_version['stage'] != "release":
        version_string += f"-{new_version['stage']}"
    if new_version['build'] > 0:
        version_string += f".{new_version['build']}"
    
    # Update manifest
    manifest["version"] = new_version
    manifest["version_string"] = version_string
    manifest["build_date"] = new_version["date"]
    
    # Add to history
    manifest["history"].insert(0, {
        "version": version_string,
        "date": new_version["date"],
        "changes": []  # Empty changes list to be filled later
    })
    
    return save_manifest(manifest)

def add_change(version, change_description):
    """Add a change to a specific version in the history."""
    manifest = load_manifest()
    if not manifest:
        return False
    
    for entry in manifest["history"]:
        if entry["version"] == version:
            entry["changes"].append(change_description)
            return save_manifest(manifest)
    
    logger.error(f"Version {version} not found in history")
    return False

def update_changelog():
    """Update the CHANGELOG.md file based on the version manifest."""
    manifest = load_manifest()
    if not manifest:
        return False
    
    try:
        with open(CHANGELOG_FILE, 'w') as f:
            f.write("# netWORKS Changelog\n\n")
            
            for entry in manifest["history"]:
                f.write(f"## {entry['version']} ({entry['date']})\n\n")
                
                if not entry["changes"]:
                    f.write("* No changes recorded\n\n")
                else:
                    for change in entry["changes"]:
                        f.write(f"* {change}\n")
                    f.write("\n")
            
            return True
    except Exception as e:
        logger.error(f"Error updating changelog: {str(e)}")
        return False

def get_current_manifest():
    """Get the current version manifest."""
    return load_manifest() 