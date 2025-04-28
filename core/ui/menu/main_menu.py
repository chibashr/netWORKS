#!/usr/bin/env python3
# NetSCAN - Main Menu Component

import sys
import os
import logging
from PySide6.QtWidgets import QMenuBar, QMenu, QDialog, QFileDialog, QInputDialog, QVBoxLayout, QTextBrowser, QPushButton, QLabel, QHBoxLayout, QMessageBox
from PySide6.QtGui import QAction, QKeySequence, QIcon, QFont, QPixmap
from PySide6.QtCore import Qt
from core.ui.dialogs.plugin_manager_dialog import PluginManagerDialog
from core.version import get_version_string, load_manifest
import datetime

logger = logging.getLogger(__name__)

def setup_main_menu(main_window):
    """Setup the main menu bar for the application."""
    menu_bar = main_window.menuBar()
    menu_bar.setMouseTracking(True)
    menu_bar.setVisible(True)
    
    # Store menus for plugin access
    main_window.menus = {}
    main_window.menu_actions = {}  # Store core actions for each menu
    
    # Define core menus that are always shown
    core_menus = {
        "File": "&File",
        "View": "&View",
        "Tools": "&Tools",
        "Plugins": "&Plugins",
        "Help": "&Help"
    }
    
    # Create core menus
    for menu_id, menu_label in core_menus.items():
        menu = menu_bar.addMenu(menu_label)
        menu.setVisible(True)
        menu.setMouseTracking(True)  # Enable mouse tracking
        menu.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Ensure menu receives mouse events
        menu.setStyle(main_window.style())  # Ensure menu has proper style
        # Create the menu before adding actions to ensure it's properly initialized
        menu.menuAction().setVisible(True)
        logger.debug(f"Created menu: {menu_id}")
        main_window.menus[menu_id] = menu
        main_window.menu_actions[menu_id] = []
    
    # Add exit action to File menu
    exit_action = QAction("E&xit", main_window)
    exit_action.setShortcut(QKeySequence.StandardKey.Quit)
    exit_action.triggered.connect(main_window.close)
    main_window.menus["File"].addAction(exit_action)
    main_window.menu_actions["File"].append(exit_action)
    
    # Add actions to View menu
    toggle_left_panel_action = QAction("Left Panel", main_window)
    toggle_left_panel_action.setCheckable(True)
    toggle_left_panel_action.setChecked(True)
    toggle_left_panel_action.triggered.connect(main_window.toggle_left_panel)
    main_window.menus["View"].addAction(toggle_left_panel_action)
    main_window.menu_actions["View"].append(toggle_left_panel_action)
    
    toggle_right_panel_action = QAction("Right Panel", main_window)
    toggle_right_panel_action.setCheckable(True)
    toggle_right_panel_action.setChecked(True)
    toggle_right_panel_action.triggered.connect(main_window.toggle_right_panel)
    main_window.menus["View"].addAction(toggle_right_panel_action)
    main_window.menu_actions["View"].append(toggle_right_panel_action)
    
    toggle_bottom_panel_action = QAction("Bottom Panel", main_window)
    toggle_bottom_panel_action.setCheckable(True)
    toggle_bottom_panel_action.setChecked(True)
    toggle_bottom_panel_action.triggered.connect(main_window.toggle_bottom_panel)
    main_window.menus["View"].addAction(toggle_bottom_panel_action)
    main_window.menu_actions["View"].append(toggle_bottom_panel_action)
    
    main_window.menus["View"].addSeparator()
    
    # Add table columns customization option
    customize_columns_action = QAction("Customize Columns...", main_window)
    customize_columns_action.triggered.connect(main_window.customize_table_columns)
    main_window.menus["View"].addAction(customize_columns_action)
    main_window.menu_actions["View"].append(customize_columns_action)
    
    # Add device alias manager
    device_alias_action = QAction("Manage Device Aliases...", main_window)
    device_alias_action.triggered.connect(main_window.manage_device_aliases)
    main_window.menus["View"].addAction(device_alias_action)
    main_window.menu_actions["View"].append(device_alias_action)
    
    # Add manage plugins action to Plugins menu
    manage_plugins_action = QAction("&Manage Plugins", main_window)
    manage_plugins_action.triggered.connect(lambda: show_plugin_manager(main_window))
    main_window.menus["Plugins"].addAction(manage_plugins_action)
    main_window.menu_actions["Plugins"].append(manage_plugins_action)
    
    # Add about and docs actions to Help menu
    about_action = QAction("&About", main_window)
    about_action.triggered.connect(lambda: show_about(main_window))
    main_window.menus["Help"].addAction(about_action)
    main_window.menu_actions["Help"].append(about_action)
    
    docs_action = QAction("&Documentation", main_window)
    docs_action.triggered.connect(lambda: show_documentation(main_window))
    main_window.menus["Help"].addAction(docs_action)
    main_window.menu_actions["Help"].append(docs_action)
    
    # Create plugin-only menus (these will only show when they have items)
    plugin_menus = ["Diagnostics", "Network", "Security"]
    for menu_name in plugin_menus:
        menu = QMenu(f"&{menu_name}", main_window)
        menu.setVisible(True)
        menu.setMouseTracking(True)  # Enable mouse tracking
        menu.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Ensure menu receives mouse events
        menu.setStyle(main_window.style())  # Ensure menu has proper style
        logger.debug(f"Created plugin menu: {menu_name}")
        main_window.menus[menu_name] = menu
        main_window.menu_actions[menu_name] = []
    
    # Register menu callback to handle plugin menu items
    main_window.plugin_manager.register_menu_callback(lambda: refresh_plugin_menus(main_window))

