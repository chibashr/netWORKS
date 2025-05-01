#!/usr/bin/env python3
# NetSCAN - Plugin Manager Dialog

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSplitter, QTextEdit,
    QWidget
)
from PySide6.QtCore import Qt

class PluginManagerDialog(QDialog):
    """Dialog for managing plugins."""
    
    def __init__(self, parent, plugin_manager):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Plugin Manager")
        self.resize(800, 500)  # Increased size to accommodate error details
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create splitter for table and error details
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Upper widget for table
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create plugin table
        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(9)  # Added columns for documentation status
        self.plugin_table.setHorizontalHeaderLabels(["ID", "Name", "Version", "Description", "Status", "Type", "README", "API Docs", "Error"])
        self.plugin_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.plugin_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.plugin_table)
        
        # Lower widget for error details
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add error details text area
        error_label = QLabel("Error Details:")
        error_layout.addWidget(error_label)
        
        self.error_details = QTextEdit()
        self.error_details.setReadOnly(True)
        error_layout.addWidget(self.error_details)
        
        # Add widgets to splitter
        splitter.addWidget(table_widget)
        splitter.addWidget(error_widget)
        splitter.setStretchFactor(0, 3)  # Table gets 3/4
        splitter.setStretchFactor(1, 1)  # Error details get 1/4
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.enable_button = QPushButton("Enable")
        self.enable_button.clicked.connect(self.enable_selected_plugin)
        button_layout.addWidget(self.enable_button)
        
        self.disable_button = QPushButton("Disable")
        self.disable_button.clicked.connect(self.disable_selected_plugin)
        button_layout.addWidget(self.disable_button)
        
        self.configure_button = QPushButton("Configure")
        self.configure_button.clicked.connect(self.configure_selected_plugin)
        button_layout.addWidget(self.configure_button)
        
        # Add retry button
        self.retry_button = QPushButton("Retry Load")
        self.retry_button.clicked.connect(self.retry_selected_plugin)
        button_layout.addWidget(self.retry_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # Populate plugin table
        self.refresh_plugin_list()
        
        # Update button states when selection changes
        self.plugin_table.itemSelectionChanged.connect(self.update_button_states)
        self.plugin_table.itemSelectionChanged.connect(self.update_error_details)
    
    def refresh_plugin_list(self):
        """Refresh the plugin list in the table."""
        self.plugin_table.setRowCount(0)
        
        # Get plugin errors
        plugin_errors = self.plugin_manager.get_plugin_errors()
        
        for plugin_id, plugin_info in self.plugin_manager.plugins.items():
            row = self.plugin_table.rowCount()
            self.plugin_table.insertRow(row)
            
            # Get plugin manifest
            manifest = plugin_info["manifest"]
            
            # Store plugin ID in the first column (hidden)
            self.plugin_table.setItem(row, 0, QTableWidgetItem(plugin_id))
            
            # Set visible plugin information
            plugin_name_item = QTableWidgetItem(manifest.get("displayName", plugin_id))
            self.plugin_table.setItem(row, 1, plugin_name_item)
            
            self.plugin_table.setItem(row, 2, QTableWidgetItem(manifest.get("version", "1.0.0")))
            self.plugin_table.setItem(row, 3, QTableWidgetItem(manifest.get("description", "")))
            
            # Check if plugin is core
            is_core = self.plugin_manager.is_core_plugin(plugin_id, plugin_info["path"])
            
            # Set status
            status = "Enabled" if plugin_info["enabled"] else "Disabled"
            if is_core:
                status += " (Core)"
            self.plugin_table.setItem(row, 4, QTableWidgetItem(status))
            
            # Set type
            plugin_type = "Core" if is_core else "Optional"
            self.plugin_table.setItem(row, 5, QTableWidgetItem(plugin_type))
            
            # Set README status
            readme_item = QTableWidgetItem()
            if plugin_info.get("has_readme", False):
                readme_item.setText("✓")
                readme_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                readme_item.setText("✗")
                readme_item.setForeground(Qt.GlobalColor.red)
                readme_item.setToolTip("Missing README.md")
            self.plugin_table.setItem(row, 6, readme_item)
            
            # Set API docs status
            api_docs_item = QTableWidgetItem()
            if plugin_info.get("has_api_docs", False):
                api_docs_item.setText("✓")
                api_docs_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                api_docs_item.setText("✗")
                api_docs_item.setForeground(Qt.GlobalColor.red)
                api_docs_item.setToolTip("Missing API documentation")
            self.plugin_table.setItem(row, 7, api_docs_item)
            
            # Set error status
            error_item = QTableWidgetItem()
            if plugin_id in plugin_errors:
                error_item.setText("Error")
                error_item.setForeground(Qt.GlobalColor.red)
                error_item.setToolTip("Double-click for details")
                
                # Highlight the plugin name for easier identification of problematic plugins
                plugin_name_item.setForeground(Qt.GlobalColor.red)
                plugin_name_item.setToolTip(plugin_errors[plugin_id][:100] + "..." if len(plugin_errors[plugin_id]) > 100 else plugin_errors[plugin_id])
            else:
                error_item.setText("OK")
                error_item.setForeground(Qt.GlobalColor.darkGreen)
            self.plugin_table.setItem(row, 8, error_item)
        
        # Hide the plugin ID column
        self.plugin_table.setColumnHidden(0, True)
        
        # Update the error details
        self.update_error_details()
        
        # If there are errors, select the first problematic plugin automatically
        if plugin_errors:
            for row in range(self.plugin_table.rowCount()):
                plugin_id = self.plugin_table.item(row, 0).text()
                if plugin_id in plugin_errors:
                    self.plugin_table.selectRow(row)
                    break
    
    def update_button_states(self):
        """Update the enable/disable/configure button states based on selection."""
        selected_items = self.plugin_table.selectedItems()
        if not selected_items:
            self.enable_button.setEnabled(False)
            self.disable_button.setEnabled(False)
            self.configure_button.setEnabled(False)
            self.retry_button.setEnabled(False)
            return
        
        row = selected_items[0].row()
        plugin_id = self.plugin_table.item(row, 0).text()  # Get plugin ID from hidden column
        plugin_info = self.plugin_manager.plugins.get(plugin_id)
        plugin_errors = self.plugin_manager.get_plugin_errors()
        
        if plugin_info:
            # Enable/disable buttons based on lock status
            if not plugin_info["locked"]:
                self.enable_button.setEnabled(not plugin_info["enabled"])
                self.disable_button.setEnabled(plugin_info["enabled"])
            else:
                self.enable_button.setEnabled(False)
                self.disable_button.setEnabled(False)
            
            # Configure button is enabled if plugin has a config dialog
            has_config = (
                plugin_info["enabled"] and 
                plugin_info["instance"] is not None and 
                hasattr(plugin_info["instance"], "get_config_panel")
            )
            self.configure_button.setEnabled(has_config)
            
            # Retry button is enabled if there's an error
            self.retry_button.setEnabled(plugin_id in plugin_errors)
        else:
            self.enable_button.setEnabled(False)
            self.disable_button.setEnabled(False)
            self.configure_button.setEnabled(False)
            self.retry_button.setEnabled(False)
    
    def update_error_details(self):
        """Update the error details text area with selected plugin's error."""
        selected_items = self.plugin_table.selectedItems()
        if not selected_items:
            self.error_details.clear()
            return
        
        row = selected_items[0].row()
        plugin_id = self.plugin_table.item(row, 0).text()  # Get plugin ID from hidden column
        plugin_errors = self.plugin_manager.get_plugin_errors()
        
        if plugin_id in plugin_errors:
            # Show error details
            error_msg = plugin_errors[plugin_id]
            self.error_details.setText(f"Plugin: {plugin_id}\n\nError: {error_msg}")
        else:
            self.error_details.clear()
    
    def enable_selected_plugin(self):
        """Enable the selected plugin."""
        selected_items = self.plugin_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        plugin_id = self.plugin_table.item(row, 0).text()  # Get plugin ID from hidden column
        
        # The dialog is shown by the plugin_manager.enable_plugin method
        if self.plugin_manager.enable_plugin(plugin_id):
            # Refresh the plugin list to show updated state
            self.refresh_plugin_list()
    
    def disable_selected_plugin(self):
        """Disable the selected plugin."""
        selected_items = self.plugin_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        plugin_id = self.plugin_table.item(row, 0).text()  # Get plugin ID from hidden column
        
        # The dialog is shown by the plugin_manager.disable_plugin method
        if self.plugin_manager.disable_plugin(plugin_id):
            # Refresh the plugin list to show updated state
            self.refresh_plugin_list()
    
    def retry_selected_plugin(self):
        """Retry loading the selected plugin."""
        selected_items = self.plugin_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        plugin_id = self.plugin_table.item(row, 0).text()  # Get plugin ID from hidden column
        
        # Clear the error for this plugin
        self.plugin_manager.clear_plugin_errors(plugin_id)
        
        # Try to load the plugin again
        if self.plugin_manager.load_plugin(plugin_id):
            # Reload UI components to reflect changes
            if hasattr(self.plugin_manager, 'reload_plugin_components'):
                self.plugin_manager.reload_plugin_components()
                
            QMessageBox.information(
                self,
                "Plugin Loaded",
                f"Plugin '{plugin_id}' was loaded successfully."
            )
        else:
            QMessageBox.warning(
                self,
                "Plugin Load Failed",
                f"Failed to load plugin '{plugin_id}'. See error details for more information."
            )
        
        # Refresh the plugin list
        self.refresh_plugin_list()
    
    def configure_selected_plugin(self):
        """Configure the selected plugin."""
        selected_items = self.plugin_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        plugin_id = self.plugin_table.item(row, 0).text()  # Get plugin ID from hidden column
        
        # Get the config dialog from the plugin
        config_panel = self.plugin_manager.get_plugin_config_dialog(plugin_id)
        if config_panel:
            config_panel.exec()
        else:
            QMessageBox.information(
                self,
                "No Configuration",
                "This plugin does not have a configuration panel."
            ) 