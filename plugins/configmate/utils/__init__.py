#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigMate Utils Module

Contains utility functions and classes for the ConfigMate plugin including
syntax highlighting, platform-specific parsers, and helper functions.
"""

# Import utility modules - try absolute import first
try:
    from configmate.utils.cisco_syntax import CiscoSyntaxHighlighter
except ImportError:
    # Fallback to direct imports
    import sys
    import os
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, plugin_dir)
    
    from utils.cisco_syntax import CiscoSyntaxHighlighter

__all__ = [
    'CiscoSyntaxHighlighter'
] 