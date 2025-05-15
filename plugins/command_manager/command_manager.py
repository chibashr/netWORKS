#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command Manager Plugin for NetWORKS
"""

from plugins.command_manager.core.command_manager import CommandManagerPlugin as CoreCommandManagerPlugin

# Create a class in this file that inherits from the core implementation
# This is necessary to satisfy the plugin loader which looks for a class with initialize() 
# defined in this specific module

class CommandManagerPlugin(CoreCommandManagerPlugin):
    """Command Manager Plugin for NetWORKS"""
    pass  # Inherit all functionality from the core implementation

# Keep for compatibility with plugin system
__all__ = ['CommandManagerPlugin']