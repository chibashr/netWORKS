#!/usr/bin/env python3
# NetSCAN - Bottom Panel UI Component

import sys
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QSizePolicy, QScrollArea, QTabBar
)
from PySide6.QtGui import QColor, QIcon, QTextCursor
from PySide6.QtCore import Qt
import datetime
import logging

# Color map for log levels
LOG_COLORS = {
    "INFO": QColor("black"),
    "WARNING": QColor("orange"),
    "ERROR": QColor("red"),
    "DEBUG": QColor("gray")
}

class BottomPanel(QTabWidget):
    """Bottom panel for logs, scan history, and plugin output."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.logger = logging.getLogger(__name__)
        
        # Create Tab Widget
        self.setTabPosition(QTabWidget.TabPosition.South)
        self.setTabsClosable(False)  # Default panels are not closable
        self.setMovable(True)  # Allow moving tabs
        
        # Set minimum height to be very small for maximum flexibility
        self.setMinimumHeight(5)  # Very small minimum height
        
        # Enable scroll bars for better handling of content
        self.setElideMode(Qt.TextElideMode.ElideRight)
        
        # Setup style for bottom panel
        self.setup_style()
        
        # Initialize UI
        self.init_ui()
        
        # Track plugin panels
        self.plugin_panels = {}  # Dictionary to track panel ID -> panel info
        self.plugin_tabs = {}  # Dictionary to track tab name -> panel
    
    def setup_style(self):
        """Setup the style for the bottom panel."""
        self.setStyleSheet("""
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
            QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
            }
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f9f9f9;
                border: 1px solid #cccccc;
                border-radius: 4px;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-left: none;
                padding: 4px;
            }
            QHeaderView::section:first {
                border-left: 1px solid #cccccc;
                border-top-left-radius: 4px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 4px;
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f5f5;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #cccccc;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal {
                border: none;
                background: #f5f5f5;
                height: 10px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #cccccc;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }
        """)
    
    def init_ui(self):
        """Initialize the user interface."""
        # Create and add Device tab (always visible)
        self.device_details_widget = QWidget()
        details_layout = QVBoxLayout(self.device_details_widget)
        # Set layout with no margin to maximize space
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        self.device_details = QTextEdit()
        self.device_details.setReadOnly(True)
        # Set the text edit to have fixed height and vertical scroll policy
        self.device_details.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.device_details.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.device_details.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Set default message
        self.device_details.setHtml("<p>No device selected</p>")
        
        details_layout.addWidget(self.device_details)
        self.device_details_tab_index = self.addTab(self.device_details_widget, "Device Details")
    
    def add_plugin_panel(self, panel, name, icon=None, closable=True):
        """Add a plugin panel to the bottom panel tabs.
        
        Args:
            panel: QWidget - The panel to add
            name: str - The name/title for the tab
            icon: QIcon - Optional icon for the tab
            closable: bool - Whether the tab can be closed by the user
            
        Returns:
            int - The index of the added tab
        """
        try:
            # Set proper size policy for plugin panels
            panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            panel.setMinimumHeight(0)  # Allow panel to resize to very small height
            
            # Get panel ID (preferring objectName if set, otherwise using id)
            panel_id = panel.objectName() or id(panel)
            
            # Register panel
            self.plugin_panels[panel_id] = {
                'panel': panel,
                'name': name,
                'icon': icon,
                'closable': closable
            }
            
            # Register in legacy dict as well for compatibility
            self.plugin_tabs[name] = panel
            
            # Add tab
            if icon:
                tab_index = self.addTab(panel, icon, name)
            else:
                tab_index = self.addTab(panel, name)
            
            # Configure tab closable property
            self.setTabsClosable(True)  # Enable close buttons
            
            # Hide close button for non-closable tabs
            if not closable:
                self.tabBar().setTabButton(tab_index, QTabBar.ButtonPosition.RightSide, None)
            
            # Set objectName for panel
            panel.setObjectName(panel_id)
            
            # Connect to tab close event if not already connected
            if not self.tabCloseRequested.isSignalConnected(self.on_tab_close_requested):
                self.tabCloseRequested.connect(self.on_tab_close_requested)
            
            # Return the tab index
            return tab_index
        except Exception as e:
            self.logger.error(f"Error adding plugin panel: {str(e)}", exc_info=True)
            return -1
        
    def on_tab_close_requested(self, index):
        """Handle tab close button click."""
        try:
            # Get panel at index
            panel = self.widget(index)
            if not panel:
                return
            
            # Check if panel is closable
            panel_id = panel.objectName() or id(panel)
            if panel_id in self.plugin_panels and not self.plugin_panels[panel_id]['closable']:
                # Not closable
                return
            
            # Remove the tab
            self.removeTab(index)
            
            # Remove from tracking dictionaries
            if panel_id in self.plugin_panels:
                name = self.plugin_panels[panel_id]['name']
                del self.plugin_panels[panel_id]
                if name in self.plugin_tabs:
                    del self.plugin_tabs[name]
        except Exception as e:
            self.logger.error(f"Error closing tab: {str(e)}", exc_info=True)
    
    def resizeEvent(self, event):
        """Handle resize events to ensure proper panel resizing.
        
        This ensures the content of the panels adjusts properly to the size changes.
        """
        super().resizeEvent(event)
        
        # Resize all contained widgets to match the new size
        for i in range(self.count()):
            widget = self.widget(i)
            if widget:
                # Ensure the widget resizes properly when panel is resized
                widget.updateGeometry()
                
                # Check for embedded scroll areas and resize them
                scroll_areas = widget.findChildren(QScrollArea)
                for scroll_area in scroll_areas:
                    scroll_area.updateGeometry()
                    
                # Check for embedded tab widgets and resize them
                tab_widgets = widget.findChildren(QTabWidget)
                for tab_widget in tab_widgets:
                    tab_widget.updateGeometry()
                    
        # Update tab bar to ensure it's properly sized
        self.tabBar().updateGeometry()
    
    def update_device_details(self, device):
        """Update the device details panel with selected device information."""
        if device:
            # Get the alias from the device or its metadata
            alias = device.get('alias', '')
            if not alias and 'metadata' in device and 'alias' in device['metadata']:
                alias = device['metadata']['alias']
            
            hostname = device.get('hostname', 'Unknown Device')
            title = hostname
            if alias:
                title = f"{alias} ({hostname})"
            
            details = f"""
            <h3>{title}</h3>
            <p><b>IP Address:</b> {device.get('ip', 'N/A')}</p>
            <p><b>MAC Address:</b> {device.get('mac', 'N/A')}</p>
            """
            
            # Add alias if exists
            if alias:
                details += f"<p><b>Alias:</b> {alias}</p>"
                
            # Add first/last seen
            details += f"""
            <p><b>First Seen:</b> {device.get('first_seen', 'N/A')}</p>
            <p><b>Last Seen:</b> {device.get('last_seen', 'N/A')}</p>
            """

            # Add metadata if any
            if device.get('metadata'):
                details += "<h4>Metadata</h4>"
                for key, value in device['metadata'].items():
                    # Skip alias as it's already shown
                    if key != 'alias':
                        details += f"<p><b>{key}:</b> {value}</p>"

            # Add tags if any
            if device.get('tags'):
                details += f"<h4>Tags</h4><p>{', '.join(device['tags'])}</p>"

            self.device_details.setHtml(details)
            
            # Switch to the device details tab when a device is selected
            self.setCurrentIndex(self.device_details_tab_index)
        else:
            # Show default message if no device is selected
            self.device_details.setHtml("<p>No device selected</p>")
    
    def add_log_entry(self, message, level="INFO"):
        """Add an entry to the log."""
        # Find the log tab if it exists
        log_tab = self.findChild(QTextEdit, "log_edit")
        if log_tab:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level}] {message}"
            log_tab.append(log_entry)
        else:
            # Log message without showing it if log tab doesn't exist
            self.logger.log(getattr(logging, level, logging.INFO), message)
    
    def add_console_message(self, message, level="INFO"):
        """Add a message to the console tab.
        
        Args:
            message: str - The message to add
            level: str - Message level (INFO, WARNING, ERROR, DEBUG)
        """
        # This method is kept for backward compatibility
        self.add_log_entry(message, level)

    def add_scan_history_entry(self, interface, ip_range, devices_found, duration):
        """Add an entry to the scan history table."""
        row_position = self.scan_history_table.rowCount()
        self.scan_history_table.insertRow(row_position)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Set table items
        self.scan_history_table.setItem(row_position, 0, QTableWidgetItem(timestamp))
        self.scan_history_table.setItem(row_position, 1, QTableWidgetItem(interface))
        self.scan_history_table.setItem(row_position, 2, QTableWidgetItem(ip_range))
        self.scan_history_table.setItem(row_position, 3, QTableWidgetItem(str(devices_found)))
        self.scan_history_table.setItem(row_position, 4, QTableWidgetItem(f"{duration:.2f}s"))
        
        # Log the scan as well
        self.add_log_entry(f"Scan completed on {interface}, {ip_range}: found {devices_found} devices in {duration:.2f}s")
    
    def add_traffic_entry(self, source, destination, protocol, size):
        """Add an entry to the network traffic table."""
        row_position = self.traffic_table.rowCount()
        self.traffic_table.insertRow(row_position)
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Set table items
        self.traffic_table.setItem(row_position, 0, QTableWidgetItem(timestamp))
        self.traffic_table.setItem(row_position, 1, QTableWidgetItem(source))
        self.traffic_table.setItem(row_position, 2, QTableWidgetItem(destination))
        self.traffic_table.setItem(row_position, 3, QTableWidgetItem(protocol))
        self.traffic_table.setItem(row_position, 4, QTableWidgetItem(f"{size} bytes"))

    def clear_plugin_panels(self):
        """Remove all plugin panels from the bottom panel.
        
        This is used when reloading the UI after plugin changes.
        
        Returns:
            bool - True if operation was successful
        """
        try:
            # Create a copy of the panels dict to iterate over while modifying
            panels_to_remove = list(self.plugin_panels.values())
            
            # Remove each panel
            for panel_info in panels_to_remove:
                self.remove_plugin_panel(panel_info['panel'])
            
            self.logger.debug(f"Cleared {len(panels_to_remove)} plugin panels from bottom panel")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing plugin panels: {str(e)}", exc_info=True)
            return False
            
    def remove_plugin_panel(self, panel):
        """Remove a plugin panel from the bottom panel.
        
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
                index = self.indexOf(panel)
                if index != -1:
                    self.removeTab(index)
                
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
            
    def has_plugin_panel(self, panel):
        """Check if a panel is in this container.
        
        Args:
            panel: QWidget - The panel to check
            
        Returns:
            bool - True if panel is in this container
        """
        panel_id = panel.objectName() or id(panel)
        return panel_id in self.plugin_panels 