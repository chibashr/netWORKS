#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sample Plugin Package

This package provides a template and example for creating NetWORKS plugins.
"""

__version__ = "1.0.0"
__author__ = "NetWORKS Team"

# Import and export the main plugin class
from .sample_plugin import SamplePlugin

__all__ = ['SamplePlugin'] 