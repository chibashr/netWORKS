#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Settings dialog for NetWORKS
"""

import os
from loguru import logger
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel, 
    QLineEdit, QCheckBox, QComboBox, QSpinBox, QFormLayout, QGroupBox,
    QPushButton, QDialogButtonBox, QFileDialog, QColorDialog, QTimeEdit,
    QSlider, QRadioButton, QButtonGroup, QScrollArea, QToolButton
)
from PySide6.QtCore import Qt, QTime, QSize, Signal, Slot
from PySide6.QtGui import QFont


class SettingsDialog(QDialog):
    """Settings dialog for configuring NetWORKS"""
    
    def __init__(self, config, plugin_manager=None, parent=None):
        """Initialize the settings dialog
        
        Args:
            config: Config instance for accessing settings
            plugin_manager: Plugin manager instance to notify of directory changes
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Store config and plugin manager instances
        self.config = config
        self.plugin_manager = plugin_manager
        
        # Set dialog properties
        self.setWindowTitle("Settings")
        self.resize(800, 600)
        
        # Initialize UI
        self._create_ui()
        self._load_settings()
        
    def _create_ui(self):
        """Create the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_general_tab()
        self._create_ui_tab()
        self._create_autosave_tab()
        self._create_device_tab()
        self._create_logging_tab()
        self._create_advanced_tab()
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        
        main_layout.addWidget(self.button_box)
        
    def _create_general_tab(self):
        """Create the general settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create a scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        form_layout = QVBoxLayout(content_widget)
        
        # Application group
        application_group = QGroupBox("Application")
        application_layout = QFormLayout(application_group)
        
        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        application_layout.addRow("Theme:", self.theme_combo)
        
        # Enable plugins
        self.enable_plugins_check = QCheckBox("Load plugins on startup")
        application_layout.addRow("Plugins:", self.enable_plugins_check)
        
        # External plugins directory
        plugins_layout = QHBoxLayout()
        self.plugins_dir_edit = QLineEdit()
        self.plugins_dir_edit.setReadOnly(True)
        plugins_browse_btn = QPushButton("Browse...")
        plugins_browse_btn.clicked.connect(self._on_browse_plugins_dir)
        plugins_layout.addWidget(self.plugins_dir_edit)
        plugins_layout.addWidget(plugins_browse_btn)
        application_layout.addRow("External Plugins Directory:", plugins_layout)
        
        # Add to layout
        form_layout.addWidget(application_group)
        
        # Updates group
        updates_group = QGroupBox("Updates")
        updates_layout = QFormLayout(updates_group)
        
        # Check for updates
        self.check_updates_check = QCheckBox("Check for updates on startup")
        updates_layout.addRow("Updates:", self.check_updates_check)
        
        # Update channel
        self.update_channel_combo = QComboBox()
        self.update_channel_combo.addItems(["Stable", "Beta", "Alpha", "Development"])
        updates_layout.addRow("Update Channel:", self.update_channel_combo)
        
        # Repository URL
        repo_url_layout = QHBoxLayout()
        self.repo_url_edit = QLineEdit()
        self.repo_url_edit.setPlaceholderText("e.g., https://github.com/chibashr/netWORKS")
        repo_reset_btn = QPushButton("Reset")
        repo_reset_btn.clicked.connect(self._on_reset_repo_url)
        repo_url_layout.addWidget(self.repo_url_edit)
        repo_url_layout.addWidget(repo_reset_btn)
        updates_layout.addRow("Repository URL:", repo_url_layout)
        
        # Add to layout
        form_layout.addWidget(updates_group)
        
        # Add spacing and stretch
        form_layout.addStretch()
        
        # Add the scroll area to the tab layout
        layout.addWidget(scroll)
        
        # Add tab to tab widget
        self.tab_widget.addTab(tab, "General")
        
    def _create_ui_tab(self):
        """Create the UI settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create a scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        form_layout = QVBoxLayout(content_widget)
        
        # Theme and Appearance group
        theme_group = QGroupBox("Theme & Appearance")
        theme_layout = QFormLayout(theme_group)
        
        # UI Theme
        self.ui_theme_combo = QComboBox()
        self.ui_theme_combo.addItems(["Modern Grayscale", "Classic Light", "System Default"])
        theme_layout.addRow("UI Theme:", self.ui_theme_combo)
        
        # Color intensity
        self.color_intensity_slider = QSlider(Qt.Horizontal)
        self.color_intensity_slider.setMinimum(50)
        self.color_intensity_slider.setMaximum(150)
        self.color_intensity_slider.setValue(100)
        self.color_intensity_slider.setTickPosition(QSlider.TicksBelow)
        self.color_intensity_slider.setTickInterval(25)
        self.color_intensity_slider.valueChanged.connect(self._update_intensity_label)
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(self.color_intensity_slider)
        self.intensity_value_label = QLabel("100%")
        intensity_layout.addWidget(self.intensity_value_label)
        theme_layout.addRow("Color Intensity:", intensity_layout)
        
        # Window opacity
        self.window_opacity_slider = QSlider(Qt.Horizontal)
        self.window_opacity_slider.setMinimum(70)
        self.window_opacity_slider.setMaximum(100)
        self.window_opacity_slider.setValue(100)
        self.window_opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.window_opacity_slider.setTickInterval(10)
        self.window_opacity_slider.valueChanged.connect(self._update_opacity_label)
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.window_opacity_slider)
        self.opacity_value_label = QLabel("100%")
        opacity_layout.addWidget(self.opacity_value_label)
        theme_layout.addRow("Window Opacity:", opacity_layout)
        
        # Modern effects
        self.modern_effects_check = QCheckBox("Enable modern visual effects")
        theme_layout.addRow("Effects:", self.modern_effects_check)
        
        # Add to layout
        form_layout.addWidget(theme_group)
        
        # Font and Text group
        font_group = QGroupBox("Font & Text")
        font_layout = QFormLayout(font_group)
        
        # Font family
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems([
            "System Default",
            "Segoe UI",
            "Roboto", 
            "Helvetica Neue",
            "Arial",
            "Calibri",
            "Consolas",
            "Monaco"
        ])
        font_layout.addRow("Font Family:", self.font_family_combo)
        
        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(8)
        self.font_size_spin.setMaximum(18)
        self.font_size_spin.setValue(9)
        font_layout.addRow("Font Size:", self.font_size_spin)
        
        # Font weight
        self.font_weight_combo = QComboBox()
        self.font_weight_combo.addItems(["Light", "Normal", "Medium", "Bold"])
        self.font_weight_combo.setCurrentText("Normal")
        font_layout.addRow("Font Weight:", self.font_weight_combo)
        
        # Add to layout
        form_layout.addWidget(font_group)
        
        # Toolbar and Interface group
        interface_group = QGroupBox("Interface Layout")
        interface_layout = QFormLayout(interface_group)
        
        # Toolbar style
        self.toolbar_style_combo = QComboBox()
        self.toolbar_style_combo.addItems(["Modern Grouped", "Classic Flat", "Icon Only", "Text Only"])
        self.toolbar_style_combo.setCurrentText("Modern Grouped")
        interface_layout.addRow("Toolbar Style:", self.toolbar_style_combo)
        
        # Show status bar
        self.show_statusbar_check = QCheckBox()
        self.show_statusbar_check.setChecked(True)
        interface_layout.addRow("Show Status Bar:", self.show_statusbar_check)
        
        # Compact interface
        self.compact_interface_check = QCheckBox("Use compact spacing")
        interface_layout.addRow("Compact Mode:", self.compact_interface_check)
        
        # Add to layout
        form_layout.addWidget(interface_group)
        
        # Table and Data Display group
        table_group = QGroupBox("Data Display")
        table_layout = QFormLayout(table_group)
        
        # Alternate row colors
        self.alt_row_colors_check = QCheckBox()
        self.alt_row_colors_check.setChecked(True)
        table_layout.addRow("Alternate Row Colors:", self.alt_row_colors_check)
        
        # Auto-resize columns
        self.auto_resize_cols_check = QCheckBox()
        self.auto_resize_cols_check.setChecked(False)
        table_layout.addRow("Auto-resize Columns:", self.auto_resize_cols_check)
        
        # Row height
        self.row_height_spin = QSpinBox()
        self.row_height_spin.setMinimum(20)
        self.row_height_spin.setMaximum(50)
        self.row_height_spin.setValue(24)
        table_layout.addRow("Row Height:", self.row_height_spin)
        
        # Grid lines
        self.show_grid_lines_check = QCheckBox()
        self.show_grid_lines_check.setChecked(True)
        table_layout.addRow("Show Grid Lines:", self.show_grid_lines_check)
        
        # Add to layout
        form_layout.addWidget(table_group)
        
        # Add spacing and stretch
        form_layout.addStretch()
        
        # Add the scroll area to the tab layout
        layout.addWidget(scroll)
        
        # Add tab to tab widget
        self.tab_widget.addTab(tab, "Interface")
        
    def _create_autosave_tab(self):
        """Create the autosave settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create a scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        form_layout = QVBoxLayout(content_widget)
        
        # Autosave group
        autosave_group = QGroupBox("Autosave")
        autosave_layout = QFormLayout(autosave_group)
        
        # Enable autosave
        self.autosave_enabled_check = QCheckBox()
        autosave_layout.addRow("Enable Autosave:", self.autosave_enabled_check)
        
        # Autosave interval
        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setMinimum(1)
        self.autosave_interval_spin.setMaximum(60)
        self.autosave_interval_spin.setSuffix(" minutes")
        autosave_layout.addRow("Autosave Interval:", self.autosave_interval_spin)
        
        # Only autosave on changes
        self.autosave_on_changes_check = QCheckBox("Only save if changes have been made")
        autosave_layout.addRow("Smart Autosave:", self.autosave_on_changes_check)
        
        # Notification on autosave
        self.autosave_notify_check = QCheckBox("Show a notification when autosave occurs")
        autosave_layout.addRow("Notifications:", self.autosave_notify_check)
        
        # Add to layout
        form_layout.addWidget(autosave_group)
        
        # Backup group
        backup_group = QGroupBox("Backups")
        backup_layout = QFormLayout(backup_group)
        
        # Create backups
        self.create_backups_check = QCheckBox()
        backup_layout.addRow("Create Backups:", self.create_backups_check)
        
        # Max backup count
        self.max_backups_spin = QSpinBox()
        self.max_backups_spin.setMinimum(1)
        self.max_backups_spin.setMaximum(100)
        backup_layout.addRow("Maximum Backups:", self.max_backups_spin)
        
        # Backup directory
        backup_dir_layout = QHBoxLayout()
        self.backup_dir_edit = QLineEdit()
        self.backup_dir_edit.setReadOnly(True)
        backup_browse_btn = QPushButton("Browse...")
        backup_browse_btn.clicked.connect(self._on_browse_backup_dir)
        backup_dir_layout.addWidget(self.backup_dir_edit)
        backup_dir_layout.addWidget(backup_browse_btn)
        backup_layout.addRow("Backup Directory:", backup_dir_layout)
        
        # Add to layout
        form_layout.addWidget(backup_group)
        
        # Add spacing and stretch
        form_layout.addStretch()
        
        # Add the scroll area to the tab layout
        layout.addWidget(scroll)
        
        # Add tab to tab widget
        self.tab_widget.addTab(tab, "Autosave")
        
    def _create_device_tab(self):
        """Create the device settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create a scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        form_layout = QVBoxLayout(content_widget)
        
        # Discovery group
        discovery_group = QGroupBox("Device Discovery")
        discovery_layout = QFormLayout(discovery_group)
        
        # Auto discover
        self.auto_discover_check = QCheckBox()
        discovery_layout.addRow("Auto-discover Devices:", self.auto_discover_check)
        
        # Refresh interval
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setMinimum(10)
        self.refresh_interval_spin.setMaximum(3600)
        self.refresh_interval_spin.setSuffix(" seconds")
        discovery_layout.addRow("Refresh Interval:", self.refresh_interval_spin)
        
        # Auto ping
        self.auto_ping_check = QCheckBox("Automatically ping devices to check status")
        discovery_layout.addRow("Auto Ping:", self.auto_ping_check)
        
        # Add to layout
        form_layout.addWidget(discovery_group)
        
        # Connection group
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QFormLayout(connection_group)
        
        # Connection timeout
        self.connection_timeout_spin = QSpinBox()
        self.connection_timeout_spin.setMinimum(1)
        self.connection_timeout_spin.setMaximum(60)
        self.connection_timeout_spin.setSuffix(" seconds")
        connection_layout.addRow("Connection Timeout:", self.connection_timeout_spin)
        
        # SSH port
        self.ssh_port_spin = QSpinBox()
        self.ssh_port_spin.setMinimum(1)
        self.ssh_port_spin.setMaximum(65535)
        connection_layout.addRow("Default SSH Port:", self.ssh_port_spin)
        
        # Telnet port
        self.telnet_port_spin = QSpinBox()
        self.telnet_port_spin.setMinimum(1)
        self.telnet_port_spin.setMaximum(65535)
        connection_layout.addRow("Default Telnet Port:", self.telnet_port_spin)
        
        # Add to layout
        form_layout.addWidget(connection_group)
        
        # Add spacing and stretch
        form_layout.addStretch()
        
        # Add the scroll area to the tab layout
        layout.addWidget(scroll)
        
        # Add tab to tab widget
        self.tab_widget.addTab(tab, "Devices")
        
    def _create_logging_tab(self):
        """Create the logging settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create a scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        form_layout = QVBoxLayout(content_widget)
        
        # Logging group
        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout(logging_group)
        
        # Log level
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        logging_layout.addRow("Log Level:", self.log_level_combo)
        
        # Log retention
        self.log_retention_spin = QSpinBox()
        self.log_retention_spin.setMinimum(1)
        self.log_retention_spin.setMaximum(90)
        self.log_retention_spin.setSuffix(" days")
        logging_layout.addRow("Log Retention:", self.log_retention_spin)
        
        # File rotation size
        self.log_rotation_spin = QSpinBox()
        self.log_rotation_spin.setMinimum(1)
        self.log_rotation_spin.setMaximum(100)
        self.log_rotation_spin.setSuffix(" MB")
        logging_layout.addRow("Log Rotation Size:", self.log_rotation_spin)
        
        # Diagnostics
        self.log_diagnostics_check = QCheckBox("Include diagnostic information in logs")
        logging_layout.addRow("Diagnostics:", self.log_diagnostics_check)
        
        # Backtrace
        self.log_backtrace_check = QCheckBox("Include exception backtraces in logs")
        logging_layout.addRow("Backtraces:", self.log_backtrace_check)
        
        # Add to layout
        form_layout.addWidget(logging_group)
        
        # Add spacing and stretch
        form_layout.addStretch()
        
        # Add the scroll area to the tab layout
        layout.addWidget(scroll)
        
        # Add tab to tab widget
        self.tab_widget.addTab(tab, "Logging")
        
    def _create_advanced_tab(self):
        """Create the advanced settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create a scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        form_layout = QVBoxLayout(content_widget)
        
        # Performance group
        performance_group = QGroupBox("Performance")
        performance_layout = QFormLayout(performance_group)
        
        # Cache size
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setMinimum(10)
        self.cache_size_spin.setMaximum(1000)
        self.cache_size_spin.setSuffix(" MB")
        performance_layout.addRow("Cache Size:", self.cache_size_spin)
        
        # Max threads
        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setMinimum(1)
        self.max_threads_spin.setMaximum(32)
        performance_layout.addRow("Maximum Threads:", self.max_threads_spin)
        
        # Add to layout
        form_layout.addWidget(performance_group)
        
        # Networking group
        networking_group = QGroupBox("Networking")
        networking_layout = QFormLayout(networking_group)
        
        # Use proxy
        self.use_proxy_check = QCheckBox()
        networking_layout.addRow("Use Proxy:", self.use_proxy_check)
        
        # Proxy host
        self.proxy_host_edit = QLineEdit()
        networking_layout.addRow("Proxy Host:", self.proxy_host_edit)
        
        # Proxy port
        self.proxy_port_spin = QSpinBox()
        self.proxy_port_spin.setMinimum(1)
        self.proxy_port_spin.setMaximum(65535)
        networking_layout.addRow("Proxy Port:", self.proxy_port_spin)
        
        # Add to layout
        form_layout.addWidget(networking_group)
        
        # Security group
        security_group = QGroupBox("Security")
        security_layout = QFormLayout(security_group)
        
        # Store credentials
        self.store_credentials_check = QCheckBox("Securely store device credentials")
        security_layout.addRow("Credentials:", self.store_credentials_check)
        
        # Credential timeout
        self.credential_timeout_spin = QSpinBox()
        self.credential_timeout_spin.setMinimum(1)
        self.credential_timeout_spin.setMaximum(60)
        self.credential_timeout_spin.setSuffix(" minutes")
        security_layout.addRow("Credential Timeout:", self.credential_timeout_spin)
        
        # Add to layout
        form_layout.addWidget(security_group)
        
        # Add spacing and stretch
        form_layout.addStretch()
        
        # Add the scroll area to the tab layout
        layout.addWidget(scroll)
        
        # Add tab to tab widget
        self.tab_widget.addTab(tab, "Advanced")
        
    def _load_settings(self):
        """Load current settings into UI elements"""
        # Set loading flag to prevent change handlers from firing
        self._loading_settings = True
        
        try:
            # General settings
            theme = self.config.get("ui.theme", "Light")
            self.theme_combo.setCurrentText(theme.capitalize())
            
            self.enable_plugins_check.setChecked(self.config.get("application.plugins_enabled", True))
            self.plugins_dir_edit.setText(self.config.get("application.external_plugins_directory", ""))
            
            # Update settings
            self.check_updates_check.setChecked(self.config.get("general.check_updates", True))
            self.update_channel_combo.setCurrentText(self.config.get("general.update_channel", "Stable"))
            self.repo_url_edit.setText(self.config.get("general.repository_url", "https://github.com/chibashr/netWORKS"))
            
            # Enhanced UI settings
            if hasattr(self, 'ui_theme_combo'):
                self.ui_theme_combo.setCurrentText(self.config.get("ui.theme", "Modern Grayscale"))
            if hasattr(self, 'color_intensity_slider'):
                intensity = self.config.get("ui.color_intensity", 100)
                self.color_intensity_slider.setValue(intensity)
                self.intensity_value_label.setText(f"{intensity}%")
            if hasattr(self, 'window_opacity_slider'):
                opacity = self.config.get("ui.window_opacity", 100)
                self.window_opacity_slider.setValue(opacity)
                self.opacity_value_label.setText(f"{opacity}%")
            if hasattr(self, 'modern_effects_check'):
                self.modern_effects_check.setChecked(self.config.get("ui.modern_effects", True))
            if hasattr(self, 'font_family_combo'):
                self.font_family_combo.setCurrentText(self.config.get("ui.font_family", "System Default"))
            if hasattr(self, 'font_weight_combo'):
                self.font_weight_combo.setCurrentText(self.config.get("ui.font_weight", "Normal"))
            if hasattr(self, 'toolbar_style_combo'):
                self.toolbar_style_combo.setCurrentText(self.config.get("ui.toolbar_style", "Modern Grouped"))
            if hasattr(self, 'compact_interface_check'):
                self.compact_interface_check.setChecked(self.config.get("ui.compact_interface", False))
            if hasattr(self, 'show_grid_lines_check'):
                self.show_grid_lines_check.setChecked(self.config.get("ui.show_grid_lines", True))
            
            # Original UI settings
            self.font_size_spin.setValue(self.config.get("ui.font_size", 9))
            self.show_statusbar_check.setChecked(self.config.get("ui.show_statusbar", True))
            
            # Table settings
            self.alt_row_colors_check.setChecked(self.config.get("ui.alternate_row_colors", True))
            self.auto_resize_cols_check.setChecked(self.config.get("ui.auto_resize_columns", False))
            self.row_height_spin.setValue(self.config.get("ui.row_height", 24))
            
            # Autosave tab
            self.autosave_enabled_check.setChecked(self.config.get("autosave.enabled", False))
            self.autosave_interval_spin.setValue(self.config.get("autosave.interval", 5))
            self.autosave_on_changes_check.setChecked(self.config.get("autosave.only_on_changes", True))
            self.autosave_notify_check.setChecked(self.config.get("autosave.show_notification", False))
            self.create_backups_check.setChecked(self.config.get("autosave.create_backups", True))
            self.max_backups_spin.setValue(self.config.get("autosave.max_backups", 10))
            self.backup_dir_edit.setText(self.config.get("autosave.backup_directory", ""))
            
            # Device tab
            self.auto_discover_check.setChecked(self.config.get("devices.auto_discover", True))
            self.refresh_interval_spin.setValue(self.config.get("devices.refresh_interval", 60))
            self.auto_ping_check.setChecked(self.config.get("devices.auto_ping", True))
            self.connection_timeout_spin.setValue(self.config.get("devices.connection_timeout", 5))
            self.ssh_port_spin.setValue(self.config.get("devices.ssh_port", 22))
            self.telnet_port_spin.setValue(self.config.get("devices.telnet_port", 23))
            
            # Logging tab
            self.log_level_combo.setCurrentText(self.config.get("logging.level", "INFO"))
            self.log_retention_spin.setValue(self.config.get("logging.retention_days", 7))
            self.log_rotation_spin.setValue(int(self.config.get("logging.file_rotation_size", "10 MB").split()[0]))
            self.log_diagnostics_check.setChecked(self.config.get("logging.diagnose", True))
            self.log_backtrace_check.setChecked(self.config.get("logging.backtrace", True))
            
            # Advanced tab
            self.cache_size_spin.setValue(self.config.get("advanced.cache_size", 100))
            self.max_threads_spin.setValue(self.config.get("advanced.max_threads", 4))
            self.use_proxy_check.setChecked(self.config.get("advanced.use_proxy", False))
            self.proxy_host_edit.setText(self.config.get("advanced.proxy_host", ""))
            self.proxy_port_spin.setValue(self.config.get("advanced.proxy_port", 8080))
            self.store_credentials_check.setChecked(self.config.get("advanced.store_credentials", True))
            self.credential_timeout_spin.setValue(self.config.get("advanced.credential_timeout", 15))
            
        finally:
            # Clear loading flag
            self._loading_settings = False
        
    def _save_settings(self):
        """Save settings from UI elements to config"""
        # Check if external plugins directory changed
        old_plugins_dir = self.config.get("application.external_plugins_directory", "")
        new_plugins_dir = self.plugins_dir_edit.text()
        
        # General settings
        self.config.set("ui.theme", self.theme_combo.currentText().lower())
        self.config.set("application.plugins_enabled", self.enable_plugins_check.isChecked())
        self.config.set("application.external_plugins_directory", new_plugins_dir)
        
        # Update settings
        self.config.set("general.check_updates", self.check_updates_check.isChecked())
        self.config.set("general.update_channel", self.update_channel_combo.currentText())
        self.config.set("general.repository_url", self.repo_url_edit.text().strip())
        
        # Enhanced UI settings
        if hasattr(self, 'ui_theme_combo'):
            self.config.set("ui.theme", self.ui_theme_combo.currentText())
        if hasattr(self, 'color_intensity_slider'):
            self.config.set("ui.color_intensity", self.color_intensity_slider.value())
        if hasattr(self, 'window_opacity_slider'):
            self.config.set("ui.window_opacity", self.window_opacity_slider.value())
        if hasattr(self, 'modern_effects_check'):
            self.config.set("ui.modern_effects", self.modern_effects_check.isChecked())
        if hasattr(self, 'font_family_combo'):
            self.config.set("ui.font_family", self.font_family_combo.currentText())
        if hasattr(self, 'font_weight_combo'):
            self.config.set("ui.font_weight", self.font_weight_combo.currentText())
        if hasattr(self, 'toolbar_style_combo'):
            self.config.set("ui.toolbar_style", self.toolbar_style_combo.currentText())
        if hasattr(self, 'compact_interface_check'):
            self.config.set("ui.compact_interface", self.compact_interface_check.isChecked())
        if hasattr(self, 'show_grid_lines_check'):
            self.config.set("ui.show_grid_lines", self.show_grid_lines_check.isChecked())
        
        # Original UI settings
        self.config.set("ui.font_size", self.font_size_spin.value())
        self.config.set("ui.show_statusbar", self.show_statusbar_check.isChecked())
        
        # Table settings
        self.config.set("ui.alternate_row_colors", self.alt_row_colors_check.isChecked())
        self.config.set("ui.auto_resize_columns", self.auto_resize_cols_check.isChecked())
        self.config.set("ui.row_height", self.row_height_spin.value())
        
        # Autosave tab
        self.config.set("autosave.enabled", self.autosave_enabled_check.isChecked())
        self.config.set("autosave.interval", self.autosave_interval_spin.value())
        self.config.set("autosave.only_on_changes", self.autosave_on_changes_check.isChecked())
        self.config.set("autosave.show_notification", self.autosave_notify_check.isChecked())
        self.config.set("autosave.create_backups", self.create_backups_check.isChecked())
        self.config.set("autosave.max_backups", self.max_backups_spin.value())
        self.config.set("autosave.backup_directory", self.backup_dir_edit.text())
        
        # Device tab
        self.config.set("devices.auto_discover", self.auto_discover_check.isChecked())
        self.config.set("devices.refresh_interval", self.refresh_interval_spin.value())
        self.config.set("devices.auto_ping", self.auto_ping_check.isChecked())
        self.config.set("devices.connection_timeout", self.connection_timeout_spin.value())
        self.config.set("devices.ssh_port", self.ssh_port_spin.value())
        self.config.set("devices.telnet_port", self.telnet_port_spin.value())
        
        # Logging tab
        self.config.set("logging.level", self.log_level_combo.currentText())
        self.config.set("logging.retention_days", self.log_retention_spin.value())
        self.config.set("logging.file_rotation_size", f"{self.log_rotation_spin.value()} MB")
        self.config.set("logging.diagnose", self.log_diagnostics_check.isChecked())
        self.config.set("logging.backtrace", self.log_backtrace_check.isChecked())
        
        # Advanced tab
        self.config.set("advanced.cache_size", self.cache_size_spin.value())
        self.config.set("advanced.max_threads", self.max_threads_spin.value())
        self.config.set("advanced.use_proxy", self.use_proxy_check.isChecked())
        self.config.set("advanced.proxy_host", self.proxy_host_edit.text())
        self.config.set("advanced.proxy_port", self.proxy_port_spin.value())
        self.config.set("advanced.store_credentials", self.store_credentials_check.isChecked())
        self.config.set("advanced.credential_timeout", self.credential_timeout_spin.value())
        
        # Notify plugin manager if external plugins directory changed
        if new_plugins_dir != old_plugins_dir and self.plugin_manager:
            logger.info(f"External plugins directory changed: {old_plugins_dir} -> {new_plugins_dir}")
            self.plugin_manager.set_external_plugins_directory(new_plugins_dir)
        
        # Save the configuration
        self.config.save()
        
    def _on_browse_plugins_dir(self):
        """Handle browse button for plugins directory"""
        current_dir = self.plugins_dir_edit.text() or os.path.dirname(os.path.abspath(__file__))
        directory = QFileDialog.getExistingDirectory(self, "Select Plugins Directory", current_dir)
        if directory:
            self.plugins_dir_edit.setText(directory)
            
    def _on_browse_backup_dir(self):
        """Handle browse button for backup directory"""
        current_dir = self.backup_dir_edit.text() or os.path.dirname(os.path.abspath(__file__))
        directory = QFileDialog.getExistingDirectory(self, "Select Backup Directory", current_dir)
        if directory:
            self.backup_dir_edit.setText(directory)
            
    def _on_apply(self):
        """Apply the settings immediately without closing the dialog"""
        self._save_settings()
        self._apply_appearance_changes()
        
    def _on_accept(self):
        """Accept button clicked - save settings and close"""
        self._save_settings()
        self._apply_appearance_changes()
        self.accept()
        
    def _apply_appearance_changes(self):
        """Apply appearance changes to the main window immediately"""
        if not self.parent():
            return
            
        main_window = self.parent()
        
        # Apply theme changes
        theme = self.ui_theme_combo.currentText()
        self._apply_theme(main_window, theme)
        
        # Apply font changes
        self._apply_font_changes(main_window)
        
        # Apply toolbar style changes
        self._apply_toolbar_style(main_window)
        
        # Apply compact mode changes
        self._apply_compact_mode(main_window)
        
        # Apply opacity
        opacity = self.window_opacity_slider.value() / 100.0
        main_window.setWindowOpacity(opacity)
        
        # Apply statusbar visibility
        if hasattr(main_window, 'status_bar'):
            main_window.status_bar.setVisible(self.show_statusbar_check.isChecked())
    
    def _apply_theme(self, main_window, theme):
        """Apply the selected theme to the main window"""
        app = main_window.app if hasattr(main_window, 'app') else None
        if not app:
            return
            
        if theme == "Modern Grayscale":
            # Use the existing modern stylesheet from app.py
            pass  # Already applied
        elif theme == "Classic Light":
            # Apply a simpler light theme
            classic_stylesheet = """
            QWidget {
                background-color: #f0f0f0;
                color: #333333;
                font-family: Arial, sans-serif;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            """
            app.setStyleSheet(classic_stylesheet)
        elif theme == "System Default":
            app.setStyleSheet("")
    
    def _on_reset_repo_url(self):
        """Reset repository URL to default"""
        self.repo_url_edit.setText("https://github.com/chibashr/netWORKS")
    
    def _update_intensity_label(self, value):
        """Update the intensity label without applying changes"""
        self.intensity_value_label.setText(f"{value}%")
    
    def _update_opacity_label(self, value):
        """Update the opacity label without applying changes"""
        self.opacity_value_label.setText(f"{value}%")
    
    def _apply_font_changes(self, main_window):
        """Apply font changes to the application"""
        try:
            app = main_window.app if hasattr(main_window, 'app') else None
            if not app:
                return
            
            # Get font settings
            font_family = self.font_family_combo.currentText()
            font_size = self.font_size_spin.value()
            font_weight = self.font_weight_combo.currentText()
            
            # Create font
            font = QFont()
            
            # Set font family
            if font_family != "System Default":
                font.setFamily(font_family)
            
            # Set font size
            font.setPointSize(font_size)
            
            # Set font weight
            if font_weight == "Light":
                font.setWeight(QFont.Light)
            elif font_weight == "Normal":
                font.setWeight(QFont.Normal)
            elif font_weight == "Medium":
                font.setWeight(QFont.Medium)
            elif font_weight == "Bold":
                font.setWeight(QFont.Bold)
            
            # Apply font to application
            app.setFont(font)
            
        except Exception as e:
            logger.error(f"Error applying font changes: {e}")
    
    def _apply_toolbar_style(self, main_window):
        """Apply toolbar style changes"""
        try:
            if not hasattr(main_window, 'toolbar'):
                return
            
            style = self.toolbar_style_combo.currentText()
            toolbar = main_window.toolbar
            
            if style == "Modern Grouped":
                # Keep current grouped style - already implemented
                pass
            elif style == "Classic Flat":
                # Apply flat style
                toolbar.setStyleSheet("""
                    QToolBar {
                        background-color: #f0f0f0;
                        border: none;
                        border-bottom: 1px solid #d0d0d0;
                        padding: 2px;
                        spacing: 1px;
                    }
                """)
            elif style == "Icon Only":
                # Set all buttons to icon only
                for widget in toolbar.findChildren(QToolButton):
                    widget.setToolButtonStyle(Qt.ToolButtonIconOnly)
            elif style == "Text Only":
                # Set all buttons to text only
                for widget in toolbar.findChildren(QToolButton):
                    widget.setToolButtonStyle(Qt.ToolButtonTextOnly)
                    
        except Exception as e:
            logger.error(f"Error applying toolbar style: {e}")
    
    def _apply_compact_mode(self, main_window):
        """Apply compact mode changes"""
        try:
            compact = self.compact_interface_check.isChecked()
            
            if compact:
                # Apply compact spacing
                main_window.setStyleSheet(main_window.styleSheet() + """
                    QWidget {
                        margin: 2px;
                        padding: 2px;
                    }
                    QGroupBox {
                        margin-top: 6px;
                        padding-top: 6px;
                    }
                    QTabWidget::pane {
                        border: 1px solid #d0d0d0;
                        background-color: #ffffff;
                        border-radius: 2px;
                    }
                    QTabBar::tab {
                        padding: 4px 8px;
                        margin-right: 1px;
                    }
                """)
                
                # Reduce toolbar height for compact mode
                if hasattr(main_window, 'toolbar'):
                    main_window.toolbar.setMinimumHeight(60)
                    
            else:
                # Remove compact styling and restore normal spacing
                # This would require reapplying the original stylesheet
                if hasattr(main_window, 'app') and hasattr(main_window.app, 'setStyleSheet'):
                    # Re-apply the original modern stylesheet
                    self._apply_theme(main_window, self.ui_theme_combo.currentText())
                    
        except Exception as e:
            logger.error(f"Error applying compact mode: {e}") 