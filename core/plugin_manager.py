import logging
import os

class PluginManager:
    """Manages plugin loading and interaction."""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing PluginManager")
        
        self.plugins = {}
        self.plugin_apis = {}
        self.menu_callbacks = []
        self.menu_items = []
        self.multi_device_menu_items = []  # New list for multi-device menu items
        
        # Load plugin configuration
        self.config_path = os.path.join("config", "plugins.json")
        self.load_config()
    
    def register_menu_item(self, plugin_id, label, callback, parent_menu=None, icon_path=None, shortcut=None, enabled_callback=None):
        """Register a menu item from a plugin.
        
        Args:
            plugin_id (str): ID of the plugin
            label (str): Label for the menu item
            callback (callable): Function to call when menu item is clicked
            parent_menu (str, optional): Parent menu for this item
            icon_path (str, optional): Path to icon for the menu item
            shortcut (str, optional): Keyboard shortcut for the menu item
            enabled_callback (callable, optional): Function to determine if menu item is enabled
            
        Returns:
            bool: True if registration was successful
        """
        try:
            self.menu_items.append({
                'plugin_id': plugin_id,
                'label': label,
                'callback': callback,
                'parent_menu': parent_menu,
                'icon_path': icon_path,
                'shortcut': shortcut,
                'enabled_callback': enabled_callback if enabled_callback else lambda x: True
            })
            
            # Refresh menus
            self.refresh_menus()
            
            return True
        except Exception as e:
            self.logger.error(f"Error registering menu item: {str(e)}")
            return False
    
    def register_multi_device_menu_item(self, plugin_id, label, callback, parent_menu=None, icon_path=None, shortcut=None):
        """Register a menu item for operating on multiple selected devices.
        
        Args:
            plugin_id (str): ID of the plugin
            label (str): Label for the menu item
            callback (callable): Function to call when menu item is clicked (receives list of devices)
            parent_menu (str, optional): Parent menu for this item
            icon_path (str, optional): Path to icon for the menu item
            shortcut (str, optional): Keyboard shortcut for the menu item
            
        Returns:
            bool: True if registration was successful
        """
        try:
            self.multi_device_menu_items.append({
                'plugin_id': plugin_id,
                'label': label,
                'callback': callback,
                'parent_menu': parent_menu,
                'icon_path': icon_path,
                'shortcut': shortcut
            })
            
            # Refresh menus
            self.refresh_menus()
            
            return True
        except Exception as e:
            self.logger.error(f"Error registering multi-device menu item: {str(e)}")
            return False
    
    def get_plugin_menu_items(self, device=None):
        """Get all menu items that should be shown for a device.
        
        Args:
            device (dict, optional): Device to get menu items for
            
        Returns:
            list: List of menu item dictionaries
        """
        # Return empty list if plugins aren't loaded
        if not self.plugins:
            return []
            
        # Filter only enabled plugins
        enabled_plugins = [p_id for p_id, p in self.plugins.items() if p.get('enabled', False)]
        
        # Return menu items for enabled plugins
        return [item for item in self.menu_items if item['plugin_id'] in enabled_plugins]
    
    def get_multi_device_menu_items(self, devices=None):
        """Get all menu items that should be shown for multiple selected devices.
        
        Args:
            devices (list, optional): List of devices to get menu items for
            
        Returns:
            list: List of menu item dictionaries
        """
        # Return empty list if plugins aren't loaded
        if not self.plugins:
            return []
            
        # Filter only enabled plugins
        enabled_plugins = [p_id for p_id, p in self.plugins.items() if p.get('enabled', False)]
        
        # Return multi-device menu items for enabled plugins
        return [item for item in self.multi_device_menu_items if item['plugin_id'] in enabled_plugins]
    
    # ... rest of the code ... 