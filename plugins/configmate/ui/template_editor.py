#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Template Editor Dialog for ConfigMate Plugin

Provides a comprehensive dialog for creating, editing, and managing configuration templates.
Includes syntax highlighting, variable detection, and template validation.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from loguru import logger
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QTextEdit, QLineEdit, QComboBox, QLabel, QPushButton, QGroupBox,
    QSplitter, QTabWidget, QWidget, QListWidget, QListWidgetItem,
    QMessageBox, QFileDialog, QCheckBox, QSpinBox, QTextBrowser,
    QDialogButtonBox, QProgressBar, QScrollArea, QTableWidget, QHeaderView,
    QMenu, QAction, QTableWidgetItem
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon

# Import syntax highlighter - try absolute import first
try:
    from configmate.utils.cisco_syntax import CiscoSyntaxHighlighter
except ImportError:
    # Fallback to relative path
    import sys
    import os
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, plugin_dir)
    from utils.cisco_syntax import CiscoSyntaxHighlighter


class TemplateEditorDialog(QDialog):
    """
    Template editor dialog for creating and editing configuration templates
    
    Features:
    - Syntax-highlighted template editor
    - Variable detection and management
    - Template validation and preview
    - Platform-specific templates
    - Import/export functionality
    """
    
    # Signals
    template_saved = Signal(str)  # template_name
    template_deleted = Signal(str)  # template_name
    
    def __init__(self, plugin, template_name=None, parent=None):
        """Initialize the template editor dialog"""
        super().__init__(parent)
        self.plugin = plugin
        self.template_name = template_name
        self.current_template = None
        self.syntax_highlighter = None
        self.selected_devices = []  # Track selected devices for generation
        
        # Set up dialog
        self.setWindowTitle("ConfigMate - Template Manager" if not template_name else f"ConfigMate - Edit Template: {template_name}")
        self.setModal(True)
        self.resize(1200, 800)  # Larger size to accommodate more functionality
        
        # Create UI
        self._create_ui()
        self._connect_signals()
        
        # Load template if editing existing one
        if template_name:
            self._load_template(template_name)
        else:
            self._setup_new_template()
        
        # Get selected devices from plugin after UI is created
        self._update_selected_devices()
        
        logger.debug("TemplateEditorDialog initialized")
    
    def _create_ui(self):
        """Create the user interface"""
        layout = QVBoxLayout(self)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Template details and variables
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Template editor and preview
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([300, 700])
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        
        # Add additional buttons
        self.preview_btn = QPushButton("Preview")
        self.validate_btn = QPushButton("Validate")
        self.detect_vars_btn = QPushButton("Detect Variables")
        self.import_btn = QPushButton("Import")
        self.export_btn = QPushButton("Export")
        
        button_box.addButton(self.preview_btn, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.addButton(self.validate_btn, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.addButton(self.detect_vars_btn, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.addButton(self.import_btn, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.addButton(self.export_btn, QDialogButtonBox.ButtonRole.ActionRole)
        
        layout.addWidget(button_box)
        
        # Store button box for signal connections
        self.button_box = button_box
    
    def _create_left_panel(self) -> QWidget:
        """Create the left panel with template details and variables"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Template details group
        details_group = QGroupBox("Template Details")
        details_layout = QFormLayout(details_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter template name")
        details_layout.addRow("Name:", self.name_edit)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["cisco_ios", "cisco_nxos", "juniper", "generic"])
        details_layout.addRow("Platform:", self.platform_combo)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Enter template description")
        details_layout.addRow("Description:", self.description_edit)
        
        layout.addWidget(details_group)
        
        # Variables group
        variables_group = QGroupBox("Template Variables")
        variables_layout = QVBoxLayout(variables_group)
        
        # Variables table
        self.variables_table = QTableWidget()
        self.variables_table.setColumnCount(4)
        self.variables_table.setHorizontalHeaderLabels([
            "Variable Name", "Type", "Default Value", "Description"
        ])
        
        # Configure table appearance
        header = self.variables_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Variable Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Default Value
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)          # Description
        
        self.variables_table.setMaximumHeight(250)
        self.variables_table.setAlternatingRowColors(True)
        self.variables_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        variables_layout.addWidget(self.variables_table)
        
        # Variable type selection
        var_type_layout = QHBoxLayout()
        var_type_layout.addWidget(QLabel("Add Variable Type:"))
        
        self.var_type_combo = QComboBox()
        self.var_type_combo.addItems(["Device Variable", "Global Variable"])
        self.var_type_combo.setToolTip("Device variables are extracted from device properties,\nGlobal variables have fixed default values")
        var_type_layout.addWidget(self.var_type_combo)
        
        var_type_layout.addStretch()
        variables_layout.addLayout(var_type_layout)
        
        # Variable management buttons
        var_buttons_layout = QHBoxLayout()
        self.add_var_btn = QPushButton("Add Variable")
        self.edit_var_btn = QPushButton("Edit Variable")
        self.remove_var_btn = QPushButton("Remove Variable")
        self.detect_vars_from_template_btn = QPushButton("Detect from Template")
        
        var_buttons_layout.addWidget(self.add_var_btn)
        var_buttons_layout.addWidget(self.edit_var_btn)
        var_buttons_layout.addWidget(self.remove_var_btn)
        var_buttons_layout.addWidget(self.detect_vars_from_template_btn)
        variables_layout.addLayout(var_buttons_layout)
        
        layout.addWidget(variables_group)
        
        # Settings group
        settings_group = QGroupBox("Editor Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.syntax_highlighting_cb = QCheckBox()
        self.syntax_highlighting_cb.setChecked(True)
        settings_layout.addRow("Syntax Highlighting:", self.syntax_highlighting_cb)
        
        self.auto_detect_vars_cb = QCheckBox()
        self.auto_detect_vars_cb.setChecked(True)
        settings_layout.addRow("Auto-detect Variables:", self.auto_detect_vars_cb)
        
        layout.addWidget(settings_group)
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        return widget
    
    def _create_right_panel(self) -> QWidget:
        """Create the right panel with template editor and preview"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Template editor tab
        editor_tab = QWidget()
        editor_layout = QVBoxLayout(editor_tab)
        
        # Template content editor
        self.template_editor = QTextEdit()
        self.template_editor.setFont(QFont("Consolas", 10))
        self.template_editor.setPlaceholderText("Enter your Jinja2 template here...")
        
        # Set up context menu for template editor
        self.template_editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.template_editor.customContextMenuRequested.connect(self._show_template_context_menu)
        
        editor_layout.addWidget(self.template_editor)
        
        tab_widget.addTab(editor_tab, "Template Editor")
        
        # Preview tab
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        
        # Preview controls
        preview_controls = QHBoxLayout()
        preview_controls.addWidget(QLabel("Test Variables:"))
        
        self.test_vars_edit = QLineEdit()
        self.test_vars_edit.setPlaceholderText('{"hostname": "SW01", "mgmt_ip": "192.168.1.10"}')
        preview_controls.addWidget(self.test_vars_edit)
        
        self.update_preview_btn = QPushButton("Update Preview")
        preview_controls.addWidget(self.update_preview_btn)
        
        preview_layout.addLayout(preview_controls)
        
        # Preview display
        self.preview_display = QTextBrowser()
        self.preview_display.setFont(QFont("Consolas", 10))
        preview_layout.addWidget(self.preview_display)
        
        tab_widget.addTab(preview_tab, "Preview")
        
        # Validation tab
        validation_tab = QWidget()
        validation_layout = QVBoxLayout(validation_tab)
        
        self.validation_display = QTextBrowser()
        validation_layout.addWidget(self.validation_display)
        
        tab_widget.addTab(validation_tab, "Validation")
        
        # Device Generation tab - add this new tab
        generation_tab = self._create_device_generation_tab()
        tab_widget.addTab(generation_tab, "Device Generation")
        
        layout.addWidget(tab_widget)
        
        # Store tab widget reference
        self.tab_widget = tab_widget
        
        return widget
    
    def _connect_signals(self):
        """Connect UI signals to handlers"""
        # Button connections
        self.button_box.accepted.connect(self._save_template)
        self.button_box.rejected.connect(self.reject)
        
        self.preview_btn.clicked.connect(self._update_preview)
        self.validate_btn.clicked.connect(self._validate_template)
        self.detect_vars_btn.clicked.connect(self._detect_variables)
        self.import_btn.clicked.connect(self._import_template)
        self.export_btn.clicked.connect(self._export_template)
        
        # Variable management
        self.add_var_btn.clicked.connect(self._add_variable)
        self.edit_var_btn.clicked.connect(self._edit_variable)
        self.remove_var_btn.clicked.connect(self._remove_variable)
        self.detect_vars_from_template_btn.clicked.connect(self._detect_variables_from_template)
        
        # Editor settings
        self.syntax_highlighting_cb.toggled.connect(self._toggle_syntax_highlighting)
        
        # Preview update
        self.update_preview_btn.clicked.connect(self._update_preview)
        
        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(30000)  # Auto-save every 30 seconds
    
    def _setup_new_template(self):
        """Set up the dialog for creating a new template"""
        # Set default values
        self.platform_combo.setCurrentText(
            self.plugin.get_setting_value("default_platform")
        )
        
        # Enable syntax highlighting if configured
        if self.plugin.get_setting_value("syntax_highlighting"):
            self._enable_syntax_highlighting()
    
    def _load_template(self, template_name: str):
        """Load an existing template for editing"""
        try:
            template = self.plugin.template_manager.get_template(template_name)
            if not template:
                QMessageBox.warning(self, "Error", f"Template '{template_name}' not found")
                return
            
            self.current_template = template
            
            # Populate UI fields
            self.name_edit.setText(template.name)
            self.platform_combo.setCurrentText(template.platform)
            self.description_edit.setPlainText(template.description)
            self.template_editor.setPlainText(template.content)
            
            # Load variables
            self._load_variables(template.variables)
            
            # Enable syntax highlighting if configured
            if self.plugin.get_setting_value("syntax_highlighting"):
                self._enable_syntax_highlighting()
            
            logger.info(f"Loaded template: {template_name}")
            
        except Exception as e:
            logger.error(f"Error loading template: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load template: {e}")
    
    def _load_variables(self, variables: Dict[str, Any]):
        """Load variables into the variables table"""
        self.variables_table.setRowCount(0)
        
        for name, value in variables.items():
            row_position = self.variables_table.rowCount()
            self.variables_table.insertRow(row_position)
            
            # Variable name
            self.variables_table.setItem(row_position, 0, QTableWidgetItem(name))
            
            # Determine variable type based on common patterns
            var_type = "Device Variable"
            if name.lower() in ['hostname', 'name', 'ip_address', 'management_ip', 'device_type', 'location', 'contact']:
                var_type = "Device Variable"
            elif isinstance(value, str) and not any(prop in name.lower() for prop in ['ip', 'host', 'name', 'type', 'location']):
                var_type = "Global Variable"
            
            self.variables_table.setItem(row_position, 1, QTableWidgetItem(var_type))
            
            # Default value
            self.variables_table.setItem(row_position, 2, QTableWidgetItem(str(value)))
            
            # Description
            if var_type == "Device Variable":
                description = f"Device property: {name}"
            else:
                description = f"Global variable: {name}"
            
            self.variables_table.setItem(row_position, 3, QTableWidgetItem(description))
    
    def _enable_syntax_highlighting(self):
        """Enable syntax highlighting for the template editor"""
        if not self.syntax_highlighter:
            self.syntax_highlighter = CiscoSyntaxHighlighter(self.template_editor.document())
    
    def _toggle_syntax_highlighting(self, enabled: bool):
        """Toggle syntax highlighting on/off"""
        if enabled:
            self._enable_syntax_highlighting()
        else:
            if self.syntax_highlighter:
                self.syntax_highlighter.setDocument(None)
                self.syntax_highlighter = None
    
    def _detect_variables(self):
        """Detect variables in the template content"""
        try:
            content = self.template_editor.toPlainText()
            if not content.strip():
                QMessageBox.information(self, "Info", "Please enter template content first")
                return
            
            # Use the plugin's variable detector
            detected_vars = self.plugin.variable_detector.detect_variables_in_template(content)
            
            if not detected_vars:
                QMessageBox.information(self, "Info", "No variables detected in template")
                return
            
            # Add detected variables to the table
            added_count = 0
            for var_name in detected_vars:
                # Check if variable already exists
                existing = False
                for row in range(self.variables_table.rowCount()):
                    item = self.variables_table.item(row, 0)
                    if item and item.text() == var_name:
                        existing = True
                        break
                
                if not existing:
                    row_position = self.variables_table.rowCount()
                    self.variables_table.insertRow(row_position)
                    
                    # Variable name
                    self.variables_table.setItem(row_position, 0, QTableWidgetItem(var_name))
                    
                    # Determine variable type based on name patterns
                    var_type = "Device Variable"
                    name_lower = var_name.lower()
                    if name_lower in ['hostname', 'name', 'ip_address', 'management_ip', 'mgmt_ip', 
                                    'device_type', 'location', 'contact', 'description', 'gateway',
                                    'dns_server', 'ntp_server', 'domain', 'snmp_community']:
                        var_type = "Device Variable"
                    elif any(keyword in name_lower for keyword in ['global', 'default', 'common', 'static']):
                        var_type = "Global Variable"
                    else:
                        # Default to device variable for most cases
                        var_type = "Device Variable"
                    
                    self.variables_table.setItem(row_position, 1, QTableWidgetItem(var_type))
                    
                    # Default value (empty for detected variables)
                    default_value = ""
                    if var_type == "Device Variable":
                        # Suggest common default values for known device variables
                        if 'hostname' in name_lower or 'name' in name_lower:
                            default_value = "Router01"
                        elif 'ip' in name_lower:
                            default_value = "192.168.1.1"
                        elif 'domain' in name_lower:
                            default_value = "example.com"
                        elif 'gateway' in name_lower:
                            default_value = "192.168.1.1"
                        elif 'dns' in name_lower:
                            default_value = "8.8.8.8"
                        elif 'ntp' in name_lower:
                            default_value = "pool.ntp.org"
                        elif 'community' in name_lower:
                            default_value = "public"
                    
                    self.variables_table.setItem(row_position, 2, QTableWidgetItem(default_value))
                    
                    # Description
                    description = f"Detected from template: {var_type.lower()}"
                    self.variables_table.setItem(row_position, 3, QTableWidgetItem(description))
                    
                    added_count += 1
            
            if added_count > 0:
                QMessageBox.information(self, "Success", f"Added {added_count} new variables from template")
            else:
                QMessageBox.information(self, "Info", "All detected variables already exist in the table")
            
        except Exception as e:
            logger.error(f"Error detecting variables: {e}")
            QMessageBox.critical(self, "Error", f"Failed to detect variables: {e}")
    
    def _validate_template(self):
        """Validate the template syntax and variables"""
        try:
            content = self.template_editor.toPlainText()
            if not content.strip():
                self.validation_display.setPlainText("Template is empty")
                self.tab_widget.setCurrentIndex(2)  # Switch to validation tab
                return
            
            # Create temporary template for validation
            try:
                from configmate.core.template_manager import Template
            except ImportError:
                import sys
                import os
                plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, plugin_dir)
                from core.template_manager import Template
            temp_template = Template(
                name="temp",
                content=content,
                platform=self.platform_combo.currentText()
            )
            
            # Get variables from UI
            variables = self._get_variables_from_ui()
            
            # Validate template
            validation_results = []
            validation_results.append("=== Template Validation Results ===\n")
            
            # Check Jinja2 syntax
            try:
                temp_template.render(variables)
                validation_results.append("✓ Jinja2 syntax is valid")
            except Exception as e:
                validation_results.append(f"✗ Jinja2 syntax error: {e}")
            
            # Check for undefined variables
            missing_vars = temp_template.validate_variables(variables)
            if missing_vars:
                validation_results.append(f"⚠ Missing variables: {', '.join(missing_vars)}")
            else:
                validation_results.append("✓ All variables are defined")
            
            # Check for unused variables
            template_vars = set(temp_template.get_variables_from_content())
            provided_vars = set(variables.keys())
            unused_vars = provided_vars - template_vars
            if unused_vars:
                validation_results.append(f"⚠ Unused variables: {', '.join(unused_vars)}")
            else:
                validation_results.append("✓ No unused variables")
            
            # Display results
            self.validation_display.setPlainText("\n".join(validation_results))
            self.tab_widget.setCurrentIndex(2)  # Switch to validation tab
            
        except Exception as e:
            logger.error(f"Error validating template: {e}")
            self.validation_display.setPlainText(f"Validation error: {e}")
            self.tab_widget.setCurrentIndex(2)
    
    def _update_preview(self):
        """Update the template preview"""
        try:
            content = self.template_editor.toPlainText()
            if not content.strip():
                self.preview_display.setPlainText("Template is empty")
                return
            
            # Get test variables
            test_vars_text = self.test_vars_edit.text().strip()
            if test_vars_text:
                try:
                    test_vars = json.loads(test_vars_text)
                except json.JSONDecodeError:
                    self.preview_display.setPlainText("Invalid JSON in test variables")
                    return
            else:
                test_vars = self._get_variables_from_ui()
            
            # Create temporary template and render
            try:
                from configmate.core.template_manager import Template
            except ImportError:
                import sys
                import os
                plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, plugin_dir)
                from core.template_manager import Template
            temp_template = Template(
                name="temp",
                content=content,
                platform=self.platform_combo.currentText()
            )
            
            rendered = temp_template.render(test_vars)
            self.preview_display.setPlainText(rendered)
            
            # Switch to preview tab
            self.tab_widget.setCurrentIndex(1)
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.preview_display.setPlainText(f"Preview error: {e}")
    
    def _get_variables_from_ui(self) -> Dict[str, Any]:
        """Get variables from the UI table"""
        variables = {}
        
        for row in range(self.variables_table.rowCount()):
            item = self.variables_table.item(row, 0)
            if item:
                var_name = item.text()
                var_value = self.variables_table.item(row, 2).text()
                variables[var_name] = var_value
        
        return variables
    
    def _add_variable(self):
        """Add a new variable"""
        # Create variable editing dialog
        dialog = VariableEditDialog(var_type=self.var_type_combo.currentText(), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Add the new variable to the table
            row_position = self.variables_table.rowCount()
            self.variables_table.insertRow(row_position)
            self.variables_table.setItem(row_position, 0, QTableWidgetItem(dialog.name))
            self.variables_table.setItem(row_position, 1, QTableWidgetItem(dialog.var_type))
            self.variables_table.setItem(row_position, 2, QTableWidgetItem(dialog.value))
            self.variables_table.setItem(row_position, 3, QTableWidgetItem(dialog.description))
    
    def _edit_variable(self):
        """Edit the selected variable"""
        current_row = self.variables_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Info", "Please select a variable to edit")
            return
        
        # Get current variable data
        var_name = self.variables_table.item(current_row, 0).text()
        var_type = self.variables_table.item(current_row, 1).text()
        var_value = self.variables_table.item(current_row, 2).text()
        var_desc = self.variables_table.item(current_row, 3).text()
        
        # Create variable editing dialog
        dialog = VariableEditDialog(var_name, var_type, var_value, var_desc, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update the table with new values
            self.variables_table.setItem(current_row, 0, QTableWidgetItem(dialog.name))
            self.variables_table.setItem(current_row, 1, QTableWidgetItem(dialog.var_type))
            self.variables_table.setItem(current_row, 2, QTableWidgetItem(dialog.value))
            self.variables_table.setItem(current_row, 3, QTableWidgetItem(dialog.description))
    
    def _remove_variable(self):
        """Remove the selected variable"""
        current_item = self.variables_table.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Please select a variable to remove")
            return
        
        row = self.variables_table.row(current_item)
        self.variables_table.removeRow(row)
    
    def _detect_variables_from_template(self):
        """Detect variables from the template"""
        try:
            content = self.template_editor.toPlainText()
            if not content.strip():
                QMessageBox.information(self, "Info", "Please enter template content first")
                return
            
            # Detect variables from the template
            variables = self.plugin.variable_detector.detect_variables_from_template(content)
            
            if not variables:
                QMessageBox.information(self, "Info", "No variables detected in template")
                return
            
            # Add detected variables to the table
            for var_name, var_value in variables.items():
                # Check if variable already exists
                existing = False
                for row in range(self.variables_table.rowCount()):
                    item = self.variables_table.item(row, 0)
                    if item.text() == var_name:
                        existing = True
                        break
                
                if not existing:
                    row_position = self.variables_table.rowCount()
                    self.variables_table.insertRow(row_position)
                    self.variables_table.setItem(row_position, 0, QTableWidgetItem(var_name))
                    self.variables_table.setItem(row_position, 1, QTableWidgetItem(type(var_value).__name__))
                    self.variables_table.setItem(row_position, 2, QTableWidgetItem(str(var_value)))
                    self.variables_table.setItem(row_position, 3, QTableWidgetItem(f"Detected from template"))
            
            QMessageBox.information(self, "Success", f"Detected {len(variables)} variables")
            
        except Exception as e:
            logger.error(f"Error detecting variables from template: {e}")
            QMessageBox.critical(self, "Error", f"Failed to detect variables from template: {e}")
    
    def _import_template(self):
        """Import template from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Template", "", 
            "Template Files (*.j2 *.jinja *.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.template_editor.setPlainText(content)
                
                # Auto-detect variables if enabled
                if self.auto_detect_vars_cb.isChecked():
                    self._detect_variables()
                
                QMessageBox.information(self, "Success", "Template imported successfully")
                
            except Exception as e:
                logger.error(f"Error importing template: {e}")
                QMessageBox.critical(self, "Error", f"Failed to import template: {e}")
    
    def _export_template(self):
        """Export template to file"""
        content = self.template_editor.toPlainText()
        if not content.strip():
            QMessageBox.information(self, "Info", "Template is empty")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Template", f"{self.name_edit.text() or 'template'}.j2",
            "Template Files (*.j2 *.jinja *.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                QMessageBox.information(self, "Success", "Template exported successfully")
                
            except Exception as e:
                logger.error(f"Error exporting template: {e}")
                QMessageBox.critical(self, "Error", f"Failed to export template: {e}")
    
    def _save_template(self):
        """Save the template"""
        try:
            # Validate required fields
            name = self.name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Warning", "Please enter a template name")
                return
            
            content = self.template_editor.toPlainText().strip()
            if not content:
                QMessageBox.warning(self, "Warning", "Please enter template content")
                return
            
            # Get other fields
            platform = self.platform_combo.currentText()
            description = self.description_edit.toPlainText().strip()
            variables = self._get_variables_from_ui()
            
            # Save template
            if self.current_template and self.current_template.name == name:
                # Update existing template
                self.plugin.template_manager.update_template(
                    name=name,
                    content=content,
                    platform=platform,
                    description=description,
                    variables=variables
                )
            else:
                # Create new template
                self.plugin.template_manager.create_template(
                    name=name,
                    content=content,
                    platform=platform,
                    description=description,
                    variables=variables
                )
            
            # Emit signal
            self.template_saved.emit(name)
            
            # Close dialog
            self.accept()
            
            logger.info(f"Template saved: {name}")
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save template: {e}")
    
    def _auto_save(self):
        """Auto-save template as draft"""
        # This could save to a temporary location for recovery
        pass
    
    def create_from_config(self, device, config_text):
        """Create a new template from device configuration"""
        logger.info(f"Creating template from device {device.get_property('name')} configuration")
        
        try:
            # Set device name as template name suggestion
            device_name = device.get_property('name', 'Unknown')
            self.name_edit.setText(f"{device_name}_template")
            
            # Detect platform from device
            device_type = device.get_property('device_type', 'generic')
            if 'cisco' in device_type.lower():
                if 'nexus' in device_type.lower() or 'nxos' in device_type.lower():
                    platform = 'cisco_nxos'
                else:
                    platform = 'cisco_ios'
            elif 'juniper' in device_type.lower():
                platform = 'juniper'
            else:
                platform = 'generic'
            
            self.platform_combo.setCurrentText(platform)
            
            # Use variable detector to create template
            template_format = self.plugin.get_setting_value("template_format") or "text"
            template_content = self.plugin.variable_detector.create_template_from_config(
                config_text, device, template_format
            )
            
            self.template_editor.setPlainText(template_content)
            
            # Auto-detect variables
            if self.auto_detect_vars_cb.isChecked():
                self._detect_variables()
            
            # Set description
            self.description_edit.setPlainText(
                f"Template created from {device_name} configuration on {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            logger.info("Template created from device configuration")
            
        except Exception as e:
            logger.error(f"Error creating template from config: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create template: {e}")

    def _update_selected_devices(self):
        """Update the list of selected devices from the plugin"""
        try:
            if hasattr(self.plugin, '_selected_devices'):
                self.selected_devices = self.plugin._selected_devices or []
            else:
                self.selected_devices = []
            
            # Update device display if we have a device group widget
            if hasattr(self, 'device_info_label'):
                if self.selected_devices:
                    device_names = [device.get_property('name', 'Unknown') for device in self.selected_devices]
                    self.device_info_label.setText(f"Selected: {', '.join(device_names)}")
                else:
                    self.device_info_label.setText("No devices selected")
            
            logger.debug(f"Updated selected devices: {len(self.selected_devices)} devices")
            
        except Exception as e:
            logger.error(f"Error updating selected devices: {e}")
            self.selected_devices = []

    def _create_device_generation_tab(self) -> QWidget:
        """Create device configuration generation tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Device selection group
        device_group = QGroupBox("Target Devices")
        device_layout = QVBoxLayout(device_group)
        
        # Device info
        self.device_info_label = QLabel("No devices selected")
        self.device_info_label.setWordWrap(True)
        device_layout.addWidget(self.device_info_label)
        
        # Refresh devices button
        refresh_devices_btn = QPushButton("Refresh Selected Devices")
        refresh_devices_btn.clicked.connect(self._update_selected_devices)
        device_layout.addWidget(refresh_devices_btn)
        
        layout.addWidget(device_group)
        
        # Variables group for generation
        gen_variables_group = QGroupBox("Generation Variables")
        gen_variables_layout = QVBoxLayout(gen_variables_group)
        
        # Auto-fill variables button
        auto_fill_btn = QPushButton("Auto-Fill from Selected Devices")
        auto_fill_btn.clicked.connect(self._auto_fill_variables)
        gen_variables_layout.addWidget(auto_fill_btn)
        
        # Variables display
        self.generation_variables_text = QTextEdit()
        self.generation_variables_text.setMaximumHeight(150)
        self.generation_variables_text.setPlaceholderText("Variables will appear here when auto-filled")
        gen_variables_layout.addWidget(self.generation_variables_text)
        
        layout.addWidget(gen_variables_group)
        
        # Configuration preview group
        preview_group = QGroupBox("Configuration Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview controls
        preview_controls = QHBoxLayout()
        
        self.preview_device_combo = QComboBox()
        self.preview_device_combo.currentTextChanged.connect(self._update_config_preview)
        preview_controls.addWidget(QLabel("Preview for:"))
        preview_controls.addWidget(self.preview_device_combo)
        
        generate_preview_btn = QPushButton("Generate Preview")
        generate_preview_btn.clicked.connect(self._generate_config_preview)
        preview_controls.addWidget(generate_preview_btn)
        
        preview_layout.addLayout(preview_controls)
        
        # Preview text
        self.config_preview_text = QTextEdit()
        self.config_preview_text.setPlaceholderText("Configuration preview will appear here")
        preview_layout.addWidget(self.config_preview_text)
        
        layout.addWidget(preview_group)
        
        # Generation actions
        action_layout = QHBoxLayout()
        
        generate_all_btn = QPushButton("Generate for All Devices")
        generate_all_btn.clicked.connect(self._generate_for_all_devices)
        action_layout.addWidget(generate_all_btn)
        
        apply_btn = QPushButton("Apply Configuration")
        apply_btn.clicked.connect(self._apply_configuration)
        action_layout.addWidget(apply_btn)
        
        layout.addLayout(action_layout)
        
        return tab

    def _auto_fill_variables(self):
        """Auto-fill variables from selected devices"""
        try:
            if not self.selected_devices:
                QMessageBox.information(self, "Info", "No devices selected")
                return
            
            # Get template name
            template_name = self.name_edit.text().strip()
            if not template_name:
                QMessageBox.warning(self, "Warning", "Please enter a template name first")
                return
            
            # Generate variables for all selected devices
            all_variables = {}
            
            for device in self.selected_devices:
                try:
                    device_vars = self.plugin.config_generator.get_template_variables_for_device(
                        device, template_name
                    )
                    device_name = device.get_property('name', 'Unknown')
                    all_variables[device_name] = device_vars
                    
                except Exception as e:
                    logger.error(f"Error getting variables for device {device.get_property('name')}: {e}")
            
            # Display variables
            variables_text = []
            for device_name, variables in all_variables.items():
                variables_text.append(f"=== {device_name} ===")
                if variables:
                    for var_name, var_value in variables.items():
                        variables_text.append(f"  {var_name}: {var_value}")
                else:
                    variables_text.append("  No variables detected")
                variables_text.append("")
            
            self.generation_variables_text.setPlainText("\n".join(variables_text))
            
            # Update preview device combo
            self.preview_device_combo.clear()
            self.preview_device_combo.addItems([device.get_property('name', 'Unknown') for device in self.selected_devices])
            
        except Exception as e:
            logger.error(f"Error auto-filling variables: {e}")
            QMessageBox.critical(self, "Error", f"Failed to auto-fill variables: {e}")

    def _generate_config_preview(self):
        """Generate configuration preview for selected device"""
        try:
            if not self.selected_devices:
                QMessageBox.information(self, "Info", "No devices selected")
                return
            
            current_device_name = self.preview_device_combo.currentText()
            if not current_device_name:
                return
            
            # Find the device
            target_device = None
            for device in self.selected_devices:
                if device.get_property('name', 'Unknown') == current_device_name:
                    target_device = device
                    break
            
            if not target_device:
                return
            
            # Get template content
            template_content = self.template_editor.toPlainText()
            if not template_content.strip():
                QMessageBox.warning(self, "Warning", "Please enter template content")
                return
            
            # Create temporary template
            temp_template_name = f"temp_{int(time.time())}"
            self.plugin.template_manager.create_template(
                name=temp_template_name,
                content=template_content,
                platform=self.platform_combo.currentText(),
                description="Temporary template for preview",
                variables=self._get_variables_from_ui()
            )
            
            try:
                # Generate variables for device
                variables = self.plugin.config_generator.get_template_variables_for_device(
                    target_device, temp_template_name
                )
                
                # Generate configuration
                config = self.plugin.config_generator.generate_config(
                    target_device, temp_template_name, variables
                )
                
                if config:
                    self.config_preview_text.setPlainText(config)
                else:
                    self.config_preview_text.setPlainText("Failed to generate configuration")
                
            finally:
                # Clean up temporary template
                try:
                    self.plugin.template_manager.delete_template(temp_template_name)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate preview: {e}")

    def _update_config_preview(self):
        """Update configuration preview when device selection changes"""
        # Clear preview when device changes
        self.config_preview_text.clear()

    def _generate_for_all_devices(self):
        """Generate configuration for all selected devices"""
        try:
            if not self.selected_devices:
                QMessageBox.information(self, "Info", "No devices selected")
                return
            
            # Save template first
            self._save_template()
            
            template_name = self.name_edit.text().strip()
            if not template_name:
                return
            
            # Generate for all devices
            results = []
            for device in self.selected_devices:
                try:
                    device_name = device.get_property('name', 'Unknown')
                    
                    # Get variables for device
                    variables = self.plugin.config_generator.get_template_variables_for_device(
                        device, template_name
                    )
                    
                    # Generate configuration
                    config = self.plugin.config_generator.generate_config(
                        device, template_name, variables
                    )
                    
                    if config:
                        results.append(f"✓ Generated config for '{device_name}' ({len(config.splitlines())} lines)")
                    else:
                        results.append(f"✗ Failed to generate config for '{device_name}'")
                        
                except Exception as e:
                    device_name = device.get_property('name', 'Unknown')
                    results.append(f"✗ Error generating config for '{device_name}': {e}")
            
            # Show results
            result_text = f"Configuration Generation Results:\n\n" + "\n".join(results)
            QMessageBox.information(self, "Generation Complete", result_text)
            
        except Exception as e:
            logger.error(f"Error generating for all devices: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate configurations: {e}")

    def _apply_configuration(self):
        """Apply configuration to selected devices"""
        try:
            if not self.selected_devices:
                QMessageBox.information(self, "Info", "No devices selected")
                return
            
            # Confirm action
            reply = QMessageBox.question(
                self, "Confirm Apply",
                f"Apply configuration to {len(self.selected_devices)} device(s)?\n\n"
                "This will modify the device configuration.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            QMessageBox.information(self, "Apply", "Configuration apply functionality will be implemented in a future version.")
            
        except Exception as e:
            logger.error(f"Error applying configuration: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply configuration: {e}")

    def _show_template_context_menu(self, position):
        """Show context menu for template editor"""
        menu = QMenu()
        cursor = self.template_editor.textCursor()
        
        # Get selected text if any
        selected_text = cursor.selectedText()
        
        # Variable insertion section
        insert_menu = menu.addMenu("Insert Variable")
        
        # Add action to create new variable and insert
        new_var_action = QAction("Create New Variable...", self)
        new_var_action.triggered.connect(lambda: self._create_and_insert_variable(position))
        insert_menu.addAction(new_var_action)
        
        insert_menu.addSeparator()
        
        # Add existing variables from table
        for row in range(self.variables_table.rowCount()):
            var_name = self.variables_table.item(row, 0).text()
            var_type = self.variables_table.item(row, 1).text()
            var_action = QAction(f"{var_name} ({var_type})", self)
            var_action.triggered.connect(lambda checked, name=var_name: self._insert_variable_at_cursor(name))
            insert_menu.addAction(var_action)
        
        if self.variables_table.rowCount() == 0:
            no_vars_action = QAction("No variables defined", self)
            no_vars_action.setEnabled(False)
            insert_menu.addAction(no_vars_action)
        
        menu.addSeparator()
        
        # Text manipulation section
        if selected_text:
            # If text is selected, offer to create variable from selection
            create_from_sel_action = QAction(f"Create Variable from '{selected_text[:20]}...'", self)
            create_from_sel_action.triggered.connect(lambda: self._create_variable_from_selection(selected_text))
            menu.addAction(create_from_sel_action)
            
            menu.addSeparator()
        
        # Standard variable management
        add_var_action = QAction("Add Variable to Table", self)
        add_var_action.triggered.connect(self._add_variable)
        menu.addAction(add_var_action)
        
        if self.variables_table.rowCount() > 0:
            edit_var_action = QAction("Edit Selected Variable", self)
            edit_var_action.triggered.connect(self._edit_variable)
            menu.addAction(edit_var_action)
            
            remove_var_action = QAction("Remove Selected Variable", self)
            remove_var_action.triggered.connect(self._remove_variable)
            menu.addAction(remove_var_action)
        
        menu.addSeparator()
        
        # Template operations
        detect_vars_action = QAction("Detect Variables from Template", self)
        detect_vars_action.triggered.connect(self._detect_variables_from_template)
        menu.addAction(detect_vars_action)
        
        # Show the context menu
        menu.exec(self.template_editor.mapToGlobal(position))
    
    def _create_and_insert_variable(self, position):
        """Create a new variable and insert it at cursor position"""
        # Create variable editing dialog
        dialog = VariableEditDialog(var_type=self.var_type_combo.currentText(), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Add the new variable to the table
            row_position = self.variables_table.rowCount()
            self.variables_table.insertRow(row_position)
            self.variables_table.setItem(row_position, 0, QTableWidgetItem(dialog.name))
            self.variables_table.setItem(row_position, 1, QTableWidgetItem(dialog.var_type))
            self.variables_table.setItem(row_position, 2, QTableWidgetItem(dialog.value))
            self.variables_table.setItem(row_position, 3, QTableWidgetItem(dialog.description))
            
            # Insert the variable into the template at cursor position
            self._insert_variable_at_cursor(dialog.name)
    
    def _insert_variable_at_cursor(self, var_name):
        """Insert a variable at the current cursor position"""
        cursor = self.template_editor.textCursor()
        
        # Format the variable for Jinja2 template
        variable_text = f"{{{{ {var_name} }}}}"
        
        cursor.insertText(variable_text)
        self.template_editor.setFocus()
    
    def _create_variable_from_selection(self, selected_text):
        """Create a new variable from selected text"""
        # Suggest a variable name based on selected text
        suggested_name = selected_text.strip().replace(' ', '_').replace('-', '_').lower()
        suggested_name = ''.join(c for c in suggested_name if c.isalnum() or c == '_')
        
        # Create variable editing dialog with suggested name and selected text as default
        dialog = VariableEditDialog(
            name=suggested_name,
            var_type=self.var_type_combo.currentText(),
            value=selected_text,
            description=f"Variable created from selected text: '{selected_text}'",
            parent=self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Add the new variable to the table
            row_position = self.variables_table.rowCount()
            self.variables_table.insertRow(row_position)
            self.variables_table.setItem(row_position, 0, QTableWidgetItem(dialog.name))
            self.variables_table.setItem(row_position, 1, QTableWidgetItem(dialog.var_type))
            self.variables_table.setItem(row_position, 2, QTableWidgetItem(dialog.value))
            self.variables_table.setItem(row_position, 3, QTableWidgetItem(dialog.description))
            
            # Replace selected text with variable
            cursor = self.template_editor.textCursor()
            variable_text = f"{{{{ {dialog.name} }}}}"
            cursor.insertText(variable_text)
            self.template_editor.setFocus()


class VariableEditDialog(QDialog):
    """Dialog for editing template variables with comprehensive options"""
    
    def __init__(self, name="", var_type="Device Variable", value="", description="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Template Variable")
        self.setModal(True)
        self.resize(400, 300)
        
        # Store values
        self.name = name
        self.var_type = var_type
        self.value = value
        self.description = description
        
        self._create_ui()
        self._load_values()
    
    def _create_ui(self):
        """Create the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Form layout for variable details
        form_layout = QFormLayout()
        
        # Variable name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Variable name (e.g., hostname, ip_address)")
        form_layout.addRow("Variable Name:", self.name_edit)
        
        # Variable type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Device Variable", "Global Variable"])
        self.type_combo.setToolTip(
            "Device Variable: Extracted from device properties\n"
            "Global Variable: Fixed value used for all devices"
        )
        form_layout.addRow("Variable Type:", self.type_combo)
        
        # Default value
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Default value")
        form_layout.addRow("Default Value:", self.value_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Variable description (optional)")
        form_layout.addRow("Description:", self.description_edit)
        
        layout.addLayout(form_layout)
        
        # Device property mapping (for device variables)
        self.mapping_group = QGroupBox("Device Property Mapping")
        mapping_layout = QFormLayout(self.mapping_group)
        
        self.property_combo = QComboBox()
        self.property_combo.setEditable(True)
        self.property_combo.addItems([
            "name", "hostname", "ip_address", "management_ip", "device_type",
            "location", "contact", "description", "domain", "gateway",
            "dns_server", "ntp_server", "snmp_community"
        ])
        self.property_combo.setToolTip("Device property to map this variable to")
        mapping_layout.addRow("Map to Property:", self.property_combo)
        
        self.fallback_edit = QLineEdit()
        self.fallback_edit.setPlaceholderText("Fallback value if property not found")
        mapping_layout.addRow("Fallback Value:", self.fallback_edit)
        
        layout.addWidget(self.mapping_group)
        
        # Update mapping visibility based on type
        self.type_combo.currentTextChanged.connect(self._update_mapping_visibility)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Initial visibility
        self._update_mapping_visibility()
    
    def _load_values(self):
        """Load existing values into the dialog"""
        self.name_edit.setText(self.name)
        self.type_combo.setCurrentText(self.var_type)
        self.value_edit.setText(self.value)
        self.description_edit.setPlainText(self.description)
        
        # Try to detect device property mapping from variable name
        if self.var_type == "Device Variable":
            name_lower = self.name.lower()
            if name_lower in ["hostname", "name"]:
                self.property_combo.setCurrentText("name")
            elif name_lower in ["ip_address", "ip", "mgmt_ip"]:
                self.property_combo.setCurrentText("ip_address")
            elif name_lower in ["device_type", "type"]:
                self.property_combo.setCurrentText("device_type")
            else:
                self.property_combo.setCurrentText(self.name)
    
    def _update_mapping_visibility(self):
        """Update visibility of device property mapping based on variable type"""
        is_device_var = self.type_combo.currentText() == "Device Variable"
        self.mapping_group.setVisible(is_device_var)
    
    def accept(self):
        """Validate and accept the dialog"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Variable name is required")
            return
        
        value = self.value_edit.text().strip()
        if not value and self.type_combo.currentText() == "Global Variable":
            QMessageBox.warning(self, "Validation Error", "Default value is required for global variables")
            return
        
        # Store the updated values
        self.name = name
        self.var_type = self.type_combo.currentText()
        self.value = value
        self.description = self.description_edit.toPlainText().strip()
        
        # Store device property mapping if applicable
        if self.var_type == "Device Variable":
            self.device_property = self.property_combo.currentText()
            self.fallback_value = self.fallback_edit.text().strip()
        
        super().accept() 