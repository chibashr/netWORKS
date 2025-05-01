"""
Panel management functions for the netWORKS application.
These functions were extracted from main_window.py to improve modularity.
"""

import logging

# Setup logger
logger = logging.getLogger(__name__)

def register_panel(main_window, panel, location, name=None):
    """Register a panel in the specified location.
    
    Args:
        main_window: Reference to the main window
        panel: QWidget - The panel to register
        location: str - Where to register the panel (left, right, bottom)
        name: str - Optional name for the panel
        
    Returns:
        bool - True if registration was successful
    """
    try:
        # Store original name to help with cleanup
        original_name = panel.objectName()
        
        # Generate unique name for panel if not provided
        if not name:
            plugin_id = panel.property("plugin_id")
            name = f"panel_{plugin_id}_{location}_{id(panel)}"
        
        # Set object name if needed
        if not panel.objectName():
            panel.setObjectName(name)
        
        # Set property to track original name
        panel.setProperty("original_name", original_name)
        
        # Thread safety: ensure panel thread matches main window thread
        if panel.thread() != main_window.thread():
            logger.warning(f"Panel {name} is in a different thread. This may cause UI issues.")
        
        # Make sure panel is parented correctly before attempting to add to UI
        panel.setParent(None)  # Remove any existing parent
        
        # Register panel based on location
        if location.lower() == "left":
            main_window.left_panel.add_plugin_panel(panel, name)
            logger.info(f"Registered left panel: {name}")
            return True
        elif location.lower() == "right":
            main_window.right_panel.add_plugin_panel(panel, name)
            logger.info(f"Registered right panel: {name}")
            return True
        elif location.lower() == "bottom":
            main_window.bottom_panel.add_plugin_panel(panel, name)
            logger.info(f"Registered bottom panel: {name}")
            return True
        else:
            logger.error(f"Invalid panel location: {location}")
            return False
    except Exception as e:
        logger.error(f"Error registering panel: {str(e)}", exc_info=True)
        return False

def remove_panel(main_window, panel):
    """Remove a panel from the UI.
    
    Args:
        main_window: Reference to the main window
        panel: QWidget - The panel to remove
        
    Returns:
        bool - True if removal was successful
    """
    try:
        # Get panel name and plugin ID
        name = panel.objectName()
        plugin_id = panel.property("plugin_id")
        
        # Check if panel is in left panel
        if main_window.left_panel.has_plugin_panel(panel):
            main_window.left_panel.remove_plugin_panel(panel)
            logger.info(f"Removed left panel: {name} from plugin {plugin_id}")
            return True
            
        # Check if panel is in right panel
        if main_window.right_panel.has_plugin_panel(panel):
            main_window.right_panel.remove_plugin_panel(panel)
            logger.info(f"Removed right panel: {name} from plugin {plugin_id}")
            return True
            
        # Check if panel is in bottom panel
        if main_window.bottom_panel.has_plugin_panel(panel):
            main_window.bottom_panel.remove_plugin_panel(panel)
            logger.info(f"Removed bottom panel: {name} from plugin {plugin_id}")
            return True
            
        logger.warning(f"Panel {name} not found in any location")
        return False
    except Exception as e:
        logger.error(f"Error removing panel: {str(e)}", exc_info=True)
        return False

def toggle_left_panel(main_window, checked):
    """Toggle left panel visibility.
    
    Args:
        main_window: Reference to the main window
        checked: bool - Whether the panel should be visible
    """
    main_window.left_panel.setVisible(checked)
    main_window.config["ui"]["panels"]["left"]["visible"] = checked

def toggle_right_panel(main_window, checked):
    """Toggle right panel visibility.
    
    Args:
        main_window: Reference to the main window
        checked: bool - Whether the panel should be visible
    """
    main_window.right_panel.setVisible(checked)
    main_window.config["ui"]["panels"]["right"]["visible"] = checked

def toggle_bottom_panel(main_window, checked):
    """Toggle bottom panel visibility.
    
    Args:
        main_window: Reference to the main window
        checked: bool - Whether the panel should be visible
    """
    main_window.bottom_panel.setVisible(checked)
    main_window.config["ui"]["panels"]["bottom"]["visible"] = checked

def refresh_plugin_panels(main_window):
    """Refresh all plugin panels in the UI.
    
    This method removes existing plugin panels and reloads them from currently 
    enabled plugins. It's used when plugins are enabled/disabled at runtime.
    
    Args:
        main_window: Reference to the main window
        
    Returns:
        bool - True if refresh was successful
    """
    logger.info("Refreshing plugin panels...")
    
    try:
        # Clear existing plugin panels from layout containers
        main_window.left_panel.clear_plugin_panels()
        main_window.right_panel.clear_plugin_panels()
        main_window.bottom_panel.clear_plugin_panels()
        
        # Rebuild panels from enabled plugins
        if hasattr(main_window, 'plugin_manager'):
            # Get all panel components from enabled plugins
            left_panels = main_window.plugin_manager.get_plugin_ui_components("left")
            right_panels = main_window.plugin_manager.get_plugin_ui_components("right")
            bottom_panels = main_window.plugin_manager.get_plugin_ui_components("bottom")
            
            # Add left panels
            for plugin_id, panel in left_panels:
                panel.setProperty("plugin_id", plugin_id)
                main_window.left_panel.add_plugin_panel(panel)
            
            # Add right panels
            for plugin_id, panel in right_panels:
                panel.setProperty("plugin_id", plugin_id)
                main_window.right_panel.add_plugin_panel(panel)
            
            # Add bottom panels
            for plugin_id, panel in bottom_panels:
                panel.setProperty("plugin_id", plugin_id)
                main_window.bottom_panel.add_tab(panel)
            
        logger.info("Plugin panels refreshed")
        return True
    except Exception as e:
        logger.error(f"Error refreshing plugin panels: {str(e)}", exc_info=True)
        return False 