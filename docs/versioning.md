# netWORKS Versioning System

This document explains how versioning works in netWORKS and how to use the version management tools.

## Version Format

netWORKS uses Semantic Versioning (SemVer) with the following format:

```
MAJOR.MINOR.PATCH[-STAGE[.BUILD]]
```

Where:
- **MAJOR**: Incremented for incompatible API changes
- **MINOR**: Incremented for new functionality in a backward-compatible manner
- **PATCH**: Incremented for backward-compatible bug fixes
- **STAGE**: Optional release stage (alpha, beta, rc, release)
- **BUILD**: Optional build number

Examples:
- `1.0.0` - Release version
- `1.2.5` - Release version with bug fixes
- `2.0.0-alpha` - Alpha release of a major version
- `1.5.0-beta.3` - Beta release with build number

## Version Manifest

The application uses a version manifest file (`version_manifest.json`) to track version information. The manifest includes:

- Current version details
- Release notes
- Compatibility requirements
- Version history with changes

## Command-line Tools

The `version_manager.py` script provides command-line tools for managing versions:

### View Current Version

```
python version_manager.py get
```

To get detailed JSON output:

```
python version_manager.py get --json
```

### Set Version Information

```
python version_manager.py set --major 1 --minor 2 --patch 0 --stage beta
```

### Increment Version

```
python version_manager.py bump [major|minor|patch|build]
```

### Add Change to Changelog

```
python version_manager.py change "Fixed bug in network scanning"
```

To add a change to a specific version:

```
python version_manager.py change --version 1.0.0-beta "Fixed UI issues"
```

### Update Changelog File

```
python version_manager.py changelog
```

### Display the Current Manifest

```
python version_manager.py manifest
```

## Changelog

The application maintains a `CHANGELOG.md` file which is automatically updated from the version manifest. This file provides a human-readable history of changes for each version.

## For Developers

### Using Version Information in Code

Import the version module to access version information:

```python
from core.version import get_version_string, get_version

# Get version string
version = get_version_string()  # e.g., "1.0.0-alpha"

# Get version dictionary
version_dict = get_version()  # e.g., {"major": 1, "minor": 0, "patch": 0, "stage": "alpha", "build": 0}
```

### Updating Version for Releases

For a new release, follow these steps:

1. Decide what type of release it is (major, minor, patch)
2. Use the version manager to bump the version:
   ```
   python version_manager.py bump minor
   ```
3. Add changes to the changelog:
   ```
   python version_manager.py change "Added new feature X"
   python version_manager.py change "Fixed bug Y"
   ```
4. Update the changelog file:
   ```
   python version_manager.py changelog
   ```
5. Commit changes to source control

## Version Compatibility

The version manifest includes compatibility information:

- `min_plugin_api`: Minimum plugin API version required
- `min_python_version`: Minimum Python version required

This information is used to ensure compatibility between components and dependencies. 