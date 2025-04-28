#!/usr/bin/env python3
# NetSCAN - Right Panel UI Component

import sys
import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, 
    QPushButton, QGroupBox, QTabWidget, QScrollArea, QFrame
)
from PySide6.QtCore import Qt

class RightPanel(QScrollArea):
    """Right panel container for plugin widgets."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.plugin_tabs = {}  # Store plugin tabs by name
        self.plugin_panels = {}  # Track plugin panels by ID
        self.logger = logging.getLogger(__name__)
        self.init_ui()
        self.setStyleSheet("""
            QScrollArea {
                background-color: #ffffff;
                border: none;
            }
            QWidget {
                background-color: #ffffff;
                color: #000000;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background: #ffffff;
            }
            QTabBar::tab {
                background: #f5f5f5;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
                color: #666666;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #000000;
            }
            QTabBar::tab:hover {
                background: #e0e0e0;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding: 8px;
            }
            QGroupBox::title {
                color: #000000;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 2px;
                padding: 4px;
            }
            QTextEdit:focus {
                border-color: #0078d4;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 2px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #999999;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                border-color: #dddddd;
                color: #999999;
            }
            QLabel {
                color: #000000;
                padding: 2px;
            }
        """)

    def init_ui(self):
        """Initialize the user interface."""
        # Create main widget and layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Configure scroll area
        self.setWidget(self.main_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Make sure tabs fit width when panel is resized
        self.tab_widget.setUsesScrollButtons(True)
        self.tab_widget.setElideMode(Qt.TextElideMode.ElideRight)

    def resizeEvent(self, event):
        """Handle resize events for the panel."""
        super().resizeEvent(event)
        
        # When panel is resized, make sure the tab widget adjusts properly
        if hasattr(self, 'tab_widget') and self.tab_widget:
            self.tab_widget.setFixedWidth(self.width() - 2)
            
            # Update any tab widgets within plugin panels
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                # Check if the tab has a tab widget as a direct child
                for child in tab.children():
                    if isinstance(child, QTabWidget):
                        child.setMaximumWidth(self.width() - 20)
                        
        # Force update of the widget layout
        self.main_widget.updateGeometry()

    def add_plugin_panel(self, panel, name=None):
        """Add a plugin panel to the right panel.
        
        Args:
            panel: QWidget - The panel to add
            name: str - Name for the panel tab
            
        Returns:
            bool - True if addition was successful
        """
        try:
            # Get plugin ID from panel properties
            plugin_id = panel.property("plugin_id")
            if not plugin_id:
                self.logger.warning(f"Panel {name} has no plugin_id property")
                plugin_id = "unknown"
            
            # Require a name for tab
            if not name:
                name = f"Plugin {plugin_id}"
            
            # Check if a tab with this name already exists
            if name in self.plugin_tabs:
                self.logger.warning(f"Tab {name} already exists, not adding duplicate")
                return False
            
            # Add panel to tab widget
            panel.setParent(None)  # Remove any existing parent
            self.tab_widget.addTab(panel, name)
            
            # Store references
            self.plugin_tabs[name] = panel
            panel_id = panel.objectName() or id(panel)
            self.plugin_panels[panel_id] = {
                'widget': panel,
                'plugin_id': plugin_id,
                'name': name
            }
            
            self.logger.debug(f"Added plugin tab: {name} from {plugin_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding plugin tab: {str(e)}", exc_info=True)
            return False

    def add_widget(self, widget, name=None):
        """Add a widget as a new tab (legacy method).
        
        This method is kept for backward compatibility.
        New code should use add_plugin_panel instead.
        """
        return self.add_plugin_panel(widget, name)

    def remove_plugin_panel(self, panel):
        """Remove a plugin panel from the right panel.
        
        Args:
            panel: QWidget - The panel to remove
            
        Returns:
            bool - True if removal was successful
        """
        try:
            # Get panel ID
            panel_id = panel.objectName() or id(panel)
            
            # If we have this panel registered
            if panel_id in self.plugin_panels:
                panel_info = self.plugin_panels[panel_id]
                name = panel_info['name']
                
                # Remove from tab widget
                index = self.tab_widget.indexOf(panel)
                if index != -1:
                    self.tab_widget.removeTab(index)
                
                # Remove from tracking dictionaries
                if name in self.plugin_tabs:
                    del self.plugin_tabs[name]
                del self.plugin_panels[panel_id]
                
                # Don't delete the panel, just remove it from parent
                panel.setParent(None)
                
                self.logger.debug(f"Removed plugin panel: {panel_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing plugin panel: {str(e)}", exc_info=True)
            return False

    def remove_widget(self, name):
        """Remove a plugin tab by name (legacy method)."""
        if name in self.plugin_tabs:
            panel = self.plugin_tabs[name]
            return self.remove_plugin_panel(panel)
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

    def ping_device(self):
        """Ping the currently selected device."""
        # This will be implemented to ping the selected device
        selected_device = self.main_window.device_table.get_selected_device()
        if selected_device:
            # Logic to ping the device would go here
            self.main_window.statusBar.showMessage(f"Pinging {selected_device.get('ip')}...")
    
    def traceroute_device(self):
        """Perform a traceroute to the currently selected device."""
        # This will be implemented to perform a traceroute to the selected device
        selected_device = self.main_window.device_table.get_selected_device()
        if selected_device:
            # Logic to traceroute the device would go here
            self.main_window.statusBar.showMessage(f"Traceroute to {selected_device.get('ip')}...")
    
    def save_notes(self):
        """Save notes for the currently selected device or workspace."""
        # This will be implemented to save notes
        self.main_window.statusBar.showMessage("Notes saved.")
        
    def get_notes(self):
        """Get the current notes text."""
        return self.notes_edit.toPlainText()
    
    def set_notes(self, notes):
        """Set the notes text."""
        self.notes_edit.setPlainText(notes) 