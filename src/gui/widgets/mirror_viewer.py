"""
Mirror Viewer Widget - Screen mirroring display and controls

Provides UI for starting/stopping screen mirroring with scrcpy.
"""

import logging
import asyncio
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, Slot, QSettings

from core.mirror_engine import MirrorEngine
from utils.async_helper import safe_ensure_future

logger = logging.getLogger(__name__)


def _clean_device_serial(serial: str) -> str:
    """Clean up mDNS-style device serials for display"""
    if '._adb-tls-' in serial:
        return serial.split('._adb-')[0]
    return serial


class MirrorViewerWidget(QWidget):
    """Widget for screen mirroring controls"""
    
    def __init__(self):
        """Initialize Mirror Viewer Widget"""
        super().__init__()
        self.mirror_engine = MirrorEngine()
        self.current_device = None
        self.settings = QSettings('ADBManager', 'ADBManager')
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("No device selected")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14pt; padding: 20px;")
        layout.addWidget(self.status_label)
        
        settings_group = QGroupBox("Mirroring Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Auto", "1920x1080", "1280x720", "854x480"])
        self.resolution_combo.setCurrentText(self.settings.value('mirror_resolution', 'Auto'))
        settings_layout.addRow("Resolution:", self.resolution_combo)
        
        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(1, 50)
        self.bitrate_spin.setSuffix(" Mbps")
        self.bitrate_spin.setValue(self.settings.value('mirror_bitrate', 8, type=int))
        settings_layout.addRow("Bitrate:", self.bitrate_spin)
        
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(15, 60)
        self.fps_spin.setSuffix(" fps")
        self.fps_spin.setValue(self.settings.value('mirror_fps', 60, type=int))
        settings_layout.addRow("Max FPS:", self.fps_spin)
        
        self.always_on_top_check = QCheckBox("Always on top")
        self.always_on_top_check.setChecked(self.settings.value('mirror_always_on_top', False, type=bool))
        settings_layout.addRow("", self.always_on_top_check)
        
        self.fullscreen_check = QCheckBox("Start in fullscreen")
        self.fullscreen_check.setChecked(self.settings.value('mirror_fullscreen', False, type=bool))
        settings_layout.addRow("", self.fullscreen_check)
        
        layout.addWidget(settings_group)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_btn = QPushButton("Start Mirroring")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start_mirroring)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Mirroring")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_mirroring)
        button_layout.addWidget(self.stop_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        info_label = QLabel(
            "💡 Requires scrcpy to be installed and available in PATH.\n"
            "Download from: https://github.com/Genymobile/scrcpy"
        )
        info_label.setWordWrap(True)
        info_label.setProperty("class", "secondary")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect mirror engine signals"""
        self.mirror_engine.mirror_started.connect(self._on_mirror_started)
        self.mirror_engine.mirror_stopped.connect(self._on_mirror_stopped)
        self.mirror_engine.error_occurred.connect(self._on_error)
    
    def set_device(self, device_serial: str):
        """
        Set current device
        
        Args:
            device_serial: Device serial number
        """
        self.current_device = device_serial
        
        if device_serial:
            display_name = _clean_device_serial(device_serial)
            self.status_label.setText(f"Ready to mirror: {display_name}")
            
            if self.mirror_engine.is_scrcpy_available():
                self.start_btn.setEnabled(True)
            else:
                self.status_label.setText("⚠️ scrcpy not found - please install scrcpy")
                self.start_btn.setEnabled(False)
        else:
            self.status_label.setText("No device selected")
            self.start_btn.setEnabled(False)
    
    @Slot()
    def _start_mirroring(self):
        """Start screen mirroring"""
        if not self.current_device:
            return
        
        options = {
            'resolution': self.resolution_combo.currentText(),
            'bitrate': self.bitrate_spin.value(),
            'max_fps': self.fps_spin.value(),
            'always_on_top': self.always_on_top_check.isChecked(),
            'fullscreen': self.fullscreen_check.isChecked()
        }
        
        self.settings.setValue('mirror_resolution', options['resolution'])
        self.settings.setValue('mirror_bitrate', options['bitrate'])
        self.settings.setValue('mirror_fps', options['max_fps'])
        self.settings.setValue('mirror_always_on_top', options['always_on_top'])
        self.settings.setValue('mirror_fullscreen', options['fullscreen'])
        
        self.start_btn.setEnabled(False)
        self.status_label.setText("Starting mirroring...")
        
        safe_ensure_future(self.mirror_engine.start_mirror(self.current_device, options))
    
    @Slot()
    def _stop_mirroring(self):
        """Stop screen mirroring"""
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Stopping mirroring...")
        safe_ensure_future(self.mirror_engine.stop_mirror())
    
    @Slot()
    def _on_mirror_started(self):
        """Handle mirror started signal"""
        display_name = _clean_device_serial(self.current_device) if self.current_device else ""
        self.status_label.setText(f"✅ Mirroring {display_name}")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.resolution_combo.setEnabled(False)
        self.bitrate_spin.setEnabled(False)
        self.fps_spin.setEnabled(False)
        self.always_on_top_check.setEnabled(False)
        self.fullscreen_check.setEnabled(False)
    
    @Slot()
    def _on_mirror_stopped(self):
        """Handle mirror stopped signal"""
        display_name = _clean_device_serial(self.current_device) if self.current_device else None
        self.status_label.setText(f"Ready to mirror: {display_name}" if display_name else "No device selected")
        self.start_btn.setEnabled(bool(self.current_device))
        self.stop_btn.setEnabled(False)
        
        self.resolution_combo.setEnabled(True)
        self.bitrate_spin.setEnabled(True)
        self.fps_spin.setEnabled(True)
        self.always_on_top_check.setEnabled(True)
        self.fullscreen_check.setEnabled(True)
    
    @Slot(str)
    def _on_error(self, error_msg: str):
        """Handle error signal"""
        QMessageBox.critical(self, "Mirroring Error", error_msg)
        self._on_mirror_stopped()
