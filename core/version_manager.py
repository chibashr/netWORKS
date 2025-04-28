#!/usr/bin/env python3
# netWORKS - Version Manager CLI Tool

import argparse
import sys
import json
from datetime import datetime
from core.version import (
    get_version,
    get_version_string, 
    load_manifest,
    update_version,
    add_change,
    update_changelog
)

def main():
    """Main entry point for the version manager CLI."""
    parser = argparse.ArgumentParser(description="netWORKS Version Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Get version command
    get_parser = subparsers.add_parser("get", help="Get current version information")
    get_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    # Set version command
    set_parser = subparsers.add_parser("set", help="Set version information")
    set_parser.add_argument("--major", type=int, help="Major version")
    set_parser.add_argument("--minor", type=int, help="Minor version")
    set_parser.add_argument("--patch", type=int, help="Patch version")
    set_parser.add_argument("--build", type=int, help="Build number")
    set_parser.add_argument("--stage", choices=["alpha", "beta", "rc", "release"], 
                          help="Release stage")
    
    # Increment version command
    bump_parser = subparsers.add_parser("bump", help="Increment version number")
    bump_parser.add_argument("component", choices=["major", "minor", "patch", "build"],
                           help="Version component to increment")
    
    # Add change command
    change_parser = subparsers.add_parser("change", help="Add a change to the changelog")
    change_parser.add_argument("--version", help="Version to add change to (defaults to current)")
    change_parser.add_argument("description", help="Description of the change")
    
    # Update changelog command
    changelog_parser = subparsers.add_parser("changelog", help="Update changelog file")
    
    # Display manifest command
    manifest_parser = subparsers.add_parser("manifest", help="Display current manifest")
    
    args = parser.parse_args()
    
    if args.command == "get":
        if args.json:
            print(json.dumps(get_version(), indent=2))
        else:
            version = get_version()
            print(f"netWORKS Version: {get_version_string()}")
            print(f"Build Date: {version['date']}")
            print(f"Release Stage: {version['stage']}")
    
    elif args.command == "set":
        if update_version(args.major, args.minor, args.patch, args.build, args.stage):
            print(f"Version updated to {get_version_string()}")
            update_changelog()
        else:
            print("Failed to update version")
            return 1
    
    elif args.command == "bump":
        version = get_version()
        
        if args.component == "major":
            new_major = version["major"] + 1
            if update_version(major=new_major, minor=0, patch=0, build=0):
                print(f"Bumped major version to {get_version_string()}")
                update_changelog()
            else:
                print("Failed to bump version")
                return 1
        
        elif args.component == "minor":
            new_minor = version["minor"] + 1
            if update_version(minor=new_minor, patch=0, build=0):
                print(f"Bumped minor version to {get_version_string()}")
                update_changelog()
            else:
                print("Failed to bump version")
                return 1
        
        elif args.component == "patch":
            new_patch = version["patch"] + 1
            if update_version(patch=new_patch, build=0):
                print(f"Bumped patch version to {get_version_string()}")
                update_changelog()
            else:
                print("Failed to bump version")
                return 1
        
        elif args.component == "build":
            new_build = version["build"] + 1
            if update_version(build=new_build):
                print(f"Bumped build number to {get_version_string()}")
                update_changelog()
            else:
                print("Failed to bump version")
                return 1
    
    elif args.command == "change":
        version = args.version or get_version_string()
        if add_change(version, args.description):
            print(f"Added change to version {version}")
            update_changelog()
        else:
            print(f"Failed to add change to version {version}")
            return 1
    
    elif args.command == "changelog":
        if update_changelog():
            print("Changelog updated successfully")
        else:
            print("Failed to update changelog")
            return 1
    
    elif args.command == "manifest":
        manifest = load_manifest()
        if manifest:
            print(json.dumps(manifest, indent=2))
        else:
            print("Failed to load manifest")
            return 1
    
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 