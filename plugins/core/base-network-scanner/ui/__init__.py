#!/usr/bin/env python3
# Base Network Scanner Plugin - UI Components

"""
UI components for the Base Network Scanner plugin.

This module initializes the UI components for the plugin, ensuring proper
import order to avoid circular dependencies.
"""

import logging

logger = logging.getLogger("plugin.base_network_scanner.ui")
logger.debug("Loading base-network-scanner UI components")

# Import individual components - note that the order matters to avoid import cycles
from . import left_panel
from . import right_panel  
from . import bottom_panel

# Import main panel last to avoid circular imports
from . import main_panel

# Export the main components for easy importing from the parent module
__all__ = ['main_panel', 'left_panel', 'right_panel', 'bottom_panel']

logger.debug("Base network scanner UI components loaded successfully") 