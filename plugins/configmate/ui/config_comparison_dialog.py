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
                device_id = device.get_property('id')
                config = self.plugin._get_device_config(device)
                configs[device_id] = {
                    'device': device,
                    'config': config
                }
                progress = 10 + (i + 1) * 40 // len(self.devices)
                self.progress_updated.emit(progress)
            
            self.progress_updated.emit(60)
            
            # Perform comparison
            if len(self.devices) == 2:
                # Two-device comparison
                device1, device2 = self.devices
                config1 = configs[device1.get_property('id')]['config']
                config2 = configs[device2.get_property('id')]['config']
                
                result = self.plugin.config_comparator.compare_configs(
                    config1, config2, device1, device2
                )
            else:
                # Multi-device comparison
                result = self.plugin.config_comparator.compare_multiple_configs(
                    [(device, configs[device.get_property('id')]['config']) 
                     for device in self.devices]
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
        
        # Device labels
        labels_layout = QHBoxLayout()
        device1_label = QLabel(self.devices[0].get_property('name', 'Device 1'))
        device1_label.setStyleSheet("font-weight: bold; padding: 5px;")
        device2_label = QLabel(self.devices[1].get_property('name', 'Device 2'))
        device2_label.setStyleSheet("font-weight: bold; padding: 5px;")
        
        labels_layout.addWidget(device1_label)
        labels_layout.addWidget(device2_label)
        layout.addLayout(labels_layout)
        
        # Text editors in splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.config1_editor = QTextEdit()
        self.config1_editor.setFont(QFont("Consolas", 10))
        self.config1_editor.setReadOnly(True)
        
        self.config2_editor = QTextEdit()
        self.config2_editor.setFont(QFont("Consolas", 10))
        self.config2_editor.setReadOnly(True)
        
        splitter.addWidget(self.config1_editor)
        splitter.addWidget(self.config2_editor)
        splitter.setSizes([700, 700])
        
        layout.addWidget(splitter)
        
        return widget
    
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
        self.config1_editor.setPlainText(result.config1)
        self.config2_editor.setPlainText(result.config2)
        
        # Apply diff highlighting
        self.diff_highlighter1 = DiffHighlighter(self.config1_editor.document())
        self.diff_highlighter2 = DiffHighlighter(self.config2_editor.document())
        
        # Display unified diff
        unified_diff = result.get_unified_diff()
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
            ("Total Lines (Device 1)", len(result.config1.splitlines())),
            ("Total Lines (Device 2)", len(result.config2.splitlines())),
            ("Added Lines", result.stats.get('added_lines', 0)),
            ("Removed Lines", result.stats.get('removed_lines', 0)),
            ("Modified Lines", result.stats.get('modified_lines', 0)),
            ("Unchanged Lines", result.stats.get('unchanged_lines', 0)),
            ("Similarity %", f"{result.stats.get('similarity_percent', 0):.1f}%")
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