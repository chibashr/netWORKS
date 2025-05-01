#!/usr/bin/env python3
# netWORKS - Workspace Selection Dialog

import os
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QPushButton, QToolButton, QInputDialog, QMessageBox,
    QListWidgetItem, QFrame, QSplitter, QWidget, QGridLayout,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFont

class WorkspaceSelectionDialog(QDialog):
    """Dialog for selecting or creating a workspace on startup."""
    
    workspace_selected = Signal(str)  # Emits workspace ID
    
    def __init__(self, workspace_manager, parent=None):
        """Initialize the workspace selection dialog.
        
        Args:
            workspace_manager: The workspace manager instance
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.logger = logging.getLogger(__name__)
        self.selected_workspace_id = None
        
        self.setWindowTitle("Select Workspace")
        self.setMinimumSize(600, 400)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        # Setup UI
        self.setup_ui()
        
        # Populate workspace list
        self.populate_workspaces()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Welcome label
        welcome_label = QLabel("Welcome to netWORKS")
        welcome_font = QFont()
        welcome_font.setPointSize(16)
        welcome_font.setBold(True)
        welcome_label.setFont(welcome_font)
        layout.addWidget(welcome_label)
        
        # Instructions label
        instructions = QLabel("Select an existing workspace or create a new one to continue:")
        layout.addWidget(instructions)
        
        # Workspace list section
        list_frame = QFrame()
        list_frame.setFrameShape(QFrame.StyledPanel)
        list_frame.setLineWidth(1)
        list_layout = QVBoxLayout(list_frame)
        
        # List widget for workspaces
        self.workspace_list = QListWidget()
        self.workspace_list.setMinimumHeight(200)
        self.workspace_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.workspace_list.itemDoubleClicked.connect(self.accept)
        list_layout.addWidget(self.workspace_list)
        
        # Workspace management buttons
        btn_layout = QHBoxLayout()
        
        # New workspace button
        self.new_btn = QPushButton("New Workspace...")
        self.new_btn.clicked.connect(self.create_new_workspace)
        btn_layout.addWidget(self.new_btn)
        
        # Delete workspace button
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_workspace)
        btn_layout.addWidget(self.delete_btn)
        
        # Rename workspace button
        self.rename_btn = QPushButton("Rename")
        self.rename_btn.setEnabled(False)
        self.rename_btn.clicked.connect(self.rename_workspace)
        btn_layout.addWidget(self.rename_btn)
        
        # Add button layout to list section
        list_layout.addLayout(btn_layout)
        
        # Add list frame to main layout
        layout.addWidget(list_frame)
        
        # Action buttons at the bottom
        action_layout = QHBoxLayout()
        
        # Spacer to push buttons to the right
        action_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Open button
        self.open_btn = QPushButton("Open")
        self.open_btn.setDefault(True)
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.accept)
        action_layout.addWidget(self.open_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)
        
        layout.addLayout(action_layout)
    
    def populate_workspaces(self):
        """Populate the list with available workspaces."""
        try:
            self.workspace_list.clear()
            
            workspaces = self.workspace_manager.get_workspaces()
            if not workspaces:
                # Create a default workspace if none exist
                try:
                    self.logger.info("No workspaces found, creating default workspace")
                    default_id = self.workspace_manager._create_default_workspace()
                    if default_id:
                        workspaces = self.workspace_manager.get_workspaces()
                except Exception as e:
                    self.logger.error(f"Error creating default workspace: {str(e)}")
                    # Show a message if we couldn't create a default workspace
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self,
                        "Workspace Error",
                        f"Failed to create default workspace: {str(e)}\n\nPlease try creating a new workspace manually."
                    )
            
            for workspace_id, metadata in workspaces.items():
                try:
                    item = QListWidgetItem()
                    item.setText(f"{metadata['name']}")
                    item.setData(Qt.UserRole, workspace_id)
                    # Add tooltip with more information
                    tooltip = (f"Name: {metadata['name']}\n"
                              f"Created: {metadata['created']}\n"
                              f"Last modified: {metadata['last_modified']}\n"
                              f"Devices: {metadata.get('devices_count', 0)}\n"
                              f"Device groups: {metadata.get('device_groups_count', 0)}\n"
                              f"Description: {metadata.get('description', '')}")
                    item.setToolTip(tooltip)
                    self.workspace_list.addItem(item)
                except Exception as e:
                    self.logger.error(f"Error adding workspace to list: {str(e)}")
            
            # Select the first item if available
            if self.workspace_list.count() > 0:
                self.workspace_list.setCurrentRow(0)
        except Exception as e:
            self.logger.error(f"Error populating workspaces: {str(e)}", exc_info=True)
    
    def on_selection_changed(self):
        """Handle workspace selection change."""
        has_selection = len(self.workspace_list.selectedItems()) > 0
        self.open_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.rename_btn.setEnabled(has_selection)
        
        if has_selection:
            item = self.workspace_list.currentItem()
            self.selected_workspace_id = item.data(Qt.UserRole)
    
    def create_new_workspace(self):
        """Create a new workspace."""
        name, ok = QInputDialog.getText(
            self, 
            "Create New Workspace",
            "Enter name for the new workspace:"
        )
        
        if ok and name:
            try:
                workspace_id = self.workspace_manager.create_workspace(name)
                if workspace_id:
                    self.populate_workspaces()
                    
                    # Select the newly created workspace
                    for i in range(self.workspace_list.count()):
                        item = self.workspace_list.item(i)
                        if item.data(Qt.UserRole) == workspace_id:
                            self.workspace_list.setCurrentItem(item)
                            break
            except Exception as e:
                self.logger.error(f"Failed to create workspace: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Workspace Creation Failed",
                    f"Could not create workspace: {str(e)}"
                )
    
    def delete_workspace(self):
        """Delete the selected workspace."""
        if not self.selected_workspace_id:
            return
            
        # Get the workspace name
        item = self.workspace_list.currentItem()
        workspace_name = item.text()
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete workspace '{workspace_name}'?\nThis cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            try:
                self.workspace_manager.delete_workspace(self.selected_workspace_id)
                self.populate_workspaces()
            except Exception as e:
                self.logger.error(f"Failed to delete workspace: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Workspace Deletion Failed",
                    f"Could not delete workspace: {str(e)}"
                )
    
    def rename_workspace(self):
        """Rename the selected workspace."""
        if not self.selected_workspace_id:
            return
            
        # Get the current workspace name
        item = self.workspace_list.currentItem()
        current_name = item.text()
        
        # Get new name
        new_name, ok = QInputDialog.getText(
            self, 
            "Rename Workspace",
            "Enter new name for the workspace:",
            text=current_name
        )
        
        if ok and new_name and new_name != current_name:
            try:
                success = self.workspace_manager.rename_workspace(self.selected_workspace_id, new_name)
                if success:
                    self.populate_workspaces()
                    
                    # Reselect the renamed workspace
                    for i in range(self.workspace_list.count()):
                        item = self.workspace_list.item(i)
                        if item.data(Qt.UserRole) == self.selected_workspace_id:
                            self.workspace_list.setCurrentItem(item)
                            break
            except Exception as e:
                self.logger.error(f"Failed to rename workspace: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Workspace Rename Failed",
                    f"Could not rename workspace: {str(e)}"
                )
    
    def accept(self):
        """Handle OK/Accept button."""
        if self.selected_workspace_id:
            self.workspace_selected.emit(self.selected_workspace_id)
            super().accept()
        else:
            QMessageBox.warning(
                self,
                "No Workspace Selected",
                "Please select a workspace or create a new one to continue."
            )
    
    def reject(self):
        """Handle Cancel/Reject button."""
        # If there are workspaces but none selected, select the first one
        if self.workspace_list.count() > 0 and not self.selected_workspace_id:
            self.workspace_list.setCurrentRow(0)
            self.selected_workspace_id = self.workspace_list.currentItem().data(Qt.UserRole)
            self.workspace_selected.emit(self.selected_workspace_id)
            super().accept()
        else:
            # Otherwise proceed with normal rejection
            super().reject() 