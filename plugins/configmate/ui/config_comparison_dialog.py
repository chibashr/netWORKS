#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Comparison Dialog for ConfigMate Plugin

Provides side-by-side configuration comparison with diff highlighting,
inspired by Notepad++ comparison but with a more user-friendly interface.
"""

import difflib
from typing import List, Dict, Any, Optional
from pathlib import Path

from loguru import logger
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTextEdit, QLabel, QPushButton, QComboBox, QCheckBox,
    QSplitter, QGroupBox, QTabWidget, QWidget, QScrollArea,
    QMessageBox, QFileDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialogButtonBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor, QSyntaxHighlighter

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


class DiffHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for diff display with color coding"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Define formats for different diff types
        self.added_format = QTextCharFormat()
        self.added_format.setBackground(QColor(200, 255, 200))  # Light green
        
        self.removed_format = QTextCharFormat()
        self.removed_format.setBackground(QColor(255, 200, 200))  # Light red
        
        self.changed_format = QTextCharFormat()
        self.changed_format.setBackground(QColor(255, 255, 200))  # Light yellow
        
        self.line_number_format = QTextCharFormat()
        self.line_number_format.setForeground(QColor(128, 128, 128))
    
    def highlightBlock(self, text):
        """Apply diff highlighting to text blocks"""
        if text.startswith('+ '):
            self.setFormat(0, len(text), self.added_format)
        elif text.startswith('- '):
            self.setFormat(0, len(text), self.removed_format)
        elif text.startswith('? '):
            self.setFormat(0, len(text), self.changed_format)
        elif text.startswith('@@ '):
            self.setFormat(0, len(text), self.line_number_format)


class ComparisonWorker(QObject):
    """Worker thread for performing configuration comparisons"""
    
    progress_updated = Signal(int)
    comparison_completed = Signal(object)  # ComparisonResult
    error_occurred = Signal(str)
    
    def __init__(self, devices, plugin):
        super().__init__()
        self.devices = devices
        self.plugin = plugin
    
    def run(self):
        """Perform the comparison in a separate thread"""
        try:
            self.progress_updated.emit(10)
            
            # Get configurations for all devices
            configs = {}
            for i, device in enumerate(self.devices):
                device_id = device.id  # Use device.id instead of device.device_id
                config = self.plugin._get_device_config(device)
                configs[device_id] = {
                    'device': device,
                    'config': config or "No configuration available"
                }
                progress = 10 + (i + 1) * 40 // len(self.devices)
                self.progress_updated.emit(progress)
            
            self.progress_updated.emit(60)
            
            # Perform comparison
            if len(self.devices) == 2:
                # Two-device comparison using the correct method
                device1, device2 = self.devices
                result = self.plugin.config_comparator.compare_devices(
                    device1, device2, 
                    command="show running-config",
                    ignore_timestamps=True,
                    ignore_comments=True,
                    context_lines=3
                )
            else:
                # Multi-device comparison using the correct method
                result = self.plugin.config_comparator.compare_multiple_devices(
                    self.devices, 
                    command="show running-config"
                )
            
            self.progress_updated.emit(100)
            self.comparison_completed.emit(result)
            
        except Exception as e:
            logger.error(f"Error in comparison worker: {e}")
            self.error_occurred.emit(str(e))


class ConfigComparisonDialog(QDialog):
    """
    Configuration comparison dialog for side-by-side diff viewing
    
    Features:
    - Side-by-side configuration comparison
    - Syntax highlighting with diff colors
    - Export comparison results
    - Filtering and ignore options
    - Multiple device comparison support
    """
    
    def __init__(self, devices, plugin, parent=None):
        """Initialize the configuration comparison dialog"""
        super().__init__(parent)
        self.devices = devices
        self.plugin = plugin
        self.comparison_result = None
        self.diff_highlighter1 = None
        self.diff_highlighter2 = None
        
        # Set up dialog
        self.setWindowTitle("Configuration Comparison")
        self.setModal(True)
        self.resize(1400, 900)
        
        # Create UI
        self._create_ui()
        self._connect_signals()
        
        # Start comparison
        self._start_comparison()
        
        logger.debug("ConfigComparisonDialog initialized")
        logger.info(f"Comparing {len(devices)} devices")
    
    def _create_ui(self):
        """Create the user interface"""
        layout = QVBoxLayout(self)
        
        # Device info header
        header_layout = QHBoxLayout()
        device_names = [device.get_property('name', 'Unknown') for device in self.devices]
        header_label = QLabel(f"Comparing: {', '.join(device_names)}")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Main content area
        if len(self.devices) == 2:
            content_widget = self._create_two_device_comparison()
        else:
            content_widget = self._create_multi_device_comparison()
        
        layout.addWidget(content_widget)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("Export Results")
        self.export_btn.setEnabled(False)
        
        self.refresh_btn = QPushButton("Refresh")
        
        self.settings_btn = QPushButton("Settings")
        
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.settings_btn)
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_two_device_comparison(self) -> QWidget:
        """Create UI for two-device side-by-side comparison"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Device and Command Selection
        selection_group = QGroupBox("Device and Command Selection")
        selection_layout = QGridLayout(selection_group)
        
        # Device 1 selection
        self.device1_combo = QComboBox()
        self._populate_device_combo(self.device1_combo, selected_index=0)
        selection_layout.addWidget(QLabel("Device 1:"), 0, 0)
        selection_layout.addWidget(self.device1_combo, 0, 1)
        
        # Device 2 selection
        self.device2_combo = QComboBox()
        self._populate_device_combo(self.device2_combo, selected_index=1 if len(self.devices) > 1 else 0)
        selection_layout.addWidget(QLabel("Device 2:"), 0, 2)
        selection_layout.addWidget(self.device2_combo, 0, 3)
        
        # Command selection for Device 1
        self.command1_combo = QComboBox()
        self.command1_combo.setEditable(True)
        self._populate_command_combo(self.command1_combo, 0)
        selection_layout.addWidget(QLabel("Command 1:"), 1, 0)
        selection_layout.addWidget(self.command1_combo, 1, 1)
        
        # Command selection for Device 2
        self.command2_combo = QComboBox()
        self.command2_combo.setEditable(True)
        self._populate_command_combo(self.command2_combo, 1 if len(self.devices) > 1 else 0)
        selection_layout.addWidget(QLabel("Command 2:"), 1, 2)
        selection_layout.addWidget(self.command2_combo, 1, 3)
        
        # Connect device combo changes to update command combos
        self.device1_combo.currentIndexChanged.connect(lambda: self._update_command_combo_for_device(self.command1_combo, self.device1_combo.currentIndex()))
        self.device2_combo.currentIndexChanged.connect(lambda: self._update_command_combo_for_device(self.command2_combo, self.device2_combo.currentIndex()))
        
        # Refresh button for selections
        refresh_selection_btn = QPushButton("Update Comparison")
        refresh_selection_btn.clicked.connect(self._update_comparison_from_selection)
        selection_layout.addWidget(refresh_selection_btn, 2, 0, 1, 4)
        
        layout.addWidget(selection_group)
        
        # Comparison options
        options_group = QGroupBox("Comparison Options")
        options_layout = QHBoxLayout(options_group)
        
        self.ignore_whitespace_cb = QCheckBox("Ignore whitespace")
        self.ignore_whitespace_cb.setChecked(True)
        
        self.ignore_comments_cb = QCheckBox("Ignore comments")
        self.ignore_comments_cb.setChecked(True)
        
        self.context_lines_spin = QSpinBox()
        self.context_lines_spin.setRange(0, 20)
        self.context_lines_spin.setValue(3)
        
        options_layout.addWidget(self.ignore_whitespace_cb)
        options_layout.addWidget(self.ignore_comments_cb)
        options_layout.addWidget(QLabel("Context lines:"))
        options_layout.addWidget(self.context_lines_spin)
        options_layout.addStretch()
        
        layout.addWidget(options_group)
        
        # Create tab widget for different views
        tab_widget = QTabWidget()
        
        # Side-by-side view
        side_by_side_widget = self._create_side_by_side_view()
        tab_widget.addTab(side_by_side_widget, "Side by Side")
        
        # Unified diff view
        unified_diff_widget = self._create_unified_diff_view()
        tab_widget.addTab(unified_diff_widget, "Unified Diff")
        
        # Statistics view
        stats_widget = self._create_statistics_view()
        tab_widget.addTab(stats_widget, "Statistics")
        
        layout.addWidget(tab_widget)
        
        # Store tab widget reference
        self.tab_widget = tab_widget
        
        return widget
    
    def _create_side_by_side_view(self) -> QWidget:
        """Create side-by-side comparison view"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(2)  # Minimal spacing between elements
        layout.setContentsMargins(5, 2, 5, 5)  # Reduce top margin significantly
        
        # Device labels - compact with IP addresses
        labels_layout = QHBoxLayout()
        labels_layout.setContentsMargins(2, 1, 2, 1)  # Very small margins
        labels_layout.setSpacing(1)  # Minimal spacing between labels
        
        device1_name = self.devices[0].get_property('name', 'Device 1')
        device1_ip = self.devices[0].get_property('ip_address', 'No IP')
        device1_label = QLabel(f"{device1_name} ({device1_ip})")
        device1_label.setStyleSheet("font-weight: bold; padding: 2px 4px; font-size: 10px; background-color: #f8f8f8; border: 1px solid #ddd; margin: 0px;")
        device1_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        device1_label.setMaximumHeight(20)  # Constrain height
        
        device2_name = self.devices[1].get_property('name', 'Device 2') 
        device2_ip = self.devices[1].get_property('ip_address', 'No IP')
        device2_label = QLabel(f"{device2_name} ({device2_ip})")
        device2_label.setStyleSheet("font-weight: bold; padding: 2px 4px; font-size: 10px; background-color: #f8f8f8; border: 1px solid #ddd; margin: 0px;")
        device2_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        device2_label.setMaximumHeight(20)  # Constrain height
        
        labels_layout.addWidget(device1_label)
        labels_layout.addWidget(device2_label)
        layout.addLayout(labels_layout)
        
        # Linked scrolling control - more compact
        scroll_control_layout = QHBoxLayout()
        scroll_control_layout.setContentsMargins(2, 0, 2, 0)  # No vertical margins
        scroll_control_layout.setSpacing(5)
        
        self.link_scrolling_checkbox = QCheckBox("Link scrolling")
        self.link_scrolling_checkbox.setChecked(True)
        self.link_scrolling_checkbox.setToolTip("Synchronize scrolling between the two configuration views")
        self.link_scrolling_checkbox.setStyleSheet("font-size: 9px; margin: 0px; padding: 1px;")  # Smaller font
        scroll_control_layout.addWidget(self.link_scrolling_checkbox)
        scroll_control_layout.addStretch()
        
        layout.addLayout(scroll_control_layout)
        
        # Text editors in splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.config1_editor = QTextEdit()
        self.config1_editor.setFont(QFont("Consolas", 10))
        self.config1_editor.setReadOnly(True)
        self.config1_editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        self.config2_editor = QTextEdit()
        self.config2_editor.setFont(QFont("Consolas", 10))
        self.config2_editor.setReadOnly(True)
        self.config2_editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        splitter.addWidget(self.config1_editor)
        splitter.addWidget(self.config2_editor)
        splitter.setSizes([700, 700])
        
        layout.addWidget(splitter)
        
        # Connect linked scrolling
        self._setup_linked_scrolling()
        
        return widget
    
    def _setup_linked_scrolling(self):
        """Set up linked scrolling between the two text editors"""
        try:
            # Get scroll bars
            self.scrollbar1 = self.config1_editor.verticalScrollBar()
            self.scrollbar2 = self.config2_editor.verticalScrollBar()
            
            # Track which editor is being scrolled to avoid infinite loops
            self._scrolling_from_editor1 = False
            self._scrolling_from_editor2 = False
            
            # Connect scroll events
            self.scrollbar1.valueChanged.connect(self._on_editor1_scroll)
            self.scrollbar2.valueChanged.connect(self._on_editor2_scroll)
            
            # Connect link checkbox
            self.link_scrolling_checkbox.toggled.connect(self._on_link_scrolling_toggled)
            
        except Exception as e:
            logger.error(f"Error setting up linked scrolling: {e}")
    
    def _on_editor1_scroll(self, value):
        """Handle scrolling in editor 1"""
        if self.link_scrolling_checkbox.isChecked() and not self._scrolling_from_editor2:
            self._scrolling_from_editor1 = True
            # Sync scroll position as percentage
            max1 = self.scrollbar1.maximum()
            max2 = self.scrollbar2.maximum()
            if max1 > 0 and max2 > 0:
                percentage = value / max1
                new_value = int(percentage * max2)
                self.scrollbar2.setValue(new_value)
            self._scrolling_from_editor1 = False
    
    def _on_editor2_scroll(self, value):
        """Handle scrolling in editor 2"""
        if self.link_scrolling_checkbox.isChecked() and not self._scrolling_from_editor1:
            self._scrolling_from_editor2 = True
            # Sync scroll position as percentage
            max2 = self.scrollbar2.maximum()
            max1 = self.scrollbar1.maximum()
            if max2 > 0 and max1 > 0:
                percentage = value / max2
                new_value = int(percentage * max1)
                self.scrollbar1.setValue(new_value)
            self._scrolling_from_editor2 = False
    
    def _on_link_scrolling_toggled(self, checked):
        """Handle link scrolling checkbox toggle"""
        if checked:
            # Sync to editor 1's position when linking is enabled
            self._on_editor1_scroll(self.scrollbar1.value())
    
    def _create_unified_diff_view(self) -> QWidget:
        """Create unified diff view"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.unified_diff_editor = QTextEdit()
        self.unified_diff_editor.setFont(QFont("Consolas", 10))
        self.unified_diff_editor.setReadOnly(True)
        
        layout.addWidget(self.unified_diff_editor)
        
        return widget
    
    def _create_statistics_view(self) -> QWidget:
        """Create statistics view"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.stats_table)
        
        return widget
    
    def _create_multi_device_comparison(self) -> QWidget:
        """Create UI for multi-device comparison"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create tab widget for each device pair
        tab_widget = QTabWidget()
        
        # Add tabs for each device comparison
        for i, device1 in enumerate(self.devices):
            for j, device2 in enumerate(self.devices[i+1:], i+1):
                tab_name = f"{device1.get_property('name', f'Device {i+1}')} vs {device2.get_property('name', f'Device {j+1}')}"
                
                # Create comparison widget for this pair
                comparison_widget = self._create_device_pair_widget(device1, device2)
                tab_widget.addTab(comparison_widget, tab_name)
        
        layout.addWidget(tab_widget)
        
        return widget
    
    def _create_device_pair_widget(self, device1, device2) -> QWidget:
        """Create comparison widget for a specific device pair"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Placeholder for device pair comparison
        # This would contain similar side-by-side view as the two-device comparison
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        editor1 = QTextEdit()
        editor1.setFont(QFont("Consolas", 10))
        editor1.setReadOnly(True)
        editor1.setPlaceholderText(f"Configuration for {device1.get_property('name', 'Device 1')}")
        
        editor2 = QTextEdit()
        editor2.setFont(QFont("Consolas", 10))
        editor2.setReadOnly(True)
        editor2.setPlaceholderText(f"Configuration for {device2.get_property('name', 'Device 2')}")
        
        splitter.addWidget(editor1)
        splitter.addWidget(editor2)
        
        layout.addWidget(splitter)
        
        return widget
    
    def _connect_signals(self):
        """Connect UI signals to handlers"""
        self.export_btn.clicked.connect(self._export_results)
        self.refresh_btn.clicked.connect(self._refresh_comparison)
        self.settings_btn.clicked.connect(self._show_settings)
        
        # Connect comparison option changes
        if hasattr(self, 'ignore_whitespace_cb'):
            self.ignore_whitespace_cb.toggled.connect(self._update_comparison)
            self.ignore_comments_cb.toggled.connect(self._update_comparison)
            self.context_lines_spin.valueChanged.connect(self._update_comparison)
    
    def _start_comparison(self):
        """Start the configuration comparison process"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Create worker thread
        self.worker_thread = QThread()
        self.worker = ComparisonWorker(self.devices, self.plugin)
        self.worker.moveToThread(self.worker_thread)
        
        # Connect worker signals
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.comparison_completed.connect(self._on_comparison_completed)
        self.worker.error_occurred.connect(self._on_comparison_error)
        
        # Start worker
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()
    
    def _on_comparison_completed(self, result):
        """Handle completion of comparison"""
        self.comparison_result = result
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        
        # Update UI with results
        self._display_comparison_results()
        
        # Clean up worker thread
        self.worker_thread.quit()
        self.worker_thread.wait()
    
    def _on_comparison_error(self, error_message):
        """Handle comparison error"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Comparison Error", f"Failed to compare configurations:\n{error_message}")
        
        # Clean up worker thread
        self.worker_thread.quit()
        self.worker_thread.wait()
    
    def _display_comparison_results(self):
        """Display the comparison results in the UI"""
        if not self.comparison_result:
            return
        
        try:
            if len(self.devices) == 2:
                self._display_two_device_results()
            else:
                self._display_multi_device_results()
                
        except Exception as e:
            logger.error(f"Error displaying comparison results: {e}")
            QMessageBox.warning(self, "Display Error", f"Error displaying results: {e}")
    
    def _display_two_device_results(self):
        """Display results for two-device comparison"""
        result = self.comparison_result
        
        # Display side-by-side configurations with highlighting
        self.config1_editor.setPlainText(result.device1_config)
        self.config2_editor.setPlainText(result.device2_config)
        
        # Apply diff highlighting
        self.diff_highlighter1 = DiffHighlighter(self.config1_editor.document())
        self.diff_highlighter2 = DiffHighlighter(self.config2_editor.document())
        
        # Display unified diff
        unified_diff = '\n'.join(result.unified_diff)
        self.unified_diff_editor.setPlainText(unified_diff)
        
        # Apply diff highlighting to unified view
        DiffHighlighter(self.unified_diff_editor.document())
        
        # Display statistics
        self._display_statistics(result)
    
    def _display_multi_device_results(self):
        """Display results for multi-device comparison"""
        # Implementation for multi-device results
        # This would populate the various tabs with comparison results
        pass
    
    def _display_statistics(self, result):
        """Display comparison statistics"""
        stats = [
            ("Total Lines (Device 1)", len(result.device1_config.splitlines())),
            ("Total Lines (Device 2)", len(result.device2_config.splitlines())),
            ("Added Lines", result.statistics.get('lines_added', 0)),
            ("Removed Lines", result.statistics.get('lines_removed', 0)),
            ("Modified Lines", result.statistics.get('difference_count', 0)),
            ("Unchanged Lines", result.statistics.get('lines_unchanged', 0)),
            ("Similarity %", f"{result.statistics.get('similarity_ratio', 0)*100:.1f}%")
        ]
        
        self.stats_table.setRowCount(len(stats))
        
        for i, (metric, value) in enumerate(stats):
            self.stats_table.setItem(i, 0, QTableWidgetItem(metric))
            self.stats_table.setItem(i, 1, QTableWidgetItem(str(value)))
    
    def _update_comparison(self):
        """Update comparison with new options"""
        if self.comparison_result:
            # Re-process the comparison with new options
            self._display_comparison_results()
    
    def _refresh_comparison(self):
        """Refresh the comparison by re-fetching configurations"""
        self._start_comparison()
    
    def _show_settings(self):
        """Show comparison settings dialog"""
        # This would open a settings dialog for comparison options
        QMessageBox.information(self, "Settings", "Comparison settings dialog - Coming Soon")
    
    def _export_results(self):
        """Export comparison results to file"""
        if not self.comparison_result:
            QMessageBox.warning(self, "Warning", "No comparison results to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Comparison Results", 
            f"comparison_{'-'.join([d.get_property('name', 'device') for d in self.devices])}.html",
            "HTML Files (*.html);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.html'):
                    self._export_html(file_path)
                else:
                    self._export_text(file_path)
                
                QMessageBox.information(self, "Success", "Comparison results exported successfully")
                
            except Exception as e:
                logger.error(f"Error exporting results: {e}")
                QMessageBox.critical(self, "Export Error", f"Failed to export results: {e}")
    
    def _export_html(self, file_path):
        """Export results as HTML"""
        html_content = self.comparison_result.to_html()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _export_text(self, file_path):
        """Export results as plain text"""
        text_content = self.comparison_result.to_text()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)

    def _populate_command_combo(self, combo, device_index):
        """Populate the command combo with available commands for a device"""
        try:
            combo.clear()  # Clear existing items
            
            # Get the device from available devices (initially uses original devices)
            devices_to_use = getattr(self, 'all_available_devices', self.devices)
            
            # If device index is provided, get actual commands from device
            if device_index is not None and device_index < len(devices_to_use):
                device = devices_to_use[device_index]
                available_commands = self._get_device_commands(device)
                
                if available_commands:
                    # Add actual device commands
                    combo.addItems(available_commands)
                    # Set default to show running-config if available
                    if "show running-config" in available_commands:
                        combo.setCurrentText("show running-config")
                    else:
                        combo.setCurrentIndex(0)  # Select first available command
                    
                    logger.debug(f"Populated command combo for device {device_index} with {len(available_commands)} commands")
                else:
                    # No commands found, show informative message
                    combo.addItem("No commands available")
                    logger.warning(f"No cached commands found for device {device.get_property('name', 'Unknown')}")
            else:
                # Fallback: add some default commands if no device specified
                default_commands = [
                    "show running-config",
                    "show version",
                    "show interface status"
                ]
                combo.addItems(default_commands)
                combo.setCurrentText("show running-config")
                logger.debug("Populated command combo with default commands (no device specified)")
                            
        except Exception as e:
            logger.error(f"Error populating command combo: {e}")
            # Fallback: add basic commands
            combo.clear()
            combo.addItems(["show running-config", "show version"])
            combo.setCurrentText("show running-config")
    
    def _get_device_commands(self, device):
        """Get available commands for a device from cached outputs"""
        try:
            # Use the plugin's new method to get available commands
            if hasattr(self.plugin, '_get_device_available_commands'):
                return self.plugin._get_device_available_commands(device)
            
            # Fallback: try to access command outputs directly (old method)
            if hasattr(device, 'command_outputs') and device.command_outputs:
                return list(device.command_outputs.keys())
            elif hasattr(device, 'get_command_outputs'):
                outputs = device.get_command_outputs()
                if outputs:
                    return list(outputs.keys())
                    
            return []
            
        except Exception as e:
            logger.debug(f"Error getting device commands: {e}")
            return []
    
    def _update_comparison_from_selection(self):
        """Update comparison based on selected devices and commands"""
        try:
            # Get selected devices from all available devices
            device1_index = self.device1_combo.currentIndex()
            device2_index = self.device2_combo.currentIndex()
            
            available_devices = getattr(self, 'all_available_devices', self.devices)
            
            if device1_index >= len(available_devices) or device2_index >= len(available_devices):
                QMessageBox.warning(self, "Selection Error", "Invalid device selection")
                return
            
            device1 = available_devices[device1_index]
            device2 = available_devices[device2_index]
            
            # Get selected commands
            command1 = self.command1_combo.currentText().strip()
            command2 = self.command2_combo.currentText().strip()
            
            if not command1 or not command2:
                QMessageBox.warning(self, "Selection Error", "Please select commands for both devices")
                return
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Get command outputs
            config1 = self._get_device_command_output(device1, command1)
            config2 = self._get_device_command_output(device2, command2)
            
            if not config1:
                config1 = f"No output available for command: {command1}"
            if not config2:
                config2 = f"No output available for command: {command2}"
            
            self.progress_bar.setValue(50)
            
            # Perform comparison using show command comparison
            if command1 == command2:
                # Same command, use show command comparison
                result = self.plugin.config_comparator.compare_show_commands(
                    device1, device2, command1
                )
            else:
                # Different commands, use template comparison
                result = self.plugin.config_comparator.compare_templates(
                    config1, config2,
                    f"{device1.get_property('name', 'Device 1')} - {command1}",
                    f"{device2.get_property('name', 'Device 2')} - {command2}"
                )
            
            self.progress_bar.setValue(100)
            
            # Store result and update display
            self.comparison_result = result
            self._display_comparison_results()
            
            # Hide progress bar
            self.progress_bar.setVisible(False)
            
            logger.info(f"Updated comparison: {command1} vs {command2}")
            
        except Exception as e:
            logger.error(f"Error updating comparison from selection: {e}")
            QMessageBox.critical(self, "Comparison Error", f"Failed to update comparison: {e}")
            self.progress_bar.setVisible(False)
    
    def _get_device_command_output(self, device, command):
        """Get specific command output from device"""
        try:
            # Check if device has command outputs stored
            command_outputs = None
            if hasattr(device, 'command_outputs') and device.command_outputs:
                command_outputs = device.command_outputs
            elif hasattr(device, 'get_command_outputs'):
                command_outputs = device.get_command_outputs()
            
            if not command_outputs:
                return None
            
            # Try exact match first
            if command in command_outputs:
                cmd_outputs = command_outputs[command]
                if cmd_outputs and isinstance(cmd_outputs, dict):
                    # Get the most recent output
                    timestamps = list(cmd_outputs.keys())
                    if timestamps:
                        latest_timestamp = max(timestamps)
                        output_data = cmd_outputs[latest_timestamp]
                        if isinstance(output_data, dict) and 'output' in output_data:
                            return output_data['output']
                        elif isinstance(output_data, str):
                            return output_data
            
            # Try fuzzy match for similar commands
            command_lower = command.lower()
            for cmd_id, cmd_outputs in command_outputs.items():
                if cmd_id.lower() == command_lower or command_lower in cmd_id.lower():
                    if cmd_outputs and isinstance(cmd_outputs, dict):
                        timestamps = list(cmd_outputs.keys())
                        if timestamps:
                            latest_timestamp = max(timestamps)
                            output_data = cmd_outputs[latest_timestamp]
                            if isinstance(output_data, dict) and 'output' in output_data:
                                return output_data['output']
                            elif isinstance(output_data, str):
                                return output_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting command output: {e}")
            return None

    def _populate_device_combo(self, combo, selected_index):
        """Populate the device combo with available devices"""
        try:
            combo.clear()  # Clear existing items
            
            # Get all available devices from the plugin (not just the ones being compared)
            all_devices = self._get_all_available_devices()
            
            if not all_devices:
                # Fallback to devices passed to comparison
                all_devices = self.devices
            
            # Store all available devices for reference
            self.all_available_devices = all_devices
            
            # Add all devices to the combo with IP addresses
            for device in all_devices:
                device_name = device.get_property('name', 'Unknown')
                device_ip = device.get_property('ip_address', 'No IP')
                combo.addItem(f"{device_name} ({device_ip})")
            
            # Set the selected device (use original devices for initial selection)
            if selected_index < len(self.devices):
                # Find the index of the original device in the full list
                original_device = self.devices[selected_index]
                original_device_id = original_device.id
                
                for i, device in enumerate(all_devices):
                    if device.id == original_device_id:
                        combo.setCurrentIndex(i)
                        break
                else:
                    combo.setCurrentIndex(0)
            else:
                combo.setCurrentIndex(0)
            
            logger.debug(f"Populated device combo with {len(all_devices)} devices")
            
        except Exception as e:
            logger.error(f"Error populating device combo: {e}")
            # Fallback: add basic devices
            combo.clear()
            for device in self.devices:
                combo.addItem(f"{device.get_property('name', 'Unknown')} ({device.get_property('ip_address', 'No IP')})")
            combo.setCurrentIndex(selected_index if selected_index < len(self.devices) else 0)
    
    def _get_all_available_devices(self):
        """Get all devices that have command outputs available"""
        try:
            # Try to get all devices from the plugin's device manager
            if hasattr(self.plugin, 'device_manager') and self.plugin.device_manager:
                # Try different method names that might exist on DeviceManager
                all_devices = None
                if hasattr(self.plugin.device_manager, 'get_all_devices'):
                    all_devices = self.plugin.device_manager.get_all_devices()
                elif hasattr(self.plugin.device_manager, 'get_devices'):
                    all_devices = self.plugin.device_manager.get_devices()
                elif hasattr(self.plugin.device_manager, 'devices'):
                    # If devices is a property or attribute
                    devices_attr = getattr(self.plugin.device_manager, 'devices')
                    if isinstance(devices_attr, dict):
                        all_devices = list(devices_attr.values())
                    elif isinstance(devices_attr, list):
                        all_devices = devices_attr
                elif hasattr(self.plugin.device_manager, '_devices'):
                    # If _devices is a private attribute
                    devices_attr = getattr(self.plugin.device_manager, '_devices')
                    if isinstance(devices_attr, dict):
                        all_devices = list(devices_attr.values())
                    elif isinstance(devices_attr, list):
                        all_devices = devices_attr
                
                if all_devices:
                    # Filter to only devices that have command outputs
                    devices_with_commands = []
                    for device in all_devices:
                        available_commands = self.plugin._get_device_available_commands(device)
                        if available_commands:
                            devices_with_commands.append(device)
                    
                    if devices_with_commands:
                        return devices_with_commands
            
            # Fallback: return the devices passed to comparison
            return self.devices
            
        except Exception as e:
            logger.error(f"Error getting all available devices: {e}")
            return self.devices
    
    def _update_command_combo_for_device(self, combo, device_index):
        """Update the command combo for a specific device"""
        try:
            combo.clear()  # Clear existing items
            
            # Get the device from all available devices
            available_devices = getattr(self, 'all_available_devices', self.devices)
            
            # If device index is provided, get actual commands from device
            if device_index is not None and device_index < len(available_devices):
                device = available_devices[device_index]
                available_commands = self._get_device_commands(device)
                
                if available_commands:
                    # Add actual device commands
                    combo.addItems(available_commands)
                    # Set default to show running-config if available
                    if "show running-config" in available_commands:
                        combo.setCurrentText("show running-config")
                    else:
                        combo.setCurrentIndex(0)  # Select first available command
                    
                    logger.debug(f"Populated command combo for device {device_index} with {len(available_commands)} commands")
                else:
                    # No commands found, show informative message
                    combo.addItem("No commands available")
                    logger.warning(f"No cached commands found for device {device.get_property('name', 'Unknown')}")
            else:
                # Fallback: add some default commands if no device specified
                default_commands = [
                    "show running-config",
                    "show version",
                    "show interface status"
                ]
                combo.addItems(default_commands)
                combo.setCurrentText("show running-config")
                logger.debug("Populated command combo with default commands (no device specified)")
                            
        except Exception as e:
            logger.error(f"Error populating command combo: {e}")
            # Fallback: add basic commands
            combo.clear()
            combo.addItems(["show running-config", "show version"])
            combo.setCurrentText("show running-config") 