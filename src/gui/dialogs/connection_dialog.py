"""
Wireless Connection Dialog - Connect to Android devices via WiFi

Provides UI for wireless ADB pairing and connection.
"""

import logging
import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QCheckBox, QLabel,
    QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIntValidator

from utils.async_helper import safe_ensure_future

logger = logging.getLogger(__name__)


class WirelessDialog(QDialog):
    """Dialog for wireless ADB connection"""
    
    def __init__(self, device_manager, parent=None):
        """
        Initialize Wireless Connection Dialog
        
        Args:
            device_manager: DeviceManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.device_manager = device_manager
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup user interface"""
        self.setWindowTitle("Connect via WiFi")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        conn_group = QGroupBox("Connection")
        conn_layout = QFormLayout(conn_group)
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        conn_layout.addRow("IP Address:", self.ip_input)
        
        self.port_input = QLineEdit("5555")
        self.port_input.setValidator(QIntValidator(1, 65535))
        conn_layout.addRow("Port:", self.port_input)
        
        layout.addWidget(conn_group)
        
        self.pair_checkbox = QCheckBox("Pair Device (Android 11+)")
        self.pair_checkbox.toggled.connect(self._toggle_pairing)
        layout.addWidget(self.pair_checkbox)
        
        self.pair_group = QGroupBox("Pairing")
        pair_layout = QFormLayout(self.pair_group)
        
        self.pair_code_input = QLineEdit()
        self.pair_code_input.setPlaceholderText("123456")
        self.pair_code_input.setMaxLength(6)
        pair_layout.addRow("Pairing Code:", self.pair_code_input)
        
        self.pair_port_input = QLineEdit("37171")
        self.pair_port_input.setValidator(QIntValidator(1, 65535))
        pair_layout.addRow("Pairing Port:", self.pair_port_input)
        
        self.pair_group.setVisible(False)
        layout.addWidget(self.pair_group)
        
        info_label = QLabel(
            "💡 Enable Wireless Debugging in Developer Options on your device.\n"
            "For Android 11+, use pairing code from Wireless Debugging settings."
        )
        info_label.setWordWrap(True)
        info_label.setProperty("class", "secondary")
        layout.addWidget(info_label)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setDefault(True)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        button_layout.addWidget(self.connect_btn)
        
        layout.addLayout(button_layout)
    
    @Slot(bool)
    def _toggle_pairing(self, checked):
        """Toggle pairing group visibility"""
        self.pair_group.setVisible(checked)
        self.connect_btn.setText("Pair & Connect" if checked else "Connect")
    
    @Slot()
    def _on_connect_clicked(self):
        """Handle connect button click - wraps async method"""
        safe_ensure_future(self._connect())
    
    def _validate_ip(self, ip: str) -> bool:
        """
        Validate IP address format
        
        Args:
            ip: IP address string
            
        Returns:
            True if valid, False otherwise
        """
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        octets = ip.split('.')
        return all(0 <= int(octet) <= 255 for octet in octets)
    
    async def _connect(self):
        """Perform the wireless connection (async)"""
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        
        if not ip:
            QMessageBox.warning(self, "Invalid Input", "Please enter an IP address.")
            return
        
        if not self._validate_ip(ip):
            QMessageBox.warning(self, "Invalid IP", "Please enter a valid IP address (e.g., 192.168.1.100).")
            return
        
        if not port:
            QMessageBox.warning(self, "Invalid Input", "Please enter a port number.")
            return
        
        try:
            port_num = int(port)
            if port_num < 1 or port_num > 65535:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", "Port must be between 1 and 65535.")
            return
        
        if self.pair_checkbox.isChecked():
            pair_code = self.pair_code_input.text().strip()
            pair_port = self.pair_port_input.text().strip()
            
            if not pair_code or len(pair_code) != 6:
                QMessageBox.warning(self, "Invalid Pairing Code", "Pairing code must be 6 digits.")
                return
            
            if not pair_port:
                QMessageBox.warning(self, "Invalid Input", "Please enter a pairing port.")
                return
            
            try:
                pair_port_num = int(pair_port)
                if pair_port_num < 1 or pair_port_num > 65535:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Invalid Port", "Pairing port must be between 1 and 65535.")
                return
            
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText("Pairing...")
            
            try:
                success = await self.device_manager.pair_wireless(ip, pair_port_num, pair_code)
                if not success:
                    QMessageBox.critical(self, "Pairing Failed", "Failed to pair with device. Check the pairing code and try again.")
                    self.connect_btn.setEnabled(True)
                    self.connect_btn.setText("Pair & Connect")
                    return
            except Exception as e:
                logger.error(f"Pairing error: {e}")
                QMessageBox.critical(self, "Pairing Error", f"Error during pairing: {str(e)}")
                self.connect_btn.setEnabled(True)
                self.connect_btn.setText("Pair & Connect")
                return
        
        self.connect_btn.setText("Connecting...")
        
        try:
            device = await self.device_manager.connect_wireless(ip, port_num)
            if device:
                QMessageBox.information(self, "Success", f"Connected to {device.serial}")
                self.accept()
            else:
                QMessageBox.critical(self, "Connection Failed", "Failed to connect to device. Make sure wireless debugging is enabled.")
                self.connect_btn.setEnabled(True)
                self.connect_btn.setText("Connect")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            QMessageBox.critical(self, "Connection Error", f"Error connecting: {str(e)}")
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Connect")
