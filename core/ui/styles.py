#!/usr/bin/env python3
# Global styles for netWORKS UI components

# Base button style with improved hover/click feedback
BUTTON_STYLE = """
    QPushButton {
        background-color: #f5f5f5;
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        padding: 6px 12px;
        color: #333;
        font-weight: 500;
        min-height: 26px;
    }
    QPushButton:hover {
        background-color: #e6e6e6;
        border-color: #adadad;
    }
    QPushButton:pressed {
        background-color: #d4d4d4;
        border-color: #8c8c8c;
        padding-top: 7px;
        padding-bottom: 5px;
        padding-left: 13px;
        padding-right: 11px;
        box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.125);
    }
    QPushButton:disabled {
        background-color: #f8f8f8;
        border-color: #e0e0e0;
        color: #a0a0a0;
    }
"""

# Primary action button style (blue)
PRIMARY_BUTTON_STYLE = """
    QPushButton {
        background-color: #007bff;
        border: 1px solid #0062cc;
        border-radius: 4px;
        padding: 6px 12px;
        color: white;
        font-weight: 500;
        min-height: 26px;
    }
    QPushButton:hover {
        background-color: #0069d9;
        border-color: #0056b3;
    }
    QPushButton:pressed {
        background-color: #0056b3;
        border-color: #004085;
        padding-top: 7px;
        padding-bottom: 5px;
        padding-left: 13px;
        padding-right: 11px;
        box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.2);
    }
    QPushButton:disabled {
        background-color: #80bdff;
        border-color: #80bdff;
        color: #f8f9fa;
    }
"""

# Success button style (green)
SUCCESS_BUTTON_STYLE = """
    QPushButton {
        background-color: #28a745;
        border: 1px solid #218838;
        border-radius: 4px;
        padding: 6px 12px;
        color: white;
        font-weight: 500;
        min-height: 26px;
    }
    QPushButton:hover {
        background-color: #218838;
        border-color: #1e7e34;
    }
    QPushButton:pressed {
        background-color: #1e7e34;
        border-color: #1c7430;
        padding-top: 7px;
        padding-bottom: 5px;
        padding-left: 13px;
        padding-right: 11px;
        box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.2);
    }
    QPushButton:disabled {
        background-color: #9be7ac;
        border-color: #9be7ac;
        color: #f8f9fa;
    }
"""

# Danger button style (red)
DANGER_BUTTON_STYLE = """
    QPushButton {
        background-color: #dc3545;
        border: 1px solid #bd2130;
        border-radius: 4px;
        padding: 6px 12px;
        color: white;
        font-weight: 500;
        min-height: 26px;
    }
    QPushButton:hover {
        background-color: #c82333;
        border-color: #bd2130;
    }
    QPushButton:pressed {
        background-color: #bd2130;
        border-color: #a71d2a;
        padding-top: 7px;
        padding-bottom: 5px;
        padding-left: 13px;
        padding-right: 11px;
        box-shadow: inset 0 3px 5px rgba(0, 0, 0, 0.2);
    }
    QPushButton:disabled {
        background-color: #f5c6cb;
        border-color: #f5c6cb;
        color: #f8f9fa;
    }
"""

# Tool button style for toolbar buttons and small action buttons
TOOL_BUTTON_STYLE = """
    QToolButton {
        background-color: transparent;
        border: 1px solid #e0e0e0;
        border-radius: 3px;
        padding: 2px;
        color: #2c5aa0;
        font-size: 8pt;
        font-weight: bold;
        min-width: 45px;
        min-height: 40px;
        text-align: center;
    }
    QToolButton:hover {
        background-color: #e8f0ff;
        border: 1px solid #c0d0f0;
    }
    QToolButton:pressed {
        background-color: #d0e0ff;
        border: 1px solid #a0b0e0;
        padding-top: 3px;
        padding-left: 3px;
        padding-bottom: 1px;
        padding-right: 1px;
    }
    QToolButton:checked {
        background-color: #d0e0ff;
        border: 1px solid #a0b0e0;
        font-weight: bold;
    }
    QToolButton:disabled {
        background-color: transparent;
        border: 1px solid #e8e8e8;
        color: #a0a0a0;
    }
"""

# Combo box style with better hover/focus states
COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        padding: 4px 10px;
        background-color: white;
        min-height: 26px;
    }
    QComboBox:hover {
        border-color: #adadad;
    }
    QComboBox:focus {
        border-color: #80bdff;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #d0d0d0;
    }
    QComboBox::down-arrow {
        image: url(:/icons/dropdown_arrow.png);
        width: 10px;
        height: 10px;
    }
    QComboBox:on {
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #d0d0d0;
        selection-background-color: #007bff;
        selection-color: white;
    }
"""

# Table style with modern look
TABLE_STYLE = """
    QTableWidget, QTableView {
        border: 1px solid #d0d0d0;
        gridline-color: #f0f0f0;
        selection-background-color: #cce5ff;
        selection-color: #000;
    }
    QTableWidget::item, QTableView::item {
        padding: 4px;
        border-bottom: 1px solid #f0f0f0;
    }
    QTableWidget::item:selected, QTableView::item:selected {
        background-color: #cce5ff;
    }
    QTableWidget::item:hover, QTableView::item:hover {
        background-color: #f2f8ff;
    }
    QHeaderView::section {
        background-color: #f8f9fa;
        border: 1px solid #d0d0d0;
        padding: 6px;
        font-weight: bold;
    }
    QHeaderView::section:hover {
        background-color: #e9ecef;
    }
    QScrollBar:vertical {
        border: 1px solid #d0d0d0;
        background: white;
        width: 12px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        min-height: 20px;
        border-radius: 6px;
    }
    QScrollBar::handle:vertical:hover {
        background: #a0a0a0;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
        height: 0px;
    }
"""

# Apply standard styles to a widget
def apply_button_styles(widget):
    """Apply standard button styles to all buttons in a widget."""
    from PySide6.QtWidgets import QPushButton, QToolButton
    
    for child in widget.findChildren(QPushButton):
        # Skip buttons that already have custom styling
        if not child.styleSheet():
            child.setStyleSheet(BUTTON_STYLE)
    
    for child in widget.findChildren(QToolButton):
        # Skip buttons that already have custom styling
        if not child.styleSheet():
            child.setStyleSheet(TOOL_BUTTON_STYLE) 