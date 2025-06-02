#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Preview Widget for ConfigMate Plugin

Provides a right panel widget for configuration preview, template selection,
and quick generation operations. Integrates with the main window's right panel area.
"""

from loguru import logger
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTextEdit, QGroupBox, QSplitter, QScrollArea, QFormLayout, QLineEdit,
    QCheckBox, QProgressBar, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QTextCharFormat, QColor


class ConfigPreviewWidget(QWidget):
    """
    Configuration preview widget for the right panel
    
    Provides functionality for:
    - Template selection and preview
    - Device selection for configuration generation
    - Variable editing and preview
    - Quick generation and apply operations
    - Integration with ConfigMate plugin
    """
    
    # Signals
    template_selected = Signal(str)  # template_name
    config_generated = Signal(str, str)  # device_id, template_name
    apply_requested = Signal(str, str)  # device_id, config_text
    
    def __init__(self, plugin, parent=None):
        """
        Initialize the configuration preview widget
        
        Args:
            plugin: ConfigMate plugin instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.plugin = plugin
        self.selected_devices = []
        self.current_template = None
        self.current_config = ""
        
        # Set up the UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Refresh data
        self._refresh_templates()
        
        logger.debug("ConfigPreviewWidget initialized")
    
    def _setup_ui(self):
        """Set up the user interface"""
        self.setMinimumWidth(300)
        self.setMaximumWidth(500)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("ConfigMate")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Template selection group
        template_group = self._create_template_group()
        layout.addWidget(template_group)
        
        # Device selection group
        device_group = self._create_device_group()
        layout.addWidget(device_group)
        
        # Variables group
        variables_group = self._create_variables_group()
        layout.addWidget(variables_group)
        
        # Preview group
        preview_group = self._create_preview_group()
        layout.addWidget(preview_group)
        
        # Action buttons
        buttons_layout = self._create_action_buttons()
        layout.addLayout(buttons_layout)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        # Add stretch to push everything to top
        layout.addStretch()
    
    def _create_template_group(self) -> QGroupBox:
        """Create template selection group"""
        group = QGroupBox("Template")
        layout = QVBoxLayout(group)
        
        # Template combo box
        self.template_combo = QComboBox()
        self.template_combo.setToolTip("Select a configuration template")
        layout.addWidget(self.template_combo)
        
        # Template info
        self.template_info_label = QLabel("No template selected")
        self.template_info_label.setWordWrap(True)
        self.template_info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.template_info_label)
        
        # Template actions
        template_actions = QHBoxLayout()
        
        self.new_template_btn = QPushButton("New")
        self.new_template_btn.setToolTip("Create a new template")
        template_actions.addWidget(self.new_template_btn)
        
        self.edit_template_btn = QPushButton("Edit")
        self.edit_template_btn.setToolTip("Edit selected template")
        self.edit_template_btn.setEnabled(False)
        template_actions.addWidget(self.edit_template_btn)
        
        layout.addLayout(template_actions)
        
        return group
    
    def _create_device_group(self) -> QGroupBox:
        """Create device selection group"""
        group = QGroupBox("Target Device(s)")
        layout = QVBoxLayout(group)
        
        # Selected devices label
        self.selected_devices_label = QLabel("No devices selected")
        self.selected_devices_label.setWordWrap(True)
        layout.addWidget(self.selected_devices_label)
        
        # Device selection button
        self.select_devices_btn = QPushButton("Select Devices")
        self.select_devices_btn.setToolTip("Select devices from the device table")
        layout.addWidget(self.select_devices_btn)
        
        return group
    
    def _create_variables_group(self) -> QGroupBox:
        """Create variables editing group"""
        group = QGroupBox("Variables")
        layout = QVBoxLayout(group)
        
        # Variables scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        
        self.variables_widget = QWidget()
        self.variables_layout = QFormLayout(self.variables_widget)
        scroll.setWidget(self.variables_widget)
        
        layout.addWidget(scroll)
        
        # Auto-fill button
        self.auto_fill_btn = QPushButton("Auto-fill from Device")
        self.auto_fill_btn.setToolTip("Automatically fill variables from selected device properties")
        self.auto_fill_btn.setEnabled(False)
        layout.addWidget(self.auto_fill_btn)
        
        return group
    
    def _create_preview_group(self) -> QGroupBox:
        """Create configuration preview group"""
        group = QGroupBox("Preview")
        layout = QVBoxLayout(group)
        
        # Preview text area
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        self.preview_text.setPlaceholderText("Configuration preview will appear here...")
        
        # Use monospace font for configuration text
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.preview_text.setFont(font)
        
        layout.addWidget(self.preview_text)
        
        # Preview options
        preview_options = QHBoxLayout()
        
        self.auto_preview_cb = QCheckBox("Auto-preview")
        self.auto_preview_cb.setToolTip("Automatically update preview when changes are made")
        self.auto_preview_cb.setChecked(True)
        preview_options.addWidget(self.auto_preview_cb)
        
        self.refresh_preview_btn = QPushButton("Refresh")
        self.refresh_preview_btn.setToolTip("Manually refresh the configuration preview")
        preview_options.addWidget(self.refresh_preview_btn)
        
        layout.addLayout(preview_options)
        
        return group
    
    def _create_action_buttons(self) -> QHBoxLayout:
        """Create action buttons layout"""
        layout = QHBoxLayout()
        
        # Generate button
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setToolTip("Generate configuration from template")
        self.generate_btn.setEnabled(False)
        layout.addWidget(self.generate_btn)
        
        # Apply button
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setToolTip("Apply generated configuration to device")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        layout.addWidget(self.apply_btn)
        
        return layout
    
    def _connect_signals(self):
        """Connect widget signals"""
        try:
            # Template selection
            self.template_combo.currentTextChanged.connect(self._on_template_selected)
            
            # Template actions
            self.new_template_btn.clicked.connect(self._on_new_template)
            self.edit_template_btn.clicked.connect(self._on_edit_template)
            
            # Device selection
            self.select_devices_btn.clicked.connect(self._on_select_devices)
            
            # Variables
            self.auto_fill_btn.clicked.connect(self._on_auto_fill_variables)
            
            # Preview
            self.auto_preview_cb.stateChanged.connect(self._on_auto_preview_changed)
            self.refresh_preview_btn.clicked.connect(self._on_refresh_preview)
            
            # Actions
            self.generate_btn.clicked.connect(self._on_generate)
            self.apply_btn.clicked.connect(self._on_apply)
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
    
    def _refresh_templates(self):
        """Refresh the template list"""
        try:
            self.template_combo.clear()
            
            if self.plugin.template_manager:
                templates = self.plugin.template_manager.get_template_list()
                if templates:
                    self.template_combo.addItems(templates)
                else:
                    self.template_combo.addItem("No templates available")
            else:
                self.template_combo.addItem("Template manager not available")
            
        except Exception as e:
            logger.error(f"Error refreshing templates: {e}")
    
    def _update_template_info(self, template_name: str):
        """Update template information display"""
        try:
            if not template_name or template_name == "No templates available":
                self.template_info_label.setText("No template selected")
                self.edit_template_btn.setEnabled(False)
                return
            
            if self.plugin.template_manager:
                template_info = self.plugin.template_manager.get_template_info(template_name)
                if template_info:
                    info_text = f"Platform: {template_info.get('platform', 'Unknown')}\n"
                    info_text += f"Variables: {template_info.get('variable_count', 0)}\n"
                    info_text += f"Lines: {template_info.get('content_lines', 0)}"
                    self.template_info_label.setText(info_text)
                    self.edit_template_btn.setEnabled(True)
                else:
                    self.template_info_label.setText("Template information not available")
                    self.edit_template_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"Error updating template info: {e}")
    
    def _update_variables_form(self, template_name: str):
        """Update the variables form based on selected template"""
        try:
            # Clear existing variables
            for i in reversed(range(self.variables_layout.count())):
                child = self.variables_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            if not template_name or not self.plugin.template_manager:
                return
            
            template = self.plugin.template_manager.get_template(template_name)
            if not template:
                return
            
            # Get template variables
            variables = template.get_variables_from_content()
            
            # Create form fields for each variable
            for var_name in variables:
                line_edit = QLineEdit()
                line_edit.setPlaceholderText(f"Enter {var_name}")
                line_edit.setObjectName(f"var_{var_name}")
                
                # Set default value if available
                default_value = template.variables.get(var_name, "")
                if default_value:
                    line_edit.setText(str(default_value))
                
                # Connect to auto-preview
                if self.auto_preview_cb.isChecked():
                    line_edit.textChanged.connect(self._on_variable_changed)
                
                self.variables_layout.addRow(var_name + ":", line_edit)
            
            # Enable auto-fill if devices are selected
            self.auto_fill_btn.setEnabled(bool(self.selected_devices))
            
        except Exception as e:
            logger.error(f"Error updating variables form: {e}")
    
    def _get_current_variables(self) -> Dict[str, str]:
        """Get current variable values from the form"""
        variables = {}
        
        try:
            for i in range(self.variables_layout.count()):
                item = self.variables_layout.itemAt(i)
                if item and hasattr(item, 'widget'):
                    widget = item.widget()
                    if isinstance(widget, QLineEdit) and widget.objectName().startswith("var_"):
                        var_name = widget.objectName()[4:]  # Remove "var_" prefix
                        variables[var_name] = widget.text()
        
        except Exception as e:
            logger.error(f"Error getting current variables: {e}")
        
        return variables
    
    def _update_preview(self):
        """Update the configuration preview"""
        try:
            if not self.current_template or not self.selected_devices:
                self.preview_text.clear()
                self.preview_text.setPlaceholderText("Select template and device to see preview...")
                return
            
            device = self.selected_devices[0]  # Use first selected device
            variables = self._get_current_variables()
            
            # Generate preview
            if self.plugin.config_generator:
                config = self.plugin.config_generator.preview_config(
                    device, self.current_template, variables
                )
                
                if config:
                    # Show first N lines based on settings
                    max_lines = self.plugin.get_setting_value("max_preview_lines") or 100
                    lines = config.splitlines()
                    
                    if len(lines) > max_lines:
                        preview_lines = lines[:max_lines]
                        preview_lines.append(f"\n... ({len(lines) - max_lines} more lines)")
                        config = '\n'.join(preview_lines)
                    
                    self.preview_text.setPlainText(config)
                    self.current_config = config
                    
                    # Enable generation button
                    self.generate_btn.setEnabled(True)
                else:
                    self.preview_text.setPlainText("Error generating configuration preview")
                    self.generate_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.preview_text.setPlainText(f"Preview error: {e}")
    
    # Signal handlers
    
    def _on_template_selected(self, template_name: str):
        """Handle template selection"""
        try:
            self.current_template = template_name if template_name != "No templates available" else None
            self._update_template_info(template_name)
            self._update_variables_form(template_name)
            
            if self.auto_preview_cb.isChecked():
                self._update_preview()
            
            self.template_selected.emit(template_name)
            
        except Exception as e:
            logger.error(f"Error handling template selection: {e}")
    
    def _on_new_template(self):
        """Handle new template button"""
        try:
            # Open template editor dialog
            self.plugin.open_template_manager()
            
            # Refresh templates after dialog closes
            QTimer.singleShot(1000, self._refresh_templates)
            
        except Exception as e:
            logger.error(f"Error opening new template dialog: {e}")
    
    def _on_edit_template(self):
        """Handle edit template button"""
        try:
            if self.current_template:
                # Open template editor with current template
                self.plugin.open_template_manager()
                
                # Refresh after editing
                QTimer.singleShot(1000, self._refresh_templates)
            
        except Exception as e:
            logger.error(f"Error opening edit template dialog: {e}")
    
    def _on_select_devices(self):
        """Handle select devices button"""
        try:
            # Get currently selected devices from device table
            selected = self.plugin._get_selected_devices()
            if selected:
                self.set_selected_devices(selected)
            else:
                QMessageBox.information(
                    self,
                    "No Selection",
                    "Please select one or more devices from the device table first."
                )
            
        except Exception as e:
            logger.error(f"Error selecting devices: {e}")
    
    def _on_auto_fill_variables(self):
        """Handle auto-fill variables button"""
        try:
            if not self.selected_devices or not self.current_template:
                return
            
            device = self.selected_devices[0]
            
            # Get variable suggestions from config generator
            if self.plugin.config_generator:
                variables = self.plugin.config_generator.get_template_variables_for_device(
                    device, self.current_template
                )
                
                # Fill form fields
                for var_name, value in variables.items():
                    widget = self.variables_widget.findChild(QLineEdit, f"var_{var_name}")
                    if widget:
                        widget.setText(str(value))
                
                if self.auto_preview_cb.isChecked():
                    self._update_preview()
                
                self.status_label.setText("Variables auto-filled from device properties")
            
        except Exception as e:
            logger.error(f"Error auto-filling variables: {e}")
    
    def _on_auto_preview_changed(self, state):
        """Handle auto-preview checkbox change"""
        try:
            if state == Qt.CheckState.Checked:
                # Connect all variable fields to preview update
                for i in range(self.variables_layout.count()):
                    item = self.variables_layout.itemAt(i)
                    if item and hasattr(item, 'widget'):
                        widget = item.widget()
                        if isinstance(widget, QLineEdit):
                            widget.textChanged.connect(self._on_variable_changed)
                
                # Update preview immediately
                self._update_preview()
            else:
                # Disconnect variable fields
                for i in range(self.variables_layout.count()):
                    item = self.variables_layout.itemAt(i)
                    if item and hasattr(item, 'widget'):
                        widget = item.widget()
                        if isinstance(widget, QLineEdit):
                            try:
                                widget.textChanged.disconnect(self._on_variable_changed)
                            except:
                                pass
            
        except Exception as e:
            logger.error(f"Error handling auto-preview change: {e}")
    
    def _on_variable_changed(self):
        """Handle variable field change"""
        try:
            if self.auto_preview_cb.isChecked():
                # Debounce preview updates
                if hasattr(self, '_preview_timer'):
                    self._preview_timer.stop()
                
                self._preview_timer = QTimer()
                self._preview_timer.setSingleShot(True)
                self._preview_timer.timeout.connect(self._update_preview)
                self._preview_timer.start(500)  # 500ms delay
            
        except Exception as e:
            logger.error(f"Error handling variable change: {e}")
    
    def _on_refresh_preview(self):
        """Handle refresh preview button"""
        try:
            self._update_preview()
            self.status_label.setText("Preview refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing preview: {e}")
    
    def _on_generate(self):
        """Handle generate button"""
        try:
            if not self.current_template or not self.selected_devices:
                return
            
            variables = self._get_current_variables()
            
            # Generate for all selected devices
            for device in self.selected_devices:
                if self.plugin.config_generator:
                    config = self.plugin.config_generator.generate_config(
                        device, self.current_template, variables
                    )
                    
                    if config:
                        self.config_generated.emit(device.device_id, self.current_template)
                        logger.info(f"Generated config for device {device.get_property('name')}")
                    else:
                        logger.error(f"Failed to generate config for device {device.get_property('name')}")
            
            self.status_label.setText(f"Generated configurations for {len(self.selected_devices)} device(s)")
            self.apply_btn.setEnabled(True)
            
        except Exception as e:
            logger.error(f"Error generating configuration: {e}")
            self.status_label.setText(f"Generation error: {e}")
    
    def _on_apply(self):
        """Handle apply button"""
        try:
            if not self.current_config or not self.selected_devices:
                return
            
            # Confirm application
            reply = QMessageBox.question(
                self,
                "Confirm Apply",
                f"Apply configuration to {len(self.selected_devices)} device(s)?\n\n"
                "This will modify the device configuration.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                for device in self.selected_devices:
                    self.apply_requested.emit(device.device_id, self.current_config)
                
                self.status_label.setText("Configuration apply requested")
            
        except Exception as e:
            logger.error(f"Error applying configuration: {e}")
            self.status_label.setText(f"Apply error: {e}")
    
    # Public methods
    
    def set_selected_devices(self, devices: List[Any]):
        """Set the selected devices"""
        try:
            self.selected_devices = devices
            
            if devices:
                device_names = [device.get_property('name', 'Unknown') for device in devices]
                if len(device_names) > 3:
                    display_text = f"{', '.join(device_names[:3])} and {len(device_names) - 3} more"
                else:
                    display_text = ', '.join(device_names)
                
                self.selected_devices_label.setText(display_text)
                self.auto_fill_btn.setEnabled(bool(self.current_template))
                
                if self.auto_preview_cb.isChecked():
                    self._update_preview()
            else:
                self.selected_devices_label.setText("No devices selected")
                self.auto_fill_btn.setEnabled(False)
                self.generate_btn.setEnabled(False)
                self.apply_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"Error setting selected devices: {e}")
    
    def refresh_device_list(self):
        """Refresh the device list (called when devices are added/removed)"""
        # Clear selection if devices no longer exist
        if self.selected_devices:
            # This would need to check if devices still exist in device manager
            pass
    
    def on_device_changed(self, device):
        """Handle device property changes"""
        try:
            if device in self.selected_devices:
                # Update device info if it's one of our selected devices
                if self.auto_preview_cb.isChecked():
                    self._update_preview()
            
        except Exception as e:
            logger.error(f"Error handling device change: {e}") 