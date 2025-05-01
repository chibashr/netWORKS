"""
Log Viewer Plugin for netWORKS
This plugin provides a way to view, filter, and download application logs.
"""

# Make this directory a proper package for import
__all__ = ['main', 'ui']

# This file can be empty but it's required for Python to recognize this as a package

import logging

# Initialize logging for this package
logger = logging.getLogger(__name__)

# Set the version
__version__ = "1.0.0" 