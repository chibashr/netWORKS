#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QToolBar, QToolButton, QComboBox, QMenu, QInputDialog,
    QMessageBox, QFileDialog, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy
)
from PySide6.QtGui import QIcon, QAction

class WorkspaceToolbar(QWidget):
    """Toolbar widget for workspace management."""
    
    # Define signals
    workspace_changed = Signal(dict)  # Emits metadata of newly selected workspace
    pin_toggled = Signal(bool)
    
    def __init__(self, parent=None):
        """Initialize the workspace toolbar.
        
        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.workspace_manager = None
        self.current_workspace = None
        self.workspaces = []
        
        # Setup UI
        self.setup_ui()
        
        # No workspaces yet
        self.workspace_menu_button.setEnabled(False)
        
        self.logger.debug("Workspace toolbar initialized")
    
    def setup_ui(self):
        """Set up the toolbar UI components."""
        # Create main layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.setLayout(layout)
        
        # Workspace menu button with dropdown
        self.workspace_menu_button = QToolButton()
        self.workspace_menu_button.setText("Workspaces")
        self.workspace_menu_button.setPopupMode(QToolButton.InstantPopup)
        
        # Create menu for the button
        self.workspace_menu = QMenu()
        self.workspace_menu_button.setMenu(self.workspace_menu)
        
        # Add pin/unpin functionality
        self.pinned = True  # Default to pinned
        
        # Create pin/unpin button
        self.pin_button = QToolButton()
        self.pin_button.setText("Unpin")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(self.pinned)
        self.pin_button.toggled.connect(self.toggle_pin)
        
        # Add buttons to layout
        layout.addWidget(self.workspace_menu_button)
        layout.addWidget(self.pin_button)
        
        # Add spacer to push buttons to left
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(spacer)
    
    def set_workspace_manager(self, workspace_manager):
        """Set the workspace manager and update available workspaces.
        
        Args:
            workspace_manager: The workspace manager instance
        """
        self.workspace_manager = workspace_manager
        self.update_workspaces()
    
    def update_workspaces(self):
        """Update the list of workspaces in the menu."""
        if not self.workspace_manager:
            return
            
        # Clear existing menu items
        self.workspace_menu.clear()
        
        # Get workspaces from manager
        self.workspaces = self.workspace_manager.get_workspaces()
        
        if not self.workspaces:
            self.workspace_menu_button.setEnabled(False)
            return
            
        self.workspace_menu_button.setEnabled(True)
        
        # Add workspace actions
        for workspace in self.workspaces:
            action = QAction(workspace['name'], self)
            action.setData(workspace)
            action.triggered.connect(lambda checked, w=workspace: self.select_workspace(w))
            self.workspace_menu.addAction(action)
            
        # Add separator and management actions
        self.workspace_menu.addSeparator()
        
        # New workspace action
        new_action = QAction("New Workspace...", self)
        new_action.triggered.connect(self.create_new_workspace)
        self.workspace_menu.addAction(new_action)
        
        # Import workspace action
        import_action = QAction("Import Workspace...", self)
        import_action.triggered.connect(self.import_workspace)
        self.workspace_menu.addAction(import_action)
        
        if self.current_workspace:
            # Export workspace action
            export_action = QAction("Export Current Workspace...", self)
            export_action.triggered.connect(self.export_workspace)
            self.workspace_menu.addAction(export_action)
            
            # Delete workspace action 
            delete_action = QAction("Delete Current Workspace", self)
            delete_action.triggered.connect(self.delete_workspace)
            self.workspace_menu.addAction(delete_action)
    
    def select_workspace(self, workspace):
        """Select a workspace and emit change signal.
        
        Args:
            workspace: The workspace metadata to select
        """
        if workspace != self.current_workspace:
            self.current_workspace = workspace
            self.workspace_menu_button.setText(workspace['name'])
            self.workspace_changed.emit(workspace)
            self.logger.info(f"Workspace changed to {workspace['name']}")
    
    def create_new_workspace(self):
        """Show dialog to create a new workspace."""
        name, ok = QInputDialog.getText(
            self, 
            "Create New Workspace",
            "Enter name for new workspace:"
        )
        
        if ok and name:
            try:
                workspace = self.workspace_manager.create_workspace(name)
                self.update_workspaces()
                self.select_workspace(workspace)
                self.logger.info(f"Created new workspace: {name}")
            except Exception as e:
                self.logger.error(f"Failed to create workspace: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Workspace Creation Failed",
                    f"Could not create workspace: {str(e)}"
                )
    
    def import_workspace(self):
        """Import a workspace from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Workspace",
            "",
            "Workspace Files (*.workspace);;All Files (*)"
        )
        
        if file_path:
            try:
                workspace = self.workspace_manager.import_workspace(file_path)
                self.update_workspaces()
                self.select_workspace(workspace)
                self.logger.info(f"Imported workspace from {file_path}")
            except Exception as e:
                self.logger.error(f"Failed to import workspace: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Workspace Import Failed",
                    f"Could not import workspace: {str(e)}"
                )
    
    def export_workspace(self):
        """Export the current workspace to file."""
        if not self.current_workspace:
            return
            
        suggested_name = f"{self.current_workspace['name']}.workspace"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Workspace",
            suggested_name,
            "Workspace Files (*.workspace);;All Files (*)"
        )
        
        if file_path:
            try:
                self.workspace_manager.export_workspace(
                    self.current_workspace['id'],
                    file_path
                )
                self.logger.info(f"Exported workspace to {file_path}")
            except Exception as e:
                self.logger.error(f"Failed to export workspace: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Workspace Export Failed",
                    f"Could not export workspace: {str(e)}"
                )
    
    def delete_workspace(self):
        """Delete the current workspace after confirmation."""
        if not self.current_workspace:
            return
            
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete workspace '{self.current_workspace['name']}'?\nThis cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            try:
                workspace_id = self.current_workspace['id']
                self.workspace_manager.delete_workspace(workspace_id)
                self.current_workspace = None
                self.update_workspaces()
                
                # Select first workspace if available
                if self.workspaces:
                    self.select_workspace(self.workspaces[0])
                else:
                    self.workspace_menu_button.setText("Workspaces")
                    
                self.logger.info(f"Deleted workspace {workspace_id}")
            except Exception as e:
                self.logger.error(f"Failed to delete workspace: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Workspace Deletion Failed",
                    f"Could not delete workspace: {str(e)}"
                )
    
    def toggle_pin(self, checked):
        """Toggle the pin state of the toolbar."""
        self.pinned = checked
        self.pin_button.setText("Unpin" if self.pinned else "Pin")
        self.pin_toggled.emit(self.pinned)
    
    def handle_pin_state_changed(self, is_pinned):
        """Update the display based on pin state."""
        self.pinned = is_pinned
        self.pin_button.setChecked(is_pinned) 