def refresh_plugin_menus(main_window):
    """Refresh plugin menu items."""
    menu_bar = main_window.menuBar()
    
    # Get all plugin menu items
    menu_items = main_window.plugin_manager.get_plugin_menu_items()
    
    # Group items by parent menu
    menu_groups = {}
    for item in menu_items:
        parent = item.get('parent_menu', 'Plugins')
        if parent not in menu_groups:
            menu_groups[parent] = []
        menu_groups[parent].append(item)
    
    # Process each menu
    for menu_name, menu in main_window.menus.items():
        # Ensure menu is visible before adding items
        menu.menuAction().setVisible(True)
        menu.setVisible(True)
        menu.setMouseTracking(True)
        
        # Store old actions to properly clean them up
        old_actions = []
        for action in menu.actions():
            if action not in main_window.menu_actions.get(menu_name, []):
                old_actions.append(action)
        
        # Handle core menus (always shown)
        if menu_name in ["File", "View", "Tools", "Plugins", "Help"]:
            # Keep existing core actions
            menu.clear()
            for action in main_window.menu_actions[menu_name]:
                menu.addAction(action)
            
            # Add plugin items if any
            if menu_name in menu_groups:
                if main_window.menu_actions[menu_name]:
                    menu.addSeparator()
                for item in menu_groups[menu_name]:
                    if item['label'] == '---':
                        menu.addSeparator()
                    else:
                        # Create action with proper parent
                        action = QAction(item['label'], menu)
                        if item.get('icon_path'):
                            action.setIcon(QIcon(item['icon_path']))
                        if item.get('shortcut'):
                            action.setShortcut(item['shortcut'])
                        if item['callback']:
                            # Use lambda with default argument to prevent late binding
                            action.triggered.connect(lambda checked=False, cb=item['callback']: cb())
                        if item['enabled_callback']:
                            action.setEnabled(item['enabled_callback'](None))
                        menu.addAction(action)
            
            # Ensure menu is visible and properly styled
            menu.setVisible(True)
            menu.setStyle(main_window.style())
        else:
            # Handle plugin-only menus
            if menu.parentWidget() == menu_bar:
                menu_bar.removeAction(menu.menuAction())
            
            menu.clear()
            if menu_name in menu_groups:
                for item in menu_groups[menu_name]:
                    if item['label'] == '---':
                        menu.addSeparator()
                    else:
                        # Create action with proper parent
                        action = QAction(item['label'], menu)
                        if item.get('icon_path'):
                            action.setIcon(QIcon(item['icon_path']))
                        if item.get('shortcut'):
                            action.setShortcut(item['shortcut'])
                        if item['callback']:
                            # Use lambda with default argument to prevent late binding
                            action.triggered.connect(lambda checked=False, cb=item['callback']: cb())
                        if item['enabled_callback']:
                            action.setEnabled(item['enabled_callback'](None))
                        menu.addAction(action)
                
                if not menu.isEmpty():
                    help_action = main_window.menus["Help"].menuAction()
                    menu_bar.insertMenu(help_action, menu)
                    # Ensure menu is visible and properly styled
                    menu.setVisible(True)
                    menu.setStyle(main_window.style())
        
        # Clean up old actions
        for action in old_actions:
            action.deleteLater()

