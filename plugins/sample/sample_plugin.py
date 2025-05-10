#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sample plugin for NetWORKS

This plugin demonstrates the NetWORKS plugin API and provides comprehensive
testing capabilities for the application.
"""

from loguru import logger
import sys
import os
import time
import datetime
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union, Tuple

from PySide6.QtWidgets import (
    QLabel, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QDockWidget,
    QPushButton, QTabWidget, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QGridLayout, QFormLayout, QGroupBox, QCheckBox, QComboBox,
    QSplitter, QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer
from PySide6.QtGui import QIcon, QAction, QFont, QColor

# Import the plugin interface
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.core.plugin_interface import PluginInterface


class SamplePlugin(PluginInterface):
    """
    Sample plugin implementation with testing capabilities
    
    This plugin serves as:
    1. A comprehensive example of the plugin API
    2. A testing utility for core NetWORKS functionality
    3. A signal monitoring tool
    """
    
    # Define custom signals
    test_started = Signal(str)  # Emitted when a test starts (test_name)
    test_completed = Signal(str, bool)  # Emitted when a test completes (test_name, success)
    test_all_completed = Signal(object)  # Emitted when all tests complete (results_dict)
    
    def __init__(self):
        """Initialize the plugin"""
        super().__init__()
        self.name = "Sample Plugin"
        self.version = "1.0.0"
        self.description = "A sample plugin that demonstrates the plugin system and provides testing capabilities"
        self.author = "NetWORKS Team"
        
        # Internal state
        self._connected_signals = set()  # Track connected signals for safe disconnection
        self._signal_monitors = {}  # Signal name -> monitoring enabled
        self._test_results = {}  # Test name -> results
        self._monitored_signal_log = []  # List of monitored signal events
        self._testing_in_progress = False
        
        # Plugin settings
        self.settings = {
            "log_level": {
                "name": "Log Level",
                "description": "The log level for plugin messages",
                "type": "choice",
                "default": "INFO",
                "value": "INFO",
                "choices": ["DEBUG", "INFO", "WARNING", "ERROR"]
            },
            "auto_sample": {
                "name": "Auto Sample",
                "description": "Automatically add sample property to new devices",
                "type": "bool",
                "default": True,
                "value": True
            },
            "default_value": {
                "name": "Default Value",
                "description": "Default value for the sample property",
                "type": "string",
                "default": "Sample Value",
                "value": "Sample Value"
            },
            "testing_mode": {
                "name": "Testing Mode",
                "description": "How tests should be executed",
                "type": "choice",
                "default": "manual",
                "value": "manual",
                "choices": ["manual", "automatic", "disabled"]
            },
            "test_signal_timeout": {
                "name": "Signal Test Timeout",
                "description": "Timeout in seconds for signal tests",
                "type": "int",
                "default": 10,
                "value": 10
            },
            "signal_monitoring": {
                "name": "Signal Monitoring",
                "description": "Enable signal monitoring by default",
                "type": "bool",
                "default": False,
                "value": False
            }
        }
        
        # Create UI components
        self._create_actions()
        self._create_widgets()
        
    def initialize(self, app, plugin_info):
        """Initialize the plugin"""
        logger.info(f"Initializing {self.name} v{self.version}")
        
        # Store app reference and set up plugin interface
        self.app = app
        self.device_manager = app.device_manager
        self.main_window = app.main_window
        self.config = app.config
        self.plugin_info = plugin_info
        
        # Create UI components
        self._create_actions()
        self._create_widgets()
        
        # Track connected signals for safe disconnection
        self._connected_signals = set()
        
        # Initialize signal monitoring
        self._initialize_signal_monitoring()
        
        # Connect to device manager signals with tracking
        self._connect_to_signal(self.device_manager.device_added, self.on_device_added, "device_added")
        self._connect_to_signal(self.device_manager.device_removed, self.on_device_removed, "device_removed")
        self._connect_to_signal(self.device_manager.device_changed, self.on_device_changed, "device_changed")
        self._connect_to_signal(self.device_manager.selection_changed, self.on_device_selected, "selection_changed")
        
        # Connect to plugin manager signals
        self._connect_to_signal(self.app.plugin_manager.plugin_loaded, self.on_plugin_loaded, "plugin_loaded")
        self._connect_to_signal(self.app.plugin_manager.plugin_unloaded, self.on_plugin_unloaded, "plugin_unloaded")
        self._connect_to_signal(self.app.plugin_manager.plugin_enabled, self.on_plugin_enabled, "plugin_enabled")
        self._connect_to_signal(self.app.plugin_manager.plugin_disabled, self.on_plugin_disabled, "plugin_disabled")
        
        # Add columns to device table
        self.add_device_columns()
        
        # Initialize signal monitoring based on settings
        if self.settings["signal_monitoring"]["value"]:
            self._enable_all_signal_monitoring()
            
        # Initialize testing system
        self._initialize_tests()
        
        # Initialize complete
        self._initialized = True
        self.plugin_initialized.emit()
        
        # Log initialization
        self.log_message(f"Plugin initialized: {self.name} v{self.version}")
        logger.info(f"Sample plugin initialization complete")
        
        return True
        
    def _connect_to_signal(self, signal, slot, signal_name):
        """Connect to a signal and track the connection"""
        try:
            signal.connect(slot)
            self._connected_signals.add(signal_name)
            logger.debug(f"Connected to signal: {signal_name}")
        except Exception as e:
            logger.error(f"Failed to connect to signal {signal_name}: {e}")
        
    def cleanup(self):
        """Clean up the plugin"""
        logger.info(f"Cleaning up {self.name}")
        self.log_message("Plugin cleanup started")
        
        # Disconnect signals safely with try/except blocks
        try:
            # Only attempt to disconnect if we have a device manager reference
            if hasattr(self, 'device_manager'):
                # Only disconnect signals that were successfully connected
                connected_signals = getattr(self, '_connected_signals', set())
                
                # Device manager signals
                if "device_added" in connected_signals:
                    try:
                        self.device_manager.device_added.disconnect(self.on_device_added)
                        logger.debug("Successfully disconnected device_added signal")
                    except Exception as e:
                        logger.debug(f"Error disconnecting device_added signal: {e}")
                
                if "device_removed" in connected_signals:
                    try:
                        self.device_manager.device_removed.disconnect(self.on_device_removed)
                        logger.debug("Successfully disconnected device_removed signal")
                    except Exception as e:
                        logger.debug(f"Error disconnecting device_removed signal: {e}")
                
                if "device_changed" in connected_signals:
                    try:
                        self.device_manager.device_changed.disconnect(self.on_device_changed)
                        logger.debug("Successfully disconnected device_changed signal")
                    except Exception as e:
                        logger.debug(f"Error disconnecting device_changed signal: {e}")
                
                if "selection_changed" in connected_signals:
                    try:
                        self.device_manager.selection_changed.disconnect(self.on_device_selected)
                        logger.debug("Successfully disconnected selection_changed signal")
                    except Exception as e:
                        logger.debug(f"Error disconnecting selection_changed signal: {e}")
                        
            # Plugin manager signals
            if hasattr(self, 'app') and hasattr(self.app, 'plugin_manager'):
                if "plugin_loaded" in connected_signals:
                    try:
                        self.app.plugin_manager.plugin_loaded.disconnect(self.on_plugin_loaded)
                        logger.debug("Successfully disconnected plugin_loaded signal")
                    except Exception as e:
                        logger.debug(f"Error disconnecting plugin_loaded signal: {e}")
                        
                if "plugin_unloaded" in connected_signals:
                    try:
                        self.app.plugin_manager.plugin_unloaded.disconnect(self.on_plugin_unloaded)
                        logger.debug("Successfully disconnected plugin_unloaded signal")
                    except Exception as e:
                        logger.debug(f"Error disconnecting plugin_unloaded signal: {e}")
                        
                if "plugin_enabled" in connected_signals:
                    try:
                        self.app.plugin_manager.plugin_enabled.disconnect(self.on_plugin_enabled)
                        logger.debug("Successfully disconnected plugin_enabled signal")
                    except Exception as e:
                        logger.debug(f"Error disconnecting plugin_enabled signal: {e}")
                        
                if "plugin_disabled" in connected_signals:
                    try:
                        self.app.plugin_manager.plugin_disabled.disconnect(self.on_plugin_disabled)
                        logger.debug("Successfully disconnected plugin_disabled signal")
                    except Exception as e:
                        logger.debug(f"Error disconnecting plugin_disabled signal: {e}")
        except Exception as e:
            logger.error(f"Error during plugin cleanup: {e}")
            
        # Stop any active tests
        if hasattr(self, '_testing_in_progress') and self._testing_in_progress:
            try:
                self._stop_tests()
            except Exception as e:
                logger.error(f"Error stopping tests during cleanup: {e}")
        
        # Clear references to help with garbage collection
        self.app = None
        self.device_manager = None
        self.main_window = None
        self.config = None
        self.plugin_info = None
        
        # Cleanup complete
        self.log_message("Plugin cleanup completed")
        logger.info(f"Sample plugin cleanup complete")
        return super().cleanup()
        
    def _create_actions(self):
        """Create actions for menus and toolbar"""
        # Create a toolbar action
        self.action_sample = QAction("Sample Action", self)
        self.action_sample.setStatusTip("Add sample property to selected devices")
        self.action_sample.triggered.connect(self.on_sample_action)
        
        # Create test action for toolbar
        self.action_test = QAction("Test Application", self)
        self.action_test.setStatusTip("Launch application testing dashboard")
        self.action_test.triggered.connect(self.on_test_action)
        
        # Create menu actions
        self.action_sample_menu = QAction("Sample Menu Action", self)
        self.action_sample_menu.setStatusTip("A sample menu action")
        self.action_sample_menu.triggered.connect(self.on_sample_menu_action)
        
        self.action_new_device = QAction("Add New Device", self)
        self.action_new_device.setStatusTip("Add a new device using the dialog")
        self.action_new_device.triggered.connect(self.create_new_device)
        
        self.action_edit_device = QAction("Edit Selected Device", self)
        self.action_edit_device.setStatusTip("Edit the selected device using the dialog")
        self.action_edit_device.triggered.connect(self.edit_selected_device)
        
        self.action_run_tests = QAction("Run Tests", self)
        self.action_run_tests.setStatusTip("Run comprehensive application tests")
        self.action_run_tests.triggered.connect(self.test_core_features)
        
        self.action_signal_monitor = QAction("Signal Monitor", self)
        self.action_signal_monitor.setStatusTip("Open signal monitoring dashboard")
        self.action_signal_monitor.triggered.connect(self.show_signal_monitor)
        
    def _create_widgets(self):
        """Create widgets for the plugin"""
        # Create the main plugin panel with tabs
        self.main_panel = QTabWidget()
        
        # --- Log Tab ---
        self.log_tab = QWidget()
        self.log_layout = QVBoxLayout(self.log_tab)
        
        # Create a text edit for logs
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_layout.addWidget(self.log_widget)
        
        # Add log control buttons
        log_buttons_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.log_widget.clear)
        log_buttons_layout.addWidget(self.clear_log_button)
        
        self.save_log_button = QPushButton("Save Log")
        self.save_log_button.clicked.connect(self._save_log)
        log_buttons_layout.addWidget(self.save_log_button)
        
        self.log_layout.addLayout(log_buttons_layout)
        
        # --- Test Dashboard Tab ---
        self.test_tab = QWidget()
        self.test_layout = QVBoxLayout(self.test_tab)
        
        # Test dashboard panel
        self.test_dashboard = QWidget()
        self.test_dashboard_layout = QVBoxLayout(self.test_dashboard)
        
        # Test control group
        test_control_group = QGroupBox("Test Controls")
        test_control_layout = QHBoxLayout(test_control_group)
        
        self.run_all_tests_button = QPushButton("Run All Tests")
        self.run_all_tests_button.clicked.connect(self.test_core_features)
        test_control_layout.addWidget(self.run_all_tests_button)
        
        self.stop_tests_button = QPushButton("Stop Tests")
        self.stop_tests_button.clicked.connect(self._stop_tests)
        self.stop_tests_button.setEnabled(False)
        test_control_layout.addWidget(self.stop_tests_button)
        
        self.test_dashboard_layout.addWidget(test_control_group)
        
        # Test results group
        test_results_group = QGroupBox("Test Results")
        test_results_layout = QVBoxLayout(test_results_group)
        
        # Add tree widget for test results
        self.test_results_tree = QTreeWidget()
        self.test_results_tree.setHeaderLabels(["Test", "Status", "Duration"])
        self.test_results_tree.setColumnWidth(0, 250)
        test_results_layout.addWidget(self.test_results_tree)
        
        # Progress bar for test progress
        self.test_progress = QProgressBar()
        self.test_progress.setRange(0, 100)
        self.test_progress.setValue(0)
        test_results_layout.addWidget(self.test_progress)
        
        self.test_dashboard_layout.addWidget(test_results_group)
        
        # Add the test dashboard to the test tab
        self.test_layout.addWidget(self.test_dashboard)
        
        # --- Signal Monitor Tab ---
        self.signal_tab = QWidget()
        self.signal_layout = QVBoxLayout(self.signal_tab)
        
        # Signal control group
        signal_control_group = QGroupBox("Signal Monitoring")
        signal_control_layout = QVBoxLayout(signal_control_group)
        
        # Signal monitoring controls
        signal_buttons_layout = QHBoxLayout()
        
        self.enable_all_signals_button = QPushButton("Enable All")
        self.enable_all_signals_button.clicked.connect(self._enable_all_signal_monitoring)
        signal_buttons_layout.addWidget(self.enable_all_signals_button)
        
        self.disable_all_signals_button = QPushButton("Disable All")
        self.disable_all_signals_button.clicked.connect(self._disable_all_signal_monitoring)
        signal_buttons_layout.addWidget(self.disable_all_signals_button)
        
        self.clear_signal_log_button = QPushButton("Clear Log")
        self.clear_signal_log_button.clicked.connect(self._clear_signal_log)
        signal_buttons_layout.addWidget(self.clear_signal_log_button)
        
        signal_control_layout.addLayout(signal_buttons_layout)
        
        # Signal selection list with checkboxes
        self.signal_list_widget = QWidget()
        self.signal_list_layout = QFormLayout(self.signal_list_widget)
        
        # We'll populate this in _initialize_signal_monitoring
        signal_control_layout.addWidget(self.signal_list_widget)
        
        self.signal_layout.addWidget(signal_control_group)
        
        # Signal log table
        signal_log_group = QGroupBox("Signal Log")
        signal_log_layout = QVBoxLayout(signal_log_group)
        
        self.signal_log_table = QTableWidget()
        self.signal_log_table.setColumnCount(4)
        self.signal_log_table.setHorizontalHeaderLabels(["Timestamp", "Signal", "Source", "Parameters"])
        self.signal_log_table.setColumnWidth(0, 150)
        self.signal_log_table.setColumnWidth(1, 150)
        self.signal_log_table.setColumnWidth(2, 150)
        self.signal_log_table.setColumnWidth(3, 250)
        
        signal_log_layout.addWidget(self.signal_log_table)
        
        self.signal_layout.addWidget(signal_log_group)
        
        # --- Device Details Tab ---
        self.details_tab = QWidget()
        self.details_layout = QVBoxLayout(self.details_tab)
        
        # Device details panel
        self.details_widget = QWidget()
        self.details_widget.setObjectName("SamplePluginDetailsWidget")
        self.details_layout_widget = QVBoxLayout(self.details_widget)
        self.details_layout_widget.addWidget(QLabel("Sample Plugin Device Details"))
        
        # Device info
        self.details_info_group = QGroupBox("Device Information")
        self.details_info_layout = QFormLayout(self.details_info_group)
        self.device_name_label = QLabel("No device selected")
        self.device_type_label = QLabel("N/A")
        self.device_status_label = QLabel("N/A")
        self.device_sample_label = QLabel("N/A")
        
        self.details_info_layout.addRow("Name:", self.device_name_label)
        self.details_info_layout.addRow("Type:", self.device_type_label)
        self.details_info_layout.addRow("Status:", self.device_status_label)
        self.details_info_layout.addRow("Sample:", self.device_sample_label)
        
        self.details_layout_widget.addWidget(self.details_info_group)
        
        # Device test group
        self.details_test_group = QGroupBox("Device Testing")
        self.details_test_layout = QVBoxLayout(self.details_test_group)
        
        # Test buttons for device
        device_test_buttons = QHBoxLayout()
        
        self.test_device_button = QPushButton("Test Device")
        self.test_device_button.clicked.connect(self._test_selected_device)
        device_test_buttons.addWidget(self.test_device_button)
        
        self.clear_device_test_button = QPushButton("Clear Test Results")
        self.clear_device_test_button.clicked.connect(self._clear_device_test_results)
        device_test_buttons.addWidget(self.clear_device_test_button)
        
        self.details_test_layout.addLayout(device_test_buttons)
        
        # Test results
        self.device_test_results = QTextEdit()
        self.device_test_results.setReadOnly(True)
        self.device_test_results.setPlaceholderText("No test results available")
        self.details_test_layout.addWidget(self.device_test_results)
        
        self.details_layout_widget.addWidget(self.details_test_group)
        
        # Add to details tab
        self.details_layout.addWidget(self.details_widget)
        
        # Add tabs to main panel
        self.main_panel.addTab(self.log_tab, "Log")
        self.main_panel.addTab(self.test_tab, "Test Dashboard")
        self.main_panel.addTab(self.signal_tab, "Signal Monitor")
        self.main_panel.addTab(self.details_tab, "Device Details")
        
        # Create a dock widget to properly contain the main panel
        self.dock_widget = QDockWidget("Sample Plugin")
        self.dock_widget.setObjectName("SamplePluginDock")
        self.dock_widget.setWidget(self.main_panel)
        
    def _save_log(self):
        """Save the log contents to a file"""
        try:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"sample_plugin_log_{timestamp}.txt")
            
            with open(log_file, 'w') as f:
                f.write(self.log_widget.toPlainText())
                
            self.log_message(f"Log saved to: {log_file}")
            logger.info(f"Sample plugin log saved to: {log_file}")
        except Exception as e:
            logger.error(f"Error saving log: {e}")
            self.log_message(f"Error saving log: {e}")
            
    def log_message(self, message):
        """Add a message to the log widget"""
        if hasattr(self, 'log_widget'):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_widget.append(f"[{timestamp}] {message}")
            
            # Ensure the new message is visible
            scrollbar = self.log_widget.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
    def add_device_columns(self):
        """Add columns to the device table"""
        # Add a sample column to the device table
        if hasattr(self.main_window, 'device_table_model'):
            self.main_window.device_table_model.add_column(
                "Sample", "sample", self.get_sample_value
            )
            # Add a test result column
            self.main_window.device_table_model.add_column(
                "Test Result", "test_result", self.get_test_result_value
            )
            
    def get_sample_value(self, device):
        """Get a sample value for a device"""
        return device.get_property("sample", "N/A")

    def get_test_result_value(self, device):
        """Get the test result value for a device"""
        result = device.get_property("test_result", "Not tested")
        return result
        
    def get_toolbar_actions(self):
        """Get actions to be added to the toolbar"""
        return [self.action_sample, self.action_test]
        
    def get_menu_actions(self):
        """Get actions to be added to the menu"""
        return {
            "Sample": [
                self.action_sample_menu,
                self.action_new_device,
                self.action_edit_device,
                self.action_run_tests,
                self.action_signal_monitor
            ]
        }
        
    def get_device_panels(self):
        """Get panels to be added to the device view"""
        return [
            ("Sample", self.details_widget)
        ]
        
    def get_dock_widgets(self):
        """Get dock widgets to be added to the main window"""
        return [
            ("Sample Plugin", self.dock_widget, Qt.RightDockWidgetArea)
        ]
        
    def get_device_table_columns(self):
        """Get columns to be added to the device table"""
        return [
            ("Sample", "sample", self.get_sample_value),
            ("Test Result", "test_result", self.get_test_result_value)
        ]
        
    def get_settings(self):
        """Get plugin settings"""
        return self.settings
        
    def update_setting(self, setting_id, value):
        """Update a plugin setting"""
        if setting_id not in self.settings:
            logger.warning(f"Unknown setting: {setting_id}")
            return False
            
        try:
            # Update the setting value
            self.settings[setting_id]["value"] = value
            
            # Handle special settings
            if setting_id == "log_level":
                logger.debug(f"Changed log level to {value}")
                
            elif setting_id == "auto_sample":
                logger.debug(f"Auto sample set to {value}")
                
            elif setting_id == "default_value":
                logger.debug(f"Default sample value set to {value}")
                
            elif setting_id == "testing_mode":
                logger.debug(f"Testing mode set to {value}")
                
            elif setting_id == "test_signal_timeout":
                logger.debug(f"Signal test timeout set to {value}")
                
            elif setting_id == "signal_monitoring":
                logger.debug(f"Signal monitoring set to {value}")
                
            self.log_widget.append(f"Setting '{self.settings[setting_id]['name']}' updated to: {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating setting {setting_id}: {e}")
            return False
        
    # Event handlers
    
    def on_sample_action(self):
        """Handle sample action"""
        logger.info("Sample action triggered")
        self.log_widget.append("Sample action triggered")
        
        # Add sample property to selected devices
        selected_devices = self.device_manager.get_selected_devices()
        for device in selected_devices:
            device.set_property("sample", self.settings["default_value"]["value"])
            self.log_widget.append(f"Added sample property to {device.get_property('name')}")
            
    def on_test_action(self):
        """Handle test action"""
        logger.info("Test action triggered")
        self.log_widget.append("Test action triggered")
        
        # Activate the test dashboard tab
        self.main_panel.setCurrentWidget(self.test_tab)
        
    def on_sample_menu_action(self):
        """Handle sample menu action"""
        logger.info("Sample menu action triggered")
        self.log_widget.append("Sample menu action triggered")
        
    def show_signal_monitor(self):
        """Show the signal monitor tab"""
        logger.info("Signal monitor action triggered")
        self.log_widget.append("Opening signal monitor")
        
        # Activate the signal monitor tab
        self.main_panel.setCurrentWidget(self.signal_tab)
        
    def create_new_device(self):
        """Create a new device using the dialog"""
        logger.info("Creating new device using dialog")
        self.log_widget.append("Creating new device...")
        
        # Use the plugin interface method to show the add device dialog
        new_device = self.add_device_dialog()
        
        if new_device:
            # Device was created and automatically added to the device manager
            logger.info(f"New device created: {new_device.get_property('alias')}")
            self.log_widget.append(f"Created device: {new_device.get_property('alias')}")
            
            # Add sample property if auto_sample is enabled
            if self.settings["auto_sample"]["value"]:
                default_value = self.settings["default_value"]["value"]
                new_device.set_property("sample", default_value)
                self.log_widget.append(f"Added sample property to new device: {default_value}")
        else:
            self.log_widget.append("Device creation cancelled")
            
    def edit_selected_device(self):
        """Edit the selected device using the dialog"""
        selected_devices = self.device_manager.get_selected_devices()
        
        if not selected_devices:
            logger.warning("No device selected to edit")
            self.log_widget.append("No device selected to edit")
            return
            
        device = selected_devices[0]
        logger.info(f"Editing device: {device.get_property('alias')}")
        self.log_widget.append(f"Editing device: {device.get_property('alias')}")
        
        # Use the plugin interface method to show the device properties dialog
        updated_device = self.show_device_properties_dialog(device)
        
        if updated_device:
            # Device was updated
            logger.info(f"Device updated: {updated_device.get_property('alias')}")
            self.log_widget.append(f"Updated device: {updated_device.get_property('alias')}")
        else:
            self.log_widget.append("Device edit cancelled")
        
    # Signal handlers
    
    def on_device_added(self, device):
        """Handle device added signal"""
        logger.debug(f"Sample plugin: Device added: {device}")
        self.log_message(f"Device added: {device.get_property('name')}")
        
        # Add sample property if auto_sample is enabled
        if self.settings["auto_sample"]["value"]:
            default_value = self.settings["default_value"]["value"]
            device.set_property("sample", default_value)
            self.log_message(f"Added sample property to new device: {default_value}")
            
        # Log signal event for monitoring
        self._log_signal_event("device_added", "Device Manager", device.get_property("name"))
        
    def on_device_removed(self, device):
        """Handle device removed signal"""
        logger.debug(f"Sample plugin: Device removed: {device}")
        self.log_message(f"Device removed: {device.get_property('name')}")
        
        # Log signal event for monitoring
        self._log_signal_event("device_removed", "Device Manager", device.get_property("name"))
        
    def on_device_changed(self, device):
        """Handle device changed signal"""
        logger.debug(f"Sample plugin: Device changed: {device}")
        
        # Update details if this is the selected device
        selected_devices = self.device_manager.get_selected_devices()
        if device in selected_devices:
            self.update_device_details(device)
            
        # Log signal event for monitoring
        self._log_signal_event("device_changed", "Device Manager", device.get_property("name"))
            
    def on_device_selected(self, devices):
        """Handle device selection changed signal"""
        logger.debug(f"Sample plugin: Device selection changed: {len(devices)} selected")
        
        if devices:
            self.update_device_details(devices[0])
        else:
            # Clear the device details
            self.device_name_label.setText("No device selected")
            self.device_type_label.setText("N/A")
            self.device_status_label.setText("N/A")
            self.device_sample_label.setText("N/A")
            self.device_test_results.clear()
            
        # Log signal event for monitoring
        device_names = [d.get_property("name") for d in devices] if devices else ["None"]
        self._log_signal_event("selection_changed", "Device Manager", f"{len(devices)} devices: {', '.join(device_names)}")
    
    def on_plugin_loaded(self, plugin_info):
        """Handle plugin loaded signal"""
        logger.debug(f"Sample plugin: Plugin loaded: {plugin_info.name}")
        self.log_message(f"Plugin loaded: {plugin_info.name} v{plugin_info.version}")
        
        # Log signal event for monitoring
        self._log_signal_event("plugin_loaded", "Plugin Manager", f"{plugin_info.name} v{plugin_info.version}")
        
    def on_plugin_unloaded(self, plugin_info):
        """Handle plugin unloaded signal"""
        logger.debug(f"Sample plugin: Plugin unloaded: {plugin_info.name}")
        self.log_message(f"Plugin unloaded: {plugin_info.name}")
        
        # Log signal event for monitoring
        self._log_signal_event("plugin_unloaded", "Plugin Manager", plugin_info.name)
        
    def on_plugin_enabled(self, plugin_info):
        """Handle plugin enabled signal"""
        logger.debug(f"Sample plugin: Plugin enabled: {plugin_info.name}")
        self.log_message(f"Plugin enabled: {plugin_info.name}")
        
        # Log signal event for monitoring
        self._log_signal_event("plugin_enabled", "Plugin Manager", plugin_info.name)
        
    def on_plugin_disabled(self, plugin_info):
        """Handle plugin disabled signal"""
        logger.debug(f"Sample plugin: Plugin disabled: {plugin_info.name}")
        self.log_message(f"Plugin disabled: {plugin_info.name}")
        
        # Log signal event for monitoring
        self._log_signal_event("plugin_disabled", "Plugin Manager", plugin_info.name)
            
    def update_device_details(self, device):
        """Update device details in the panel"""
        # Update device information labels
        self.device_name_label.setText(device.get_property("name", "N/A"))
        self.device_type_label.setText(device.get_property("type", "N/A"))
        self.device_status_label.setText(device.get_property("status", "N/A"))
        self.device_sample_label.setText(device.get_property("sample", "N/A"))
        
        # Update test results if available
        test_result = device.get_property("test_result", "Not tested")
        test_timestamp = device.get_property("test_timestamp", "")
        
        if test_result != "Not tested":
            if test_timestamp:
                self.device_test_results.setText(f"Last test: {test_timestamp}\nResult: {test_result}")
            else:
                self.device_test_results.setText(f"Result: {test_result}")
        else:
            self.device_test_results.clear()
        
    # Testing functionality
    
    def _initialize_tests(self):
        """Initialize the testing system"""
        # Define available tests
        self._test_definitions = {
            "core": {
                "name": "Core Features",
                "tests": {
                    "application_version": {
                        "name": "Application Version",
                        "function": self._test_application_version,
                        "description": "Verify application version information"
                    },
                    "device_manager": {
                        "name": "Device Manager",
                        "function": self._test_device_manager,
                        "description": "Test device manager functionality"
                    },
                    "plugin_manager": {
                        "name": "Plugin Manager",
                        "function": self._test_plugin_manager,
                        "description": "Test plugin manager functionality"
                    },
                    "configuration": {
                        "name": "Configuration System",
                        "function": self._test_configuration,
                        "description": "Test configuration loading and saving"
                    }
                }
            },
            "signals": {
                "name": "Signal System",
                "tests": {
                    "device_signals": {
                        "name": "Device Signals",
                        "function": self._test_device_signals,
                        "description": "Test device-related signals"
                    },
                    "plugin_signals": {
                        "name": "Plugin Signals",
                        "function": self._test_plugin_signals,
                        "description": "Test plugin-related signals"
                    },
                    "ui_signals": {
                        "name": "UI Signals",
                        "function": self._test_ui_signals,
                        "description": "Test UI-related signals"
                    }
                }
            },
            "ui": {
                "name": "User Interface",
                "tests": {
                    "main_window": {
                        "name": "Main Window",
                        "function": self._test_main_window,
                        "description": "Test main window functionality"
                    },
                    "device_table": {
                        "name": "Device Table",
                        "function": self._test_device_table,
                        "description": "Test device table functionality"
                    },
                    "dialogs": {
                        "name": "Dialogs",
                        "function": self._test_dialogs,
                        "description": "Test application dialogs"
                    }
                }
            }
        }
        
        # Initialize test results
        self._test_results = {}
        
        # Populate the test tree widget
        self._populate_test_tree()
        
    def _populate_test_tree(self):
        """Populate the test tree widget with available tests"""
        self.test_results_tree.clear()
        
        for category_id, category in self._test_definitions.items():
            category_item = QTreeWidgetItem(self.test_results_tree)
            category_item.setText(0, category["name"])
            category_item.setExpanded(True)
            
            for test_id, test in category["tests"].items():
                test_item = QTreeWidgetItem(category_item)
                test_item.setText(0, test["name"])
                test_item.setText(1, "Not Run")
                test_item.setToolTip(0, test["description"])
                
                # Store test IDs in the item data
                test_item.setData(0, Qt.UserRole, f"{category_id}.{test_id}")
        
    def _update_test_result(self, category_id, test_id, success, duration, message=None):
        """Update the result of a test in the UI"""
        # Find the test item in the tree
        test_data = f"{category_id}.{test_id}"
        root = self.test_results_tree.invisibleRootItem()
        
        for i in range(root.childCount()):
            category_item = root.child(i)
            
            for j in range(category_item.childCount()):
                test_item = category_item.child(j)
                if test_item.data(0, Qt.UserRole) == test_data:
                    # Update the item
                    status = "SUCCESS" if success else "FAILED"
                    test_item.setText(1, status)
                    test_item.setText(2, f"{duration:.2f}s")
                    
                    # Set status color
                    test_item.setForeground(1, QColor("green" if success else "red"))
                    
                    # Store the message in the tooltip
                    if message:
                        test_item.setToolTip(1, message)
                    
                    break
                    
        # Update the progress bar
        total_tests = 0
        completed_tests = 0
        
        for category_id, category in self._test_definitions.items():
            for test_id in category["tests"]:
                total_tests += 1
                if f"{category_id}.{test_id}" in self._test_results:
                    completed_tests += 1
                    
        if total_tests > 0:
            progress = int((completed_tests / total_tests) * 100)
            self.test_progress.setValue(progress)
        
    def test_core_features(self):
        """Run all tests for core application features"""
        if self._testing_in_progress:
            logger.warning("Tests already in progress")
            self.log_message("Tests already in progress, please wait...")
            return
            
        self._testing_in_progress = True
        self.stop_tests_button.setEnabled(True)
        self.run_all_tests_button.setEnabled(False)
        self.log_message("Starting comprehensive application tests...")
        
        # Clear previous results
        self._test_results = {}
        self._populate_test_tree()
        self.test_progress.setValue(0)
        
        # Emit test started signal
        self.test_started.emit("all")
        
        # Run tests in a timer to keep UI responsive
        self._remaining_tests = []
        
        # Build the list of tests to run
        for category_id, category in self._test_definitions.items():
            for test_id, test in category["tests"].items():
                self._remaining_tests.append((category_id, test_id, test))
                
        # Start running tests
        QTimer.singleShot(100, self._run_next_test)
        
    def _run_next_test(self):
        """Run the next test in the queue"""
        if not self._testing_in_progress or not self._remaining_tests:
            # No more tests or testing stopped
            self._testing_in_progress = False
            self.stop_tests_button.setEnabled(False)
            self.run_all_tests_button.setEnabled(True)
            
            # Emit completed signal
            self.test_all_completed.emit(self._test_results)
            
            # Log completion
            total_tests = len(self._test_results)
            passed_tests = sum(1 for r in self._test_results.values() if r["success"])
            
            self.log_message(f"Testing complete: {passed_tests}/{total_tests} tests passed")
            logger.info(f"Sample plugin testing complete: {passed_tests}/{total_tests} tests passed")
            
            return
            
        # Get the next test
        category_id, test_id, test = self._remaining_tests.pop(0)
        
        # Log test start
        test_name = test["name"]
        self.log_message(f"Running test: {test_name}")
        
        # Emit test started signal
        self.test_started.emit(f"{category_id}.{test_id}")
        
        # Run the test
        start_time = time.time()
        try:
            result = test["function"]()
            if isinstance(result, tuple) and len(result) == 2:
                success, message = result
            else:
                success = result
                message = "Test completed successfully" if success else "Test failed"
        except Exception as e:
            success = False
            message = f"Test raised an exception: {str(e)}"
            logger.error(f"Test {test_name} failed with exception: {e}", exc_info=True)
            
        duration = time.time() - start_time
        
        # Store the result
        self._test_results[f"{category_id}.{test_id}"] = {
            "success": success,
            "duration": duration,
            "message": message,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Update the UI
        self._update_test_result(category_id, test_id, success, duration, message)
        
        # Emit test completed signal
        self.test_completed.emit(f"{category_id}.{test_id}", success)
        
        # Schedule the next test
        QTimer.singleShot(100, self._run_next_test)
    
    def _stop_tests(self):
        """Stop the currently running tests"""
        if not self._testing_in_progress:
            return
            
        self._testing_in_progress = False
        self._remaining_tests = []
        self.stop_tests_button.setEnabled(False)
        self.run_all_tests_button.setEnabled(True)
        
        self.log_message("Tests stopped by user")
        logger.info("Sample plugin tests stopped by user")
        
    def test_signal(self, signal_name):
        """Test a specific signal"""
        if signal_name not in self._connected_signals:
            self.log_message(f"Signal {signal_name} is not connected, cannot test")
            return False
            
        # Log test start
        self.log_message(f"Testing signal: {signal_name}")
        
        # The implementation would depend on the specific signal
        # Here we'll just log that we would test it
        self.log_message(f"Signal test for {signal_name} would be implemented here")
        
        # For now, return True
        return True
        
    def _test_application_version(self):
        """Test application version functionality"""
        try:
            if not hasattr(self.app, 'get_version'):
                return False, "Application does not have get_version method"
                
            version = self.app.get_version()
            self.log_message(f"Application version: {version}")
            
            # Basic validation that version looks reasonable
            if isinstance(version, str) and len(version.split('.')) >= 2:
                return True, f"Version validated: {version}"
            else:
                return False, f"Invalid version format: {version}"
        except Exception as e:
            return False, f"Error testing application version: {str(e)}"
            
    def _test_device_manager(self):
        """Test device manager functionality"""
        try:
            device_count = len(self.device_manager.get_devices())
            self.log_message(f"Device manager has {device_count} devices")
            
            # Create a test device
            from src.core.device import Device
            test_device = Device()
            test_device.set_property("name", "Test Device")
            test_device.set_property("type", "test")
            
            # Add to device manager
            self.device_manager.add_device(test_device)
            new_count = len(self.device_manager.get_devices())
            
            if new_count != device_count + 1:
                return False, f"Failed to add test device. Count before: {device_count}, after: {new_count}"
                
            # Remove test device
            self.device_manager.remove_device(test_device)
            final_count = len(self.device_manager.get_devices())
            
            if final_count != device_count:
                return False, f"Failed to remove test device. Original count: {device_count}, final: {final_count}"
                
            return True, f"Successfully tested device addition and removal"
        except Exception as e:
            return False, f"Error testing device manager: {str(e)}"
            
    def _test_plugin_manager(self):
        """Test plugin manager functionality"""
        try:
            plugin_count = len(self.app.plugin_manager.get_plugins())
            self.log_message(f"Plugin manager has {plugin_count} plugins")
            
            # Check that our plugin is loaded
            our_plugin = self.app.plugin_manager.get_plugin("sample")
            if not our_plugin or not our_plugin.loaded:
                return False, "Sample plugin not properly loaded"
                
            return True, f"Plugin manager has {plugin_count} plugins including sample plugin"
        except Exception as e:
            return False, f"Error testing plugin manager: {str(e)}"
            
    def _test_configuration(self):
        """Test configuration system"""
        try:
            # Test reading a config value
            app_name = self.app.config.get("application.name", None)
            if not app_name:
                return False, "Could not read application name from config"
                
            self.log_message(f"Application name from config: {app_name}")
            
            # For now, we'll just verify we can read a value
            return True, "Successfully read configuration value"
        except Exception as e:
            return False, f"Error testing configuration: {str(e)}"
            
    def _test_device_signals(self):
        """Test device-related signals"""
        self.log_message("Testing device signals - verification is manual")
        return True, "Device signals test completed"
            
    def _test_plugin_signals(self):
        """Test plugin-related signals"""
        self.log_message("Testing plugin signals - verification is manual")
        return True, "Plugin signals test completed"
            
    def _test_ui_signals(self):
        """Test UI-related signals"""
        self.log_message("Testing UI signals - verification is manual")
        return True, "UI signals test completed"
            
    def _test_main_window(self):
        """Test main window functionality"""
        try:
            if not self.main_window:
                return False, "Main window reference not available"
                
            window_title = self.main_window.windowTitle()
            self.log_message(f"Main window title: {window_title}")
            
            # For now, just verify we have access to the main window
            return True, "Successfully accessed main window"
        except Exception as e:
            return False, f"Error testing main window: {str(e)}"
            
    def _test_device_table(self):
        """Test device table functionality"""
        try:
            if not hasattr(self.main_window, 'device_table_model'):
                return False, "Device table model not available"
                
            column_count = self.main_window.device_table_model.columnCount()
            self.log_message(f"Device table has {column_count} columns")
            
            # For now, just verify we have access to the device table
            return True, "Successfully accessed device table"
        except Exception as e:
            return False, f"Error testing device table: {str(e)}"
            
    def _test_dialogs(self):
        """Test application dialogs"""
        self.log_message("Testing dialogs - skipped for automated testing")
        return True, "Dialog tests skipped (would require user interaction)"
        
    def _test_selected_device(self):
        """Test the currently selected device"""
        selected_devices = self.device_manager.get_selected_devices()
        if not selected_devices:
            self.log_message("No device selected for testing")
            return
            
        device = selected_devices[0]
        self.log_message(f"Testing device: {device.get_property('name')}")
        
        # Record the test start time
        start_time = time.time()
        
        # Perform some simple tests on the device
        test_results = []
        
        # Test 1: Verify device has required properties
        required_props = ["name", "type", "id"]
        missing_props = []
        
        for prop in required_props:
            if not device.has_property(prop):
                missing_props.append(prop)
                
        if missing_props:
            test_results.append(f"FAIL: Device missing required properties: {', '.join(missing_props)}")
        else:
            test_results.append("PASS: Device has all required properties")
            
        # Test 2: Set and verify a property
        test_value = f"test-{int(time.time())}"
        device.set_property("sample", test_value)
        
        read_value = device.get_property("sample")
        if read_value == test_value:
            test_results.append(f"PASS: Property read/write test successful")
        else:
            test_results.append(f"FAIL: Property read/write test failed. Expected {test_value}, got {read_value}")
            
        # Calculate duration
        duration = time.time() - start_time
        
        # Generate summary
        passes = sum(1 for r in test_results if r.startswith("PASS"))
        fails = sum(1 for r in test_results if r.startswith("FAIL"))
        
        summary = f"Test Results: {passes} passed, {fails} failed (completed in {duration:.2f}s)"
        
        # Update device test results
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = "PASS" if fails == 0 else "FAIL"
        
        device.set_property("test_timestamp", current_time)
        device.set_property("test_result", result)
        
        # Update the UI
        self.device_test_results.clear()
        self.device_test_results.append(summary)
        self.device_test_results.append("")
        for result in test_results:
            self.device_test_results.append(result)
            
        # Log the results
        self.log_message(f"Device test complete: {summary}")
        
    def _clear_device_test_results(self):
        """Clear the test results for the selected device"""
        selected_devices = self.device_manager.get_selected_devices()
        if not selected_devices:
            return
            
        device = selected_devices[0]
        
        # Clear the properties
        device.set_property("test_result", "Not tested")
        device.set_property("test_timestamp", "")
        
        # Clear the UI
        self.device_test_results.clear()
        
        self.log_message(f"Cleared test results for device: {device.get_property('name')}")
        
    # Signal monitoring functionality
    
    def _initialize_signal_monitoring(self):
        """Initialize signal monitoring system"""
        # Define all monitorable signals
        signals = [
            # Device manager signals
            {"name": "device_added", "source": "Device Manager"},
            {"name": "device_removed", "source": "Device Manager"},
            {"name": "device_changed", "source": "Device Manager"},
            {"name": "selection_changed", "source": "Device Manager"},
            {"name": "group_added", "source": "Device Manager"},
            {"name": "group_removed", "source": "Device Manager"},
            
            # Plugin manager signals
            {"name": "plugin_loaded", "source": "Plugin Manager"},
            {"name": "plugin_unloaded", "source": "Plugin Manager"},
            {"name": "plugin_enabled", "source": "Plugin Manager"},
            {"name": "plugin_disabled", "source": "Plugin Manager"}
        ]
        
        # Create the signal monitor checkboxes
        for signal in signals:
            name = signal["name"]
            checkbox = QCheckBox(f"{signal['source']}.{name}")
            checkbox.stateChanged.connect(lambda state, s=name: self.monitor_signal(s, state == Qt.Checked))
            
            # Set initial state
            enable_monitoring = self.settings["signal_monitoring"]["value"]
            checkbox.setChecked(enable_monitoring)
            self._signal_monitors[name] = enable_monitoring
            
            # Add to the form layout
            self.signal_list_layout.addWidget(checkbox)
            
        # Clear the signal log table
        self.signal_log_table.setRowCount(0)
        
    def monitor_signal(self, signal_name, enable=True):
        """Enable or disable monitoring for a specific signal"""
        self._signal_monitors[signal_name] = enable
        self.log_message(f"Signal monitoring for {signal_name}: {'Enabled' if enable else 'Disabled'}")
        return True
        
    def _log_signal_event(self, signal_name, source, parameters=None):
        """Log a signal event to the monitor"""
        if signal_name not in self._signal_monitors or not self._signal_monitors[signal_name]:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format parameters for display
        params_text = ""
        if parameters:
            if isinstance(parameters, list) or isinstance(parameters, tuple):
                params_text = ", ".join(str(p) for p in parameters)
            else:
                params_text = str(parameters)
                
        # Add to monitored signal log
        self._monitored_signal_log.append({
            "timestamp": timestamp,
            "signal": signal_name,
            "source": source,
            "parameters": params_text
        })
        
        # Add to the table
        row = self.signal_log_table.rowCount()
        self.signal_log_table.insertRow(row)
        
        self.signal_log_table.setItem(row, 0, QTableWidgetItem(timestamp))
        self.signal_log_table.setItem(row, 1, QTableWidgetItem(signal_name))
        self.signal_log_table.setItem(row, 2, QTableWidgetItem(source))
        self.signal_log_table.setItem(row, 3, QTableWidgetItem(params_text))
        
        # Scroll to the new row
        self.signal_log_table.scrollToBottom()
        
    def _enable_all_signal_monitoring(self):
        """Enable monitoring for all signals"""
        for signal_name in self._signal_monitors:
            self._signal_monitors[signal_name] = True
            
        # Update checkboxes
        for i in range(self.signal_list_layout.count()):
            widget = self.signal_list_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.blockSignals(True)
                widget.setChecked(True)
                widget.blockSignals(False)
                
        self.log_message("Enabled monitoring for all signals")
        
    def _disable_all_signal_monitoring(self):
        """Disable monitoring for all signals"""
        for signal_name in self._signal_monitors:
            self._signal_monitors[signal_name] = False
            
        # Update checkboxes
        for i in range(self.signal_list_layout.count()):
            widget = self.signal_list_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.blockSignals(True)
                widget.setChecked(False)
                widget.blockSignals(False)
                
        self.log_message("Disabled monitoring for all signals")
        
    def _clear_signal_log(self):
        """Clear the signal log"""
        self._monitored_signal_log = []
        self.signal_log_table.setRowCount(0)
        self.log_message("Signal log cleared")
        
    # Action handlers
        
    def on_sample_action(self):
        """Handle sample action"""
        logger.info("Sample action triggered")
        self.log_widget.append("Sample action triggered")
        
        # Add sample property to selected devices
        selected_devices = self.device_manager.get_selected_devices()
        for device in selected_devices:
            device.set_property("sample", self.settings["default_value"]["value"])
            self.log_widget.append(f"Added sample property to {device.get_property('name')}")
            
    def on_test_action(self):
        """Handle test action"""
        logger.info("Test action triggered")
        self.log_widget.append("Test action triggered")
        
        # Activate the test dashboard tab
        self.main_panel.setCurrentWidget(self.test_tab)
        
    def on_sample_menu_action(self):
        """Handle sample menu action"""
        logger.info("Sample menu action triggered")
        self.log_widget.append("Sample menu action triggered")
        
    def show_signal_monitor(self):
        """Show the signal monitor tab"""
        logger.info("Signal monitor action triggered")
        self.log_widget.append("Opening signal monitor")
        
        # Activate the signal monitor tab
        self.main_panel.setCurrentWidget(self.signal_tab)
        
    def create_new_device(self):
        """Create a new device using the dialog"""
        logger.info("Creating new device using dialog")
        self.log_widget.append("Creating new device...")
        
        # Use the plugin interface method to show the add device dialog
        new_device = self.add_device_dialog()
        
        if new_device:
            # Device was created and automatically added to the device manager
            logger.info(f"New device created: {new_device.get_property('alias')}")
            self.log_widget.append(f"Created device: {new_device.get_property('alias')}")
            
            # Add sample property if auto_sample is enabled
            if self.settings["auto_sample"]["value"]:
                default_value = self.settings["default_value"]["value"]
                new_device.set_property("sample", default_value)
                self.log_widget.append(f"Added sample property to new device: {default_value}")
        else:
            self.log_widget.append("Device creation cancelled")
            
    def edit_selected_device(self):
        """Edit the selected device using the dialog"""
        selected_devices = self.device_manager.get_selected_devices()
        
        if not selected_devices:
            logger.warning("No device selected to edit")
            self.log_widget.append("No device selected to edit")
            return
            
        device = selected_devices[0]
        logger.info(f"Editing device: {device.get_property('alias')}")
        self.log_widget.append(f"Editing device: {device.get_property('alias')}")
        
        # Use the plugin interface method to show the device properties dialog
        updated_device = self.show_device_properties_dialog(device)
        
        if updated_device:
            # Device was updated
            logger.info(f"Device updated: {updated_device.get_property('alias')}")
            self.log_widget.append(f"Updated device: {updated_device.get_property('alias')}")
        else:
            self.log_widget.append("Device edit cancelled") 