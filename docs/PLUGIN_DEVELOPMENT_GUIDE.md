# Plugin Development Quick Start Guide

## 🚀 Creating Your First Plugin

This guide will walk you through creating a plugin with the hardened requirements system.

## 📁 1. Plugin Structure

Create your plugin directory:
```
plugins/my_awesome_plugin/
├── manifest.json           # ⚡ Required: Plugin metadata & requirements
├── my_awesome_plugin.py    # ⚡ Required: Main plugin file  
├── core/                   # 📂 Optional: Core functionality
├── ui/                     # 📂 Optional: User interface components
├── utils/                  # 📂 Optional: Utility functions
├── data/                   # 📂 Optional: Plugin data files
├── docs/                   # 📂 Optional: Documentation
└── lib/                    # 🔧 Auto-generated: Dependencies (DO NOT EDIT)
```

## 📋 2. Create manifest.json

```json
{
    "id": "my_awesome_plugin",
    "name": "My Awesome Plugin",
    "version": "1.0.0",
    "description": "Does awesome things for network management",
    "author": "Your Name",
    "entry_point": "my_awesome_plugin.py",
    "requirements": {
        "python": [
            "requests>=2.25.1",
            "beautifulsoup4>=4.9.0"
        ],
        "system": [
            "Python 3.8+",
            "Internet Connection"
        ]
    },
    "permissions": {
        "network": true,
        "file_system": false,
        "device_access": true
    }
}
```

## 🐍 3. Create Plugin Class

```python
# my_awesome_plugin.py
import sys
import os

# Add plugin lib to path FIRST (before any other imports that use requirements)
plugin_dir = os.path.dirname(__file__)
lib_dir = os.path.join(plugin_dir, 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

# Now import your requirements
import requests
from bs4 import BeautifulSoup

from src.core.plugin_interface import PluginInterface
from loguru import logger

class MyAwesomePlugin(PluginInterface):
    """My awesome plugin for network management"""
    
    def __init__(self):
        super().__init__()
        self.name = "My Awesome Plugin"
        self.version = "1.0.0"
        
    def initialize(self, app, plugin_info):
        """Initialize the plugin"""
        logger.info(f"Initializing {self.name} v{self.version}")
        self.app = app
        self.plugin_info = plugin_info
        
        # Your initialization code here
        self._setup_ui()
        self._register_commands()
        
        logger.info(f"{self.name} initialized successfully")
        
    def _setup_ui(self):
        """Setup plugin UI components"""
        # Add menu items, toolbars, etc.
        pass
        
    def _register_commands(self):
        """Register plugin commands"""
        # Register any commands your plugin provides
        pass
        
    def scan_network(self, target_url):
        """Example method that uses requirements"""
        try:
            # Use requests from requirements
            response = requests.get(target_url, timeout=10)
            
            # Use beautifulsoup from requirements
            soup = BeautifulSoup(response.content, 'html.parser')
            
            return soup.title.string if soup.title else "No title"
            
        except Exception as e:
            logger.error(f"Error scanning {target_url}: {e}")
            return None
            
    def cleanup(self):
        """Cleanup when plugin is disabled/unloaded"""
        logger.info(f"Cleaning up {self.name}")
        # Your cleanup code here
```

## 🔧 4. Test Your Plugin

Create a test file:
```python
# test_my_plugin.py
import unittest
import sys
import os

# Add plugin to path
plugin_dir = os.path.join(os.path.dirname(__file__), 'plugins', 'my_awesome_plugin')
sys.path.insert(0, plugin_dir)

from my_awesome_plugin import MyAwesomePlugin

class TestMyAwesomePlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = MyAwesomePlugin()
        
    def test_plugin_creation(self):
        """Test plugin can be created"""
        self.assertIsNotNone(self.plugin)
        self.assertEqual(self.plugin.name, "My Awesome Plugin")
        
    def test_requirements_import(self):
        """Test that requirements can be imported"""
        try:
            import requests
            import beautifulsoup4
        except ImportError as e:
            self.fail(f"Failed to import requirements: {e}")

if __name__ == '__main__':
    unittest.main()
```

## 🎯 5. Best Practices

