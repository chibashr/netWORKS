"""
Dialog management functions for the netWORKS application.
These functions were extracted from main_window.py to improve modularity.
"""

import logging
from PySide6.QtWidgets import QMessageBox

# Setup logger
logger = logging.getLogger(__name__)

def show_error_dialog(main_window, title, message):
    """Show an error dialog with the specified title and message.
    
    Args:
        main_window: Reference to the main window
        title: str - Title of the error dialog
        message: str - Error message to display
    """
    logger.error(f"Error dialog: {title} - {message}")
    QMessageBox.critical(main_window, title, message) 