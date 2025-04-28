# netWORKS Plugin UI Framework

This document provides guidance on the UI framework used in netWORKS plugins, including which Qt framework to use and best practices for UI development.

## Qt Framework Migration

netWORKS is transitioning from PyQt5 to PySide6 as its primary UI framework. Here's what plugin developers need to know:

### Current Status

- **Core application**: Now uses PySide6
- **Legacy plugins**: PyQt5 remains in requirements.txt for backward compatibility
- **New plugins**: Should use PySide6 exclusively

### Imports to Use

For new plugin development, always use PySide6 imports:

```python
# Use these imports for all new code
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon, QAction
```

### File and Class Naming

> **IMPORTANT**: Python file names and class names must match exactly in capitalization when using relative imports. 
> 
> For example, if you have a file named `left_panel.py` with a class named `ScanControlPanel`, your import should use:
> ```python
> from .left_panel import ScanControlPanel  # Correct
> ```
> 
> Avoid mismatched capitalization such as:
> ```python
> from .left_panel import LeftPanel  # WRONG if class is named ScanControlPanel
> ```
> 
> This can cause import errors on case-sensitive platforms like Linux.

### Panel Naming Conventions

Maintain consistent panel class names across your plugin. For larger plugins with multiple UI components, the recommended naming convention is:

| File Name        | Class Name       | Purpose                            |
|------------------|------------------|------------------------------------|
| `left_panel.py`  | `LeftPanel`      | Main navigation or control panel   |
| `right_panel.py` | `RightPanel`     | Details or settings panel          |
| `bottom_panel.py`| `BottomPanel`    | Status or results panel            |
| `main_panel.py`  | `MainPanel`      | Container for all other panels     |

If your panels have more specific purposes, use descriptive names:

```python
# In left_panel.py
class ScanControlPanel(QWidget):
    """Panel for scan controls."""
    pass

# In right_panel.py
class ScanSettingsPanel(QWidget):
    """Panel for scan settings."""
    pass

# In bottom_panel.py
class ScanHistoryPanel(QWidget):
    """Panel for scan history."""
    pass

# In main_panel.py - update imports to match class names
from .left_panel import ScanControlPanel
from .right_panel import ScanSettingsPanel 
from .bottom_panel import ScanHistoryPanel

class NetworkScannerMainPanel(QWidget):
    """Main container panel."""
    
    def __init__(self, plugin):
        # ...
        self.left_panel = ScanControlPanel(plugin)
        self.right_panel = ScanSettingsPanel(plugin)
        self.bottom_panel = ScanHistoryPanel(plugin)
        # ...
```

### Signal/Slot Connections

PySide6 signals and slots work slightly differently than PyQt5:

```python
# PySide6 style signal/slot connection
button.clicked.connect(self.on_button_clicked)

# Use Signal and Slot decorators
from PySide6.QtCore import Signal, Slot

class MyClass(QObject):
    my_signal = Signal(str)  # Signal with string parameter
    
    @Slot(str)  # Slot that accepts a string
    def my_slot(self, value):
        print(f"Received: {value}")
```

## Thread Safety

Qt UI components must run in the main thread. Follow these rules:

1. Create UI components in the main thread
2. Never modify UI from background threads directly
3. Use signals/slots for thread-safe communication

```python
# Example of proper thread handling
from PySide6.QtCore import QObject, Signal, Slot, QThread

class Worker(QObject):
    result_ready = Signal(dict)  # Signal to send results back to UI
    
    def process(self):
        # Do work...
        result = {"status": "complete", "data": [1, 2, 3]}
        self.result_ready.emit(result)  # Emit signal with results

class MyPlugin:
    def setup_worker(self):
        self.worker_thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.worker_thread)
        
        # Connect worker signals to UI slots
        self.worker.result_ready.connect(self.update_ui)
        
        # Start thread when needed
        self.worker_thread.start()
        
    @Slot(dict)
    def update_ui(self, result):
        # This runs in the main thread and is safe to update UI
        self.result_label.setText(f"Results: {result['data']}")
```

## Plugin UI Components

### Recommended Panel Structure

For consistency, follow this structure for UI panels:

```python
class YourPluginPanel(QWidget):
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.logger = logging.getLogger(__name__)
        
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Add widgets
        title = QLabel("Your Plugin")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Add more widgets as needed
    
    def connect_signals(self):
        # Connect signals and slots
        pass
```

### Style Guidelines

- Use layouts for proper widget positioning
- Follow the netWORKS color scheme for visual consistency
- Keep UI responsive by moving long operations to background threads
- Use Qt stylesheets sparingly and consistently

## UI Registration

Register your UI components using the plugin API when the main window is ready:

```python
def __init__(self, plugin_api):
    self.api = plugin_api
    # Wait for main window to be ready
    self.api.on_main_window_ready(self.init_ui)

def init_ui(self):
    """Initialize UI when main window is ready."""
    # Create panels
    self.left_panel = YourLeftPanel(self)
    self.right_panel = YourRightPanel(self)
    
    # Register with main window
    self.api.register_panel(self.left_panel, "left", "Your Panel")
    self.api.register_panel(self.right_panel, "right", "Settings")
```

## Example Implementation

Here's a complete example of a plugin UI component:

