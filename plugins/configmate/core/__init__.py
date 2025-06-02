#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigMate Core Module

Contains the core functionality for template management, configuration generation,
comparison, and variable detection.
"""

# Import core modules - try absolute import first
try:
    from configmate.core.template_manager import TemplateManager
    from configmate.core.config_generator import ConfigGenerator
    from configmate.core.config_comparator import ConfigComparator
    from configmate.core.variable_detector import VariableDetector
except ImportError:
    # Fallback to direct imports
    import sys
    import os
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, plugin_dir)
    
    from core.template_manager import TemplateManager
    from core.config_generator import ConfigGenerator
    from core.config_comparator import ConfigComparator
    from core.variable_detector import VariableDetector

__all__ = [
    'TemplateManager',
    'ConfigGenerator', 
    'ConfigComparator',
    'VariableDetector'
] 