#!/usr/bin/env python3
# netWORKS - Version Management

import os
import json
import logging
import requests
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

def check_for_updates(show_always=False):
    """Check for updates by comparing local version with GitHub repository.
    
    Args:
        show_always (bool): If True, show notification even if up to date
        
    Returns:
        dict: Update status information:
            {
                'status': 'up_to_date' or 'update_available' or 'error',
                'current_version': current version string,
                'latest_version': latest version string,
                'download_url': GitHub repository URL,
                'release_notes': release notes for the latest version,
                'plugin_compatibility': information about plugin compatibility,
                'breaking_changes': list of breaking changes if any,
                'new_features': list of major new features,
                'error': error message if status is 'error'
            }
    """
    try:
        logger.info("Checking for updates...")
        result = {
            'status': 'up_to_date',
            'current_version': get_version_string(),
            'latest_version': get_version_string(),
            'download_url': 'https://github.com/chibashr/netWORKS',
            'release_notes': '',
            'plugin_compatibility': {},
            'breaking_changes': [],
            'new_features': [],
            'error': ''
        }
        
        # Load local manifest
        local_manifest = load_manifest()
        if not local_manifest:
            result['status'] = 'error'
            result['error'] = 'Failed to load local version manifest'
            logger.error(result['error'])
            return result
        
        # Get the latest version info from GitHub
        try:
            # Try to get the version_manifest.json from GitHub repository
            github_url = 'https://raw.githubusercontent.com/chibashr/netWORKS/main/docs/version_manifest.json'
            response = requests.get(github_url, timeout=5)
            
            if response.status_code == 200:
                remote_manifest = response.json()
                result['latest_version'] = remote_manifest.get('version_string', 'Unknown')
                
                # Compare versions
                current_parts = parse_version_string(result['current_version'])
                latest_parts = parse_version_string(result['latest_version'])
                
                if compare_versions(current_parts, latest_parts) < 0:
                    result['status'] = 'update_available'
                    
                    # Get release notes from all versions newer than current
                    history = remote_manifest.get('history', [])
                    if history:
                        # Extract all changes from newer versions
                        all_changes = []
                        breaking_changes = []
                        new_features = []
                        
                        for entry in history:
                            entry_version = parse_version_string(entry.get('version', '0.0.0'))
                            # Only include changes from versions newer than current
                            if compare_versions(current_parts, entry_version) < 0:
                                release_changes = entry.get('changes', [])
                                all_changes.extend(release_changes)
                                
                                # Check for breaking changes (look for keywords in changes)
                                for change in release_changes:
                                    lower_change = change.lower()
                                    if any(kw in lower_change for kw in ['breaking', 'incompatible', 'migration required']):
                                        breaking_changes.append(change)
                                    if any(kw in lower_change for kw in ['new feature', 'added', 'introduces']):
                                        new_features.append(change)
                                
                        result['release_notes'] = '\n'.join([f"- {change}" for change in all_changes])
                        result['breaking_changes'] = breaking_changes
                        result['new_features'] = new_features
                        
                    # Check plugin compatibility
                    plugin_compatibility = remote_manifest.get('plugin_compatibility', {})
                    if plugin_compatibility:
                        result['plugin_compatibility'] = plugin_compatibility
                    
                    # If no explicit plugin compatibility info, derive from version changes
                    if not result['plugin_compatibility'] and result['breaking_changes']:
                        # If there are breaking changes, assume plugin API might be affected
                        result['plugin_compatibility'] = {
                            'warning': "This update contains breaking changes that might affect plugin compatibility.",
                            'affected_plugins': [],
                            'min_plugin_api': remote_manifest.get('compatibility', {}).get('min_plugin_api', '1.0.0')
                        }
                    
                    logger.info(f"Update available: {result['current_version']} -> {result['latest_version']}")
                else:
                    logger.info(f"Software is up to date: {result['current_version']}")
            else:
                logger.warning(f"Failed to check for updates. Status code: {response.status_code}")
                result['status'] = 'error'
                result['error'] = f"Failed to check for updates. Status code: {response.status_code}"
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
            result['status'] = 'error'
            result['error'] = f"Error checking for updates: {str(e)}"
        
        return result
    except Exception as e:
        logger.error(f"Unexpected error checking for updates: {str(e)}")
        return {
            'status': 'error',
            'current_version': get_version_string(),
            'latest_version': 'Unknown',
            'download_url': 'https://github.com/chibashr/netWORKS',
            'release_notes': '',
            'plugin_compatibility': {},
            'breaking_changes': [],
            'new_features': [],
            'error': f"Unexpected error checking for updates: {str(e)}"
        }

def parse_version_string(version_string):
    """Parse a version string into a dictionary of parts.
    
    Args:
        version_string (str): Version string like "1.0.0-alpha.1"
        
    Returns:
        dict: Version parts (major, minor, patch, stage, build)
    """
    parts = {
        'major': 0,
        'minor': 0,
        'patch': 0,
        'stage': 'release',
        'stage_order': 4,  # alpha=1, beta=2, rc=3, release=4
        'build': 0
    }
    
    try:
        # Split by hyphen to separate version from stage
        version_parts = version_string.split('-')
        
        # Parse main version numbers
        if len(version_parts) > 0:
            main_version = version_parts[0].split('.')
            if len(main_version) > 0:
                parts['major'] = int(main_version[0])
            if len(main_version) > 1:
                parts['minor'] = int(main_version[1])
            if len(main_version) > 2:
                parts['patch'] = int(main_version[2])
        
        # Parse stage and build
        if len(version_parts) > 1:
            stage_parts = version_parts[1].split('.')
            if len(stage_parts) > 0:
                parts['stage'] = stage_parts[0]
                # Convert stage to numeric value for comparison
                stage_order = {'alpha': 1, 'beta': 2, 'rc': 3, 'release': 4}
                parts['stage_order'] = stage_order.get(parts['stage'], 0)
            if len(stage_parts) > 1:
                parts['build'] = int(stage_parts[1])
        
        return parts
    except Exception as e:
        logger.error(f"Error parsing version string '{version_string}': {str(e)}")
        return parts

def compare_versions(version1, version2):
    """Compare two version dictionaries.
    
    Args:
        version1 (dict): First version to compare
        version2 (dict): Second version to compare
        
    Returns:
        int: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
    """
    # Compare major, minor, patch
    for key in ['major', 'minor', 'patch']:
        if version1[key] < version2[key]:
            return -1
        elif version1[key] > version2[key]:
            return 1
    
    # Compare stage (alpha < beta < rc < release)
    if version1['stage_order'] < version2['stage_order']:
        return -1
    elif version1['stage_order'] > version2['stage_order']:
        return 1
    
    # Compare build number
    if version1['build'] < version2['build']:
        return -1
    elif version1['build'] > version2['build']:
        return 1
    
    # Versions are identical
    return 0

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