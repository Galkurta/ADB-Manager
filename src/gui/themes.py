"""
Theme management for ADB Manager application.

Provides dark and light themes with modern color palettes and QSS stylesheets.
"""

from enum import Enum
from typing import Dict


class Theme(Enum):
    """Available themes"""
    DARK = "dark"
    LIGHT = "light"


class ThemeManager:
    """Manages application theming"""
    
    DARK_COLORS = {
        'background': '#1e1e1e',
        'surface': '#252526',
        'surface_hover': '#2a2d2e',
        'primary': '#007acc',
        'primary_hover': '#1c97ea',
        'text': '#cccccc',
        'text_secondary': '#858585',
        'border': '#3c3c3c',
        'success': '#4ec9b0',
        'warning': '#ce9178',
        'error': '#f48771',
        'selection': '#264f78'
    }
    
    LIGHT_COLORS = {
        'background': '#ffffff',
        'surface': '#f3f3f3',
        'surface_hover': '#e8e8e8',
        'primary': '#0078d4',
        'primary_hover': '#106ebe',
        'text': '#1e1e1e',
        'text_secondary': '#616161',
        'border': '#e0e0e0',
        'success': '#107c10',
        'warning': '#ca5010',
        'error': '#d13438',
        'selection': '#cce8ff'
    }
    
    @staticmethod
    def get_stylesheet(theme: Theme) -> str:
        """
        Get QSS stylesheet for the specified theme
        
        Args:
            theme: Theme to apply
            
        Returns:
            QSS stylesheet string
        """
        colors = ThemeManager.DARK_COLORS if theme == Theme.DARK else ThemeManager.LIGHT_COLORS
        
        return f"""
/* Main Window */
QMainWindow {{
    background-color: {colors['background']};
    color: {colors['text']};
}}

/* Menu Bar */
QMenuBar {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border-bottom: 1px solid {colors['border']};
    padding: 4px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 4px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {colors['surface_hover']};
}}

QMenuBar::item:pressed {{
    background-color: {colors['primary']};
}}

/* Menu */
QMenu {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {colors['surface_hover']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {colors['border']};
    margin: 4px 8px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {colors['surface']};
    color: {colors['text_secondary']};
    border-top: 1px solid {colors['border']};
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {colors['border']};
    background-color: {colors['background']};
    border-radius: 4px;
}}

QTabBar::tab {{
    background-color: {colors['surface']};
    color: {colors['text']};
    padding: 8px 16px;
    border: 1px solid {colors['border']};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {colors['background']};
    color: {colors['primary']};
    border-bottom: 2px solid {colors['primary']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {colors['surface_hover']};
}}

/* Buttons */
QPushButton {{
    background-color: {colors['primary']};
    color: white;
    border: none;
    padding: 6px 16px;
    border-radius: 4px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {colors['primary_hover']};
}}

QPushButton:pressed {{
    background-color: {colors['primary']};
    padding-top: 7px;
    padding-bottom: 5px;
}}

QPushButton:disabled {{
    background-color: {colors['surface']};
    color: {colors['text_secondary']};
}}

QPushButton[flat="true"] {{
    background-color: transparent;
    color: {colors['text']};
}}

QPushButton[flat="true"]:hover {{
    background-color: {colors['surface_hover']};
}}

/* Combo Box */
QComboBox {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 6px 10px;
    padding-right: 30px;
    min-height: 24px;
    min-width: 150px;
    outline: none;
}}

QComboBox:hover {{
    border-color: {colors['text_secondary']};
}}

QComboBox:focus {{
    border-color: {colors['text_secondary']};
    outline: none;
}}

QComboBox::drop-down {{
    subcontrol-origin: border;
    subcontrol-position: center right;
    width: 24px;
    border-left: 1px solid {colors['border']};
    background-color: transparent;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
    margin-right: 1px;
}}

QComboBox::drop-down:hover {{
    background-color: {colors['surface_hover']};
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {colors['text']};
    width: 0px;
    height: 0px;
}}

QComboBox QAbstractItemView {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: 1px solid {colors['border']};
    selection-background-color: {colors['selection']};
    outline: none;
}}

/* Line Edit */
QLineEdit {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 4px 8px;
}}

QLineEdit:focus {{
    border-color: {colors['primary']};
}}

/* Text Edit */
QTextEdit, QPlainTextEdit {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    selection-background-color: {colors['selection']};
}}

/* Tree Widget */
QTreeWidget {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    outline: none;
}}

QTreeWidget::item {{
    padding: 4px;
}}

QTreeWidget::item:selected {{
    background-color: {colors['selection']};
}}

QTreeWidget::item:hover {{
    background-color: {colors['surface_hover']};
}}

QTreeWidget::branch {{
    background-color: {colors['surface']};
}}

/* Table Widget */
QTableWidget {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    gridline-color: {colors['border']};
}}

QTableWidget::item:selected {{
    background-color: {colors['selection']};
}}

QHeaderView::section {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: none;
    border-bottom: 1px solid {colors['border']};
    padding: 6px;
    font-weight: 600;
}}

/* Scroll Bar */
QScrollBar:vertical {{
    background-color: {colors['surface']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {colors['border']};
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {colors['text_secondary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {colors['surface']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {colors['border']};
    border-radius: 6px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {colors['text_secondary']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {colors['surface']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    text-align: center;
    color: {colors['text']};
}}

QProgressBar::chunk {{
    background-color: {colors['primary']};
    border-radius: 3px;
}}

/* Group Box */
QGroupBox {{
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    background-color: {colors['background']};
}}

/* Check Box */
QCheckBox {{
    color: {colors['text']};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {colors['border']};
    border-radius: 3px;
    background-color: {colors['surface']};
}}

QCheckBox::indicator:checked {{
    background-color: {colors['primary']};
    border-color: {colors['primary']};
}}

QCheckBox::indicator:hover {{
    border-color: {colors['primary']};
}}

/* Radio Button */
QRadioButton {{
    color: {colors['text']};
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {colors['border']};
    border-radius: 8px;
    background-color: {colors['surface']};
}}

QRadioButton::indicator:checked {{
    background-color: {colors['primary']};
    border-color: {colors['primary']};
}}

QRadioButton::indicator:hover {{
    border-color: {colors['primary']};
}}

/* Spin Box */
QSpinBox, QDoubleSpinBox {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 6px 10px;
    padding-right: 30px;
    min-height: 24px;
    outline: none;
    selection-background-color: {colors['surface_hover']};
    selection-color: {colors['text']};
}}

QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {colors['text_secondary']};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {colors['text_secondary']};
    outline: none;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid {colors['border']};
    background-color: transparent;
    border-top-right-radius: 3px;
    margin-top: 1px;
    margin-right: 1px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: {colors['surface_hover']};
}}

QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
    background-color: {colors['surface_hover']};
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {colors['text']};
    width: 0px;
    height: 0px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 24px;
    border-left: 1px solid {colors['border']};
    border-top: 1px solid {colors['border']};
    background-color: transparent;
    border-bottom-right-radius: 3px;
    margin-bottom: 1px;
    margin-right: 1px;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {colors['surface_hover']};
}}

QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background-color: {colors['surface_hover']};
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {colors['text']};
    width: 0px;
    height: 0px;
}}

/* Slider */
QSlider::groove:horizontal {{
    background-color: {colors['surface']};
    height: 4px;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background-color: {colors['primary']};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {colors['primary_hover']};
}}

/* Tool Tip */
QToolTip {{
    background-color: {colors['surface']};
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 4px;
}}

/* Dialog */
QDialog {{
    background-color: {colors['background']};
    color: {colors['text']};
}}

/* Label */
QLabel {{
    color: {colors['text']};
}}

QLabel[class="secondary"] {{
    color: {colors['text_secondary']};
}}

QLabel[class="success"] {{
    color: {colors['success']};
}}

QLabel[class="warning"] {{
    color: {colors['warning']};
}}

QLabel[class="error"] {{
    color: {colors['error']};
}}
"""
    
    @staticmethod
    def get_colors(theme: Theme) -> Dict[str, str]:
        """
        Get color palette for the specified theme
        
        Args:
            theme: Theme to get colors for
            
        Returns:
            Dictionary of color names to hex values
        """
        return ThemeManager.DARK_COLORS if theme == Theme.DARK else ThemeManager.LIGHT_COLORS
