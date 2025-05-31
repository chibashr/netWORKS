# NetWORKS Plugins Directory

This directory contains external plugins for NetWORKS.

## Plugin System Status

✅ **The NetWORKS plugin system is fully functional and properly implemented.**

For a comprehensive status report, see: [`docs/plugins/PLUGIN_SYSTEM_STATUS.md`](../docs/plugins/PLUGIN_SYSTEM_STATUS.md)

## How to Install Plugins

1. Copy plugin folders to this directory
2. Restart NetWORKS
3. Enable plugins in the Plugin Manager (Tools -> Plugin Manager)

## Plugin Development

See the comprehensive documentation in the `docs/plugins/` directory:

- **[Plugin Development Guide](../docs/plugins/README.md)** - Complete guide for developing plugins
- **[Workspace Integration](../docs/plugins/workspace_integration.md)** - How plugins work with workspaces
- **[Getting Started](../docs/plugins/GETTING_STARTED.md)** - Step-by-step tutorial

## Plugin Directory Structure

NetWORKS supports three types of plugin directories:

1. **Built-in Plugins** (`src/plugins/`): Shipped with NetWORKS
2. **External Plugins** (`plugins/`): User-installed, shared across workspaces  
3. **Workspace Plugins** (`config/workspaces/<workspace>/plugins/`): Workspace-specific

## Built-in Plugins

Built-in plugins are included with the application and don't need to be placed here.
They include:
- Command Manager
- Config Manager  
- Network Scanner
- Sample Plugin (for reference)

## Workspace Integration

**Important**: Plugins are workspace-aware in NetWORKS. Each workspace can have its own set of enabled plugins, and plugins are completely unloaded when switching workspaces to ensure proper isolation.

For more information, visit: https://github.com/networks/networks
