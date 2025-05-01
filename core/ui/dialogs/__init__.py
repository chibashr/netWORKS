#!/usr/bin/env python3
# netWORKS - UI Dialogs Package

"""
Dialog management module for the netWORKS application.
"""

# Import existing dialog classes
try:
    from core.ui.dialogs.workspace_dialog import WorkspaceSelectionDialog
except ImportError:
    pass

# Import dialog functions
from core.ui.dialogs.dialog_functions import (
    show_error_dialog,
)

__all__ = [
    'WorkspaceSelectionDialog',
    'show_error_dialog',
]