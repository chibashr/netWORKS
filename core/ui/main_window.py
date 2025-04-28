#!/usr/bin/env python3
# NetSCAN - Main Window UI Component

import sys
import os
import json
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QSplitter, QToolBar, QStatusBar, QMessageBox, QLabel, QProgressBar, QTabWidget,
    QToolButton, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QEvent, QTimer
from PySide6.QtGui import QIcon, QAction

from core.ui.panels.left_panel import LeftPanel
from core.ui.panels.right_panel import RightPanel
from core.ui.panels.bottom_panel import BottomPanel
from core.ui.table.device_table import DeviceTable
from core.ui.menu.main_menu import setup_main_menu
from core.database.device_manager import DeviceDatabaseManager

class MainWindow(QMainWindow):
    """Main application window for NetSCAN."""
    
    def __init__(self, plugin_manager):
        super().__init__()
        
        self.plugin_manager = plugin_manager
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing main window")
        
        # Initialize menus dictionary
        self.menus = {}
        self.menu_actions = {}
        
        # Initialize database manager
        self.database_manager = DeviceDatabaseManager(self)
        self.logger.debug("Database manager initialized")
        
        # Initialize config first
        self.load_config()
        
        # Create the toolbar first
        self.setup_toolbar()
        
        # Setup main menu and transfer actions to ribbon
        self.setup_menus()
        
        # Initialize UI components
        self.init_ui()
        
        # Set main window reference in plugin APIs after UI is initialized
        try:
            for plugin_id, plugin_info in self.plugin_manager.plugins.items():
                if plugin_info.get("enabled", False) and plugin_info.get("instance"):
                    plugin_api = self.plugin_manager.plugin_apis.get(plugin_id)
                    if plugin_api:
                        try:
                            plugin_api.set_main_window(self)
                            self.logger.info(f"Set main window reference for plugin {plugin_id}")
                        except Exception as e:
                            self.logger.error(f"Error setting main window for plugin {plugin_id}: {str(e)}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Error initializing plugins: {str(e)}", exc_info=True)
            # Show error dialog but continue
            self.show_error_dialog("Plugin Initialization Error", 
                                  f"There was an error initializing one or more plugins: {str(e)}\n\n"
                                  "The application will continue to run with limited functionality.")
    
    def load_config(self):
        """Load application configuration."""
        config_path = os.path.join('config', 'settings.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                self.config = self.get_default_config()
                print(f"Error loading config: {e}")
        else:
            self.config = self.get_default_config()
            os.makedirs('config', exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
    
    def get_default_config(self):
        """Return default configuration."""
        return {
            "app": {
                "theme": "light",
                "auto_save_interval": 300
            },
            "ui": {
                "panels": {
                    "left": {"visible": True, "width": 250},
                    "right": {"visible": True, "width": 300},
                    "bottom": {"visible": True, "height": 200}
                },
                "toolbar": {
                    "visible": True,
                    "pinned": False,
                    "position": "top",
                    "categories": {}
                },
                "table": {
                    "columns": [
                        "ip",
                        "hostname",
                        "mac",
                        "vendor",
                        "scan_method",
                        "ports",
                        "last_seen"
                    ],
                    "sort_by": "ip",
                    "sort_direction": "ascending"
                }
            }
        }
    
    def init_ui(self):
        """Initialize the user interface."""
        self.logger.debug("Setting up main window UI")
        self.setWindowTitle("NetSCAN")
        self.resize(1200, 800)
        
        # Set application-wide style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                background-color: #ffffff;
                color: #333333;
            }
            QMenuBar {
                background-color: #f5f5f5;
                border-bottom: 1px solid #aabbcc;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #e8f0ff;
                color: #2c5aa0;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #aabbcc;
                border-radius: 3px;
            }
            QMenu::item {
                padding: 4px 20px;
            }
            QMenu::item:selected {
                background-color: #e8f0ff;
                color: #2c5aa0;
            }
            QToolBar {
                background-color: #f5f5f5;
                border-bottom: 1px solid #aabbcc;
                spacing: 2px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 3px;
                min-width: 60px;
                min-height: 20px;
            }
            QToolBar QToolButton:hover {
                background-color: #e8f0ff;
                border: 1px solid #aabbcc;
            }
            QToolBar QToolButton:checked {
                background-color: #d0e0ff;
                border: 1px solid #aabbcc;
            }
            QStatusBar {
                background-color: #f5f5f5;
                border-top: 1px solid #aabbcc;
                color: #333333;
            }
            QSplitter::handle {
                background-color: #aabbcc;
            }
            QSplitter::handle:horizontal {
                width: 1px;
            }
            QSplitter::handle:vertical {
                height: 1px;
            }
            QProgressBar {
                border: 1px solid #aabbcc;
                border-radius: 3px;
                text-align: center;
                background-color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #2c5aa0;
                width: 10px;
            }
            QTabWidget::pane {
                border: 1px solid #aabbcc;
                border-top: 0px;
                background-color: #ffffff;
                top: -1px;
            }
            QTabWidget::tab-bar {
                left: 0px;
                alignment: left;
            }
            QTabBar::tab {
                background: #f5f5f5;
                border: 1px solid #aabbcc;
                border-bottom: none;
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 60px;
                min-height: 20px;
                color: #555555;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #2c5aa0;
                border-bottom: 2px solid #2c5aa0;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #e8f0ff;
                color: #2c5aa0;
            }
            QTabBar::tab:disabled {
                color: #bbbbbb;
                background: #f0f0f0;
            }
            QTabBar::close-button {
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM4ODg4ODgiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48bGluZSB4MT0iMTgiIHkxPSI2IiB4Mj0iNiIgeTI9IjE4Ij48L2xpbmU+PGxpbmUgeDE9IjYiIHkxPSI2IiB4Mj0iMTgiIHkyPSIxOCI+PC9saW5lPjwvc3ZnPg==);
                margin: 2px;
            }
            QTabBar::close-button:hover {
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMyYzVhYTAiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48bGluZSB4MT0iMTgiIHkxPSI2IiB4Mj0iNiIgeTI9IjE4Ij48L2xpbmU+PGxpbmUgeDE9IjYiIHkxPSI2IiB4Mj0iMTgiIHkyPSIxOCI+PC9saW5lPjwvc3ZnPg==);
            }
            QPushButton {
                background-color: #f8f8f8;
                border: 1px solid #aabbcc;
                border-radius: 3px;
                padding: 4px 12px;
                min-width: 80px;
                min-height: 22px;
                color: #2c5aa0;
            }
            QPushButton:hover {
                background-color: #e8f0ff;
                border: 1px solid #8899bb;
            }
            QPushButton:pressed {
                background-color: #d0e0ff;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                border: 1px solid #aabbcc;
                border-radius: 3px;
                padding: 3px;
                background-color: #ffffff;
                selection-background-color: #d0e0ff;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #2c5aa0;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #aabbcc;
            }
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM1NTU1NTUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI2IDkgMTIgMTUgMTggOSI+PC9wb2x5bGluZT48L3N2Zz4=);
                width: 12px;
                height: 12px;
                margin-right: 4px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #aabbcc;
                selection-background-color: #e8f0ff;
            }
            QTableView {
                border: 1px solid #aabbcc;
                gridline-color: #e0e0e0;
                selection-background-color: #e8f0ff;
                selection-color: #2c5aa0;
            }
            QTableView::item:hover {
                background-color: #f0f8ff;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                border: 1px solid #aabbcc;
                border-left: 0px;
                padding: 3px;
                font-weight: bold;
                color: #333333;
            }
            QScrollBar:vertical {
                border: 1px solid #aabbcc;
                background: #f5f5f5;
                width: 14px;
                margin: 16px 0 16px 0;
            }
            QScrollBar::handle:vertical {
                background: #d0d0d0;
                min-height: 20px;
                border-radius: 3px;
                margin: 2px;
                width: 10px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2c5aa0;
            }
            QScrollBar::add-line:vertical {
                border: 1px solid #aabbcc;
                background: #f5f5f5;
                height: 15px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-radius: 3px;
            }
            QScrollBar::sub-line:vertical {
                border: 1px solid #aabbcc;
                background: #f5f5f5;
                height: 15px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-radius: 3px;
            }
            QScrollBar::up-arrow:vertical {
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM1NTU1NTUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSIxOCAxNSAxMiA5IDYgMTUiPjwvcG9seWxpbmU+PC9zdmc+);
                width: 10px;
                height: 10px;
            }
            QScrollBar::down-arrow:vertical {
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM1NTU1NTUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI2IDkgMTIgMTUgMTggOSI+PC9wb2x5bGluZT48L3N2Zz4=);
                width: 10px;
                height: 10px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: 1px solid #aabbcc;
                background: #f5f5f5;
                height: 14px;
                margin: 0 16px 0 16px;
            }
            QScrollBar::handle:horizontal {
                background: #d0d0d0;
                min-width: 20px;
                border-radius: 3px;
                margin: 2px;
                height: 10px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #2c5aa0;
            }
            QScrollBar::add-line:horizontal {
                border: 1px solid #aabbcc;
                background: #f5f5f5;
                width: 15px;
                subcontrol-position: right;
                subcontrol-origin: margin;
                border-radius: 3px;
            }
            QScrollBar::sub-line:horizontal {
                border: 1px solid #aabbcc;
                background: #f5f5f5;
                width: 15px;
                subcontrol-position: left;
                subcontrol-origin: margin;
                border-radius: 3px;
            }
            QScrollBar::left-arrow:horizontal {
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM1NTU1NTUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSIxNSAxOCA5IDEyIDE1IDYiPjwvcG9seWxpbmU+PC9zdmc+);
                width: 10px;
                height: 10px;
            }
            QScrollBar::right-arrow:horizontal {
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM1NTU1NTUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI5IDE4IDE1IDEyIDkgNiI+PC9wb2x5bGluZT48L3N2Zz4=);
                width: 10px;
                height: 10px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            QGroupBox {
                border: 1px solid #aabbcc;
                border-radius: 3px;
                margin-top: 20px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #2c5aa0;
                font-weight: bold;
            }
            QLabel {
                color: #333333;
            }
            QLabel[title="true"] {
                color: #2c5aa0;
                font-weight: bold;
                font-size: 11pt;
            }
            QCheckBox, QRadioButton {
                color: #333333;
                spacing: 5px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 13px;
                height: 13px;
                border: 1px solid #aabbcc;
                border-radius: 2px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background-color: #2c5aa0;
            }
        """)
        
        # Enable mouse tracking for the main window
        self.setMouseTracking(True)
        
        # Central widget with main layout
        central_widget = QWidget()
        central_widget.setMouseTracking(True)  # Enable mouse tracking for central widget
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitters for panels
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create and configure panels
        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)
        self.bottom_panel = BottomPanel(self)
        self.device_table = DeviceTable(self)
        
        # Configure layout with panels
        self.h_splitter.addWidget(self.left_panel)
        self.h_splitter.addWidget(self.v_splitter)
        self.h_splitter.addWidget(self.right_panel)
        
        self.v_splitter.addWidget(self.device_table)
        self.v_splitter.addWidget(self.bottom_panel)
        
        # Set initial splitter sizes based on config
        ui_config = self.config["ui"]["panels"]
        self.h_splitter.setSizes([
            ui_config["left"]["width"], 
            self.width() - ui_config["left"]["width"] - ui_config["right"]["width"],
            ui_config["right"]["width"]
        ])
        self.v_splitter.setSizes([
            self.height() - ui_config["bottom"]["height"],
            ui_config["bottom"]["height"]
        ])
        
        # Force panel visibility
        self.left_panel.setVisible(True)
        self.right_panel.setVisible(True)
        self.bottom_panel.setVisible(True)
        
        # Add splitter to main layout
        main_layout.addWidget(self.h_splitter)
        
        # Setup status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Add progress bar to status bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.hide()
        self.statusBar.addPermanentWidget(self.progress_bar)
        
        # Update toolbar groups visibility after all initialization is done
        QTimer.singleShot(100, self.update_toolbar_groups_visibility)
        
        self.logger.debug("Main window UI setup complete")
    
    def setup_toolbar(self):
        """Set up the application toolbar with a modern Microsoft Office-style ribbon interface."""
        # Create the toolbar and set its properties
        self.toolbar = QToolBar()
        self.toolbar.setObjectName("ribbonToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        
        # Add toolbar to main window
        self.addToolBar(self.toolbar)
        
        # Create tab widget for the ribbon
        self.toolbar_tabs = QTabWidget()
        self.toolbar_tabs.setObjectName("ribbonTabs")
        
        # Set the tabBar property for styling
        self.toolbar_tabs.tabBar().setProperty("ribbonTabBar", True)
        
        # Apply styling to tabs and toolbar
        style = """
            QToolBar#ribbonToolbar {
                background-color: #f0f0f0;
                border-bottom: 1px solid #aabbcc;
                padding: 0px;
                spacing: 0px;
                min-height: 100px;
                alignment: left;
            }
            
            QTabWidget#ribbonTabs::pane {
                border: none;
                background-color: #f5f5f5;
                padding: 0px;
            }
            
            QTabWidget::tab-bar {
                alignment: left;
                left: 5px;
            }
            
            QTabBar[ribbonTabBar="true"]::tab {
                background-color: #e8e8e8;
                color: #555555;
                border: 1px solid #aabbcc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
                font-weight: normal;
                min-width: 70px;
                min-height: 20px;
            }
            
            QTabBar[ribbonTabBar="true"]::tab:selected {
                background-color: #f5f5f5;
                color: #2c5aa0;
                border-bottom: 2px solid #2c5aa0;
                font-weight: bold;
            }
            
            QTabBar[ribbonTabBar="true"]::tab:hover:!selected {
                background-color: #e8f0ff;
                color: #2c5aa0;
            }
            
            QToolButton {
                min-width: 45px;
                min-height: 45px;
                max-width: 70px;
                max-height: 70px;
                padding: 2px;
                margin: 2px;
                border-radius: 3px;
                border: 1px solid transparent;
                background-color: transparent;
                color: #2c5aa0;
                font-size: 8pt;
                font-weight: bold;
                text-align: center;
            }
            
            QToolButton:hover {
                background-color: #e8f0ff;
                border: 1px solid #aabbcc;
            }
            
            QToolButton:pressed {
                background-color: #d0e0ff;
                border: 1px solid #8899bb;
                padding-top: 4px;
                padding-left: 4px;
                padding-bottom: 0px;
                padding-right: 0px;
                margin-top: 4px;
                margin-left: 4px;
                box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.2);
            }

            QPushButton {
                background-color: #f8f8f8;
                border: 1px solid #aabbcc;
                border-radius: 3px;
                padding: 4px 12px;
                min-width: 80px;
                min-height: 22px;
                color: #2c5aa0;
            }
            
            QPushButton:hover {
                background-color: #e8f0ff;
                border: 1px solid #8899bb;
            }
            
            QPushButton:pressed {
                background-color: #d0e0ff;
                border: 1px solid #5577aa;
                padding-top: 5px;
                padding-left: 13px;
                padding-bottom: 3px;
                padding-right: 11px;
                box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.2);
            }
        """
        self.setStyleSheet(style)
        
        # Add the tab widget to the toolbar
        self.toolbar.addWidget(self.toolbar_tabs)
        
        # Create default tabs
        self.home_tab = QWidget()
        self.view_tab = QWidget()
        self.tools_tab = QWidget()
        self.plugins_tab = QWidget()
        self.help_tab = QWidget()
        
        # Set layouts for tabs with left alignment
        self.home_tab.setLayout(QHBoxLayout())
        self.home_tab.layout().setSpacing(0)
        self.home_tab.layout().setContentsMargins(2, 2, 2, 0)
        self.home_tab.layout().setAlignment(Qt.AlignLeft)
        
        self.view_tab.setLayout(QHBoxLayout())
        self.view_tab.layout().setSpacing(0)
        self.view_tab.layout().setContentsMargins(2, 2, 2, 0)
        self.view_tab.layout().setAlignment(Qt.AlignLeft)
        
        self.tools_tab.setLayout(QHBoxLayout())
        self.tools_tab.layout().setSpacing(0)
        self.tools_tab.layout().setContentsMargins(2, 2, 2, 0)
        self.tools_tab.layout().setAlignment(Qt.AlignLeft)
        
        self.plugins_tab.setLayout(QHBoxLayout())
        self.plugins_tab.layout().setSpacing(0)
        self.plugins_tab.layout().setContentsMargins(2, 2, 2, 0)
        self.plugins_tab.layout().setAlignment(Qt.AlignLeft)
        
        self.help_tab.setLayout(QHBoxLayout())
        self.help_tab.layout().setSpacing(0)
        self.help_tab.layout().setContentsMargins(2, 2, 2, 0)
        self.help_tab.layout().setAlignment(Qt.AlignLeft)
        
        # Add groups to home tab
        self.file_group = self.create_toolbar_group("File", self.home_tab)
        self.add_toolbar_separator(self.home_tab)
        self.edit_group = self.create_toolbar_group("Edit", self.home_tab)
        self.add_toolbar_separator(self.home_tab)
        self.clipboard_group = self.create_toolbar_group("Clipboard", self.home_tab)
        
        # Add Save button to File group
        save_action = QAction("Save", self)
        save_action.setIcon(QIcon.fromTheme("document-save"))
        save_action.setToolTip("Save devices and settings to database")
        save_action.triggered.connect(self.save_workspace_data)
        
        save_button = QToolButton()
        save_button.setDefaultAction(save_action)
        save_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.file_group.layout().addWidget(save_button)
        
        # Add Import/Export buttons
        import_action = QAction("Import", self)
        import_action.setIcon(QIcon.fromTheme("document-open"))
        import_action.setToolTip("Import devices and settings from file")
        import_action.triggered.connect(self.import_workspace_data)
        
        import_button = QToolButton()
        import_button.setDefaultAction(import_action)
        import_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.file_group.layout().addWidget(import_button)
        
        export_action = QAction("Export", self)
        export_action.setIcon(QIcon.fromTheme("document-save-as"))
        export_action.setToolTip("Export devices and settings to file")
        export_action.triggered.connect(self.export_workspace_data)
        
        export_button = QToolButton()
        export_button.setDefaultAction(export_action)
        export_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.file_group.layout().addWidget(export_button)
        
        # Add groups to view tab
        self.display_group = self.create_toolbar_group("Display", self.view_tab)
        self.add_toolbar_separator(self.view_tab)
        self.panel_group = self.create_toolbar_group("Panels", self.view_tab)
        self.add_toolbar_separator(self.view_tab)
        self.zoom_group = self.create_toolbar_group("Zoom", self.view_tab)
        
        # Add groups to tools tab
        self.utilities_group = self.create_toolbar_group("Utilities", self.tools_tab)
        self.add_toolbar_separator(self.tools_tab)
        self.network_group = self.create_toolbar_group("Network", self.tools_tab)
        self.add_toolbar_separator(self.tools_tab)
        self.diagnostics_group = self.create_toolbar_group("Diagnostics", self.tools_tab)
        
        # Add groups to plugins tab
        self.plugins_group = self.create_toolbar_group("Installed Plugins", self.plugins_tab)
        
        # Add groups to help tab
        self.help_group = self.create_toolbar_group("Help & Support", self.help_tab)
        self.add_toolbar_separator(self.help_tab)
        self.about_group = self.create_toolbar_group("About", self.help_tab)
        
        # Add tabs to tab widget
        self.toolbar_tabs.addTab(self.home_tab, "Home")
        self.toolbar_tabs.addTab(self.view_tab, "View")
        self.toolbar_tabs.addTab(self.tools_tab, "Tools")
        self.toolbar_tabs.addTab(self.plugins_tab, "Plugins")
        self.toolbar_tabs.addTab(self.help_tab, "Help")
        
        # Force the toolbar to be visible and select Home tab by default
        self.toolbar.setVisible(True)
        self.toolbar_tabs.setCurrentIndex(0)  # Select Home tab
        
        self.logger.debug("Toolbar setup complete")
    
    def create_toolbar_group(self, title, parent_tab):
        """Create a group within a toolbar tab with a title and layout.
        
        Args:
            title (str): The title for the group
            parent_tab (QWidget): The tab widget to add the group to
            
        Returns:
            QWidget: The group widget
        """
        group = QWidget()
        group.setProperty("ribbonGroup", True)
        group.setLayout(QVBoxLayout())
        group.layout().setSpacing(2)
        group.layout().setContentsMargins(3, 2, 3, 2)
        
        # Add explicit styling to ensure it's applied
        group.setStyleSheet("""
            QWidget {
                background-color: #f8f8f8;
                border: 1px solid #aabbcc;
                border-radius: 4px;
                margin: 3px;
                padding: 4px;
                min-width: 100px;
            }
        """)
        
        title_label = QLabel(title)
        title_label.setProperty("ribbonGroupTitle", True)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #2c5aa0;
                font-size: 8pt;
                padding: 2px 3px;
                margin-top: 2px;
                margin-bottom: 2px;
                font-weight: bold;
                text-align: center;
                background-color: #e8f0ff;
                border-radius: 2px;
                border-bottom: 1px solid #aabbcc;
            }
        """)
        
        content_widget = QWidget()
        content_widget.setLayout(QHBoxLayout())
        content_widget.layout().setSpacing(2)
        content_widget.layout().setContentsMargins(1, 1, 1, 1)
        
        group.layout().addWidget(title_label)
        group.layout().addWidget(content_widget)
        
        # Store the container widget and title for references
        content_widget.container = group
        content_widget.title = title
        
        # Add method to check if empty and hide accordingly
        def check_empty():
            is_empty = content_widget.layout().count() == 0
            group.setVisible(not is_empty)
            return is_empty
        
        content_widget.check_empty = check_empty
        
        # Add method to add widget that automatically updates visibility
        original_add_widget = content_widget.layout().addWidget
        def add_widget_with_visibility_update(widget):
            original_add_widget(widget)
            group.setVisible(True)
        content_widget.layout().addWidget = add_widget_with_visibility_update
        
        # Initial visibility check
        check_empty()
        
        parent_tab.layout().addWidget(group)
        return content_widget
    
    def add_toolbar_separator(self, parent_tab):
        """Add a vertical separator to a toolbar tab."""
        separator = QWidget()
        separator.setProperty("ribbonSeparator", True)
        separator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        separator.setStyleSheet("""
            QWidget {
                min-width: 6px;
                max-width: 6px;
                margin-left: 2px;
                margin-right: 2px;
                background-color: transparent;
                border-right: 1px solid #aabbcc;
            }
        """)
        parent_tab.layout().addWidget(separator)
    
    def transfer_menu_actions_to_toolbar(self):
        """Transfer menu actions to the ribbon toolbar tabs based on their category."""
        if not hasattr(self, 'menuBar'):
            self.logger.debug("Menu bar not available for transfer")
            return
        
        # Map menu names to ribbon tabs
        menu_to_tab = {
            'File': {'tab': self.home_tab, 'group': self.file_group},
            'Edit': {'tab': self.home_tab, 'group': self.edit_group},
            'View': {'tab': self.view_tab, 'group': self.display_group},
            'Tools': {'tab': self.tools_tab, 'group': self.utilities_group},
            'Plugins': {'tab': self.plugins_tab, 'group': self.plugins_group},
            'Help': {'tab': self.help_tab, 'group': self.help_group},
            'Diagnostics': {'tab': self.tools_tab, 'group': self.diagnostics_group},
            'Network': {'tab': self.plugins_tab, 'group': self.network_group},
            'Security': {'tab': self.tools_tab, 'group': self.create_toolbar_group("Security", self.tools_tab)}
        }
        
        # Default icon themes for different menus
        default_icons = {
            'File': 'document-new',
            'Edit': 'edit',
            'View': 'view-preview',
            'Tools': 'tools',
            'Plugins': 'plugin',
            'Help': 'help-contents',
            'Diagnostics': 'debug',
            'Network': 'network',
            'Security': 'security'
        }
        
        # Process each menu in the menu bar
        for menu_name, menu in self.menus.items():
            if menu_name in menu_to_tab:
                # Get corresponding tab and group
                target = menu_to_tab[menu_name]
                
                # Add all actions from this menu to the target group
                for action in menu.actions():
                    if not action.isSeparator():
                        # Create button for the action
                        from PySide6.QtWidgets import QToolButton
                        button = QToolButton()
                        button.setDefaultAction(action)
                        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                        
                        # If action doesn't have an icon, set a default one
                        if action.icon().isNull():
                            action.setIcon(QIcon.fromTheme(default_icons.get(menu_name, 'document')))
                        
                        # Add the button to the group
                        target['group'].layout().addWidget(button)
        
        self.logger.debug("Menu actions transferred to ribbon toolbar")

    def add_toolbar_widget(self, widget, tab_name="Home", group_name=None):
        """Add a widget or action to the toolbar.
        
        Args:
            widget (QWidget or QAction): The widget or action to add to the toolbar.
            tab_name (str): The name of the tab to add the widget to.
            group_name (str, optional): The name of the group to add the widget to.
                                     If not provided, will add to the first group in the tab.
        
        Returns:
            bool: True if the widget was added successfully, False otherwise.
        """
        # Make sure the toolbar is visible
        self.toolbar.setVisible(True)
        
        # Find the requested tab
        tab = None
        for i in range(self.toolbar_tabs.count()):
            if self.toolbar_tabs.tabText(i) == tab_name:
                tab = self.toolbar_tabs.widget(i)
                break
        
        # If tab not found, create it
        if not tab:
            tab = QWidget()
            tab.setLayout(QHBoxLayout())
            tab.layout().setSpacing(2)
            tab.layout().setContentsMargins(5, 5, 5, 5)
            self.toolbar_tabs.addTab(tab, tab_name)
        
        # If group specified, find or create it
        if group_name:
            group = None
            
            # Check if group already exists
            for i in range(tab.layout().count()):
                item = tab.layout().itemAt(i).widget()
                if item and item.property("ribbonGroup"):
                    title_label = item.layout().itemAt(0).widget()
                    if title_label and title_label.text() == group_name:
                        # Found matching group, get content widget
                        group = item.layout().itemAt(1).widget()
                        break
            
            # If group not found, create it
            if not group:
                group_container = QWidget()
                group_container.setProperty("ribbonGroup", True)
                group_container.setLayout(QVBoxLayout())
                group_container.layout().setSpacing(2)
                group_container.layout().setContentsMargins(5, 2, 5, 2)
                
                title_label = QLabel(group_name)
                title_label.setProperty("ribbonGroupTitle", True)
                title_label.setAlignment(Qt.AlignCenter)
                
                group = QWidget()
                group.setLayout(QHBoxLayout())
                group.layout().setSpacing(2)
                group.layout().setContentsMargins(0, 0, 0, 0)
                
                group_container.layout().addWidget(title_label)
                group_container.layout().addWidget(group)
                
                tab.layout().addWidget(group_container)
        else:
            # Use first group in tab if available
            if tab.layout().count() > 0:
                item = tab.layout().itemAt(0).widget()
                if item and item.property("ribbonGroup"):
                    group = item.layout().itemAt(1).widget()
                else:
                    # Create a default group
                    group = self.create_toolbar_group("General", tab)
            else:
                # Create a default group
                group = self.create_toolbar_group("General", tab)
        
        # Add the widget/action to the group
        if isinstance(widget, QAction):
            # Create a tool button for the action
            from PySide6.QtWidgets import QToolButton
            button = QToolButton()
            button.setDefaultAction(widget)
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            # Add to the group
            group.layout().addWidget(button)
        else:
            # It's a regular widget, just add it
            group.layout().addWidget(widget)
        
        # Switch to the tab where we added the widget
        for i in range(self.toolbar_tabs.count()):
            if self.toolbar_tabs.widget(i) == tab:
                self.toolbar_tabs.setCurrentIndex(i)
                break
        
        return True
    
    def toggle_toolbar(self, checked):
        """Toggle toolbar visibility."""
        self.toolbar.setVisible(checked)
        self.config["ui"]["toolbar"]["visible"] = checked
    
    def toggle_toolbar_pin(self, checked):
        """Toggle toolbar pin state."""
        self.toolbar.setMovable(not checked)
        self.toolbar.setFloatable(not checked)
        self.config["ui"]["toolbar"]["pinned"] = checked
    
    def _on_toolbar_visibility_changed(self, visible):
        """Handle toolbar visibility changes."""
        try:
            self.toolbar_visibility_action.setChecked(visible)
            if "ui" not in self.config:
                self.config["ui"] = {}
            if "toolbar" not in self.config["ui"]:
                self.config["ui"]["toolbar"] = {"visible": True, "pinned": False, "position": "top", "categories": {}}
            self.config["ui"]["toolbar"]["visible"] = visible
            self.logger.debug(f"Toolbar visibility changed to {visible}")
        except Exception as e:
            self.logger.error(f"Error updating toolbar visibility: {str(e)}")
    
    def toggle_left_panel(self, checked):
        """Toggle left panel visibility."""
        self.left_panel.setVisible(checked)
        self.config["ui"]["panels"]["left"]["visible"] = checked
    
    def toggle_right_panel(self, checked):
        """Toggle right panel visibility."""
        self.right_panel.setVisible(checked)
        self.config["ui"]["panels"]["right"]["visible"] = checked
    
    def toggle_bottom_panel(self, checked):
        """Toggle bottom panel visibility."""
        self.bottom_panel.setVisible(checked)
        self.config["ui"]["panels"]["bottom"]["visible"] = checked
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_config()
        event.accept()
    
    def save_config(self):
        """Save application configuration."""
        # Update config with current panel sizes
        left_width = self.left_panel.width()
        right_width = self.right_panel.width()
        bottom_height = self.bottom_panel.height()
        
        self.config["ui"]["panels"]["left"]["width"] = left_width
        self.config["ui"]["panels"]["right"]["width"] = right_width
        self.config["ui"]["panels"]["bottom"]["height"] = bottom_height
        
        # Save to file
        config_path = os.path.join('config', 'settings.json')
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def event(self, event):
        """Handle Qt events for the main window."""
        if event.type() == QEvent.Type.WindowActivate:
            self.logger.debug("Window activated")
        elif event.type() == QEvent.Type.WindowDeactivate:
            self.logger.debug("Window deactivated")
        return super().event(event)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        self.logger.debug(f"Mouse press event at {event.pos()}")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        self.logger.debug(f"Mouse release event at {event.pos()}")
        super().mouseReleaseEvent(event)

    def show_progress(self, show=True):
        """Show or hide the progress bar."""
        self.progress_bar.setVisible(show)
        if not show:
            self.progress_bar.setValue(0)
    
    def update_progress(self, value, maximum=None):
        """Update the progress bar value and optionally its maximum."""
        if maximum is not None:
            self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)

    def register_panel(self, panel, location, name=None):
        """Register a panel in the specified location.
        
        Args:
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
            if panel.thread() != self.thread():
                self.logger.warning(f"Panel {name} is in a different thread. This may cause UI issues.")
            
            # Make sure panel is parented correctly before attempting to add to UI
            panel.setParent(None)  # Remove any existing parent
            
            # Register panel based on location
            if location.lower() == "left":
                self.left_panel.add_plugin_panel(panel, name)
                self.logger.info(f"Registered left panel: {name}")
                return True
            elif location.lower() == "right":
                self.right_panel.add_plugin_panel(panel, name)
                self.logger.info(f"Registered right panel: {name}")
                return True
            elif location.lower() == "bottom":
                self.bottom_panel.add_plugin_panel(panel, name)
                self.logger.info(f"Registered bottom panel: {name}")
                return True
            else:
                self.logger.error(f"Invalid panel location: {location}")
                return False
        except Exception as e:
            self.logger.error(f"Error registering panel: {str(e)}", exc_info=True)
            return False
    
    def remove_panel(self, panel):
        """Remove a panel from the UI.
        
        Args:
            panel: QWidget - The panel to remove
            
        Returns:
            bool - True if removal was successful
        """
        try:
            # Get panel name and plugin ID
            name = panel.objectName()
            plugin_id = panel.property("plugin_id")
            
            # Check if panel is in left panel
            if self.left_panel.has_plugin_panel(panel):
                self.left_panel.remove_plugin_panel(panel)
                self.logger.info(f"Removed left panel: {name} from plugin {plugin_id}")
                return True
                
            # Check if panel is in right panel
            if self.right_panel.has_plugin_panel(panel):
                self.right_panel.remove_plugin_panel(panel)
                self.logger.info(f"Removed right panel: {name} from plugin {plugin_id}")
                return True
                
            # Check if panel is in bottom panel
            if self.bottom_panel.has_plugin_panel(panel):
                self.bottom_panel.remove_plugin_panel(panel)
                self.logger.info(f"Removed bottom panel: {name} from plugin {plugin_id}")
                return True
                
            self.logger.warning(f"Panel {name} not found in any location")
            return False
        except Exception as e:
            self.logger.error(f"Error removing panel: {str(e)}", exc_info=True)
            return False

    def refresh_menus(self):
        """Refresh plugin menus."""
        if hasattr(self, 'plugin_manager'):
            self.plugin_manager.refresh_menus()

    def show_error_dialog(self, title, message):
        """Show an error dialog with the specified title and message."""
        QMessageBox.critical(self, title, message)
        
    def customize_table_columns(self):
        """Show dialog for customizing device table columns."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
            QPushButton, QLabel, QCheckBox, QWidget, QSpacerItem, QSizePolicy
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Customize Columns")
        dialog.resize(500, 400)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Explanation label
        label = QLabel("Select columns to display in the device table:")
        layout.addWidget(label)
        
        # Available columns
        all_columns = [
            "ip", "hostname", "mac", "vendor", "scan_method", 
            "ports", "last_seen", "first_seen", "status", "alias"
        ]
        
        # Add metadata columns from devices
        for device in self.device_table.devices:
            if "metadata" in device:
                for key in device["metadata"]:
                    if key not in all_columns and key != "tags":
                        all_columns.append(key)
        
        # Currently selected columns
        current_columns = self.config["ui"]["table"]["columns"]
        
        # Create list widget for column selection with better styling
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #d0dbe8;
                border-radius: 3px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f4f8;
            }
            QListWidget::item:hover {
                background-color: #f5f9ff;
            }
            QListWidget::item:selected {
                background-color: #e8f0ff;
                color: #2c5aa0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #d0dbe8;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:unchecked:hover {
                border-color: #2c5aa0;
            }
            QCheckBox::indicator:checked {
                background-color: #2c5aa0;
                border-color: #2c5aa0;
                image: url(core/ui/icons/check.png);
            }
        """)
        
        for column in all_columns:
            item = QListWidgetItem(column)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if column in current_columns:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        # Quick selection buttons
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f4f8;
                border: 1px solid #d0dbe8;
                border-radius: 3px;
                padding: 6px 12px;
                color: #2c5aa0;
            }
            QPushButton:hover {
                background-color: #e8f0ff;
                border-color: #2c5aa0;
            }
            QPushButton:pressed {
                background-color: #d0e0ff;
                padding-top: 7px;
                padding-bottom: 5px;
                padding-left: 13px;
                padding-right: 11px;
                box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.125);
            }
        """)
        select_all_btn.clicked.connect(lambda: [list_widget.item(i).setCheckState(Qt.CheckState.Checked) for i in range(list_widget.count())])
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f4f8;
                border: 1px solid #d0dbe8;
                border-radius: 3px;
                padding: 6px 12px;
                color: #2c5aa0;
            }
            QPushButton:hover {
                background-color: #e8f0ff;
                border-color: #2c5aa0;
            }
            QPushButton:pressed {
                background-color: #d0e0ff;
                padding-top: 7px;
                padding-bottom: 5px;
                padding-left: 13px;
                padding-right: 11px;
                box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.125);
            }
        """)
        deselect_all_btn.clicked.connect(lambda: [list_widget.item(i).setCheckState(Qt.CheckState.Unchecked) for i in range(list_widget.count())])
        
        reset_default_btn = QPushButton("Reset to Default")
        reset_default_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f4f8;
                border: 1px solid #d0dbe8;
                border-radius: 3px;
                padding: 6px 12px;
                color: #2c5aa0;
            }
            QPushButton:hover {
                background-color: #e8f0ff;
                border-color: #2c5aa0;
            }
            QPushButton:pressed {
                background-color: #d0e0ff;
                padding-top: 7px;
                padding-bottom: 5px;
                padding-left: 13px;
                padding-right: 11px;
                box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.125);
            }
        """)
        
        # Define default columns
        default_columns = ["ip", "hostname", "mac", "vendor", "ports", "status"]
        
        def reset_to_default():
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.text() in default_columns:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                    
        reset_default_btn.clicked.connect(reset_to_default)
        
        selection_layout.addWidget(select_all_btn)
        selection_layout.addWidget(deselect_all_btn)
        selection_layout.addWidget(reset_default_btn)
        
        layout.addLayout(selection_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Add spacer to push buttons to the right
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        button_layout.addItem(spacer)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f4f8;
                border: 1px solid #d0dbe8;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: bold;
                color: #2c5aa0;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #e8f0ff;
                border-color: #2c5aa0;
            }
            QPushButton:pressed {
                background-color: #d0e0ff;
                padding-top: 7px;
                padding-bottom: 5px;
                padding-left: 13px;
                padding-right: 11px;
                box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.125);
            }
        """)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #2c5aa0;
                border: 1px solid #1a4580;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: bold;
                color: white;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #3a6ab0;
                border-color: #2a5590;
            }
            QPushButton:pressed {
                background-color: #1a4580;
                padding-top: 7px;
                padding-bottom: 5px;
                padding-left: 13px;
                padding-right: 11px;
                box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.2);
            }
        """)
        apply_button.clicked.connect(dialog.accept)
        button_layout.addWidget(apply_button)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get selected columns
            selected_columns = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    selected_columns.append(item.text())
            
            # Make sure IP column is always included (required for identification)
            if "ip" not in selected_columns:
                selected_columns.insert(0, "ip")
                self.statusBar.showMessage("IP column is required and was automatically included", 3000)
            
            # Update config
            self.config["ui"]["table"]["columns"] = selected_columns
            
            # Save config
            self.save_config()
            
            # Update the statusbar to give visual feedback
            self.statusBar.showMessage("Table columns updated", 3000)
            
            # Store current device data
            devices = self.device_table.devices.copy()
            
            # Refresh table columns
            self.device_table.setup_columns()
            
            # Re-add all devices to update the table
            self.device_table.setRowCount(0)
            for device in devices:
                self.device_table.add_device(device)

    def manage_device_aliases(self):
        """Show dialog for managing device aliases."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
            QPushButton, QLabel, QLineEdit, QHeaderView, QMessageBox
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Device Aliases")
        dialog.resize(600, 400)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Explanation label
        label = QLabel("Set custom aliases for devices on your network:")
        layout.addWidget(label)
        
        # Create table for aliases
        alias_table = QTableWidget()
        alias_table.setColumnCount(3)
        alias_table.setHorizontalHeaderLabels(["IP Address", "Hostname", "Alias"])
        
        # Set column stretching
        header = alias_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Populate table with devices
        devices = self.device_table.devices
        alias_table.setRowCount(len(devices))
        
        for row, device in enumerate(devices):
            # IP Address
            ip_item = QTableWidgetItem(device.get("ip", "N/A"))
            ip_item.setFlags(ip_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            alias_table.setItem(row, 0, ip_item)
            
            # Hostname
            hostname_item = QTableWidgetItem(device.get("hostname", "Unknown"))
            hostname_item.setFlags(hostname_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            alias_table.setItem(row, 1, hostname_item)
            
            # Alias (editable)
            alias_item = QTableWidgetItem(device.get("alias", ""))
            alias_item.setFlags(alias_item.flags() | Qt.ItemFlag.ItemIsEditable)
            alias_table.setItem(row, 2, alias_item)
        
        layout.addWidget(alias_table)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Add spacer to push buttons to the right
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        button_layout.addItem(spacer)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(dialog.accept)
        button_layout.addWidget(apply_button)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            # Update device aliases
            for row in range(alias_table.rowCount()):
                ip = alias_table.item(row, 0).text()
                alias = alias_table.item(row, 2).text()
                
                # Find device in device list
                for device in self.device_table.devices:
                    if device.get("ip") == ip:
                        # Set alias in device data
                        device["alias"] = alias
                        
                        # Add alias to metadata if not already there
                        if "metadata" not in device:
                            device["metadata"] = {}
                        device["metadata"]["alias"] = alias
                        
                        # Save to database if available
                        if hasattr(self, 'database_manager') and self.database_manager:
                            self.database_manager.save_device(device)
            
            # Refresh device table
            self.device_table.update_data(self.device_table.devices)
            
            # Make sure 'alias' column is available
            if "alias" not in self.config["ui"]["table"]["columns"]:
                self.customize_table_columns()

    def setup_menus(self):
        """Setup the main menu bar and then hide it, using ribbon only."""
        # Set up main menu using the menu component
        from core.ui.menu.main_menu import setup_main_menu
        setup_main_menu(self)
        
        # Transfer all menu actions to the ribbon before hiding the menu bar
        self.transfer_menu_actions_to_toolbar()
        
        # Hide the menu bar since we're using the ribbon exclusively
        self.menuBar().setVisible(False)
        
        # Ensure all menus have proper mouse tracking and visibility settings
        for menu_name, menu in self.menus.items():
            menu.setMouseTracking(True)
            menu.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        self.logger.debug("Menu setup complete with ribbon-only interface") 

    def update_toolbar_groups_visibility(self):
        """Check all toolbar groups and hide empty ones."""
        # Process all tabs
        for tab_index in range(self.toolbar_tabs.count()):
            tab = self.toolbar_tabs.widget(tab_index)
            empty_tabs = True
            
            # Check each group in the tab
            for i in range(tab.layout().count()):
                widget = tab.layout().itemAt(i).widget()
                if widget and widget.property("ribbonGroup"):
                    # Get the content widget which has our check_empty method
                    content_widget = widget.layout().itemAt(1).widget()
                    if hasattr(content_widget, 'check_empty'):
                        is_empty = content_widget.check_empty()
                        if not is_empty:
                            empty_tabs = False
                elif widget and widget.property("ribbonSeparator"):
                    # Handle separators: hide them if the preceding or following group is hidden
                    prev_visible = False
                    next_visible = False
                    
                    # Check previous widget
                    if i > 0:
                        prev_widget = tab.layout().itemAt(i-1).widget()
                        if prev_widget and prev_widget.property("ribbonGroup"):
                            prev_visible = prev_widget.isVisible()
                    
                    # Check next widget
                    if i < tab.layout().count() - 1:
                        next_widget = tab.layout().itemAt(i+1).widget()
                        if next_widget and next_widget.property("ribbonGroup"):
                            next_visible = next_widget.isVisible()
                    
                    # Hide separator if either adjacent group is hidden
                    widget.setVisible(prev_visible and next_visible)
            
            # Hide entire tab if all groups are empty (optional)
            # Uncomment to enable this behavior
            # self.toolbar_tabs.setTabVisible(tab_index, not empty_tabs) 

    def save_workspace_data(self):
        """Save current devices and settings to the database."""
        try:
            # Save the current devices if we have a device table
            if hasattr(self, 'device_table') and self.device_table:
                devices = self.device_table.get_all_devices()
                saved_count = 0
                
                if hasattr(self, 'database_manager') and self.database_manager:
                    for device in devices:
                        # Add/update the device in the database
                        if self.database_manager.save_device(device):
                            saved_count += 1
                    
                    self.statusBar.showMessage(f"Saved {saved_count} devices to database", 5000)
                    self.logger.info(f"Saved {saved_count} devices to database")
                    
                    # Save application settings
                    if hasattr(self, 'config') and self.config:
                        self.database_manager.store_plugin_data('core', 'app_settings', self.config)
                        self.logger.info("Saved application settings to database")
                else:
                    self.logger.warning("Database manager not available, cannot save devices")
                    self.statusBar.showMessage("Database not available, cannot save devices", 5000)
            else:
                self.logger.warning("Device table not available, cannot save devices")
        except Exception as e:
            self.logger.error(f"Error saving workspace data: {str(e)}")
            self.statusBar.showMessage(f"Error saving data: {str(e)}", 5000)

    def export_workspace_data(self):
        """Export devices and settings to a file."""
        try:
            from PySide6.QtWidgets import QFileDialog
            import json
            import datetime
            import platform
            import os
            
            # Ask user for export file location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Workspace Data",
                "",
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if not file_path:
                return
                
            # Add .json extension if not present
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
                
            # Prepare export data structure with complete information
            export_data = {
                "export_version": "2.0",
                "timestamp": datetime.datetime.now().isoformat(),
                "system_info": {
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "hostname": platform.node()
                },
                "application": {
                    "name": "netWORKS",
                    "version": self.plugin_manager.get_app_version() if hasattr(self.plugin_manager, 'get_app_version') else "Unknown",
                },
                "settings": self.config if hasattr(self, 'config') else {},
                "devices": [],
                "device_groups": {},
                "plugins": {}
            }
            
            # Get device data if available
            if hasattr(self, 'device_table') and self.device_table:
                # Get complete device information
                devices = self.device_table.get_all_devices()
                
                # For each device, make sure we have ALL available data
                for device in devices:
                    # Make sure we get any plugin data attached to the device
                    if hasattr(self, 'plugin_manager') and self.plugin_manager:
                        for plugin_id, plugin_info in self.plugin_manager.plugins.items():
                            if plugin_info.get("enabled", False) and plugin_info.get("instance"):
                                # Check if plugin has a method to get device data
                                plugin_api = self.plugin_manager.plugin_apis.get(plugin_id)
                                if plugin_api and hasattr(plugin_api, 'get_device_data'):
                                    try:
                                        plugin_data = plugin_api.get_device_data(device['id'])
                                        if plugin_data:
                                            # Add plugin data to device metadata
                                            if 'plugin_data' not in device:
                                                device['plugin_data'] = {}
                                            device['plugin_data'][plugin_id] = plugin_data
                                    except Exception as e:
                                        self.logger.warning(f"Error getting device data from plugin {plugin_id}: {str(e)}")
                
                export_data["devices"] = devices
                
                # Extract device groups
                if hasattr(self.device_table, 'device_groups'):
                    export_data["device_groups"] = self.device_table.device_groups
            
            # Add information about enabled plugins and their versions
            if hasattr(self, 'plugin_manager') and self.plugin_manager:
                for plugin_id, plugin_info in self.plugin_manager.plugins.items():
                    export_data["plugins"][plugin_id] = {
                        "enabled": plugin_info.get("enabled", False),
                        "version": plugin_info.get("version", "Unknown"),
                        "name": plugin_info.get("name", plugin_id),
                        "description": plugin_info.get("description", ""),
                        "author": plugin_info.get("author", ""),
                        "config": {}
                    }
                    
                    # Try to get plugin configuration if available
                    plugin_api = self.plugin_manager.plugin_apis.get(plugin_id)
                    if plugin_api and hasattr(plugin_api, 'get_config'):
                        try:
                            plugin_config = plugin_api.get_config()
                            if plugin_config:
                                export_data["plugins"][plugin_id]["config"] = plugin_config
                        except Exception as e:
                            self.logger.warning(f"Error getting config from plugin {plugin_id}: {str(e)}")
                    
                    # Get plugin data from database
                    if hasattr(self, 'database_manager') and self.database_manager:
                        try:
                            plugin_data = self.database_manager.get_plugin_data(plugin_id)
                            if plugin_data:
                                export_data["plugins"][plugin_id]["stored_data"] = plugin_data
                        except Exception as e:
                            self.logger.warning(f"Error getting stored data for plugin {plugin_id}: {str(e)}")
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            device_count = len(export_data["devices"])
            plugin_count = len(export_data["plugins"])
            self.statusBar.showMessage(
                f"Exported {device_count} devices with complete data, {plugin_count} plugins, and all settings to {file_path}", 
                5000
            )
            self.logger.info(f"Exported {device_count} devices, {plugin_count} plugins, and settings to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting workspace data: {str(e)}")
            self.statusBar.showMessage(f"Error exporting data: {str(e)}", 5000)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Error", f"Failed to export data: {str(e)}")

    def import_workspace_data(self):
        """Import devices and settings from a file."""
        try:
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            import json
            
            # Ask user for import file
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Workspace Data",
                "",
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if not file_path:
                return
                
            # Read file
            with open(file_path, 'r') as f:
                import_data = json.load(f)
                
            # Validate import data
            if ("version" not in import_data and "export_version" not in import_data) or "devices" not in import_data:
                QMessageBox.warning(self, "Invalid File", "The selected file is not a valid workspace export.")
                return
                
            # Show import information to user
            export_version = import_data.get("export_version", import_data.get("version", "Unknown"))
            device_count = len(import_data.get("devices", []))
            plugin_count = len(import_data.get("plugins", {}))
            
            info_text = (
                f"File Information:\n"
                f"Export Version: {export_version}\n"
                f"Devices: {device_count}\n"
                f"Plugins: {plugin_count}\n"
                f"Created: {import_data.get('timestamp', 'Unknown')}\n\n"
                f"What would you like to import?"
            )
            
            # Ask user what to import
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Import Options")
            dialog.resize(400, 300)
            layout = QVBoxLayout(dialog)
            
            # Add info text
            info_label = QLabel(info_text)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # Create checkboxes for import options
            import_devices = QCheckBox("Import Devices with All Metadata")
            import_devices.setChecked(True)
            layout.addWidget(import_devices)
            
            import_groups = QCheckBox("Import Device Groups")
            import_groups.setChecked(True)
            layout.addWidget(import_groups)
            
            import_settings = QCheckBox("Import Application Settings")
            import_settings.setChecked(True)
            layout.addWidget(import_settings)
            
            import_plugins = QCheckBox("Import Plugin Configurations")
            import_plugins.setChecked(plugin_count > 0)
            import_plugins.setEnabled(plugin_count > 0)
            layout.addWidget(import_plugins)
            
            # Add buttons
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            # Show dialog
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
                
            # Process import based on user selections
            device_count = 0
            
            # Import devices if selected
            if import_devices.isChecked() and "devices" in import_data:
                # Clear existing devices if needed
                result = QMessageBox.question(
                    self,
                    "Replace Devices",
                    "Do you want to replace all existing devices or merge with the current ones?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if result == QMessageBox.StandardButton.Yes:
                    # Clear existing devices
                    if hasattr(self, 'device_table') and self.device_table:
                        self.device_table.setRowCount(0)
                        self.device_table.devices = []
                
                # Import devices with complete metadata
                for device in import_data["devices"]:
                    if hasattr(self, 'device_table') and self.device_table:
                        # Check if device already exists (by ID or IP)
                        device_id = device.get('id')
                        device_ip = device.get('ip')
                        existing_device = None
                        
                        # Look for existing device
                        for existing in self.device_table.devices:
                            if existing.get('id') == device_id or existing.get('ip') == device_ip:
                                existing_device = existing
                                break
                        
                        if existing_device and result == QMessageBox.StandardButton.No:
                            # Merge device data
                            for key, value in device.items():
                                # Skip basic identifiers
                                if key not in ['id', 'ip']:
                                    existing_device[key] = value
                            
                            # Update device in table
                            row = self.device_table.find_device_row(device_ip)
                            if row is not None:
                                self.device_table.update_device_row(row, existing_device)
                        else:
                            # Add as new device
                            self.device_table.add_device(device)
                        
                        device_count += 1
                
            # Import device groups if selected
            if import_groups.isChecked() and "device_groups" in import_data:
                if hasattr(self, 'device_table') and self.device_table:
                    # Ask if we should replace or merge
                    if hasattr(self.device_table, 'device_groups') and self.device_table.device_groups:
                        result = QMessageBox.question(
                            self,
                            "Replace Device Groups",
                            "Do you want to replace all existing device groups or merge with the current ones?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.No
                        )
                        
                        if result == QMessageBox.StandardButton.Yes:
                            # Replace groups
                            self.device_table.device_groups = import_data["device_groups"]
                        else:
                            # Merge groups
                            for group_name, device_ids in import_data["device_groups"].items():
                                if group_name in self.device_table.device_groups:
                                    # Merge device IDs
                                    for device_id in device_ids:
                                        if device_id not in self.device_table.device_groups[group_name]:
                                            self.device_table.device_groups[group_name].append(device_id)
                                else:
                                    # Add new group
                                    self.device_table.device_groups[group_name] = device_ids
                    else:
                        # No existing groups, just set directly
                        self.device_table.device_groups = import_data["device_groups"]
            
            # Import settings if selected
            if import_settings.isChecked() and "settings" in import_data:
                # Ask if user wants to replace all settings
                result = QMessageBox.question(
                    self,
                    "Replace Settings",
                    "Do you want to replace all existing settings?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if result == QMessageBox.StandardButton.Yes:
                    # Replace all settings
                    self.config = import_data["settings"]
                    self.save_config()
                    
                    # Apply column settings to table
                    if hasattr(self, 'device_table') and self.device_table:
                        self.device_table.setup_columns()
            
            # Import plugin configurations if selected
            if import_plugins.isChecked() and "plugins" in import_data:
                plugin_configs_imported = 0
                
                if hasattr(self, 'plugin_manager') and self.plugin_manager:
                    for plugin_id, plugin_data in import_data["plugins"].items():
                        # Check if plugin exists
                        if plugin_id in self.plugin_manager.plugins:
                            plugin_info = self.plugin_manager.plugins[plugin_id]
                            plugin_api = self.plugin_manager.plugin_apis.get(plugin_id)
                            
                            # Set plugin enabled state if possible
                            if plugin_api and "enabled" in plugin_data:
                                try:
                                    if plugin_data["enabled"]:
                                        self.plugin_manager.enable_plugin(plugin_id)
                                    else:
                                        self.plugin_manager.disable_plugin(plugin_id)
                                except Exception as e:
                                    self.logger.warning(f"Could not set enabled state for plugin {plugin_id}: {str(e)}")
                            
                            # Import plugin configuration if possible
                            if plugin_api and "config" in plugin_data and hasattr(plugin_api, 'set_config'):
                                try:
                                    plugin_api.set_config(plugin_data["config"])
                                    plugin_configs_imported += 1
                                except Exception as e:
                                    self.logger.warning(f"Could not import config for plugin {plugin_id}: {str(e)}")
                            
                            # Import plugin stored data if available
                            if "stored_data" in plugin_data and hasattr(self, 'database_manager') and self.database_manager:
                                try:
                                    for key, value in plugin_data["stored_data"].items():
                                        self.database_manager.store_plugin_data(plugin_id, key, value)
                                    plugin_configs_imported += 1
                                except Exception as e:
                                    self.logger.warning(f"Could not import stored data for plugin {plugin_id}: {str(e)}")
                
                self.logger.info(f"Imported configuration for {plugin_configs_imported} plugins")
            
            # Save imported data to database if available
            if hasattr(self, 'database_manager') and self.database_manager:
                # Save devices if imported
                if import_devices.isChecked():
                    for device in import_data["devices"]:
                        self.database_manager.save_device(device)
                
                # Save settings if imported
                if import_settings.isChecked():
                    self.database_manager.store_plugin_data('core', 'app_settings', self.config)
            
            # Update status
            self.statusBar.showMessage(f"Imported {device_count} devices with complete metadata from {file_path}", 5000)
            self.logger.info(f"Imported {device_count} devices with complete data from {file_path}")
            
            # Force refresh of the UI
            if hasattr(self, 'device_table') and self.device_table:
                self.device_table.update_data(self.device_table.devices)
            
        except Exception as e:
            self.logger.error(f"Error importing workspace data: {str(e)}")
            self.statusBar.showMessage(f"Error importing data: {str(e)}", 5000)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Import Error", f"Failed to import data: {str(e)}")

    def setup_menu(self):
        """Set up the application menu bar."""
        # ... existing code ...
        
        # Add action to the File menu
        save_workspace_action = QAction("Save Workspace", self)
        save_workspace_action.setIcon(QIcon.fromTheme("document-save"))
        save_workspace_action.setShortcut("Ctrl+S")
        save_workspace_action.setStatusTip("Save devices and settings to database")
        save_workspace_action.triggered.connect(self.save_workspace_data)
        
        # Import/Export actions
        import_workspace_action = QAction("Import Workspace...", self)
        import_workspace_action.setIcon(QIcon.fromTheme("document-open"))
        import_workspace_action.setShortcut("Ctrl+O")
        import_workspace_action.setStatusTip("Import devices and settings from file")
        import_workspace_action.triggered.connect(self.import_workspace_data)
        
        export_workspace_action = QAction("Export Workspace...", self)
        export_workspace_action.setIcon(QIcon.fromTheme("document-save-as"))
        export_workspace_action.setShortcut("Ctrl+E")
        export_workspace_action.setStatusTip("Export devices and settings to file")
        export_workspace_action.triggered.connect(self.export_workspace_data)
        
        # Add to File menu if it exists
        if 'File' in self.menus:
            self.menus['File'].addAction(save_workspace_action)
            self.menus['File'].addSeparator()
            self.menus['File'].addAction(import_workspace_action)
            self.menus['File'].addAction(export_workspace_action)
            self.menus['File'].addSeparator()
        
        # Also add it to the toolbar
        if hasattr(self, 'file_group'):
            save_button = QToolButton()
            save_button.setDefaultAction(save_workspace_action)
            save_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            self.file_group.layout().addWidget(save_button) 