"""
Wireless Connection Dialog - Connect to devices over WiFi

This dialog allows users to connect to Android devices wirelessly.
"""

import asyncio
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt, Slot

from core.device_manager import DeviceManager

logger = logging.getLogger(__name__)


class WirelessDialog(QDialog):
    """Dialog for wireless ADB connection"""
    
    def __init__(self, device_manager: DeviceManager, parent=None):
        """
        Initialize Wireless Dialog
        
        Args:
            device_manager: DeviceManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.device_manager = device_manager
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup user interface"""
        self.setWindowTitle("Wireless Connection")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        instructions = QLabel(
            "Connect to an Android device over WiFi.\n\n"
            "Requirements:\n"
            "1. Device must be on the same network\n"
            "2. USB debugging must be enabled\n"
            "3. Wireless debugging must be enabled (Android 11+)\n\n"
            "Enter the device IP address and port:"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        form_layout = QFormLayout()
        
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("192.168.1.100")
        form_layout.addRow("IP Address:", self.ip_edit)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(5555)
        form_layout.addRow("Port:", self.port_spin)
        
        layout.addLayout(form_layout)
        
        button_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect)
        self.connect_btn.setDefault(True)
        button_layout.addWidget(self.connect_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    @Slot()
    def _connect(self):
        """Connect to device"""
        ip = self.ip_edit.text().strip()
        port = self.port_spin.value()
        
        if not ip:
            QMessageBox.warning(self, "Error", "Please enter an IP address")
            return
        
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")
        
        asyncio.ensure_future(self._do_connect(ip, port))
    
    async def _do_connect(self, ip: str, port: int):
        """
        Perform connection
        
        Args:
            ip: Device IP address
            port: ADB port
        """
        try:
            success = await self.device_manager.connect_wireless(ip, port)
            
            if success:
                QMessageBox.information(
                    self, "Success",
                    f"Successfully connected to {ip}:{port}"
                )
                self.accept()
            else:
                QMessageBox.warning(
                    self, "Error",
                    f"Failed to connect to {ip}:{port}\n\n"
                    "Please check:\n"
                    "- Device is on the same network\n"
                    "- Wireless debugging is enabled\n"
                    "- IP address and port are correct"
                )
                self.connect_btn.setEnabled(True)
                self.connect_btn.setText("Connect")
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            QMessageBox.warning(self, "Error", f"Connection failed: {e}")
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Connect")