### ✅ DO's

```python
# ✅ Specify minimum versions for stability
"requests>=2.25.1"

# ✅ Add lib directory to path FIRST
plugin_dir = os.path.dirname(__file__)
lib_dir = os.path.join(plugin_dir, 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

# ✅ Use try/except for requirement imports
try:
    import requests
except ImportError:
    logger.error("requests not available")
    
# ✅ Log important actions
logger.info("Plugin action completed")

# ✅ Handle cleanup properly  
def cleanup(self):
    # Clean up resources
    pass
```

### ❌ DON'Ts

```python
# ❌ Don't use exact versions (breaks updates)
"requests==2.25.1"

# ❌ Don't modify lib/ directory manually
# This is auto-managed by the system

# ❌ Don't import requirements before adding lib to path
import requests  # This will fail!
sys.path.insert(0, lib_dir)

# ❌ Don't ignore errors
requests.get(url)  # Could fail silently

# ❌ Don't include unnecessary dependencies
"python": ["requests", "urllib3", "certifi"]  # urllib3, certifi come with requests
```

## 🔒 6. Security Guidelines

### Safe Package Names
```json
// ✅ Safe: Well-known packages
"requests", "beautifulsoup4", "lxml", "pillow"

// ⚠️ Be careful: Less common packages  
"new-package-2024", "obscure-lib"

// ❌ Avoid: Suspicious patterns
"requests-backdoor", "numpy123456"
```

### Version Ranges
```json
// ✅ Good: Flexible compatibility
"requests>=2.25.1,<3.0"

// ✅ Good: Minimum version
"beautifulsoup4>=4.9.0"

// ❌ Avoid: Too restrictive
"requests==2.25.1"
```

## 🧪 7. Testing Your Plugin

### Manual Testing
```bash
# 1. Copy plugin to plugins directory
cp -r my_awesome_plugin/ plugins/

# 2. Start NetWORKS
python networks.py

# 3. Open Plugin Manager (Tools → Plugin Manager)

# 4. Enable your plugin and check logs
```

### Automated Testing
```bash
# Run unit tests
python -m unittest test_my_plugin.py

# Test requirements installation
python -c "
import sys
sys.path.insert(0, 'plugins/my_awesome_plugin/lib')
import requests
print('Requirements working!')
"
```

## 📦 8. Requirements System Details

### How It Works
1. **Enable Plugin** → System validates requirements
2. **Install Dependencies** → Downloads to `plugin/lib/` 
3. **Add to Path** → Your plugin can import them
4. **Isolation** → Each plugin has its own dependencies

### Progress Tracking
```python
# Connect to progress signals in your UI
def on_requirements_progress(plugin_id, progress, message):
    print(f"{plugin_id}: {progress}% - {message}")

plugin_manager.requirements_progress.connect(on_requirements_progress)
```

### Error Handling
The system automatically:
- ✅ Validates package names for security
- ✅ Checks for version conflicts
- ✅ Creates backups before installation
- ✅ Rolls back on failure
- ✅ Provides detailed error messages

## 🚀 9. Ready to Ship

### Checklist
- [ ] ✅ `manifest.json` with all required fields
- [ ] ✅ Main plugin file with proper class
- [ ] ✅ Requirements properly specified
- [ ] ✅ Lib directory added to path
- [ ] ✅ Error handling implemented
- [ ] ✅ Cleanup method defined
- [ ] ✅ Unit tests created
- [ ] ✅ Manual testing completed

### Distribution
```bash
# Create plugin package
zip -r my_awesome_plugin.zip my_awesome_plugin/

# Exclude lib directory (will be auto-generated)
zip -r my_awesome_plugin.zip my_awesome_plugin/ -x "my_awesome_plugin/lib/*"
```

## 📞 Need Help?

- 📚 **Full Documentation**: `docs/PLUGIN_REQUIREMENTS_SYSTEM.md`
- 🔧 **Troubleshooting**: Check the troubleshooting section
- 🎯 **Examples**: Look at existing plugins in `plugins/` directory
- 🐛 **Issues**: Enable debug logging for detailed error info

---

**Happy Plugin Development!** 🎉 