```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QFormLayout, QLineEdit
)
from PySide6.QtCore import Qt, Signal, Slot

class SamplePanel(QWidget):
    """Sample panel for demonstration."""
    
    # Define signals
    action_requested = Signal(str)
    
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.logger = logging.getLogger(__name__)
        
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Sample Panel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Form layout for inputs
        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)
        layout.addLayout(form_layout)
        
        # Button
        self.action_button = QPushButton("Perform Action")
        layout.addWidget(self.action_button)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Add stretch to push everything up
        layout.addStretch(1)
    
    def connect_signals(self):
        """Connect signals and slots."""
        self.action_button.clicked.connect(self.on_action_clicked)
    
    @Slot()
    def on_action_clicked(self):
        """Handle action button click."""
        name = self.name_input.text().strip()
        if name:
            self.status_label.setText(f"Processing: {name}")
            self.action_requested.emit(name)
        else:
            self.status_label.setText("Error: Name is required")
    
    @Slot(str)
    def update_status(self, status):
        """Update the status label."""
        self.status_label.setText(status)
```

## Common Interface Methods

All panel classes used in a plugin that interacts with NetworkScannerMainPanel should implement these common interface methods:

```python
def show_device(self, device):
    """Show device details for the given device.
    
    Args:
        device: Device information dictionary
    """
    pass

def refresh(self):
    """Refresh panel data."""
    pass

def on_scan_started(self, scan_data):
    """Handle scan started event.
    
    Args:
        scan_data: Scan information dictionary
    """
    pass

def on_scan_finished(self, scan_data):
    """Handle scan finished event.
    
    Args:
        scan_data: Scan information dictionary
    """
    pass

def on_scan_progress(self, progress_data):
    """Handle scan progress event.
    
    Args:
        progress_data: Progress information dictionary
    """
    pass
```

These methods ensure compatibility with the main panel, which will call these methods on various events.

## Common Mistakes to Avoid

1. **Importing UI components outside the main thread**: Always import and create UI components in the main thread or in methods called from the main thread.

2. **Using PyQt5 and PySide6 together**: This can cause conflicts. Stick with PySide6 for all new code.

3. **Direct UI updates from background threads**: Always use signals and slots for thread-safe UI updates.

4. **Heavy processing in the UI thread**: Move any significant processing to background threads to keep the UI responsive.

5. **Hardcoded sizes and positions**: Use layouts instead of hardcoded geometries for better adaptability.

6. **File/class name mismatches**: Make sure file names and class names are correctly matched in imports to avoid cross-platform issues.

7. **Missing interface methods**: Ensure all panel classes implement the common interface methods expected by the main container.

8. **Circular imports**: Be careful of import cycles between UI files. Use the following pattern in your `__init__.py`:

```python
# plugins/your_plugin/ui/__init__.py

import logging

logger = logging.getLogger("plugin.your_plugin.ui")
logger.debug("Loading UI components")

# Import individual panel components first
from . import left_panel
from . import right_panel
from . import bottom_panel

# Import main panel last since it imports from the other modules
from . import main_panel

# Export all components for easier imports from parent module
__all__ = ['main_panel', 'left_panel', 'right_panel', 'bottom_panel']
```

This approach ensures panels are loaded in the correct order, preventing circular import issues.

## Resources

- [PySide6 Documentation](https://doc.qt.io/qtforpython-6/)
- [Qt Style Sheets Reference](https://doc.qt.io/qt-6/stylesheet-reference.html)
- [Qt Threading Basics](https://doc.qt.io/qt-6/thread-basics.html)

# Toolbar Integration

netWORKS uses a ribbon-style toolbar interface similar to Microsoft Office applications. All main functions are organized in this ribbon toolbar rather than traditional dropdown menus. Plugins can interact with and extend this interface to provide a consistent user experience.

## Adding to the Ribbon Toolbar

Plugins can add their own functionality to the toolbar in several ways:

### Adding to Existing Tabs

To add a button to an existing tab:

```python
# Create an action
action = QAction("My Function", self.main_window)
action.setIcon(QIcon("path/to/icon.png"))
action.triggered.connect(self.my_function)

# Create a tool button
button = QToolButton()
button.setDefaultAction(action)
button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

# Add to existing tab and group
self.main_window.add_toolbar_widget(button, "Plugins", "My Plugin")
```

### Creating a New Group

If you need to organize multiple related functions, create a new group:

```python
# Create a group in the Plugins tab
group = self.main_window.create_toolbar_group("My Functions", self.main_window.plugins_tab)

# Add several buttons to the group
for function_name, callback in self.functions.items():
    action = QAction(function_name, self.main_window)
    action.triggered.connect(callback)
    
    button = QToolButton()
    button.setDefaultAction(action)
    button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    
    group.layout().addWidget(button)
```

### Using Plugin-Specific Tabs

For plugins with many functions, you can request a dedicated tab:

```python
# First check if a custom tab exists for your plugin
tab_name = "My Plugin"
custom_tab = None

for i in range(self.main_window.toolbar_tabs.count()):
    if self.main_window.toolbar_tabs.tabText(i) == tab_name:
        custom_tab = self.main_window.toolbar_tabs.widget(i)
        break

# If not found, create a new tab widget and add it
if not custom_tab:
    custom_tab = QWidget()
    custom_tab.setLayout(QHBoxLayout())
    custom_tab.layout().setSpacing(2)
    custom_tab.layout().setContentsMargins(5, 5, 5, 5)
    self.main_window.toolbar_tabs.addTab(custom_tab, tab_name)

# Now add groups to this tab
group = self.main_window.create_toolbar_group("Main Functions", custom_tab)
# Add buttons to the group...
```

## Best Practices for Ribbon Interface

1. **Follow Microsoft Office conventions** - users are familiar with this pattern
2. **Use clear icons** - ensure your functions are easily recognizable 
3. **Group related functions** - keep related functionality together
4. **Use text under icons** - this helps with discoverability
5. **Consider frequency of use** - place common functions in readily accessible locations
6. **Use appropriate tabs** - add to existing tabs when possible, create new ones only when necessary
7. **Maintain consistent styling** - match the application's existing visual language
``` 