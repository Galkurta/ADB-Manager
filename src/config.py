"""
Configuration Manager - Application settings and preferences

This module handles loading, saving, and managing application configuration.
"""

import logging
from pathlib import Path
from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration and user preferences"""
    
    def __init__(self):
        """Initialize configuration manager"""
        self.settings = QSettings("ADB Manager", "ADB Manager")
        logger.info("Config Manager initialized")
    
    def save_window_geometry(self, geometry: bytes):
        """Save main window geometry"""
        self.settings.setValue("window/geometry", geometry)
    
    def load_window_geometry(self) -> bytes:
        """Load main window geometry"""
        return self.settings.value("window/geometry", b"")
    
    def save_window_state(self, state: bytes):
        """Save main window state"""
        self.settings.setValue("window/state", state)
    
    def load_window_state(self) -> bytes:
        """Load main window state"""
        return self.settings.value("window/state", b"")
    
    def save_last_device(self, serial: str):
        """Save last connected device"""
        self.settings.setValue("device/last_serial", serial)
    
    def load_last_device(self) -> str:
        """Load last connected device"""
        return self.settings.value("device/last_serial", "")
    
    def save_theme(self, theme: str):
        """Save theme preference (light/dark)"""
        self.settings.setValue("appearance/theme", theme)
    
    def load_theme(self) -> str:
        """Load theme preference"""
        return self.settings.value("appearance/theme", "light")
    
    def save_adb_path(self, path: str):
        """Save custom ADB binary path"""
        self.settings.setValue("adb/custom_path", path)
    
    def load_adb_path(self) -> str:
        """Load custom ADB binary path"""
        return self.settings.value("adb/custom_path", "")
    
    def save_last_local_path(self, path: str):
        """Save last used local directory"""
        self.settings.setValue("files/last_local_path", path)
    
    def load_last_local_path(self) -> str:
        """Load last used local directory"""
        return self.settings.value("files/last_local_path", str(Path.home()))
    
    def save_last_remote_path(self, path: str):
        """Save last used remote directory"""
        self.settings.setValue("files/last_remote_path", path)
    
    def load_last_remote_path(self) -> str:
        """Load last used remote directory"""
        return self.settings.value("files/last_remote_path", "/sdcard")
