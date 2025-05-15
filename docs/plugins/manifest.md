# Plugin Manifest

Each NetWORKS plugin must include a manifest file that describes the plugin and its requirements. The manifest can be provided as either a `manifest.json` or a `plugin.json` file in the root directory of the plugin.

## Required Fields

The following fields are required in every plugin manifest:

- `id`: A unique identifier for the plugin (lowercase letters, numbers, underscores, and hyphens only)
- `name`: The display name of the plugin
- `version`: The plugin version in semantic versioning format (X.Y.Z)
- `entry_point`: The main Python file that contains the plugin class

## Optional Fields

The following fields are optional but recommended:

- `description`: A description of the plugin's functionality
- `author`: The plugin author or organization
- `min_app_version`: The minimum NetWORKS version required
- `max_app_version`: The maximum NetWORKS version supported
- `dependencies`: A list of plugin dependencies
- `requirements`: Python package and system dependencies needed by the plugin
- `changelog`: A list of changes for each version

## Example Manifest

```json
{
  "id": "sample",
  "name": "Sample Plugin",
  "version": "1.0.0",
  "description": "A sample plugin to demonstrate the plugin system",
  "author": "NetWORKS Team",
  "entry_point": "sample_plugin.py",
  "min_app_version": "0.2.0",
  "dependencies": [
    {
      "id": "core",
      "version": ">=1.0.0"
    }
  ],
  "requirements": {
    "python": [
      "requests>=2.28.0",
      "beautifulsoup4>=4.11.0"
    ],
    "system": [
      "nmap (for network scanning functionality)"
    ]
  },
  "changelog": [
    {
      "version": "1.0.0",
      "date": "2023-11-14",
      "changes": [
        "Initial release"
      ]
    }
  ]
}
```

## Validation

NetWORKS validates plugin manifests against a JSON schema to ensure they contain all required fields and follow the correct format. The schema is available at `docs/plugins/manifest_schema.json`.

## Legacy Support

For backward compatibility, NetWORKS also supports the older `plugin.yaml` format. However, it is recommended to use the JSON format for new plugins.

## Plugin Dependencies

The `dependencies` field specifies other plugins that must be enabled for this plugin to function. Each dependency includes:

- `id`: The plugin ID of the dependency
- `version`: The required version range (using npm-style version specifiers)

## Package Requirements

The `requirements` field specifies external dependencies needed by the plugin:

- `python`: A list of Python packages (in pip format) that will be automatically installed
- `system`: A list of system/OS dependencies that may need to be manually installed

NetWORKS will automatically install Python package requirements when the plugin is enabled and remove them when the plugin is uninstalled, ensuring clean system management.

## Changelog

The changelog is an array of version entries, each containing:

- `version`: The version string
- `date`: The release date in YYYY-MM-DD format
- `changes`: An array of strings describing the changes in this version

Maintaining a changelog helps users understand what has changed between versions and makes it easier to troubleshoot issues. 