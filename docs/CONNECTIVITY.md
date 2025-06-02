# NetWORKS Connectivity Monitoring

NetWORKS now includes comprehensive internet connectivity monitoring to provide a better user experience when working online and offline.

## Features

### Real-time Connectivity Status
- **Status Bar Indicator**: Shows 🌐 Online or 📵 Offline in the application status bar
- **Window Title Indicator**: Displays [OFFLINE] in the window title when no internet connection is available
- **Automatic Monitoring**: Checks connectivity every 30 seconds (configurable)
- **Instant Updates**: Status updates immediately when connectivity changes

### Network Operation Protection
- **Automatic Blocking**: Network operations are automatically blocked when offline
- **Graceful Handling**: Clear error messages and logging when operations cannot complete
- **User Feedback**: Status bar messages inform users when connectivity is restored or lost

### Affected Operations
The following operations now check for connectivity before executing:
- **Update Checking**: Blocked when offline with appropriate messaging
- **Issue Reporting**: GitHub issue submission requires connectivity
- **Plugin Operations**: Any plugin network requests can use connectivity checks

## Technical Implementation

### ConnectivityManager Class
The `ConnectivityManager` class handles all connectivity monitoring:

```python
from src.core.connectivity_manager import ConnectivityManager

# Initialize connectivity manager
connectivity_manager = ConnectivityManager(config, app)

# Check current status
is_online = connectivity_manager.is_online()
status_text = connectivity_manager.get_status_text()  # "Online" or "Offline"

# Get detailed status
status = connectivity_manager.get_detailed_status()
```

### Connectivity Decorators
Use the `@require_connectivity()` decorator to automatically check connectivity:

```python
from src.core.connectivity_manager import require_connectivity

@require_connectivity()
def my_network_function():
    # This function will only execute if online
    # Returns None if offline
    pass
```

### Manual Connectivity Checks
For manual connectivity checking in functions:

```python
from src.core.connectivity_manager import check_connectivity_before_request

def my_function(self):
    if not check_connectivity_before_request(self.app.connectivity_manager):
        return False  # Cannot proceed offline
    
    # Continue with network operation
    pass
```

## Configuration

Connectivity monitoring can be configured through the application settings:

```yaml
connectivity:
  auto_check: true          # Enable automatic monitoring
  check_interval: 30        # Check interval in seconds
```

## Connectivity Testing

Multiple reliable endpoints are tested to ensure accurate connectivity detection:
- GitHub API (api.github.com)
- Google (www.google.com)  
- Cloudflare DNS (1.1.1.1)

The system considers the connection online if any of these endpoints responds successfully.

## Integration with Existing Features

### Update Checker
- Checks connectivity before attempting to fetch updates from GitHub
- Shows "No internet connection available" message when offline
- Prevents network timeouts and errors

### Issue Reporter
- Checks connectivity before submitting issues to GitHub
- Queues issues for later submission when offline
- Processes queued issues when connectivity is restored

### Main Window
- Updates window title to show offline status
- Displays connectivity status in status bar
- Shows temporary messages when connectivity changes

## User Experience

### Visual Indicators
- **Green 🌐 Online**: Internet connection available
- **Red 📵 Offline**: No internet connection detected
- **Tooltip Information**: Hover over status for additional details

### Behavioral Changes
- Network operations gracefully fail with informative messages
- Users are clearly informed when features are unavailable
- No unexpected timeouts or hanging operations

## Testing Connectivity Features

A test script is provided to demonstrate connectivity monitoring:

```bash
python test_connectivity.py
```

This opens a test window that shows:
- Real-time connectivity status
- Connectivity change notifications
- Demonstration of blocked network operations when offline

## Plugin Development

Plugin developers can integrate connectivity checking:

```python
class MyPlugin(PluginInterface):
    def __init__(self, app=None):
        super().__init__()
        self.app = app
    
    @require_connectivity()
    def my_network_operation(self):
        # This will only run when online
        pass
    
    def another_network_operation(self):
        # Manual connectivity check
        if not check_connectivity_before_request(self.app.connectivity_manager):
            logger.warning("Cannot perform operation: offline")
            return
        
        # Continue with network operation
        pass
```

## Troubleshooting

### Connectivity Detection Issues
If connectivity detection is not working properly:

1. **Check Firewall Settings**: Ensure the application can access the test URLs
2. **Proxy Configuration**: Configure proxy settings if behind a corporate firewall
3. **Test URLs**: The system tests multiple endpoints for reliability

### Performance Considerations
- Connectivity checks use a 3-second timeout
- Multiple endpoints prevent false negatives
- Monitoring interval is configurable (default: 30 seconds)

## Future Enhancements

Planned improvements for connectivity monitoring:
- Proxy server support configuration
- Custom test endpoints
- Bandwidth detection
- Network quality indicators
- Plugin-specific connectivity requirements 