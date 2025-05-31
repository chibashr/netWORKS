#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command Manager Plugin Package

This package provides command execution and management capabilities for NetWORKS.
"""

__version__ = "1.0.3"
__author__ = "NetWORKS Team"

# Import and export the main plugin class
from .command_manager import CommandManagerPlugin

__all__ = ['CommandManagerPlugin'] 