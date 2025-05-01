"""
Toolbar management functions for the netWORKS application.
These functions were extracted from main_window.py to improve modularity.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt

# Setup logger
logger = logging.getLogger(__name__)

def create_toolbar_group(main_window, title, parent_tab):
    """Create a group in the toolbar with a title and content area.
    
    Args:
        title (str): The title of the group
        parent_tab (QWidget): The parent tab widget
        
    Returns:
        QWidget: The content widget to add items to
    """
    # Create group container
    group_container = QWidget()
    group_container.setProperty("ribbonGroup", True)
    
    # Set layout
    group_layout = QVBoxLayout(group_container)
    group_layout.setContentsMargins(2, 2, 2, 2)
    group_layout.setSpacing(2)
    
    # Create title label
    title_label = QLabel(title)
    title_label.setProperty("groupTitle", True)
    title_label.setAlignment(Qt.AlignCenter)
    
    # Create content widget
    content_widget = QWidget()
    content_widget.setLayout(QHBoxLayout())
    content_widget.layout().setContentsMargins(2, 2, 2, 2)
    content_widget.layout().setSpacing(1)
    content_widget.layout().setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    
    # Add title and content to group
    group_layout.addWidget(title_label)
    group_layout.addWidget(content_widget)
    
    # Add to parent tab
    parent_tab.layout().addWidget(group_container)
    
    # Utility function to check if the group is empty
    def check_empty():
        """Check if the group has any visible widgets."""
        for i in range(content_widget.layout().count()):
            item = content_widget.layout().itemAt(i)
            if item.widget() and item.widget().isVisible():
                return False
        return True
    
    # Attach the function to the content widget for later use
    content_widget.check_empty = check_empty
    
    # Helper function to add a widget and update visibility
    def add_widget_with_visibility_update(widget):
        """Add a widget to the content and update group visibility."""
        content_widget.layout().addWidget(widget)
        # Update group visibility in case this was the first widget
        group_container.setVisible(not check_empty())
        main_window.update_toolbar_groups_visibility()
        
    # Attach the helper function
    content_widget.add_widget_with_visibility_update = add_widget_with_visibility_update
    
    return content_widget

def add_toolbar_separator(main_window, parent_tab):
    """Add a vertical separator to a toolbar tab.
    
    Args:
        parent_tab (QWidget): The parent tab widget
    """
    separator = QFrame()
    separator.setFrameShape(QFrame.VLine)
    separator.setFrameShadow(QFrame.Sunken)
    separator.setFixedWidth(1)
    separator.setProperty("ribbonSeparator", True)
    separator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    separator.setStyleSheet("""
        QFrame {
            background-color: #e0e0e0;
            margin-top: 4px;
            margin-bottom: 4px;
        }
    """)
    parent_tab.layout().addWidget(separator)

def update_toolbar_groups_visibility(main_window):
    """Check all toolbar groups and hide empty ones."""
    # Process all tabs
    for tab_index in range(main_window.toolbar.count()):
        tab = main_window.toolbar.widget(tab_index)
        empty_tabs = True
        
        # Check each item in this tab
        if hasattr(tab, 'layout'):
            for i in range(tab.layout().count()):
                item = tab.layout().itemAt(i).widget()
                if item and item.property("ribbonGroup"):
                    content_layout = item.layout().itemAt(1).widget().layout()
                    if content_layout.count() == 0:
                        # Hide empty groups
                        item.setVisible(False)
                    else:
                        # Show non-empty groups
                        item.setVisible(True)
                        empty_tabs = False
                elif item and item.property("ribbonSeparator") and i > 0 and i < tab.layout().count() - 1:
                    # Get the widgets on either side of this separator
                    prev_widget = tab.layout().itemAt(i-1).widget()
                    next_widget = tab.layout().itemAt(i+1).widget()
                    
                    # Only show the separator if both adjacent widgets are visible
                    item.setVisible(
                        prev_widget and next_widget and 
                        prev_widget.isVisible() and next_widget.isVisible()
                    )
            
            # Hide tabs that are completely empty
            tab_bar = main_window.toolbar.tabBar()
            tab_bar.setTabVisible(tab_index, not empty_tabs) 