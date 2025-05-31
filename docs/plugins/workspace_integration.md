# Plugin Workspace Integration

This document explains how plugins interact with NetWORKS workspaces and provides guidelines for proper workspace-aware plugin development.

## Overview

NetWORKS workspaces provide isolated environments for different use cases, and plugins are an integral part of this isolation. Each workspace can have its own set of enabled plugins and plugin configurations, allowing for highly customized environments.

## Workspace Plugin Lifecycle

### 1. Plugin Discovery

During application startup, the Plugin Manager discovers plugins from multiple locations:

- **Built-in plugins**: `src/plugins/` (shipped with NetWORKS)
- **External plugins**: `plugins/` (user-installed, shared across workspaces)  
- **Workspace plugins**: `config/workspaces/<workspace>/plugins/` (workspace-specific)

All plugins are discovered but none are loaded at this stage.

### 2. Workspace Loading

When a workspace is loaded or switched to:

1. **Unload Current Plugins**: All currently loaded plugins are unloaded with proper cleanup
2. **Load Workspace Configuration**: The workspace's `enabled_plugins` list is read
3. **Plugin State Restoration**: Each plugin's enabled/disabled state is restored
4. **Plugin Loading**: Only plugins enabled for this workspace are loaded and initialized

### 3. Plugin Isolation

Each workspace maintains complete plugin isolation:

- **State Separation**: Plugin enabled/disabled states are workspace-specific
- **Data Isolation**: Plugin data directories are separated by workspace
- **Settings Isolation**: Plugin settings are stored per-workspace
- **Memory Isolation**: Plugins are fully unloaded between workspace switches

## Plugin Data Storage

Plugins should store workspace-specific data in dedicated directories:

```python
class MyPlugin(PluginInterface):
    def initialize(self, app, plugin_info):
        # Get workspace-specific data directory
        workspace_name = app.device_manager.current_workspace
        self.data_dir = os.path.join(
            app.device_manager.workspaces_dir,
            workspace_name,
            "plugin_data",
            plugin_info.id
        )
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load workspace-specific configuration
        self.load_workspace_config()
        
    def load_workspace_config(self):
        """Load configuration specific to current workspace"""
        config_file = os.path.join(self.data_dir, "config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.workspace_config = json.load(f)
        else:
            self.workspace_config = self.get_default_config()
            
    def save_workspace_config(self):
        """Save configuration for current workspace"""
        config_file = os.path.join(self.data_dir, "config.json")
        with open(config_file, 'w') as f:
            json.dump(self.workspace_config, f, indent=2)
```

## Workspace-Specific Plugin Installation

Plugins can be installed specifically for a workspace:

```bash
# Install plugin for specific workspace
mkdir -p config/workspaces/production/plugins/my_plugin
cp -r my_plugin/* config/workspaces/production/plugins/my_plugin/
```

This plugin will only be available when the "production" workspace is active.

## Plugin Settings Per Workspace

The workspace configuration file stores plugin-specific settings:

```json
{
  "name": "production",
  "description": "Production environment",
  "enabled_plugins": [
    "command_manager",
    "network_scanner",
    "monitoring_plugin"
  ],
  "plugin_settings": {
    "command_manager": {
      "auto_save_commands": true,
      "command_timeout": 30,
      "allowed_command_types": ["show", "display"]
    },
    "monitoring_plugin": {
      "polling_interval": 60,
      "alert_threshold": 85,
      "notification_email": "admin@company.com"
    }
  }
}
```

## Best Practices

### 1. Proper Resource Cleanup

Always implement proper cleanup to prevent memory leaks:

```python
class MyPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self._timers = []
        self._threads = []
        self._connected_signals = set()
        
    def cleanup(self):
        """Clean up all resources"""
        # Stop timers
        for timer in self._timers:
            timer.stop()
        self._timers.clear()
        
        # Stop threads
        for thread in self._threads:
            thread.quit()
            thread.wait()
        self._threads.clear()
        
        # Disconnect signals
        for signal, slot in self._connected_signals:
            try:
                signal.disconnect(slot)
            except Exception:
                pass
        self._connected_signals.clear()
        
        return super().cleanup()
```

### 2. Workspace-Aware Configuration

Store configuration per workspace:

```python
def get_workspace_config_path(self):
    """Get path to workspace-specific config file"""
    workspace_name = self.app.device_manager.current_workspace
    workspace_dir = os.path.join(
        self.app.device_manager.workspaces_dir,
        workspace_name
    )
    return os.path.join(workspace_dir, "plugin_data", self.plugin_info.id, "config.json")
```

### 3. Signal Connection Tracking

Track all signal connections for proper cleanup:

```python
def connect_signal(self, signal, slot):
    """Connect signal and track for cleanup"""
    try:
        signal.connect(slot)
        self._connected_signals.add((signal, slot))
        logger.debug(f"Connected signal {signal} to {slot}")
    except Exception as e:
        logger.error(f"Failed to connect signal: {e}")
```

### 4. Graceful Error Handling

Handle initialization and cleanup errors gracefully:

```python
def initialize(self, app, plugin_info):
    """Initialize plugin with error handling"""
    try:
        self.app = app
        self.plugin_info = plugin_info
        
        # Initialize components
        self._init_ui_components()
        self._init_data_connections()
        self._load_workspace_config()
        
        logger.info(f"Plugin {plugin_info.id} initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize plugin {plugin_info.id}: {e}")
        self.cleanup()  # Clean up partial initialization
        return False
```

## Testing Workspace Integration

When testing plugins, verify proper workspace integration:

```python
def test_workspace_isolation(self):
    """Test that plugin data is isolated between workspaces"""
    # Load workspace A
    self.app.device_manager.load_workspace("workspace_a")
    plugin_a_data = self.plugin.get_data()
    
    # Switch to workspace B
    self.app.device_manager.load_workspace("workspace_b") 
    plugin_b_data = self.plugin.get_data()
    
    # Verify data isolation
    assert plugin_a_data != plugin_b_data
    
def test_plugin_cleanup(self):
    """Test that plugin properly cleans up resources"""
    initial_signal_connections = len(self.plugin._connected_signals)
    
    # Plugin should be loaded
    assert self.plugin._initialized
    
    # Unload plugin
    self.app.plugin_manager.unload_plugin(self.plugin.plugin_info.id)
    
    # Verify cleanup
    assert not self.plugin._initialized
    assert len(self.plugin._connected_signals) == 0
```

## Common Issues and Solutions

### Issue: Plugin State Persists Between Workspaces

**Symptom**: Plugin remembers data from previous workspace
**Solution**: Implement proper data isolation using workspace-specific directories

### Issue: Memory Leaks When Switching Workspaces

**Symptom**: Application memory usage increases with each workspace switch
**Solution**: Implement thorough cleanup() method that releases all resources

### Issue: Plugin Conflicts Between Workspaces

**Symptom**: Plugin behavior changes unexpectedly when switching workspaces
**Solution**: Use workspace-specific plugin settings and avoid global state

### Issue: Plugin Fails to Load in Specific Workspace

**Symptom**: Plugin works in one workspace but not another
**Solution**: Check workspace-specific plugin directories and configuration files 