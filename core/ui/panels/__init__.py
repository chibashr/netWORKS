"""
Panel management module for the netWORKS application.
"""

from core.ui.panels.panel_functions import (
    register_panel,
    remove_panel,
    toggle_left_panel,
    toggle_right_panel,
    toggle_bottom_panel,
    refresh_plugin_panels
)

__all__ = [
    'register_panel',
    'remove_panel',
    'toggle_left_panel',
    'toggle_right_panel',
    'toggle_bottom_panel',
    'refresh_plugin_panels'
] 