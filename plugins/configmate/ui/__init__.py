#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigMate UI Module

Contains the user interface components for the ConfigMate plugin.
"""

# Import UI modules - try absolute import first
try:
    from configmate.ui.template_editor import TemplateEditorDialog
    from configmate.ui.config_comparison_dialog import ConfigComparisonDialog
    from configmate.ui.config_preview_widget import ConfigPreviewWidget
except ImportError:
    # Fallback to direct imports
    import sys
    import os
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, plugin_dir)
    
    from ui.template_editor import TemplateEditorDialog
    from ui.config_comparison_dialog import ConfigComparisonDialog
    from ui.config_preview_widget import ConfigPreviewWidget

__all__ = [
    'TemplateEditorDialog',
    'ConfigComparisonDialog',
    'ConfigPreviewWidget'
] 