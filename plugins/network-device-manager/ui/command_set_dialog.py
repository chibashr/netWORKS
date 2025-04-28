#!/usr/bin/env python3
# Network Device Manager - Command Set Dialog

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QTabWidget, QWidget, QFormLayout, QLineEdit, 
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QFileDialog, QGroupBox, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, Slot

class CommandSetDialog(QDialog):
    """
    Dialog for managing command sets.
    Allows creating, editing, importing, and exporting command sets.
    """
    
    def __init__(self, parent, command_manager):
        super().__init__(parent)
        self.command_manager = command_manager
        self.current_device_type = None
        self.current_command_id = None
        
        self.setWindowTitle("Manage Command Sets")
        self.resize(800, 600)
        
        self._init_ui()
        self._load_command_sets()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Main horizontal layout
        main_layout = QHBoxLayout()
        
        # Left side - Command sets list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Command set list
        left_layout.addWidget(QLabel("Command Sets:"))
        self.command_set_list = QListWidget()
        self.command_set_list.currentItemChanged.connect(self._on_command_set_changed)
        left_layout.addWidget(self.command_set_list)
        
        # Command set buttons
        cmd_set_buttons = QHBoxLayout()
        self.add_set_button = QPushButton("Add")
        self.add_set_button.clicked.connect(self._add_command_set)
        self.remove_set_button = QPushButton("Remove")
        self.remove_set_button.clicked.connect(self._remove_command_set)
        self.remove_set_button.setEnabled(False)
        
        cmd_set_buttons.addWidget(self.add_set_button)
        cmd_set_buttons.addWidget(self.remove_set_button)
        left_layout.addLayout(cmd_set_buttons)
        
        # Import/Export buttons
        imp_exp_buttons = QHBoxLayout()
        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self._import_command_set)
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self._export_command_set)
        self.export_button.setEnabled(False)
        
        imp_exp_buttons.addWidget(self.import_button)
        imp_exp_buttons.addWidget(self.export_button)
        left_layout.addLayout(imp_exp_buttons)
        
        # Right side - Command set details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Command set details form
        self.details_group = QGroupBox("Command Set Details")
        details_layout = QFormLayout(self.details_group)
        
        self.device_type_edit = QLineEdit()
        self.device_type_edit.setPlaceholderText("E.g. cisco_3650")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("E.g. Cisco Catalyst 3650")
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Description of this command set")
        self.description_edit.setMaximumHeight(80)
        
        details_layout.addRow("Device Type ID:", self.device_type_edit)
        details_layout.addRow("Display Name:", self.name_edit)
        details_layout.addRow("Description:", self.description_edit)
        
        right_layout.addWidget(self.details_group)
        
        # Commands group
        self.commands_group = QGroupBox("Commands")
        commands_layout = QVBoxLayout(self.commands_group)
        
        # Commands table
        self.commands_table = QTableWidget(0, 3)
        self.commands_table.setHorizontalHeaderLabels(["ID", "Command", "Description"])
        self.commands_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.commands_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.commands_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.commands_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.commands_table.currentItemChanged.connect(self._on_command_selected)
        
        commands_layout.addWidget(self.commands_table)
        
        # Command buttons
        cmd_buttons = QHBoxLayout()
        self.add_cmd_button = QPushButton("Add Command")
        self.add_cmd_button.clicked.connect(self._add_command)
        self.add_cmd_button.setEnabled(False)
        self.edit_cmd_button = QPushButton("Edit Command")
        self.edit_cmd_button.clicked.connect(self._edit_command)
        self.edit_cmd_button.setEnabled(False)
        self.remove_cmd_button = QPushButton("Remove Command")
        self.remove_cmd_button.clicked.connect(self._remove_command)
        self.remove_cmd_button.setEnabled(False)
        
        cmd_buttons.addWidget(self.add_cmd_button)
        cmd_buttons.addWidget(self.edit_cmd_button)
        cmd_buttons.addWidget(self.remove_cmd_button)
        commands_layout.addLayout(cmd_buttons)
        
        right_layout.addWidget(self.commands_group)
        
        # Command edit form
        self.command_edit_group = QGroupBox("Command Details")
        command_edit_layout = QFormLayout(self.command_edit_group)
        
        self.command_id_edit = QLineEdit()
        self.command_id_edit.setPlaceholderText("E.g. show_version")
        self.command_text_edit = QLineEdit()
        self.command_text_edit.setPlaceholderText("E.g. show version")
        self.command_desc_edit = QLineEdit()
        self.command_desc_edit.setPlaceholderText("E.g. Display system version information")
        
        self.output_type_combo = QComboBox()
        self.output_type_combo.addItems(["text", "tabular", "json"])
        
        command_edit_layout.addRow("Command ID:", self.command_id_edit)
        command_edit_layout.addRow("Command:", self.command_text_edit)
        command_edit_layout.addRow("Description:", self.command_desc_edit)
        command_edit_layout.addRow("Output Type:", self.output_type_combo)
        
        # Command edit buttons
        cmd_edit_buttons = QHBoxLayout()
        self.save_cmd_button = QPushButton("Save Command")
        self.save_cmd_button.clicked.connect(self._save_command)
        self.cancel_cmd_button = QPushButton("Cancel")
        self.cancel_cmd_button.clicked.connect(self._cancel_command_edit)
        
        cmd_edit_buttons.addWidget(self.save_cmd_button)
        cmd_edit_buttons.addWidget(self.cancel_cmd_button)
        command_edit_layout.addRow("", cmd_edit_buttons)
        
        right_layout.addWidget(self.command_edit_group)
        self.command_edit_group.setVisible(False)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)
        
        layout.addLayout(main_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save_changes)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Disable edit controls initially
        self._set_edit_mode(False)
    
    def _load_command_sets(self):
        """Load command sets into the list."""
        self.command_set_list.clear()
        
        # Get device types with display names
        device_types = self.command_manager.get_device_type_display_names()
        
        for device_type, display_name in device_types.items():
            # Create item with device type as data
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, device_type)
            self.command_set_list.addItem(item)
    
    def _set_edit_mode(self, enabled):
        """Enable or disable editing controls."""
        self.device_type_edit.setEnabled(enabled)
        self.name_edit.setEnabled(enabled)
        self.description_edit.setEnabled(enabled)
        self.add_cmd_button.setEnabled(enabled)
        
        # Hide command edit group when not editing
        self.command_edit_group.setVisible(False)
    
    def _on_command_set_changed(self, current, previous):
        """Handle command set selection change."""
        if not current:
            self._set_edit_mode(False)
            self.remove_set_button.setEnabled(False)
            self.export_button.setEnabled(False)
            return
        
        # Get device type from item data
        device_type = current.data(Qt.ItemDataRole.UserRole)
        self.current_device_type = device_type
        
        # Get command set
        command_set = self.command_manager.commands_by_type.get(device_type, {})
        
        # Update form
        self.device_type_edit.setText(device_type)
        self.name_edit.setText(command_set.get('name', ''))
        self.description_edit.setText(command_set.get('description', ''))
        
        # Enable controls
        self._set_edit_mode(True)
        self.remove_set_button.setEnabled(True)
        self.export_button.setEnabled(True)
        
        # Load commands
        self._load_commands(device_type)
    
    def _load_commands(self, device_type):
        """Load commands for a device type."""
        # Clear table
        self.commands_table.setRowCount(0)
        
        # Get commands
        commands = self.command_manager.get_commands_for_device_type(device_type)
        
        # Add commands to table
        for command_id, command_data in commands.items():
            row = self.commands_table.rowCount()
            self.commands_table.insertRow(row)
            
            # Set command data
            self.commands_table.setItem(row, 0, QTableWidgetItem(command_id))
            self.commands_table.setItem(row, 1, QTableWidgetItem(command_data.get('command', '')))
            self.commands_table.setItem(row, 2, QTableWidgetItem(command_data.get('description', '')))
            
            # Store output type in user data
            self.commands_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, command_data.get('output_type', 'text'))
    
    def _on_command_selected(self, current, previous):
        """Handle command selection change."""
        if not current:
            self.edit_cmd_button.setEnabled(False)
            self.remove_cmd_button.setEnabled(False)
            return
        
        # Enable edit/remove buttons
        self.edit_cmd_button.setEnabled(True)
        self.remove_cmd_button.setEnabled(True)
    
    def _add_command_set(self):
        """Add a new command set."""
        # Create a default command set
        default_device_type = "new_device_type"
        default_name = "New Device Type"
        default_description = "Description of the new device type"
        
        # Add to command manager
        self.command_manager.add_command_set(
            default_device_type,
            default_name,
            default_description,
            {}
        )
        
        # Reload command sets
        self._load_command_sets()
        
        # Select the new command set
        for i in range(self.command_set_list.count()):
            item = self.command_set_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == default_device_type:
                self.command_set_list.setCurrentItem(item)
                break
    
    def _remove_command_set(self):
        """Remove the selected command set."""
        if not self.current_device_type:
            return
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the command set '{self.name_edit.text()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Remove command set
        self.command_manager.remove_command_set(self.current_device_type)
        
        # Reload command sets
        self._load_command_sets()
        
        # Clear current selection
        self.current_device_type = None
        self._set_edit_mode(False)
        self.remove_set_button.setEnabled(False)
        self.export_button.setEnabled(False)
    
    def _import_command_set(self):
        """Import a command set from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Command Set",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        # Import command set
        success, message = self.command_manager.import_command_set(file_path)
        
        if success:
            QMessageBox.information(self, "Import Successful", message)
            self._load_command_sets()
        else:
            QMessageBox.warning(self, "Import Failed", message)
    
    def _export_command_set(self):
        """Export the selected command set to a file."""
        if not self.current_device_type:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Command Set",
            f"{self.current_device_type}.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        # Export command set
        success, message = self.command_manager.export_command_set(self.current_device_type, file_path)
        
        if success:
            QMessageBox.information(self, "Export Successful", message)
        else:
            QMessageBox.warning(self, "Export Failed", message)
    
    def _add_command(self):
        """Add a new command."""
        if not self.current_device_type:
            return
        
        # Show command edit form
        self.command_edit_group.setVisible(True)
        
        # Clear form
        self.command_id_edit.setText("")
        self.command_text_edit.setText("")
        self.command_desc_edit.setText("")
        self.output_type_combo.setCurrentIndex(0)
        
        # Set focus
        self.command_id_edit.setFocus()
        
        # Set current command ID to None (new command)
        self.current_command_id = None
    
    def _edit_command(self):
        """Edit the selected command."""
        if not self.current_device_type:
            return
        
        # Get selected command
        selected_rows = self.commands_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        command_id = self.commands_table.item(row, 0).text()
        
        # Get command details
        command_details = self.command_manager.get_command_details(self.current_device_type, command_id)
        if not command_details:
            return
        
        # Show command edit form
        self.command_edit_group.setVisible(True)
        
        # Set form values
        self.command_id_edit.setText(command_id)
        self.command_text_edit.setText(command_details.get('command', ''))
        self.command_desc_edit.setText(command_details.get('description', ''))
        
        # Set output type
        output_type = command_details.get('output_type', 'text')
        index = self.output_type_combo.findText(output_type)
        if index >= 0:
            self.output_type_combo.setCurrentIndex(index)
        
        # Set focus
        self.command_text_edit.setFocus()
        
        # Store current command ID
        self.current_command_id = command_id
    
    def _remove_command(self):
        """Remove the selected command."""
        if not self.current_device_type:
            return
        
        # Get selected command
        selected_rows = self.commands_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        command_id = self.commands_table.item(row, 0).text()
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the command '{command_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Remove command
        self.command_manager.remove_command(self.current_device_type, command_id)
        
        # Reload commands
        self._load_commands(self.current_device_type)
    
    def _save_command(self):
        """Save the current command."""
        if not self.current_device_type:
            return
        
        # Get form values
        command_id = self.command_id_edit.text().strip()
        command_text = self.command_text_edit.text().strip()
        command_desc = self.command_desc_edit.text().strip()
        output_type = self.output_type_combo.currentText()
        
        # Validate inputs
        if not command_id:
            QMessageBox.warning(self, "Validation Error", "Command ID is required.")
            self.command_id_edit.setFocus()
            return
        
        if not command_text:
            QMessageBox.warning(self, "Validation Error", "Command text is required.")
            self.command_text_edit.setFocus()
            return
        
        # Check if this is a new command or update
        is_new = self.current_command_id is None
        
        # If ID changed and new ID already exists, show error
        if (is_new or command_id != self.current_command_id) and command_id in self.command_manager.get_commands_for_device_type(self.current_device_type):
            QMessageBox.warning(self, "Validation Error", f"Command ID '{command_id}' already exists.")
            self.command_id_edit.setFocus()
            return
        
        # If updating existing command with new ID, remove old command
        if not is_new and command_id != self.current_command_id:
            self.command_manager.remove_command(self.current_device_type, self.current_command_id)
        
        # Add or update command
        self.command_manager.add_command(
            self.current_device_type,
            command_id,
            command_text,
            command_desc,
            output_type
        )
        
        # Hide command edit form
        self.command_edit_group.setVisible(False)
        
        # Reload commands
        self._load_commands(self.current_device_type)
        
        # Reset current command ID
        self.current_command_id = None
    
    def _cancel_command_edit(self):
        """Cancel command editing."""
        self.command_edit_group.setVisible(False)
        self.current_command_id = None
    
    def _save_changes(self):
        """Save all changes and close dialog."""
        if not self.current_device_type:
            self.accept()
            return
        
        # Get form values
        new_device_type = self.device_type_edit.text().strip()
        name = self.name_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        
        # Validate inputs
        if not new_device_type:
            QMessageBox.warning(self, "Validation Error", "Device Type ID is required.")
            self.device_type_edit.setFocus()
            return
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Display Name is required.")
            self.name_edit.setFocus()
            return
        
        # Get commands
        commands = self.command_manager.get_commands_for_device_type(self.current_device_type)
        
        # If device type changed, remove old command set
        if new_device_type != self.current_device_type:
            # Check if new device type already exists
            if new_device_type in self.command_manager.get_device_types():
                QMessageBox.warning(self, "Validation Error", f"Device Type ID '{new_device_type}' already exists.")
                self.device_type_edit.setFocus()
                return
            
            # Remove old command set
            self.command_manager.remove_command_set(self.current_device_type)
        
        # Add or update command set
        self.command_manager.add_command_set(
            new_device_type,
            name,
            description,
            commands
        )
        
        # Accept dialog
        self.accept() 