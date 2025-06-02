#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigMate Plugin for NetWORKS

Configuration and template management tool designed for network engineers.
Provides template creation, configuration generation, and comparison capabilities
with intuitive GUI integration.
"""

from loguru import logger
import sys
import os
import json
import functools
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit,
    QSplitter, QTreeWidget, QTreeWidgetItem, QTabWidget, QGroupBox,
    QComboBox, QLineEdit, QCheckBox, QMessageBox, QDialog, QDialogButtonBox,
    QFormLayout, QScrollArea, QFileDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QMenu, QToolButton
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QObject
from PySide6.QtGui import QIcon, QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QAction

# Import the plugin interface
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.core.plugin_interface import PluginInterface

# Add the local lib directory to sys.path for bundled dependencies
plugin_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(plugin_dir, 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

# Import ConfigMate core modules - using absolute imports
try:
    # Try to import as if the plugin directory is in sys.path
    from configmate.core.template_manager import TemplateManager
    from configmate.core.config_generator import ConfigGenerator
    from configmate.core.config_comparator import ConfigComparator
    from configmate.core.variable_detector import VariableDetector
    from configmate.ui.template_editor import TemplateEditorDialog
    from configmate.ui.config_comparison_dialog import ConfigComparisonDialog
    from configmate.ui.config_preview_widget import ConfigPreviewWidget
    from configmate.utils.cisco_syntax import CiscoSyntaxHighlighter
except ImportError:
    # Fallback: construct the path manually
    import sys
    import os
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, plugin_dir)
    
    from core.template_manager import TemplateManager
    from core.config_generator import ConfigGenerator
    from core.config_comparator import ConfigComparator
    from core.variable_detector import VariableDetector
    from ui.template_editor import TemplateEditorDialog
    from ui.config_comparison_dialog import ConfigComparisonDialog
    from ui.config_preview_widget import ConfigPreviewWidget
    from utils.cisco_syntax import CiscoSyntaxHighlighter


def safe_action_wrapper(func):
    """Decorator to safely handle actions without crashing the application"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            action_name = func.__name__
            logger.debug(f"ConfigMate: Starting action {action_name}")
            
            result = func(self, *args, **kwargs)
            logger.debug(f"ConfigMate: Successfully completed action {action_name}")
            return result
        except Exception as e:
            logger.error(f"ConfigMate: Error in action {func.__name__}: {e}", exc_info=True)
            
            # Try to show error in UI
            try:
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage(f"ConfigMate Error: {e}", 5000)
            except Exception:
                pass
            
            return None
    return wrapper


