"""
UI Utilities - Helper functions for UI components

Provides consistent styling and behavior for dialogs and other UI elements.
"""

from PySide6.QtWidgets import QMessageBox, QWidget, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt
from typing import Optional


def _set_min_width(msg_box: QMessageBox, min_width: int = 250) -> None:
    """
    Force a minimum width on QMessageBox by adding a spacer to its layout.
    
    QMessageBox.setMinimumWidth() doesn't work because it uses a fixed layout.
    This workaround adds a spacer to the grid layout to force the width.
    """
    layout = msg_box.layout()
    if layout:
        spacer = QSpacerItem(min_width, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())


def show_warning(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show a warning message box with proper sizing.
    
    Ensures the window is wide enough to display the title without cropping.
    
    Args:
        parent: Parent widget
        title: Dialog title (shown in title bar)
        message: Warning message content
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    
    _set_min_width(msg_box, 250)
    
    msg_box.exec()


def show_info(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show an info message box with proper sizing.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Info message content
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    _set_min_width(msg_box, 250)
    msg_box.exec()


def show_error(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show an error message box with proper sizing.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Error message content
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    _set_min_width(msg_box, 250)
    msg_box.exec()


def show_question(parent: Optional[QWidget], title: str, message: str) -> bool:
    """
    Show a yes/no question dialog with proper sizing.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Question message
        
    Returns:
        True if user clicked Yes, False otherwise
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Question)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    msg_box.setDefaultButton(QMessageBox.StandardButton.No)
    _set_min_width(msg_box, 250)
    
    return msg_box.exec() == QMessageBox.StandardButton.Yes
