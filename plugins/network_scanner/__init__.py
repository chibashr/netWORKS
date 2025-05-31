#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Network Scanner Plugin Package

This package provides network scanning capabilities for NetWORKS.
"""

__version__ = "1.3.0"
__author__ = "NetWORKS Team"

# Import and export the main plugin class
from .network_scanner import NetworkScannerPlugin

__all__ = ['NetworkScannerPlugin'] 