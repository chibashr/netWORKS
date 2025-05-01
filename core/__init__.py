#!/usr/bin/env python3
# netWORKS - Core Module Package

from . import database
from . import plugins
from . import ui
from . import workspace

__all__ = ['database', 'plugins', 'ui', 'workspace']

"""
Core module for netWORKS application.
Contains fundamental components for the application to function.
"""

__version__ = "1.0.0" 