class ConfigMatePlugin(PluginInterface):
    """
    ConfigMate Plugin implementation
    
    Provides comprehensive configuration and template management capabilities:
    - Template creation and management with syntax highlighting
    - Intelligent template generation from device configurations  
    - Configuration generation with variable substitution
    - Side-by-side configuration comparison
    - Integration with command_manager for device operations
    - Batch operations for multiple devices
    """
    
    # Custom signals
    template_created = Signal(str)  # template_name
    template_updated = Signal(str)  # template_name
    template_deleted = Signal(str)  # template_name
    config_generated = Signal(str, str)  # device_id, template_name
    comparison_completed = Signal(list)  # comparison_results
    
    def __init__(self, app=None):
        """Initialize the ConfigMate plugin"""
        super().__init__()
        self.name = "ConfigMate Plugin"
        self.version = "1.0.0"
        self.description = "Configuration and template management tool for network engineers"
        self.author = "NetWORKS Team"
        
        # Store app reference early if provided
        self.app = app
        
        # Internal state
        self._connected_signals = set()
        self._templates_path = None
        self._data_path = None
        
        # Track device selection
        self._selected_devices = []
        
        # Core components
        self.template_manager = None
        self.config_generator = None
        self.config_comparator = None
        self.variable_detector = None
        
        # UI components
        self.config_preview_widget = None
        self.toolbar_actions = []
        self.menu_actions = {}
        self.context_menu_actions = []
        
        # Plugin settings
        self.settings = {
            "default_platform": {
                "name": "Default Platform",
                "description": "Default device platform for new templates",
                "type": "choice",
                "default": "cisco_ios",
                "value": "cisco_ios",
                "choices": ["cisco_ios", "cisco_nxos", "juniper", "generic"]
            },
            "auto_detect_variables": {
                "name": "Auto-Detect Variables",
                "description": "Automatically detect variables when creating templates",
                "type": "bool",
                "default": True,
                "value": True
            },
            "syntax_highlighting": {
                "name": "Syntax Highlighting",
                "description": "Enable syntax highlighting in template editor",
                "type": "bool",
                "default": True,
                "value": True
            },
            "confirm_apply": {
                "name": "Confirm Apply",
                "description": "Always confirm before applying configurations",
                "type": "bool",
                "default": True,
                "value": True
            },
            "max_preview_lines": {
                "name": "Max Preview Lines",
                "description": "Maximum lines to show in configuration preview",
                "type": "int",
                "default": 100,
                "value": 100
            },
            "backup_before_apply": {
                "name": "Backup Before Apply",
                "description": "Create backup before applying configurations",
                "type": "bool",
                "default": True,
                "value": True
            },
            "comparison_context_lines": {
                "name": "Comparison Context Lines",
                "description": "Number of context lines to show in comparisons",
                "type": "int",
                "default": 3,
                "value": 3
            },
            "template_format": {
                "name": "Template Format",
                "description": "Default format for saved templates",
                "type": "choice",
                "default": "text",
                "value": "text",
                "choices": ["text", "jinja2", "simple", "python"]
            }
        }
        
        # Create actions and widgets
        self._create_actions()
    
    def initialize(self, app, plugin_info):
        """Initialize the plugin with application context"""
        logger.info(f"Initializing {self.name} v{self.version}")
        
        # Store app reference and set up plugin interface
        if not hasattr(self, 'app') or self.app is None:
            self.app = app
        self.device_manager = app.device_manager
        self.main_window = app.main_window
        self.config = app.config
        self.plugin_info = plugin_info
        
        # Set up data paths
        self._setup_data_paths()
        
        # Initialize core components
        self._initialize_core_components()
        
        # Create UI components
        self._create_widgets()
        
        # Connect to signals
        self._connect_signals()
        
        # Register context menu actions
        self._register_context_menu_actions()
        
        # Create sample template if no templates exist
        try:
            if self.template_manager and len(self.template_manager.get_template_list()) == 0:
                logger.info("No templates found, creating sample template")
                self.create_sample_template()
        except Exception as e:
            logger.warning(f"Failed to create sample template: {e}")
        
        self._initialized = True
        self.plugin_initialized.emit()
        logger.info(f"ConfigMate plugin initialized successfully")
        
        # Return True to indicate successful initialization
        return True
    
    def _setup_data_paths(self):
        """Set up data storage paths for the plugin"""
        try:
            # Get workspace path from device manager if available
            workspace_path = None
            if hasattr(self, 'device_manager') and self.device_manager:
                workspace_path = self.device_manager.get_workspace_dir()
                logger.debug(f"ConfigMate: Got workspace path from device manager: {workspace_path}")
            
            # Fallback to config setting if device manager not available or returns None
            if not workspace_path:
                workspace_path = Path(self.config.get('workspace_path', 'workspaces/default'))
                logger.debug(f"ConfigMate: Using fallback workspace path: {workspace_path}")
            else:
                workspace_path = Path(workspace_path)
            
            # Create plugin data directories
            self._data_path = workspace_path / 'configmate'
            self._templates_path = self._data_path / 'templates'
            
            # Create directories if they don't exist
            self._data_path.mkdir(parents=True, exist_ok=True)
            self._templates_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"ConfigMate data path: {self._data_path}")
            logger.info(f"ConfigMate templates path: {self._templates_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup data paths: {e}")
            # Fallback to plugin directory
            plugin_dir = Path(__file__).parent
            self._data_path = plugin_dir / 'data'
            self._templates_path = plugin_dir / 'templates'
            self._data_path.mkdir(exist_ok=True)
            self._templates_path.mkdir(exist_ok=True)
    
    def _initialize_core_components(self):
        """Initialize the core ConfigMate components"""
        try:
            # Verify jinja2 is available from local lib
            try:
                import jinja2
                logger.info(f"ConfigMate: Using Jinja2 version {jinja2.__version__} from {jinja2.__file__}")
            except ImportError as e:
                logger.error(f"ConfigMate: Failed to import jinja2: {e}")
                raise
            
            # Initialize template manager
            self.template_manager = TemplateManager(self._templates_path)
            
            # Initialize config generator
            self.config_generator = ConfigGenerator(self.template_manager)
            
            # Initialize config comparator
            self.config_comparator = ConfigComparator()
            
            # Initialize variable detector
            self.variable_detector = VariableDetector()
            
            logger.info("ConfigMate core components initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize core components: {e}")
            # Don't raise - try to continue with partial initialization
            # Set up fallback/dummy components if needed
            if not hasattr(self, 'template_manager') or self.template_manager is None:
                logger.warning("Template manager failed to initialize - some features may not work")
            if not hasattr(self, 'config_generator') or self.config_generator is None:
                logger.warning("Config generator failed to initialize - some features may not work")
            if not hasattr(self, 'config_comparator') or self.config_comparator is None:
                logger.warning("Config comparator failed to initialize - some features may not work")
            if not hasattr(self, 'variable_detector') or self.variable_detector is None:
                logger.warning("Variable detector failed to initialize - some features may not work")
    
    def _create_actions(self):
        """Create toolbar and menu actions"""
        try:
            # Template Management Action
            self.template_action = QAction("Template Manager", self)
            self.template_action.setToolTip("Open template management dialog")
            self.template_action.triggered.connect(self.open_template_manager)
            
            # Quick Generate Action
            self.quick_generate_action = QAction("Quick Generate", self)
            self.quick_generate_action.setToolTip("Generate configuration from template")
            self.quick_generate_action.triggered.connect(self.quick_generate_config)
            
            # Compare Configs Action
            self.compare_action = QAction("Compare Configs", self)
            self.compare_action.setToolTip("Compare device configurations")
            self.compare_action.triggered.connect(self.compare_configurations)
            
            # Test Device Info Action (for debugging)
            self.test_device_info_action = QAction("Test Device Info", self)
            self.test_device_info_action.setToolTip("Show device information for debugging")
            self.test_device_info_action.triggered.connect(self.test_device_info)
            
            # Store actions for toolbar
            self.toolbar_actions = [
                self.template_action,
                self.quick_generate_action,
                self.compare_action,
                self.test_device_info_action
            ]
            
            logger.debug("ConfigMate actions created")
            
        except Exception as e:
            logger.error(f"Failed to create actions: {e}")
    
    def _create_widgets(self):
        """Create UI widgets for the plugin"""
        try:
            # Create config preview widget for right panel
            self.config_preview_widget = ConfigPreviewWidget(self)
            
            logger.debug("ConfigMate widgets created")
            
        except Exception as e:
            logger.error(f"Failed to create widgets: {e}")
    
    def _connect_signals(self):
        """Connect to application signals"""
        try:
            # Connect to device manager signals
            self._connect_to_signal(
                self.device_manager.device_added,
                self.on_device_added,
                "device_added"
            )
            
            self._connect_to_signal(
                self.device_manager.device_removed,
                self.on_device_removed,
                "device_removed"
            )
            
            self._connect_to_signal(
                self.device_manager.device_changed,
                self.on_device_changed,
                "device_changed"
            )
            
            # Connect to selection changed signal - this is the proper way to track device selection
            self._connect_to_signal(
                self.device_manager.selection_changed,
                self.on_selection_changed,
                "selection_changed"
            )
            
            logger.debug("ConfigMate signals connected")
            
        except Exception as e:
            logger.error(f"Failed to connect signals: {e}")
    
    def _connect_to_signal(self, signal, slot, signal_name):
        """Connect to signal and track connection for cleanup"""
        try:
            signal.connect(slot)
            self._connected_signals.add((signal, slot, signal_name))
            return True
        except Exception as e:
            logger.error(f"Error connecting to signal {signal_name}: {e}")
            return False
    
    def _register_context_menu_actions(self):
        """Register context menu actions with the device table"""
        try:
            # Try different ways to access the device table
            device_table = None
            
            # Try common method names
            if hasattr(self.main_window, 'get_device_table'):
                device_table = self.main_window.get_device_table()
            elif hasattr(self.main_window, 'device_table'):
                device_table = self.main_window.device_table
            elif hasattr(self.main_window, 'deviceTable'):
                device_table = self.main_window.deviceTable
            elif hasattr(self.main_window, 'central_widget'):
                # Try to find device table in central widget
                central = self.main_window.central_widget
                if hasattr(central, 'device_table'):
                    device_table = central.device_table
                elif hasattr(central, 'get_device_table'):
                    device_table = central.get_device_table()
            
            if device_table and hasattr(device_table, 'register_context_menu_action'):
                # Generate Configuration action
                device_table.register_context_menu_action(
                    "Generate Configuration",
                    self._on_generate_config_context,
                    priority=50
                )
                
                # Apply Template action
                device_table.register_context_menu_action(
                    "Apply Template",
                    self._on_apply_template_context,
                    priority=51
                )
                
                # Create Template action
                device_table.register_context_menu_action(
                    "Create Template from Device",
                    self._on_create_template_context,
                    priority=52
                )
                
                logger.debug("ConfigMate context menu actions registered successfully")
            else:
                logger.warning("Device table not found or doesn't support context menu registration - skipping context menu actions")
                
        except Exception as e:
            logger.warning(f"Failed to register context menu actions (non-fatal): {e}")
            # Don't let this failure stop plugin initialization
    
    def cleanup(self):
        """Clean up plugin resources"""
        logger.info("Cleaning up ConfigMate plugin")
        
        # Disconnect signals safely
        for signal, slot, signal_name in self._connected_signals:
            try:
                signal.disconnect(slot)
            except Exception as e:
                logger.debug(f"Error disconnecting {signal_name}: {e}")
        
        self._connected_signals.clear()
        
        # Save any pending data
        if self.template_manager:
            try:
                self.template_manager.save_all()
            except Exception as e:
                logger.error(f"Error saving templates during cleanup: {e}")
        
        self.plugin_cleaned_up.emit()
        logger.info("ConfigMate plugin cleanup completed")
    
    # Plugin interface methods
    
    def get_toolbar_actions(self):
        """Return actions for the toolbar"""
        return self.toolbar_actions
    
    def get_menu_actions(self):
        """Return actions for the main menu"""
        # Try to find existing Tools menu
        tools_menu = self._find_existing_menu("Tools")
        return {
            tools_menu: self.toolbar_actions
        }
    
    def get_device_panels(self):
        """Return panels for device details"""
        # All functionality moved to Template Manager dialog
        return []
    
    def get_dock_widgets(self):
        """Return dock widgets for main window"""
        return []  # Using right panel widget instead
    
    def get_device_table_columns(self):
        """Return custom columns for device table"""
        return [
            {
                "id": "config_status",
                "name": "Config Status",
                "tooltip": "Configuration generation status",
                "get_value": self._get_config_status_value
            }
        ]
    
    def get_settings(self):
        """Return plugin settings"""
        return self.settings
    
    def update_setting(self, setting_id, value):
        """Update a plugin setting"""
        if setting_id in self.settings:
            self.settings[setting_id]["value"] = value
            logger.debug(f"ConfigMate setting updated: {setting_id} = {value}")
            
            # Apply setting changes
            if setting_id == "syntax_highlighting":
                self._update_syntax_highlighting(value)
            elif setting_id == "default_platform":
                self._update_default_platform(value)
    
    # Event handlers
    
    def on_device_added(self, device):
        """Handle device added event"""
        logger.debug(f"ConfigMate: Device added - {device.get_property('name', 'Unknown')}")
        
        # Update config preview if this device is selected
        if self.config_preview_widget:
            self.config_preview_widget.refresh_device_list()
    
    def on_device_removed(self, device):
        """Handle device removed event"""
        logger.debug(f"ConfigMate: Device removed - {device.get_property('name', 'Unknown')}")
        
        # Update config preview
        if self.config_preview_widget:
            self.config_preview_widget.refresh_device_list()
    
    def on_device_changed(self, device):
        """Handle device changed event"""
        logger.debug(f"ConfigMate: Device changed - {device.get_property('name', 'Unknown')}")
        
        # Update config preview if needed
        if self.config_preview_widget:
            self.config_preview_widget.on_device_changed(device)
    
    def on_selection_changed(self, devices):
        """Handle device selection changed event"""
        self._selected_devices = devices if devices else []
        logger.debug(f"ConfigMate: Device selection changed - {len(self._selected_devices)} devices selected")
        
        # Update config preview widget with new selection
        if self.config_preview_widget:
            if hasattr(self.config_preview_widget, 'set_selected_devices'):
                self.config_preview_widget.set_selected_devices(self._selected_devices)
            elif hasattr(self.config_preview_widget, 'refresh_device_list'):
                self.config_preview_widget.refresh_device_list()
    
    # Action handlers
    
    @safe_action_wrapper
    def open_template_manager(self):
        """Open the template management dialog"""
        # Ensure we have the latest device selection
        self._update_selection_if_needed()
        
        dialog = TemplateEditorDialog(self, template_name=None, parent=self.main_window)
        dialog.exec()
    
    def _update_selection_if_needed(self):
        """Update selection from device manager if needed"""
        try:
            # This ensures we have the latest selection in case the signal wasn't received
            if hasattr(self.device_manager, 'get_selected_devices'):
                current_selection = self.device_manager.get_selected_devices()
                if current_selection is not None:
                    self._selected_devices = current_selection
                    logger.debug(f"ConfigMate: Updated selection to {len(self._selected_devices)} devices")
        except Exception as e:
            logger.debug(f"ConfigMate: Could not update selection directly: {e}")
    
    @safe_action_wrapper
    def test_device_info(self):
        """Test device information extraction and display"""
        selected_devices = self._get_selected_devices()
        if not selected_devices:
            QMessageBox.information(
                self.main_window,
                "No Selection",
                "Please select one or more devices to test device information extraction."
            )
            return
        
        # Show device information for all selected devices
        info_text = []
        for i, device in enumerate(selected_devices):
            info_text.append(f"=== Device {i+1} ===")
            info_text.append(self.get_device_info_summary(device))
            info_text.append("")
            
            # Test template variable extraction
            if self.template_manager and self.config_generator:
                templates = self.template_manager.get_template_list()
                if templates:
                    template_name = templates[0]
                    info_text.append(f"--- Template Variables for '{template_name}' ---")
                    variables = self.config_generator.get_template_variables_for_device(device, template_name)
                    if variables:
                        for var_name, var_value in variables.items():
                            info_text.append(f"  {var_name}: {var_value}")
                    else:
                        info_text.append("  No variables extracted")
                    info_text.append("")
        
        # Show in dialog
        dialog = QMessageBox(self.main_window)
        dialog.setWindowTitle("Device Information Test")
        dialog.setText("Device Information and Variable Extraction Test")
        dialog.setDetailedText("\n".join(info_text))
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()
    
    @safe_action_wrapper
    def quick_generate_config(self):
        """Quick generate configuration for selected devices"""
        selected_devices = self._get_selected_devices()
        if not selected_devices:
            QMessageBox.information(
                self.main_window,
                "No Selection",
                "Please select one or more devices to generate configurations.\n\n"
                "Tip: If no devices are selected, the plugin will use all available devices for testing."
            )
            return
        
        # Show template selection dialog
        templates = self.template_manager.get_template_list()
        if not templates:
            # Try to create sample template
            if self.create_sample_template():
                templates = self.template_manager.get_template_list()
            
            if not templates:
                QMessageBox.information(
                    self.main_window,
                    "No Templates",
                    "No templates available. Please create a template first using the Template Manager."
                )
                return
        
        # Use the first template for quick generation
        template_name = templates[0]
        
        # Generate configurations with detailed feedback
        results = []
        for device in selected_devices:
            try:
                device_name = device.get_property('name', 'Unknown')
                
                # Get variables for this device
                variables = self.config_generator.get_template_variables_for_device(device, template_name)
                
                # Generate configuration
                config = self.config_generator.generate_config(device, template_name, variables)
                if config:
                    results.append(f"✓ Generated config for '{device_name}' ({len(config.splitlines())} lines)")
                    logger.info(f"Generated config for device {device_name}")
                    self.config_generated.emit(device.device_id, template_name)
                else:
                    results.append(f"✗ Failed to generate config for '{device_name}'")
                    
            except Exception as e:
                device_name = device.get_property('name', 'Unknown')
                results.append(f"✗ Error generating config for '{device_name}': {e}")
                logger.error(f"Failed to generate config for device {device_name}: {e}")
        
        # Show results
        result_text = f"Configuration Generation Results (Template: {template_name}):\n\n" + "\n".join(results)
        QMessageBox.information(
            self.main_window,
            "Generation Complete",
            result_text
        )
    
    @safe_action_wrapper
    def compare_configurations(self):
        """Compare configurations between selected devices"""
        selected_devices = self._get_selected_devices()
        if len(selected_devices) < 2:
            QMessageBox.information(
                self.main_window,
                "Select Devices",
                "Please select at least two devices to compare configurations."
            )
            return
        
        # Open comparison dialog
        dialog = ConfigComparisonDialog(selected_devices, self, self.main_window)
        dialog.exec()
    
    # Context menu handlers
    
    @safe_action_wrapper
    def _on_generate_config_context(self, device_or_devices):
        """Handle generate config context menu action"""
        devices = device_or_devices if isinstance(device_or_devices, list) else [device_or_devices]
        
        # Show template selection and generate
        templates = self.template_manager.get_template_list()
        if not templates:
            QMessageBox.information(
                self.main_window,
                "No Templates",
                "No templates available. Please create a template first."
            )
            return
        
        # For now, show preview in the right panel widget
        if self.config_preview_widget and devices:
            self.config_preview_widget.set_selected_devices(devices)
    
    @safe_action_wrapper 
    def _on_apply_template_context(self, device_or_devices):
        """Handle apply template context menu action"""
        devices = device_or_devices if isinstance(device_or_devices, list) else [device_or_devices]
        
        # Show confirmation dialog and apply
        if self.get_setting_value("confirm_apply"):
            reply = QMessageBox.question(
                self.main_window,
                "Confirm Apply",
                f"Apply configuration to {len(devices)} device(s)?\n\n"
                "This will modify the device configuration.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Apply configurations (placeholder for now)
        logger.info(f"Apply template requested for {len(devices)} devices")
    
    @safe_action_wrapper
    def _on_create_template_context(self, device_or_devices):
        """Handle create template from device context menu action"""
        devices = device_or_devices if isinstance(device_or_devices, list) else [device_or_devices]
        
        if not devices:
            return
        
        device = devices[0]  # Use first device
        
        # Get device configuration from command manager
        config_text = self._get_device_config(device)
        if not config_text:
            QMessageBox.warning(
                self.main_window,
                "No Configuration",
                "Could not retrieve configuration from device.\n"
                "Make sure the device is accessible and try running 'show running-config' first."
            )
            return
        
        # Open template editor with detected variables
        dialog = TemplateEditorDialog(self, self.main_window)
        dialog.create_from_config(device, config_text)
        dialog.exec()
    
    # Helper methods
    
    def _get_selected_devices(self):
        """Get currently selected devices from stored selection"""
        try:
            # Return stored selection if available
            if self._selected_devices:
                logger.debug(f"ConfigMate: Returning {len(self._selected_devices)} selected devices")
                return self._selected_devices
            
            # Fallback: if no selection, try to get all devices (limited for safety)
            if hasattr(self.device_manager, 'get_all_devices'):
                all_devices = self.device_manager.get_all_devices()
                if all_devices:
                    logger.info(f"ConfigMate: No selection, using first 3 of {len(all_devices)} devices for testing")
                    return all_devices[:3]  # Limit for safety
            
            logger.warning("ConfigMate: No devices selected and no devices available")
            return []
            
        except Exception as e:
            logger.error(f"ConfigMate: Failed to get selected devices: {e}")
            return []
    
    def _get_device_config(self, device):
        """Get device configuration using command manager plugin
        
        This method retrieves device configuration by:
        1. First checking for cached command outputs (show running-config, etc.)
        2. If no cached output is found, attempting to run the command directly
        
        Fixed: Access plugin manager through self.app.plugin_manager instead of 
               non-existent self.plugin_manager attribute.
        """
        try:
            # Get command manager plugin through the app's plugin manager
            if not hasattr(self, 'app') or not self.app:
                logger.error("App reference not available")
                return None
                
            if not hasattr(self.app, 'plugin_manager') or not self.app.plugin_manager:
                logger.error("Plugin manager not available")
                return None
                
            command_manager = self.app.plugin_manager.get_plugin("command_manager")
            if not command_manager:
                logger.error("Command manager plugin not found")
                return None
                
            # Get the actual plugin instance
            if hasattr(command_manager, 'instance') and command_manager.instance:
                command_manager_instance = command_manager.instance
            else:
                logger.error("Command manager plugin instance not available")
                return None
            
            # Try to get cached show run output first
            # Check different possible command IDs
            command_ids_to_try = [
                "show running-config",
                "show_run", 
                "Show Running Config",
                "show run"
            ]
            
            if hasattr(command_manager_instance, 'get_command_outputs'):
                for command_id in command_ids_to_try:
                    try:
                        outputs = command_manager_instance.get_command_outputs(device.device_id, command_id)
                        if outputs and isinstance(outputs, dict):
                            # Get the most recent output (latest timestamp)
                            timestamps = list(outputs.keys())
                            if timestamps:
                                latest_timestamp = max(timestamps)
                                output_data = outputs[latest_timestamp]
                                if isinstance(output_data, dict) and 'output' in output_data:
                                    logger.info(f"Found cached command output for {command_id}")
                                    return output_data['output']
                                elif isinstance(output_data, str):
                                    # Sometimes the output might be stored directly as string
                                    logger.info(f"Found cached command output for {command_id}")
                                    return output_data
                    except Exception as e:
                        logger.debug(f"Error checking command ID {command_id}: {e}")
                        continue
                
                # Also try getting all outputs for the device to see what's available
                try:
                    all_outputs = command_manager_instance.get_command_outputs(device.device_id)
                    if all_outputs:
                        logger.info(f"Available command outputs for device {device.device_id}: {list(all_outputs.keys())}")
                        # Look for any command that might contain "show" and "run" or "config"
                        for cmd_id, cmd_outputs in all_outputs.items():
                            if any(keyword in cmd_id.lower() for keyword in ['show', 'run', 'config']):
                                if cmd_outputs and isinstance(cmd_outputs, dict):
                                    timestamps = list(cmd_outputs.keys())
                                    if timestamps:
                                        latest_timestamp = max(timestamps)
                                        output_data = cmd_outputs[latest_timestamp]
                                        if isinstance(output_data, dict) and 'output' in output_data:
                                            logger.info(f"Using output from similar command: {cmd_id}")
                                            return output_data['output']
                except Exception as e:
                    logger.debug(f"Error getting all outputs: {e}")
            
            # If no cached output, try to run command
            if hasattr(command_manager_instance, 'run_command'):
                logger.info("No cached configuration found, attempting to run show running-config")
                result = command_manager_instance.run_command(device, "show running-config")
                if result and result.get('success'):
                    return result.get('output', '')
                else:
                    logger.warning(f"Failed to run show running-config: {result}")
            
            logger.warning("No method available to retrieve device configuration")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get device config: {e}")
            return None
    
    def _get_config_status_value(self, device):
        """Get configuration status value for device table column"""
        try:
            # Check if device has generated configs
            device_id = device.device_id
            config_file = self._data_path / f"{device_id}_last_config.txt"
            
            if config_file.exists():
                return "Generated"
            else:
                return "None"
                
        except Exception as e:
            logger.debug(f"Error getting config status: {e}")
            return "Unknown"
    
    def _find_existing_menu(self, menu_name):
        """Find existing menu by name (case-insensitive)"""
        try:
            if hasattr(self.main_window, 'menuBar'):
                menubar = self.main_window.menuBar()
                for action in menubar.actions():
                    if action.text().lower().replace('&', '') == menu_name.lower():
                        return action.text()
            return menu_name
        except Exception:
            return menu_name
    
    def _update_syntax_highlighting(self, enabled):
        """Update syntax highlighting setting"""
        # Implementation would update all syntax highlighters
        logger.debug(f"Syntax highlighting {'enabled' if enabled else 'disabled'}")
    
    def _update_default_platform(self, platform):
        """Update default platform setting"""
        logger.debug(f"Default platform set to: {platform}")
    
    def get_setting_value(self, setting_id):
        """Get the current value of a setting"""
        if setting_id in self.settings:
            return self.settings[setting_id]["value"]
        return None

    def get_device_info_summary(self, device) -> str:
        """Get a summary of device information for debugging and testing"""
        try:
            info_lines = []
            info_lines.append(f"Device Information:")
            info_lines.append(f"  ID: {getattr(device, 'device_id', 'Unknown')}")
            
            # Common properties to check
            common_props = [
                'name', 'hostname', 'device_name',
                'ip_address', 'ip', 'management_ip', 'mgmt_ip',
                'mac_address', 'mac',
                'device_type', 'type', 'platform',
                'description', 'desc',
                'location', 'site',
                'contact', 'owner',
                'domain', 'domain_name',
                'vlan', 'vlan_id',
                'interface', 'mgmt_interface',
                'gateway', 'default_gateway',
                'dns_server', 'dns1', 'primary_dns',
                'ntp_server', 'ntp1', 'primary_ntp',
                'snmp_community', 'snmp_ro_community'
            ]
            
            found_props = {}
            for prop in common_props:
                value = device.get_property(prop)
                if value is not None and value != '':
                    found_props[prop] = value
            
            if found_props:
                info_lines.append(f"  Found Properties:")
                for prop, value in found_props.items():
                    info_lines.append(f"    {prop}: {value}")
            else:
                info_lines.append(f"  No common properties found")
            
            # Check all properties
            if hasattr(device, 'properties'):
                all_props = device.properties
                info_lines.append(f"  All Properties ({len(all_props)}):")
                for prop, value in all_props.items():
                    if prop not in found_props:  # Don't repeat
                        info_lines.append(f"    {prop}: {value}")
            
            return '\n'.join(info_lines)
            
        except Exception as e:
            return f"Error getting device info: {e}"
    
    def create_sample_template(self):
        """Create a sample template for testing"""
        try:
            if not self.template_manager:
                logger.error("Template manager not available")
                return False
            
            sample_template_content = """!
! Sample Cisco IOS Configuration Template
! Generated by ConfigMate
!
hostname <HOSTNAME>
!
! Management Interface
interface <MGMT_INTERFACE>
 description Management Interface
 ip address <IP_ADDRESS> <SUBNET_MASK>
 no shutdown
!
! Default Gateway
ip route 0.0.0.0 0.0.0.0 <GATEWAY>
!
! DNS Configuration
ip name-server <DNS_SERVER>
ip domain-name <DOMAIN>
!
! NTP Configuration
ntp server <NTP_SERVER>
!
! SNMP Configuration
snmp-server community <SNMP_COMMUNITY> RO
snmp-server location <LOCATION>
snmp-server contact <CONTACT>
!
! Banner
banner motd ^
Device: <HOSTNAME>
Location: <LOCATION>
Contact: <CONTACT>
^
!
end"""

            # Create the sample template
            self.template_manager.create_template(
                name="sample_cisco_basic_text",
                content=sample_template_content,
                platform="cisco_ios",
                description="Basic Cisco IOS configuration template with text placeholders",
                variables={
                    'hostname': 'SW01',
                    'mgmt_interface': 'GigabitEthernet0/0',
                    'ip_address': '192.168.1.100',
                    'subnet_mask': '255.255.255.0',
                    'gateway': '192.168.1.1',
                    'dns_server': '8.8.8.8',
                    'domain': 'example.com',
                    'ntp_server': 'pool.ntp.org',
                    'snmp_community': 'public',
                    'location': 'Server Room',
                    'contact': 'admin@example.com'
                }
            )
            
            logger.info("Created sample template: sample_cisco_basic_text")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create sample template: {e}")
            return False


# Plugin entry point function
def create_plugin():
    """Create and return a new instance of the ConfigMate plugin"""
    return ConfigMatePlugin() 