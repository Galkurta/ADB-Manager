"""
Settings Dialog - Application configuration

Provides tabbed interface for all application settings.
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QWidget, QPushButton, QLineEdit,
    QSpinBox, QCheckBox, QComboBox, QLabel,
    QFileDialog, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, Slot, QSettings

from gui.themes import Theme

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Settings dialog with tabbed interface"""
    
    def __init__(self, settings: QSettings, parent=None):
        """
        Initialize Settings Dialog
        
        Args:
            settings: QSettings instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Setup user interface"""
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_general_tab(), "General")
        self.tabs.addTab(self._create_adb_tab(), "ADB")
        self.tabs.addTab(self._create_file_tab(), "File Transfer")
        self.tabs.addTab(self._create_mirror_tab(), "Mirroring")
        self.tabs.addTab(self._create_advanced_tab(), "Advanced")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        appearance_layout.addRow("Theme:", self.theme_combo)
        
        layout.addWidget(appearance_group)
        
        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)
        
        self.auto_connect_check = QCheckBox("Auto-connect to last device")
        behavior_layout.addWidget(self.auto_connect_check)
        
        self.minimize_tray_check = QCheckBox("Minimize to system tray")
        behavior_layout.addWidget(self.minimize_tray_check)
        
        layout.addWidget(behavior_group)
        
        layout.addStretch()
        return widget
    
    def _create_adb_tab(self) -> QWidget:
        """Create ADB settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # ADB Configuration
        adb_group = QGroupBox("ADB Configuration")
        adb_layout = QFormLayout(adb_group)
        
        adb_path_layout = QHBoxLayout()
        self.adb_path_input = QLineEdit()
        self.adb_path_input.setPlaceholderText("Auto-detect")
        adb_path_layout.addWidget(self.adb_path_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_adb)
        adb_path_layout.addWidget(browse_btn)
        
        adb_layout.addRow("ADB Binary:", adb_path_layout)
        
        self.connection_timeout_spin = QSpinBox()
        self.connection_timeout_spin.setRange(5, 120)
        self.connection_timeout_spin.setSuffix(" seconds")
        adb_layout.addRow("Connection Timeout:", self.connection_timeout_spin)
        
        self.scan_interval_spin = QSpinBox()
        self.scan_interval_spin.setRange(1, 10)
        self.scan_interval_spin.setSuffix(" seconds")
        adb_layout.addRow("Device Scan Interval:", self.scan_interval_spin)
        
        layout.addWidget(adb_group)
        
        # Wireless ADB
        wireless_group = QGroupBox("Wireless ADB")
        wireless_layout = QFormLayout(wireless_group)
        
        self.wireless_port_spin = QSpinBox()
        self.wireless_port_spin.setRange(1, 65535)
        self.wireless_port_spin.setValue(5555)
        wireless_layout.addRow("Default Port:", self.wireless_port_spin)
        
        layout.addWidget(wireless_group)
        
        layout.addStretch()
        return widget
    
    def _create_file_tab(self) -> QWidget:
        """Create file transfer settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # File Transfer
        transfer_group = QGroupBox("File Transfer")
        transfer_layout = QFormLayout(transfer_group)
        
        download_layout = QHBoxLayout()
        self.download_path_input = QLineEdit()
        download_layout.addWidget(self.download_path_input)
        
        browse_download_btn = QPushButton("Browse...")
        browse_download_btn.clicked.connect(self._browse_download)
        download_layout.addWidget(browse_download_btn)
        
        transfer_layout.addRow("Download Location:", download_layout)
        
        self.buffer_size_spin = QSpinBox()
        self.buffer_size_spin.setRange(1, 128)
        self.buffer_size_spin.setSuffix(" MB")
        transfer_layout.addRow("Buffer Size:", self.buffer_size_spin)
        
        layout.addWidget(transfer_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.confirm_overwrite_check = QCheckBox("Confirm before overwriting files")
        options_layout.addWidget(self.confirm_overwrite_check)
        
        self.show_hidden_check = QCheckBox("Show hidden files")
        options_layout.addWidget(self.show_hidden_check)
        
        layout.addWidget(options_group)
        
        layout.addStretch()
        return widget
    
    def _create_mirror_tab(self) -> QWidget:
        """Create mirroring settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Scrcpy Configuration
        scrcpy_group = QGroupBox("Scrcpy Configuration")
        scrcpy_layout = QFormLayout(scrcpy_group)
        
        scrcpy_path_layout = QHBoxLayout()
        self.scrcpy_path_input = QLineEdit()
        self.scrcpy_path_input.setPlaceholderText("Auto-detect (from PATH)")
        scrcpy_path_layout.addWidget(self.scrcpy_path_input)
        
        browse_scrcpy_btn = QPushButton("Browse...")
        browse_scrcpy_btn.clicked.connect(self._browse_scrcpy)
        scrcpy_path_layout.addWidget(browse_scrcpy_btn)
        
        scrcpy_layout.addRow("Scrcpy Directory:", scrcpy_path_layout)
        
        layout.addWidget(scrcpy_group)
        
        # Quality Settings
        quality_group = QGroupBox("Quality Settings")
        quality_layout = QFormLayout(quality_group)
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Auto", "1920x1080", "1280x720", "854x480"])
        quality_layout.addRow("Resolution:", self.resolution_combo)
        
        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(1, 50)
        self.bitrate_spin.setSuffix(" Mbps")
        quality_layout.addRow("Bitrate:", self.bitrate_spin)
        
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(15, 60)
        self.fps_spin.setSuffix(" fps")
        quality_layout.addRow("Max FPS:", self.fps_spin)
        
        layout.addWidget(quality_group)
        
        # Window Options
        window_group = QGroupBox("Window Options")
        window_layout = QVBoxLayout(window_group)
        
        self.always_on_top_check = QCheckBox("Always on top")
        window_layout.addWidget(self.always_on_top_check)
        
        self.fullscreen_check = QCheckBox("Start in fullscreen")
        window_layout.addWidget(self.fullscreen_check)
        
        layout.addWidget(window_group)
        
        layout.addStretch()
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logging
        logging_group = QGroupBox("Logging")
        logging_layout = QVBoxLayout(logging_group)
        
        self.debug_logging_check = QCheckBox("Enable debug logging")
        logging_layout.addWidget(self.debug_logging_check)
        
        log_path_layout = QHBoxLayout()
        log_path_layout.addWidget(QLabel("Log Location:"))
        self.log_path_input = QLineEdit()
        self.log_path_input.setReadOnly(True)
        log_path_layout.addWidget(self.log_path_input)
        
        open_log_btn = QPushButton("Open")
        open_log_btn.clicked.connect(self._open_log_folder)
        log_path_layout.addWidget(open_log_btn)
        
        logging_layout.addLayout(log_path_layout)
        
        layout.addWidget(logging_group)
        
        # Maintenance
        maintenance_group = QGroupBox("Maintenance")
        maintenance_layout = QVBoxLayout(maintenance_group)
        
        clear_cache_btn = QPushButton("Clear Cache")
        clear_cache_btn.clicked.connect(self._clear_cache)
        maintenance_layout.addWidget(clear_cache_btn)
        
        layout.addWidget(maintenance_group)
        
        layout.addStretch()
        return widget
    
    def _load_settings(self):
        """Load settings from QSettings"""
        # General
        theme = self.settings.value('theme', Theme.DARK.value)
        self.theme_combo.setCurrentText("Dark" if theme == Theme.DARK.value else "Light")
        self.auto_connect_check.setChecked(self.settings.value('auto_connect', False, type=bool))
        self.minimize_tray_check.setChecked(self.settings.value('minimize_tray', False, type=bool))
        
        # ADB
        self.adb_path_input.setText(self.settings.value('adb_path', ''))
        self.connection_timeout_spin.setValue(self.settings.value('connection_timeout', 30, type=int))
        self.scan_interval_spin.setValue(self.settings.value('scan_interval', 2, type=int))
        self.wireless_port_spin.setValue(self.settings.value('wireless_port', 5555, type=int))
        
        # File Transfer
        self.download_path_input.setText(self.settings.value('download_path', str(Path.home() / 'Downloads')))
        self.buffer_size_spin.setValue(self.settings.value('buffer_size', 8, type=int))
        self.confirm_overwrite_check.setChecked(self.settings.value('confirm_overwrite', True, type=bool))
        self.show_hidden_check.setChecked(self.settings.value('show_hidden', False, type=bool))
        
        # Mirroring
        self.scrcpy_path_input.setText(self.settings.value('scrcpy_path', ''))
        self.resolution_combo.setCurrentText(self.settings.value('mirror_resolution', 'Auto'))
        self.bitrate_spin.setValue(self.settings.value('mirror_bitrate', 8, type=int))
        self.fps_spin.setValue(self.settings.value('mirror_fps', 60, type=int))
        self.always_on_top_check.setChecked(self.settings.value('mirror_always_on_top', False, type=bool))
        self.fullscreen_check.setChecked(self.settings.value('mirror_fullscreen', False, type=bool))
        
        # Advanced
        self.debug_logging_check.setChecked(self.settings.value('debug_logging', False, type=bool))
        self.log_path_input.setText(str(Path.cwd() / 'logs'))
    
    @Slot()
    def _save_settings(self):
        """Save settings to QSettings"""
        # General
        theme_value = Theme.DARK.value if self.theme_combo.currentText() == "Dark" else Theme.LIGHT.value
        self.settings.setValue('theme', theme_value)
        self.settings.setValue('auto_connect', self.auto_connect_check.isChecked())
        self.settings.setValue('minimize_tray', self.minimize_tray_check.isChecked())
        
        # ADB
        self.settings.setValue('adb_path', self.adb_path_input.text())
        self.settings.setValue('connection_timeout', self.connection_timeout_spin.value())
        self.settings.setValue('scan_interval', self.scan_interval_spin.value())
        self.settings.setValue('wireless_port', self.wireless_port_spin.value())
        
        # File Transfer
        self.settings.setValue('download_path', self.download_path_input.text())
        self.settings.setValue('buffer_size', self.buffer_size_spin.value())
        self.settings.setValue('confirm_overwrite', self.confirm_overwrite_check.isChecked())
        self.settings.setValue('show_hidden', self.show_hidden_check.isChecked())
        
        # Mirroring
        self.settings.setValue('scrcpy_path', self.scrcpy_path_input.text())
        self.settings.setValue('mirror_resolution', self.resolution_combo.currentText())
        self.settings.setValue('mirror_bitrate', self.bitrate_spin.value())
        self.settings.setValue('mirror_fps', self.fps_spin.value())
        self.settings.setValue('mirror_always_on_top', self.always_on_top_check.isChecked())
        self.settings.setValue('mirror_fullscreen', self.fullscreen_check.isChecked())
        
        # Advanced
        self.settings.setValue('debug_logging', self.debug_logging_check.isChecked())
        
        logger.info("Settings saved")
        self.accept()
    
    @Slot()
    def _reset_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings.clear()
            self._load_settings()
            logger.info("Settings reset to defaults")
    
    @Slot()
    def _browse_adb(self):
        """Browse for ADB binary"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ADB Binary",
            "",
            "Executables (*.exe);;All Files (*.*)"
        )
        if file_path:
            self.adb_path_input.setText(file_path)
    
    @Slot()
    def _browse_download(self):
        """Browse for download location"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Download Location",
            self.download_path_input.text()
        )
        if dir_path:
            self.download_path_input.setText(dir_path)
    
    @Slot()
    def _browse_scrcpy(self):
        """Browse for scrcpy directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Scrcpy Directory",
            self.scrcpy_path_input.text() or "D:\\"
        )
        if dir_path:
            self.scrcpy_path_input.setText(dir_path)
    
    @Slot()
    def _open_log_folder(self):
        """Open log folder in file explorer"""
        import subprocess
        import platform
        
        log_path = Path(self.log_path_input.text())
        log_path.mkdir(parents=True, exist_ok=True)
        
        if platform.system() == 'Windows':
            subprocess.run(['explorer', str(log_path)])
        elif platform.system() == 'Darwin':
            subprocess.run(['open', str(log_path)])
        else:
            subprocess.run(['xdg-open', str(log_path)])
    
    @Slot()
    def _clear_cache(self):
        """Clear application cache"""
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            "Are you sure you want to clear the cache?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 1. Clear device cache
                cache_file = Path("config/device_cache.json")
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info("Removed device cache file")

                # 2. Clear logs (keep current log file if possible, or just delete old ones)
                log_dir = Path("logs")
                if log_dir.exists():
                    current_log = None
                    # Try to identify current log file (it's locked likely)
                    # Simple approach: try to delete all, ignore errors for locked files
                    deleted_count = 0
                    for log_file in log_dir.glob("*.log"):
                        try:
                            log_file.unlink()
                            deleted_count += 1
                        except OSError:
                            pass # Likely currently open
                    logger.info(f"Cleared {deleted_count} log files")
                
                # 3. Clear temp binaries if any
                for temp_dir in ["binaries_temp", "binaries_temp_scrcpy"]:
                    path = Path(temp_dir)
                    if path.exists():
                        import shutil
                        shutil.rmtree(path, ignore_errors=True)

                QMessageBox.information(
                    self, 
                    "Cache Cleared", 
                    "Temporary files, logs, and device cache have been cleared.\n"
                    "Some settings may take effect after restart."
                )
                logger.info("Cache clearing completed")
            
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
                QMessageBox.warning(self, "Error", f"Failed to clear some cache files: {e}")
