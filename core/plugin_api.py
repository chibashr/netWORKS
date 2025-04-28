import logging
import datetime

class PluginAPI:
    """API for plugins to interact with the main application."""
    
    def __init__(self, plugin_id, plugin_manager):
        self.plugin_id = plugin_id
        self.plugin_manager = plugin_manager
        self.main_window = None
        self.logger = logging.getLogger(f"PluginAPI.{plugin_id}")
    
    def set_main_window(self, main_window):
        """Set the main window reference."""
        self.main_window = main_window
    
    # UI Integration
    
    def register_panel(self, panel, location, name=None):
        """Register a panel in the specified location."""
        if not self.main_window:
            self.logger.warning("Cannot register panel: main window not available")
            return False
            
        # Set plugin ID property to help with cleanup
        panel.setProperty("plugin_id", self.plugin_id)
        
        return self.main_window.register_panel(panel, location, name)
    
    def remove_panel(self, panel):
        """Remove a panel from the UI."""
        if not self.main_window:
            self.logger.warning("Cannot remove panel: main window not available")
            return False
            
        return self.main_window.remove_panel(panel)
    
    def register_menu_item(self, label, callback, parent_menu=None, icon_path=None, shortcut=None, enabled_callback=None):
        """Register a menu item.
        
        Args:
            label (str): Label for the menu item
            callback (callable): Function to call when menu item is clicked
            parent_menu (str, optional): Parent menu for this item
            icon_path (str, optional): Path to icon for the menu item
            shortcut (str, optional): Keyboard shortcut for the menu item
            enabled_callback (callable, optional): Function to determine if menu item is enabled
            
        Returns:
            bool: True if registration was successful
        """
        return self.plugin_manager.register_menu_item(
            self.plugin_id, label, callback, parent_menu, icon_path, shortcut, enabled_callback
        )
    
    def register_multi_device_menu_item(self, label, callback, parent_menu=None, icon_path=None, shortcut=None):
        """Register a menu item for operating on multiple selected devices.
        
        Args:
            label (str): Label for the menu item
            callback (callable): Function to call when menu item is clicked (receives list of devices)
            parent_menu (str, optional): Parent menu for this item
            icon_path (str, optional): Path to icon for the menu item
            shortcut (str, optional): Keyboard shortcut for the menu item
            
        Returns:
            bool: True if registration was successful
        """
        return self.plugin_manager.register_multi_device_menu_item(
            self.plugin_id, label, callback, parent_menu, icon_path, shortcut
        )
    
    def add_toolbar_widget(self, widget, category="Tools"):
        """Add a widget to the toolbar in the specified category."""
        if not self.main_window:
            self.logger.warning("Cannot add toolbar widget: main window not available")
            return False
            
        # Set plugin ID property to help with cleanup
        widget.setProperty("plugin_id", self.plugin_id)
        
        self.main_window.add_toolbar_widget(widget, category)
        return True
    
    def log(self, message, level="INFO"):
        """Log a message to the application log panel."""
        if not self.main_window:
            # Fall back to Python logging
            getattr(self.logger, level.lower(), self.logger.info)(message)
            return
            
        if hasattr(self.main_window, 'bottom_panel'):
            self.main_window.bottom_panel.add_log_entry(
                message, source=self.plugin_id, level=level
            )
    
    # Device Access
    
    def get_selected_devices(self):
        """Get the currently selected device(s).
        
        Returns:
            A device dictionary if one device is selected
            A list of device dictionaries if multiple devices are selected
            None or empty list if no devices are selected
        """
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return None
            
        return self.main_window.device_table.get_selected_devices()
    
    def get_all_devices(self):
        """Get all devices from the device table."""
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return []
            
        return self.main_window.device_table.get_all_devices()
    
    def add_device(self, device_data):
        """Add a device to the workspace."""
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return False
            
        # Ensure device has required fields
        if not device_data or not device_data.get('ip'):
            self.logger.error("Cannot add device: missing required fields")
            return False
            
        # Add source plugin ID to device metadata
        if 'metadata' not in device_data:
            device_data['metadata'] = {}
        device_data['metadata']['discovery_source'] = self.plugin_id
        
        # Set timestamp if not already present
        if 'first_seen' not in device_data:
            device_data['first_seen'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if 'last_seen' not in device_data:
            device_data['last_seen'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        # Add device to table
        self.main_window.device_table.add_device(device_data)
        return True
    
    def update_device(self, device_data):
        """Update a device in the workspace."""
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return False
            
        # Ensure device has required fields
        if not device_data or not device_data.get('ip'):
            self.logger.error("Cannot update device: missing required fields")
            return False
            
        # Find device row
        row = self.main_window.device_table.find_device_row(device_data['ip'])
        if row is None:
            self.logger.error(f"Cannot update device: device not found with IP {device_data['ip']}")
            return False
            
        # Update device in table
        self.main_window.device_table.update_device_row(row, device_data)
        return True
    
    def remove_device(self, device_id):
        """Remove a device from the workspace."""
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return False
            
        # Find device by ID
        device = None
        for d in self.main_window.device_table.devices:
            if d.get('id') == device_id:
                device = d
                break
                
        if not device:
            self.logger.error(f"Cannot remove device: device not found with ID {device_id}")
            return False
            
        # Find device row
        row = self.main_window.device_table.find_device_row(device['ip'])
        if row is None:
            self.logger.error(f"Cannot remove device: device row not found with IP {device['ip']}")
            return False
            
        # Remove device from table
        self.main_window.device_table.removeRow(row)
        
        # Remove from devices list
        self.main_window.device_table.devices = [d for d in self.main_window.device_table.devices if d['id'] != device_id]
        
        # Remove from all groups
        for group_name, device_ids in self.main_window.device_table.device_groups.items():
            if device_id in device_ids:
                device_ids.remove(device_id)
                
        return True
    
    def search_devices(self, query):
        """Search for devices.
        
        Args:
            query (str): Search query
            
        Returns:
            list: List of matching device dictionaries
        """
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return []
            
        # Simple search implementation
        results = []
        query = query.lower()
        
        for device in self.main_window.device_table.devices:
            # Search in common fields
            if (
                query in device.get('ip', '').lower() or
                query in device.get('hostname', '').lower() or
                query in device.get('mac', '').lower() or
                query in device.get('vendor', '').lower() or
                query in device.get('alias', '').lower()
            ):
                results.append(device)
                continue
                
            # Search in metadata
            if 'metadata' in device:
                for key, value in device['metadata'].items():
                    if isinstance(value, str) and query in value.lower():
                        results.append(device)
                        break
                        
        return results
    
    # Device Groups
    
    def get_device_groups(self):
        """Get all device groups.
        
        Returns:
            dict: Dictionary of group names and their device IDs
        """
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return {}
            
        return self.main_window.device_table.device_groups
    
    def create_device_group(self, group_name):
        """Create a new device group.
        
        Args:
            group_name (str): Name of the group to create
            
        Returns:
            bool: True if creation was successful, False otherwise
        """
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return False
            
        return self.main_window.device_table.create_device_group(group_name)
    
    def delete_device_group(self, group_name):
        """Delete a device group.
        
        Args:
            group_name (str): Name of the group to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return False
            
        return self.main_window.device_table.delete_device_group(group_name)
    
    def add_device_to_group(self, device_id, group_name):
        """Add a device to a group.
        
        Args:
            device_id (str): ID of the device to add
            group_name (str): Name of the group to add to
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return False
            
        return self.main_window.device_table.add_device_to_group(device_id, group_name)
    
    def remove_device_from_group(self, device_id, group_name):
        """Remove a device from a group.
        
        Args:
            device_id (str): ID of the device to remove
            group_name (str): Name of the group to remove from
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return False
            
        return self.main_window.device_table.remove_device_from_group(device_id, group_name)
    
    def get_devices_in_group(self, group_name):
        """Get all devices in a group.
        
        Args:
            group_name (str): Name of the group
            
        Returns:
            list: List of device dictionaries in the group
        """
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return []
            
        return self.main_window.device_table.get_devices_in_group(group_name)
    
    def get_device_groups_for_device(self, device_id):
        """Get all groups a device belongs to.
        
        Args:
            device_id (str): ID of the device
            
        Returns:
            list: List of group names the device belongs to
        """
        if not self.main_window or not hasattr(self.main_window, 'device_table'):
            return []
            
        return self.main_window.device_table.get_device_groups(device_id) 