def show_plugin_manager(main_window):
    """Show the plugin manager dialog."""
    dialog = PluginManagerDialog(main_window, main_window.plugin_manager)
    dialog.exec()

def show_preferences(main_window):
    """Show preferences dialog."""
    # Placeholder
    pass

def refresh_view(main_window):
    """Refresh the view."""
    # Placeholder - will be implemented by specific components
    pass

def show_scan_settings(main_window):
    """Show scan settings dialog."""
    # Placeholder
    pass

def show_about(main_window):
    """Show about dialog."""
    # Create dialog
    dialog = QDialog(main_window)
    dialog.setWindowTitle("About netWORKS")
    dialog.setFixedSize(500, 350)
    
    # Create layout
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 20, 20, 20)
    
    # Application title
    title = QLabel("netWORKS")
    title_font = QFont()
    title_font.setPointSize(24)
    title_font.setBold(True)
    title.setFont(title_font)
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    
    # Version information
    version_str = get_version_string()
    version = QLabel(f"Version {version_str}")
    version.setAlignment(Qt.AlignCenter)
    layout.addWidget(version)
    
    # Load full manifest for additional details
    manifest = load_manifest()
    if manifest:
        build_date = manifest.get("build_date", "Unknown")
        build_date_label = QLabel(f"Build Date: {build_date}")
        build_date_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(build_date_label)
    
    # Description
    description = QLabel("Network scanning and management tool")
    description.setAlignment(Qt.AlignCenter)
    layout.addWidget(description)
    
    # Add spacer
    layout.addSpacing(20)
    
    # System information
    import platform
    import sys
    system_info = QLabel(f"System: {platform.system()} {platform.release()}")
    system_info.setAlignment(Qt.AlignCenter)
    layout.addWidget(system_info)
    
    python_info = QLabel(f"Python: {platform.python_version()}")
    python_info.setAlignment(Qt.AlignCenter)
    layout.addWidget(python_info)
    
    # Copyright information
    copyright_info = QLabel("© 2023-2024 netWORKS Team. All rights reserved.")
    copyright_info.setAlignment(Qt.AlignCenter)
    layout.addWidget(copyright_info)
    
    # Add spacer
    layout.addSpacing(20)
    
    # Button layout
    button_layout = QHBoxLayout()
    
    # Add spacer to push button to the right
    button_layout.addStretch()
    
    # Close button
    close_button = QPushButton("Close")
    close_button.clicked.connect(dialog.close)
    button_layout.addWidget(close_button)
    
    layout.addLayout(button_layout)
    
    # Show dialog
    dialog.exec()

def show_documentation(main_window):
    """Show the documentation."""
    # Create dialog
    dialog = QDialog(main_window)
    dialog.setWindowTitle("NetSCAN Documentation")
    dialog.setMinimumSize(800, 600)
    
    # Create layout
    layout = QVBoxLayout(dialog)
    
    # Create text browser for documentation
    browser = QTextBrowser()
    browser.setOpenExternalLinks(True)
    layout.addWidget(browser)
    
    # Load documentation content
    docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs")
    
    # Read main README.md
    readme_path = os.path.join(docs_path, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
            browser.setMarkdown(content)
    
    # Add close button
    close_button = QPushButton("Close")
    close_button.clicked.connect(dialog.close)
    layout.addWidget(close_button)
    
    # Show dialog
    dialog.exec()

def check_for_updates(main_window):
    """Check for application updates."""
    # Update check would be implemented here
    main_window.bottom_panel.add_log_entry("Checking for updates...") 