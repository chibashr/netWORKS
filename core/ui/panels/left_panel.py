#!/usr/bin/env python3
# NetSCAN - Left Panel UI Component

import sys
import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSizePolicy, QScrollArea, QFrame
)
from PySide6.QtCore import Qt

class LeftPanel(QScrollArea):
    """Left panel container for plugin widgets."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.logger = logging.getLogger(__name__)
        self.plugin_panels = {}  # Track plugin panels by ID
        self.init_ui()
        self.setStyleSheet("""
            QScrollArea {
                background-color: #ffffff;
                border: none;
            }
            QWidget {
                color: #000000;
            }
        """)

    def init_ui(self):
        # Create main widget and layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)  # Add some padding
        self.main_layout.setSpacing(5)  # Add spacing between widgets

        # Set size policies for the main widget
        self.main_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_widget.setMinimumWidth(200)  # Set minimum width to prevent too narrow panels

        # Configure scroll area
        self.setWidget(self.main_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # Show horizontal scroll when needed
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)    # Show vertical scroll when needed
        self.setFrameShape(QFrame.Shape.NoFrame)

        # Set size policy for the scroll area itself
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def add_plugin_panel(self, panel, name=None):
        """Add a plugin panel to the left panel.
        
        Args:
            panel: QWidget - The panel to add
            name: str - Optional name for the panel
            
        Returns:
            bool - True if addition was successful
        """
        try:
            # Set name if provided
            if name and not panel.objectName():
                panel.setObjectName(name)
            
            # Get plugin ID from panel properties
            plugin_id = panel.property("plugin_id")
            if not plugin_id:
                self.logger.warning(f"Panel {name} has no plugin_id property")
                plugin_id = "unknown"
            
            # Add panel to layout
            panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self.main_layout.addWidget(panel)
            
            # Store reference to panel
            panel_id = panel.objectName() or id(panel)
            self.plugin_panels[panel_id] = {
                'widget': panel,
                'plugin_id': plugin_id,
                'name': name
            }
            
            self.logger.debug(f"Added plugin panel: {name} from {plugin_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding plugin panel: {str(e)}", exc_info=True)
            return False

    def add_widget(self, widget, name=None):
        """Add a widget to the panel (legacy method).
        
        This method is kept for backward compatibility.
        New code should use add_plugin_panel instead.
        """
        return self.add_plugin_panel(widget, name)

    def addWidget(self, widget):
        """Qt-style convenience method."""
        return self.add_plugin_panel(widget)

    def remove_plugin_panel(self, panel):
        """Remove a plugin panel from the left panel.
        
        Args:
            panel: QWidget - The panel to remove
            
        Returns:
            bool - True if removal was successful
        """
        try:
            # Get panel ID
            panel_id = panel.objectName() or id(panel)
            
            # Remove from layout
            self.main_layout.removeWidget(panel)
            
            # Remove from tracking dictionary
            if panel_id in self.plugin_panels:
                del self.plugin_panels[panel_id]
                
            # Don't delete the panel, just remove it from parent
            panel.setParent(None)
            
            self.logger.debug(f"Removed plugin panel: {panel_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing plugin panel: {str(e)}", exc_info=True)
            return False

    def remove_widget(self, name):
        """Remove a plugin widget by name (legacy method)."""
        # Find and remove widget by name
        for panel_id, panel_info in list(self.plugin_panels.items()):
            if panel_info['name'] == name:
                return self.remove_plugin_panel(panel_info['widget'])
        return False
    
    def has_plugin_panel(self, panel):
        """Check if a panel is in this container.
        
        Args:
            panel: QWidget - The panel to check
            
        Returns:
            bool - True if panel is in this container
        """
        panel_id = panel.objectName() or id(panel)
        return panel_id in self.plugin_panels 